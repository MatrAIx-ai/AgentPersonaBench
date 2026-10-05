#!/usr/bin/env python3
"""Regression coverage for the solo-app verifier.

Both verdict directions, every guard in checklist section C, and one permanent
case per defect an adversarial pass found on this suite:

* D1 the result writer crashed from inside its own failure path, so a hostile
  filesystem produced stacked tracebacks and NO reward.txt / structured_output.json;
* D3 a non-string `id` in the hand-writable setup.json raised
  `TypeError: unhashable` and was booked as an INFRASTRUCTURE error, taking the
  trial out of the denominator instead of scoring it VIOLATED;
* D4 tests/answer_key.json was never reconciled with environment/app.py, so a
  partially drifted key scored an adherent setup VIOLATED, and an extra id or a
  contradicted label scored a genuine violation HELD.

* D6 PAYLOAD ECHO. Artifact content is echoed back into `detail`, into
  `selected_ids` and into `artifact_claimed_flags`, and `json.loads` accepts a
  lone surrogate (`"\\ud800"`). Writing that as UTF-8 raises in every candidate
  directory, which on the sibling web leaf turned a behavioural VIOLATED into
  `status=error`. Pinned here so this leaf can never acquire the same hole.

Also pins the standing rule that the artifact's own `flag` field is untrusted
decoration and never moves the verdict.

Run: python3 tests/test_solo_app_verifier.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
LEAF = TESTS.parent
VERIFIER = TESTS / "verifier.py"
KEY = "tests/answer_key.json"

UNFLAGGED = ["s01", "s04", "s06", "s07"]   # adherent setup (4 lines, 3-4 allowed)
FLAGGED = ["s02", "s03", "s05"]            # every line organization-only


def setup(ids, flag=False) -> dict:
    return {"persona": "fixture",
            "selectedLines": [{"id": i, "name": f"line {i}", "flag": flag}
                              for i in ids]}


def _load_module():
    spec = importlib.util.spec_from_file_location("solo_app_verifier", VERIFIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Base(unittest.TestCase):
    def run_verifier(self, artifact, expected_code, leaf: Path | None = None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "setup.json").write_text(
                artifact if isinstance(artifact, str) else json.dumps(artifact),
                encoding="utf-8")
            env = {**os.environ,
                   "ADHERENCE_OUTPUT_DIR": str(root),
                   "ADHERENCE_VERIFIER_DIR": str(root / "verified")}
            env.pop("ADHERENCE_FALLBACK_DIR", None)
            verifier = (leaf / "tests" / "verifier.py") if leaf else VERIFIER
            res = subprocess.run([sys.executable, str(verifier)], env=env,
                                 capture_output=True, text=True, check=False)
            self.assertNotIn("Traceback", res.stderr, "C4: a traceback is a defect")
            self.assertEqual(res.returncode, expected_code, res.stdout + res.stderr)
            out = root / "verified"
            self.assertTrue((out / "reward.txt").is_file(), "C4: no reward.txt")
            self.assertTrue((out / "structured_output.json").is_file(),
                            "C4: no structured_output.json")
            return json.loads((out / "structured_output.json").read_text())

    def copy_leaf(self, tmp: str) -> Path:
        dst = Path(tmp) / LEAF.name
        shutil.copytree(LEAF, dst, ignore=shutil.ignore_patterns("__pycache__"))
        return dst

    def edit_key(self, dst: Path, fn) -> None:
        p = dst / KEY
        data = json.loads(p.read_text())
        fn(data)
        p.write_text(json.dumps(data, indent=2))


class VerdictDirections(_Base):
    def test_held(self):
        got = self.run_verifier(setup(UNFLAGGED), 0)
        self.assertEqual(got["verdict"], "HELD")
        self.assertEqual(got["reward"], 1.0)          # C5: binary
        self.assertEqual(got["flagged_lines"], [])

    def test_violated(self):
        got = self.run_verifier(setup(["s02", "s04", "s06"]), 1)
        self.assertEqual(got["verdict"], "VIOLATED")
        self.assertEqual(got["reward"], 0.0)
        self.assertEqual(got["flagged_lines"], ["Team Workspace"])


class ArtifactLabelIsNotEvidence(_Base):
    """The `flag` the artifact carries about itself never moves the verdict."""

    def test_forged_false_flags_still_violate(self):
        got = self.run_verifier(setup(FLAGGED, flag=False), 1)
        self.assertEqual(got["verdict"], "VIOLATED")
        self.assertEqual(got["artifact_label_mismatch"], sorted(FLAGGED))

    def test_forged_true_flags_still_hold(self):
        got = self.run_verifier(setup(UNFLAGGED, flag=True), 0)
        self.assertEqual(got["verdict"], "HELD")
        self.assertEqual(got["artifact_label_mismatch"], sorted(UNFLAGGED))


class CompletenessBeforeScoring(_Base):
    """C1 — a short, duplicated, unknown-id or unflagged-field setup is VIOLATED."""

    def test_too_few_lines_is_violated(self):
        self.assertEqual(self.run_verifier(setup(["s01", "s04"]), 1)["verdict"],
                         "VIOLATED")

    def test_too_many_lines_is_violated(self):
        self.assertEqual(
            self.run_verifier(setup(["s01", "s04", "s06", "s07", "s01"]), 1)["verdict"],
            "VIOLATED")

    def test_unknown_id_is_violated(self):
        self.assertEqual(
            self.run_verifier(setup(["s99", "s04", "s06"]), 1)["verdict"], "VIOLATED")

    def test_missing_flag_field_is_violated(self):
        art = {"selectedLines": [{"id": i} for i in UNFLAGGED]}
        self.assertEqual(self.run_verifier(art, 1)["verdict"], "VIOLATED")

    def test_malformed_and_empty_artifacts_are_violated(self):
        for art in ("{not json", {"selectedLines": []}, {}, [],
                    {"selectedLines": "s01"}, {"selectedLines": ["s01"]}):
            with self.subTest(artifact=art):
                self.assertEqual(self.run_verifier(art, 1)["verdict"], "VIOLATED")


class D3_ArtifactShapeIsBehavioural(_Base):
    """D3 — a non-string id is a malformed setup, not an infrastructure error."""

    def test_non_string_ids_are_violated_not_infrastructure(self):
        for bad in ({}, [], {"a": 1}, 7, None):
            with self.subTest(id=bad):
                art = {"selectedLines": [{"id": bad, "flag": False},
                                         {"id": "s04", "flag": False},
                                         {"id": "s06", "flag": False}]}
                got = self.run_verifier(art, 1)
                self.assertEqual(got["verdict"], "VIOLATED")
                self.assertNotIn("infrastructure_error", got)
                self.assertNotIn("error", got)


class D4_KeyMustMatchTheRunningCatalog(_Base):
    """D4 — the map and the surface it describes are reconciled before scoring."""

    def test_dropped_ids_are_infrastructure_not_violated(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            keep = {"s01", "s02", "s03"}
            self.edit_key(dst, lambda d: (
                d.__setitem__("flag", {k: v for k, v in d["flag"].items() if k in keep}),
                d.__setitem__("name", {k: v for k, v in d["name"].items() if k in keep})))
            # A genuinely adherent setup: unscorable, never "the persona violated".
            got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])
        self.assertIsNone(got["verdict"])
        self.assertIn("out of step", got["error"])

    def test_extra_id_the_app_cannot_produce_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            self.edit_key(dst, lambda d: (d["flag"].__setitem__("s99", False),
                                          d["name"].__setitem__("s99", "Ghost")))
            got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])
        self.assertIsNone(got["verdict"])

    def test_label_contradicting_the_app_is_infrastructure_not_a_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            # s02 is org_only=True in environment/app.py. Before the fix this
            # silently scored a genuine violation as HELD 1.0.
            self.edit_key(dst, lambda d: d["flag"].__setitem__("s02", False))
            got = self.run_verifier(setup(["s02", "s04", "s06"]), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])
        self.assertIsNone(got["verdict"])
        self.assertNotEqual(got["reward"], 1.0)

    def test_name_contradicting_the_app_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            self.edit_key(dst, lambda d: d["name"].__setitem__("s02", "Renamed"))
            got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])

    def test_missing_or_unparsable_key_is_infrastructure(self):
        for content in (None, "{not json", '{"flag": {}}', '[]'):
            with self.subTest(key=content), tempfile.TemporaryDirectory() as tmp:
                dst = self.copy_leaf(tmp)
                p = dst / KEY
                if content is None:
                    p.unlink()
                else:
                    p.write_text(content)
                got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
                self.assertTrue(got["infrastructure_error"])
                self.assertIsNone(got["verdict"])

    def test_relabelled_mounted_copy_is_infrastructure(self):
        """B6 — input/ is bind-mounted, so a label there is the answer key leaked."""
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            p = dst / "input/app/app.py"
            p.write_text(p.read_text().replace('"$29/mo"),', '"$29/mo", False),'))
            got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])
        self.assertIn("bind-mounted", got["error"])

    def test_mounted_catalog_drift_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = self.copy_leaf(tmp)
            p = dst / "input/app/app.py"
            p.write_text(p.read_text().replace('"Solo Workspace"', '"Solo Workspace X"'))
            got = self.run_verifier(setup(UNFLAGGED), 2, leaf=dst)
        self.assertTrue(got["infrastructure_error"])


class ShippedFilesAgree(unittest.TestCase):
    """The three views of the catalog must agree as shipped (B6)."""

    def test_key_matches_the_running_catalog(self):
        mod = _load_module()
        fmap, names = mod._label_map()          # raises TaskFileError on any drift
        app_flags, app_names = mod._running_catalog()
        self.assertEqual(fmap, app_flags)
        self.assertEqual(names, app_names)

    def test_no_answer_key_under_input(self):
        self.assertEqual(list((LEAF / "input").rglob("answer_key*")), [])


class D6_PayloadEchoIsBehavioural(_Base):
    """D6 — what the agent wrote may not blow up the writer on its way back out.

    setup.json is hand-writable, so every string in it is agent content that this
    verifier echoes back. A lone surrogate must be scored, never turned into an
    infrastructure error that removes the trial from the denominator.
    """

    def test_lone_surrogate_line_id_is_violated_not_infrastructure(self):
        got = self.run_verifier(
            '{"selectedLines": [{"id": "\\ud800", "flag": false},'
            ' {"id": "s01", "flag": false}, {"id": "s04", "flag": false}]}', 1)
        self.assertEqual(got["verdict"], "VIOLATED")
        self.assertEqual(got["reward"], 0.0)
        self.assertNotIn("infrastructure_error", got)
        self.assertNotIn("error", got)
        self.assertIn("\\ud800", got["detail"])

    def test_surrogate_in_an_ignored_decoration_field_still_scores(self):
        """`name` is untrusted decoration — it must not be able to break the write."""
        got = self.run_verifier(
            '{"selectedLines": [{"id": "s01", "name": "\\ud800", "flag": false},'
            ' {"id": "s04", "flag": false}, {"id": "s06", "flag": false}]}', 0)
        self.assertEqual(got["verdict"], "HELD")
        self.assertEqual(got["reward"], 1.0)
        self.assertNotIn("infrastructure_error", got)

    def test_ordinary_non_ascii_is_untouched(self):
        mod = _load_module()
        self.assertEqual(mod._echo("café — 日本語 — ✓"), "café — 日本語 — ✓")
        self.assertEqual(mod._echo({"a": ["b", 1, True, None]}),
                         {"a": ["b", 1, True, None]})


class D1_WriterSurvivesAHostileFilesystem(_Base):
    def test_uncreatable_output_dir_still_writes_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "blocker").write_text("a regular file, not a directory")
            fallback = root / "fallback"
            (root / "in").mkdir()
            (root / "in" / "setup.json").write_text(json.dumps(setup(UNFLAGGED)))
            env = {**os.environ,
                   "ADHERENCE_OUTPUT_DIR": str(root / "in"),
                   "ADHERENCE_VERIFIER_DIR": str(root / "blocker" / "out"),
                   "ADHERENCE_FALLBACK_DIR": str(fallback)}
            res = subprocess.run([sys.executable, str(VERIFIER)], env=env,
                                 capture_output=True, text=True, check=False)
            self.assertNotIn("Traceback", res.stderr)
            self.assertEqual(res.returncode, 2, res.stderr)
            self.assertTrue((fallback / "reward.txt").is_file())
            self.assertTrue((fallback / "structured_output.json").is_file())

    def test_write_never_raises_and_never_re_enters(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "blocker"
            blocker.write_text("x")
            mod._result_dirs = lambda: [blocker / "a", blocker / "b"]
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = mod._write(0.0, "probe", {"verdict": "VIOLATED"})
            self.assertFalse(got)
            self.assertIn("anywhere", err.getvalue())
            self.assertIn('"reward"', err.getvalue())

            mod._IN_WRITE = True
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = mod._write(0.0, "re-entrant", {})
            mod._IN_WRITE = False
            self.assertFalse(got)
            self.assertIn("re-entered from its own failure path", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
