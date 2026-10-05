from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.src.tools.task_doctor import Report, check_sim_context

def _flagged(rep) -> bool:
    """True when check_sim_context reported the leak, at whatever severity.

    The severity is deliberately WARN while seven merged suites still carry a
    coaching context.md; asserting on rep.failed would tie these tests to that
    temporary choice instead of to the detection itself.
    """
    return any(s in ("FAIL", "WARN") for s, _ in rep.rows)


META = {"checks": [{"dimension_id": "lstyle_diet_type", "value": "Vegan"}]}


def _task(context: str | None) -> Path:
    d = Path(tempfile.mkdtemp())
    if context is not None:
        (d / "input").mkdir()
        (d / "input" / "context.md").write_text(context, encoding="utf-8")
    return d


def _run(context: str | None, meta: dict = META) -> Report:
    rep = Report()
    check_sim_context(_task(context), meta, rep)
    return rep


class SimContextTests(unittest.TestCase):
    """input/context.md is injected into the persona simulator's own prompt."""

    def test_a_task_without_context_md_is_not_judged(self) -> None:
        rep = _run(None)
        self.assertEqual(rep.rows, [])
        self.assertFalse(_flagged(rep))

    def test_scenario_only_context_passes(self) -> None:
        rep = _run("# Scenario — dinner plans\n\n"
                   "The persona asks an assistant to help plan meals.\n\n"
                   "## The user's message\n\n> Can you help me plan dinners?\n")
        self.assertFalse(_flagged(rep))

    def test_naming_the_tested_value_fails(self) -> None:
        rep = _run("The persona is Vegan and orders accordingly.\n")
        self.assertTrue(_flagged(rep))
        self.assertIn("names the tested value", rep.rows[0][1])

    def test_announcing_the_measurement_fails(self) -> None:
        rep = _run("We are testing latent adherence across three axes.\n")
        self.assertTrue(_flagged(rep))
        self.assertIn("coaches the persona simulator", rep.rows[0][1])

    def test_prescribing_the_expected_behaviour_fails(self) -> None:
        for line in ("The persona should decline the suggestion.\n",
                     "A persona holding this value should steer away.\n",
                     "They should resist the monthly cadence.\n"):
            with self.subTest(line=line):
                self.assertTrue(_flagged(_run(line)))

    def test_the_announcement_is_caught_across_a_line_break(self) -> None:
        rep = _run("The request is generic. We are\ntesting latent adherence here.\n")
        self.assertTrue(_flagged(rep))

    def test_ordinary_narration_is_not_coaching(self) -> None:
        rep = _run("# Scenario — a friend asks about a crypto tip\n\n"
                   "Jordan has no emergency fund and is leaning toward "
                   "putting most of it in.\n\n> Should I do it?\n")
        self.assertFalse(_flagged(rep))


class ValueBoundaryTests(unittest.TestCase):
    r"""A value ending in punctuation must not slip past the guard.

    `\b` is a boundary between a word and a non-word character, so `\b85+\b`
    can never match "85+ machines": the trailing `\b` is asserted between `+`
    and a space, two non-word characters. 28 values in evaluation/src/persona/schema/dimensions.json end
    that way — `85+`, `20+`, `$200k+`, `Enterprise (5k+)`, `Fluent (C1-C2)` —
    and for every one of them the guard silently passed a context.md that named
    the tested value, which chat_harness then injects into the simulator.
    """

    def _named(self, value: str, context: str) -> bool:
        return _flagged(_run(context, {"checks": [{"dimension_id": "d", "value": value}]}))

    def test_a_plus_terminated_value_is_caught(self) -> None:
        self.assertTrue(self._named("20+", "A shop with 20+ years behind it.\n"))
        self.assertTrue(self._named("85+", "Readers in the 85+ bracket.\n"))

    def test_values_wrapped_in_punctuation_are_caught(self) -> None:
        self.assertTrue(self._named("$200k+", "Household income $200k+ or so.\n"))
        self.assertTrue(self._named("Fluent (C1-C2)", "German: fluent (c1-c2).\n"))
        self.assertTrue(self._named("Enterprise (5k+)",
                                    "They work at an enterprise (5k+).\n"))

    def test_a_longer_number_is_not_a_match(self) -> None:
        self.assertFalse(self._named("20+", "A fleet of 120+ machines.\n"))
        self.assertFalse(self._named("85+", "We ship 185+ units a week.\n"))

    def test_ordinary_word_values_keep_their_boundaries(self) -> None:
        self.assertTrue(self._named("Vegan", "The persona is vegan.\n"))
        self.assertFalse(self._named("Vegan", "Veganism is on the rise.\n"))
        self.assertFalse(self._named("Vegan", "Two vegans walk in.\n"))


class InstructionBoundaryTests(unittest.TestCase):
    """check_instruction built the same broken `\\b...\\b` guard."""

    def _leaks(self, value: str, instruction: str) -> bool:
        from evaluation.src.tools.task_doctor import Report, check_instruction
        d = Path(tempfile.mkdtemp())
        (d / "instruction.md").write_text(instruction, encoding="utf-8")
        rep = Report()
        check_instruction(d, {"checks": [{"dimension_id": "d", "value": value}]}, rep)
        return any("LEAKS the tested value" in msg for _, msg in rep.rows)

    def test_a_plus_terminated_value_is_caught(self) -> None:
        self.assertTrue(self._leaks("20+", "Plan for a team with 20+ years.\n"))

    def test_a_longer_number_is_not_a_match(self) -> None:
        self.assertFalse(self._leaks("20+", "Plan for a fleet of 120+ vans.\n"))

    def test_a_clean_instruction_still_passes(self) -> None:
        self.assertFalse(self._leaks("20+", "Put together the tooling you need.\n"))


if __name__ == "__main__":
    unittest.main()
