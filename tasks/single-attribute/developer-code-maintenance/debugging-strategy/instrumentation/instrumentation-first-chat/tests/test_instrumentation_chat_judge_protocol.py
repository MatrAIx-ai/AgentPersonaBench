"""Structured output validation and native call wiring, without network calls."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

_local_spec = importlib.util.spec_from_file_location(__name__ + "_completion", Path(__file__).with_name("completion_protocol.py"))
_local_completion = importlib.util.module_from_spec(_local_spec)
_local_spec.loader.exec_module(_local_completion)
SPEC = importlib.util.spec_from_file_location("chat_judge_protocol", Path(__file__).with_name("judge_protocol.py"))
protocol = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {"completion_protocol": _local_completion}):
    SPEC.loader.exec_module(protocol)


class Protocol(unittest.TestCase):
    def good(self):
        return [{"type": "tool_use", "id": "tool_1", "name": "record_verdict", "input": {"verdict": "HELD"}}]

    def test_exact_tool(self):
        self.assertEqual(protocol.parse_tool_verdict(self.good(), "tool_use"), "HELD")
        other = self.good()
        other[0]["input"]["verdict"] = "VIOLATED"
        self.assertEqual(protocol.parse_tool_verdict(other, "tool_use"), "VIOLATED")

    def test_text_extra_and_duplicate_blocks_rejected(self):
        for blocks in ([], self.good() * 2, [{"type": "text", "text": "HELD"}],
                       self.good() + [{"type": "text", "text": "Because..."}]):
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                protocol.parse_tool_verdict(blocks, "tool_use")

    def test_malformed_tool_name_input_or_verdict_rejected(self):
        changes = (("name", "other"), ("id", ""), ("input", None), ("input", {"verdict": True}),
                   ("input", {"verdict": "HELD", "reason": "extra"}),
                   ("input", {"verdict": "not HELD"}), ("input", {"verdict": "held"}))
        for key, value in changes:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                item = self.good()
                item[0][key] = value
                protocol.parse_tool_verdict(item, "tool_use")

    def test_truncated_response_rejected_even_with_verdict(self):
        with self.assertRaises(ValueError):
            protocol.parse_tool_verdict(self.good(), "max_tokens")

    def test_forced_tool_call_and_usage(self):
        requests = []
        tokens = []
        block = self.good()[0]
        response = SimpleNamespace(content=[SimpleNamespace(model_dump=lambda **kw: copy.deepcopy(block))],
                                   stop_reason="tool_use", model="haiku", id="message_1")
        def create(**kwargs):
            requests.append(kwargs)
            return response
        fake_sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
        modules = {"anthropic": fake_sdk,
                   "llm_client": SimpleNamespace(load_token=lambda provider: "test-placeholder"),
                   "usage": SimpleNamespace(record_response=lambda *a, **kw: tokens.append((a, kw)))}
        resolved = SimpleNamespace(provider="anthropic", model="haiku", base_url="")
        item = {}
        with patch.dict(sys.modules, modules):
            self.assertEqual(protocol.call_judge(resolved, "Frozen semantic rubric", "Untrusted user data", item), "HELD")
        self.assertEqual(requests[0]["tool_choice"], {"type": "tool", "name": "record_verdict",
                                                     "disable_parallel_tool_use": True})
        self.assertEqual(requests[0]["tools"], [protocol.VERDICT_TOOL])
        self.assertEqual(requests[0]["max_tokens"], 128)
        self.assertNotIn("Untrusted user data", requests[0]["system"])
        self.assertEqual(len(tokens), 1)
        self.assertEqual(item["raw"], [block])

    def test_other_provider_keeps_strict_text_route(self):
        fake = SimpleNamespace(chat=lambda *a, **kw: "HELD")
        item = {}
        with patch.dict(sys.modules, {"llm_client": fake, "usage": SimpleNamespace()}):
            raw = protocol.call_judge(SimpleNamespace(provider="openai", model="other"), "rule", "data", item)
        self.assertEqual(raw, "HELD")
        self.assertEqual(item["protocol"], "strict-text-v1")

    def test_completion_uses_distinct_closed_tool_and_bounded_output(self):
        requests = []
        report = {"incident": "Receipt adjustment", **{
            field: {"state": "ABSENT", "evidence": []} for field in protocol.completion_protocol.FIELDS[:-1]},
            "post_change": {"operation": [], "change": [], "evidence": [], "order": "NO_COMMITTED_CHECK"}}
        block = {"type": "tool_use", "id": "call1", "name": "record_completion_evidence", "input": report}
        response = SimpleNamespace(content=[SimpleNamespace(model_dump=lambda **kw: block)],
                                   stop_reason="tool_use", model="haiku", id="message1")
        def create(**kw):
            requests.append(kw)
            return response
        modules = {"anthropic": SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create))),
                   "llm_client": SimpleNamespace(load_token=lambda *a: "test-placeholder"),
                   "usage": SimpleNamespace(record_response=lambda *a, **k: None)}
        item = {"stage": "completion/Receipt adjustment"}
        with patch.dict(sys.modules, modules):
            actual = protocol.call_judge(SimpleNamespace(provider="anthropic", model="haiku", base_url=""),
                                         "completion rules", "untrusted persona turns", item)
        self.assertEqual(actual, report)
        self.assertEqual(requests[0]["tools"], [protocol.completion_protocol.COMPLETION_TOOL])
        self.assertEqual(requests[0]["tool_choice"]["name"], "record_completion_evidence")
        self.assertEqual(requests[0]["max_tokens"], 1800)
        self.assertNotIn("untrusted persona turns", requests[0]["system"])
        self.assertEqual(item["protocol"], "anthropic-completion-criteria-v6.0")
        self.assertNotIn("status", requests[0]["tools"][0]["input_schema"]["properties"])
        relation_schema = requests[0]["tools"][0]["input_schema"]["properties"]["post_change"]
        self.assertEqual(set(relation_schema["required"]), {"operation", "change", "evidence", "order"})
        self.assertNotIn("state", relation_schema["properties"])
        self.assertEqual(relation_schema["properties"]["operation"]["items"]["type"], "string")

    def test_other_provider_uses_criteria_schema_and_bounded_json_route(self):
        requests = []
        report = {"incident": "Receipt adjustment", **{
            field: {"state": "ABSENT", "evidence": []} for field in protocol.completion_protocol.FIELDS[:-1]},
            "post_change": {"operation": [], "change": [], "evidence": [], "order": "NO_COMMITTED_CHECK"}}
        def chat(messages, **kwargs):
            requests.append((messages, kwargs))
            return json.dumps(report)
        item = {"stage": "completion/Receipt adjustment"}
        with patch.dict(sys.modules, {"llm_client": SimpleNamespace(chat=chat), "usage": SimpleNamespace()}):
            actual = protocol.call_judge(SimpleNamespace(provider="openai", model="other"),
                                         "completion rules", "untrusted persona turns", item)
        self.assertEqual(actual, report)
        self.assertEqual(item["protocol"], "strict-completion-json-v6.0")
        messages, options = requests[0]
        self.assertEqual(options["max_tokens"], 1800)
        self.assertEqual(options["temperature"], 0.0)
        self.assertEqual(messages[1], {"role": "user", "content": "untrusted persona turns"})
        self.assertNotIn("untrusted persona turns", messages[0]["content"])
        self.assertIn(json.dumps(protocol.completion_protocol.COMPLETION_TOOL["input_schema"]), messages[0]["content"])

    def test_other_provider_completion_rejects_prose_prefix(self):
        item = {"stage": "completion/Receipt adjustment"}
        with patch.dict(sys.modules, {"llm_client": SimpleNamespace(chat=lambda *a, **k: 'COMPLETE: {}'),
                                      "usage": SimpleNamespace()}):
            with self.assertRaises(ValueError):
                protocol.call_judge(SimpleNamespace(provider="openai", model="other"), "rules", "data", item)

    def test_provider_rejection_retains_only_sanitized_response_details(self):
        requests = []
        error = RuntimeError("unsafe exception text and request headers")
        error.status_code = 400
        error.body = {"error": {"type": "invalid_request_error", "message": "maxItems unsupported token-placeholder sk-ant-test Bearer fake-secret " + "x" * 2100},
                      "headers": {"x-api-key": "token-placeholder"}, "request": "never retain"}
        error.request_id = "request_123"
        def create(**kwargs):
            requests.append(kwargs)
            raise error
        modules = {"anthropic": SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create))),
                   "llm_client": SimpleNamespace(load_token=lambda *a: "token-placeholder"),
                   "usage": SimpleNamespace(record_response=lambda *a, **k: self.fail("failed request has no response usage"))}
        item = {"stage": "completion/Receipt adjustment"}
        with patch.dict(sys.modules, modules), self.assertRaises(RuntimeError):
            protocol.call_judge(SimpleNamespace(provider="anthropic", model="haiku", base_url=""), "rules", "data", item)
        details = item["provider_error"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(details["status_code"], 400)
        self.assertEqual(details["type"], "invalid_request_error")
        self.assertEqual(details["request_id"], "request_123")
        self.assertLessEqual(len(details["message"]), 2000)
        for forbidden in ("token-placeholder", "sk-ant-test", "fake-secret", "headers", "request", "unsafe exception text"):
            self.assertNotIn(forbidden, details["message"])
        self.assertEqual(set(details), {"exception_type", "status_code", "type", "message", "request_id"})
        self.assertEqual(item["request_tool"], protocol.completion_protocol.COMPLETION_TOOL)

    def test_luna_uses_shared_responses_with_reasoning_room_and_default_effort(self):
        import llm_client
        requests = []
        def create(**kwargs):
            requests.append(kwargs)
            return SimpleNamespace(status="completed", output_text="{}" if len(requests) == 1 else "HELD",
                                   usage=SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30))
        sdk = SimpleNamespace(OpenAI=lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(create=create)))
        env = {"LLM_PROVIDER": "openai", "LLM_CALL_ROLE": "judge",
               "ADHERENCE_JUDGE_PROVIDER": "openai", "ADHERENCE_JUDGE_MODEL": "gpt-5.6-luna",
               "LLM_REASONING_EFFORT": ""}
        for stage in ("completion/Receipt adjustment", "method/Receipt adjustment"):
            item = {"stage": stage}
            with patch.dict(sys.modules, {"openai": sdk}), patch.dict("os.environ", env), patch.object(
                llm_client, "load_token", return_value="test-placeholder"
            ):
                result = protocol.call_judge(SimpleNamespace(provider="openai", model="gpt-5.6-luna"),
                                             "Unchanged rubric", "Untrusted persona turns", item)
            self.assertEqual(result, {} if stage.startswith("completion/") else "HELD")
            self.assertEqual(item["max_tokens"], 16000)
            self.assertEqual(item["timeout_seconds"], 180)
        for request in requests:
            self.assertEqual(request["model"], "gpt-5.6-luna")
            self.assertEqual(request["max_output_tokens"], 16000)
            self.assertEqual(request["input"], [{"role": "user", "content": "Untrusted persona turns"}])
            self.assertTrue(request["instructions"].startswith("Unchanged rubric"))
            self.assertNotIn("temperature", request)
            self.assertNotIn("reasoning", request)
            self.assertFalse(request["store"])



if __name__ == "__main__":
    unittest.main()
