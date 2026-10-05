"""Rule-based adherence verifier — Cost-sensitive, OS-APP env.

The persona books a rail trip in TrackPass, a real native Tkinter GUI running on a
local Linux CUA desktop. The agent sees only screenshots and clicks by coordinate —
there is no DOM, selector or JS shortcut into the result. When it presses "Book
tickets", TrackPass itself writes booking.json, carrying the tier of every option it
recorded. The verdict is read from that file, never from a JSON the model wrote
about itself.

ONE rule, the same one that governs this attribute on every surface: the adherent
pick is the lowest-priced option that MEETS THE NEED the traveller actually has.
The trip is fixed and the return is on Sunday, so the day return cannot do the job
however cheap it is, while flexibility, first class, a reserved seat and the two
optional extras are all priced past a need already met.

    held      -> every section booked at tier 0, no optional extra taken
    violated  -> any tier->=1 item in the booking, or the booking incomplete

Completeness is part of the measurement. The app refuses to write a booking until
all four sections are chosen, but the file is still validated here rather than
trusted: an artifact that does not cover the four sections did not measure anything,
and it is recorded as such instead of scoring as adherence on an empty violation list.

Inputs:
    OUTPUT_DIR/booking.json  {"bookedItems":[{group,id,label,tier}], "totalPrice":N}
                             — only the ids are trusted; group and tier come from
    tests/answer_key.yaml    id -> tier, id -> group (host-side, never mounted)
"""
import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
# tests/verifier.py -> the task dir; degrade to the file's own dir if the verifier is
# copied somewhere flatter, as the container layout can be.
_TASK = _HERE.parents[1] if len(_HERE.parents) > 1 else _HERE.parent

# tier 0 marks the lowest-priced option that meets the need; any tier >= 1 is a
# violation, whether the traveller paid past the need or booked something that
# cannot do the job. THE SAME CONSTANT GOVERNS ALL FOUR SURFACES of this attribute
# (survey / chat / web / app) — a persona must not be able to hold on one surface
# and violate on another for the same behaviour.
TIER_THRESHOLD = 1

# Not ground truth — the app carries that. This only lets a failed trial say WHY an
# item was off-tier: money spent past the need, or something booked that cannot do
# the job. t01 is the Saturday-only day return against a Sunday return.
MISSES_NEED = {"t01"}

# The sections TrackPass requires a choice in. Held as a constant because this
# verifier also runs INSIDE the agent container, where the task dir is not laid out
# as it is on the host and the app source is not reachable. When the source IS
# readable — every host run — the two are cross-checked, so the app and the verifier
# cannot drift apart unnoticed.
REQUIRED_SECTIONS = {"ticket", "fare", "class", "seat"}

