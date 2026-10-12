"""The host agenda, not model timing, guarantees all final handoff opportunities."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TASK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tested_agenda", TASK / "solution/agenda.py")
agenda = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agenda)


class Agenda(unittest.TestCase):
    def test_actual_history_and_fixed_questions_survive_ignored_timing(self):
        requests = []
        def chat(messages, **settings):
            requests.append((messages, settings))
            return "I would like to keep discussing the first report indefinitely."
        bot = agenda.AgendaColleague("Neutral colleague", "explicit-model", TASK / "input/agenda.json", chat=chat)
        replies = []
        for i in range(12):
            replies.append(bot.run_turn_sync(f"Actual persona turn {i + 1}.")["assistantMessage"])
        for n in (1, 4, 7, 9, 10, 11, 12):
            self.assertEqual(replies[n - 1], bot.agenda["fixed_replies"][str(n)])
        self.assertEqual(len(requests), 5)
        self.assertEqual(len(bot.history), 24)
        self.assertEqual([e["reply"] for e in bot.events], list(range(1, 13)))
        # The final generated reply sees all earlier fixed and generated turns.
        self.assertEqual(requests[-1][0][1:], bot.history[:15])
        self.assertEqual(requests[-1][1], {"model": "explicit-model", "max_tokens": 1024, "temperature": 0.6})
        with self.assertRaises(ValueError):
            bot.run_turn_sync("An unauthorized thirteenth turn.")

    def test_empty_generated_reply_does_not_invent_history(self):
        bot = agenda.AgendaColleague("role", "model", TASK / "input/agenda.json", chat=lambda *a, **k: "")
        bot.run_turn_sync("Opening")
        with self.assertRaises(ValueError):
            bot.run_turn_sync("My receipt plan")
        self.assertEqual(len(bot.history), 2)
        self.assertEqual(len(bot.events), 1)

    def test_corrupt_schedule_rejected_before_calls(self):
        data = json.loads((TASK / "input/agenda.json").read_text(encoding="utf-8"))
        del data["fixed_replies"]["11"]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "agenda.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                agenda.AgendaColleague("role", "model", p, chat=lambda *a, **k: self.fail("called model"))

    def test_luna_reserves_reasoning_budget_without_changing_scheduled_content(self):
        requests = []
        def chat(messages, **settings):
            requests.append((messages, settings))
            return "A natural follow-up."
        bot = agenda.AgendaColleague("Neutral colleague", "gpt-5.6-luna", TASK / "input/agenda.json", chat=chat)
        self.assertEqual(bot.run_turn_sync("Opening")["assistantMessage"], bot.agenda["fixed_replies"]["1"])
        self.assertEqual(requests, [])
        bot.run_turn_sync("My receipt plan")
        self.assertEqual(requests[0][1], {"model": "gpt-5.6-luna", "max_tokens": 16000, "temperature": 0.6})
        self.assertEqual(requests[0][0][1:], bot.history[:-1])
        self.assertNotIn("reasoning", requests[0][0][0]["content"].lower())



if __name__ == "__main__":
    unittest.main()
