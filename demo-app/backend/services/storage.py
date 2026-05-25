from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
PACK_ROOT = APP_DIR.parent.parent
RUNTIME_DIR = APP_DIR / "runtime"
UPLOADS_DIR = RUNTIME_DIR / "uploads"
JOBS_DIR = RUNTIME_DIR / "jobs"
REVIEWS_DIR = RUNTIME_DIR / "reviews"
GENERATED_CASES_DIR = RUNTIME_DIR / "generated_cases"


def ensure_runtime_dirs() -> None:
    for path in [UPLOADS_DIR, JOBS_DIR, REVIEWS_DIR, GENERATED_CASES_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_runtime_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_json(directory: Path) -> list[dict[str, Any]]:
    ensure_runtime_dirs()
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def clear_runtime() -> None:
    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    ensure_runtime_dirs()
