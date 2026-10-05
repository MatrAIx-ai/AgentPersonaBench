import copy, importlib.util, json, os, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; s=importlib.util.spec_from_file_location("v",HERE/"verifier.py"); v=importlib.util.module_from_spec(s); s.loader.exec_module(v)
structure,key=v.load_contract()
def run(payload=None,raw=None):
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)
  if raw is not None:(out/"survey_result.json").write_text(raw)
  elif payload is not None:(out/"survey_result.json").write_text(json.dumps(payload))
  old=(os.environ.get("ADHERENCE_OUTPUT_DIR"),os.environ.get("ADHERENCE_VERIFIER_DIR"));os.environ["ADHERENCE_OUTPUT_DIR"]=str(out);os.environ["ADHERENCE_VERIFIER_DIR"]=str(out/"v")
  try:
   try:v.main();rc=0
   except SystemExit as e:rc=int(e.code or 0)
   result=json.loads((out/"v/structured_output.json").read_text())
  finally:
   for k,x in zip(("ADHERENCE_OUTPUT_DIR","ADHERENCE_VERIFIER_DIR"),old): os.environ.pop(k,None) if x is None else os.environ.__setitem__(k,x)
  return rc,result
def payload(a,b):
 ans=[]
 for q,ids in structure.items():
  oid=next(x for x in ids if key[v.LABELS[0]][x] is a and key[v.LABELS[1]][x] is b);ans.append({"questionId":q,"selectedOptionId":oid})
 return {"answers":ans}
def test_fixtures():
 for cell,score in [((True,True),2),((True,False),1),((False,True),1),((False,False),0)]: assert run(payload(*cell))[1]["reward"]==score
 good=payload(True,True); bad=[(None,None),({},None),({"answers":[]},None),(None,"{"),({"answers":good["answers"][:2]},None),({"answers":[good["answers"][0]]*3},None),({"answers":[dict(good["answers"][0],selectedOptionId="ghost"),*good["answers"][1:]]},None),({**good,"extra":1},None)]
 for p,r in bad: assert run(p,r)[1]["reward"]==0
 for mutate in (lambda d:d[v.LABELS[0]].pop(next(iter(d[v.LABELS[0]]))),lambda d:d[v.LABELS[0]].__setitem__("ghost",False),lambda d:d[v.LABELS[0]].__setitem__(next(iter(d[v.LABELS[0]])),"true"),lambda d:d[v.LABELS[0]].__setitem__(next(iter(d[v.LABELS[0]])),not d[v.LABELS[0]][next(iter(d[v.LABELS[0]]))])):
  d=copy.deepcopy(key);mutate(d)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"k";p.write_text(json.dumps(d))
   try:v.load_contract(keypath=p);raise AssertionError("corrupt key accepted")
   except v.ContractError:pass
