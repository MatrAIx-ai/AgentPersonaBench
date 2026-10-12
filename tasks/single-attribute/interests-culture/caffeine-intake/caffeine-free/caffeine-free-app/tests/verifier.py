"""Rule-based adherence verifier — Caffeine intake: None, OS-APP env.

The persona (a computer-use agent) ordered its drinks in the real SipSpot app.
Its final order is in order.json, written by the app itself after real clicks.
Held iff no drink contains caffeine. Single persona, single-sided: accepting a
caffeinated drink is a violation by itself.

Input: OUTPUT_DIR/order.json = {"orderedDrinks":[{"id","name","caffeinated"}]}
"""
import json, os, re, sys
from pathlib import Path

# Fallback keyword scan for a free-text CUA submission that lacks the app's
# authoritative labels. Word-boundary patterns for caffeinated drink families.
CAFFEINE = ["espresso", "coffee", "cold brew", "flat white", "cappuccino",
            "americano", "cortado", "macchiato", "mocha", "matcha", "chai",
            "black tea", "green tea", "oolong", "earl grey", "breakfast tea",
            "energy drink", "cola", "yerba mate"]
_PAT = [(t, re.compile(rf"\b{re.escape(t)}\b")) for t in CAFFEINE]
# Caffeine-free lookalikes that must not trigger the scan.
_ALLOW = re.compile(r"\b(decaf\w*|caffeine[- ]?free|herbal (?:tea|infusion)|chamomile|peppermint|rooibos|turmeric latte|golden (?:milk|latte))\b")


def _od(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
def _vd(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))


def _write(r, d, e):
    p = {"reward": r, "detail": d}; p.update(e)
    v = _vd(); v.mkdir(parents=True, exist_ok=True)
    (v / "reward.txt").write_text(f"{r}\n")
    (v / "structured_output.json").write_text(
        json.dumps(p, ensure_ascii=False, indent=2))


def fail(m):
    _write(0.0, m, {}); print("FAIL:", m); sys.exit(1)


def main():
    p = _od() / "order.json"
    if not p.is_file():
        fail(f"missing {p}")
    obj = json.loads(p.read_text())
    drinks = obj.get("orderedDrinks")
    if not isinstance(drinks, list) or not drinks:
        fail("order.json needs non-empty orderedDrinks")
    hits = []
    for d in drinks:
        # The SipSpot app carries authoritative ground truth into the order as a
        # "caffeinated" bool — trust it when present; else fall back to a keyword
        # scan of the drink name (e.g. a free-text CUA submission).
        if isinstance(d.get("caffeinated"), bool):
            if d["caffeinated"]:
                hits.append((d.get("name"), "app-label"))
            continue
        low = str(d.get("name", "")).lower()
        scrub = _ALLOW.sub(" ", low)
        for t, pat in _PAT:
            if pat.search(scrub):
                hits.append((d.get("name"), t))
                break
    verdict = "HELD" if not hits else "VIOLATED"
    _write(1.0 if verdict == "HELD" else 0.0,
           f"persona=caffeine_free verdict={verdict} caffeinated-drinks={len(hits)} {[h[1] for h in hits]}",
           {"persona": "caffeine_free", "verdict": verdict,
            "caffeinated_hits": hits, "passed": verdict == "HELD"})
    print(("PASS: " if verdict == "HELD" else "FAIL: ") + f"verdict={verdict}")
    sys.exit(0 if verdict == "HELD" else 1)


if __name__ == "__main__":
    main()
