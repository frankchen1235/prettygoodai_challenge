from __future__ import annotations

from twilio.twiml.voice_response import VoiceResponse


def connectivity_twiml(run_id: str) -> str:
    response = VoiceResponse()
    response.say(
        "Hello. This is a short automated connectivity test for the voice bot.",
        voice="alice",
    )
    response.pause(length=2)
    response.say(f"The run identifier is {run_id}. Goodbye.", voice="alice")
    response.hangup()
    return str(response)


def media_stream_twiml(run_id: str, stream_url: str) -> str:
    response = VoiceResponse()
    connect = response.connect()
    connect.stream(name=run_id, url=stream_url)
    response.hangup()
    return str(response)
