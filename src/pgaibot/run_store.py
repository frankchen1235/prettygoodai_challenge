from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pgaibot.artifacts import call_dir
from pgaibot.prompts import build_patient_prompt, phase3_patient_prompt
from pgaibot.scenarios import Scenario


def write_run_context(
    run_id: str,
    *,
    prompt: str,
    scenario_metadata: dict[str, Any] | None,
) -> Path:
    directory = call_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "run_context.json"
    payload = {
        "run_id": run_id,
        "prompt": prompt,
        "scenario": scenario_metadata,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_scenario_context(run_id: str, scenario: Scenario, source_path: Path) -> Path:
    return write_run_context(
        run_id,
        prompt=build_patient_prompt(scenario),
        scenario_metadata=scenario.to_metadata(source_path),
    )


def read_prompt_for_run(run_id: str) -> str:
    path = call_dir(run_id) / "run_context.json"
    if not path.exists():
        return phase3_patient_prompt()

    payload = json.loads(path.read_text(encoding="utf-8"))
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return phase3_patient_prompt()
    return prompt
