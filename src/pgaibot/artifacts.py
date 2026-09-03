from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ARTIFACTS_ROOT = Path("artifacts")
CALLS_ROOT = ARTIFACTS_ROOT / "calls"


def new_run_id(prefix: str = "call") -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{uuid4().hex[:8]}"


def call_dir(run_id: str) -> Path:
    return CALLS_ROOT / run_id


def write_metadata(run_id: str, metadata: dict[str, Any]) -> Path:
    directory = call_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "metadata.json"
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
