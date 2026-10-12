#!/usr/bin/env python3
"""Deterministic smoke suite for the compiled two-check (multi-attribute) sets.

For every set the two-check compiler lists in generated_multi_sets.json, this
exercises the survey, web and app verifiers against fixtures DERIVED FROM THE
TASK'S OWN GROUND TRUTH (the questionnaire + tests/answer_key.yaml, the page's
two data-* labels, the app catalog parsed from its Tkinter source). The single
suite (verifier_smoke.py) proves a binary verdict flips; a two-check verifier
must additionally prove that the two checks are scored INDEPENDENTLY on the
same picks, so per verifier this asserts:
  * a submission acceptable on both checks scores 2/2 (reward 2.0);
  * a submission acceptable on check A only scores exactly 1/2 with check A
    HELD and check B VIOLATED — and the mirror for B only;
  * a submission acceptable on neither scores 0/2 while still exiting 0
    (scored, not failed);
  * a partial / under-count submission never scores (fails on the bound, the
    bound is named in the detail);
  * a three-pick and an OVER-count submission fail on the count bound (the app
    asks for exactly two picks: only two rows are acceptable on both checks);
  * duplicated ids collapse before the bound;
  * a malformed submission fails cleanly WITH reward.txt + structured_output.json;
  * (apps) forged ids and labels contradicting the catalog never score.
Chat verifiers are checked for the ambiguity-safe verdict parse, the data guard
and one judge rubric per check; the web driver gets the same static lint as the
single sets; and the corpus positional audit is rebuilt from the shipped
artifacts per check.

Run from the repo root:  python3 evaluation/src/tools/multi_smoke.py
Requires stdlib + pyyaml. Exit 0 = all green.
"""
from __future__ import annotations

import ast
import json
import re
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import verifier_smoke as VS  # noqa: E402  (shared helpers: check, run_verifier, ...)

MANIFEST = HERE / "generated_multi_sets.json"
check, run_verifier, outputs_written, last_detail = VS.check, VS.run_verifier, VS.outputs_written, VS.last_detail


