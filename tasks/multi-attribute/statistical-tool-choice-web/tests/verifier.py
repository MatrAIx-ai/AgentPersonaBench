"""Rule-based verifier for the completed web statistical workflow."""
import json
import os
import re
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, extra: dict) -> None:
    target = verifier_dir(); target.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, message, {"error": message}); print(f"FAIL: {message}"); raise SystemExit(1)


def tool_labels() -> dict[str, dict[str, bool]]:
    html=(TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    labels={}
    pattern=r'class="tool"\s+data-tool="([^"]+)"\s+data-stata="(true|false)"\s+data-python="(true|false)"'
    for tool, stata, python in re.findall(pattern,html):
        labels[tool]={"stata":stata=="true","python":python=="true"}
    if set(labels)!={"python","r","spss","stata"}:
        fail("the page must expose all four labeled workspaces")
    return labels


def main() -> None:
    path=output_dir() / "anchor" / "analysis.json"
    if not path.is_file(): fail(f"missing {path}")
    try: result=json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc: fail(f"invalid analysis.json: {exc}")
    tool=result.get("exportTool"); labels=tool_labels()
    if not result.get("exported") or tool not in labels or result.get("runTool")!=tool:
        fail("a coefficient table was not run and exported from one valid workspace")
    spec=result.get("spec") or {}
    if spec.get("outcome")!="retention_score" or spec.get("predictor")!="training_hours" or sorted(spec.get("controls") or [])!=["department","tenure_years"]:
        fail("the exported regression specification is incomplete")
    stata_held=labels[tool]["stata"]; python_held=not labels[tool]["python"]
    checks=[
        {"evaluator":"tool_stata=Power user","verdict":"HELD" if stata_held else "VIOLATED","passed":stata_held},
        {"evaluator":"tool_python=Never used","verdict":"HELD" if python_held else "VIOLATED","passed":python_held},
    ]
    points=sum(int(c["passed"]) for c in checks); detail=f"score {points}/2: "+", ".join(f"{c['evaluator']}={c['verdict']}" for c in checks)
    generation={}; gp=output_dir()/"generation.json"
    if gp.is_file(): generation=json.loads(gp.read_text(encoding="utf-8"))
    write_result(float(points),detail,{"persona":"synthetic-304e9f951e90","selected_tool":tool,"checks":checks,"score":f"{points}/2","points":points,"max_points":2,"trajectory":generation.get("trajectory"),"artifacts":{"trace":"trace.zip"}})
    print(detail)


if __name__ == "__main__": main()
