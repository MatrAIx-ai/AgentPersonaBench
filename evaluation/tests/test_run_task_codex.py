from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from evaluation.run_codex_ablation import evaluate_ablation
from evaluation.run_task_codex import (
    DEFAULT_CODEX_MODEL,
    EXIT_AGENT_INVALID,
    EXIT_HELD,
    EXIT_INFRA_ERROR,
    EXIT_VIOLATED,
    AgentInvalid,
    InfrastructureError,
    build_output_schema,
    codex_environment,
    load_app_contract,
    load_metadata,
    load_web_catalog,
    resolve_task_dir,
    run_codex,
    selection_schema,
    validate_result,
    validate_selection,
    verifier_environment,
)

QUESTIONS = [
    {
        "id": "q1",
        "prompt": "First?",
        "options": [{"id": "q1a", "text": "A"}, {"id": "q1b", "text": "B"}],
    },
    {
        "id": "q2",
        "prompt": "Second?",
        "options": [{"id": "q2a", "text": "A"}, {"id": "q2b", "text": "B"}],
    },
]


def write_task_toml(path: Path, task_type: str, evaluator: str) -> None:
    path.write_text(
        f'[metadata]\ntype = "{task_type}"\n\n[[checks]]\nevaluator = "{evaluator}"\n',
        encoding="utf-8",
    )


