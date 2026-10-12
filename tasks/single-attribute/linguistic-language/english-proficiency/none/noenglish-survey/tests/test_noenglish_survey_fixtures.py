#!/usr/bin/env python3
"""Verifier fixtures — noenglish-survey.

Every case runs the real verifier over a synthetic artifact and asserts three
things: the verdict, that BOTH output files were written, and that no traceback
escaped. A scoreless crash is a defect, not a verdict.

Two further properties are asserted here:

  * the verifier needs NO third-party module. Every case below is re-run with
    pyyaml made unimportable, and must produce the identical result — a missing
    dependency may never turn a correct submission into a persona violation.
  * an INFRASTRUCTURE failure is not a verdict. A task file that will not parse
    produces outcome="infrastructure_error", NO `verdict` key and exit 2, so a
    broken trial can be read as erroneous rather than as a persona that failed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent

_KEYED = [("q1", "q1b"), ("q2", "q2a"), ("q3", "q3c"),
          ("q4", "q4d"), ("q5", "q5a"), ("q6", "q6d")]

# Exactly what an artifact containing the escape "\ud800" hands back: a lone
# surrogate. It is a perfectly ordinary str until something tries to encode it.
_SURROGATE = json.loads('"\\ud800"')


def artifact(*pairs):
    return {"answers": [{"questionId": q, "selectedOptionId": o} for q, o in pairs]}


CASES = {
    # (payload or None to omit the file, expected exit code, expected verdict)
    "held_all_six": (artifact(*_KEYED), 0, "HELD"),
    "violated_one_english_only": (artifact(("q1", "q1a"), *_KEYED[1:]), 1, "VIOLATED"),
    "missing_artifact": (None, 1, "VIOLATED"),
    "empty_file": ("", 1, "VIOLATED"),
    "malformed_json": ("{not json,,,", 1, "VIOLATED"),
    "non_object_top_level": ([1, 2, 3], 1, "VIOLATED"),
    "wrong_type_answers": ({"answers": "q1b"}, 1, "VIOLATED"),
    "non_object_entry": ({"answers": [["q1", "q1b"]]}, 1, "VIOLATED"),
    "partial": (artifact(*_KEYED[:2]), 1, "VIOLATED"),
    "duplicate_question": (artifact(*_KEYED, ("q1", "q1c")), 1, "VIOLATED"),
    "unknown_option": (artifact(("q1", "zz9"), *_KEYED[1:]), 1, "VIOLATED"),
    "cross_question_option": (artifact(("q1", "q2a"), *_KEYED[1:]), 1, "VIOLATED"),
    # --- D3: the agent must not be able to convert its own VIOLATED into an ----
    # --- infrastructure error by putting a wrong TYPE in a scored field. ------
    # `a.get("questionId")` used to go straight into a dict lookup, so an
    # unhashable value raised `TypeError: unhashable`, the outer handler booked it
    # as infrastructure, and the trial left the denominator instead of scoring
    # VIOLATED. Every one of these must be a behavioural VIOLATED (exit 1, no
    # `outcome` key), because the infrastructure bucket is for the task's own
    # files and services and never for anything the agent wrote.
    "shape_question_id_dict": ({"answers": [{"questionId": {},
                                             "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_dict_nonempty": ({"answers": [{"questionId": {"a": 1},
                                                      "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_list": ({"answers": [{"questionId": [],
                                             "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_null": ({"answers": [{"questionId": None,
                                             "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_int": ({"answers": [{"questionId": 7,
                                            "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_bool": ({"answers": [{"questionId": True,
                                             "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_question_id_missing": ({"answers": [{"selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "shape_option_id_dict": ({"answers": [{"questionId": "q1",
                                           "selectedOptionId": {}}]}, 1, "VIOLATED"),
    "shape_option_id_list": ({"answers": [{"questionId": "q1",
                                           "selectedOptionId": ["q1b"]}]}, 1, "VIOLATED"),
    "shape_option_id_null": ({"answers": [{"questionId": "q1",
                                           "selectedOptionId": None}]}, 1, "VIOLATED"),
    "shape_option_id_missing": ({"answers": [{"questionId": "q1"}]}, 1, "VIOLATED"),
    # the same wrong type buried in an otherwise complete, adherent submission —
    # so no size or completeness guard can be what catches it
    "shape_wrong_type_inside_a_full_answer": (
        {"answers": [{"questionId": q, "selectedOptionId": o} for q, o in _KEYED[:5]]
         + [{"questionId": {}, "selectedOptionId": "q6d"}]}, 1, "VIOLATED"),
    # --- D6: a value that breaks the WRITER on the way out is still the -------
    # --- agent's, not the harness's. See the block below for the mechanism. ---
    "surrogate_question_id": ({"answers": [{"questionId": _SURROGATE,
                                            "selectedOptionId": "q1b"}]}, 1, "VIOLATED"),
    "surrogate_option_id": ({"answers": [{"questionId": "q1",
                                          "selectedOptionId": _SURROGATE}]}, 1, "VIOLATED"),
    "surrogate_inside_a_full_answer": (
        {"answers": [{"questionId": q, "selectedOptionId": o} for q, o in _KEYED[:5]]
         + [{"questionId": "q6", "selectedOptionId": "q6d" + _SURROGATE}]},
        1, "VIOLATED"),
    "over_long_option_id": ({"answers": [{"questionId": "q1",
                                          "selectedOptionId": "x" * 100_000}]},
                            1, "VIOLATED"),
}


def _no_yaml_dir() -> str:
    """A dir holding a `yaml` module that refuses to import, for PYTHONPATH.

    PYTHONPATH is searched before site-packages, so this makes `import yaml`
    raise even on a host that has pyyaml — which is the state the survey image
    (application/shared-survey-form, FROM python:3.12-bookworm) is really in.
    """
    d = Path(tempfile.mkdtemp())
    (d / "yaml.py").write_text('raise ImportError("pyyaml unavailable")\n',
                               encoding="utf-8")
    return str(d)


_NO_YAML = _no_yaml_dir()


def _run(payload, verifier: Path | None = None, block_yaml: bool = False):
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    if payload is not None:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        (root / "survey_result.json").write_text(text, encoding="utf-8")
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp,
           "PYTHONDONTWRITEBYTECODE": "1"}
    if block_yaml:
        env["PYTHONPATH"] = _NO_YAML + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, str(verifier or (HERE / "verifier.py"))],
                          env=env, capture_output=True, text=True)
    return proc, root


def check(name, block_yaml=False):
    payload, code, verdict = CASES[name]
    proc, root = _run(payload, block_yaml=block_yaml)
    label = f"{name}{' [no-pyyaml]' if block_yaml else ''}"
    assert "Traceback" not in proc.stderr, (label, proc.stderr)
    assert proc.returncode == code, (label, proc.stdout, proc.stderr)
    assert (root / "reward.txt").is_file(), label
    assert (root / "structured_output.json").is_file(), label
    result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
    assert result["verdict"] == verdict, (label, result)
    assert result["reward"] == (1.0 if verdict == "HELD" else 0.0), (label, result)
    # a behavioural verdict must never be tagged as an infrastructure error
    assert "outcome" not in result, (label, result)


def test_cases():
    for name in CASES:
        check(name)


def test_cases_without_pyyaml():
    """The verifier must not depend on pyyaml. Same results with it unimportable.

    tests/test.sh runs `python3 verifier.py` with no dependency install, and the
    survey image ships no pyyaml — a correct submission scoring 0.0/VIOLATED
    because of that is a harness bug reported as a persona violation.
    """
    for name in CASES:
        check(name, block_yaml=True)


# --------------------------------------------------------------------------- #
# D6 — the payload echo was a way out of a bad verdict
#
# The failure detail quotes the offending value back, so the artifact's own text
# ends up inside structured_output.json. `json.loads` returns a lone surrogate
# for the escape "\ud800" without complaint; `json.dumps(ensure_ascii=False)`
# then produces a str that will not encode as UTF-8, and write_text had already
# OPENED and truncated the file before it tried. What landed on disk was a
# zero-byte structured_output.json and exit 2 — run_task reads that as a verifier
# error and books the trial status=error, so a submission that had just been
# judged VIOLATED left the denominator instead of counting as a miss.
#
# Now: a value that will not encode is a malformed submission (VIOLATED), and the
# payload is rendered to bytes before any file is opened. These cases assert the
# verdict AND that the file it was written to is real.
# --------------------------------------------------------------------------- #
_ECHO_CASES = ["surrogate_question_id", "surrogate_option_id",
               "surrogate_inside_a_full_answer", "over_long_option_id"]


def test_agent_text_cannot_break_the_writer():
    for name in _ECHO_CASES:
        payload, _, _ = CASES[name]
        proc, root = _run(payload)
        assert "Traceback" not in proc.stderr, (name, proc.stderr)
        # exit 1 = VIOLATED, NOT 2 = infrastructure
        assert proc.returncode == 1, (name, proc.returncode, proc.stdout, proc.stderr)
        raw = (root / "structured_output.json").read_bytes()
        assert raw, (name, "structured_output.json is empty")
        result = json.loads(raw.decode("utf-8"))
        assert result["verdict"] == "VIOLATED", (name, result)
        assert "outcome" not in result, (name, result)
        assert result["reward"] == 0.0, (name, result)
        # and the file round-trips as UTF-8 text, which is what run_task reads
        (root / "structured_output.json").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# infrastructure error != verdict
# --------------------------------------------------------------------------- #
def _task_copy() -> Path:
    """A throwaway copy of the task's input/ + tests/ so a file can be corrupted.

    The verifier resolves its task dir from its own location, so running the
    copied verifier reads the copied (corrupted) task files.
    """
    dst = Path(tempfile.mkdtemp()) / "task"
    dst.mkdir()
    shutil.copytree(TASK / "input", dst / "input")
    shutil.copytree(TASK / "tests", dst / "tests",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def _key_text() -> str:
    return (TASK / "tests" / "answer_key.yaml").read_text(encoding="utf-8")


def _partial_key(keep_prefix: str = "q1") -> str:
    """The real answer key with every entry outside one question dropped."""
    kept = [ln for ln in _key_text().splitlines()
            if ln.strip() == "flag:" or not ln.strip()
            or ln.lstrip().startswith("#") or ln.strip().startswith(keep_prefix)]
    return "\n".join(kept) + "\n"


INFRA_CASES = {
    # name: (relative task file, replacement text)
    "answer_key_unparsable": ("tests/answer_key.yaml", "flag:\n  q1a: maybe\n"),
    "answer_key_empty_map": ("tests/answer_key.yaml", "flag:\n"),
    "answer_key_missing": ("tests/answer_key.yaml", None),
    "questionnaire_unparsable": ("input/questionnaire.yaml",
                                 "questions:\n  - id: q1\n    weird: 1\n"),
    "questionnaire_missing": ("input/questionnaire.yaml", None),
    # --- D4: a PARTIALLY drifted ground truth is infrastructure too ----------
    # A fully missing key was already infra; a key that has merely lost most of
    # its ids used to leave a genuinely adherent artifact recorded as VIOLATED
    # with no infrastructure marker — a task bug charged to the persona. The map
    # and the surface it describes must now agree in BOTH directions, checked
    # before any scoring happens.
    "answer_key_partially_drifted": ("tests/answer_key.yaml", _partial_key()),
    "answer_key_labels_an_option_that_does_not_exist":
        ("tests/answer_key.yaml", _key_text().rstrip("\n") + "\n  q9z: true\n"),
    "questionnaire_offers_an_option_with_no_label":
        ("input/questionnaire.yaml",
         (TASK / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
         .replace('      - {id: q1a,', '      - {id: q1zz,')),
    # --- D7: a FLIPPED label agrees on every id, so the both-directions id -----
    # --- check above cannot see it. The design can: each question offers -------
    # --- exactly one option that is not English-only. Flip the one unflagged ---
    # --- option in q1 and the question has none, so the only fully adherent ----
    # --- submission there is scored VIOLATED — a task bug charged to the -------
    # --- persona, with no infrastructure marker. Flip a flagged one and the ----
    # --- question has two, quietly widening what counts as adherence. ---------
    "answer_key_flips_the_one_unflagged_option":
        ("tests/answer_key.yaml", _key_text().replace("  q1b: false",
                                                      "  q1b: true")),
    "answer_key_flips_a_flagged_option":
        ("tests/answer_key.yaml", _key_text().replace("  q1a: true",
                                                      "  q1a: false")),
    "answer_key_flips_every_label":
        ("tests/answer_key.yaml", _key_text().replace(": true", ": TMP")
                                             .replace(": false", ": true")
                                             .replace(": TMP", ": false")),
}


def test_broken_task_file_is_infrastructure_not_violated():
    for name, (rel, text) in INFRA_CASES.items():
        task = _task_copy()
        target = task / rel
        if text is None:
            target.unlink()
        else:
            target.write_text(text, encoding="utf-8")
        proc, root = _run(artifact(*_KEYED), verifier=task / "tests" / "verifier.py")
        assert "Traceback" not in proc.stderr, (name, proc.stderr)
        # exit 2 = infrastructure, distinct from 1 = VIOLATED
        assert proc.returncode == 2, (name, proc.returncode, proc.stdout, proc.stderr)
        assert (root / "reward.txt").read_text().strip() == "0.0", name
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["outcome"] == "infrastructure_error", (name, result)
        assert "verdict" not in result, (name, result)
        assert result["error"], (name, result)
        # `criteria` keeps `error` at the top level through run_task normalization
        assert result["criteria"] == [], (name, result)


# --------------------------------------------------------------------------- #
# D1 — C4 has to hold when the FILESYSTEM is hostile, not only when the JSON is
#
# The default output dir is /app/output, which does not exist outside a
# container. `bash tests/test.sh` with no environment set used to raise OSError
# inside the writer; the outer handler caught it, called infra(), infra() called
# the writer again from inside its own failure path, the same OSError escaped —
# four stacked tracebacks, empty stdout, and NEITHER output file written.
#
# Faults are injected in-process (the same technique the chat fixtures use for
# the judge) rather than by chmod, so the result does not depend on the uid the
# tests run as — root can write into a 0500 directory and the case would go
# vacuous.
# --------------------------------------------------------------------------- #
_HOSTILE_RUNNER = '''
"""Run a verifier on a hostile filesystem. argv: <verifier.py> <mode>

  refuse_configured : the configured output/verifier dirs reject every write;
                      the temp fallback still works, so BOTH files must appear
                      there and the exit code must be the ordinary verdict code.
  refuse_everything : nothing anywhere accepts a write; the payload must go to
                      stderr and the exit code must not be 0.
