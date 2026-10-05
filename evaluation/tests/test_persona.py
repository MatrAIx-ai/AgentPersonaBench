from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from evaluation.src.persona import persona_system_prompt


class PersonaRenderingTests(unittest.TestCase):
    def _render(self, attributes: dict, task_toml: str | None = None) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            (task_dir / "persona.yaml").write_text(
                yaml.safe_dump({"attributes": attributes}), encoding="utf-8"
            )
            if task_toml is not None:
                (task_dir / "task.toml").write_text(task_toml, encoding="utf-8")
            return persona_system_prompt(task_dir)

    def test_pinned_categorical_none_is_rendered(self) -> None:
        prompt = self._render(
            {
                "lstyle_caffeine": {
                    "value": "None",
                    "label": "Caffeine intake",
                    "category": "Interests: Culture",
                }
            },
            '[[checks]]\ndimension_id = "lstyle_caffeine"\nvalue = "None"\n',
        )
        self.assertIn("- Caffeine intake: None", prompt)

    def test_unpinned_nullish_values_are_suppressed(self) -> None:
        prompt = self._render(
            {
                "placeholder": {"value": "None", "label": "Placeholder"},
                "actual_null": {"value": None, "label": "Actual null"},
                "normal": {"value": "Tea", "label": "Drink"},
            }
        )
        self.assertNotIn("Placeholder", prompt)
        self.assertNotIn("Actual null", prompt)
        self.assertIn("- Drink: Tea", prompt)

    def test_direct_persona_path_finds_sibling_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            persona_path = task_dir / "persona.yaml"
            persona_path.write_text(
                yaml.safe_dump(
                    {
                        "attributes": {
                            "lstyle_caffeine": {
                                "value": "None",
                                "label": "Caffeine intake",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (task_dir / "task.toml").write_text(
                '[[checks]]\ndimension_id = "lstyle_caffeine"\nvalue = "None"\n',
                encoding="utf-8",
            )
            prompt = persona_system_prompt(persona_path)
        self.assertIn("- Caffeine intake: None", prompt)


if __name__ == "__main__":
    unittest.main()