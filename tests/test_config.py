import pytest

from pgaibot.config import ALLOWED_TARGET_PHONE_NUMBER, ConfigError, Settings


def test_default_target_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TARGET_PHONE_NUMBER", raising=False)

    settings = Settings.from_env()

    assert settings.target_phone_number == ALLOWED_TARGET_PHONE_NUMBER
    settings.validate_safe_target()


def test_rejects_non_assessment_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_PHONE_NUMBER", "+15551234567")

    settings = Settings.from_env()

    with pytest.raises(ConfigError):
        settings.validate_safe_target()


def test_missing_runtime_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENAI_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "PUBLIC_BASE_URL",
    ):
        monkeypatch.setenv(name, "")

    settings = Settings.from_env()

    assert set(settings.missing_runtime_keys()) == {
        "OPENAI_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "PUBLIC_BASE_URL",
    }


def test_call_runtime_does_not_require_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550000000")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok-free.app")

    settings = Settings.from_env()

    assert settings.missing_call_runtime_keys() == []
    settings.require_call_runtime()
