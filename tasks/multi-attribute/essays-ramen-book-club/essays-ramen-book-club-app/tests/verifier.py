"""Two-check rule-based adherence verifier — Books: Essays = Like · Cuisine: Ramen = Like, OS-APP env.

The persona used the real native desktop app; the two checks are scored
independently on the same two picks and reward = checks held (0..2):
  * bookg_essays=Like: held iff every pick is on its host-keyed acceptable side.
  * cuis_ramen=Like: held iff every pick is on its host-keyed acceptable side.

Ground truth is a host-only answer key under tests/. Visible id/name pairs are
parsed independently from the app source; malformed or forged files fail closed.

Input: OUTPUT_DIR/pilot_reservations.json = {"persona":"...","reservedPilots":[{"id":"...","name":"..."}]}
"""
import ast, json, os, sys
from pathlib import Path

_TASK = Path(__file__).resolve().parents[1]
PERSONA = "hf-6283061910"
APP_SRC = _TASK / "environment" / "pilotstudio.py"
ANSWER_KEY = _TASK / "tests" / "answer_key.json"
LIST_KEY, FNAME = "reservedPilots", "pilot_reservations.json"
LABELS = ("essayaxis", "ramenaxis")
# (evaluator name, label, True if a labeled row is the ACCEPTABLE side)
CHECKS = [
    ("bookg_essays=Like", "essayaxis", True),
    ("cuis_ramen=Like", "ramenaxis", True),
]
MAX_POINTS = len(CHECKS)
MIN_ITEMS, MAX_ITEMS = 2, 2

def _od(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output"))
def _vd(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))
def _write(r,d,e):
    p={"reward":r,"detail":d}; p.update(e); v=_vd(); v.mkdir(parents=True,exist_ok=True)
    (v/"reward.txt").write_text(f"{r}\n", encoding="utf-8"); (v/"structured_output.json").write_text(json.dumps(p,ensure_ascii=False,indent=2), encoding="utf-8")
def fail(m, infra=False):
    e={"checks": [], "points": 0, "max_points": MAX_POINTS}
    if infra: e["error"]=m
    _write(0.0, m, e); print("FAIL:", m); sys.exit(1)

def _visible_catalog() -> dict[str,str]:
    try:
        tree = ast.parse(APP_SRC.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        fail(f"cannot parse app catalog from {APP_SRC}: {exc}", infra=True)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
            try:
                items = ast.literal_eval(node.value)
            except ValueError:
                continue
            if items and all(isinstance(t,tuple) and len(t)==5 and isinstance(t[0],str) for t in items):
                ids=[t[0] for t in items]
                if len(ids)!=len(set(ids)): fail("app catalog has duplicate ids",infra=True)
                return {t[0]:t[2] for t in items}
    fail(f"no visible catalog literal found in {APP_SRC}",infra=True)

def _answer_key(ids:set[str])->dict:
    try: raw=json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: fail(f"cannot load host answer key: {exc}",infra=True)
    if not isinstance(raw,dict) or set(raw)!=ids: fail("host key must exactly cover catalog ids",infra=True)
    for oid,v in raw.items():
        if not isinstance(v,dict) or set(v)!=set(LABELS) or not all(isinstance(v[k],bool) for k in v): fail(f"invalid host labels for {oid}",infra=True)
    return raw

def main():
    p=_od()/FNAME
    if not p.is_file(): fail(f"missing {p} — the agent never submitted in the app")
    if p.stat().st_size>65536: fail(f"{p} is too large")
    try:
        obj=json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{p} is not valid JSON (app-written file): {exc}", infra=True)
    if not isinstance(obj, dict):
        fail(f"{p} top-level JSON must be an object — file not app-written")
    if set(obj)!={"persona",LIST_KEY} or obj.get("persona")!=PERSONA: fail(f"{p} has invalid top-level keys or persona")
    entries=obj.get(LIST_KEY)
    if not isinstance(entries,list) or not entries: fail(f"{FNAME} needs non-empty {LIST_KEY}")
    visible=_visible_catalog(); cat=_answer_key(set(visible))
    seen={}
    for d in entries:
        if not isinstance(d, dict):
            fail(f"{FNAME} entries must be objects (got {type(d).__name__}) — file not app-written")
        if not isinstance(d.get("id"), str):
            fail(f"{FNAME} entry id must be a string — file not app-written")
        if d["id"] in seen: fail(f"duplicate entry id {d['id']!r}")
        seen[d["id"]]=d
    entries=list(seen.values())
    if not (MIN_ITEMS <= len(entries) <= MAX_ITEMS):
        fail(f"submission has {len(entries)} distinct pick(s); the task asks for exactly 2")
    picks=[]
    for d in entries:
        oid = d.get("id")
        if oid not in cat:
            fail(f"entry id {oid!r} is not in the app catalog — file not app-written")
        if set(d)!={"id","name"} or d.get("name")!=visible[oid]: fail(f"entry {oid!r} has invalid app-written shape")
        picks.append(oid)
    results=[]
    for name, label, labeled_ok in CHECKS:
        offside=[oid for oid in picks if cat[oid][label] != labeled_ok]
        held = not offside
        results.append({"evaluator": name, "label": label,
                        "verdict": "HELD" if held else "VIOLATED", "passed": held,
                        "offside_picks": offside})
    points=sum(r["passed"] for r in results)
    detail=(f"persona={PERSONA} score {points}/{MAX_POINTS} checks HELD: "
            + ", ".join(f"{r['evaluator']}={r['verdict']}" for r in results)
            + f" picks={picks} (labels derived from host-only answer key)")
    _write(float(points), detail,
           {"persona":PERSONA,"checks":results,"score":f"{points}/{MAX_POINTS}",
            "points":points,"max_points":MAX_POINTS,
            "passed_count":points,"total_checks":MAX_POINTS,"picks":picks})
    print(f"score={points}/{MAX_POINTS} (reward={points})  {detail}")
    sys.exit(0)

if __name__=="__main__": main()
