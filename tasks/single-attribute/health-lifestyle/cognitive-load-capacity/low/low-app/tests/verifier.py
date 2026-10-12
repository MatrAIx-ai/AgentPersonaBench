"""Rule-based adherence verifier — Cognitive load capacity = Low, OS-APP env.

The persona (a computer-use agent) organized a photo library in the real
PhotoKeep app. Its final action is in order.json. Held iff it used the single
Auto-Organize by Date action rather than the four-concurrent-field Custom
Organize path.

Input: OUTPUT_DIR/order.json = {"path": "auto"|"custom", ...}
"""
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
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(state, dict):
        fail(f"{path} must contain a JSON object")
    if state.get("path") not in {"auto", "custom"}:
        fail(f"order.json: invalid or missing 'path' field {state.get('path')!r}")
    verdict = "HELD" if state["path"] == "auto" else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={verdict} path={state['path']}"
    _write(1.0 if passed else 0.0, detail,
           {"verdict": verdict, "path": state["path"], "passed": passed})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
