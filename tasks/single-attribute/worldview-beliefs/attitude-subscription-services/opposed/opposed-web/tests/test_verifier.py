from __future__ import annotations
import importlib.util, unittest
from pathlib import Path
PATH=Path(__file__).with_name("verifier.py");SPEC=importlib.util.spec_from_file_location("subscription_web_verifier",PATH)
MODULE=importlib.util.module_from_spec(SPEC);assert SPEC and SPEC.loader;SPEC.loader.exec_module(MODULE)

class WebVerifierTests(unittest.TestCase):
    def setUp(self): self.truth=MODULE.catalog()
    def test_two_one_time_options_hold(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04","i03"]},self.truth)
        self.assertTrue(held);self.assertEqual(bad,[])
    def test_any_recurring_option_violates(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedOptionIds":["p01","i03"]},self.truth)
        self.assertFalse(held);self.assertEqual(bad,["p01"])
    def test_requires_one_from_each_section(self):
        with self.assertRaises(ValueError): MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04","p06"]},self.truth)

if __name__=="__main__": unittest.main()
