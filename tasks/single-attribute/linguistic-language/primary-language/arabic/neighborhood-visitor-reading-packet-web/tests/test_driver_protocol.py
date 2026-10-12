"""Real-browser driver regressions with stubbed replies, not model evidence."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('driver', ROOT/'solution/driver.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
VIEW = {'questions':[{'id':f'q{i}', 'options':[{'id':f'q{i}{c}'} for c in 'abcd']} for i in range(1,7)]}
VALID = json.dumps({'answers':[{'questionId':f'q{i}','selectedOptionId':f'q{i}a'} for i in range(1,7)]})

class ProtocolTests(unittest.TestCase):
    def test_wrapped_json_preserves_exact_choices(self):
        for text in (VALID, 'Here are my choices:\n'+VALID,
                     '```json\n'+VALID+'\n```', VALID+'\nThese are my choices.'):
            with self.subTest(text=text[:20]):
                self.assertEqual(driver.parse_choices(text,VIEW), {f'q{i}':f'q{i}a' for i in range(1,7)})

    def test_invalid_not_salvaged_or_filled(self):
        malformed = [VALID+VALID, 'I cannot choose.', '[]', '{"answers":[]}',
            '{"wrapper":'+VALID+'}', '{"answers":[],"answers":[]}',
            VALID.replace('q1a','q2a'), VALID.replace('q2','q1'),
            '['*5000+']'*5000, 'x'*256001,
            json.dumps({'answers':json.loads(VALID)['answers'][:-1]})]
        for text in malformed:
            with self.subTest(text=text[:30]), self.assertRaises((ValueError,RecursionError)):
                driver.parse_choices(text,VIEW)

    def invoke_main(self,reply=None,error=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        output = Path(temp.name)
        client = types.ModuleType('agent_client')
        def chat(**kwargs):
            if error: raise error
            return reply
        client.chat = chat
        with patch.dict(sys.modules, {'agent_client':client}), patch.dict(os.environ, {
            'ADHERENCE_OUTPUT_DIR':str(output), 'SITE_PATH':str(ROOT/'input/site/index.html'),
            'PERSONA_SYS':'Offline fixture; no persona or model call.'}), patch.object(sys,'argv',['driver.py']):
            if error:
                with self.assertRaises(type(error)): driver.main()
            else:
                driver.main()
        return output

    def test_unrecoverable_reply_finishes_with_empty_actual_receipt(self):
        for reply in ('I cannot choose.',json.dumps({'answers':json.loads(VALID)['answers'][:-1]})):
            with self.subTest(reply=reply[:20]):
                output=self.invoke_main(reply=reply)
                self.assertEqual(json.loads((output/'selection.json').read_text()), {'answers':[]})
                record=json.loads((output/'generation.json').read_text())
                self.assertEqual(record['raw_response'],reply)
                self.assertEqual([e['action'] for e in record['events']],['invalid_response'])
                self.assertIn('data-confirmed="false"',(output/'final.html').read_text())
                self.assertTrue((output/'trace.zip').stat().st_size)

    def test_wrapped_reply_executes_real_confirmation(self):
        output=self.invoke_main(reply='```json\n'+VALID+'\n```')
        self.assertEqual(json.loads((output/'selection.json').read_text()),json.loads(VALID))
        self.assertEqual(len(json.loads((output/'generation.json').read_text())['events']),7)

    def test_provider_failure_stays_infrastructure_failure(self):
        output=self.invoke_main(error=RuntimeError('fixture provider unavailable'))
        self.assertFalse((output/'selection.json').exists())
        self.assertTrue((output/'generation.json').exists())

if __name__=='__main__': unittest.main()