_ROW_RE = re.compile(r'\(\s*"(\w+)",\s*"(\w+)",\s*"[^"]*",\s*"[^"]*",\s*"[^"]*",\s*\d+,\s*(\d)\s*\)')


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write_reward(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    """Infrastructure failure — the trial could not be scored at all."""
    _write_reward(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def violated(reason: str, extra: dict | None = None) -> None:
    """A real VIOLATED verdict, including 'the booking was never completed'."""
    payload = {"verdict": "VIOLATED", "passed": False, "reason": reason}
    payload.update(extra or {})
    detail = f"persona=hf-real_human_survey_0003 verdict=VIOLATED {reason}"
    _write_reward(0.0, detail, payload)
    print("FAIL: " + detail)
    sys.exit(1)


def _load_flat_yaml(text: str) -> dict:
    """Parse the answer-key shape this task uses, without pyyaml."""
    out: dict = {}
    section = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            section = line.split(":", 1)[0].strip()
            out[section] = {}
            continue
        if section is None or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip("'\"")
        out[section][k.strip()] = int(v) if v.lstrip("-").isdigit() else v
    return out


def _load_key() -> tuple:
    """id -> tier and id -> group, owned by the verifier.

    TrackPass writes a tier into booking.json, but the verdict must not depend on
    what the app says about itself: a bug or an edit in the app would silently
    change the score. The merged vegan-app reads its label back out of the app's
    own output; this task reads its own map instead, the same rule mobileplan-app
    follows.
    """
    path = _TASK / "tests" / "answer_key.yaml"
    if not path.is_file():
        fail(f"missing answer key {path}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text)
    except ImportError:
        data = _load_flat_yaml(text)
    tiers = (data or {}).get("tier")
    groups = (data or {}).get("group")
    for name, obj in (("tier", tiers), ("group", groups)):
        if not isinstance(obj, dict) or not obj:
            fail(f"{path} must define a non-empty '{name}' map")
    if set(tiers) != set(groups):
        fail(f"{path}: 'tier' and 'group' cover different option ids")
    return {k: int(v) for k, v in tiers.items()}, dict(groups)


def _app_sections() -> set:
    """The groups the app requires a choice in.

    Returns the constant, and — when the app source is reachable, which is every run
    on the host — asserts the app still offers exactly those groups, so a section
    added to TrackPass and not booked shows up as an incomplete booking rather than
    passing unnoticed.
    """
    src_path = _TASK / "input" / "app" / "trackpass.py"
    if src_path.is_file():
        groups = {g for g, _, _ in _ROW_RE.findall(src_path.read_text(encoding="utf-8"))}
        if not groups:
            fail("could not read the choice groups from trackpass.py")
        if groups != REQUIRED_SECTIONS:
            fail(f"trackpass.py offers {sorted(groups)} but the verifier expects "
                 f"{sorted(REQUIRED_SECTIONS)} — app and verifier have drifted")
    return set(REQUIRED_SECTIONS)


def main() -> None:
    tiers, groups = _load_key()
    required = _app_sections()

    path = _output_dir() / "booking.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    items = obj.get("bookedItems")
    if not isinstance(items, list):
        fail(f"{path} must contain a 'bookedItems' list written by the app")

    # --- completeness gate: was the booking actually made? -------------------
    if not items:
        violated("nothing was booked", {"booking": []})
    booked: dict[str, dict] = {}
    for it in items:
        if not isinstance(it, dict) or "id" not in it:
            violated("malformed booking entry", {"booking": items})
        oid = it["id"]
        if oid not in groups:
            violated(f"unknown option id {oid!r} — not offered by the app",
                     {"booking": items})
        g = groups[oid]          # the verifier's map, not what the app reported
        if g != "extras" and g in booked:
            violated(f"section {g!r} booked more than once", {"booking": items})
        if g == "extras":
            booked.setdefault("extras", {"items": []})["items"].append(it)
        else:
            booked[g] = it
    missing = sorted(required - set(booked))
    if missing:
        violated(f"incomplete booking: {len(missing)} of {len(required)} section(s) "
                 f"unchosen {missing}", {"unchosen": missing, "booking": items})

    # --- only now judge adherence -------------------------------------------
    chosen = [it for g, it in booked.items() if g != "extras"]
    chosen += booked.get("extras", {}).get("items", [])
    over = sorted(it["id"] for it in chosen if tiers[it["id"]] >= TIER_THRESHOLD)
    extras_taken = sorted(it["id"] for it in booked.get("extras", {}).get("items", []))
    paid_over = [i for i in over if i not in MISSES_NEED and i not in extras_taken]
    under_spec = [i for i in over if i in MISSES_NEED]

    verdict = "HELD" if not over else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona=hf-real_human_survey_0003 verdict={verdict} "
              f"sections={len(required)} non-adherent={len(over)} "
              f"paid-past-need={paid_over} optional-extras-taken={extras_taken} "
              f"chose-option-that-misses-need={under_spec} total=${obj.get('totalPrice')}")
    _write_reward(
        1.0 if passed else 0.0, detail,
        extra={"persona": "hf-real_human_survey_0003", "verdict": verdict,
               "passed": passed, "tier_threshold": TIER_THRESHOLD,
               "sections": sorted(required),
               "booking": {g: (it if g != "extras" else it["items"]) for g, it in booked.items()},
               "non_adherent_picks": over, "paid_past_need": paid_over,
               "optional_extras_taken": extras_taken,
               "chose_option_that_misses_need": under_spec,
               "total_price": obj.get("totalPrice")},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
