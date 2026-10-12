"""Multi-attribute rule-based verifier — Morning kit: daily walk · tracks hydration, OS-APP env.

The persona (a computer-use agent) completed one morning-kit setup in the real
KitStart app. kit.json is written by the app itself after real clicks and
carries the authoritative hidden labels. One binary verdict per check. No LLM.
Reward = integer 0..2.

Input: OUTPUT_DIR/kit.json = {"kit":{"block","widget"}}
"""
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

_TASK = Path(__file__).resolve().parents[1]


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

CHECKS = [("block", "morning_walk=Daily"), ("widget", "hydration_tracking=Daily")]


def main() -> None:
    path = _output_dir() / "kit.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    kit = obj.get("kit")
    if not isinstance(kit, dict) or not kit:
        fail("kit.json needs a non-empty 'kit' object")
    results = []
    for sec, name in CHECKS:
        entry = kit.get(sec)
        if not isinstance(entry, dict) or not isinstance(entry.get("flag"), bool):
            fail(f"kit.json {sec!r} entry lacks the app-written boolean flag")
        held = entry["flag"]
        results.append({"evaluator": name, "section": sec,
                        "selected_option": entry.get("id"), "text": entry.get("text"),
                        "verdict": "HELD" if held else "VIOLATED", "passed": held})
    passed_n = sum(1 for r in results if r["passed"])
    reward = float(passed_n)
    detail = f"score {passed_n}/2 checks HELD: " + ", ".join(
        f"{r['evaluator']}={r['verdict']}" for r in results)
    _write(reward, detail, {"persona": "morning_kit", "checks": results,
                            "score": f"{passed_n}/2", "points": passed_n, "max_points": 2,
                            "passed_count": passed_n, "total_checks": 2})
    print(f"score={passed_n}/2 (reward={reward:.0f})  {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
