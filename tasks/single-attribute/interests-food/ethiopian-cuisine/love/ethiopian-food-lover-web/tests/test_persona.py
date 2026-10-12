"""Regression checks for the complete dataset-native adult food persona."""
import hashlib
import json
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


class PersonaTests(unittest.TestCase):
    def test_complete_adult_profile_matches_pinned_source(self) -> None:
        persona = yaml.safe_load((HERE.parent / "persona.yaml").read_text(encoding="utf-8"))
        provenance = json.loads((HERE / "persona_provenance.json").read_text(encoding="utf-8"))
        attributes = persona["attributes"]
        self.assertEqual(persona["persona_id"], provenance["persona_id"])
        self.assertEqual(persona["source"], f"MatrAIx_Persona_1M:{provenance['source_row_index']}")
        self.assertEqual(len(attributes), 1290)
        self.assertEqual(len(attributes), provenance["populated_attribute_count"])
        self.assertEqual(attributes["age_bracket"]["value"], "45-54")
        self.assertEqual(attributes["cuis_ethiopian"]["value"], "Love")
        self.assertEqual(attributes["lstyle_diet_type"]["value"], "Omnivore")
        for dimension in provenance["neutral_alternative_dimensions"]:
            with self.subTest(dimension=dimension):
                self.assertEqual(attributes[dimension]["value"], "Neutral")
        canonical = json.dumps(attributes, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(), provenance["attributes_sha256"])


if __name__ == "__main__":
    unittest.main()
