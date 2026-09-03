from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency may not be installed in phase 0 smoke tests
    load_dotenv = None


ALLOWED_TARGET_PHONE_NUMBER = "+18054398008"


class ConfigError(ValueError):
    """Raised when required runtime configuration is missing or unsafe."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_phone_number: str | None
    public_base_url: str | None
    target_phone_number: str
    openai_realtime_model: str
    openai_transcribe_model: str
    openai_realtime_voice: str
    media_stream_max_seconds: int
    response_delay_seconds: float

    @classmethod
    def from_env(cls, *, dotenv_override: bool = False) -> Settings:
        if load_dotenv is not None:
            load_dotenv(override=dotenv_override)

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
            public_base_url=os.getenv("PUBLIC_BASE_URL"),
            target_phone_number=os.getenv("TARGET_PHONE_NUMBER", ALLOWED_TARGET_PHONE_NUMBER),
            openai_realtime_model=os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime"),
            openai_transcribe_model=os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe"),
            openai_realtime_voice=os.getenv("OPENAI_REALTIME_VOICE", "verse"),
            media_stream_max_seconds=int(os.getenv("MEDIA_STREAM_MAX_SECONDS", "20")),
            response_delay_seconds=float(os.getenv("RESPONSE_DELAY_SECONDS", "1.6")),
        )

    def validate_safe_target(self) -> None:
        if self.target_phone_number != ALLOWED_TARGET_PHONE_NUMBER:
            raise ConfigError(
                "Unsafe TARGET_PHONE_NUMBER. This challenge bot may only call "
                f"{ALLOWED_TARGET_PHONE_NUMBER}."
            )

    def missing_runtime_keys(self) -> list[str]:
        required = {
            "OPENAI_API_KEY": self.openai_api_key,
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "TWILIO_PHONE_NUMBER": self.twilio_phone_number,
            "PUBLIC_BASE_URL": self.public_base_url,
        }
        return [name for name, value in required.items() if not value]

    def missing_call_runtime_keys(self) -> list[str]:
        required = {
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "TWILIO_PHONE_NUMBER": self.twilio_phone_number,
            "PUBLIC_BASE_URL": self.public_base_url,
        }
        return [name for name, value in required.items() if not value]

    def require_call_runtime(self) -> None:
        self.validate_safe_target()
        missing = self.missing_call_runtime_keys()
        if missing:
            raise ConfigError("Missing runtime environment variables: " + ", ".join(missing))

    def require_realtime_runtime(self) -> None:
        self.require_call_runtime()
        if not self.openai_api_key:
            raise ConfigError("Missing runtime environment variables: OPENAI_API_KEY")

    def public_url(self, path: str) -> str:
        if not self.public_base_url:
            raise ConfigError("PUBLIC_BASE_URL is required to build webhook URLs.")

        base = self.public_base_url.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{base}{suffix}"

    def public_ws_url(self, path: str) -> str:
        url = self.public_url(path)
        if url.startswith("https://"):
            return "wss://" + url.removeprefix("https://")
        if url.startswith("http://"):
            return "ws://" + url.removeprefix("http://")
        raise ConfigError("PUBLIC_BASE_URL must start with http:// or https://.")
