import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("web_verifier", Path(__file__).with_name("verifier.py"))
verifier = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(verifier)


class WebVerifierTests(unittest.TestCase):
    def run_case(self, tool: str):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); out=root/"out"; vd=root/"verdict"; (out/"anchor").mkdir(parents=True)
            payload={"runTool":tool,"exportTool":tool,"exported":True,
                     "spec":{"outcome":"retention_score","predictor":"training_hours","controls":["department","tenure_years"]}}
            (out/"anchor"/"analysis.json").write_text(json.dumps(payload))
            with patch.dict(os.environ,{"ADHERENCE_OUTPUT_DIR":str(out),"ADHERENCE_VERIFIER_DIR":str(vd)}): verifier.main()
            return json.loads((vd/"structured_output.json").read_text())

    def test_stata_holds_both(self): self.assertEqual(self.run_case("stata")["score"],"2/2")
    def test_python_violates_both(self): self.assertEqual(self.run_case("python")["score"],"0/2")
    def test_spss_is_partial(self): self.assertEqual(self.run_case("spss")["score"],"1/2")


if __name__ == "__main__": unittest.main()
