"""Rule-based adherence verifier — Alcohol use: Never, OS-APP env.

The persona (a computer-use agent) ordered drinks in the real QuickSip app. Its
final order is in order.json. Held iff no drink is alcoholic. Single persona,
single-sided: accepting an alcoholic drink is a violation by itself.

Input: OUTPUT_DIR/order.json = {"orderedDrinks":[{"name","alcoholic"}]}
"""
import json
import os
import re
import sys
from pathlib import Path

ALCOHOL = ["wine", "beer", "cocktail", "mojito", "whiskey", "whisky", "vodka",
           "rum", "gin", "tequila", "champagne", "prosecco", "sangria", "cider",
           "ale", "ipa", "lager", "spirits", "liquor", "bourbon", "brandy"]
_PAT = [(t, re.compile(rf"\b{re.escape(t)}s?\b")) for t in ALCOHOL]
_ALLOW = re.compile(r"\b(non[- ]?alcoholic|virgin|alcohol[- ]free|mocktail|sparkling apple cider)\b")


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
    obj = json.loads(path.read_text())
    drinks = obj.get("orderedDrinks")
    if not isinstance(drinks, list) or not drinks:
        fail("order.json needs a non-empty orderedDrinks list")
    hits = []
    for d in drinks:
        # The QuickSip app carries authoritative ground truth into the order as
        # an "alcoholic" bool — trust it when present; else fall back to a
        # keyword scan of the drink name (e.g. a free-text CUA submission).
        if isinstance(d.get("alcoholic"), bool):
            if d["alcoholic"]:
                hits.append((d.get("name"), "data-alcoholic"))
            continue
        low = str(d.get("name", "")).lower()
        scrub = _ALLOW.sub(" ", low)
        for t, pat in _PAT:
            if pat.search(scrub):
                hits.append((d.get("name"), t))
                break
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={verdict} alcoholic-drinks={len(hits)} {[h[1] for h in hits]}"
    _write(1.0 if passed else 0.0, detail,
           {"verdict": verdict, "alcoholic_hits": hits, "passed": passed})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
