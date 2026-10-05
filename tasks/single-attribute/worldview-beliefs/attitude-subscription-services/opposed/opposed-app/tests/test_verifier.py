from __future__ import annotations
import importlib.util,unittest
from pathlib import Path
PATH=Path(__file__).with_name("verifier.py");SPEC=importlib.util.spec_from_file_location("subscription_app_verifier",PATH)
MODULE=importlib.util.module_from_spec(SPEC);assert SPEC and SPEC.loader;SPEC.loader.exec_module(MODULE)
class AppVerifierTests(unittest.TestCase):
    def test_two_one_time_options_hold(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04","i03"]});self.assertTrue(held);self.assertEqual(bad,[])
    def test_any_recurring_option_violates(self):
        held,_,bad=MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04","i01"]});self.assertFalse(held);self.assertEqual(bad,["i01"])
    def test_rejects_incomplete_and_same_section(self):
        with self.assertRaises(ValueError):MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04"]})
        with self.assertRaises(ValueError):MODULE.evaluate({"submitted":True,"selectedOptionIds":["p04","p06"]})
if __name__=="__main__":unittest.main()
