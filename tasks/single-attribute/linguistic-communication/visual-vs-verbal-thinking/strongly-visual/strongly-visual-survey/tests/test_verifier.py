import importlib.util, unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("verifier", Path(__file__).with_name("verifier.py"))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
class TestVerifier(unittest.TestCase):
    def payload(self, ids): return {"answers": [{"questionId": f"q{i+1}", "selectedOptionId": oid} for i, oid in enumerate(ids)]}
    def test_held(self): self.assertTrue(v.evaluate(self.payload(["q1d","q2c","q3b","q4d","q5b","q6c"]))[0])
    def test_one_exception_still_held(self): self.assertTrue(v.evaluate(self.payload(["q1a","q2c","q3b","q4d","q5b","q6c"]))[0])
    def test_two_exceptions_violated(self): self.assertFalse(v.evaluate(self.payload(["q1a","q2a","q3b","q4d","q5b","q6c"]))[0])
    def test_incomplete_rejected(self):
        with self.assertRaises(ValueError): v.evaluate(self.payload(["q1d"]))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): v.evaluate({"answers":[{"questionId":"q1","selectedOptionId":"q1d"}]*6})
if __name__ == "__main__": unittest.main()
