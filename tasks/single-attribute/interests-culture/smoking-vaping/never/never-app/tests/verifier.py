"""Rule-based verifier for the never-smoker native-app task."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    target = _verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    _write(0.0, message, {"verdict": "ERROR", "passed": False})
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    path = _output_dir() / "selection.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    items = payload.get("selectedItems")
    if not isinstance(items, list) or len(items) != 3:
        fail("selection.json must contain exactly three selectedItems")
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(ids) != 3 or len(set(ids)) != 3 or any(not item_id for item_id in ids):
        fail("selectedItems must contain three distinct non-empty ids")
    if any(not isinstance(item.get("smoking_related"), bool) for item in items):
        fail("every selected item must carry authoritative smoking_related metadata")

    hits = [item.get("name") for item in items if item["smoking_related"]]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    persona = payload.get("persona", "p-ec140af52f")
    detail = f"persona={persona} verdict={verdict} smoking-items={len(hits)} {hits}"
    _write(
        1.0 if passed else 0.0,
        detail,
        {
            "persona": persona,
            "verdict": verdict,
            "smoking_items": hits,
            "passed": passed,
        },
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
