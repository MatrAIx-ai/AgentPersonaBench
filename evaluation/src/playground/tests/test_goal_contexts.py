from playground.user_sim.kickoff import get_goal_context, load_goal_contexts


def test_registry_has_seeded_contexts():
    ids = {gc.id for gc in load_goal_contexts()}
    assert ids == {"scenario_default"}  # gradual_reveal collapsed into one realistic scenario


def test_goal_context_labels():
    labels = {gc.id: gc.label for gc in load_goal_contexts()}
    assert labels["scenario_default"] == "Realistic scenario"
    assert "gradual_reveal" not in labels  # collapsed; no longer offered


def test_template_consumes_required_fields():
    t = get_goal_context("scenario_default").template
    for key in ("{domain}", "{sut_description}", "{persona_context}"):
        assert key in t


def test_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_goal_context("nope")
