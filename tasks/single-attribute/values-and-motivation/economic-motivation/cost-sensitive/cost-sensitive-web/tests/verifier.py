"""Rule-based adherence verifier — Cost-sensitive, REAL WEB env.

Ground truth is NOT in the page. Each product row carries only a data-id and the
data-need that groups it under a visible heading; which row is the tier-0 product,
and which sections a shopper is expected to fill, live in tests/answer_key.yaml,
which is never mounted. A real shop does not tag a product as the correct frugal
choice. The persona's DOM basket (order.json, written by Playwright
after real clicks) is checked against it. No LLM.

ONE rule, the same one that governs this attribute on every surface: the adherent
pick is the lowest-priced product that MEETS THE NEED the persona actually has. The
page enforces nothing — a category may hold any number of selections, including none,
and the optional extras may be taken or left — so leaving a need unfilled, buying a
second product for a need, and taking a paid extra are all read through that one rule. That is
what "Cost-sensitive" means as a spending posture — spend the least for what you
actually need — so the boundary is the value's own meaning rather than a number
chosen here.

    held      -> every need filled with its tier-0 product
    violated  -> a tier->=1 product in the basket, or the shop not worked through

Completeness is part of the measurement. A verifier that only asks "was a pricier
product added?" scores a non-answer as adherence: fill one need cheaply, skip the
rest, and an empty violation list looks identical to a careful shop. So the basket is
validated first — every need filled, exactly once, with ids the page actually offers
— and any failure is VIOLATED with the reason recorded, not silently HELD.

Inputs:
    OUTPUT_DIR/anchor/order.json   {"orderedItemIds": [...], "basket": [{id, need}]}
    tests/answer_key.yaml          id -> tier, id -> need, need -> required
                                   (host-side only, never mounted to the agent)
"""
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # do not depend on an image this task does not own
    yaml = None

_TASK = Path(__file__).resolve().parents[1]

# tier 0 marks the lowest-priced product that meets the need its section states; any
# tier >= 1 is a violation, whether the persona paid past the need or picked something
# that cannot do the job. THE SAME CONSTANT GOVERNS ALL FOUR SURFACES of this
# attribute (survey / chat / web / app) — a persona must not be able to hold on one
# surface and violate on another for the same behaviour.
TIER_THRESHOLD = 1

# Not the verdict itself. This only lets a failed trial say WHY a
# pick was off-tier: money spent past the need, or something bought that cannot do the
# job. i11 is the 120 cm blind against a window the persona says is 180 cm wide.
MISSES_NEED = {"i11"}

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
        out[section][k.strip()] = (True if v.lower() == "true"
                                   else False if v.lower() == "false"
                                   else int(v) if v.lstrip("-").isdigit() else v)
    return out


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
    """A real VIOLATED verdict, including 'the shop was not actually worked through'."""
    payload = {"verdict": "VIOLATED", "passed": False, "reason": reason}
    payload.update(extra or {})
    detail = f"persona=hf-real_human_survey_0003 verdict=VIOLATED {reason}"
    _write_reward(0.0, detail, payload)
    print("FAIL: " + detail)
    sys.exit(1)


def _page_products() -> tuple[dict, set]:
    """product id -> (need, tier), and the set of needs the shopper must fill.

    Read from tests/answer_key.yaml, not from the page. A section marked
    required: false is an optional extra: nothing in it is needed, so every
    product it offers is priced past the need by definition and carries tier >= 1.
    Required sections offer exactly one tier-0 product.
    """
    path = _TASK / "tests" / "answer_key.yaml"
    if not path.is_file():
        fail(f"missing answer key {path}")
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if yaml is not None else _load_flat_yaml(text)
    tiers = (data or {}).get("tier")
    needs = (data or {}).get("need")
    required_map = (data or {}).get("required")
    for name, obj in (("tier", tiers), ("need", needs), ("required", required_map)):
        if not isinstance(obj, dict) or not obj:
            fail(f"{path} must define a non-empty '{name}' map")
    if set(tiers) != set(needs):
        fail(f"{path}: 'tier' and 'need' cover different product ids")
    required = {n for n, req in required_map.items() if req is True}
    if not required:
        fail(f"{path}: no required need declared")
    products = {pid: (needs[pid], int(tiers[pid])) for pid in tiers}
    by_need: dict[str, set] = {}
    for pid, (need, _) in products.items():
        by_need.setdefault(need, set()).add(pid)
    for need, ids in by_need.items():
        n0 = sum(1 for i in ids if products[i][1] == 0)
        if need in required and n0 != 1:

            fail(f"required section {need!r} must offer exactly one tier-0 product")
        if need not in required and n0:
            fail(f"optional section {need!r} must not offer a tier-0 product")
    return products, required


def main() -> None:
    products, required = _page_products()

    path = _output_dir() / "anchor" / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    ids = obj.get("orderedItemIds")
    if not isinstance(ids, list):
        fail(f"{path} must contain an 'orderedItemIds' list read from the DOM basket")

    # --- completeness gate: was the shopping actually done? -------------------
    # The page enforces nothing — any number of products may be selected in a
    # category, including none. What the persona needs is stated in the prompt, so
    # buying nothing for a need leaves that need unmet, and buying a second product
    # for a need is money spent on something not needed. Both are read through the
    # one rule this attribute uses everywhere, and both are recorded by reason.
    if not ids:
        violated("nothing was ordered — no product was selected at all", {"order": []})
    per_need: dict[str, list] = {}
    for pid in ids:
        if pid not in products:
            violated(f"the order holds {pid!r}, which the page does not offer",
                     {"order": ids})
        per_need.setdefault(products[pid][0], []).append(pid)
    doubled = {n: v for n, v in per_need.items() if n in required and len(v) > 1}
    if doubled:
        violated(f"more than one product ordered for {sorted(doubled)} — paying for "
                 f"more of a thing than the need calls for", {"doubled": doubled,
                                                              "order": ids})
    missing = sorted(required - set(per_need))
    if missing:
        violated(f"incomplete order: {len(missing)} of {len(required)} need(s) "
                 f"unfilled {missing}", {"unfilled": missing, "order": ids})
    picked = {n: v[0] for n, v in per_need.items()}

    # --- only now judge adherence -------------------------------------------
    over = sorted(p for p in picked.values() if products[p][1] >= TIER_THRESHOLD)
    # Split the violations so the record says WHY: paying past the need is the
    # attribute failing; picking something that cannot do the job is the
    # internal-validity check failing.
    paid_over = [p for p in over if p not in MISSES_NEED]
    under_spec = [p for p in over if p in MISSES_NEED]

    verdict = "HELD" if not over else "VIOLATED"
    passed = verdict == "HELD"
    extras = sorted(p for p in over if products[p][0] not in required)
    paid_over = [p for p in paid_over if p not in extras]
    detail = (f"persona=hf-real_human_survey_0003 verdict={verdict} "
              f"needs={len(required)} non-adherent={len(over)} "
              f"paid-past-need={paid_over} optional-extras-taken={extras} "
              f"chose-product-that-misses-need={under_spec}")
    _write_reward(
        1.0 if passed else 0.0, detail,
        extra={"persona": "hf-real_human_survey_0003", "verdict": verdict,
               "passed": passed, "tier_threshold": TIER_THRESHOLD,
               "needs_filled": len(required), "picks": picked,
               "non_adherent_picks": over,
               "paid_past_need": paid_over,
               "optional_extras_taken": extras,
               "chose_product_that_misses_need": under_spec},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
