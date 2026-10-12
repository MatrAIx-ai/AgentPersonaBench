import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("verifier",Path(__file__).with_name("verifier.py"));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class TestVerifier(unittest.TestCase):
 viewed=[f"b{i:02d}" for i in range(1,9)]
 def test_held(self):self.assertTrue(v.evaluate({"submitted":True,"selectedBookId":"b07","viewedBookIds":self.viewed})[0])
 def test_violated(self):self.assertFalse(v.evaluate({"submitted":True,"selectedBookId":"b05","viewedBookIds":self.viewed})[0])
 def test_unknown_rejected(self):
  with self.assertRaises(ValueError):v.evaluate({"submitted":True,"selectedBookId":"bad","viewedBookIds":self.viewed})
 def test_unsubmitted_rejected(self):
  with self.assertRaises(ValueError):v.evaluate({"submitted":False,"selectedBookId":"b07","viewedBookIds":self.viewed})
 def test_incomplete_review_rejected(self):
  with self.assertRaises(ValueError):v.evaluate({"submitted":True,"selectedBookId":"b07","viewedBookIds":["b07"]})
if __name__=="__main__":unittest.main()
