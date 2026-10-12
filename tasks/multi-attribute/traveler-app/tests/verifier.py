"""Multi-attribute adherence verifier — Traveler profile, OS-APP env.

The persona (a computer-use agent) built a travel plan in the real TripBuilder
app: one pick in each of three sections. The app itself wrote plan.json after
real clicks, carrying the authoritative labels for each chosen option
(`section` = the persona dimension that section probes, `flag` = true when the
option is inconsistent with this persona's value).

Per check:  HELD  iff that section was answered and its pick is unflagged.
Task reward = integer score, one point per check HELD (0..3); per-check
verdicts in structured_output.json — mirrors the codestyle convention.

Input: OUTPUT_DIR/plan.json = {"chosenOptions":[{"id","section","text","flag"}]}
"""
import json
import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # py<3.11
    tomllib = None

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


def _declared_checks() -> list:
    if tomllib is None:
        fail("tomllib unavailable (python >= 3.11 required)")
    meta = tomllib.loads((_TASK / "task.toml").read_text(encoding="utf-8"))
    return meta.get("checks", [])


def main() -> None:
    path = _output_dir() / "plan.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        chosen = json.loads(path.read_text(encoding="utf-8")).get("chosenOptions")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(chosen, list) or not chosen:
        fail(f"{path} must contain a non-empty 'chosenOptions' list")

    checks = _declared_checks()
    if not checks:
        fail("task.toml declares no [[checks]]")

    by_section: dict = {}
    for o in chosen:
        by_section.setdefault(o.get("section"), []).append(o)

    results = []
    passed_n = 0
    for c in checks:
        dim = c.get("dimension_id")
        picks = by_section.get(dim, [])
        hits = [o.get("id") for o in picks if o.get("flag")]
        # The app allows exactly one pick per section. An unanswered section
        # cannot be HELD (silence is not adherence), and more than one pick
        # means the plan was not committed to a single choice.
        held = len(picks) == 1 and not hits
        passed_n += int(held)
        entry = {
            "dimension_id": dim,
            "value": c.get("value") or c.get("anchor_value"),
            "verdict": "HELD" if held else "VIOLATED",
            "passed": bool(held),
            "picked": [o.get("id") for o in picks],
            "flagged_picks": hits,
        }
        if not picks:
            entry["incomplete"] = "section unanswered"
        elif len(picks) > 1:
            entry["incomplete"] = f"section has {len(picks)} picks, expected exactly 1"
        results.append(entry)

    total_n = len(checks)
    # Integer score: one point per HELD check (0..N), codestyle convention.
    reward = float(passed_n)
    detail = f"score {passed_n}/{total_n} checks HELD: " + ", ".join(
        f"{r['dimension_id']}={r['verdict']}" for r in results)
    _write(reward, detail, {"checks": results, "passed": passed_n == total_n})
    print(("PASS: " if passed_n == total_n else "PARTIAL/FAIL: ") + detail)
    sys.exit(0 if passed_n == total_n else 1)


if __name__ == "__main__":
    main()