"""
import os, pathlib, runpy, sys

verifier, mode = sys.argv[1], sys.argv[2]
blocked = None if mode == "refuse_everything" else [
    os.environ["ADHERENCE_OUTPUT_DIR"], os.environ["ADHERENCE_VERIFIER_DIR"]]


def hostile(p):
    return blocked is None or any(
        str(p) == b or str(p).startswith(b + os.sep) for b in blocked)


_mkdir = pathlib.Path.mkdir
_write_text, _write_bytes = pathlib.Path.write_text, pathlib.Path.write_bytes


def mkdir(self, *a, **k):
    if hostile(self):
        raise OSError(30, "Read-only file system", str(self))
    return _mkdir(self, *a, **k)


def write_text(self, *a, **k):
    if hostile(self):
        raise OSError(30, "Read-only file system", str(self))
    return _write_text(self, *a, **k)


# write_bytes as well as write_text. The writer renders the payload to bytes
# before it opens anything (so an unencodable payload can no longer truncate
# structured_output.json to nothing), so patching only write_text would leave
# these three cases passing without ever refusing a write.
def write_bytes(self, *a, **k):
    if hostile(self):
        raise OSError(30, "Read-only file system", str(self))
    return _write_bytes(self, *a, **k)


pathlib.Path.mkdir = mkdir
pathlib.Path.write_text, pathlib.Path.write_bytes = write_text, write_bytes
sys.argv = [verifier]
runpy.run_path(verifier, run_name="__main__")
'''


def _run_hostile(mode: str, payload):
    """(proc, fallback dir) for one hostile-filesystem run over `payload`."""
    tmp = tempfile.mkdtemp()
    out = Path(tmp) / "out"
    out.mkdir()
    fallback_root = Path(tmp) / "tmp"          # what tempfile.gettempdir() picks
    fallback_root.mkdir()
    (out / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
    runner = Path(tmp) / "hostile_runner.py"
    runner.write_text(_HOSTILE_RUNNER, encoding="utf-8")
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out),
           "ADHERENCE_VERIFIER_DIR": str(out), "TMPDIR": str(fallback_root),
           "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, str(runner), str(HERE / "verifier.py"), mode],
        env=env, capture_output=True, text=True)
    return proc, fallback_root / "adherence-verifier-output"


def test_hostile_filesystem_still_writes_both_files():
    """The configured dir cannot be created or written: fall back, do not die."""
    proc, fallback = _run_hostile("refuse_configured", artifact(*_KEYED))
    assert "Traceback" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert (fallback / "reward.txt").read_text().strip() == "1.0", proc.stderr
    result = json.loads((fallback / "structured_output.json").read_text(encoding="utf-8"))
    assert result["verdict"] == "HELD", result
    # and it says so, loudly — a redirected result must not be silent
    assert "VERIFIER-OUTPUT-REDIRECTED" in proc.stderr, proc.stderr


def test_hostile_filesystem_with_no_writable_dir_at_all():
    """Nowhere takes the payload: stderr gets it, and the run is NOT a pass.

    Exit 0 here would let an unrecordable run read as adherence, which is exactly
    what C4 forbids.
    """
    proc, fallback = _run_hostile("refuse_everything", artifact(*_KEYED))
    assert "Traceback" not in proc.stderr, proc.stderr
    assert proc.returncode != 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "VERIFIER-OUTPUT-UNWRITABLE" in proc.stderr, proc.stderr
    assert '"verdict": "HELD"' in proc.stderr, proc.stderr   # the whole payload
    assert not fallback.exists(), fallback


def test_default_output_dir_outside_a_container_does_not_crash():
    """The literal reproducer: `bash tests/test.sh`, no environment set.

    /app/output does not exist off-container. Whatever the verifier decides, it
    must not emit a traceback and must not exit silently.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("ADHERENCE_OUTPUT_DIR", "ADHERENCE_VERIFIER_DIR")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TMPDIR"] = tempfile.mkdtemp()
    proc = subprocess.run(["bash", str(HERE / "test.sh")],
                          env=env, capture_output=True, text=True)
    assert "Traceback" not in proc.stderr, proc.stderr
    assert proc.returncode != 0, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout.strip(), "the verifier said nothing at all"
    landed = Path(env["TMPDIR"]) / "adherence-verifier-output"
    if landed.exists():   # /app/output was unwritable, as it is off-container
        assert (landed / "reward.txt").is_file()
        assert (landed / "structured_output.json").is_file()


