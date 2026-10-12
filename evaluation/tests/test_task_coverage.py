from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import subprocess

from evaluation.src.tools.task_coverage import (
    IGNORED_REVIEW_IDS,
    MAX_ISSUE_BODY_BYTES,
    Profile,
    TaskProvenance,
    _git_history,
    _with_legacy_reviewers,
    generate,
    generate_issue_body,
    load_task_provenance,
    load_tasks,
)


class FakeGitHubClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.web_root = "https://github.com/example/repo"

    def get(self, path: str) -> object:
        self.calls.append(path)
        return self.responses[path]


class TaskCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        (self.repo / "evaluation" / "src" / "persona" / "schema").mkdir(parents=True)
        (self.repo / "evaluation" / "src" / "persona" / "schema" / "dimensions.json").write_text(
            json.dumps(
                {
                    "dimensions": [
                        {
                            "id": "diet",
                            "label": "Diet type",
                            "category": "Health",
                            "values": ["Vegan", "Omnivore"],
                        },
                        {
                            "id": "risk",
                            "label": "Risk tolerance",
                            "category": "Values",
                            "values": ["Cautious"],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _manifest(
        self, bucket: str, path: str, checks: str, persona_id: str = "persona-1"
    ) -> None:
        task_dir = self.repo / "tasks" / bucket / path
        task_dir.mkdir(parents=True)
        (task_dir / "task.toml").write_text(
            "[task]\n"
            f'name = "personabench/{task_dir.name}"\n'
            'theme = "Test"\n\n'
            f"{checks}",
            encoding="utf-8",
        )
        (task_dir / "persona.yaml").write_text(
            f"persona_id: {persona_id}\nsource: test-fixture\nattributes: {{}}\n",
            encoding="utf-8",
        )

    def test_counts_pairs_and_surfaces_without_treating_repeats_as_new_coverage(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-survey", vegan)
        self._manifest("single-attribute", "health/diet/vegan/vegan-chat", vegan)
        self._manifest(
            "multi-attribute",
            "trip-web",
            '[[checks]]\ndimension_id = "diet"\nvalue = "Vegan"\n'
            '[[checks]]\ndimension_id = "risk"\nvalue = "Cautious"\n',
        )

        tasks = load_tasks(self.repo)
        dashboard = generate(self.repo)

        self.assertEqual(len(tasks), 3)
        self.assertIn("**3 task implementations:** 2 single-attribute + 1 multi-attribute", dashboard)
        self.assertIn("**2 unique attribute-value pairs** across **2/2 dimensions**", dashboard)
        self.assertIn("**1 unique persona IDs** used across 3 task implementations", dashboard)
        self.assertIn("| Single | 1 | 1 | 0 | 0 | **2** |", dashboard)
        self.assertIn("| Multi | 0 | 0 | 1 | 0 | **1** |", dashboard)
        self.assertIn("| Vegan | `persona-1` | 2 | 1 | **3** |", dashboard)
        self.assertIn("| Cautious | `persona-1` | 0 | 1 | **1** |", dashboard)

    def test_lists_distinct_personas_and_sources(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "one-survey", vegan, "persona-a")
        self._manifest("single-attribute", "two-chat", vegan, "persona-b")

        dashboard = generate(self.repo)

        self.assertIn("**2 unique persona IDs** used across 2 task implementations", dashboard)
        self.assertIn("`persona-a`<br>`persona-b`", dashboard)
        self.assertIn("| `persona-a` | test-fixture | **1** | `diet=Vegan` |", dashboard)
        self.assertIn("| `persona-b` | test-fixture | **1** | `diet=Vegan` |", dashboard)

    def test_document_keeps_every_table_and_per_task_links(self) -> None:
        """The committed file has no size ceiling, so nothing is dropped there."""
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-web", vegan)

        document = generate(self.repo)

        self.assertIn("## Measured attributes", document)
        self.assertIn("| Attribute | Value | Persona(s) | Single | Multi | Total | Tasks |", document)
        self.assertIn("Persona inventory", document)
        self.assertIn("| Persona ID | Source | Task implementations | Attribute-values |", document)
        self.assertIn("[vegan-web](/MatrAIx-ai/Agent_PersonaBench/tree/main/", document)

    def test_issue_body_is_a_snapshot_plus_a_link_to_the_document(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-web", vegan)

        body = generate_issue_body(self.repo)

        self.assertIn("## Snapshot", body)
        self.assertIn("**1 task implementations:**", body)
        self.assertIn("[`docs/task-coverage.md`](/MatrAIx-ai/Agent_PersonaBench/blob/main/", body)
        # The tables are what blew past the ceiling; they must not come back.
        self.assertNotIn("## Measured attributes", body)
        self.assertNotIn("Persona inventory", body)
        self.assertNotIn("tree/main", body)

    def test_issue_body_stays_under_the_github_limit_as_the_benchmark_grows(self) -> None:
        """Regression for the silent stall: `updateIssue` rejects an over-limit
        body, so the tracker stopped updating with nothing said on the issue."""
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        for i in range(200):
            self._manifest("single-attribute", f"health/diet/vegan/vegan-{i}", vegan, f"persona-{i}")

        body = generate_issue_body(self.repo)

        self.assertLessEqual(len(body.encode("utf-8")), MAX_ISSUE_BODY_BYTES)
        # Fixed-size: 200 tasks must not render 200 anything.
        self.assertLess(len(body.encode("utf-8")), 2000)

    def test_reads_anchor_value_and_value(self) -> None:
        self._manifest(
            "single-attribute",
            "health/diet/vegan/vegan-app",
            '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n',
        )
        self._manifest(
            "multi-attribute",
            "risk-chat",
            '[[checks]]\ndimension_id = "risk"\nvalue = "Cautious"\n',
        )

        checks = [check for task in load_tasks(self.repo) for check in task.checks]
        self.assertEqual({(check.dimension_id, check.value) for check in checks}, {("diet", "Vegan"), ("risk", "Cautious")})

    def test_renders_task_contributors_reviewers_and_origins(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-web", vegan)
        task = load_tasks(self.repo)[0]
        provenance = {
            task.path: TaskProvenance(
                contributor=Profile("contributor", "https://github.com/contributor"),
                reviewers=(
                    Profile("alice", "https://github.com/alice"),
                    Profile("bob", "https://github.com/bob"),
                ),
                origin_label="PR #42",
                origin_url="https://github.com/example/repo/pull/42",
            )
        }

        dashboard = generate(self.repo, provenance=provenance)

        self.assertIn("Task contributions (1)", dashboard)
        self.assertLess(dashboard.index("## Task contributions"), dashboard.index("## Snapshot"))
        self.assertIn("| **1** | [contributor](https://github.com/contributor)", dashboard)
        self.assertIn("[contributor](https://github.com/contributor)", dashboard)
        self.assertIn("[alice](https://github.com/alice) · [bob](https://github.com/bob)", dashboard)
        self.assertIn("[PR #42](https://github.com/example/repo/pull/42)", dashboard)
        self.assertIn("[vegan-web](/MatrAIx-ai/Agent_PersonaBench/tree/main/", dashboard)

    def test_resolves_verified_pr_and_uses_actual_reviewers(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-web", vegan)
        task = load_tasks(self.repo)[0]
        manifest = f"{task.path.as_posix()}/task.toml"
        client = FakeGitHubClient(
            {
                "commits/contaminated/pulls?per_page=100": [
                    {
                        "number": 10,
                        "merged_at": "2026-01-01T00:00:00Z",
                        "user": {"login": "wrong", "html_url": "https://github.com/wrong"},
                    }
                ],
                "pulls/10/files?per_page=100": [{"filename": "tasks/another/task.toml"}],
                "commits/introduction/pulls?per_page=100": [
                    {
                        "number": 11,
                        "merged_at": "2026-01-02T00:00:00Z",
                        "html_url": "https://github.com/example/repo/pull/11",
                        "user": {"login": "author", "html_url": "https://github.com/author"},
                        "merged_by": {"login": "merger", "type": "User", "html_url": "https://github.com/merger"},
                    }
                ],
                "pulls/11/files?per_page=100": [{"filename": manifest}],
                "pulls/11": {
                    "number": 11,
                    "merged_at": "2026-01-02T00:00:00Z",
                    "html_url": "https://github.com/example/repo/pull/11",
                    "user": {"login": "author", "html_url": "https://github.com/author"},
                    "merged_by": {"login": "merger", "type": "User", "html_url": "https://github.com/merger"},
                },
                "pulls/11/reviews?per_page=100": [
                    {"id": 1, "user": {"login": "reviewer", "html_url": "https://github.com/reviewer"}},
                    {"id": next(iter(IGNORED_REVIEW_IDS)), "user": {"login": "accidental", "html_url": "https://github.com/accidental"}},
                    {"user": {"login": "author", "html_url": "https://github.com/author"}},
                    {"user": {"login": "review-bot[bot]", "html_url": "https://github.com/apps/review-bot"}},
                ],
                "pulls/11/comments?per_page=100": [
                    {"user": {"login": "inline-reviewer", "html_url": "https://github.com/inline-reviewer"}},
                    {"user": {"login": "reviewer", "html_url": "https://github.com/reviewer"}},
                ],
                "issues/11/comments?per_page=100": [
                    {"user": {"login": "feedback-reviewer", "html_url": "https://github.com/feedback-reviewer"}},
                    {"user": {"login": "author", "html_url": "https://github.com/author"}},
                ],
            }
        )

        provenance = load_task_provenance(
            self.repo,
            [task],
            client,  # type: ignore[arg-type]
            history_loader=lambda _repo, _manifest: [
                ("contaminated", manifest),
                ("introduction", manifest),
            ],
        )[task.path]

        self.assertEqual(provenance.contributor.name, "author")
        self.assertEqual(
            [reviewer.name for reviewer in provenance.reviewers],
            ["feedback-reviewer", "inline-reviewer", "reviewer"],
        )
        self.assertEqual(provenance.origin_label, "PR #11")

    def test_direct_commit_uses_linked_author_and_no_reviewers(self) -> None:
        vegan = '[[checks]]\ndimension_id = "diet"\nanchor_value = "Vegan"\n'
        self._manifest("single-attribute", "health/diet/vegan/vegan-web", vegan)
        task = load_tasks(self.repo)[0]
        client = FakeGitHubClient(
            {
                "commits/direct/pulls?per_page=100": [],
                "commits/direct": {
                    "author": {"login": "direct-user", "html_url": "https://github.com/direct-user"},
                    "commit": {"author": {"name": "Fallback Name", "email": "hidden@example.com"}},
                },
            }
        )

        provenance = load_task_provenance(
            self.repo,
            [task],
            client,  # type: ignore[arg-type]
            history_loader=lambda _repo, _manifest: [("direct", f"{task.path.as_posix()}/task.toml")],
        )[task.path]

        self.assertEqual(provenance.contributor.name, "direct-user")
        self.assertEqual(provenance.reviewers, ())
        self.assertNotIn("hidden@example.com", provenance.contributor.name)
        self.assertEqual(provenance.origin_label, "commit direct")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def test_git_history_credits_the_commit_that_produced_the_current_path(self) -> None:
        """Regression: a task.toml similar enough to an old, deleted one that
        `git log --follow` reports it as a rename/copy used to be recorded
        against the *old* path for the commit that actually introduced the
        *new* one -- e.g. a task rebuilt onto a fresh persona under a renamed
        dimension. That old path is invisible in a merged PR's cumulative
        file list (added and removed within the same PR nets to no diff), so
        provenance lookup always missed it and fell back to "Unknown" even
        though the introducing commit really was in the PR."""
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")

        boilerplate = (
            "[task]\nname = \"personabench/{name}\"\ntheme = \"Test\"\n\n"
            "[metadata]\ndifficulty = \"medium\"\ntype = \"chat\"\n\n"
            "[[checks]]\ndimension_id = \"{dim}\"\nanchor_value = \"{val}\"\n\n"
            "[verifier]\ntimeout_sec = 180.0\n\n[agent]\ntimeout_sec = 600.0\n"
        )
        old_dir = self.repo / "tasks" / "single-attribute" / "old-dim" / "old-value" / "old-chat"
        old_dir.mkdir(parents=True)
        old_manifest = old_dir / "task.toml"
        old_manifest.write_text(
            boilerplate.format(name="old-chat", dim="old_dim", val="Old"), encoding="utf-8"
        )
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "add old task")
        introducing_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout.strip()

        new_dir = self.repo / "tasks" / "single-attribute" / "new-dim" / "new-value" / "new-chat"
        new_dir.mkdir(parents=True)
        new_manifest = new_dir / "task.toml"
        new_manifest.write_text(
            boilerplate.format(name="new-chat", dim="new_dim", val="New"), encoding="utf-8"
        )
        old_manifest.unlink()
        old_dir.rmdir()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "rebuild onto a fresh dimension")
        rebuild_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout.strip()

        history = _git_history(self.repo, new_manifest)

        # Sanity check this repo's git actually detected a rename/copy between
        # the two paths -- otherwise this test would pass for the wrong reason.
        self.assertEqual(len(history), 2, history)
        self.assertEqual(history, [
            (introducing_sha, "tasks/single-attribute/old-dim/old-value/old-chat/task.toml"),
            (rebuild_sha, "tasks/single-attribute/new-dim/new-value/new-chat/task.toml"),
        ])

    def test_legacy_reviewers_fill_only_missing_historical_credit(self) -> None:
        jintao = _with_legacy_reviewers("PR #8", ())
        self.assertEqual([reviewer.name for reviewer in jintao], ["jintao-h"])

        recorded = (Profile("recorded-reviewer"),)
        self.assertEqual(_with_legacy_reviewers("PR #8", recorded), recorded)
        self.assertEqual(_with_legacy_reviewers("PR #999", ()), ())


if __name__ == "__main__":
    unittest.main()
