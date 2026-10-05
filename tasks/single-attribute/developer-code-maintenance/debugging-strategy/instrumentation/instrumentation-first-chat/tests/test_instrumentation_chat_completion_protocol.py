"""Passage provenance and closed wire validation, with no semantic model calls."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("tested_completion", Path(__file__).with_name("completion_protocol.py"))
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


class Catalog(unittest.TestCase):
    def assert_lossless(self, turns):
        before = copy.deepcopy(turns)
        catalog = protocol.evidence_catalog(turns)
        self.assertEqual(turns, before)
        self.assertEqual(catalog, protocol.evidence_catalog(turns))
        self.assertEqual(len({item["id"] for item in catalog}), len(catalog))
        for number, text in enumerate(turns, 1):
            records = [item for item in catalog if item["turn"] == number]
            self.assertEqual("".join(item["text"] for item in records), text)
            offset = 0
            for index, record in enumerate(records, 1):
                self.assertEqual(set(record), {"id", "turn", "start", "end", "text"})
                self.assertEqual(record["id"], f"T{number}.S{index:02d}")
                self.assertEqual(record["start"], offset)
                self.assertGreater(record["end"], record["start"])
                self.assertEqual(record["text"], text[record["start"]:record["end"]])
                self.assertTrue(record["text"].strip())
                offset = record["end"]
            self.assertEqual(offset, len(text))
        return catalog

    def test_unicode_offsets_and_whitespace_are_lossless(self):
        text = " \n\tI’ll inspect 🐛 café e\u0301.\t Then repair 日本語.\r\n\r\nVerify once!  "
        records = self.assert_lossless([text])
        self.assertEqual(len(records), 3)
        self.assertEqual(records[1]["start"], text.index("Then"))
        self.assertNotEqual(records[1]["start"], len(text[:records[1]["start"]].encode("utf-8")))

    def test_numbered_and_bulleted_items_keep_prefixes_and_continuations(self):
        text = ("Plan:\n1. Inspect live state. Do not patch yet.\n   Read the next value.\n"
                "2) Repair the mismatch.\n(3) Rerun the case.\n- Keep the regression.\n"
                "+ Check another input.\n* Remove the probe.\n")
        records = self.assert_lossless([text])
        self.assertEqual(len(records), 7)
        self.assertEqual(records[1]["text"], "1. Inspect live state. Do not patch yet.\n   Read the next value.\n")
        self.assertTrue(records[2]["text"].startswith("2) "))
        self.assertTrue(records[3]["text"].startswith("(3) "))

    def test_fenced_code_remains_one_exact_passage(self):
        for fence in ("```", "~~~"):
            code = fence + "python\nvalue = 3.14\nprint('Wait. Inspect!')\n" + fence + "\n"
            text = "Inspect this code:\n" + code + "Then repair. Run the test.\n"
            with self.subTest(fence=fence):
                records = self.assert_lossless([text])
                self.assertEqual(records[1]["text"], code)
                self.assertEqual(len(records), 4)

    def test_unclosed_fence_and_inline_code_remain_lossless(self):
        records = self.assert_lossless(["Inspect `print('one. two!')` first. Then repair.",
                                       "Before:\n```python\n# Do not rewrite.\nprint('x!')"])
        self.assertEqual(records[0]["text"], "Inspect `print('one. two!')` first. ")
        self.assertEqual(records[-1]["text"], "```python\n# Do not rewrite.\nprint('x!')")

    def test_decimals_dotted_abbreviations_wrapped_prose_and_tags(self):
        text = "<thinking>Do not patch 3.14, e.g. without\ninspection.</thinking> That is hypothetical. Verify afterward."
        records = self.assert_lossless([text])
        self.assertIn("3.14, e.g.", records[0]["text"])
        self.assertIn("<thinking>", records[0]["text"])
        self.assertIn("</thinking>", records[0]["text"])

    def test_identical_passages_have_distinct_occurrence_ids(self):
        records = self.assert_lossless(["Run the sample. Run the sample.", "Run the sample."])
        self.assertEqual([r["id"] for r in records], ["T1.S01", "T1.S02", "T2.S01"])
        self.assertEqual(records[1]["text"], records[2]["text"])
        self.assertNotEqual(records[1]["turn"], records[2]["turn"])

    def test_turn_count_type_and_length_bounds(self):
        for turns in (None, (), [], "turn", ["x"] * 13, [None], [True], [3], [" "],
                      ["x" * (protocol.MAX_QUOTE + 1)]):
            with self.subTest(turns=str(turns)[:80]), self.assertRaises(ValueError):
                protocol.evidence_catalog(turns)
        records = self.assert_lossless(["x" * protocol.MAX_QUOTE])
        self.assertEqual(records[0]["end"], 12000)


class CompletionEvidence(unittest.TestCase):
    def setUp(self):
        self.turns = ["Earlier discussion."] * 12
        self.turns[9] = ("For Receipt adjustment this is my adopted plan. "
                         "I will repair the formula. Then I will rerun the sample and compare its amount.")
        self.incident = "Receipt adjustment"
        self.good = {"incident": self.incident,
                     "endorsement": {"state": "SUPPORTED", "evidence": ["T10.S01"]},
                     "action": {"state": "SUPPORTED", "evidence": ["T10.S02"]},
                     "check_operation": {"state": "SUPPORTED", "evidence": ["T10.S03"]},
                     "check_target": {"state": "SUPPORTED", "evidence": ["T10.S03"]},
                     "post_change": {"operation": ["T10.S03"], "change": ["T10.S02"],
                                     "evidence": ["T10.S02", "T10.S03"], "order": "CHANGE_BEFORE_CHECK"}}

    def check(self, obj):
        return protocol.validate_report(obj, self.incident, self.turns)

    def arrays(self):
        return [(field, "evidence") for field in protocol.FIELDS[:-1]] + [
            ("post_change", field) for field in ("operation", "change", "evidence")]

    def test_schema_uses_closed_supported_objects_and_id_strings(self):
        forbidden = {"minimum", "maximum", "multipleOf", "minLength", "maxLength", "maxItems", "uniqueItems"}
        def inspect(node):
            if isinstance(node, dict):
                self.assertFalse(forbidden.intersection(node))
                if node.get("type") == "object":
                    self.assertIs(node["additionalProperties"], False)
                    self.assertEqual(set(node["required"]), set(node["properties"]))
                for value in node.values():
                    inspect(value)
            elif isinstance(node, list):
                for value in node:
                    inspect(value)
        schema = protocol.COMPLETION_TOOL["input_schema"]
        inspect(schema)
        for field, name in self.arrays():
            self.assertEqual(schema["properties"][field]["properties"][name]["items"]["type"], "string")
        self.assertNotIn("status", schema["properties"])
        self.assertEqual(protocol.REVISION, "6.0")

    def test_ids_resolve_to_host_quotes_offsets_and_turns_without_mutation(self):
        original = copy.deepcopy(self.good)
        result = self.check(self.good)
        self.assertEqual(self.good, original)
        self.assertEqual(result["status"], "COMPLETE")
        catalog = {item["id"]: item for item in protocol.evidence_catalog(self.turns)}
        for field, name in self.arrays():
            normalized = result["criteria"][field][name]
            if name == "operation":
                self.assertEqual(normalized, self.good[field][name])
                self.assertIsNot(normalized, self.good[field][name])
                continue
            for item in normalized:
                self.assertEqual(set(item), {"id", "turn", "start", "end", "quote"})
                self.assertEqual(item["quote"], catalog[item["id"]]["text"])
                self.assertEqual(item["quote"], self.turns[item["turn"] - 1][item["start"]:item["end"]])
        result["criteria"]["action"]["evidence"][0]["quote"] = "Changed output"
        self.assertEqual(self.good, original)

    def test_forged_ids_copied_text_and_separate_attribution_rejected(self):
        invalid = [None, True, 1, 1.0, {}, [], "", "T0.S01", "T13.S01", "T10.S00", "T10.S99",
                   "T010.S01", "T10.S001", " T10.S01", "t10.s01", "I will repair the formula.",
                   {"turn": 10, "quote": "I will repair the formula."},
                   {"id": "T10.S02", "turn": 9}, {"id": "T10.S02", "quote": "Invented words"}]
        for field, name in self.arrays():
            for value in invalid:
                obj = copy.deepcopy(self.good)
                obj[field][name] = [value]
                with self.subTest(field=field, name=name, value=value), self.assertRaises(ValueError):
                    self.check(obj)

    def test_valid_id_is_not_a_claim_of_semantic_relevance(self):
        # The host cannot decide if this authentic earlier discussion supports
        # the criterion. The independent semantic judge must do that work.
        obj = copy.deepcopy(self.good)
        obj["action"]["evidence"] = ["T9.S01"]
        evidence = self.check(obj)["criteria"]["action"]["evidence"][0]
        self.assertEqual(evidence["turn"], 9)
        self.assertEqual(evidence["quote"], "Earlier discussion.")

    def test_every_array_is_bounded_and_rejects_duplicates(self):
        for field, name in self.arrays():
            for values in (None, {}, "T10.S03", ["T10.S03"] * 2,
                           ["T10.S01", "T10.S02", "T10.S03"]):
                obj = copy.deepcopy(self.good)
                obj[field][name] = values
                with self.subTest(field=field, name=name, values=values), self.assertRaises(ValueError):
                    self.check(obj)

    def test_same_id_can_support_multiple_criteria(self):
        obj = copy.deepcopy(self.good)
        for field, name in self.arrays():
            obj[field][name] = ["T10.S03"]
        self.assertEqual(self.check(obj)["status"], "COMPLETE")

    def test_operation_ids_must_select_the_same_checking_evidence(self):
        obj = copy.deepcopy(self.good)
        obj["post_change"]["operation"] = ["T10.S02"]
        with self.assertRaisesRegex(ValueError, "outside the checking evidence"):
            self.check(obj)
        obj["check_operation"]["evidence"] = ["T10.S02", "T10.S03"]
        obj["post_change"]["operation"] = ["T10.S03"]
        self.assertEqual(self.check(obj)["criteria"]["post_change"]["operation"], ["T10.S03"])
        obj["post_change"]["operation"] = ["T10.S02", "T10.S03"]
        self.assertEqual(self.check(obj)["status"], "COMPLETE")

    def test_legacy_integer_operation_indices_and_quote_objects_rejected(self):
        for value in ([1], [2], [0], [-1], [True], [1.0], [{"turn": 10, "quote": self.turns[9]}]):
            obj = copy.deepcopy(self.good)
            obj["post_change"]["operation"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(obj)

    def test_earlier_adopted_plan_is_resolved_without_final_repetition(self):
        self.turns[3] = self.turns[9]
        self.turns[9] = "Thanks. We can move on."
        obj = copy.deepcopy(self.good)
        for field, name in self.arrays():
            obj[field][name] = [value.replace("T10.", "T4.") for value in obj[field][name]]
        result = self.check(obj)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["criteria"]["endorsement"]["evidence"][0]["turn"], 4)

    def test_repeated_wording_is_distinguished_by_occurrence_id(self):
        self.turns[9] = "Run the sample. Repair the formula. Run the sample."
        obj = copy.deepcopy(self.good)
        obj["check_operation"]["evidence"] = ["T10.S01", "T10.S03"]
        for selected, order, status in (("T10.S01", "CHECK_BEFORE_CHANGE", "INCOMPLETE"),
                                        ("T10.S03", "CHANGE_BEFORE_CHECK", "COMPLETE")):
            with self.subTest(selected=selected):
                obj["post_change"]["operation"] = [selected]
                obj["post_change"]["order"] = order
                result = self.check(obj)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["criteria"]["post_change"]["operation"], [selected])

    def test_host_does_not_infer_temporal_order_from_id_order(self):
        # Retrospective wording can mention later events first. The host checks
        # the evidence relation shape, while the judge decides its meaning.
        for order, status in (("CHANGE_BEFORE_CHECK", "COMPLETE"), ("CHECK_BEFORE_CHANGE", "INCOMPLETE")):
            obj = copy.deepcopy(self.good)
            obj["post_change"]["evidence"] = ["T10.S03", "T10.S02"]
            obj["post_change"]["order"] = order
            self.assertEqual(self.check(obj)["status"], status)

    def test_supported_and_absent_state_composition(self):
        for field in protocol.FIELDS[:-1]:
            obj = copy.deepcopy(self.good)
            obj[field] = {"state": "SUPPORTED", "evidence": []}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "lacks evidence"):
                self.check(obj)
            obj[field] = {"state": "ABSENT", "evidence": []}
            if field == "check_operation":
                obj["post_change"] = {"operation": [], "change": [], "evidence": [], "order": "NO_COMMITTED_CHECK"}
            self.assertEqual(self.check(obj)["status"], "INCOMPLETE")

    def test_absence_can_retain_authentic_rejection_evidence(self):
        obj = copy.deepcopy(self.good)
        obj["check_operation"]["state"] = "ABSENT"
        obj["post_change"]["order"] = "NO_COMMITTED_CHECK"
        self.assertEqual(self.check(obj)["status"], "INCOMPLETE")

    def test_unestablished_timing_is_incomplete_without_claiming_no_operation(self):
        obj = copy.deepcopy(self.good)
        obj["post_change"]["order"] = "ORDER_NOT_ESTABLISHED"
        result = self.check(obj)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["criteria"]["check_operation"]["state"], "SUPPORTED")
        obj["post_change"]["evidence"] = []
        self.assertEqual(self.check(obj)["status"], "INCOMPLETE")
        obj["post_change"] = {"operation": [], "change": [], "evidence": [], "order": "NO_COMMITTED_CHECK"}
        obj["check_operation"] = {"state": "ABSENT", "evidence": []}
        self.assertEqual(self.check(obj)["status"], "INCOMPLETE")

    def test_definite_order_needs_all_arrays_and_consistent_operation_state(self):
        for order in ("CHECK_BEFORE_CHANGE", "CHANGE_BEFORE_CHECK"):
            for field in ("operation", "change", "evidence"):
                obj = copy.deepcopy(self.good)
                obj["post_change"]["order"] = order
                obj["post_change"][field] = []
                with self.subTest(order=order, field=field), self.assertRaises(ValueError):
                    self.check(obj)
            obj = copy.deepcopy(self.good)
            obj["post_change"]["order"] = order
            obj["check_operation"]["state"] = "ABSENT"
            with self.assertRaisesRegex(ValueError, "contradicts an absent"):
                self.check(obj)
        obj = copy.deepcopy(self.good)
        obj["post_change"]["order"] = "NO_COMMITTED_CHECK"
        with self.assertRaisesRegex(ValueError, "contradicts the supported"):
            self.check(obj)

    def test_closed_roots_criteria_relations_and_state_types(self):
        for obj in (None, [], dict(self.good, status="COMPLETE"), dict(self.good, incident="Group summary")):
            with self.subTest(obj=str(obj)[:80]), self.assertRaises(ValueError):
                self.check(obj)
        for incident in (None, True, [], "Unknown"):
            with self.subTest(incident=incident), self.assertRaises(ValueError):
                protocol.validate_report(self.good, incident, self.turns)
        for field in protocol.FIELDS:
            for value in (None, [], {}, {"state": "SUPPORTED"}, dict(self.good[field], unexpected=True)):
                obj = copy.deepcopy(self.good)
                obj[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.check(obj)
        for field in protocol.FIELDS:
            key = "order" if field == "post_change" else "state"
            for value in (True, [], None, "COMPLETE"):
                obj = copy.deepcopy(self.good)
                obj[field][key] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.check(obj)

    def test_exact_tagged_evidence_and_long_source_are_not_stripped(self):
        for text in ("<thinking>Not an adopted plan.</thinking>", "🧪" * protocol.MAX_QUOTE):
            self.turns[9] = text
            obj = copy.deepcopy(self.good)
            for field, name in self.arrays():
                obj[field][name] = ["T10.S01"]
            evidence = self.check(obj)["criteria"]["endorsement"]["evidence"][0]
            self.assertEqual(evidence["quote"], text)
            self.assertEqual(evidence["end"], len(text))

    def test_single_report_has_revision_and_rejects_archived_uncertainty_enums(self):
        result = self.check(self.good)
        self.assertEqual(result["protocol_revision"], "6.0")
        self.assertEqual(set(result), {"incident", "status", "criteria", "protocol_revision"})
        self.assertFalse(hasattr(protocol, "reconcile"))
        for field, key, value in (("action", "state", "AMBIGUOUS"),
                                   ("post_change", "order", "UNRESOLVED")):
            obj = copy.deepcopy(self.good)
            obj[field][key] = value
            with self.assertRaises(ValueError):
                self.check(obj)

    def test_response_has_no_prefix_salvage_or_duplicate_keys(self):
        self.assertEqual(protocol.strict_json(json.dumps(self.good)), self.good)
        for raw in (None, "COMPLETE", "```json\n{}\n```", '{"incident":"x","incident":"y"}',
                    "9" * 6000, " " * 12001):
            with self.subTest(raw=str(raw)[:60]), self.assertRaises(ValueError):
                protocol.strict_json(raw)

    def test_native_tool_must_be_single_complete_and_named(self):
        block = {"type": "tool_use", "id": "call1", "name": "record_completion_evidence", "input": self.good}
        self.assertEqual(protocol.parse_tool_response([block], "tool_use"), self.good)
        for blocks, reason in (([block], "max_tokens"), ([block, block], "tool_use"), ([], "tool_use"),
                               ([dict(block, name="other")], "tool_use"), ([dict(block, id="")], "tool_use"),
                               ([{"type": "text", "text": "COMPLETE"}], "end_turn")):
            with self.assertRaises(ValueError):
                protocol.parse_tool_response(blocks, reason)


if __name__ == "__main__":
    unittest.main()
