"""Freeze inputs without gold labels; explicitly execute at most 24 single judge calls.

Default invocation only freezes. --execute consumes that freeze once. This runner
collects production completion decisions and never evaluates them against golds.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile

TASK = Path(__file__).resolve().parents[1]
REPO = next(p for p in TASK.parents if (p / 'evaluation/src').is_dir())
MAX_CASES = 24
MAX_REQUESTS = MAX_CASES
MAX_BYTES = 16_000_000
FINAL_TURNS = {'Receipt adjustment': 10, 'Group summary': 11, 'Duplicate normalization': 12}
SETTINGS = {'protocol_revision': '6.0', 'completion_calls_per_case': 1, 'retry_failed_cases': False}
PROVENANCE_LIMITS = {'suite_id': 256, 'created_by': 256, 'purpose': 4000}
PROVENANCE_FLAG = 'created_without_access_to_revised_prompt'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def parse_inputs(data):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ValueError('Input exceeds bounded byte limit')
    try:
        obj = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError('Invalid bounded input JSON') from exc
    required = {'construct_version', 'cases'}
    allowed = required | set(PROVENANCE_LIMITS) | {PROVENANCE_FLAG}
    if not isinstance(obj, dict) or not required <= set(obj) <= allowed:
        raise ValueError('Inputs contain missing or unexpected fields; no gold fields are allowed')
    for key, limit in PROVENANCE_LIMITS.items():
        if key in obj and (not isinstance(obj[key], str) or not obj[key].strip() or len(obj[key]) > limit):
            raise ValueError('Invalid bounded input provenance string')
    if PROVENANCE_FLAG in obj and type(obj[PROVENANCE_FLAG]) is not bool:
        raise ValueError('Input provenance access flag must be boolean')
    if type(obj['construct_version']) is not int or obj['construct_version'] != 3:
        raise ValueError('Expected construct_version 3')
    cases = obj['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError('Expected one through 24 cases')
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'incident', 'assigned_final_turn', 'persona_turns'}:
            raise ValueError('Each case needs only id, incident, assigned_final_turn and persona_turns')
        identifier = case['id']
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', identifier) or identifier in seen:
            raise ValueError('Invalid or duplicate case id')
        seen.add(identifier)
        incident = case['incident']
        if not isinstance(incident, str) or incident not in FINAL_TURNS:
            raise ValueError('Unknown incident')
        if type(case['assigned_final_turn']) is not int or case['assigned_final_turn'] != FINAL_TURNS[incident]:
            raise ValueError('Assigned final turn does not match production agenda')
        turns = case['persona_turns']
        if not isinstance(turns, list) or len(turns) != 12:
            raise ValueError('Each case requires all twelve persona turns')
        for index, turn in enumerate(turns, 1):
            if not isinstance(turn, dict) or set(turn) != {'turn', 'text'}:
                raise ValueError('Each persona turn needs exactly turn and text')
            if type(turn['turn']) is not int or turn['turn'] != index:
                raise ValueError('Persona turns must be numbered one through twelve')
            text = turn['text']
            if not isinstance(text, str) or not text.strip() or len(text) > 12_000:
                raise ValueError('Invalid bounded persona turn text')
    return cases


def read_bounded(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Input exceeds bounded byte limit')
    return data


def write_new(path, value):
    data = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # Persist directory entries where supported; files are fsynced on Windows too.
    if os.name != 'nt':
        descriptor = os.open(str(Path(path).parent), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def source_paths():
    family = REPO / 'tasks/single-attribute/developer-code-maintenance/debugging-strategy'
    relative = ['task.toml', 'persona.yaml', 'instruction.md', 'input/bot.md', 'input/context.md',
                'input/agenda.json', 'solution/agenda.py', 'solution/run_chat.py', 'solution/solve.sh',
                'tests/verifier.py', 'tests/judge_protocol.py', 'tests/completion_protocol.py',
                'tests/rubric.md', 'tests/completion_rubric.md',
                'tests/criteria_checks.py']
    paths = [family / leaf / name for leaf in ('interactive-debugger/debugger-first-chat',
              'instrumentation/instrumentation-first-chat') for name in relative]
    paths.extend([family / 'interactive-debugger/debugger-first-chat/tests/test_debugger_chat_criteria_checks.py',
                  family / 'instrumentation/instrumentation-first-chat/tests/test_instrumentation_chat_criteria_checks.py'])
    # Explicit production files only in tasks: never enumerate case/gold fixtures.
    paths.extend(p for p in (REPO / 'evaluation/src').rglob('*.py') if '__pycache__' not in p.parts)
    paths.extend([REPO / 'evaluation/run_task.py', REPO / 'evaluation/configs/judge.json'])
    return sorted(set(paths))


def snapshot_sources():
    files = {p.relative_to(REPO).as_posix(): p.read_bytes() for p in source_paths()}
    return {name: digest(data) for name, data in files.items()}, files


def runtime():
    versions = {}
    for package in ('anthropic', 'openai', 'pydantic', 'httpx'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(), 'packages': versions}


def resolve_judge():
    sys.path.insert(0, str(REPO / 'evaluation/src'))
    import judge
    resolved = judge.resolve()
    from urllib.parse import urlsplit
    endpoint = urlsplit(resolved.base_url)
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError('Judge endpoint must not contain credentials or query data')
    return resolved


def judge_metadata(resolved):
    """Whitelist shared resolver fields; never serialize tokens or arbitrary extras."""
    value = resolved._asdict()
    if set(value) != {'model', 'provider', 'base_url', 'source'}:
        raise ValueError('Unexpected judge metadata fields')
    if any(not isinstance(item, str) or len(item) > 2048 for item in value.values()):
        raise ValueError('Invalid bounded judge metadata')
    if not value['model'].strip() or not value['provider'].strip():
        raise ValueError('Judge metadata requires a model and provider')
    if any(re.search(r'(?i)(?:\bsk-[A-Za-z0-9_-]{12,}|\bbearer\s+\S+)', item) for item in value.values()):
        raise ValueError('Judge metadata must not contain credentials')
    from urllib.parse import urlsplit
    endpoint = urlsplit(value['base_url'])
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError('Judge endpoint must not contain credentials or query data')
    return value


def production():
    """Load this task's modules without reloading another task's cached verifier."""
    missing = object()
    names = ('completion_protocol', 'judge_protocol', 'verifier')
    previous = {name: sys.modules.get(name, missing) for name in names}
    previous_path = list(sys.path)
    modules = {}
    try:
        sys.path.insert(0, str(REPO / 'evaluation/src'))
        for name in names:
            spec = importlib.util.spec_from_file_location(name, TASK / 'tests' / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            modules[name] = module
        import usage
        return modules['verifier'], modules['judge_protocol'], usage
    finally:
        sys.path[:] = previous_path
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def freeze(inputs, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    hashes, files = snapshot_sources()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as target:
        for name, data in files.items():
            target.writestr(name, data)
    # Source bytes and lock are durable BEFORE the supplied input path is opened.
    write_new(output / 'sources.zip', archive.getvalue())
    write_new(output / 'source-lock.json', {'files': hashes, 'archive_sha256': digest(archive.getvalue())})
    if snapshot_sources()[0] != hashes:
        raise ValueError('Production source changed during freeze')
    data = read_bounded(inputs)
    cases = parse_inputs(data)
    write_new(output / 'inputs.json', data)
    resolved = resolve_judge()
    result = {'construct_version': 3, 'settings': dict(SETTINGS), 'runtime': runtime(),
              'judge': judge_metadata(resolved), 'inputs_sha256': digest(data), 'input_bytes': len(data),
              'case_count': len(cases), 'max_requests': len(cases),
              'reasoning_effort_override': os.environ.get('LLM_REASONING_EFFORT', ''),
              'source_lock_sha256': digest((output / 'source-lock.json').read_bytes()),
              'purpose': 'Single-judge production completion collection; no gold labels or semantic acceptance gate.'}
    write_new(output / 'freeze.json', result)
    return result


class RequestRecord(dict):
    """Persist the actual task-client request before its provider invocation."""
    def __init__(self, path, initial):
        super().__init__(initial)
        self.path = path

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == 'request':
            write_new(self.path, value)


def execute(inputs, output):
    output = Path(output)
    frozen = json.loads((output / 'freeze.json').read_text(encoding='utf-8'))
    lock_bytes = (output / 'source-lock.json').read_bytes()
    lock = json.loads(lock_bytes)
    if digest(lock_bytes) != frozen['source_lock_sha256'] or digest((output / 'sources.zip').read_bytes()) != lock['archive_sha256']:
        raise ValueError('Source archive or lock changed after freeze')
    def verify_sources():
        if snapshot_sources()[0] != lock['files']:
            raise ValueError('Production source changed after freeze')
    verify_sources()
    data = read_bounded(inputs)
    if data != (output / 'inputs.json').read_bytes() or digest(data) != frozen['inputs_sha256']:
        raise ValueError('Input bytes changed after freeze')
    cases = parse_inputs(data)
    budget = len(cases)
    if frozen['construct_version'] != 3 or frozen['settings'] != SETTINGS or frozen['case_count'] != len(cases) or type(frozen['max_requests']) is not int or frozen['max_requests'] != budget or not 1 <= budget <= MAX_REQUESTS:
        raise ValueError('Frozen request budget or settings are invalid')
    if frozen.get('reasoning_effort_override', '') != os.environ.get('LLM_REASONING_EFFORT', ''):
        raise ValueError('Judge reasoning effort changed after freeze')
    if frozen['runtime'] != runtime():
        raise ValueError('Runtime changed after freeze')
    resolved = resolve_judge()
    if judge_metadata(resolved) != frozen['judge']:
        raise ValueError('Judge resolution changed after freeze')
    if (output / 'execution.json').exists() or (output / 'calls').exists():
        raise ValueError('Execution evidence already exists; retries and overwrite are forbidden')
    write_new(output / 'execution-started.json', {'started_at': time.time(), 'max_requests': budget})
    calls_dir = output / 'calls'
    calls_dir.mkdir()
    state = {'status': 'collecting', 'judge_invocations': 0, 'max_requests': budget, 'cases': [], 'usage': {}}
    usage = None
    judge_env = {'LLM_CALL_ROLE': 'judge', 'ADHERENCE_JUDGE_MODEL': resolved.model,
                 'ADHERENCE_JUDGE_PROVIDER': resolved.provider,
                 'ADHERENCE_JUDGE_BASE_URL': resolved.base_url}
    previous_env = {key: os.environ.get(key) for key in judge_env}
    os.environ.update(judge_env)
    try:
        verifier, protocol, usage = production()
        verify_sources()
        usage.reset()
        for case_index, case in enumerate(cases, 1):
            calls = []
            def call(stage, system, payload):
                verify_sources()
                expected = 'completion/' + case['incident']
                if calls or stage != expected or state['judge_invocations'] >= budget:
                    raise ValueError('Single-judge request budget or stage violated')
                state['judge_invocations'] += 1
                number = state['judge_invocations']
                stem = calls_dir / f'{number:03d}'
                item = RequestRecord(Path(str(stem) + '-request.json'), {
                    'number': number, 'case_index': case_index, 'case_id': case['id'], 'stage': stage,
                    'model': resolved.model, 'provider': resolved.provider, 'system_prompt': system,
                    'payload': payload, 'payload_sha256': digest(payload.encode()), 'raw': None, 'usage': []})
                write_new(Path(str(stem) + '-intent.json'), dict(item))
                first_usage = len(usage.CALL_LOG)
                try:
                    result = protocol.call_judge(resolved, system, payload, item)
                    if not item.path.is_file():
                        raise ValueError('Production transport did not persist an exact request')
                    item['parsed'] = result
                    calls.append(number)
                    return result
                except Exception as exc:
                    item['error_type'] = type(exc).__name__
                    raise
                finally:
                    item['usage'] = list(usage.CALL_LOG[first_usage:])
                    item['system_sha256'] = digest(item['system_prompt'].encode())
                    write_new(Path(str(stem) + '-response.json'), dict(item))
            turns = [turn['text'] for turn in case['persona_turns']]
            decision = verifier.assess_completion(turns, case['incident'], call)
            if len(calls) != 1:
                raise ValueError('Production completion did not produce exactly one call')
            row = {'case_id': case['id'], 'incident': case['incident'], 'calls': calls, 'completion': decision}
            write_new(output / f'case-{case_index:03d}.json', row)
            state['cases'].append(row)
        state['status'] = 'collected'
    except Exception as exc:
        state['status'] = 'stopped'
        state['error_type'] = type(exc).__name__
        state['failed_case_index'] = len(state['cases']) + 1
    finally:
        for key, old in previous_env.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        state['usage'] = usage.summary() if usage is not None else {}
        write_new(output / 'execution.json', state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Explicitly consume an existing frozen schedule once')
    args = parser.parse_args()
    result = execute(args.inputs, args.output) if args.execute else freeze(args.inputs, args.output)
    print(json.dumps({key: result[key] for key in ('status', 'case_count', 'max_requests', 'judge_invocations') if key in result}))
    return 3 if result.get('status') == 'stopped' else 0


if __name__ == '__main__':
    raise SystemExit(main())
