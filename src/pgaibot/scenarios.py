from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ScenarioError(ValueError):
    """Raised when a scenario file is missing or invalid."""


@dataclass(frozen=True)
class Persona:
    name: str
    dob: str | None = None
    phone: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    id: str
    persona: Persona
    goal: str
    constraints: list[str]
    success_criteria: list[str]
    bug_checks: list[str]
    opening_style: str = "Wait for the agent to finish greeting you, then state your goal."

    @classmethod
    def from_path(cls, path: Path) -> Scenario:
        if not path.exists():
            raise ScenarioError(f"Scenario file does not exist: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ScenarioError(f"Scenario file must contain a mapping: {path}")

        persona_raw = raw.get("persona")
        if not isinstance(persona_raw, dict):
            raise ScenarioError("Scenario must include persona mapping.")

        required = ["id", "goal"]
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise ScenarioError("Scenario is missing required fields: " + ", ".join(missing))
        if not persona_raw.get("name"):
            raise ScenarioError("Scenario persona is missing required field: name")

        extras = {
            key: value for key, value in persona_raw.items() if key not in {"name", "dob", "phone"}
        }
        return cls(
            id=str(raw["id"]),
            persona=Persona(
                name=str(persona_raw["name"]),
                dob=str(persona_raw["dob"]) if persona_raw.get("dob") is not None else None,
                phone=str(persona_raw["phone"]) if persona_raw.get("phone") is not None else None,
                extras=extras,
            ),
            goal=str(raw["goal"]),
            constraints=string_list(raw.get("constraints", []), "constraints"),
            success_criteria=string_list(raw.get("success_criteria", []), "success_criteria"),
            bug_checks=string_list(raw.get("bug_checks", []), "bug_checks"),
            opening_style=str(
                raw.get(
                    "opening_style",
                    "Wait for the agent to finish greeting you, then state your goal.",
                )
            ),
        )

    def to_metadata(self, source_path: Path | None = None) -> dict[str, Any]:
        metadata = {
            "id": self.id,
            "persona": {
                "name": self.persona.name,
                "dob": self.persona.dob,
                "phone": self.persona.phone,
                **self.persona.extras,
            },
            "goal": self.goal,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "bug_checks": self.bug_checks,
            "opening_style": self.opening_style,
        }
        if source_path is not None:
            metadata["source_path"] = str(source_path)
        return metadata


def string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ScenarioError(f"Scenario field {field_name} must be a list of strings.")
    return value
