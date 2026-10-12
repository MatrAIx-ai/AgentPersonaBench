#!/usr/bin/env python3
"""The model must receive current page context, not a second hardcoded scenario."""
import ast
import json
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "solution/driver.py").read_text(encoding="utf-8")
tree = ast.parse(source)
builder = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_prompt")
namespace = {"json": json}
exec(compile(ast.Module(body=[builder], type_ignores=[]), "driver.py", "exec"), namespace)
questions = [{"id": "q1", "prompt": "Choose one", "options": [{"id": "q1a", "text": "Option A"}]}]
for introduction in ("Collection takes 20 minutes; alternatives are ready now.", "The reservation costs $30, not $10."):
    prompt = namespace["build_prompt"]("Visible page title", introduction, questions)
    payload = json.JSONDecoder().raw_decode(prompt[prompt.index("{"):])[0]
    assert payload == {"title": "Visible page title", "introduction": introduction, "questions": questions}
    assert "questionId" in prompt and "optionId" in prompt
calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "build_prompt"]
assert len(calls) == 1
assert [node.id for node in calls[0].args] == ["page_title", "page_intro", "questions"]
assert 'page.locator("header h1").inner_text().strip()' in source
assert 'page.locator("header p").inner_text().strip()' in source
print("DOM-backed prompt regression: passed")