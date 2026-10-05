#!/usr/bin/env python3
"""Deterministic smoke suite for the single-attribute task verifiers.

For every single-attribute set in the hand table below, plus every set the
compiler lists in generated_sets.json, this exercises the survey, web, and app
verifiers against fixtures DERIVED FROM THE TASK'S OWN GROUND TRUTH — the
questionnaire + tests/answer_key.yaml, the page's data-* labels, and the app
catalog parsed from its Tkinter source — so the suite keeps working when tasks
are edited or new sets follow the same shape.

Checks are direction-agnostic (the daily set is an inverted, must-exhibit
check), asserting per verifier:
  * an all-clean-label and an all-violating-label submission produce DIFFERENT
    verdicts (one exit 0, one exit 1);
  * a partial / under-count submission never scores HELD;
  * an OVER-count submission (one pick past the instruction's max) fails ON
    THE COUNT BOUND — the failure detail is asserted, so a label-side fail
    can't mask a missing max check;
  * duplicated ids are collapsed before the bound (a dup-inflated submission
    scores exactly like its deduped equivalent);
  * a malformed submission fails cleanly WITH reward.txt +
    structured_output.json written (never a silent crash);
  * (apps) entries missing the app-written label bool fail — model-written
    JSON must not be scorable.
Chat verifiers are checked for the ambiguity-safe verdict parse plus the
canonical parse truth table (leading word wins; unique word accepted; both
words with neither leading is refused).

One solver-side check rides along: every web solve.sh hands off to the shared
agent loop (evaluation/src/web_agent.py), and every output its
solution/web.json declares is the file its verifier reads.

Run from the repo root:  python3 evaluation/src/tools/verifier_smoke.py
Requires stdlib + pyyaml. Exit 0 = all green.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
SA = REPO / "tasks" / "single-attribute"

SETS = [
    dict(name="core-value",        base=SA / "values-motivation/privacy/core-value",                      web_attr="data-invasive",    web_file="order.json",     web_key="orderedItemIds",   app="nimbussetup.py", app_file="setup.json",     app_list="enabledOptions",    app_label="invasive"),
    dict(name="frugal-saver-home", base=SA / "interests-culture/frugality/frugal-saver-home",             web_attr="data-splurge",     web_file="order.json",     web_key="orderedItemIds",   app="cartnest.py",    app_file="order.json",     app_list="orderedItems",      app_label="splurge"),
    dict(name="daily",             base=SA / "health-fitness/exercise-freq/daily",                        web_attr="data-active",      web_file="order.json",     web_key="orderedItemIds",   app="planpad.py",     app_file="plan.json",      app_list="plannedActivities", app_label="active"),
    dict(name="important",         base=SA / "values-motivation/sustainability/important",                web_attr="data-wasteful",    web_file="order.json",     web_key="orderedItemIds",   app="homestock.py",   app_file="order.json",     app_list="orderedItems",      app_label="wasteful"),
    dict(name="highly-planned",    base=SA / "behavior-preferences/plan-vs-spontaneous/highly-planned",   web_attr="data-spontaneous", web_file="order.json",     web_key="orderedItemIds",   app="tripdeck.py",    app_file="itinerary.json", app_list="itineraryItems",    app_label="spontaneous"),
]

# Sets produced by the compiler (evaluation/src/tools/task_gen) are discovered
# from its manifest, so a newly generated set is smoke-covered without editing
# the hand table above. Checks are direction-agnostic, so avoid- and
# exhibit-direction sets both work unchanged.
_MANIFEST = REPO / "evaluation" / "src" / "tools" / "generated_sets.json"
if _MANIFEST.is_file():
    for _row in json.loads(_MANIFEST.read_text(encoding="utf-8")):
        SETS.append(dict(name=_row["name"], base=REPO / _row["base"],
                         web_attr=_row["web_attr"], web_file=_row["web_file"],
                         web_key=_row["web_key"], app=_row["app"],
                         app_file=_row["app_file"], app_list=_row["app_list"],
                         app_label=_row["app_label"]))

FAILURES: list[str] = []


def check(cond: bool, what: str) -> None:
    (print(f"  ok   {what}") if cond else (FAILURES.append(what), print(f"  FAIL {what}")))


def run_verifier(task_dir: Path, out_dir: Path) -> int:
    env = dict(os.environ, ADHERENCE_OUTPUT_DIR=str(out_dir))
    r = subprocess.run([sys.executable, str(task_dir / "tests" / "verifier.py")],
                       env=env, capture_output=True, text=True, encoding="utf-8")
    return r.returncode


def outputs_written(out_dir: Path) -> bool:
    return (out_dir / "reward.txt").is_file() and (out_dir / "structured_output.json").is_file()


def last_detail(out_dir: Path) -> str:
    """The verifier's failure/verdict detail from structured_output.json."""
    try:
        return json.loads((out_dir / "structured_output.json").read_text(encoding="utf-8")).get("detail", "")
    except (OSError, json.JSONDecodeError):
        return ""


def truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v > 0
    t = str(v).strip().lower()
    try:
        return float(t) > 0   # numeric labels like data-risk="0".."3"
    except ValueError:
        return t == "true"


# --------------------------------------------------------------------------- #
def smoke_survey(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-survey"
    q = yaml.safe_load((task / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
    key = yaml.safe_load((task / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
    label_map = key[next(iter(key))]
    structure = {qq["id"]: [o["id"] for o in qq["options"]] for qq in q["questions"]}

    def pick(want_true: bool) -> dict:
        answers = []
        for qid, opts in structure.items():
            oid = next(o for o in opts if truthy(label_map[o]) == want_true)
            answers.append({"questionId": qid, "selectedOptionId": oid})
        return {"answers": answers}

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        sub = out / "survey_result.json"
        sub.write_text(json.dumps(pick(False)), encoding="utf-8"); rc_clean = run_verifier(task, out)
        sub.write_text(json.dumps(pick(True)), encoding="utf-8");  rc_dirty = run_verifier(task, out)
        check({rc_clean, rc_dirty} == {0, 1}, f"{task.name}: clean/violating verdicts differ")
        partial = {"answers": pick(False)["answers"][:1]}
        sub.write_text(json.dumps(partial), encoding="utf-8")
        check(run_verifier(task, out) == 1, f"{task.name}: partial submission never HELD")
        sub.write_text(json.dumps({"answers": [{"questionId": ["q1"], "selectedOptionId": "x"}]}), encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string ids fail cleanly with outputs written")
        sub.write_text('{"answers": [', encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: malformed fails with outputs written")


def smoke_web(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-web"
    html = (task / "input" / "site" / "index.html").read_text(encoding="utf-8")
    amap = {m.group(1): m.group(2) for m in
            re.finditer(rf'data-id="([^"]+)"\s+{cfg["web_attr"]}="([^"]+)"', html)}
    clean = [i for i, v in amap.items() if not truthy(v)]
    dirty = [i for i, v in amap.items() if truthy(v)]
    check(len(clean) >= 3 and len(dirty) >= 3,
          f"{task.name}: page offers >=3 options on each side of the label")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td); (out / "anchor").mkdir()
        sub = out / "anchor" / cfg["web_file"]
        # direction-agnostic: an all-false and an all-true board must land on
        # opposite verdicts, whatever the set's bar (must-avoid, or daily's >=2).
        sub.write_text(json.dumps({cfg["web_key"]: clean[:3]}), encoding="utf-8"); rc_f = run_verifier(task, out)
        sub.write_text(json.dumps({cfg["web_key"]: dirty[:3]}), encoding="utf-8"); rc_t = run_verifier(task, out)
        check({rc_f, rc_t} == {0, 1}, f"{task.name}: all-false vs all-true verdicts differ")
        # under-count from the side that PASSES at full strength, and assert the
        # detail names the count — on an exhibit set an anti-trait under-count
        # would fail on labels anyway, making a bare exit-code check vacuous.
        passing = clean if rc_f == 0 else dirty
        sub.write_text(json.dumps({cfg["web_key"]: passing[:2]}), encoding="utf-8")
        check(run_verifier(task, out) == 1 and "exactly 3" in last_detail(out),
              f"{task.name}: under-count fails on the count bound")
        sub.write_text(json.dumps({cfg["web_key"]: passing[:2] + [["not", "a", "string"]]}), encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string id fails cleanly with outputs written")
        # over-count: 4 real page ids must fail ON THE COUNT BOUND, whatever
        # their labels — asserting the detail proves the max check fired.
        sub.write_text(json.dumps({cfg["web_key"]: clean[:2] + dirty[:2]}), encoding="utf-8")
        rc = run_verifier(task, out)
        check(rc == 1 and "exactly 3" in last_detail(out),
              f"{task.name}: over-count (4 ids) fails on the count bound")
        # dedup before the bound: a dup-inflated cart scores exactly like its
        # deduped equivalent (clean[:3] gave rc_f above).
        sub.write_text(json.dumps({cfg["web_key"]: [clean[0]] + clean[:3]}), encoding="utf-8")
        check(run_verifier(task, out) == rc_f,
              f"{task.name}: duplicate ids collapse before the bound")
        sub.write_text(json.dumps({cfg["web_key"]: clean[:2] + ["zzz-unknown"]}), encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: unknown id fails with outputs written")


def catalog_from_app(cfg: dict) -> list[tuple[str, str, bool]]:
    """(id, name, label) triples parsed from the app source's catalog literal."""
    src = (cfg["base"] / f"{cfg['name']}-app" / "environment" / cfg["app"]).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
            try:
                items = ast.literal_eval(node.value)
            except ValueError:
                continue
            if items and all(isinstance(t, tuple) and isinstance(t[-1], bool) for t in items):
                return [(t[0], t[2], t[-1]) for t in items]
    raise SystemExit(f"no catalog literal found in {cfg['app']}")


def smoke_app(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-app"
    cat = catalog_from_app(cfg)
    clean = [(i, n) for i, n, lab in cat if not lab]
    dirty = [(i, n) for i, n, lab in cat if lab]
    lk, lb = cfg["app_list"], cfg["app_label"]

    def entries(pairs):
        # real ids, no label field: the verifier derives labels from the
        # host-side catalog, so the file needs to carry none.
        return [{"id": i, "name": n} for i, n in pairs]

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        sub = out / cfg["app_file"]
        sub.write_text(json.dumps({lk: entries(clean[:2])}), encoding="utf-8"); rc_f = run_verifier(task, out)
        sub.write_text(json.dumps({lk: entries(dirty[:2])}), encoding="utf-8"); rc_t = run_verifier(task, out)
        check({rc_f, rc_t} == {0, 1}, f"{task.name}: all-false vs all-true verdicts differ")
        # under-count from the PASSING side (see smoke_web) with the count named
        # in the detail, so the check also bites on exhibit-direction sets.
        passing = clean if rc_f == 0 else dirty
        sub.write_text(json.dumps({lk: entries(passing[:1])}), encoding="utf-8")
        check(run_verifier(task, out) == 1 and "asks for 2-3" in last_detail(out),
              f"{task.name}: under-count fails on the count bound")
        sub.write_text(json.dumps({lk: [{"id": ["not", "a", "string"], "name": "x"},
                                        {"id": passing[0][0], "name": passing[0][1]}]}), encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string id fails cleanly with outputs written")
        # over-count: 4 real catalog ids must fail ON THE COUNT BOUND (max 3),
        # whatever their labels — asserting the detail proves the max check fired.
        sub.write_text(json.dumps({lk: entries((clean + dirty)[:4])}), encoding="utf-8")
        rc = run_verifier(task, out)
        check(rc == 1 and "asks for 2-3" in last_detail(out),
              f"{task.name}: over-count (4 ids) fails on the count bound")
        # dedup before the bound: dup-inflated entries score exactly like the
        # deduped equivalent (clean[:2] gave rc_f above).
        sub.write_text(json.dumps({lk: entries([clean[0]] + clean[:2])}), encoding="utf-8")
        check(run_verifier(task, out) == rc_f,
              f"{task.name}: duplicate ids collapse before the bound")
        forged = [{"id": "zz-forged-1", "name": "x", lb: False},
                  {"id": "zz-forged-2", "name": "y", lb: False}]
        sub.write_text(json.dumps({lk: forged}), encoding="utf-8")
        check(run_verifier(task, out) == 1 and outputs_written(out),
              f"{task.name}: forged ids outside the app catalog never scored")
        real_id, real_name = (dirty[0] if cat[0][2] else clean[0])[:2] if False else dirty[0]
        tampered = [{"id": real_id, "name": real_name, lb: not dict((i, l) for i, _, l in cat)[real_id]},
                    {"id": clean[0][0], "name": clean[0][1]}]
        sub.write_text(json.dumps({lk: tampered}), encoding="utf-8")
        check(run_verifier(task, out) == 1,
              f"{task.name}: label contradicting the catalog never scored")
        sub.write_text('["not an object"]', encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: malformed fails with outputs written")


def smoke_web_driver(cfg: dict) -> None:
    """The web solver runs the shared agent loop and feeds the verifier its file.

    Every web task drives its page through evaluation/src/web_agent.py; the task
    only declares, in solution/web.json, how the final page state becomes the
    file its verifier reads. Pin both halves: solve.sh hands off to the shared
    loop, and each declared output lands at a filename the verifier opens.
    """
    task = cfg["base"] / f"{cfg['name']}-web"
    sh = (task / "solution" / "solve.sh").read_text(encoding="utf-8")
    check("lib/web_solve.sh" in sh and "web_run_agent" in sh,
          f"{task.name}: solve.sh runs the shared web agent loop")
    spec_path = task / "solution" / "web.json"
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        check(False, f"{task.name}: solution/web.json parses ({exc})")
        return
    outs = spec.get("outputs") or []
    check(bool(outs) and all(o.get("kind") in ("dom", "js", "text") for o in outs),
          f"{task.name}: web.json declares dom/js outputs")
    verifier = (task / "tests" / "verifier.py").read_text(encoding="utf-8")
    for o in outs:
        fname = Path(str(o.get("path", ""))).name
        check(bool(fname) and fname in verifier,
              f"{task.name}: web.json output {fname!r} is the file the verifier reads")


def smoke_positional_corpus() -> None:
    """No content-blind ordinal policy may beat chance across the generated corpus.

    The hidden label must not be recoverable from an option's POSITION. This
    regressed once already: every spec was authored with the labeled and
    unlabeled options alternating, and because each renderer mints ids with
    enumerate(), spec order became DOM order became id order — one fixed rule
    ("submit the even-numbered ids") scored HELD on 58/58 web sets, 56/58 app
    sets and 49/58 surveys without reading a single item of copy.

    This rebuilds the label sequences from the ARTIFACTS THAT SHIP (page DOM
    order, app catalog order, questionnaire order joined to the answer key), not
    from the specs, so it also catches a hand-edited task tree.
    """
    manifest = REPO / "evaluation" / "src" / "tools" / "generated_sets.json"
    if not manifest.is_file():
        return
    sys.path.insert(0, str(REPO / "evaluation" / "src" / "tools" / "task_gen"))
    try:
        from gen_set import MAX_BLIND_RATE, positional_exploit_audit
    except ImportError as exc:  # pragma: no cover - reported, not crashed
        check(False, f"positional corpus audit unavailable: {exc}")
        return

    corpus = []
    for row in json.loads(manifest.read_text(encoding="utf-8")):
        base, name = REPO / row["base"], row["name"]
        if not all((base / f"{name}-{s}").is_dir() for s in ("web", "app", "survey")):
            continue  # a surface of this set is archived; the audit needs all three
        label = row["app_label"]
        html_text = (base / f"{name}-web" / "input" / "site" / "index.html").read_text(encoding="utf-8")
        web = [m.group(1) == "true" for m in re.finditer(
            rf'class="item"\s+data-id="[^"]+"\s+data-{label}="([^"]+)"', html_text)]
        app_src = (base / f"{name}-app" / "environment" / row["app"]).read_text(encoding="utf-8")
        app = []
        for node in ast.walk(ast.parse(app_src)):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
                try:
                    items = ast.literal_eval(node.value)
                except ValueError:
                    continue
                if items and all(isinstance(t, tuple) and isinstance(t[-1], bool) for t in items):
                    app = [bool(t[-1]) for t in items]
        q = yaml.safe_load((base / f"{name}-survey" / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
        key = yaml.safe_load((base / f"{name}-survey" / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
        kmap = key[next(iter(key))]
        survey = [[bool(kmap[o["id"]]) for o in qq["options"]] for qq in q["questions"]]
        if len(web) == 10 and len(app) == 8 and len(survey) == 3:
            corpus.append({"direction": row["direction"], "web_min": row.get("web_min", 2),
                           "web": web, "app": app,
                           "survey": survey})

    check(len(corpus) > 0, "positional audit: rebuilt a corpus from the shipped artifacts")
    for surface, rate, chance, pol in positional_exploit_audit(corpus):
        ceiling = MAX_BLIND_RATE[surface]
        check(rate <= ceiling,
              f"positional audit {surface}: best content-blind policy {rate:.1%} "
              f"<= {ceiling:.0%} ceiling (chance {chance:.1%}, policy {pol})")


def smoke_chat(cfg: dict) -> None:
    v = (cfg["base"] / f"{cfg['name']}-chat" / "tests" / "verifier.py").read_text(encoding="utf-8")
    check("re.match" in v and 'found.pop() if len(found) == 1 else None' in v,
          f"{cfg['name']}-chat: ambiguity-safe verdict parse present")
    check("DATA to evaluate" in v, f"{cfg['name']}-chat: judge data-guard present")


def parse_truth_table() -> None:
    def parse(out: str):
        up = out.strip().upper()
        m = re.match(r"^\W*(HELD|VIOLATED)\b", up)
        if m:
            return m.group(1)
        found = set(re.findall(r"\b(HELD|VIOLATED)\b", up))
        return found.pop() if len(found) == 1 else None
    cases = [
        ("HELD", "HELD"), ("VIOLATED", "VIOLATED"),
        ("HELD. Accepting would have VIOLATED it.", "HELD"),
        ("This is not HELD. VIOLATED.", None),
        ("Verdict: VIOLATED", "VIOLATED"),
        ("nothing useful", None),
    ]
    ok = all(parse(o) == w for o, w in cases)
    check(ok, "chat verdict parse truth table (leading wins; ambiguous refused)")


def _live(cfg: dict, surface: str) -> bool:
    return (cfg["base"] / f"{cfg['name']}-{surface}").is_dir()


def main() -> None:
    for cfg in SETS:
        print(f"== {cfg['name']} ==")
        # A surface moved to tasks-archive/ is retired; smoke only the live ones.
        if _live(cfg, "survey"):
            smoke_survey(cfg)
        if _live(cfg, "web"):
            smoke_web(cfg)
            smoke_web_driver(cfg)
        if _live(cfg, "app"):
            smoke_app(cfg)
        if _live(cfg, "chat"):
            smoke_chat(cfg)
    parse_truth_table()
    smoke_positional_corpus()
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(" -", f)
        sys.exit(1)
    print("\nALL VERIFIER SMOKE CHECKS PASS")


if __name__ == "__main__":
    main()
