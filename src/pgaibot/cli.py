from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pgaibot import __version__
from pgaibot.artifacts import new_run_id, write_metadata
from pgaibot.config import ALLOWED_TARGET_PHONE_NUMBER, ConfigError, Settings
from pgaibot.evaluator import discover_latest_scenario_runs, write_report
from pgaibot.run_store import write_scenario_context
from pgaibot.scenarios import Scenario, ScenarioError
from pgaibot.twilio_client import (
    build_outbound_call_plan,
    build_realtime_call_plan,
    build_scenario_call_plan,
    build_stream_call_plan,
    create_outbound_call,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pgaibot",
        description="Pretty Good AI voice bot runner",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="Check local configuration without making calls")
    subparsers.add_parser("guard-check", help="Verify the target-number safety guard")

    serve = subparsers.add_parser("serve", help="Run the local FastAPI server")
    serve.add_argument("--host", default="0.0.0.0", help="Host to bind")
    serve.add_argument("--port", default=8000, type=int, help="Port to bind")
    serve.add_argument("--reload", action="store_true", help="Enable uvicorn reload")

    call_spike = subparsers.add_parser("call-spike", help="Create a phase-1 Twilio call")
    call_spike.add_argument("--run-id", help="Optional stable run id for this call")
    call_spike.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and save call metadata without calling Twilio",
    )

    stream_spike = subparsers.add_parser("stream-spike", help="Create a phase-2 media stream call")
    stream_spike.add_argument("--run-id", help="Optional stable run id for this call")
    stream_spike.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and save stream call metadata without calling Twilio",
    )

    realtime_spike = subparsers.add_parser(
        "realtime-spike", help="Create a phase-3 OpenAI Realtime call"
    )
    realtime_spike.add_argument("--run-id", help="Optional stable run id for this call")
    realtime_spike.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and save realtime call metadata without calling Twilio",
    )

    run = subparsers.add_parser("run", help="Run a Realtime call from a scenario YAML file")
    run.add_argument("--scenario", required=True, help="Path to scenario YAML")
    run.add_argument("--run-id", help="Optional stable run id for this call")
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and save scenario call metadata without calling Twilio",
    )

    report = subparsers.add_parser("report", help="Evaluate scenario call artifacts")
    report.add_argument(
        "runs",
        nargs="*",
        help="Optional run directories or run ids. Defaults to latest run for each scenario.",
    )
    report.add_argument(
        "--json-output",
        default="artifacts/eval_report.json",
        help="Path for structured JSON output",
    )
    report.add_argument(
        "--markdown-output",
        default="BUG_REPORT.md",
        help="Path for Markdown bug report output",
    )
    return parser


def run_doctor() -> int:
    settings = Settings.from_env()
    try:
        settings.validate_safe_target()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    missing = settings.missing_runtime_keys()
    print("Python package: pgaibot")
    print(f"Allowed target: {ALLOWED_TARGET_PHONE_NUMBER}")
    print(f"Configured target: {settings.target_phone_number}")
    print(f"Realtime model: {settings.openai_realtime_model}")
    print(f"Transcription model: {settings.openai_transcribe_model}")

    if missing:
        print("Missing runtime environment variables:")
        for name in missing:
            print(f"- {name}")
        return 1

    print("Configuration looks ready.")
    return 0


def run_guard_check() -> int:
    settings = Settings.from_env()
    try:
        settings.validate_safe_target()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"OK: target number is locked to {ALLOWED_TARGET_PHONE_NUMBER}")
    return 0


def run_serve(host: str, port: int, reload: bool) -> int:
    import uvicorn

    uvicorn.run("pgaibot.app:app", host=host, port=port, reload=reload)
    return 0


def run_call_spike(run_id: str | None, dry_run: bool) -> int:
    settings = Settings.from_env()
    try:
        plan = build_outbound_call_plan(settings, run_id or new_run_id("spike"))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return execute_call_plan(plan, settings, dry_run)


def run_stream_spike(run_id: str | None, dry_run: bool) -> int:
    settings = Settings.from_env()
    try:
        plan = build_stream_call_plan(settings, run_id or new_run_id("stream"))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return execute_call_plan(plan, settings, dry_run)


def run_realtime_spike(run_id: str | None, dry_run: bool) -> int:
    settings = Settings.from_env()
    try:
        plan = build_realtime_call_plan(settings, run_id or new_run_id("realtime"))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return execute_call_plan(plan, settings, dry_run)


def run_scenario_call(scenario_path: str, run_id: str | None, dry_run: bool) -> int:
    settings = Settings.from_env()
    path = Path(scenario_path)
    try:
        scenario = Scenario.from_path(path)
        actual_run_id = run_id or new_run_id(scenario.id)
        context_path = write_scenario_context(actual_run_id, scenario, path)
        plan = build_scenario_call_plan(settings, actual_run_id)
    except (ConfigError, ScenarioError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    extra_metadata = {
        "scenario": scenario.to_metadata(path),
        "run_context_path": str(context_path),
    }
    return execute_call_plan(plan, settings, dry_run, extra_metadata=extra_metadata)


def execute_call_plan(
    plan,
    settings: Settings,
    dry_run: bool,
    *,
    extra_metadata: dict[str, object] | None = None,
) -> int:
    if dry_run:
        metadata = {"dry_run": True, **plan.as_metadata(), **(extra_metadata or {})}
        path = write_metadata(plan.run_id, metadata)
        print(json.dumps(metadata, indent=2, sort_keys=True))
        print(f"Saved metadata to {path}")
        return 0

    metadata = {**create_outbound_call(settings, plan), **(extra_metadata or {})}
    path = write_metadata(plan.run_id, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Saved metadata to {path}")
    return 0


def run_report(runs: list[str], json_output: str, markdown_output: str) -> int:
    run_dirs = resolve_run_dirs(runs) if runs else discover_latest_scenario_runs()
    if not run_dirs:
        print("ERROR: no scenario call artifacts found.", file=sys.stderr)
        return 2

    report = write_report(run_dirs, Path(json_output), Path(markdown_output))
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"Saved JSON report to {json_output}")
    print(f"Saved Markdown report to {markdown_output}")
    return 0


def resolve_run_dirs(runs: list[str]) -> list[Path]:
    run_dirs: list[Path] = []
    for run in runs:
        path = Path(run)
        if not path.exists():
            path = Path("artifacts") / "calls" / run
        run_dirs.append(path)
    return run_dirs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor()
    if args.command == "guard-check":
        return run_guard_check()
    if args.command == "serve":
        return run_serve(args.host, args.port, args.reload)
    if args.command == "call-spike":
        return run_call_spike(args.run_id, args.dry_run)
    if args.command == "stream-spike":
        return run_stream_spike(args.run_id, args.dry_run)
    if args.command == "realtime-spike":
        return run_realtime_spike(args.run_id, args.dry_run)
    if args.command == "run":
        return run_scenario_call(args.scenario, args.run_id, args.dry_run)
    if args.command == "report":
        return run_report(args.runs, args.json_output, args.markdown_output)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
