import copy,importlib.util,json,os,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location("v",HERE/"verifier.py");v=importlib.util.module_from_spec(s);s.loader.exec_module(v);vis,items=v.load_catalog()
def run(payload=None,raw=None):
 with tempfile.TemporaryDirectory() as td:
  o=Path(td)
  if raw is not None:(o/v.FNAME).write_text(raw)
  elif payload is not None:(o/v.FNAME).write_text(json.dumps(payload))
  old=(os.environ.get("ADHERENCE_OUTPUT_DIR"),os.environ.get("ADHERENCE_VERIFIER_DIR"));os.environ["ADHERENCE_OUTPUT_DIR"]=str(o);os.environ["ADHERENCE_VERIFIER_DIR"]=str(o/"v")
  try:
   try:v.main();rc=0
   except SystemExit as e:rc=int(e.code or 0)
   r=json.loads((o/"v/structured_output.json").read_text())
  finally:
   for k,x in zip(("ADHERENCE_OUTPUT_DIR","ADHERENCE_VERIFIER_DIR"),old):os.environ.pop(k,None) if x is None else os.environ.__setitem__(k,x)
  return rc,r
def payload(a,b):
 ids=[i for i,x in items.items() if x[v.LABELS[0]] is a and x[v.LABELS[1]] is b][:2];return {"persona":v.PERSONA,v.LIST_KEY:[{"id":i,"name":vis[i]["name"]} for i in ids]}
def test_fixtures():
 for cell,score in [((True,True),2),((True,False),1),((False,True),1),((False,False),0)]:assert run(payload(*cell))[1]["reward"]==score
 good=payload(True,True);rows=good[v.LIST_KEY];bad=[(None,None),({},None),(None,"{"),({"persona":"forged",v.LIST_KEY:rows},None),({"persona":v.PERSONA,v.LIST_KEY:rows[:1]},None),({"persona":v.PERSONA,v.LIST_KEY:[rows[0],rows[0]]},None),({"persona":v.PERSONA,v.LIST_KEY:[{"id":"ghost","name":"x"},rows[1]]},None),({**good,"extra":1},None)]
 for p,r in bad:assert run(p,r)[1]["reward"]==0
 text=v.APP_SOURCE.read_text();key=json.loads(v.KEY.read_text());first=next(iter(key["items"]))
 for src,k in [(text.replace(f'("{first}"',f'("drift"',1),copy.deepcopy(key)),(text,{"items":{i:x for i,x in key["items"].items() if i!=first}})]:
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/"a";kk=Path(td)/"k";a.write_text(src);kk.write_text(json.dumps(k))
   try:v.load_catalog(a,kk);raise AssertionError("source/key drift accepted")
   except v.ContractError:pass
