import json
from pathlib import Path

from pgaibot.evaluator import evaluate_call, render_markdown_report, split_transcript, write_report


def test_split_transcript() -> None:
    patient, agent = split_transcript(
        """
PATIENT/BOT:
Hi.

PGAI_AGENT_TRANSCRIPTION_DELTAS:
Hello.
""".strip()
    )

    assert patient == "Hi."
    assert agent == "Hello."


def test_evaluate_call_notes_caller_id_identity_assumption(tmp_path: Path) -> None:
    run_dir = write_call_fixture(
        tmp_path,
        scenario_id="cancel_existing_appointment",
        persona={"name": "Priya Shah", "dob": "1991-02-17", "phone": "+15559876543"},
        goal="Cancel an appointment scheduled for Monday at 2:15 PM.",
        transcript="""
PATIENT/BOT:
Hi there. I need to cancel my physical therapy appointment on Monday at 2:15 PM.
Sure, my date of birth is February 17, 1991.

PGAI_AGENT_TRANSCRIPTION_DELTAS:
Thanks for calling. How may I help you today?
I see you're calling from the number we have on file. Was speaking with Maria?
Please provide your date of birth to locate your chart.
I'm unable to locate your record in our system, so I can't cancel the appointment right now. I'll connect you to our patient support team.
""".strip(),
    )

    evaluation = evaluate_call(run_dir, {"Maria Lopez", "Priya Shah"})

    assert evaluation.status == "pass_with_observations"
    assert (
        evaluation.issues[0].title
        == "Caller-ID based identity assumption may confuse multi-patient test calls"
    )
    assert evaluation.issues[0].severity == "Observation"
    assert evaluation.checks["agent_recognized_intent"] is True


def test_write_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    run_dir = write_call_fixture(
        tmp_path,
        scenario_id="medication_refill_request",
        persona={"name": "Robert Chen", "dob": "1964-11-05", "phone": "+15553456789"},
        goal="Request a refill for meloxicam 15 mg.",
        transcript="""
PATIENT/BOT:
Hi, I need a refill for meloxicam 15 milligrams, and I’d like it sent to CVS on Market Street.

PGAI_AGENT_TRANSCRIPTION_DELTAS:
Can you please tell me your full name and date of birth?
I'm unable to find your record in our system, so I can't process the refill right now. I'll connect you to our patient support team. Transferring you now.
Hello, you've reached the Pretty Good AI test line, goodbye.
""".strip(),
    )
    json_path = tmp_path / "eval_report.json"
    markdown_path = tmp_path / "BUG_REPORT.md"

    report = write_report([run_dir], json_path, markdown_path)

    assert report["summary"]["calls_evaluated"] == 1
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["issues_found"] == 0
    assert "medication_refill_request" in markdown_path.read_text(encoding="utf-8")


def test_render_markdown_includes_findings() -> None:
    markdown = render_markdown_report(
        {
            "summary": {"calls_evaluated": 1, "issues_found": 0, "high_or_medium_issues": 0},
            "evaluations": [
                {
                    "scenario_id": "simple_schedule_new_patient",
                    "status": "pass",
                    "run_id": "run-1",
                    "call_sid": "CA123",
                    "duration_seconds": 10.0,
                    "close_reason": "twilio_stop",
                    "checks": {"agent_recognized_intent": True},
                    "notes": [],
                    "issues": [],
                }
            ],
        }
    )

    assert "No clear bugs found" in markdown


def test_render_markdown_groups_repeated_findings() -> None:
    issue = {
        "severity": "Observation",
        "title": "Caller-ID based identity assumption may confuse multi-patient test calls",
        "details": "Shared caller ID was associated with another demo patient.",
        "expected": "The agent should ask for confirmation and allow correction.",
        "evidence": "Am I speaking with Maria?",
    }
    report = {
        "summary": {"calls_evaluated": 2, "issues_found": 2, "high_or_medium_issues": 0},
        "evaluations": [
            {
                "scenario_id": "cancel_existing_appointment",
                "status": "pass_with_observations",
                "run_id": "run-cancel",
                "call_sid": "CA123",
                "duration_seconds": 153.0,
                "close_reason": "max_seconds_reached",
                "checks": {},
                "notes": [],
                "issues": [issue],
            },
            {
                "scenario_id": "medication_refill_request",
                "status": "pass_with_observations",
                "run_id": "run-refill",
                "call_sid": "CA456",
                "duration_seconds": 153.0,
                "close_reason": "max_seconds_reached",
                "checks": {},
                "notes": [],
                "issues": [{**issue, "evidence": "Was speaking with Maria?"}],
            },
        ],
    }

    markdown = render_markdown_report(report)

    assert markdown.count("### Observation: Caller-ID based identity assumption") == 1
    assert "`cancel_existing_appointment`" in markdown
    assert "`medication_refill_request`" in markdown


def write_call_fixture(
    root: Path,
    *,
    scenario_id: str,
    persona: dict[str, str],
    goal: str,
    transcript: str,
) -> Path:
    run_dir = root / scenario_id
    run_dir.mkdir()
    context = {
        "run_id": run_dir.name,
        "prompt": "test prompt",
        "scenario": {
            "id": scenario_id,
            "persona": persona,
            "goal": goal,
            "constraints": [],
            "success_criteria": [],
            "bug_checks": [],
        },
    }
    metadata = {"run_id": run_dir.name, "call_sid": "CA123"}
    summary = {
        "run_id": run_dir.name,
        "duration_seconds": 153.0,
        "close_reason": "max_seconds_reached",
    }
    (run_dir / "run_context.json").write_text(json.dumps(context), encoding="utf-8")
    (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (run_dir / "realtime_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "realtime_transcript.txt").write_text(transcript, encoding="utf-8")
    return run_dir
