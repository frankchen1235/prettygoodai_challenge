from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import WebSocketException

from pgaibot.config import Settings
from pgaibot.run_store import read_prompt_for_run

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class RealtimeBridge:
    def __init__(self, websocket: WebSocket, run_id: str, directory: Path, settings: Settings) -> None:
        self.websocket = websocket
        self.run_id = run_id
        self.directory = directory
        self.settings = settings
        self.started_at = datetime.now(UTC)
        self.counts: dict[str, int] = {}
        self.stream_sid: str | None = None
        self.call_sid: str | None = None
        self.media_payload_chars = 0
        self.openai_audio_delta_chars = 0
        self.close_reason = "unknown"
        self.assistant_transcript_parts: list[str] = []
        self.input_transcript_parts: list[str] = []
        self.log_lock = asyncio.Lock()
        self.pending_response_task: asyncio.Task[None] | None = None
        self.response_in_progress = False
        self.agent_speaking = False
        self.bot_audio_pending = False
        self.mark_index = 0

    async def run(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        await self.websocket.accept()

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
        }
        url = f"{OPENAI_REALTIME_URL}?model={self.settings.openai_realtime_model}"

        try:
            async with websockets.connect(
                url,
                additional_headers=headers,
                max_size=None,
            ) as openai_ws:
                await self.configure_openai(openai_ws)
                await asyncio.gather(
                    self.forward_twilio_to_openai(openai_ws),
                    self.forward_openai_to_twilio(openai_ws),
                )
        except WebSocketDisconnect:
            self.close_reason = "twilio_websocket_disconnect"
        except (OSError, RuntimeError, TimeoutError, WebSocketException, json.JSONDecodeError) as exc:
            self.close_reason = f"bridge_error:{type(exc).__name__}"
            await self.log_event("bridge.error", {"error": repr(exc)})
        finally:
            if self.pending_response_task is not None:
                self.pending_response_task.cancel()
            await self.write_summary()

    async def configure_openai(self, openai_ws: Any) -> None:
        prompt = read_prompt_for_run(self.run_id)
        session_update = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": self.settings.openai_realtime_model,
                "output_modalities": ["audio"],
                "instructions": prompt,
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "transcription": {
                            "model": self.settings.openai_transcribe_model,
                            "language": "en",
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": False,
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 900,
                            "interrupt_response": False,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": self.settings.openai_realtime_voice,
                    },
                },
            },
        }
        await openai_ws.send(json.dumps(session_update))
        await self.log_event("openai.client.session_update", session_update)

    async def forward_twilio_to_openai(self, openai_ws: Any) -> None:
        while True:
            elapsed = (datetime.now(UTC) - self.started_at).total_seconds()
            if elapsed >= self.settings.media_stream_max_seconds:
                self.close_reason = "max_seconds_reached"
                await self.close_twilio_websocket()
                await openai_ws.close()
                return

            try:
                raw_message = await asyncio.wait_for(self.websocket.receive_text(), timeout=1.0)
            except TimeoutError:
                continue

            message = json.loads(raw_message)
            event = str(message.get("event", "unknown"))
            self.counts[f"twilio.{event}"] = self.counts.get(f"twilio.{event}", 0) + 1

            self.stream_sid = message.get("streamSid", self.stream_sid)
            if event == "start":
                start = message.get("start", {})
                self.call_sid = start.get("callSid", self.call_sid)
                self.stream_sid = start.get("streamSid", self.stream_sid)
            elif event == "media":
                payload = message.get("media", {}).get("payload", "")
                self.media_payload_chars += len(payload)
                await openai_ws.send(
                    json.dumps({"type": "input_audio_buffer.append", "audio": payload})
                )
            elif event == "mark":
                self.bot_audio_pending = False
            elif event == "stop":
                self.close_reason = "twilio_stop"
                await openai_ws.close()
                return

            await self.log_event("twilio.server", message)

    async def forward_openai_to_twilio(self, openai_ws: Any) -> None:
        async for raw_message in openai_ws:
            message = json.loads(raw_message)
            event = str(message.get("type", "unknown"))
            self.counts[f"openai.{event}"] = self.counts.get(f"openai.{event}", 0) + 1
            await self.log_event("openai.server", message)

            if event == "response.output_audio.delta":
                await self.send_audio_to_twilio(message.get("delta", ""))
            elif event == "response.output_audio_transcript.delta":
                self.assistant_transcript_parts.append(message.get("delta", ""))
            elif event == "response.output_audio_transcript.done":
                self.assistant_transcript_parts.append("\n")
            elif event == "response.created":
                self.response_in_progress = True
            elif event == "response.output_audio.done":
                await self.mark_twilio_audio()
            elif event == "response.done":
                self.response_in_progress = False
            elif event == "input_audio_buffer.speech_started":
                self.agent_speaking = True
                self.cancel_pending_response()
            elif event == "input_audio_buffer.speech_stopped":
                self.agent_speaking = False
                self.schedule_response(openai_ws)
            elif event == "conversation.item.input_audio_transcription.delta":
                self.input_transcript_parts.append(message.get("delta", ""))
            elif event == "conversation.item.input_audio_transcription.completed":
                self.input_transcript_parts.append("\n")
            elif event == "error":
                self.close_reason = "openai_error"

    async def send_audio_to_twilio(self, payload: str) -> None:
        if not payload or not self.stream_sid:
            return

        self.openai_audio_delta_chars += len(payload)
        self.bot_audio_pending = True
        await self.websocket.send_text(
            json.dumps(
                {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload},
                }
            )
        )

    async def mark_twilio_audio(self) -> None:
        if not self.stream_sid or not self.bot_audio_pending:
            return

        self.mark_index += 1
        await self.websocket.send_text(
            json.dumps(
                {
                    "event": "mark",
                    "streamSid": self.stream_sid,
                    "mark": {"name": f"bot-audio-{self.mark_index}"},
                }
            )
        )

    def cancel_pending_response(self) -> None:
        if self.pending_response_task is not None and not self.pending_response_task.done():
            self.pending_response_task.cancel()
        self.pending_response_task = None

    def schedule_response(self, openai_ws: Any) -> None:
        if self.response_in_progress or self.bot_audio_pending:
            return

        self.cancel_pending_response()
        self.pending_response_task = asyncio.create_task(self.create_response_after_delay(openai_ws))

    async def create_response_after_delay(self, openai_ws: Any) -> None:
        try:
            await asyncio.sleep(self.settings.response_delay_seconds)
            if self.agent_speaking or self.response_in_progress or self.bot_audio_pending:
                return
            await openai_ws.send(json.dumps({"type": "response.create", "response": {}}))
            await self.log_event(
                "openai.client.response_create",
                {"delay_seconds": self.settings.response_delay_seconds},
            )
        except asyncio.CancelledError:
            return

    async def close_twilio_websocket(self) -> None:
        try:
            await self.websocket.close(code=1000)
        except RuntimeError:
            pass

    async def log_event(self, source: str, payload: dict[str, Any]) -> None:
        path = self.directory / "realtime_events.jsonl"
        line = json.dumps(
            {
                "received_at": datetime.now(UTC).isoformat(),
                "source": source,
                "payload": payload,
            },
            sort_keys=True,
        )
        async with self.log_lock:
            with path.open("a", encoding="utf-8") as events_file:
                events_file.write(line + "\n")

    async def write_summary(self) -> None:
        ended_at = datetime.now(UTC)
        summary = {
            "run_id": self.run_id,
            "call_sid": self.call_sid,
            "stream_sid": self.stream_sid,
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - self.started_at).total_seconds(), 3),
            "close_reason": self.close_reason,
            "event_counts": self.counts,
            "twilio_media_payload_chars": self.media_payload_chars,
            "openai_audio_delta_chars": self.openai_audio_delta_chars,
        }
        (self.directory / "realtime_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        transcript = "\n".join(
            [
                "PATIENT/BOT:",
                "".join(self.assistant_transcript_parts).strip(),
                "",
                "PGAI_AGENT_TRANSCRIPTION_DELTAS:",
                "".join(self.input_transcript_parts).strip(),
                "",
            ]
        )
        (self.directory / "realtime_transcript.txt").write_text(transcript, encoding="utf-8")
