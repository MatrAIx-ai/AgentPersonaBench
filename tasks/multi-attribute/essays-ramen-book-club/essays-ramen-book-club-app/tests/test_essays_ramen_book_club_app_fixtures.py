#!/usr/bin/env python3
import json,os,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).parent;P=os.environ.get("RUNTIME_PYTHON","python3");ID="hf-6283061910"
N={'pt01': 'Harbor mystery novel + Roast vegetable sandwich', 'pt02': 'Small Arguments essay anthology + Miso ramen bowl', 'pt03': 'Orbit science-fiction novel + Spicy sesame ramen bowl', 'pt04': 'City Margins essay collection + Roast vegetable sandwich', 'pt05': 'Small Arguments essay anthology + Miso ramen bowl', 'pt06': 'Orbit science-fiction novel + Lentil grain bowl', 'pt07': 'Harbor mystery novel + Shoyu ramen bowl', 'pt08': 'Small Arguments essay anthology + Herb pasta plate'}
def a(*x):return {"persona":ID,"reservedPilots":[{"id":i,"name":N.get(i,"bad")} for i in x]}
def run(x=...,home=H):
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);o=r/"o";v=r/"v";o.mkdir()
  if x is not ...:(o/"pilot_reservations.json").write_text(x if isinstance(x,str) else json.dumps(x))
  c=subprocess.run([P,str(home/"verifier.py")],env=os.environ|{"ADHERENCE_OUTPUT_DIR":str(o),"ADHERENCE_VERIFIER_DIR":str(v)},capture_output=True);return c.returncode,json.loads((v/"structured_output.json").read_text())
def corrupt(fn):
 with tempfile.TemporaryDirectory() as t:
  task=Path(t)/"task";shutil.copytree(H.parent,task);k=task/"tests/answer_key.json";k.write_text(json.dumps(fn(json.loads(k.read_text()))));return run(a("pt02","pt05"),task/"tests")
def main():
 for x,s in [(a("pt02","pt05"),"2/2"),(a("pt04","pt08"),"1/2"),(a("pt03","pt07"),"1/2"),(a("pt01","pt06"),"0/2")]:assert run(x)[1]["score"]==s
 bad=[...,"{",[],{}, {"persona":ID,"reservedPilots":[]},{"persona":"bad","reservedPilots":[]},a("bad","pt02"),a("pt02"),a("pt02","pt02"),{"persona":ID,"reservedPilots":[{"id":"pt02","name":"forged"},{"id":"pt05","name":N["pt05"]}],"extra":1}]
 for x in bad:
  rc,d=run(x);assert rc==1 and d["reward"]==0 and d["checks"]==[]
 for fn in (lambda d:d|{"extra":{"essayaxis":True,"ramenaxis":True}},lambda d:{k:v for k,v in d.items() if k!="pt01"},lambda d:{**d,"pt01":{**d["pt01"],"ramenaxis":"true"}}):
  rc,d=corrupt(fn);assert rc==1 and d["reward"]==0 and "error" in d
 print("app fixtures PASS")
def test_fixtures():
 main()
if __name__=="__main__":main()
