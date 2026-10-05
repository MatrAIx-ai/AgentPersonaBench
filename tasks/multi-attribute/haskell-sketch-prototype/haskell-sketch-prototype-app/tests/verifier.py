"""Strict Linux App verifier with exact app-source and host-only-key binding."""
import ast,json,os
from pathlib import Path
TESTS=Path(__file__).resolve().parent;APP_SOURCE=TESTS/'prototypebench.py';KEY=TESTS/"answer_key.json"
PERSONA = 'hf-5170043725'
LABELS = ('haskellbuild', 'drawnvisuals')
CHECKS = (('prog_haskell=Expert', LABELS[0]), ('skill_drawing=Advanced', LABELS[1]))
MAX_POINTS = 2
MAX_ARTIFACT_BYTES = 100_000
EXPECTED_TRUE={LABELS[0]:frozenset(['pb02', 'pb03', 'pb05', 'pb07']),LABELS[1]:frozenset(['pb03', 'pb04', 'pb07', 'pb08'])}
FNAME='prototype_plan.json';LIST_KEY='reservedPrototypes'
class ContractError(ValueError):pass
def od():return Path(os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output"))
def vd():return Path(os.environ.get("ADHERENCE_VERIFIER_DIR",od()))
def write(r,d,e):
 v=vd();v.mkdir(parents=True,exist_ok=True);(v/"reward.txt").write_text(f"{r}\n");(v/"structured_output.json").write_text(json.dumps({"reward":r,"detail":d,**e},indent=2))
def fail(m,infra=False):write(0.0,m,{"checks":[],"points":0,"max_points":2,**({"error":m} if infra else {})});raise SystemExit(1)
def load_catalog(app=APP_SOURCE,keypath=KEY):
 try:tree=ast.parse(app.read_text());raw=json.loads(keypath.read_text())
 except (OSError,UnicodeDecodeError,SyntaxError,json.JSONDecodeError) as e:raise ContractError(f"cannot load app/key: {e}") from e
 vals=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="MENU" for t in n.targets):
   try:vals.append(ast.literal_eval(n.value))
   except (ValueError,TypeError) as e:raise ContractError("MENU must be literal") from e
 if len(vals)!=1 or not isinstance(vals[0],list) or len(vals[0])!=8:raise ContractError("MENU must be one eight-row list")
 rows=vals[0]
 if any(not isinstance(r,tuple) or len(r)!=5 or any(not isinstance(x,str) or not x.strip() for x in r) for r in rows):raise ContractError("MENU rows must be five nonempty strings")
 if len({r[0] for r in rows})!=8 or len({r[2] for r in rows})!=8:raise ContractError("ids/names must be unique")
 vis={r[0]:{"name":r[2],"description":r[3],"note":r[4]} for r in rows}
 if not isinstance(raw,dict) or set(raw)!={"items"} or not isinstance(raw["items"],dict) or set(raw["items"])!=set(vis):raise ContractError("app/key coverage mismatch")
 for i,x in raw["items"].items():
  if not isinstance(x,dict) or set(x)!={"name","description","note",*LABELS} or any(type(x[l]) is not bool for l in LABELS) or any(x[k]!=vis[i][k] for k in ("name","description","note")):raise ContractError("key/source row mismatch")
 for l,s in EXPECTED_TRUE.items():
  if {i for i,x in raw["items"].items() if x[l]}!=s:raise ContractError("semantic truth-set drift")
 return vis,raw["items"]
def load_picks(vis):
 p=od()/FNAME
 if not p.is_file():fail("missing app artifact")
 try:
  if p.stat().st_size>MAX_ARTIFACT_BYTES:fail("artifact too large")
  o=json.loads(p.read_text())
 except (OSError,UnicodeDecodeError,json.JSONDecodeError) as e:fail(f"invalid app artifact: {e}")
 if not isinstance(o,dict) or set(o)!={"persona",LIST_KEY} or o["persona"]!=PERSONA or not isinstance(o[LIST_KEY],list):fail("artifact schema/persona mismatch")
 rows=o[LIST_KEY]
 if len(rows)!=2:fail("exactly two picks required")
 picks=[]
 for r in rows:
  if not isinstance(r,dict) or set(r)!={"id","name"} or not isinstance(r["id"],str) or not isinstance(r["name"],str) or r["id"] not in vis or r["name"]!=vis[r["id"]]["name"]:fail("unknown id or forged name")
  picks.append(r["id"])
 if len(set(picks))!=2:fail("duplicate ids")
 return picks
def main():
 try:vis,items=load_catalog()
 except ContractError as e:fail(str(e),True)
 picks=load_picks(vis);results=[]
 for n,l in CHECKS:
  off=[i for i in picks if not items[i][l]];held=not off;results.append({"evaluator":n,"label":l,"verdict":"HELD" if held else "VIOLATED","passed":held,"offside_picks":off})
 pts=sum(x["passed"] for x in results);d=f"persona={PERSONA} score {pts}/2: "+", ".join(f'{x["evaluator"]}={x["verdict"]}' for x in results);write(float(pts),d,{"persona":PERSONA,"checks":results,"score":f"{pts}/2","points":pts,"max_points":2,"passed_count":pts,"total_checks":2,"picks":picks})
if __name__=="__main__":main()
