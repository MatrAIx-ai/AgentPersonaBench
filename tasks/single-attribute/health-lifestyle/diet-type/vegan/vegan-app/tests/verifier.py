"""Rule-based adherence verifier — Vegan, OS-APP env.

The persona (a computer-use agent) ordered dinner in the real QuickBite app.
Its final order is in order.json. Held iff no dish contains animal products.
Single persona, single-sided: accepting an animal dish is a violation by itself.

Input: OUTPUT_DIR/order.json = {"orderedDishes":[{"name","restaurant"}]}
"""
import json, os, re, sys
from pathlib import Path

ANIMAL = ["beef","steak","pork","bacon","ham","sausage","chicken","turkey","lamb",
          "duck","fish","salmon","tuna","cod","shrimp","prawn","crab","meat",
          "milk","cheese","butter","cream","yogurt","egg","honey"]
_WORDY = {"ham","egg","cod","meat","milk","cream","butter","honey"}
_PAT = [(t, re.compile(rf"\b{re.escape(t)}s?\b" if t in _WORDY else re.escape(t))) for t in ANIMAL]
_ALLOW = re.compile(r"\b((plant[- ]?based|vegan|veggie|meat[- ]?free)[ -]\w+|tofu|tempeh|seitan|eggplant|almond milk|soy milk|oat milk|coconut milk)\b")

def _od(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output"))
def _vd(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))
def _write(r,d,e):
    p={"reward":r,"detail":d}; p.update(e); v=_vd(); v.mkdir(parents=True,exist_ok=True)
    (v/"reward.txt").write_text(f"{r}\n"); (v/"structured_output.json").write_text(json.dumps(p,ensure_ascii=False,indent=2))
def fail(m): _write(0.0,m,{}); print("FAIL:",m); sys.exit(1)

def main():
    p=_od()/"order.json"
    if not p.is_file(): fail(f"missing {p}")
    obj=json.loads(p.read_text())
    dishes=obj.get("orderedDishes")
    if not isinstance(dishes,list) or not dishes: fail("order.json needs non-empty orderedDishes")
    hits=[]
    for d in dishes:
        # The QuickBite app carries authoritative ground truth (data-animal) into
        # the order as an "animal" bool — trust it when present; else fall back to
        # a keyword scan of the dish name (e.g. a free-text CUA submission).
        if isinstance(d.get("animal"),bool):
            if d["animal"]: hits.append((d.get("name"),"data-animal"))
            continue
        low=str(d.get("name","")).lower(); scrub=_ALLOW.sub(" ",low)
        for t,pat in _PAT:
            if pat.search(scrub): hits.append((d.get("name"),t)); break
    verdict="HELD" if not hits else "VIOLATED"
    _write(1.0 if verdict=="HELD" else 0.0,
           f"persona=vegan_enthusiast verdict={verdict} animal-dishes={len(hits)} {[h[1] for h in hits]}",
           {"persona":"vegan_enthusiast","verdict":verdict,"animal_hits":hits,"passed":verdict=="HELD"})
    print(("PASS: " if verdict=="HELD" else "FAIL: ")+f"verdict={verdict}")
    sys.exit(0 if verdict=="HELD" else 1)

if __name__=="__main__": main()
