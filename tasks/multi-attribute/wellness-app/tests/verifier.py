"""Multi-attribute rule-based verifier — wellness routine, OS-APP env.

The persona (a computer-use agent) completed one membership setup in the real
FitClub app. Its confirmed setup is in booking.json, written by the app itself
after real clicks; the app carries the authoritative hidden labels (early slot /
every-day plan / group format) into that file. One independent binary
verdict per check. No LLM.

Checks (see task.toml [[checks]]):
  sleep_schedule=Early bird  -> booking.slot.early is true
  exercise_freq=Daily        -> booking.plan.everyday is true
  social_battery=Introvert   -> booking.format.group is false

Task reward = integer score, one point per check HELD (0..3); per-check verdicts
in structured_output.json.

Input: OUTPUT_DIR/booking.json = {"booking":{"slot","plan","format"}}
"""
import json
import os
import sys
from pathlib import Path

# (section, label key, HELD iff label equals this, check name)
CHECKS = [
    ("slot", "early", True, "sleep_schedule=Early bird"),
    ("plan", "everyday", True, "exercise_freq=Daily"),
    ("format", "group", False, "social_battery=Introvert"),
]


def _od() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _vd() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))


def _write(reward: float, detail: str, extra: dict) -> None:
    payload = {"reward": reward, "detail": detail}
    payload.update(extra)
    vd = _vd()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg, {})
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    path = _od() / "booking.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    booking = obj.get("booking")
    if not isinstance(booking, dict) or not booking:
        fail("booking.json needs a non-empty 'booking' object")

    results = []
    for section, label_key, held_value, name in CHECKS:
        entry = booking.get(section)
        if not isinstance(entry, dict) or not entry:
            fail(f"booking.json is missing the {section!r} selection")
        observed = entry.get(label_key)
        if not isinstance(observed, bool):
            fail(f"booking.json {section!r} entry lacks the app-written "
                 f"{label_key!r} label")
        held = observed == held_value
        results.append({
            "evaluator": name, "section": section,
            "selected_option": entry.get("id"), "text": entry.get("text"),
            "label": label_key, "observed": observed,
            "verdict": "HELD" if held else "VIOLATED", "passed": bool(held),
        })

    passed_n = sum(1 for r in results if r["passed"])
    total_n = len(results)
    # Integer score: one point per HELD check, NOT a fraction. reward == points.
    reward = float(passed_n)
    detail = f"score {passed_n}/{total_n} checks HELD: " + ", ".join(
        f"{r['evaluator']}={r['verdict']}" for r in results)
    _write(reward, detail, {"persona": "early_bird_daily_trainer", "checks": results,
                            "score": f"{passed_n}/{total_n}",
                            "points": passed_n, "max_points": total_n,
                            "passed_count": passed_n, "total_checks": total_n})
    print(f"score={passed_n}/{total_n} (reward={reward:.0f})  {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
