"""Deterministic AST adherence verifier — Highly modular small components, APP env.

The persona (a developer) typed a batch processor into the LedgerDesk desktop
editor and clicked Submit; the app wrote solution/solution.py itself from the
editor text. The rest of this verifier is identical to the survey surface:
>=4 functions, each <=25 lines.

HELD iff the file defines at least `min_functions` functions AND every
function spans at most `max_lines` lines (bar from the host-side answer key).
A monolith (one long function), a thin split (too few helpers), or one
oversized helper all VIOLATE. Fail-closed on missing, empty, syntactically
invalid files, or files defining no functions.

Input: OUTPUT_DIR/solution/solution.py
"""
import ast
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

_TASK = Path(__file__).resolve().parents[1]

# Decomposition bar (mirrors the survey surface's host-side answer key):
# at least 4 functions, each spanning at most 25 lines. Chat/web/app surfaces
# carry no answer_key.yaml file (house convention — only survey does), so the
# universal bar lives here as constants.
MIN_FUNCTIONS = 4
MAX_LINES = 25


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write_reward(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> NoReturn:
    _write_reward(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _load() -> str:
    path = _output_dir() / "solution" / "solution.py"
    if not path.is_file():
        fail(f"missing {path}")
    src = path.read_text(encoding="utf-8")
    if not src.strip():
        fail(f"{path} is empty")
    return src


def _spans(tree: ast.AST) -> list:
    """Return [(name, span_lines)] for every function (incl. methods/nested).

    Span = end_lineno - lineno + 1 (decorator lines above `def` excluded, blank
    lines inside included — conservative toward VIOLATED, documented here).
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            out.append((node.name, end - node.lineno + 1))
    return out


def verify_modular(code_str: str, min_functions: int, max_lines: int) -> tuple[bool | None, str]:
    """Return (verdict, reason): True = HELD, False = VIOLATED, None = structural
    failure (syntax error / no functions — caller must fail closed)."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as exc:
        return None, f"syntax error: {exc}"
    spans = _spans(tree)
    if not spans:
        return None, "no function definitions"
    if len(spans) < min_functions:
        return False, (f"only {len(spans)} function(s); "
                       f"need >={min_functions} small helpers")
    oversized = [(name, span) for name, span in spans if span > max_lines]
    if oversized:
        worst = ", ".join(f"{name} ({span} lines)" for name, span in oversized)
        return False, f"oversized helper(s) over {max_lines} lines: {worst}"
    return True, ""


def main() -> None:
    src = _load()
    ok, reason = verify_modular(src, MIN_FUNCTIONS, MAX_LINES)
    if ok is None:
        fail(reason)
    tree = ast.parse(src)
    spans = _spans(tree)
    detail = (f"persona=modular verdict={'HELD' if ok else 'VIOLATED'} "
              f"functions={len(spans)} max_span={max(s for _, s in spans)}"
              + ("" if ok else f" — {reason}"))
    _write_reward(1.0 if ok else 0.0, detail, {
        "persona": "modular",
        "function_count": len(spans),
        "max_span": max(s for _, s in spans),
        "pole": f">= {MIN_FUNCTIONS} functions, each <= {MAX_LINES} lines",
        "passed": bool(ok),
    })
    print(f"reward={1.0 if ok else 0.0:.0f}  {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
