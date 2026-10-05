from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.src.tools.task_doctor import (
    Report,
    _already_reported,
    _looks_like_label,
    _structural_labels,
    _walk_for_labels,
    check_input_no_labels,
)

DIMS = frozenset({"skill_budgeting", "val_sustainability"})


def _questionnaire(*options: str) -> str:
    """A one-question questionnaire whose options are the given `k: v` strings."""
    opts = "".join(f"      - {{{o}}}\n" for o in options)
    return "questions:\n  - id: q1\n    options:\n" + opts


def _yaml(text: str) -> Path:
    d = Path(tempfile.mkdtemp())
    p = d / "questionnaire.yaml"
    p.write_text(text, encoding="utf-8")
    return p


class LabelShapeTests(unittest.TestCase):
    """A ground-truth label is recognised by shape, not by the name it is given."""

    def test_bool_next_to_an_id_is_a_label_whatever_it_is_called(self) -> None:
        for key in ("flag", "animal", "eco", "keyed", "correct", "is_target"):
            with self.subTest(key=key):
                self.assertTrue(_looks_like_label(key, True, DIMS))

    def test_small_int_next_to_an_id_is_a_label(self) -> None:
        self.assertTrue(_looks_like_label("risk", 2, DIMS))
        self.assertTrue(_looks_like_label("score", 0, DIMS))

    def test_a_dimension_id_as_a_value_is_a_label(self) -> None:
        self.assertTrue(_looks_like_label("check", "skill_budgeting", DIMS))

    def test_presentation_keys_are_never_labels(self) -> None:
        for key, val in (("id", "q1a"), ("text", "Bottled water"),
                         ("price", 3), ("type", "single_choice"),
                         ("index", 2), ("value", True)):
            with self.subTest(key=key):
                self.assertFalse(_looks_like_label(key, val, DIMS))

    def test_unrelated_string_is_not_a_label(self) -> None:
        self.assertFalse(_looks_like_label("note", "cheaper and quicker", DIMS))

    def test_large_int_is_not_a_label(self) -> None:
        self.assertFalse(_looks_like_label("count", 1200, DIMS))


class WalkTests(unittest.TestCase):
    def test_label_is_only_flagged_inside_an_entry_that_has_an_id(self) -> None:
        doc = {"meta": {"draft": True},
               "questions": [{"id": "q1",
                              "options": [{"id": "q1a", "text": "A", "flag": True}]}]}
        found = _walk_for_labels(doc, DIMS)
        self.assertEqual([w for w, _ in found], ["questions[0].options[0].flag"])

    def test_clean_questionnaire_yields_nothing(self) -> None:
        doc = {"questions": [{"id": "q1", "prompt": "Pick one", "type": "single_choice",
                              "options": [{"id": "q1a", "text": "A"},
                                          {"id": "q1b", "text": "B"}]}]}
        self.assertEqual(_walk_for_labels(doc, DIMS), [])


class StructuralFileTests(unittest.TestCase):
    def test_yaml_with_a_custom_label_name_is_detected(self) -> None:
        p = _yaml(
            "questions:\n"
            "  - id: q1\n"
            "    prompt: Pick one\n"
            "    options:\n"
            "      - {id: q1a, text: A, flag: true}\n"
            "      - {id: q1b, text: B, flag: false}\n"
        )
        self.assertEqual(len(_structural_labels(p)), 2)

    def test_clean_yaml_is_silent(self) -> None:
        p = _yaml(
            "questions:\n"
            "  - id: q1\n"
            "    prompt: Pick one\n"
            "    options:\n"
            "      - {id: q1a, text: A}\n"
            "      - {id: q1b, text: B}\n"
        )
        self.assertEqual(_structural_labels(p), [])

    def test_json_is_handled_too(self) -> None:
        d = Path(tempfile.mkdtemp())
        p = d / "questionnaire.json"
        p.write_text(json.dumps(
            {"questions": [{"id": "q1",
                            "options": [{"id": "q1a", "text": "A", "keyed": 1}]}]}),
            encoding="utf-8")
        self.assertEqual(len(_structural_labels(p)), 1)

    def test_unparseable_file_is_skipped_rather_than_crashing(self) -> None:
        p = _yaml("this: is: not: valid: yaml:\n  - [\n")
        self.assertEqual(_structural_labels(p), [])


