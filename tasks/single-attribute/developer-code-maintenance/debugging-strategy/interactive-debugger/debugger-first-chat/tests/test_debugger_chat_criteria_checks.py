"""No-model runner checks using only generic toy turns, never sealed fixtures."""
from contextlib import ExitStack
from collections import namedtuple
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

TESTS = Path(__file__).resolve().parent
REAL_REPO = next(p for p in TESTS.parents if (p / 'evaluation/src').is_dir())
_spec = importlib.util.spec_from_file_location(__name__ + "_runner", TESTS / "criteria_checks.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)
verifier, judge_protocol, _ = runner.production()
completion_protocol = verifier.completion_protocol
SOURCE_PATHS = runner.source_paths
RESOLVE_JUDGE = runner.resolve_judge
TEST_MODEL = "toy-configured-model"


def toy_inputs(count=1):
    incident = 'Receipt adjustment'
    return {'construct_version': 3, 'cases': [
        {'id': f'TOY_GOLD_ID_MUST_NOT_ENTER_PROMPT_{i}', 'incident': incident,
         'assigned_final_turn': 10,
         'persona_turns': [{'turn': n, 'text': f'Toy persona turn {n}.'} for n in range(1, 13)]}
        for i in range(count)]}


def toy_report(incident='Receipt adjustment', state='ABSENT'):
    citation = 'T10.S01'
    return {'incident': incident, **{field: {'state': state, 'evidence': [] if state == 'ABSENT' else [citation]}
                                    for field in completion_protocol.FIELDS[:-1]},
            'post_change': {
                'operation': [] if state == 'ABSENT' else [citation],
                'change': [] if state == 'ABSENT' else [citation],
                'evidence': [] if state == 'ABSENT' else [citation],
                'order': {'ABSENT': 'NO_COMMITTED_CHECK', 'SUPPORTED': 'CHANGE_BEFORE_CHECK'}[state],
            }}


class ToyUsage:
    def __init__(self):
        self.CALL_LOG = []

    def reset(self):
        self.CALL_LOG.clear()

    def summary(self):
        return {'calls': len(self.CALL_LOG)} if self.CALL_LOG else {}


class CriteriaRunnerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.source = self.root / 'production.py'
        self.source.write_text('VALUE = 1\n')
        self.inputs = self.root / 'toy-inputs.json'
        self.output = self.root / 'frozen'
        self.inputs.write_text(json.dumps(toy_inputs()))
        self.stack.enter_context(patch.object(runner, 'REPO', self.root))
        self.stack.enter_context(patch.object(runner, 'source_paths', return_value=[self.source]))
        judge = namedtuple('Judge', 'model provider base_url source')(TEST_MODEL, 'anthropic', '', 'toy')
        self.stack.enter_context(patch.object(runner, 'resolve_judge', return_value=judge))
        self.stack.enter_context(patch.object(runner, 'runtime', return_value={'python': 'toy-runtime'}))
        self.usage = ToyUsage()
        self.calls = []

    def test_real_source_inventory_tracks_both_renamed_test_modules(self):
        with patch.object(runner, "REPO", REAL_REPO):
            paths = SOURCE_PATHS()
        self.assertTrue(all(path.is_file() for path in paths))
        names = {path.name for path in paths}
        self.assertIn("test_debugger_chat_criteria_checks.py", names)
        self.assertIn("test_instrumentation_chat_criteria_checks.py", names)
        self.assertNotIn("test_criteria_checks.py", names)
        self.assertFalse(any("cases" in path.name or "gold" in path.name for path in paths
                             if "tasks" in path.parts))

    def test_production_loads_own_modules_and_restores_foreign_cache(self):
        foreign = {name: SimpleNamespace(marker="another task")
                   for name in ("verifier", "judge_protocol", "completion_protocol")}
        with patch.object(runner, "REPO", REAL_REPO), patch.dict(sys.modules, foreign):
            own_verifier, own_protocol, _ = runner.production()
            self.assertEqual(Path(own_verifier.__file__).parent, TESTS)
            self.assertEqual(Path(own_protocol.__file__).parent, TESTS)
            self.assertEqual(Path(own_verifier.completion_protocol.__file__).parent, TESTS)
            self.assertIs(own_protocol.completion_protocol, own_verifier.completion_protocol)
            for name, value in foreign.items():
                self.assertIs(sys.modules[name], value)

    def freeze(self, count=1):
        self.inputs.write_text(json.dumps(toy_inputs(count)))
        return runner.freeze(self.inputs, self.output)

    def fake_protocol(self, state='ABSENT', fail_on=None, mutate_after=None):
        def call_judge(resolved, system, payload, item):
            number = len(self.calls) + 1
            if number > 1:
                previous = self.output / 'calls' / f'{number - 1:03d}-response.json'
                self.assertTrue(previous.is_file(), 'Previous raw response must be durable before the next call')
                self.assertIn('usage', json.loads(previous.read_text()))
            item['system_prompt'] = system + '\nToy transport suffix.'
            item['request_tool'] = completion_protocol.COMPLETION_TOOL
            item['request'] = {'transport': 'toy', 'model': resolved.model, 'system': item['system_prompt'], 'payload': payload}
            self.assertTrue(item.path.is_file(), 'Exact request must be saved before provider invocation')
            self.calls.append({'system': system, 'payload': payload})
            if number == fail_on:
                item['provider_error'] = {'exception_type': 'ToyProviderError', 'status_code': 400}
                raise RuntimeError('sensitive SDK exception must not be copied')
            raw = toy_report(state=state)
            item['raw'] = [{'type': 'tool_use', 'name': 'record_completion_evidence', 'id': f'toy-{number}', 'input': raw}]
            item['stop_reason'] = 'tool_use'
            item['response_model'] = TEST_MODEL
            self.usage.CALL_LOG.append({'model': TEST_MODEL, 'prompt_tokens': 3, 'completion_tokens': 2})
            if number == mutate_after:
                self.source.write_text('VALUE = 2\n')
            return raw
        return SimpleNamespace(call_judge=call_judge)

    def execute(self, **kwargs):
        with patch.object(runner, 'production', return_value=(verifier, self.fake_protocol(**kwargs), self.usage)):
            return runner.execute(self.inputs, self.output)

    def test_source_archive_is_durable_before_input_read(self):
        original = runner.read_bounded
        def checked_read(path):
            self.assertTrue((self.output / 'source-lock.json').is_file())
            with zipfile.ZipFile(self.output / 'sources.zip') as archive:
                self.assertEqual(archive.read('production.py'), self.source.read_bytes())
            return original(path)
        with patch.object(runner, 'read_bounded', side_effect=checked_read), patch.object(runner, 'production') as production:
            frozen = runner.freeze(self.inputs, self.output)
        production.assert_not_called()
        self.assertEqual(frozen['max_requests'], 1)
        self.assertEqual((self.output / 'inputs.json').read_bytes(), self.inputs.read_bytes())

    def test_strict_input_schema_rejects_gold_and_invalid_fields(self):
        variants = []
        for key in ('expected', 'gold', 'gold_labels'):
            obj = toy_inputs(); obj[key] = 'FORBIDDEN'; variants.append(obj)
            obj = toy_inputs(); obj['cases'][0][key] = 'FORBIDDEN'; variants.append(obj)
            obj = toy_inputs(); obj['cases'][0]['persona_turns'][0][key] = 'FORBIDDEN'; variants.append(obj)
        obj = toy_inputs(); obj['construct_version'] = True; variants.append(obj)
        obj = toy_inputs(); obj['cases'][0]['assigned_final_turn'] = 11; variants.append(obj)
        obj = toy_inputs(); obj['cases'][0]['persona_turns'][0]['turn'] = True; variants.append(obj)
        obj = toy_inputs(); obj['cases'][0]['persona_turns'].pop(); variants.append(obj)
        obj = toy_inputs(); obj['cases'][0]['persona_turns'][0]['text'] = 'x' * 12001; variants.append(obj)
        obj = toy_inputs(2); obj['cases'][1]['id'] = obj['cases'][0]['id']; variants.append(obj)
        variants.extend([toy_inputs(0), toy_inputs(25)])
        for obj in variants:
            with self.subTest(keys=list(obj)):
                with self.assertRaises(ValueError):
                    runner.parse_inputs(json.dumps(obj).encode())
        for raw in (b'{"construct_version":3,"construct_version":3,"cases":[]}', b'[' * 10000):
            with self.assertRaises(ValueError):
                runner.parse_inputs(raw)

    def test_optional_provenance_is_bounded_and_never_added_to_prompts(self):
        obj = toy_inputs()
        obj.update({'suite_id': 'TOY_PROVENANCE_SENTINEL', 'created_by': 'generic test author',
                    'created_without_access_to_revised_prompt': True, 'purpose': 'Generic schema test.'})
        self.assertEqual(runner.parse_inputs(json.dumps(obj).encode()), obj['cases'])
        self.inputs.write_text(json.dumps(obj))
        runner.freeze(self.inputs, self.output)
        result = self.execute()
        self.assertEqual(result['status'], 'collected')
        for request in self.calls:
            self.assertNotIn('TOY_PROVENANCE_SENTINEL', request['system'] + request['payload'])
        for field, limit in runner.PROVENANCE_LIMITS.items():
            for invalid in (None, True, '', 'x' * (limit + 1)):
                bad = copy.deepcopy(obj); bad[field] = invalid
                with self.subTest(field=field, kind=type(invalid).__name__), self.assertRaises(ValueError):
                    runner.parse_inputs(json.dumps(bad).encode())
        for invalid in (0, 1, 'true', None):
            bad = copy.deepcopy(obj); bad[runner.PROVENANCE_FLAG] = invalid
            with self.assertRaises(ValueError):
                runner.parse_inputs(json.dumps(bad).encode())
        bad = copy.deepcopy(obj); bad['expected'] = 'FORBIDDEN'
        with self.assertRaises(ValueError):
            runner.parse_inputs(json.dumps(bad).encode())

    def test_judge_metadata_whitelists_fields_and_rejects_credentials(self):
        clean = {'model': TEST_MODEL, 'provider': 'anthropic', 'base_url': '', 'source': 'toy'}
        self.assertEqual(runner.judge_metadata(SimpleNamespace(_asdict=lambda: clean)), clean)
        for extra in ('api_key', 'token', 'headers'):
            bad = dict(clean, **{extra: 'toy secret'})
            with self.assertRaisesRegex(ValueError, 'Unexpected judge metadata'):
                runner.judge_metadata(SimpleNamespace(_asdict=lambda: bad))
        for endpoint in ('https://user:password@example.test', 'https://example.test?token=secret',
                         'https://example.test/#secret', 'https://example.test/sk-ant-toycredential1234'):
            bad = dict(clean, base_url=endpoint)
            with self.assertRaises(ValueError):
                runner.judge_metadata(SimpleNamespace(_asdict=lambda: bad))

    def test_resolver_uses_shared_config_without_overriding_model_or_provider(self):
        configured = namedtuple('Judge', 'model provider base_url source')(
            'gpt-5.6-luna', 'openai', '', 'environment')
        calls = []
        def resolve(**kwargs):
            calls.append(kwargs)
            return configured
        with patch.dict(sys.modules, {'judge': SimpleNamespace(resolve=resolve)}):
            self.assertEqual(RESOLVE_JUDGE(), configured)
        self.assertEqual(calls, [{}])
        self.assertEqual(runner.judge_metadata(configured)['provider'], 'openai')

    def test_configured_openai_request_is_saved_before_call_and_environment_restored(self):
        configured = namedtuple('Judge', 'model provider base_url source')(
            'gpt-5.6-luna', 'openai', '', 'environment')
        sys.path.insert(0, str(REAL_REPO / 'evaluation/src'))
        import usage
        import llm_client
        requests = []
        def chat(**kwargs):
            saved = json.loads((self.output / 'calls/001-request.json').read_text())
            self.assertEqual(saved, {'transport': 'llm_client.chat', **kwargs})
            self.assertEqual(os.environ['LLM_CALL_ROLE'], 'judge')
            self.assertEqual(os.environ['ADHERENCE_JUDGE_MODEL'], 'gpt-5.6-luna')
            self.assertEqual(os.environ['ADHERENCE_JUDGE_PROVIDER'], 'openai')
            requests.append(kwargs)
            return json.dumps(toy_report())
        original = {'LLM_CALL_ROLE': 'actor', 'ADHERENCE_JUDGE_MODEL': 'original-model',
                    'ADHERENCE_JUDGE_PROVIDER': 'original-provider', 'LLM_REASONING_EFFORT': ''}
        with patch.dict(os.environ, original), patch.object(runner, 'resolve_judge', return_value=configured):
            frozen = self.freeze()
            self.assertEqual(frozen['judge']['model'], 'gpt-5.6-luna')
            with patch.object(llm_client, 'chat', side_effect=chat), patch.object(
                runner, 'production', return_value=(verifier, judge_protocol, usage)
            ):
                result = runner.execute(self.inputs, self.output)
            for key, value in original.items():
                self.assertEqual(os.environ[key], value)
        self.assertEqual(result['status'], 'collected')
        self.assertEqual(result['judge_invocations'], 1)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['max_tokens'], 16000)
        self.assertEqual(requests[0]['retries'], 1)
        self.assertEqual(result['cases'][0]['completion']['status'], 'INCOMPLETE')
        self.assertNotIn('reasoning_effort', requests[0])

    def test_freeze_and_execution_refuse_overwrite(self):
        self.freeze()
        before = (self.output / 'freeze.json').read_bytes()
        with self.assertRaises(FileExistsError):
            runner.freeze(self.inputs, self.output)
        self.assertEqual((self.output / 'freeze.json').read_bytes(), before)
        self.execute()
        response = (self.output / 'calls/001-response.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.execute()
        self.assertEqual((self.output / 'calls/001-response.json').read_bytes(), response)

    def test_source_change_blocks_execution_before_calls(self):
        self.freeze(); self.source.write_text('VALUE = 2\n')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_input_change_blocks_execution_before_calls(self):
        self.freeze(); self.inputs.write_text(json.dumps(toy_inputs(2)))
        with self.assertRaisesRegex(ValueError, 'Input bytes changed'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_runtime_and_budget_changes_block_calls(self):
        self.freeze()
        with patch.object(runner, 'runtime', return_value={'python': 'different'}):
            with self.assertRaisesRegex(ValueError, 'Runtime changed'):
                self.execute()
        frozen = json.loads((self.output / 'freeze.json').read_text())
        frozen['max_requests'] = 49
        (self.output / 'freeze.json').write_text(json.dumps(frozen))
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_collects_all_24_incomplete_cases_with_exact_24_call_cap(self):
        self.freeze(24)
        result = self.execute(state='ABSENT')
        self.assertEqual(result['status'], 'collected')
        self.assertEqual(result['judge_invocations'], 24)
        self.assertEqual(len(result['cases']), 24)
        self.assertTrue(all(row['completion']['status'] == 'INCOMPLETE' for row in result['cases']))
        self.assertEqual(len(list((self.output / 'calls').glob('*-request.json'))), 24)
        self.assertEqual(len(list((self.output / 'calls').glob('*-response.json'))), 24)

    def test_collects_one_relational_report_without_semantic_rewriting(self):
        self.freeze()
        result = self.execute(state='SUPPORTED')
        self.assertEqual(result['status'], 'collected')
        self.assertEqual(result['judge_invocations'], 1)
        report = result['cases'][0]['completion']
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['protocol_revision'], '6.0')
        expected = toy_report(state='SUPPORTED')['post_change']
        raw = json.loads((self.output / 'calls/001-response.json').read_text())
        self.assertEqual(raw['raw'][0]['input']['post_change'], expected)
        self.assertEqual(report['criteria']['post_change']['order'], expected['order'])
        self.assertEqual(report['criteria']['post_change']['operation'], expected['operation'])
        self.assertEqual(report['criteria']['post_change']['change'][0]['id'], expected['change'][0])
        self.assertEqual(raw['usage'], [{'model': TEST_MODEL, 'prompt_tokens': 3, 'completion_tokens': 2}])

    def test_long_authentic_passage_is_resolved_by_host_without_copying(self):
        inputs = toy_inputs()
        quote = "My intended correction and subsequent comparison" + " with generic context" * 30 + "."
        self.assertGreater(len(quote), 240)
        inputs["cases"][0]["persona_turns"][9]["text"] = quote
        self.inputs.write_text(json.dumps(inputs))
        runner.freeze(self.inputs, self.output)
        with patch.object(runner, "production", return_value=(verifier, self.fake_protocol(state="SUPPORTED"), self.usage)):
            result = runner.execute(self.inputs, self.output)
        self.assertEqual(result["status"], "collected")
        self.assertEqual(result["judge_invocations"], 1)
        report = result["cases"][0]["completion"]
        raw = json.loads((self.output / "calls/001-response.json").read_text())
        self.assertEqual(raw["raw"][0]["input"]["action"]["evidence"], ["T10.S01"])
        self.assertEqual(report["criteria"]["action"]["evidence"][0]["quote"], quote)

    def test_out_of_range_operation_reference_stops_after_retaining_the_actual_raw_response(self):
        self.freeze()
        protocol = self.fake_protocol(state='SUPPORTED')
        original = protocol.call_judge
        unlinked = 2
        def mismatched(*args):
            raw = original(*args)
            raw['post_change']['operation'] = [unlinked]
            return raw
        protocol.call_judge = mismatched
        with patch.object(runner, 'production', return_value=(verifier, protocol, self.usage)):
            result = runner.execute(self.inputs, self.output)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['judge_invocations'], 1)
        self.assertEqual(result['cases'], [])
        raw = json.loads((self.output / 'calls/001-response.json').read_text())
        self.assertEqual(raw['raw'][0]['input']['post_change']['operation'], [unlinked])
        self.assertEqual(len(raw['usage']), 1)
        self.assertFalse((self.output / 'calls/002-intent.json').exists())

    def test_case_ids_and_gold_files_never_enter_prompts_or_get_read(self):
        (self.root / 'gold-labels.json').write_text('SEALED_GOLD_SENTINEL')
        self.freeze()
        original = Path.open
        def no_gold_open(path, *args, **kwargs):
            if path.name == 'gold-labels.json':
                raise AssertionError('Gold file was opened')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', no_gold_open):
            result = self.execute()
        self.assertEqual(result['status'], 'collected')
        for call in self.calls:
            self.assertNotIn('TOY_GOLD_ID_MUST_NOT_ENTER_PROMPT', call['system'] + call['payload'])
            self.assertNotIn('SEALED_GOLD_SENTINEL', call['system'] + call['payload'])

    def test_provider_failure_stops_and_preserves_raw_partial_evidence(self):
        self.freeze(2)
        result = self.execute(fail_on=2)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['judge_invocations'], 2)
        self.assertEqual(len(result['cases']), 1)
        first = json.loads((self.output / 'calls/001-response.json').read_text())
        failed = json.loads((self.output / 'calls/002-response.json').read_text())
        self.assertIsNotNone(first['raw']); self.assertEqual(len(first['usage']), 1)
        self.assertEqual(failed['provider_error']['status_code'], 400)
        self.assertNotIn('sensitive SDK exception', json.dumps(failed))
        self.assertFalse((self.output / 'calls/003-intent.json').exists())

    def test_protocol_failure_stops_after_first_raw_response(self):
        self.freeze()
        protocol = self.fake_protocol()
        original = protocol.call_judge
        def malformed(*args):
            original(*args)
            return {'bad': 'protocol'}
        protocol.call_judge = malformed
        with patch.object(runner, 'production', return_value=(verifier, protocol, self.usage)):
            result = runner.execute(self.inputs, self.output)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['judge_invocations'], 1)
        self.assertTrue((self.output / 'calls/001-response.json').is_file())

    def test_source_change_between_calls_stops_without_retry(self):
        self.freeze(2)
        result = self.execute(mutate_after=1)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['judge_invocations'], 1)
        self.assertTrue((self.output / 'calls/001-response.json').is_file())

    def test_production_sdk_request_is_saved_before_call_with_zero_retries(self):
        self.freeze()
        sys.path.insert(0, str(REAL_REPO / 'evaluation/src'))
        import usage
        import llm_client
        actual_calls = []
        def create(**kwargs):
            number = len(actual_calls) + 1
            persisted = json.loads((self.output / f'calls/{number:03d}-request.json').read_text())
            self.assertEqual(kwargs, {key: persisted[key] for key in ('model', 'max_tokens', 'system', 'messages', 'tools', 'tool_choice')})
            self.assertEqual(kwargs['max_tokens'], 1800)
            self.assertNotIn('temperature', kwargs)
            actual_calls.append(kwargs)
            raw = {'type': 'tool_use', 'id': f'toy-{number}', 'name': 'record_completion_evidence', 'input': toy_report()}
            return SimpleNamespace(content=[SimpleNamespace(model_dump=lambda **unused: raw)], stop_reason='tool_use',
                model=TEST_MODEL, id=f'toy-response-{number}', usage=SimpleNamespace(input_tokens=3, output_tokens=2))
        def client(**kwargs):
            self.assertEqual(kwargs['max_retries'], 0)
            self.assertEqual(kwargs['timeout'], 60)
            return SimpleNamespace(messages=SimpleNamespace(create=create))
        with patch.dict(sys.modules, {'anthropic': SimpleNamespace(Anthropic=client)}), \
                patch.object(llm_client, 'load_token', return_value='toy-test-key'), \
                patch.object(runner, 'production', return_value=(verifier, judge_protocol, usage)):
            result = runner.execute(self.inputs, self.output)
        self.assertEqual(result['status'], 'collected')
        self.assertEqual(len(actual_calls), 1)
        self.assertEqual(result['usage']['calls'], 1)
        self.assertNotIn('toy-test-key', ''.join(p.read_text() for p in (self.output / 'calls').glob('*.json')))


if __name__ == '__main__':
    unittest.main()
