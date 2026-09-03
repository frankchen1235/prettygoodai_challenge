import pytest

from pgaibot.config import ConfigError, Settings
from pgaibot.twilio_client import (
    build_outbound_call_plan,
    build_realtime_call_plan,
    build_scenario_call_plan,
    build_stream_call_plan,
)


def test_build_call_plan_uses_public_twiml_url() -> None:
    settings = Settings(
        openai_api_key="sk-test",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_phone_number="+15550000000",
        public_base_url="https://example.ngrok-free.app/",
        target_phone_number="+18054398008",
        openai_realtime_model="gpt-realtime",
        openai_transcribe_model="gpt-4o-transcribe",
        openai_realtime_voice="verse",
        media_stream_max_seconds=20,
        response_delay_seconds=1.6,
    )

    plan = build_outbound_call_plan(settings, "spike-test")

    assert plan.to == "+18054398008"
    assert plan.from_ == "+15550000000"
    assert plan.twiml_url == "https://example.ngrok-free.app/twiml/spike-test"
    assert plan.status_callback_url == "https://example.ngrok-free.app/twilio/status/spike-test"
    assert plan.recording_enabled is True


def test_build_call_plan_rejects_unsafe_target() -> None:
    settings = Settings(
        openai_api_key="sk-test",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_phone_number="+15550000000",
        public_base_url="https://example.ngrok-free.app",
        target_phone_number="+15551234567",
        openai_realtime_model="gpt-realtime",
        openai_transcribe_model="gpt-4o-transcribe",
        openai_realtime_voice="verse",
        media_stream_max_seconds=20,
        response_delay_seconds=1.6,
    )

    with pytest.raises(ConfigError):
        build_outbound_call_plan(settings, "spike-test")


def test_build_stream_call_plan_uses_stream_mode_twiml() -> None:
    settings = Settings(
        openai_api_key=None,
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_phone_number="+15550000000",
        public_base_url="https://example.ngrok-free.app",
        target_phone_number="+18054398008",
        openai_realtime_model="gpt-realtime",
        openai_transcribe_model="gpt-4o-transcribe",
        openai_realtime_voice="verse",
        media_stream_max_seconds=20,
        response_delay_seconds=1.6,
    )

    plan = build_stream_call_plan(settings, "stream-test")

    assert plan.twiml_url == "https://example.ngrok-free.app/twiml/stream-test?mode=stream"


def test_build_realtime_call_plan_uses_realtime_mode_twiml() -> None:
    settings = Settings(
        openai_api_key="sk-test",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_phone_number="+15550000000",
        public_base_url="https://example.ngrok-free.app",
        target_phone_number="+18054398008",
        openai_realtime_model="gpt-realtime",
        openai_transcribe_model="gpt-4o-transcribe",
        openai_realtime_voice="verse",
        media_stream_max_seconds=20,
        response_delay_seconds=1.6,
    )

    plan = build_realtime_call_plan(settings, "realtime-test")

    assert plan.twiml_url == "https://example.ngrok-free.app/twiml/realtime-test?mode=realtime"


def test_build_scenario_call_plan_uses_realtime_mode_twiml() -> None:
    settings = Settings(
        openai_api_key="sk-test",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
        twilio_phone_number="+15550000000",
        public_base_url="https://example.ngrok-free.app",
        target_phone_number="+18054398008",
        openai_realtime_model="gpt-realtime",
        openai_transcribe_model="gpt-4o-transcribe",
        openai_realtime_voice="verse",
        media_stream_max_seconds=20,
        response_delay_seconds=1.6,
    )

    plan = build_scenario_call_plan(settings, "scenario-test")

    assert plan.twiml_url == "https://example.ngrok-free.app/twiml/scenario-test?mode=realtime"
