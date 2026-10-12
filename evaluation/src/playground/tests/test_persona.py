import pytest
from playground.persona_catalog import get_persona, load_personas


def test_loads_curated_catalog():
    ps = load_personas()
    ids = [p.id for p in ps]
    assert len(ids) == len(set(ids))            # unique ids
    # The checked-in matraix-persona-dev-sample is the canonical local catalog.
    assert len(ps) == 200
    assert all(p.source for p in ps)
    assert {"Nemotron", "OASIS", "PersonaHub", "PRIMEX"} <= {p.source for p in ps}


def test_curated_persona_has_rich_context_and_no_domain():
    p = get_persona("0001")
    assert p.name == "persona-0001"
    assert "Software & AI" in p.context
    assert not hasattr(p, "domain")


def test_search_and_limit():
    hits = load_personas(query="software", limit=5)
    assert 0 < len(hits) <= 5
    assert all("software" in (h.name + h.context).lower() for h in hits)


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        get_persona("nope")


def test_context_humanizes_enum_values():
    """Snake_case dimension keys render humanized for display, not raw."""
    ctx = get_persona("0001").context
    assert "Age Bracket:" in ctx
    assert "Role Function:" in ctx
    assert "age_bracket" not in ctx
    assert "role_function" not in ctx


def test_humanizing_preserves_free_text_and_proper_nouns():
    """Multi-word / already-cased values (cities, sentences) pass through as-is."""
    ctx = get_persona("0001").context
    assert "Software & AI" in ctx
    assert "Eastern Europe" in ctx


def test_long_persona_context_is_complete_not_capped():
    """The rendered bench persona context is returned in full, uncapped."""
    import yaml

    from playground import persona_catalog as P

    data = yaml.safe_load(
        (P._CURATED_DIR / "persona_0001.yaml").read_text(encoding="utf-8")
    )
    full = "\n".join(
        P._render({k: v for k, v in data.items() if k not in P._SKIP_KEYS})
    ).strip()
    assert len(full) > 1000
    assert get_persona("0001").context == full


def test_get_persona_accepts_persona_prefixed_ids():
    direct = get_persona("0001")
    prefixed = get_persona("persona_0001")
    assert prefixed.id == direct.id
    assert prefixed.context == direct.context
