from pathlib import Path

from pgaibot.prompts import build_patient_prompt
from pgaibot.run_store import read_prompt_for_run, write_scenario_context
from pgaibot.scenarios import Scenario

SCENARIO_PATHS = sorted(Path("scenarios").glob("*.yaml"))


def test_loads_simple_schedule_scenario() -> None:
    scenario = Scenario.from_path(Path("scenarios/01_simple_schedule.yaml"))

    assert scenario.id == "simple_schedule_new_patient"
    assert scenario.persona.name == "Maria Lopez"
    assert "lower back pain" in scenario.goal


def test_all_checked_in_scenarios_load() -> None:
    assert SCENARIO_PATHS

    scenarios = [Scenario.from_path(path) for path in SCENARIO_PATHS]

    assert {scenario.id for scenario in scenarios} == {
        "simple_schedule_new_patient",
        "reschedule_existing_appointment",
        "cancel_existing_appointment",
        "medication_refill_request",
        "office_hours_locations_insurance",
        "unclear_request_edge_case",
        "office_hours_locations_insurance_variant",
        "unclear_request_edge_case_variant",
    }
    for scenario in scenarios:
        assert scenario.goal
        assert scenario.constraints
        assert scenario.success_criteria
        assert scenario.bug_checks


def test_build_patient_prompt_contains_scenario_details() -> None:
    scenario = Scenario.from_path(Path("scenarios/01_simple_schedule.yaml"))

    prompt = build_patient_prompt(scenario)

    assert "Scenario id: simple_schedule_new_patient" in prompt
    assert "Maria Lopez" in prompt
    assert "lower back pain" in prompt
    assert "Do not dump all facts at once" in prompt


def test_run_context_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = Path("scenario.yaml")
    source.write_text(
        """
id: test_scenario
persona:
  name: Test Patient
goal: Ask about office hours.
constraints: []
success_criteria: []
bug_checks: []
""".strip(),
        encoding="utf-8",
    )
    scenario = Scenario.from_path(source)

    write_scenario_context("run-1", scenario, source)

    assert "Ask about office hours" in read_prompt_for_run("run-1")
