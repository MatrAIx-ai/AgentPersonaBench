"""Rule-based verifier for actions written by the CareerScout native app."""
import json
import os
import sys
import tomllib
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
PERSONA = "synthetic-d4731e88b55d"
FIELD = {"linkedin_activity":"action", "domain":"domain", "role_function":"function", "seniority":"seniority", "years_experience":"experience"}
EXPECTED = {"linkedin_activity":"apply", "domain":"Software & AI", "role_function":"Engineering", "seniority":"Entry", "years_experience":"0-2"}

def output_dir(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
def verifier_dir(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))
def write(reward, detail, extra):
    target=verifier_dir(); target.mkdir(parents=True, exist_ok=True); payload={"reward":reward,"detail":detail,**extra}
    (target/"reward.txt").write_text(f"{reward}\n",encoding="utf-8")
    (target/"structured_output.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
def fail(message): write(0.0,message,{}); print("FAIL:",message); sys.exit(1)

def main():
    path=output_dir()/"career_actions.json"
    if not path.is_file(): fail(f"missing {path}; the app writes it after FINISH REVIEW")
    try:
        record=json.loads(path.read_text(encoding="utf-8"))
        items=record.get("selected")
    except (json.JSONDecodeError, AttributeError) as exc: fail(f"invalid output: {exc}")
    if record.get("finished") is not True or not isinstance(items,list): fail("career review was not finished")
    if len(items)!=3 or len({item.get("id") for item in items})!=3: fail("exactly three distinct opportunity actions are required")
    required={"id","action","domain","function","seniority","experience"}
    if any(not required.issubset(item) for item in items): fail("an acted-on opportunity is missing app metadata")
    with open(TASK/"task.toml","rb") as stream: checks=tomllib.load(stream)["checks"]
    results=[]
    for check in checks:
        dim=check["dimension_id"]; observed={item["id"]:item[FIELD[dim]] for item in items}
        # One application positively demonstrates active job seeking; saving a
        # second fitting role does not negate that behavior. Fit checks stay strict.
        held=(any(value=="apply" for value in observed.values()) if dim=="linkedin_activity" else all(value==EXPECTED[dim] for value in observed.values()))
        results.append({"evaluator":check.get("evaluator_name",dim),"dimension_id":dim,"value":check["value"],"observed":observed,"verdict":"HELD" if held else "VIOLATED","passed":held})
    points=sum(item["passed"] for item in results); total=len(results)
    detail=f"persona={PERSONA} score {points}/{total}: "+", ".join(f"{item['dimension_id']}={item['verdict']}" for item in results)
    write(float(points),detail,{"persona":PERSONA,"criteria":results,"checks":results,"score":f"{points}/{total}","points":points,"max_points":total,"passed_count":points,"total_checks":total,"completed":True,"selected":items})
    print(detail); sys.exit(0)

if __name__=="__main__": main()
