"""Public naming contract for the Playground UI and API."""

from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
FORMER_BRAND = "RecBot" + " Studio"
FORMER_PRODUCT = "Persona" + "Eval"


def test_public_product_name_is_playground(client):
    """The public API brand should be Playground."""
    assert client.app.title == "Playground API"


def test_frontend_header_uses_playground_nav():
    top_bar = (APP_ROOT / "frontend/src/components/TopBar.tsx").read_text()

    assert "Playground" in top_bar
    assert "Persona World" in top_bar
    assert FORMER_BRAND not in top_bar
    assert FORMER_PRODUCT not in top_bar


def test_public_docs_do_not_use_old_product_names():
    public_files = [
        APP_ROOT / "README.md",
        APP_ROOT / "run_demo.sh",
        APP_ROOT / "backend/api/app.py",
        APP_ROOT / "backend/run_dev.sh",
        APP_ROOT / "backend/run_real.sh",
        APP_ROOT / "frontend/index.html",
        APP_ROOT / "frontend/package.json",
        APP_ROOT / "frontend/src/App.tsx",
        APP_ROOT / "frontend/src/components/ErrorBoundary.tsx",
    ]

    for path in public_files:
        text = path.read_text()
        assert FORMER_BRAND not in text, str(path.relative_to(APP_ROOT))
        assert FORMER_PRODUCT not in text, str(path.relative_to(APP_ROOT))
        assert "persona_eval" not in text, str(path.relative_to(APP_ROOT))
        assert "persona-eval" not in text, str(path.relative_to(APP_ROOT))