def _structured(out_dir: Path) -> dict:
    try:
        return json.loads((out_dir / "structured_output.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _score(out_dir: Path) -> tuple[float | None, list]:
    s = _structured(out_dir)
    return s.get("reward"), [(c.get("evaluator"), c.get("passed")) for c in s.get("checks", [])]


def _acceptable(row: dict, labels: dict, want: tuple[bool, bool]) -> bool:
    """row -> label bools; want -> (acceptable on A?, acceptable on B?)."""
    return all(((row[lab] == ok) == w) for (lab, ok), w in zip(labels.items(), want))


def _labeled_ok(cfg: dict) -> dict:
    """label -> True if a labeled stimulus is the acceptable side (exhibit) else False."""
    return {c["label"]: c["direction"] == "exhibit" for c in cfg["checks"]}


def _names(cfg: dict) -> list[str]:
    return [f"{c['attribute']}={c['value']}" for c in cfg["checks"]]


def _assert_split(task: Path, out: Path, want_reward: float, want_passed: list[bool], what: str) -> None:
    rc = run_verifier(task, out)
    reward, checks = _score(out)
    passed = [p for _, p in checks]
    check(rc == 0 and reward == want_reward and passed == want_passed and outputs_written(out),
          f"{task.name}: {what} -> reward {want_reward} checks {want_passed} (got rc={rc}, {reward}, {passed})")


# --------------------------------------------------------------------------- #
def smoke_survey(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-survey"
    q = yaml.safe_load((task / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
    key = yaml.safe_load((task / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
    ok = _labeled_ok(cfg)
    labels = list(ok)
    check(set(labels) <= set(key), f"{task.name}: answer key carries both label maps {labels}")
    structure = {qq["id"]: [o["id"] for o in qq["options"]] for qq in q["questions"]}

    def pick(want: tuple[bool, bool]) -> dict:
        answers = []
        for qid, opts in structure.items():
            oid = next(o for o in opts if _acceptable({lab: bool(key[lab][o]) for lab in labels}, ok, want))
            answers.append({"questionId": qid, "selectedOptionId": oid})
        return {"answers": answers}

    for qid, opts in structure.items():
        cells = {tuple(key[lab][o] == ok[lab] for lab in labels) for o in opts}
        check(len(opts) == 4 and len(cells) == 4, f"{task.name}: {qid} offers one option per acceptability cell")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        sub = out / "survey_result.json"
        sub.write_text(json.dumps(pick((True, True))), encoding="utf-8")
        _assert_split(task, out, 2.0, [True, True], "both-acceptable answers")
        sub.write_text(json.dumps(pick((True, False))), encoding="utf-8")
        _assert_split(task, out, 1.0, [True, False], "A-only answers")
        sub.write_text(json.dumps(pick((False, True))), encoding="utf-8")
        _assert_split(task, out, 1.0, [False, True], "B-only answers")
        sub.write_text(json.dumps(pick((False, False))), encoding="utf-8")
        _assert_split(task, out, 0.0, [False, False], "neither-acceptable answers")
        partial = {"answers": pick((True, True))["answers"][:1]}
        sub.write_text(json.dumps(partial), encoding="utf-8")
        check(run_verifier(task, out) == 1 and "unanswered" in last_detail(out) and outputs_written(out),
              f"{task.name}: partial submission fails on coverage")
        sub.write_text(json.dumps({"answers": [{"questionId": ["q1"], "selectedOptionId": "x"}]}), encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string ids fail cleanly with outputs written")
        sub.write_text('{"answers": [', encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: malformed fails with outputs written")


def _page_rows(cfg: dict) -> dict:
    task = cfg["base"] / f"{cfg['name']}-web"
    html = (task / "input" / "site" / "index.html").read_text(encoding="utf-8")
    la, lb = [c["label"] for c in cfg["checks"]]
    rows = {}
    for m in re.finditer(rf'data-id="([^"]+)"\s+data-{la}="([^"]+)"\s+data-{lb}="([^"]+)"', html):
        rows[m.group(1)] = {la: m.group(2) == "true", lb: m.group(3) == "true"}
    return rows


def smoke_web(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-web"
    rows = _page_rows(cfg)
    ok = _labeled_ok(cfg)
    cell = {w: [i for i, r in rows.items() if _acceptable(r, ok, w)]
            for w in ((True, True), (True, False), (False, True), (False, False))}
    check(len(rows) == 12 and all(len(v) == 3 for v in cell.values()),
          f"{task.name}: page offers 12 items, 3 per acceptability cell")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td); (out / "anchor").mkdir()
        sub = out / "anchor" / cfg["web_file"]
        put = lambda ids: sub.write_text(json.dumps({cfg["web_key"]: ids}), encoding="utf-8")  # noqa: E731
        put(cell[(True, True)]);   _assert_split(task, out, 2.0, [True, True], "both-acceptable cart")
        put(cell[(True, False)]);  _assert_split(task, out, 1.0, [True, False], "A-only cart")
        put(cell[(False, True)]);  _assert_split(task, out, 1.0, [False, True], "B-only cart")
        put(cell[(False, False)]); _assert_split(task, out, 0.0, [False, False], "neither cart")
        # one offside pick is enough to lose a check: 2 both-ok + 1 A-only -> B violated
        put(cell[(True, True)][:2] + cell[(True, False)][:1])
        _assert_split(task, out, 1.0, [True, False], "one B-offside pick costs check B only")
        put(cell[(True, True)][:2])
        check(run_verifier(task, out) == 1 and "exactly 3" in last_detail(out),
              f"{task.name}: under-count fails on the count bound")
        put(cell[(True, True)] + cell[(False, False)][:1])
        check(run_verifier(task, out) == 1 and "exactly 3" in last_detail(out),
              f"{task.name}: over-count (4 ids) fails on the count bound")
        put([cell[(True, True)][0]] + cell[(True, True)])
        _assert_split(task, out, 2.0, [True, True], "duplicate ids collapse before the bound")
        put(cell[(True, True)][:2] + [["not", "a", "string"]])
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string id fails cleanly with outputs written")
        put(cell[(True, True)][:2] + ["zzz-unknown"])
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: unknown id fails with outputs written")
        sub.write_text("{", encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: malformed fails with outputs written")


def catalog_from_app(cfg: dict) -> dict:
    """id -> {"name", labels...} parsed from the app source's catalog literal."""
    src = (cfg["base"] / f"{cfg['name']}-app" / "environment" / cfg["app"]).read_text(encoding="utf-8")
    la, lb = [c["label"] for c in cfg["checks"]]
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
            try:
                items = ast.literal_eval(node.value)
            except ValueError:
                continue
            if items and all(isinstance(t, tuple) and len(t) >= 7 and isinstance(t[-1], bool)
                             and isinstance(t[-2], bool) for t in items):
                return {t[0]: {"name": t[2], la: t[-2], lb: t[-1]} for t in items}
    raise SystemExit(f"no two-label catalog literal found in {cfg['app']}")


def smoke_app(cfg: dict) -> None:
    task = cfg["base"] / f"{cfg['name']}-app"
    cat = catalog_from_app(cfg)
    ok = _labeled_ok(cfg)
    la, lb = list(ok)
    cell = {w: [i for i, r in cat.items() if _acceptable({la: r[la], lb: r[lb]}, ok, w)]
            for w in ((True, True), (True, False), (False, True), (False, False))}
    check(len(cat) == 8 and all(len(v) == 2 for v in cell.values()),
          f"{task.name}: catalog holds 8 rows, 2 per acceptability cell")
    lk = cfg["app_list"]

    def entries(ids):
        # real ids, no label fields: labels come from the host-side catalog
        return [{"id": i, "name": cat[i]["name"]} for i in ids]

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        sub = out / cfg["app_file"]
        put = lambda rows: sub.write_text(json.dumps({lk: rows}), encoding="utf-8")  # noqa: E731
        put(entries(cell[(True, True)]));   _assert_split(task, out, 2.0, [True, True], "both-acceptable picks")
        put(entries(cell[(True, False)]));  _assert_split(task, out, 1.0, [True, False], "A-only picks")
        put(entries(cell[(False, True)]));  _assert_split(task, out, 1.0, [False, True], "B-only picks")
        put(entries(cell[(False, False)])); _assert_split(task, out, 0.0, [False, False], "neither picks")
        put(entries(cell[(True, True)][:1]))
        check(run_verifier(task, out) == 1 and "asks for exactly 2" in last_detail(out),
              f"{task.name}: under-count fails on the count bound")
        put(entries(cell[(True, True)] + cell[(False, False)][:1]))
        check(run_verifier(task, out) == 1 and "asks for exactly 2" in last_detail(out),
              f"{task.name}: three picks fail on the count bound (only two rows are acceptable on both checks)")
        put(entries(cell[(True, True)] + cell[(False, False)]))
        check(run_verifier(task, out) == 1 and "asks for exactly 2" in last_detail(out),
              f"{task.name}: over-count (4 ids) fails on the count bound")
        put(entries([cell[(True, True)][0]] + cell[(True, True)]))
        _assert_split(task, out, 2.0, [True, True], "duplicate ids collapse before the bound")
        put([{"id": ["not", "a", "string"], "name": "x"}] + entries(cell[(True, True)][:1]))
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: non-string id fails cleanly with outputs written")
        forged = [{"id": "zz-forged-1", "name": "x", la: True, lb: False},
                  {"id": "zz-forged-2", "name": "y", la: True, lb: False}]
        put(forged)
        check(run_verifier(task, out) == 1 and outputs_written(out),
              f"{task.name}: forged ids outside the app catalog never scored")
        real = cell[(True, True)][0]
        tampered = [{"id": real, "name": cat[real]["name"], la: not cat[real][la]},
                    {"id": cell[(True, True)][1], "name": cat[cell[(True, True)][1]]["name"]}]
        put(tampered)
        check(run_verifier(task, out) == 1 and "contradicting" in last_detail(out),
              f"{task.name}: label contradicting the catalog never scored")
        sub.write_text('["not an object"]', encoding="utf-8")
        check(run_verifier(task, out) != 0 and outputs_written(out),
              f"{task.name}: malformed fails with outputs written")


def smoke_chat(cfg: dict) -> None:
    v = (cfg["base"] / f"{cfg['name']}-chat" / "tests" / "verifier.py").read_text(encoding="utf-8")
    check("re.match" in v and "len(found) == 1" in v,
          f"{cfg['name']}-chat: ambiguity-safe verdict parse present")
    check("DATA to evaluate" in v, f"{cfg['name']}-chat: judge data-guard present")
    names = _names(cfg)
    check(all(json.dumps(n) in v for n in names) and v.count("Answer HELD if") == 2,
          f"{cfg['name']}-chat: one judge rubric per check {names}")


def smoke_positional_corpus(sets: list) -> None:
    """Rebuild per-check acceptability rows from the SHIPPED artifacts and audit them."""
    sys.path.insert(0, str(HERE / "task_gen"))
    from gen_multi import MAX_BLIND_RATE, positional_exploit_audit
    corpus = []
    for cfg in sets:
        ok = _labeled_ok(cfg)
        rows = _page_rows(cfg)
        cat = catalog_from_app(cfg)
        task = cfg["base"] / f"{cfg['name']}-survey"
        q = yaml.safe_load((task / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
        key = yaml.safe_load((task / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
        for lab, want in ok.items():
            corpus.append({
                "web": [r[lab] == want for r in rows.values()],
                "app": [r[lab] == want for r in cat.values()],
                "survey": [[bool(key[lab][o["id"]]) == want for o in qq["options"]] for qq in q["questions"]],
            })
    check(len(corpus) > 0, "positional audit: rebuilt a per-check corpus from the shipped artifacts")
    # Like the compiler, the ceiling is enforced from 30 sets: the ceilings are
    # calibrated on the 58-set null, and over a small corpus the best of hundreds
    # of candidate policies sits well above them by chance alone, so small
    # corpora are reported, not gated.
    enforce = len(sets) >= 30
    for surface, rate, chance, pol in positional_exploit_audit(corpus):
        ceiling = MAX_BLIND_RATE[surface]
        what = (f"positional audit {surface}: best content-blind policy {rate:.1%} "
                f"<= {ceiling:.0%} ceiling (chance {chance:.1%}, policy {pol})")
        if enforce:
            check(rate <= ceiling, what)
        else:
            print(f"  info {what} — advisory at {len(sets)} set(s)")


def _live(cfg: dict, surface: str) -> bool:
    return (cfg["base"] / f"{cfg['name']}-{surface}").is_dir()


def main() -> None:
    if not MANIFEST.is_file():
        print("no generated_multi_sets.json — nothing to smoke")
        return
    sets = []
    for row in json.loads(MANIFEST.read_text(encoding="utf-8")):
        sets.append(dict(row, base=REPO / row["base"]))
    for cfg in sets:
        print(f"== {cfg['name']} ==")
        # A surface moved to tasks-archive/ is retired; smoke only the live ones.
        if _live(cfg, "survey"):
            smoke_survey(cfg)
        if _live(cfg, "web"):
            smoke_web(cfg)
            VS.smoke_web_driver(cfg)
        if _live(cfg, "app"):
            smoke_app(cfg)
        if _live(cfg, "chat"):
            smoke_chat(cfg)
    smoke_positional_corpus([c for c in sets if all(_live(c, s) for s in ("survey", "web", "app"))])
    if VS.FAILURES:
        print(f"\n{len(VS.FAILURES)} FAILURE(S):")
        for f in VS.FAILURES:
            print(" -", f)
        sys.exit(1)
    print(f"\nALL TWO-CHECK SMOKE CHECKS PASS ({len(sets)} sets)")


if __name__ == "__main__":
    main()
