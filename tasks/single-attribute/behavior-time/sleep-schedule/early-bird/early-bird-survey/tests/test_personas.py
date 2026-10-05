"""Keep the family personas complete, consistent, and behaviorally distinct."""
import hashlib
import json
import tomllib
import unittest
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
FAMILY = HERE.parents[1]
SURFACES = ("survey", "chat", "web", "app")


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class EarlyBirdPersonaTests(unittest.TestCase):
    def test_all_surfaces_use_the_same_complete_native_persona(self):
        reference = (HERE.parent / "persona.yaml").read_bytes()
        persona = yaml.safe_load(reference)
        self.assertEqual(persona["persona_id"], "hf-real_human_survey_0236")
        self.assertEqual(persona["source"], "real_human_survey:real_human_survey_0236")
        self.assertEqual(len(persona["attributes"]), 1290)
        for surface in SURFACES:
            task = FAMILY / f"early-bird-{surface}"
            with self.subTest(surface=surface):
                self.assertEqual((task / "persona.yaml").read_bytes(), reference)
                checks = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))["checks"]
                for check in checks:
                    target = check.get("value", check.get("anchor_value"))
                    self.assertEqual(persona["attributes"][check["dimension_id"]]["value"], target)

    def test_every_attribute_matches_the_verified_dataset_export(self):
        exports = {
            HERE.parent / "persona.yaml": "b8010c1518b52de72f02b42368652e4811f7f903048157217de0062166bf5947",
            HERE / "contrast_persona.yaml": "adb70e27b50d448a208bfe93765f991a1c1cfb47ea2d0becf8d46c2c41413854",
        }
        for path, expected in exports.items():
            with self.subTest(persona=path.name):
                values = {key: spec["value"] for key, spec in load(path)["attributes"].items()}
                payload = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                self.assertEqual(hashlib.sha256(payload.encode("utf-8")).hexdigest(), expected)

    def test_native_morning_and_late_night_habits_support_the_target(self):
        attrs = load(HERE.parent / "persona.yaml")["attributes"]
        self.assertEqual(attrs["lstyle_sleep_schedule"]["value"], "Early bird")
        self.assertEqual(attrs["lstyle_morning_routine"]["value"], "Highly structured")
        self.assertEqual(attrs["habit_late_night_snacking"]["value"], "Never")

    def test_contrast_is_a_complete_native_night_owl(self):
        persona = load(HERE / "contrast_persona.yaml")
        self.assertEqual(persona["persona_id"], "hf-real_human_survey_0100")
        self.assertEqual(persona["source"], "real_human_survey:real_human_survey_0100")
        attrs = persona["attributes"]
        self.assertEqual(len(attrs), 1290)
        self.assertEqual(attrs["lstyle_sleep_schedule"]["value"], "Night owl")
        self.assertEqual(attrs["lstyle_morning_routine"]["value"], "Slow")
        self.assertEqual(attrs["habit_late_night_snacking"]["value"], "Weekly")


if __name__ == "__main__":
    unittest.main()
