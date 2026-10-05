"""Multi-attribute rule-based verifier — Morning kit: daily walk · tracks hydration, REAL WEB env.

Ground truth is the live page: hidden data-pick attributes on the options in
input/site/index.html. The agent's DOM selections (kit.json, written by
Playwright after real clicks) are checked against them — one independent binary
verdict per check. No LLM. Reward = integer 0..2.

Input: OUTPUT_DIR/anchor/kit.json = {"blockId","widgetId"}
"""
import re
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

_TASK = Path(__file__).resolve().parents[1]


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)

CHECKS = [
    ("blockId", "blocks", "morning_walk=Daily"),
    ("widgetId", "widgets", "hydration_tracking=Daily"),
]


def _maps() -> dict:
    # Option ids are prefixed by section (b* = blocks, w* = widgets), so the
    # ground truth can be bucketed straight from the data attributes.
    html = (_TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    out = {"blocks": {}, "widgets": {}}
    for mm in re.finditer(r'data-id="([bw]\d+)" data-pick="([^"]+)"', html):
        sec = "blocks" if mm.group(1).startswith("b") else "widgets"
        out[sec][mm.group(1)] = mm.group(2).lower() == "true"
    if not out["blocks"] or not out["widgets"]:
        fail("could not parse data-pick ground truth from index.html")
    return out


def main() -> None:
    maps = _maps()
    path = _output_dir() / "anchor" / "kit.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        kit = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    results = []
    for keyname, sec_id, name in CHECKS:
        oid = kit.get(keyname)
        if not oid:
            fail(f"kit.json has no {keyname} — the DOM selection is missing")
        if oid not in maps[sec_id]:
            fail(f"kit.json: {keyname}={oid!r} not on the page")
        held = maps[sec_id][oid]
        results.append({"evaluator": name, "selection": keyname, "selected_option": oid,
                        "verdict": "HELD" if held else "VIOLATED", "passed": held})
    passed_n = sum(1 for r in results if r["passed"])
    reward = float(passed_n)
    detail = f"score {passed_n}/2 checks HELD: " + ", ".join(
        f"{r['evaluator']}={r['verdict']}" for r in results)
    gen = {}
    gp = _output_dir() / "generation.json"
    if gp.is_file():
        gen = json.loads(gp.read_text(encoding="utf-8"))
    _write(reward, detail, {"persona": "morning_kit", "checks": results,
                            "score": f"{passed_n}/2", "points": passed_n, "max_points": 2,
                            "passed_count": passed_n, "total_checks": 2,
                            "trajectory": gen.get("trajectory"),
                            "generation": {"model": gen.get("model"), "usage": gen.get("token_usage")},
                            "artifacts": {"trace": "trace.zip"}})
    print(f"score={passed_n}/2 (reward={reward:.0f})  {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
