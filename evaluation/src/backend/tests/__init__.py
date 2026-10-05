"""Test package for the Playground backend (service + API).

These tests exercise the pure-python service layer
(:mod:`backend.service`) and the FastAPI app (:mod:`backend.api`) **without**
any RecAI / OpenAI / numpy / pandas / network dependency. The heavyweight
backend (``recbot.interecagent_bridge.run_turn`` and ``recbot.types``) is
replaced by a faithful in-memory fake installed into ``sys.modules`` by
:mod:`tests.conftest` before any service module lazily imports it.
"""
