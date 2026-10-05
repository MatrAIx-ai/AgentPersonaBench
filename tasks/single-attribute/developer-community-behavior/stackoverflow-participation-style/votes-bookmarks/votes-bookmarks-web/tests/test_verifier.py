from __future__ import annotations
import importlib.util, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

PATH=Path(__file__).with_name("verifier.py"); SPEC=importlib.util.spec_from_file_location("votes_bookmarks_web_verifier",PATH)
MODULE=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)


class WebVerifierTests(unittest.TestCase):
    def setUp(self): self.truth=MODULE.catalog()
    def test_votes_and_bookmarks_hold(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedActionIds":["a12","a22","a33","a44"]},self.truth)
        self.assertTrue(held); self.assertEqual(bad,[])
    def test_one_written_contribution_violates(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedActionIds":["a11","a22","a33","a44"]},self.truth)
        self.assertFalse(held); self.assertEqual(bad,["a11"])
    def test_two_written_contributions_violate(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedActionIds":["a11","a23","a33","a44"]},self.truth)
        self.assertFalse(held); self.assertEqual(bad,["a11","a23"])
    def test_partial_duplicate_unknown_and_wrong_thread_fail(self):
        for payload in (None, [], {"submitted":False,"selectedActionIds":["a12","a22","a33","a44"]},
                        {"submitted":True,"selectedActionIds":["a12"]},
                        {"submitted":True,"selectedActionIds":["a12","a12","a33","a44"]},
                        {"submitted":True,"selectedActionIds":["a12","a22","a33","bogus"]},
                        {"submitted":True,"selectedActionIds":["a12","a14","a33","a44"]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError): MODULE.evaluate(payload,self.truth)
    def test_malformed_artifact_fails_closed_and_writes_result(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); (out/"anchor").mkdir(); (out/"anchor/session.json").write_text("[]")
            with patch.dict(os.environ,{"ADHERENCE_OUTPUT_DIR":temp,"ADHERENCE_VERIFIER_DIR":temp}):
                with self.assertRaisesRegex(SystemExit,"1"): MODULE.main()
            result=json.loads((out/"structured_output.json").read_text())
            self.assertEqual(result["reward"],0.0); self.assertEqual(result["verdict"],"ERROR")


if __name__ == "__main__": unittest.main()