class CodexTaskRunnerTests(unittest.TestCase):
    def test_default_model_is_explicitly_pinned(self) -> None:
        self.assertEqual(DEFAULT_CODEX_MODEL, "gpt-5.6-sol")

    def test_ablation_gate_requires_persona_specific_separation(self) -> None:
        passing = evaluate_ablation(
            {
                "persona": [True, True, True, True, False],
                "blind": [False, False, False, False, True],
                "explicit": [True, True, True, True, True],
            }
        )
        failing = evaluate_ablation(
            {
                "persona": [True] * 5,
                "blind": [True] * 5,
                "explicit": [True] * 5,
            }
        )
        self.assertTrue(passing["passed"])
        self.assertFalse(failing["passed"])

    def test_exit_taxonomy_is_unambiguous(self) -> None:
        self.assertEqual(
            (EXIT_HELD, EXIT_VIOLATED, EXIT_AGENT_INVALID, EXIT_INFRA_ERROR),
            (0, 1, 2, 3),
        )

    def test_survey_schema_pins_count_and_known_ids(self) -> None:
        schema = build_output_schema(QUESTIONS)
        answers = schema["properties"]["answers"]
        self.assertEqual((answers["minItems"], answers["maxItems"]), (2, 2))
        properties = answers["items"]["properties"]
        self.assertEqual(properties["questionId"]["enum"], ["q1", "q2"])
        self.assertEqual(
            properties["selectedOptionId"]["enum"],
            ["q1a", "q1b", "q2a", "q2b"],
        )

    def test_survey_result_is_validated_and_reordered(self) -> None:
        result = validate_result(
            {
                "answers": [
                    {"questionId": "q2", "selectedOptionId": "q2b"},
                    {"questionId": "q1", "selectedOptionId": "q1a"},
                ]
            },
            QUESTIONS,
        )
        self.assertEqual(
            result["answers"],
            [
                {"questionId": "q1", "selectedOptionId": "q1a"},
                {"questionId": "q2", "selectedOptionId": "q2b"},
            ],
        )

    def test_survey_result_rejects_cross_question_option(self) -> None:
        with self.assertRaisesRegex(AgentInvalid, "invalid option"):
            validate_result(
                {
                    "answers": [
                        {"questionId": "q1", "selectedOptionId": "q2a"},
                        {"questionId": "q2", "selectedOptionId": "q2b"},
                    ]
                },
                QUESTIONS,
            )

    def test_selection_contract_rejects_duplicates(self) -> None:
        schema = selection_schema(["a", "b", "c"], 2, 3)
        self.assertEqual(schema["properties"]["selectedItemIds"]["minItems"], 2)
        with self.assertRaisesRegex(AgentInvalid, "duplicate"):
            validate_selection({"selectedItemIds": ["a", "a"]}, ["a", "b"], 2, 2)

    def test_resolve_accepts_bucket_prefixed_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = Path(temp_dir)
            single_root = tasks / "single-attribute"
            multi_root = tasks / "multi-attribute"
            task_dir = single_root / "category" / "sample"
            task_dir.mkdir(parents=True)
            multi_root.mkdir(parents=True)
            (task_dir / "task.toml").write_text("", encoding="utf-8")
            resolved = resolve_task_dir(
                "single-attribute/category/sample", (single_root, multi_root)
            )
        self.assertEqual(resolved, task_dir.resolve())

    def test_metadata_enforces_surface_evaluator_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            write_task_toml(task_dir / "task.toml", "web", "llm-judge")
            with self.assertRaisesRegex(InfrastructureError, "unsupported web"):
                load_metadata(task_dir)

    def test_web_catalog_exposes_text_but_not_hidden_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            site = task_dir / "input" / "site"
            site.mkdir(parents=True)
            (site / "index.html").write_text(
                """<div class="item" data-id="x1" data-secret-label="ANCHOR">
                <span>Visible one</span><button>Add</button></div>
                <div class="item" data-id="x2" data-secret-label="SURFACE">
                <span>Visible two</span><button>Add</button></div>
                <div class="item" data-id="x3" data-secret-label="ANCHOR">
                <span>Visible three</span><button>Add</button></div>""",
                encoding="utf-8",
            )
            catalog = load_web_catalog(task_dir)
        encoded = json.dumps(catalog)
        self.assertEqual([item["id"] for item in catalog], ["x1", "x2", "x3"])
        self.assertNotIn("ANCHOR", encoded)
        self.assertNotIn("SURFACE", encoded)

    def test_app_contract_keeps_labels_host_side(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            app_dir = task_dir / "input" / "app"
            tests_dir = task_dir / "tests"
            app_dir.mkdir(parents=True)
            tests_dir.mkdir()
            (app_dir / "demo.py").write_text(
                "MENU = [\n"
                " ('a', 'Cat', 'Alpha', 'Visible A', 'Free'),\n"
                " ('b', 'Cat', 'Beta', 'Visible B', 'Free'),\n"
                "]\n",
                encoding="utf-8",
            )
            (tests_dir / "answer_key.json").write_text(
                json.dumps({"label": {"a": True, "b": False},
                            "name": {"a": "Alpha", "b": "Beta"}}),
                encoding="utf-8",
            )
            (tests_dir / "verifier.py").write_text(
                "PERSONA='p1'\nLIST_KEY='picks'\n"
                "MIN_ITEMS,MAX_ITEMS,FNAME=1,2,'result.json'\n",
                encoding="utf-8",
            )
            contract = load_app_contract(task_dir)
        self.assertEqual(contract["rows"]["a"], {"id": "a", "name": "Alpha"})
        self.assertIsNone(contract["label"])
        self.assertNotIn("hidden", json.dumps(contract["visible"]))
        self.assertNotIn("true", json.dumps(contract["visible"]).lower())

    def test_app_contract_preserves_legacy_labelled_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir)
            app_dir = task_dir / "input" / "app"
            tests_dir = task_dir / "tests"
            app_dir.mkdir(parents=True)
            tests_dir.mkdir()
            (app_dir / "demo.py").write_text(
                "MENU=[('a','Cat','Alpha','Visible A','Free',True)]\n",
                encoding="utf-8",
            )
            (tests_dir / "verifier.py").write_text(
                "PERSONA='p1'\nLIST_KEY,LABEL='picks','hidden'\n"
                "MIN_ITEMS,MAX_ITEMS,FNAME=1,1,'result.json'\n",
                encoding="utf-8",
            )
            contract = load_app_contract(task_dir)
        self.assertEqual(contract["rows"]["a"]["hidden"], True)
        self.assertNotIn("hidden", json.dumps(contract["visible"]))

    def test_codex_environment_is_allowlisted(self) -> None:
        env = codex_environment(
            {
                "PATH": "/bin",
                "HOME": "/home/test",
                "CODEX_API_KEY": "codex-secret",
                "CREATEAI_BUILDER_API_KEY": "builder-secret",
                "UNRELATED": "value",
            }
        )
        self.assertEqual(
            env,
            {"PATH": "/bin", "HOME": "/home/test", "CODEX_API_KEY": "codex-secret"},
        )

    def test_verifier_environment_scrubs_credentials(self) -> None:
        env = verifier_environment(
            Path("/tmp/output"),
            {
                "PATH": "/bin",
                "OPENAI_API_KEY": "openai-secret",
                "CREATEAI_BUILDER_API_KEY": "builder-secret",
                "SERVICE_TOKEN": "token-secret",
                "SAFE": "ok",
            },
        )
        self.assertEqual(env["SAFE"], "ok")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CREATEAI_BUILDER_API_KEY", env)
        self.assertNotIn("SERVICE_TOKEN", env)

    def test_codex_call_uses_ephemeral_read_only_no_config_mode(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            captured["command"] = command
            captured["env"] = kwargs["env"]
            response = Path(command[command.index("--output-last-message") + 1])
            response.write_text('{"message":"ok"}', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("evaluation.run_task_codex.subprocess.run", side_effect=fake_run),
        ):
            result, _ = run_codex(
                codex_bin="codex",
                prompt="respond",
                schema={"type": "object"},
                output_dir=Path(temp_dir),
                model=None,
                timeout=5,
            )
        command = captured["command"]
        self.assertEqual(result, {"message": "ok"})
        for flag in ("--ephemeral", "--ignore-user-config", "--ignore-rules"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")

    def test_compatibility_entrypoint_classifies_login_failure_as_infra(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task_dir = Path(temp_dir) / "task"
            (task_dir / "input").mkdir(parents=True)
            write_task_toml(task_dir / "task.toml", "survey", "rule-based")
            (task_dir / "input" / "questionnaire.yaml").write_text(
                yaml.safe_dump({"questions": QUESTIONS}), encoding="utf-8"
            )
            (task_dir / "persona.yaml").write_text(
                yaml.safe_dump(
                    {
                        "persona_id": "p1",
                        "attributes": {
                            "sample": {
                                "value": "focused",
                                "label": "Style",
                                "category": "Personality: Character",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (task_dir / "instruction.md").write_text("Complete it.", encoding="utf-8")
            fake_codex = Path(temp_dir) / "codex-fail"
            fake_codex.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake_codex.chmod(0o755)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "run_survey_codex.py"),
                    str(task_dir),
                    "--codex-bin",
                    str(fake_codex),
                    "--output-dir",
                    str(Path(temp_dir) / "output"),
                ],
                capture_output=True,
                check=False,
                text=True,
            )
        self.assertEqual(completed.returncode, EXIT_INFRA_ERROR)
        self.assertIn("Codex login check failed", completed.stderr)
        self.assertNotIn("ModuleNotFoundError", completed.stderr)


if __name__ == "__main__":
    unittest.main()