class ProseAnswerHintTests(unittest.TestCase):
    """A comment under input/ is read by the agent exactly like the data is."""

    def _hits(self, line: str) -> int:
        from evaluation.src.tools.task_doctor import _prose_answer_hints
        d = Path(tempfile.mkdtemp())
        p = d / "questionnaire.yaml"
        p.write_text(line + "\nquestions: []\n", encoding="utf-8")
        return len(_prose_answer_hints(p))

    def test_a_comment_that_identifies_the_keyed_option_is_a_leak(self) -> None:
        for line in ("# The keyed option is the most expensive choice in q3.",
                     "# persona-consistent picks are s01 and s04",
                     "# the flagged option is q1d",
                     "# correct answer is the first one"):
            with self.subTest(line=line):
                self.assertEqual(self._hits(line), 1)

    def test_saying_only_where_ground_truth_lives_is_not_a_leak(self) -> None:
        for line in ("# ground truth lives in tests/answer_key.yaml, never mounted",
                     "# data-flag is ground truth for the verifier; not shown",
                     "# Ground truth (which options are alcoholic) is NOT in this file"):
            with self.subTest(line=line):
                self.assertEqual(self._hits(line), 0)

    def test_ordinary_design_notes_and_option_text_pass(self) -> None:
        for line in ("# Non-sustainable options are deliberately cheaper",
                     "#   - {id: q1a, text: 'A 24-pack of bottled water'}"):
            with self.subTest(line=line):
                self.assertEqual(self._hits(line), 0)


class OpaqueOptionIdTests(unittest.TestCase):
    """Option ids are opaque by contract, so the scan reads the real ones.

    docs/05-CONTRACT.md: "option ids are opaque". Guessing a shape
    (`q<digits><letter>` / `<letter><two digits>`) missed every id that does not
    follow it — and merged tasks already use `apt_harbor`, `animals_one_dog`,
    `code_sample`, `visit_review`.
    """

    def _ids(self, text: str) -> tuple[str, ...]:
        from evaluation.src.tools.task_doctor import _declared_ids
        return _declared_ids([text])

    def _hits(self, doc: str, line: str) -> int:
        from evaluation.src.tools.task_doctor import _prose_answer_hints
        d = Path(tempfile.mkdtemp())
        p = d / "questionnaire.yaml"
        p.write_text(doc + "\n" + line + "\n", encoding="utf-8")
        return len(_prose_answer_hints(p, self._ids(p.read_text(encoding="utf-8"))))

    DOC = ("questions:\n"
           "  - id: intake\n"
           "    options:\n"
           "      - {id: option_a, text: A}\n"
           "      - {id: option_b, text: B}\n")

    def test_ids_are_parsed_out_of_the_document(self) -> None:
        self.assertEqual(self._ids(self.DOC), ("option_a", "option_b", "intake"))

    def test_html_and_json_id_declarations_are_parsed(self) -> None:
        self.assertIn("apt_harbor", self._ids(
            '<div class="item" data-id="apt_harbor" data-flag="true">'))
        self.assertIn("visit_review", self._ids('{"id": "visit_review"}'))

    def test_a_comment_naming_an_opaque_id_is_a_leak(self) -> None:
        for line in ("# correct answer is option_a",
                     "# the keyed option is `option_b`",
                     "# persona-consistent picks are option_a and option_b"):
            with self.subTest(line=line):
                self.assertEqual(self._hits(self.DOC, line), 1)

    def test_the_conventional_shapes_still_trip_without_declarations(self) -> None:
        from evaluation.src.tools.task_doctor import _prose_answer_re
        self.assertTrue(_prose_answer_re(()).search("# the flagged option is q1d"))
        self.assertTrue(_prose_answer_re(()).search("# the keyed option is s04"))

    def test_an_id_that_is_an_ordinary_word_is_not_used_as_a_needle(self) -> None:
        # otherwise the scan degenerates into a word search and starts
        # false-positiving on ordinary prose.
        self.assertEqual(self._ids("options:\n  - {id: no, text: N}\n"), ())

    def test_declared_ids_do_not_create_false_positives(self) -> None:
        for line in ("# ground truth for option_a lives in tests/answer_key.yaml",
                     "# option_a is deliberately the dearer of the two",
                     "#   - {id: option_a, text: 'Take the company seat'}"):
            with self.subTest(line=line):
                self.assertEqual(self._hits(self.DOC, line), 0)


