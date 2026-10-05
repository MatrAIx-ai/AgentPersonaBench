"""No API calls: missing dependencies and hostile JSON must fail closed."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RuntimeSafety(unittest.TestCase):
    def probe(self,flags=(),content=None):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);out=base/'agent';out.mkdir();verdict=base/'verifier'
            if content is not None:
                for name in ('selection.json','survey_result.json'):(out/name).write_text(content,encoding='utf-8')
            run=subprocess.run([sys.executable,*flags,str(ROOT/'tests/verifier.py')],env=dict(os.environ,ADHERENCE_OUTPUT_DIR=str(out),ADHERENCE_VERIFIER_DIR=str(verdict)),capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,1,run.stderr);self.assertNotIn('Traceback',run.stderr)
            self.assertFalse((out/'reward.txt').exists());self.assertEqual((verdict/'reward.txt').read_text().strip(),'0.0')
            result=json.loads((verdict/'structured_output.json').read_text());self.assertEqual(result['verdict'],'VIOLATED');self.assertFalse(result['passed']);return result
    def test_missing_pyyaml_is_structured_infrastructure_failure(self):
        result=self.probe(('-I','-S'));self.assertEqual(result['status'],'infra_error');self.assertIn('ModuleNotFoundError',result['error'])
    def test_deep_json_is_structured_invalid_artifact(self):
        result=self.probe(content='['*5000+']'*5000);self.assertEqual(result['status'],'invalid_artifact')
if __name__=='__main__':unittest.main()
