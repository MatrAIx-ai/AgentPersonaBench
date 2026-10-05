#!/usr/bin/env python3
"""Regression tests for the label-free App artifact and host-only answer key."""
import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")
SPEC = importlib.util.spec_from_file_location("task_verifier", VERIFIER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CATALOG = MODULE._catalog()
LABELS, _ = MODULE._label_map(CATALOG)
POSITIVE = [row for item_id, row in CATALOG.items() if LABELS[item_id]]
NEGATIVE = [row for item_id, row in CATALOG.items() if not LABELS[item_id]]


def artifact(entries):
    ids = [entry["id"] for entry in entries]
    return {"persona": MODULE.PERSONA, MODULE.LIST_KEY: entries,
            "events": [*({"action": "select", "id": item_id} for item_id in ids),
                       {"action": "submit", "ids": ids}]}


class AppVerifierTests(unittest.TestCase):
    def run_verifier(self, payload, *, raw=False, leaf=None, expected_code=None):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            (output / MODULE.FNAME).write_text(
                payload if raw else json.dumps(payload), encoding="utf-8")
            verifier = (leaf / "tests" / "verifier.py") if leaf else VERIFIER
            env = dict(os.environ, ADHERENCE_OUTPUT_DIR=td,
                       ADHERENCE_VERIFIER_DIR=td)
            proc = subprocess.run([sys.executable, str(verifier)], env=env,
                                  capture_output=True, text=True, check=False)
            self.assertNotIn("Traceback", proc.stderr)
            if expected_code is not None:
                self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            result = json.loads((output / "structured_output.json").read_text())
            return proc.returncode, (output / "reward.txt").read_text().strip(), result

    def copy_leaf(self, root):
        leaf = Path(root) / MODULE._TASK.name
        shutil.copytree(MODULE._TASK, leaf, ignore=shutil.ignore_patterns("__pycache__"))
        return leaf

    def test_held_and_violated_directions(self):
        got = self.run_verifier(artifact(POSITIVE[:3]))
        self.assertEqual((got[0], got[1], got[2]["verdict"]), (0, "1.0", "HELD"))
        got = self.run_verifier(
            artifact([POSITIVE[0], POSITIVE[1], NEGATIVE[0]]))
        self.assertEqual((got[0], got[1], got[2]["verdict"]), (1, "0.0", "VIOLATED"))

    def test_tampered_or_self_labelled_rows_fail_closed(self):
        renamed = deepcopy(POSITIVE[:3])
        renamed[0]["name"] = "forged display name"
        labelled = deepcopy(POSITIVE[:3])
        labelled[0]["target"] = True
        for entries in (renamed, labelled):
            with self.subTest(entries=entries):
                code, reward, result = self.run_verifier(artifact(entries))
                self.assertEqual((code, reward, result["verdict"]),
                                 (1, "0.0", "VIOLATED"))
                self.assertNotIn("error", result)

    def test_impossible_event_history_fails_closed(self):
        payload = artifact(POSITIVE[:3])
        payload["events"][-1]["ids"].reverse()
        got = self.run_verifier(payload)
        self.assertEqual((got[0], got[1], got[2]["verdict"]),
                         (1, "0.0", "VIOLATED"))

    def test_malformed_artifacts_are_behavioral(self):
        cases = [artifact([POSITIVE[0]]), artifact(POSITIVE[:2]), artifact(POSITIVE),
                 artifact([POSITIVE[0], POSITIVE[0], POSITIVE[1]]),
                 artifact([{"id": "unknown", "name": "Unknown"},
                           POSITIVE[0], POSITIVE[1]]),
                 artifact([{"id": [], "name": "bad"}, POSITIVE[0], POSITIVE[1]]),
                 {"persona": MODULE.PERSONA, MODULE.LIST_KEY: POSITIVE[:3]},
                 {"persona": "wrong", MODULE.LIST_KEY: POSITIVE[:3], "events": []}, []]
        for payload in cases:
            with self.subTest(payload=repr(payload)[:80]):
                code, reward, result = self.run_verifier(payload)
                self.assertEqual((code, reward, result["verdict"]),
                                 (1, "0.0", "VIOLATED"))
                self.assertNotIn("error", result)

    def test_invalid_json_and_lone_surrogate_are_behavioral(self):
        hostile = ('{"persona":"x","' + MODULE.LIST_KEY + '":'
                   '[{"id":"\\ud800","name":"bad"}],"events":[]}')
        for payload in ("{broken", "[]", '"text"', hostile):
            code, reward, result = self.run_verifier(payload, raw=True)
            self.assertEqual((code, reward, result["verdict"]),
                             (1, "0.0", "VIOLATED"))
            self.assertNotIn("error", result)

    def test_missing_malformed_and_drifted_key_are_infrastructure(self):
        def drop_id(data):
            item_id = next(iter(data["label"]))
            data["label"].pop(item_id)
            data["name"].pop(item_id)

        def add_id(data):
            data["label"]["ghost"] = False
            data["name"]["ghost"] = "Ghost"

        def rename(data):
            data["name"][next(iter(data["name"]))] = "Drifted"

        def unbalance(data):
            item_id = next(i for i, value in data["label"].items() if value)
            data["label"][item_id] = False

        for content, mutation in ((None, None), ("{bad", None), (None, drop_id),
                                  (None, add_id), (None, rename), (None, unbalance)):
            with self.subTest(content=content, mutation=getattr(mutation, "__name__", None)), \
                    tempfile.TemporaryDirectory() as td:
                leaf = self.copy_leaf(td)
                key = leaf / "tests" / "answer_key.json"
                if content is not None:
                    key.write_text(content)
                elif mutation is None:
                    key.unlink()
                else:
                    data = json.loads(key.read_text())
                    mutation(data)
                    key.write_text(json.dumps(data))
                _, reward, result = self.run_verifier(
                    artifact(POSITIVE[:3]), leaf=leaf, expected_code=2)
                self.assertEqual(reward, "0.0")
                self.assertTrue(result["infrastructure_error"])
                self.assertIsNone(result["verdict"])

    def test_exposed_catalog_drift_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as td:
            leaf = self.copy_leaf(td)
            source = leaf / MODULE.INPUT_SRC.relative_to(MODULE._TASK)
            source.write_text(source.read_text().replace(
                POSITIVE[0]["name"], POSITIVE[0]["name"] + " X", 1))
            _, _, result = self.run_verifier(
                artifact(POSITIVE[:3]), leaf=leaf, expected_code=2)
        self.assertTrue(result["infrastructure_error"])

    def test_shipped_catalogs_are_identical_and_label_free(self):
        self.assertEqual(MODULE.APP_SRC.read_bytes(), MODULE.INPUT_SRC.read_bytes())
        self.assertEqual(list((MODULE._TASK / "input").rglob("answer_key*")), [])
        for source in (MODULE.APP_SRC, MODULE.INPUT_SRC):
            tree = ast.parse(source.read_text())
            menu = next(node for node in tree.body if isinstance(node, ast.Assign)
                        and any(getattr(target, "id", None) == "MENU" for target in node.targets))
            rows = ast.literal_eval(menu.value)
            self.assertTrue(all(len(row) == 5 and all(isinstance(v, str) for v in row)
                                for row in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
