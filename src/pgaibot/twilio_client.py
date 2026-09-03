from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from twilio.rest import Client

from pgaibot.config import Settings


@dataclass(frozen=True)
class OutboundCallPlan:
    run_id: str
    to: str
    from_: str
    twiml_url: str
    status_callback_url: str
    recording_enabled: bool

    def as_metadata(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "to": self.to,
            "from": self.from_,
            "twiml_url": self.twiml_url,
            "status_callback_url": self.status_callback_url,
            "recording_enabled": self.recording_enabled,
        }


def build_outbound_call_plan(settings: Settings, run_id: str) -> OutboundCallPlan:
    settings.require_call_runtime()
    assert settings.twilio_phone_number is not None

    return OutboundCallPlan(
        run_id=run_id,
        to=settings.target_phone_number,
        from_=settings.twilio_phone_number,
        twiml_url=settings.public_url(f"/twiml/{run_id}"),
        status_callback_url=settings.public_url(f"/twilio/status/{run_id}"),
        recording_enabled=True,
    )


def build_stream_call_plan(settings: Settings, run_id: str) -> OutboundCallPlan:
    settings.require_call_runtime()
    assert settings.twilio_phone_number is not None

    return OutboundCallPlan(
        run_id=run_id,
        to=settings.target_phone_number,
        from_=settings.twilio_phone_number,
        twiml_url=settings.public_url(f"/twiml/{run_id}?mode=stream"),
        status_callback_url=settings.public_url(f"/twilio/status/{run_id}"),
        recording_enabled=True,
    )


def build_realtime_call_plan(settings: Settings, run_id: str) -> OutboundCallPlan:
    settings.require_realtime_runtime()
    assert settings.twilio_phone_number is not None

    return OutboundCallPlan(
        run_id=run_id,
        to=settings.target_phone_number,
        from_=settings.twilio_phone_number,
        twiml_url=settings.public_url(f"/twiml/{run_id}?mode=realtime"),
        status_callback_url=settings.public_url(f"/twilio/status/{run_id}"),
        recording_enabled=True,
    )


def build_scenario_call_plan(settings: Settings, run_id: str) -> OutboundCallPlan:
    return build_realtime_call_plan(settings, run_id)


def create_outbound_call(settings: Settings, plan: OutboundCallPlan) -> dict[str, Any]:
    assert settings.twilio_account_sid is not None
    assert settings.twilio_auth_token is not None

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    call = client.calls.create(
        to=plan.to,
        from_=plan.from_,
        url=plan.twiml_url,
        method="POST",
        record=plan.recording_enabled,
        recording_channels="dual",
        status_callback=plan.status_callback_url,
        status_callback_method="POST",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
    )

    return {
        "call_sid": call.sid,
        "status": call.status,
        "created_at": datetime.now(UTC).isoformat(),
        **plan.as_metadata(),
    }
