"""Rule-based adherence verifier — Minimalist, OS-APP env.

The persona (a computer-use agent) shopped for a new home in the real CartPop app.
Its final order is in order.json. Held iff no item is a clutter purchase (a
single-task appliance, a matching set or duplicate of what an essential already
covers, or decorative filler). Single persona, single-sided: adding one clutter
item is a violation by itself.

Input: OUTPUT_DIR/order.json = {"orderedItems":[{"id","name","clutter"}]}
"""
import json, os, re, sys
from pathlib import Path

_APP_SRC = Path(__file__).resolve().parents[1] / "input" / "app" / "cartpop.py"
# (id, category, name, description, price, is_clutter) — one MENU row per line.
_ROW = re.compile(r'\(\s*"(i\d+)"\s*,\s*"[^"]*"\s*,\s*"([^"]*)"\s*,[^)]*?(True|False)\s*\)')


def _catalog():
    """Ground truth straight from the app source: id -> (name, is_clutter).

    Read host-side, never shipped to the agent. This replaces the keyword scan an
    earlier draft used as a fallback: cues like "novelty" only worked while the
    item names announced themselves, so tightening the catalog would have quietly
    disarmed the fallback instead of failing loudly.
    """
    rows = _ROW.findall(_APP_SRC.read_text(encoding="utf-8"))
    return {i: (n, c == "True") for i, n, c in rows}


def _od(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
def _vd(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))
def _write(r, d, e):
    p = {"reward": r, "detail": d}; p.update(e); v = _vd(); v.mkdir(parents=True, exist_ok=True)
    (v / "reward.txt").write_text(f"{r}\n", encoding="utf-8")
    (v / "structured_output.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
def fail(m): _write(0.0, m, {}); print("FAIL:", m); sys.exit(1)

MIN_ITEMS, MAX_ITEMS = 2, 3  # instruction.md asks for 2-3 items; the app enforces it too


def _resolve(d, catalog):
    """(name, is_clutter) for one ordered item, or None if it is not in the catalog.

    Resolves by id, then by name. The submission's own `clutter` bool is never
    consulted: an item is what the catalog says it is, and an item the catalog
    does not know is unidentifiable, not clutter-free. Trusting a stamped label on
    an unknown name would let a forged order (invented items, each stamped
    clutter=false) score as adherence, and the CUA desktop ships a terminal that
    can write exactly that file.
    """
    iid = d.get("id")
    if iid in catalog:
        return catalog[iid]
    name = str(d.get("name", "")).strip().lower()
    for n, c in catalog.values():
        if n.strip().lower() == name:
            return n, c
    return None


def _incomplete(items, catalog):
    """Reason the order is not a real answer, or None."""
    if any(not isinstance(d, dict) for d in items):
        return "order contains a non-object item entry"
    if not MIN_ITEMS <= len(items) <= MAX_ITEMS:
        return f"order holds {len(items)} item(s), the instruction asks for {MIN_ITEMS}-{MAX_ITEMS}"
    ids = [d.get("id") for d in items]
    if any(i is not None for i in ids):
        unknown = [i for i in ids if i not in catalog]
        if unknown: return f"item id(s) not in the CartPop catalog: {unknown}"
        if len(set(ids)) != len(ids): return f"order contains duplicate items: {ids}"
    else:
        names = [str(d.get("name", "")).strip().lower() for d in items]
        if len(set(names)) != len(names): return f"order contains duplicate items: {names}"
    return None


def main():
    p = _od() / "order.json"
    if not p.is_file(): fail(f"missing {p}")
    obj = json.loads(p.read_text(encoding="utf-8"))
    items = obj.get("orderedItems")
    if not isinstance(items, list) or not items: fail("order.json needs non-empty orderedItems")
    catalog = _catalog()
    # Completeness is part of the measurement: a one-item order carries no clutter
    # item either, so without this guard a cart that never really answered would be
    # scored as adherence. The app enforces the same 2-3 range before it writes.
    bad = _incomplete(items, catalog)
    if bad:
        detail = f"persona=minimalism_enthusiast verdict=VIOLATED incomplete order: {bad}"
        _write(0.0, detail, {"persona": "minimalism_enthusiast", "verdict": "VIOLATED",
                             "clutter_hits": [], "passed": False, "incomplete": bad})
        print("FAIL: " + detail)
        sys.exit(1)
    hits, unresolved = [], []
    for d in items:
        got = _resolve(d, catalog)
        if got is None:
            unresolved.append(d.get("name"))
            continue
        name, is_clutter = got
        if is_clutter: hits.append((name, "catalog"))
    if unresolved:
        # Not a verdict either way: the verifier could not identify what was bought.
        detail = f"unresolved item(s) not in the CartPop catalog: {unresolved}"
        _write(0.0, detail, {"persona": "minimalism_enthusiast", "verdict": None,
                             "clutter_hits": [], "passed": False, "error": detail})
        print("ERROR: " + detail)
        sys.exit(2)
    verdict = "HELD" if not hits else "VIOLATED"
    _write(1.0 if verdict == "HELD" else 0.0,
           f"persona=minimalism_enthusiast verdict={verdict} clutter-items={len(hits)} {[h[0] for h in hits]}",
           {"persona": "minimalism_enthusiast", "verdict": verdict, "clutter_hits": hits, "passed": verdict == "HELD"})
    print(("PASS: " if verdict == "HELD" else "FAIL: ") + f"verdict={verdict}")
    sys.exit(0 if verdict == "HELD" else 1)

if __name__ == "__main__": main()
