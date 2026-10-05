#!/usr/bin/env python3
import json,os,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).parent;P=os.environ.get("RUNTIME_PYTHON","python3")
def a(*ids):return {"answers":[{"questionId":f"q{i}","selectedOptionId":x} for i,x in enumerate(ids,1)]}
def run(x=...):
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);o=r/"o";v=r/"v";o.mkdir()
  if x is not ...:(o/"survey_result.json").write_text(x if isinstance(x,str) else json.dumps(x))
  c=subprocess.run([P,str(H/"verifier.py")],env=os.environ|{"ADHERENCE_OUTPUT_DIR":str(o),"ADHERENCE_VERIFIER_DIR":str(v)},capture_output=True);return c.returncode,json.loads((v/"structured_output.json").read_text())
def corrupt(fn):
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);task=r/"task";shutil.copytree(H.parent,task);o=r/"o";v=r/"v";o.mkdir();(o/"survey_result.json").write_text(json.dumps(a("q1c","q2d","q3a")));k=task/"tests/answer_key.yaml";k.write_text(fn(k.read_text()));c=subprocess.run([P,str(task/"tests/verifier.py")],env=os.environ|{"ADHERENCE_OUTPUT_DIR":str(o),"ADHERENCE_VERIFIER_DIR":str(v)},capture_output=True);return c.returncode,json.loads((v/"structured_output.json").read_text())
def main():
 for x,s in [(a("q1c","q2d","q3a"),"2/2"),(a("q1b","q2a","q3d"),"1/2"),(a("q1d","q2b","q3c"),"1/2"),(a("q1a","q2c","q3b"),"0/2")]:assert run(x)[1]["score"]==s
 bad=[...,"{",[],{}, {"answers":[]},{"answers":[3]},a("q1c"),a("q2d","q2d","q3a"),{"answers":a("q1c","q2d","q3a")["answers"],"extra":1},{"answers":[{"questionId":"q1","selectedOptionId":"q1c","extra":1}]}]
 for x in bad:
  rc,d=run(x);assert rc==1 and d["reward"]==0 and d["checks"]==[]
 for fn in (lambda s:s+"\nextraaxis: {}\n",lambda s:s.replace("  q1a: false","  q1a: \"false\"",1)):
  rc,d=corrupt(fn);assert rc==1 and d["reward"]==0 and "error" in d
 print("survey fixtures PASS")
def test_fixtures():
 main()
if __name__=="__main__":main()