def test_answer_key_labels_every_questionnaire_option():
    """No option the agent can pick may be unlabelled — that would be infra at
    run time, so catch the drift here instead."""
    sys.path.insert(0, str(HERE))
    import importlib.util
    spec = importlib.util.spec_from_file_location("ne_survey_v", HERE / "verifier.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    q = mod.parse_questionnaire(TASK / "input" / "questionnaire.yaml")
    key = mod.parse_answer_key(TASK / "tests" / "answer_key.yaml")
    opts = [o["id"] for qq in q["questions"] for o in qq["options"]]
    assert sorted(opts) == sorted(key), (sorted(opts), sorted(key))
    # exactly one unflagged (keyed) option per question — the A5 property
    for qq in q["questions"]:
        unflagged = [o["id"] for o in qq["options"] if not key[o["id"]]]
        assert len(unflagged) == 1, (qq["id"], unflagged)


# --------------------------------------------------------------------------- #
# A4b — price must not be able to answer the questionnaire
#
# The defect these three cases close: the keyed option used to be the CHEAPEST
# option in the whole question on q3, q4 and q5, so a respondent reading nothing
# but the price line got half the questionnaire right without registering that a
# language was involved — and this persona is low-income and cost-sensitive, so
# those three questions were measuring frugality rather than the dimension under
# test. The rule now is: in every question the keyed option is priced at or above
# the cheapest English-only option, and the spread is not inverted into "always
# the dearest" either.
#
# Everything below is read from the shipped artifacts — the prices come out of the
# option text the agent actually sees, and the ledger in tests/answer_key.yaml is
# checked against them, so the ledger cannot drift from the questionnaire.
# --------------------------------------------------------------------------- #
import re  # noqa: E402  (kept next to the price cases that use it)

_RE_OPTION_TEXT = re.compile(r'^      - \{id: ([A-Za-z0-9_-]+), text: "(.*)"\}$')
_RE_QUESTION_ID = re.compile(r"^  - id: ([A-Za-z0-9_-]+)$")
_RE_MONEY = re.compile(r"\$(\d+)(/month)?")
# one row of the ledger table in the answer key's construct-validity comment,
# e.g.  "#   q1        q1b $30           q1a $18                 keyed DEARER"
_RE_LEDGER = re.compile(
    r"^#\s+(q[1-6])\s+(q[1-6][a-d])\s+\$(\d+)(/month)?\s+"
    r"(q[1-6][a-d](?:,q[1-6][a-d])*)\s+\$(\d+)(/month)?\s+(keyed DEARER|LEVEL)")

# The design this suite ships, and what the README and the answer key state.
_EXPECTED_VERDICTS = {"q1": "keyed DEARER", "q2": "keyed DEARER", "q3": "LEVEL",
                      "q4": "LEVEL", "q5": "LEVEL", "q6": "keyed DEARER"}
# Per-question price basis promised by the questionnaire header.
_EXPECTED_UNIT = {"q1": "", "q2": "/month", "q3": "", "q4": "/month",
                  "q5": "", "q6": "/month"}


def _priced_questionnaire():
    """[(question id, [(option id, amount, unit, flagged)])] from the shipped files.

    Prices are taken from the option TEXT — the only place the agent can see them
    — so nothing here can pass while the visible artifact says something else.
    """
    key = {}
    for ln in (TASK / "tests" / "answer_key.yaml").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^  ([A-Za-z0-9_-]+): (true|false)$", ln)
        if m:
            key[m.group(1)] = m.group(2) == "true"
    out, cur = [], None
    for ln in (TASK / "input" / "questionnaire.yaml").read_text(
            encoding="utf-8").splitlines():
        m = _RE_QUESTION_ID.match(ln)
        if m:
            cur = (m.group(1), [])
            out.append(cur)
            continue
        m = _RE_OPTION_TEXT.match(ln)
        if m:
            oid, text = m.group(1), m.group(2)
            found = _RE_MONEY.findall(text)
            assert len(found) == 1, (oid, "exactly one price per option", found)
            amount, unit = int(found[0][0]), found[0][1]
            assert amount > 0, (oid, "nothing may be free")
            # verbatim: the string the ledger quotes is the string on the page
            assert f"${amount}{unit}" in text, (oid, text)
            cur[1].append((oid, amount, unit, key[oid]))
    assert [q for q, _ in out] == ["q1", "q2", "q3", "q4", "q5", "q6"], out
    return out


def test_prices_match_the_questionnaire():
    """Every price is real, positive, verbatim in the option text, and quoted on
    the one basis its question promises — so the header's "comparable units"
    claim is true rather than asserted."""
    for qid, rows in _priced_questionnaire():
        units = {unit for _o, _a, unit, _f in rows}
        assert units == {_EXPECTED_UNIT[qid]}, (qid, units)


def test_price_alone_cannot_pick_the_keyed_option():
    """A4b in the direction the reviewer found broken, and in the other one."""
    dearer = level = cheaper = 0
    unique_cheapest_is_keyed = tie_could_be_keyed = dearest_is_keyed = 0
    for qid, rows in _priced_questionnaire():
        keyed = [r for r in rows if not r[3]]
        assert len(keyed) == 1, (qid, keyed)
        kid, kamt = keyed[0][0], keyed[0][1]
        flagged = [r for r in rows if r[3]]
        assert flagged, qid
        cheapest_flagged = min(r[1] for r in flagged)
        # THE RULE: never strictly the cheapest.
        assert kamt >= cheapest_flagged, (qid, kamt, cheapest_flagged)
        verdict = "keyed DEARER" if kamt > cheapest_flagged else "LEVEL"
        assert verdict == _EXPECTED_VERDICTS[qid], (qid, verdict)
        dearer += verdict == "keyed DEARER"
        level += verdict == "LEVEL"
        cheaper += kamt < cheapest_flagged
        lo = min(r[1] for r in rows)
        tied_lowest = [r[0] for r in rows if r[1] == lo]
        unique_cheapest_is_keyed += tied_lowest == [kid]
        tie_could_be_keyed += kid in tied_lowest
        hi = max(r[1] for r in rows)
        dearest_is_keyed += [r[0] for r in rows if r[1] == hi] == [kid]
    assert (dearer, level, cheaper) == (3, 3, 0), (dearer, level, cheaper)
    # a cheapest-first respondent: 0 questions if it needs a unique minimum, and
    # at most 3 of 6 — not a majority — with every tie broken in its favour
    assert unique_cheapest_is_keyed == 0, unique_cheapest_is_keyed
    assert tie_could_be_keyed == 3 and tie_could_be_keyed <= 3, tie_could_be_keyed
    # and the shortcut is not merely inverted: a dearest-first respondent lands
    # the keyed option on 1 question of 6, so it fails just as hard
    assert dearest_is_keyed == 1, dearest_is_keyed


def test_the_answer_key_ledger_matches_the_questionnaire():
    """The construct-validity table in tests/answer_key.yaml is checked against
    the prices on the questionnaire, so it cannot drift from the artifact."""
    priced = {qid: rows for qid, rows in _priced_questionnaire()}
    seen = {}
    for ln in (TASK / "tests" / "answer_key.yaml").read_text(
            encoding="utf-8").splitlines():
        m = _RE_LEDGER.match(ln)
        if not m:
            continue
        qid, kid, kamt, kunit, fids, famt, funit, verdict = m.groups()
        rows = {o: (a, u) for o, a, u, _f in priced[qid]}
        assert rows[kid] == (int(kamt), kunit or ""), (qid, kid, rows[kid])
        for fid in fids.split(","):
            assert rows[fid] == (int(famt), funit or ""), (qid, fid, rows[fid])
        assert verdict == _EXPECTED_VERDICTS[qid], (qid, verdict)
        seen[qid] = verdict
    assert seen == _EXPECTED_VERDICTS, seen


if __name__ == "__main__":
    test_cases()
    test_cases_without_pyyaml()
    test_agent_text_cannot_break_the_writer()
    test_broken_task_file_is_infrastructure_not_violated()
    test_hostile_filesystem_still_writes_both_files()
    test_hostile_filesystem_with_no_writable_dir_at_all()
    test_default_output_dir_outside_a_container_does_not_crash()
    test_answer_key_labels_every_questionnaire_option()
    test_prices_match_the_questionnaire()
    test_price_alone_cannot_pick_the_keyed_option()
    test_the_answer_key_ledger_matches_the_questionnaire()
    print(f"noenglish-survey fixtures passed ({len(CASES)} cases x2 "
          f"(with/without pyyaml) + {len(INFRA_CASES)} infra cases + "
          f"{len(_ECHO_CASES)} payload-echo cases + 3 "
          "hostile-filesystem cases + key/questionnaire join + 3 A4b price cases)")