class LeakSeverityTests(unittest.TestCase):
    """Each pass owns its severity, and CI gates on the exit code.

    Regression guard for review round 2 of PR #74: the WARN downgrade meant for
    the two NEW passes also covered the pre-existing named-key regex pass, so a
    questionnaire carrying an inline `animal: true` — the exact leak this checker
    exists to stop — reported a WARN and exited 0. CI runs the doctor per task
    and gates on that exit code (.github/workflows/ci.yml).
    """

    def _report(self, body: str, rel: str = "questionnaire.yaml") -> Report:
        d = Path(tempfile.mkdtemp())
        p = d / "input" / rel
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
        rep = Report()
        check_input_no_labels(d, rep)
        return rep

    @staticmethod
    def _severities(rep: Report) -> list[str]:
        return [status for status, _ in rep.rows]

    # `animal` is a key the regex knows; `flag` is one only the shape pass sees.
    KNOWN = _questionnaire("id: q1a, text: A, animal: true")
    SHAPE_ONLY = _questionnaire("id: q1a, text: A, flag: true")

    def test_a_known_label_key_fails_the_task(self) -> None:
        rep = self._report(self.KNOWN)
        self.assertEqual(self._severities(rep), ["FAIL"])
        self.assertTrue(rep.failed)          # -> exit 1, which CI gates on

    def test_a_shape_only_label_warns_but_does_not_fail(self) -> None:
        rep = self._report(self.SHAPE_ONLY)
        self.assertEqual(self._severities(rep), ["WARN"])
        self.assertFalse(rep.failed)

    def test_a_clean_questionnaire_passes(self) -> None:
        rep = self._report(_questionnaire("id: q1a, text: A", "id: q1b, text: B"))
        self.assertEqual(self._severities(rep), ["PASS"])
        self.assertFalse(rep.failed)

    def test_a_runtime_surface_only_warns(self) -> None:
        rep = self._report('<div class="p" data-id="p01" data-risk="0">',
                           rel="site/index.html")
        self.assertEqual(self._severities(rep), ["WARN"])
        self.assertFalse(rep.failed)

    def test_a_hit_both_passes_see_is_reported_once(self) -> None:
        # The regex pass reads the raw line ('animal: true'); the structural pass
        # reads the parsed value, whose repr is 'animal: True'. The dedupe must
        # fold the two spellings instead of reporting one label twice.
        rep = self._report(self.KNOWN)
        self.assertEqual(len(rep.rows), 1, rep.rows)
        self.assertNotIn("animal: True", rep.rows[0][1])

    def test_a_second_label_on_the_same_line_is_still_reported(self) -> None:
        rep = self._report(
            _questionnaire("id: q1a, text: A, animal: true, flag: true"))
        self.assertEqual(self._severities(rep), ["FAIL", "WARN"])

    def test_the_dedupe_does_not_fold_a_different_label(self) -> None:
        self.assertTrue(_already_reported("animal: True", ["animal: true"]))
        self.assertTrue(_already_reported("risk: 3", ['"risk":   3']))
        self.assertFalse(_already_reported("animal: 1", ["animal: 10"]))
        self.assertFalse(_already_reported("animal: true", ["is_animal: true"]))
        self.assertFalse(_already_reported("animal: False", ["animal: true"]))

    def test_the_overflow_line_carries_the_severity_of_its_own_hits(self) -> None:
        body = _questionnaire(*(f"id: q1{c}, text: A, animal: true"
                                for c in "abcdefghij"))
        rep = self._report(body)                       # 10 hits, printed cap is 8
        self.assertEqual(self._severities(rep), ["FAIL"] * 9)
        self.assertIn("and 2 more", rep.rows[-1][1])
        self.assertTrue(rep.failed)

    def test_the_warn_overflow_line_stays_a_warn(self) -> None:
        body = _questionnaire(*(f"id: q1{c}, text: A, flag: true"
                                for c in "abcdefghij"))
        rep = self._report(body)
        self.assertEqual(self._severities(rep), ["WARN"] * 9)
        self.assertIn("and 2 more", rep.rows[-1][1])
        self.assertFalse(rep.failed)


if __name__ == "__main__":
    unittest.main()
