from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_suite = load_module("run_suite", REPO / "evaluation" / "run_suite.py")
report_suite = load_module("report_suite", REPO / "evaluation" / "report_suite.py")


class SuiteRunnerTest(unittest.TestCase):
    def test_progress_tracks_status_and_prints_timing(self) -> None:
        stream = io.StringIO()
        with mock.patch.object(run_suite.sys, "stderr", stream):
            progress = run_suite.Progress("Test", 2)
            progress.started = time.monotonic() - 2
            progress.advance("pass")
            progress.advance("fail")
            progress.finish()
        output = stream.getvalue()
        self.assertIn("2/2 (100.0%)", output)
        self.assertIn("elapsed", output)
        self.assertIn("ETA", output)
        self.assertIn("fail=1 pass=1", output)

    def test_discovery_matches_every_merged_task_manifest(self) -> None:
        discovered = run_suite.discover_tasks()
        manifests = list((REPO / "tasks" / "single-attribute").rglob("task.toml"))
        manifests += list((REPO / "tasks" / "multi-attribute").rglob("task.toml"))
        self.assertEqual(len(discovered), len(manifests))
        self.assertEqual(len({(task["bucket"], task["task"]) for task in discovered}), len(discovered))
        self.assertLessEqual({task["surface"] for task in discovered}, {"survey", "chat", "web", "app"})

    def test_discovery_filters_surface_and_glob(self) -> None:
        # derive the probe from whatever is actually present, so the test holds for
        # a full inventory and for a subset distribution alike
        surveys = run_suite.discover_tasks(None, {"survey"})
        self.assertTrue(surveys, "expected at least one survey task")
        stem = surveys[0]["task"].rsplit("/", 1)[-1]
        tasks = run_suite.discover_tasks([f"*{stem}"], {"survey"})
        self.assertTrue(tasks)
        self.assertTrue(all(task["task"].endswith(stem) and task["surface"] == "survey"
                            for task in tasks))
        self.assertFalse(run_suite.discover_tasks([f"*{stem}"], {"chat"}))

    def test_run_key_is_stable_and_path_safe(self) -> None:
        key = run_suite.run_key("health/diet/vegan survey", "my/arm", "medium", 3)
        self.assertEqual(key, run_suite.run_key("health/diet/vegan survey", "my/arm", "medium", 3))
        self.assertNotIn("/", key)
        self.assertNotIn(" ", key)

    def test_latest_events_keeps_last_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("\n".join([
                json.dumps({"event": "completed", "run_key": "a", "status": "error"}),
                "not-json",
                json.dumps({"event": "completed", "run_key": "a", "status": "pass"}),
            ]), encoding="utf-8")
            self.assertEqual(report_suite.latest_events(path)["a"]["status"], "pass")

    def test_report_normalizes_multi_attribute_scores(self) -> None:
        plan = {"suite_id": "test", "git_sha": "abc", "tasks": [{}, {}], "models": ["m"], "seeds": [0]}
        rows = [
            {"task": "one", "surface": "survey", "model": "m", "seed": 0, "status": "pass",
             "score": "1/1", "normalized_reward": 1.0, "duration_s": 10.0, "model_latency_s": 4.0,
             "total_tokens": 100, "error_class": ""},
            {"task": "multi", "surface": "app", "model": "m", "seed": 0, "status": "fail",
             "score": "1/3", "normalized_reward": 1 / 3, "duration_s": 20.0, "model_latency_s": 8.0,
             "total_tokens": 200, "error_class": ""},
        ]
        report = report_suite.render_markdown(plan, rows)
        self.assertIn("0.667", report)
        self.assertIn("Common / planned | Infra errors", report)
        self.assertIn("| 2 / 2 | 0 |", report)
        self.assertIn("Avg time / task (s)", report)
        self.assertIn("| App | 1 | 0 / 1 / 0 | 20.0 | — | 200 |", report)

    def test_every_committed_arm_config_is_loadable(self) -> None:
        arms = sorted(p.stem for p in (REPO / "evaluation" / "configs").glob("*.json"))
        self.assertTrue(arms)
        configs = run_suite.load_arm_configs(arms, {})
        for arm in arms:
            # assert against the runner's own provider set, not a hardcoded list:
            # OpenAI-compatible providers are registry-driven and can grow
            self.assertIn(configs[arm]["provider"], run_suite._PROVIDER_KEYS)
            self.assertIsInstance(configs[arm]["model"], str)

    def test_model_id_override_is_pinned_without_changing_config(self) -> None:
        arm = "opus-4-8"
        path = REPO / "evaluation" / "configs" / f"{arm}.json"
        configs = run_suite.load_arm_configs([arm], {arm: "runtime-only-model-id"})
        self.assertEqual(configs[arm]["model"], "runtime-only-model-id")
        self.assertTrue(configs[arm]["model_overridden"])
        self.assertNotEqual(json.loads(path.read_text())["model"], "runtime-only-model-id")

    def test_model_id_for_unselected_arm_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "unselected arm"):
            run_suite.load_arm_configs(["opus-4-8"], {"not-selected": "x"})

    def test_unresolved_model_template_is_rejected_before_runtime(self) -> None:
        with self.assertRaisesRegex(SystemExit, "use --model-id"):
            run_suite.validate_resolved_models({"some-arm": {"model": "REPLACE_WITH_MODEL_ID"}})
        run_suite.validate_resolved_models({"some-arm": {"model": "a-real-model-id"}})

    def test_usage_falls_back_to_envelope_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            envelope = Path(tmp) / "envelope.json"
            envelope.write_text(json.dumps({"model_usage": {"total_tokens": 42}}), encoding="utf-8")
            self.assertEqual(report_suite.usage_for(envelope)["total_tokens"], 42)

    def test_report_ranks_only_common_behavioral_coverage(self) -> None:
        plan = {"suite_id": "test", "git_sha": "abc", "tasks": [{}, {}], "models": ["a", "b"], "seeds": [0]}
        base = {"surface": "survey", "effort": "medium", "seed": 0, "duration_s": 1,
                "model_latency_s": None, "total_tokens": None, "error_class": "", "score": "1/1"}
        rows = [
            {**base, "task": "shared", "model": "a", "status": "fail", "normalized_reward": 0.0},
            {**base, "task": "extra", "model": "a", "status": "pass", "normalized_reward": 1.0},
            {**base, "task": "shared", "model": "b", "status": "pass", "normalized_reward": 1.0},
            {**base, "task": "extra", "model": "b", "status": "error", "normalized_reward": None},
        ]
        report = report_suite.render_markdown(plan, rows)
        self.assertIn("| 1 | `b` | 1.000 |", report)
        self.assertIn("| 2 | `a` | 0.000 | 0.500 |", report)
        self.assertIn("Comparable coverage:** 1/2", report)

    def test_html_dashboard_contains_metrics_and_filter(self) -> None:
        plan = {"suite_id": "dashboard", "git_sha": "abc", "tasks": [{}], "models": ["m"], "seeds": [0]}
        rows = [{"bucket": "single-attribute", "task": "one", "surface": "survey", "model": "m",
                 "effort": "medium", "seed": 0, "status": "pass", "score": "1/1",
                 "normalized_reward": 1.0, "duration_s": 2.0, "model_latency_s": 1.0,
                 "total_tokens": 42, "cost_usd": 0.01, "error_class": ""}]
        dashboard = report_suite.render_html(plan, rows)
        self.assertIn("PersonaBench · dashboard", dashboard)
        self.assertIn("Common score", dashboard)
        self.assertIn("Avg time / task", dashboard)
        self.assertIn("Total tokens", dashboard)
        self.assertIn("Performance by task type", dashboard)
        self.assertIn("Search task, type, model, or status", dashboard)

    def test_dashboard_uses_all_attempts_for_average_time_and_sums_tokens(self) -> None:
        plan = {"suite_id": "metrics", "git_sha": "abc", "tasks": [{}, {}], "models": ["m"], "seeds": [0]}
        base = {"bucket": "single-attribute", "surface": "survey", "model": "m", "effort": "medium",
                "seed": 0, "model_latency_s": None, "cost_usd": None, "error_class": "", "score": "1/1"}
        rows = [
            {**base, "task": "pass", "status": "pass", "normalized_reward": 1.0,
             "duration_s": 10.0, "total_tokens": 100},
            {**base, "task": "fail", "status": "fail", "normalized_reward": 0.0,
             "duration_s": 30.0, "total_tokens": 300},
        ]
        dashboard = report_suite.render_html(plan, rows)
        self.assertIn("<b>20.0s</b><small>All recorded attempts</small>", dashboard)
        self.assertIn("<td>400</td>", dashboard)


if __name__ == "__main__":
    unittest.main()
