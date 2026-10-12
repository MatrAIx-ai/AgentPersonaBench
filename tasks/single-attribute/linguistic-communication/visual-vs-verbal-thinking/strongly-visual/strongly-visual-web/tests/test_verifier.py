import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("verifier",Path(__file__).with_name("verifier.py"));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class TestVerifier(unittest.TestCase):
    def test_held(self): self.assertTrue(v.evaluate({"submitted":True,"selectedBookId":"b07","selectedWorkbookId":"w03"})[0])
    def test_violated_book(self): self.assertFalse(v.evaluate({"submitted":True,"selectedBookId":"b01","selectedWorkbookId":"w03"})[0])
    def test_violated_workbook(self): self.assertFalse(v.evaluate({"submitted":True,"selectedBookId":"b07","selectedWorkbookId":"w01"})[0])
    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):v.evaluate({"submitted":True,"selectedBookId":"b99","selectedWorkbookId":"w03"})
    def test_unknown_workbook_rejected(self):
        with self.assertRaises(ValueError):v.evaluate({"submitted":True,"selectedBookId":"b07","selectedWorkbookId":"w99"})
    def test_unsubmitted_rejected(self):
        with self.assertRaises(ValueError):v.evaluate({"submitted":False,"selectedBookId":"b07","selectedWorkbookId":"w03"})
if __name__=="__main__":unittest.main()
