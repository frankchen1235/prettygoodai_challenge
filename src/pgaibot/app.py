from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect

from pgaibot.artifacts import call_dir
from pgaibot.config import ConfigError, Settings
from pgaibot.realtime_bridge import RealtimeBridge
from pgaibot.twiml import connectivity_twiml, media_stream_twiml

app = FastAPI(title="Pretty Good AI Voice Bot")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/twiml/{run_id}")
@app.get("/twiml/{run_id}")
def twiml(run_id: str, mode: str = "connectivity") -> Response:
    if mode == "stream":
        try:
            settings = Settings.from_env(dotenv_override=True)
            stream_url = settings.public_ws_url(f"/ws/twilio/{run_id}")
            body = media_stream_twiml(run_id, stream_url)
        except ConfigError as exc:
            body = connectivity_twiml(f"configuration error {exc}")
    elif mode == "realtime":
        try:
            settings = Settings.from_env(dotenv_override=True)
            stream_url = settings.public_ws_url(f"/ws/twilio-realtime/{run_id}")
            body = media_stream_twiml(run_id, stream_url)
        except ConfigError as exc:
            body = connectivity_twiml(f"configuration error {exc}")
    else:
        body = connectivity_twiml(run_id)
    return Response(content=body, media_type="application/xml")


@app.post("/twilio/status/{run_id}")
async def twilio_status(run_id: str, request: Request) -> dict[str, Any]:
    form = await request.form()
    return {"run_id": run_id, "received": dict(form)}


@app.websocket("/ws/twilio/{run_id}")
async def twilio_media_stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()

    settings = Settings.from_env(dotenv_override=True)
    directory = call_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    events_path = directory / "twilio_events.jsonl"
    summary_path = directory / "stream_summary.json"

    started_at = datetime.now(UTC)
    counts: dict[str, int] = {}
    payload_bytes = 0
    stream_sid: str | None = None
    call_sid: str | None = None
    close_reason = "unknown"

    try:
        with events_path.open("a", encoding="utf-8") as events_file:
            while True:
                elapsed = (datetime.now(UTC) - started_at).total_seconds()
                if elapsed >= settings.media_stream_max_seconds:
                    close_reason = "max_seconds_reached"
                    await websocket.close(code=1000)
                    break

                try:
                    raw_message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                except TimeoutError:
                    continue

                received_at = datetime.now(UTC).isoformat()
                message = json.loads(raw_message)
                event = str(message.get("event", "unknown"))
                counts[event] = counts.get(event, 0) + 1

                stream_sid = message.get("streamSid", stream_sid)
                if event == "start":
                    start = message.get("start", {})
                    call_sid = start.get("callSid", call_sid)
                    stream_sid = start.get("streamSid", stream_sid)
                elif event == "media":
                    payload = message.get("media", {}).get("payload", "")
                    payload_bytes += len(payload)
                elif event == "stop":
                    close_reason = "twilio_stop"

                events_file.write(
                    json.dumps({"received_at": received_at, "message": message}, sort_keys=True)
                    + "\n"
                )
                events_file.flush()

                if event == "stop":
                    break
    except WebSocketDisconnect:
        close_reason = "websocket_disconnect"
    finally:
        ended_at = datetime.now(UTC)
        summary = {
            "run_id": run_id,
            "call_sid": call_sid,
            "stream_sid": stream_sid,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - started_at).total_seconds(), 3),
            "close_reason": close_reason,
            "event_counts": counts,
            "media_payload_chars": payload_bytes,
            "events_path": str(events_path),
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@app.websocket("/ws/twilio-realtime/{run_id}")
async def twilio_realtime_stream(websocket: WebSocket, run_id: str) -> None:
    settings = Settings.from_env(dotenv_override=True)
    bridge = RealtimeBridge(websocket, run_id, call_dir(run_id), settings)
    await bridge.run()
