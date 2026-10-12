from backend.service import run_store


def test_friendly_persona_name_prefers_occupation_from_context():
    name = run_store.friendly_persona_name(
        {
            "name": "Nemotron · 01B0D4D4",
            "source": "Nemotron",
            "context": "Demographics:\n  Age: 51\n  Occupation: Financial Manager\n  Location:\n",
        }
    )
    assert name == "Financial Manager"


def test_friendly_persona_name_falls_back_to_name_then_source():
    assert run_store.friendly_persona_name({"name": "Ada Lovelace", "context": "no role here"}) == "Ada Lovelace"
    assert run_store.friendly_persona_name({"name": "", "source": "PersonaHub", "context": ""}) == "PersonaHub"


def test_persona_summary_uses_friendly_name():
    summary = run_store.persona_summary(
        {"id": "p1", "name": "Nemotron · 01B0D4D4", "source": "Nemotron", "context": "Occupation: Nurse"}
    )
    assert summary["id"] == "p1"
    assert summary["name"] == "Nurse"
    assert summary["source"] == "Nemotron"
