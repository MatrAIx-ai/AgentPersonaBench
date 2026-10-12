#!/usr/bin/env python3
"""Generate the body of the pinned PersonaBench task-coverage issue.

The inventory distinguishes task implementations from unique attribute-value
pairs and personas. Repeated pairs are allowed, but visible coverage helps
contributors prefer new schema areas when possible.

Usage:
    python evaluation/src/tools/task_coverage.py
    python evaluation/src/tools/task_coverage.py --output /tmp/task-coverage.md

Dependencies: Python 3.11+ and PyYAML.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

import yaml

REPO = Path(__file__).resolve().parents[3]
SURFACES = ("survey", "chat", "web", "app")
GITHUB_ROOT = "https://github.com/MatrAIx-ai/Agent_PersonaBench"
GITHUB_PATH = GITHUB_ROOT.removeprefix("https://github.com")

# GitHub rejects an issue body over this with "Body is too long (updateIssue)",
# which is how this generator silently stopped updating #35: the body had grown
# to 387 KB, almost all of it per-task links repeated in two tables.
MAX_ISSUE_BODY_BYTES = 65536

# These initial task imports predate consistent GitHub review assignment. Their
# reviewer credit was confirmed separately; all newer PRs use API evidence only.
LEGACY_REVIEWERS: dict[str, tuple[Profile, ...]]


@dataclasses.dataclass(frozen=True)
class Check:
    dimension_id: str
    value: str


@dataclasses.dataclass(frozen=True)
class Persona:
    persona_id: str
    source: str


@dataclasses.dataclass(frozen=True)
class Task:
    bucket: str
    path: Path
    surface: str
    checks: tuple[Check, ...]
    persona: Persona


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    url: str = ""


LEGACY_REVIEWERS = {
    "PR #6": (Profile("jintao-h", "https://github.com/jintao-h"),),
    "PR #8": (Profile("jintao-h", "https://github.com/jintao-h"),),
    "PR #9": (Profile("jintao-h", "https://github.com/jintao-h"),),
    "commit 236fb00": (Profile("jintao-h", "https://github.com/jintao-h"),),
    "commit 70b7b91": (Profile("jintao-h", "https://github.com/jintao-h"),),
}


@dataclasses.dataclass(frozen=True)
class TaskProvenance:
    contributor: Profile
    reviewers: tuple[Profile, ...]
    origin_label: str
    origin_url: str


class GitHubClient:
    """Minimal cached GitHub REST client used only by the coverage workflow."""

    def __init__(self, repository: str, token: str) -> None:
        if not repository or "/" not in repository:
            raise ValueError("GitHub repository must use owner/name format")
        if not token:
            raise ValueError("GitHub attribution requires GH_TOKEN or GITHUB_TOKEN")
        self.base = f"https://api.github.com/repos/{repository}"
        self.web_root = f"https://github.com/{repository}"
        self.token = token
        self._cache: dict[str, object] = {}

    def get(self, path: str) -> object:
        if path in self._cache:
            return self._cache[path]
        url = f"{self.base}/{path.lstrip('/')}"
        items: list[object] = []
        first = True
        while url:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "personabench-task-coverage",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    value = json.loads(response.read().decode("utf-8"))
                    link = response.headers.get("Link", "")
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
                raise RuntimeError(f"GitHub API {exc.code} for {path}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"GitHub API request failed for {path}: {exc}") from exc
            if isinstance(value, list):
                items.extend(value)
                url = _next_link(link)
                first = False
            else:
                if not first:
                    raise RuntimeError(f"GitHub API pagination changed shape for {path}")
                self._cache[path] = value
                return value
        self._cache[path] = items
        return items


def _next_link(header: str) -> str:
    for part in header.split(","):
        pieces = [piece.strip() for piece in part.split(";")]
        if len(pieces) > 1 and pieces[1] == 'rel="next"':
            return pieces[0].strip("<>")
    return ""


def _git_history(repo: Path, manifest: Path) -> list[tuple[str, str]]:
    """Return oldest-first (commit, path-at-commit) history across renames."""
    relative = manifest.relative_to(repo).as_posix()
    result = subprocess.run(
        ["git", "log", "--follow", "--format=commit:%H", "--name-status", "--", relative],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    newest_first: list[tuple[str, str]] = []
    current_path = relative
    current_sha = ""
    # The path a commit introduced/left the file at, snapshotted before that
    # commit's own rename/copy line (if any) walks current_path further back.
    # Mutating current_path in place and appending it lazily on the *next*
    # "commit:" line meant every commit got credited with the path one hop
    # too old -- e.g. the commit that copied a task.toml to a new path under a
    # renamed dimension was recorded against the path it copied *from*, which
    # is invisible in a merged PR's cumulative file list (added and removed
    # within the same PR nets to no diff), so provenance lookup always missed
    # and fell back to "Unknown" even though the commit was really in the PR.
    path_for_current_sha = current_path
    for line in result.stdout.splitlines():
        if line.startswith("commit:"):
            if current_sha:
                newest_first.append((current_sha, path_for_current_sha))
            current_sha = line.removeprefix("commit:")
            path_for_current_sha = current_path
            continue
        fields = line.split("\t")
        if len(fields) == 3 and fields[0].startswith(("R", "C")):
            old_path, new_path = fields[1], fields[2]
            if new_path == current_path:
                current_path = old_path
    if current_sha:
        newest_first.append((current_sha, path_for_current_sha))
    return list(reversed(newest_first))


def _profile(user: object, fallback: str = "Unknown") -> Profile:
    if not isinstance(user, dict):
        return Profile(fallback)
    name = str(user.get("login") or fallback)
    return Profile(name=name, url=str(user.get("html_url") or ""))


# Duplicate approvals submitted during the 2026-09-02 merge sweep after another
# reviewer had already completed each review. Ignore these exact records only;
# all earlier and later activity by the same user remains eligible for credit.
IGNORED_REVIEW_IDS = frozenset(
    {
        5094869424,
        5094869655,
        5094869883,
        5094870122,
        5094870374,
        5094870569,
        5094870893,
        5094871121,
        5095252242,
        5095252387,
        5095252571,
        5095252899,
        5095253164,
        5095253445,
        5095253633,
    }
)


def _reviewers(client: GitHubClient, number: int, contributor: Profile) -> tuple[Profile, ...]:
    """Credit recorded human review and feedback activity, never merge ownership alone."""
    users: dict[str, Profile] = {}
    for path in (
        f"pulls/{number}/reviews?per_page=100",
        f"pulls/{number}/comments?per_page=100",
        f"issues/{number}/comments?per_page=100",
    ):
        records = client.get(path)
        for record in records if isinstance(records, list) else []:
            if not isinstance(record, dict):
                continue
            if "/reviews?" in path and record.get("id") in IGNORED_REVIEW_IDS:
                continue
            profile = _profile(record.get("user"), "")
            key = profile.name.casefold()
            if (
                not profile.name
                or key == contributor.name.casefold()
                or profile.name.lower().endswith("[bot]")
            ):
                continue
            users.setdefault(key, profile)
    return tuple(users[key] for key in sorted(users))


def _with_legacy_reviewers(
    origin_label: str, reviewers: tuple[Profile, ...]
) -> tuple[Profile, ...]:
    return reviewers or LEGACY_REVIEWERS.get(origin_label, ())


def load_task_provenance(
    repo: Path,
    tasks: list[Task],
    client: GitHubClient,
    history_loader: Callable[[Path, Path], list[tuple[str, str]]] = _git_history,
) -> dict[Path, TaskProvenance]:
    """Resolve each task to the PR (or direct commit) that introduced its manifest."""
    result: dict[Path, TaskProvenance] = {}
    for task in tasks:
        manifest = repo / task.path / "task.toml"
        history = history_loader(repo, manifest)
        provenance: TaskProvenance | None = None
        for sha, historical_path in history:
            pulls = client.get(f"commits/{sha}/pulls?per_page=100")
            candidates = pulls if isinstance(pulls, list) else []
            if not candidates:
                commit = client.get(f"commits/{sha}")
                commit_data = commit if isinstance(commit, dict) else {}
                author = commit_data.get("author")
                fallback = str(
                    ((commit_data.get("commit") or {}).get("author") or {}).get("name")
                    or "Unknown"
                )
                contributor = _profile(author, fallback)
                origin_label = f"commit {sha[:7]}"
                provenance = TaskProvenance(
                    contributor=contributor,
                    reviewers=_with_legacy_reviewers(origin_label, ()),
                    origin_label=origin_label,
                    origin_url=f"{client.web_root}/commit/{sha}",
                )
                break
            for pull in sorted(
                (item for item in candidates if isinstance(item, dict) and item.get("merged_at")),
                key=lambda item: int(item.get("number", 0)),
            ):
                number = int(pull["number"])
                files = client.get(f"pulls/{number}/files?per_page=100")
                if not any(
                    isinstance(item, dict)
                    and historical_path in (item.get("filename"), item.get("previous_filename"))
                    for item in (files if isinstance(files, list) else [])
                ):
                    continue
                details = client.get(f"pulls/{number}")
                pull_details = details if isinstance(details, dict) else pull
                contributor = _profile(pull_details.get("user"))
                origin_label = f"PR #{number}"
                provenance = TaskProvenance(
                    contributor=contributor,
                    reviewers=_with_legacy_reviewers(
                        origin_label, _reviewers(client, number, contributor)
                    ),
                    origin_label=origin_label,
                    origin_url=str(
                        pull_details.get("html_url") or f"{client.web_root}/pull/{number}"
                    ),
                )
                break
            if provenance is not None:
                break
        result[task.path] = provenance or TaskProvenance(
            contributor=Profile("Unknown"), reviewers=(), origin_label="Unknown", origin_url=""
        )
    return result


def _surface(path: Path, meta: dict) -> str:
    candidates = (path.name, str(meta.get("task", {}).get("name", "")))
    for candidate in candidates:
        for surface in SURFACES:
            if candidate.endswith(f"-{surface}"):
                return surface
    definition = str(meta.get("environment", {}).get("definition", "")).lower()
    return next((surface for surface in SURFACES if surface in definition), "other")


def _persona(task_dir: Path) -> Persona:
    data = yaml.safe_load((task_dir / "persona.yaml").read_text(encoding="utf-8")) or {}
    return Persona(
        persona_id=str(data.get("persona_id") or "unknown"),
        source=str(data.get("source") or "unspecified"),
    )


def load_tasks(repo: Path) -> list[Task]:
    tasks: list[Task] = []
    for bucket in ("single-attribute", "multi-attribute"):
        root = repo / "tasks" / bucket
        for manifest in sorted(root.rglob("task.toml")):
            meta = tomllib.loads(manifest.read_text(encoding="utf-8"))
            checks = []
            for raw in meta.get("checks", []):
                value = raw.get("value", raw.get("anchor_value"))
                dimension_id = raw.get("dimension_id")
                if dimension_id and value is not None:
                    checks.append(Check(str(dimension_id), str(value)))
            tasks.append(
                Task(
                    bucket=bucket,
                    path=manifest.parent.relative_to(repo),
                    surface=_surface(manifest.parent, meta),
                    checks=tuple(checks),
                    persona=_persona(manifest.parent),
                )
            )
    return tasks


def load_schema(repo: Path) -> tuple[dict[str, dict], int]:
    data = json.loads((repo / "evaluation" / "src" / "persona" / "schema" / "dimensions.json").read_text(encoding="utf-8"))
    dimensions = {item["id"]: item for item in data["dimensions"]}
    return dimensions, sum(len(item.get("values", [])) for item in dimensions.values())


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _task_link(task: Task) -> str:
    # Root-relative, not absolute: an issue body resolves "/<owner>/<repo>/..."
    # against github.com, so this is the shortest form that still clicks through.
    # A bare "/tasks/..." would NOT work here -- issue bodies do not resolve
    # repo-relative paths the way a README does.
    url = f"{GITHUB_PATH}/tree/main/{task.path.as_posix()}"
    return f"[{task.path.name}]({url})"


def _markdown_link(label: str, url: str) -> str:
    escaped = _escape(label)
    return f"[{escaped}]({url})" if url else escaped


DOC_PATH = "docs/task-coverage.md"
DOC_URL = f"{GITHUB_PATH}/blob/main/{DOC_PATH}"

_MANAGED_BY = "<!-- Managed by .github/workflows/task-coverage-issue.yml. Do not edit manually. -->"
_INTRO = [
    "> This is the contributor-facing source of truth for merged coverage.",
    "> Repeating a pair is allowed when it adds a meaningfully different scenario or",
    "> behavioral pressure, but uncovered pairs are preferred to broaden the benchmark.",
]


@dataclasses.dataclass(frozen=True)
class Coverage:
    """The aggregates every section is rendered from."""

    tasks: list[Task]
    by_bucket: collections.Counter
    by_surface: dict[str, collections.Counter]
    pair_tasks: dict[Check, list[Task]]
    persona_tasks: dict[Persona, list[Task]]


def _aggregate(tasks: list[Task]) -> Coverage:
    pair_tasks: dict[Check, list[Task]] = collections.defaultdict(list)
    persona_tasks: dict[Persona, list[Task]] = collections.defaultdict(list)
    for task in tasks:
        persona_tasks[task.persona].append(task)
        for check in task.checks:
            pair_tasks[check].append(task)
    return Coverage(
        tasks=tasks,
        by_bucket=collections.Counter(task.bucket for task in tasks),
        by_surface={
            bucket: collections.Counter(task.surface for task in tasks if task.bucket == bucket)
            for bucket in ("single-attribute", "multi-attribute")
        },
        pair_tasks=pair_tasks,
        persona_tasks=persona_tasks,
    )


def _snapshot_lines(cov: Coverage, dimensions: dict[str, dict], schema_value_count: int) -> list[str]:
    total = len(cov.tasks)
    covered = {check.dimension_id for check in cov.pair_tasks}
    lines = [
        "",
        "## Snapshot",
        "",
        f"- **{total} task implementations:** {cov.by_bucket['single-attribute']} single-attribute "
        f"+ {cov.by_bucket['multi-attribute']} multi-attribute",
        f"- **{len(cov.pair_tasks)} unique attribute-value pairs** across "
        f"**{len(covered)}/{len(dimensions)} dimensions**",
        f"- **{len(cov.persona_tasks)} unique persona IDs** used across {total} task implementations",
        f"- Attribute-value reach: **{len(cov.pair_tasks)}/{schema_value_count}** schema values",
        "",
        "| Type | Survey | Chat | Web | App | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for bucket, label in (("single-attribute", "Single"), ("multi-attribute", "Multi")):
        counts = cov.by_surface[bucket]
        lines.append(
            f"| {label} | {counts['survey']} | {counts['chat']} | {counts['web']} | "
            f"{counts['app']} | **{cov.by_bucket[bucket]}** |"
        )
    return lines


def _footer_lines(revision: str) -> list[str]:
    if revision:
        return ["", "---", "", f"Updated automatically from [`{revision[:7]}`]({GITHUB_ROOT}/commit/{revision}).", ""]
    return ["", "---", "", "Generated automatically from committed `task.toml` and `persona.yaml` files.", ""]


def render_issue_body(
    tasks: list[Task],
    dimensions: dict[str, dict],
    schema_value_count: int,
    revision: str = "",
) -> str:
    """The pinned issue: headline numbers and a pointer to the full tables.

    GitHub caps an issue body at MAX_ISSUE_BODY_BYTES, and the per-attribute,
    per-contribution and per-persona tables outgrew that ceiling -- which is how
    the tracker silently stopped updating. They live in the repository now, where
    nothing truncates them; this body stays a fixed handful of lines regardless
    of how far the benchmark grows.
    """
    cov = _aggregate(tasks)
    lines = [_MANAGED_BY, "# PersonaBench task coverage", "", *_INTRO]
    lines += _snapshot_lines(cov, dimensions, schema_value_count)
    lines += [
        "",
        "## Full coverage tables",
        "",
        f"Measured attributes, task contributions and the persona inventory live in "
        f"[`{DOC_PATH}`]({DOC_URL}), regenerated on every merge that touches tasks.",
        "",
        "Search that file for a dimension ID, value, or persona ID before proposing a task.",
    ]
    lines += _footer_lines(revision)
    return "\n".join(lines)


def render_document(
    tasks: list[Task],
    dimensions: dict[str, dict],
    schema_value_count: int,
    revision: str = "",
    provenance: dict[Path, TaskProvenance] | None = None,
) -> str:
    """The committed document: every table, in full, with per-task links."""
    cov = _aggregate(tasks)
    lines = [
        _MANAGED_BY,
        "# PersonaBench task coverage",
        "",
        *_INTRO,
        "",
        f"Headline numbers are mirrored in the pinned tracker issue ({GITHUB_ROOT}/issues/35).",
    ]

    if provenance is not None:
        by_origin: dict[TaskProvenance, list[Task]] = collections.defaultdict(list)
        for task in tasks:
            item = provenance.get(task.path)
            if item is None:
                item = TaskProvenance(Profile("Unknown"), (), "Unknown", "")
            by_origin[item].append(task)
        lines.extend(
            [
                "",
                f"## Task contributions ({len(tasks)})",
                "",
                "Contributor means the author of the PR or direct commit that introduced each task. "
                "Reviewer credit comes from recorded non-author human review activity: submitted reviews, "
                "inline code-review comments, or PR feedback comments. Merge ownership alone does not count. "
                "Explicit overrides cover the initial task imports that predate consistent review assignment; "
                "new contributions use GitHub activity only. A dash means no qualifying reviewer is known.",
                "",
                "Tasks introduced together share one row. The count makes each contribution directly measurable.",
                "",
                "| Task(s) | Count | Contributor | Reviewer(s) | Origin |",
                "|---|---:|---|---|---|",
            ]
        )
        for item, matching in sorted(
            by_origin.items(),
            key=lambda entry: (-len(entry[1]), entry[0].contributor.name.casefold(), entry[0].origin_label),
        ):
            reviewer_text = " · ".join(
                _markdown_link(profile.name, profile.url) for profile in item.reviewers
            ) or "—"
            task_text = " · ".join(
                _task_link(task) for task in sorted(matching, key=lambda task: task.path.as_posix())
            )
            lines.append(
                f"| {task_text} | **{len(matching)}** | "
                f"{_markdown_link(item.contributor.name, item.contributor.url)} "
                f"| {reviewer_text} | {_markdown_link(item.origin_label, item.origin_url)} |"
            )

    lines += _snapshot_lines(cov, dimensions, schema_value_count)
    lines.extend(
        [
            "",
            "## Measured attributes",
            "",
            "Search this file for a dimension ID, value, or persona ID before proposing a task.",
            "",
            "| Attribute | Value | Persona(s) | Single | Multi | Total | Tasks |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )

    def pair_sort(item: tuple[Check, list[Task]]) -> tuple[str, str, str]:
        check, _ = item
        dim = dimensions.get(check.dimension_id, {})
        return (str(dim.get("category", "Unknown")), str(dim.get("label", check.dimension_id)), check.value)

    for check, matching in sorted(cov.pair_tasks.items(), key=pair_sort):
        dim = dimensions.get(check.dimension_id, {})
        label = _escape(str(dim.get("label", check.dimension_id)))
        category = _escape(str(dim.get("category", "Unknown")))
        personas = sorted({task.persona.persona_id for task in matching})
        persona_text = "<br>".join(f"`{_escape(persona_id)}`" for persona_id in personas)
        single_count = sum(task.bucket == "single-attribute" for task in matching)
        multi_count = sum(task.bucket == "multi-attribute" for task in matching)
        task_links = " · ".join(
            _task_link(task)
            for task in sorted(matching, key=lambda task: (task.bucket, task.surface, task.path.as_posix()))
        )
        lines.append(
            f"| **{label}**<br><sub>{_escape(check.dimension_id)} · {category}</sub> "
            f"| {_escape(check.value)} | {persona_text} | {single_count} | {multi_count} "
            f"| **{len(matching)}** | {task_links} |"
        )

    lines.extend(
        [
            "",
            "<details>",
            f"<summary><strong>Persona inventory ({len(cov.persona_tasks)})</strong></summary>",
            "",
            "| Persona ID | Source | Task implementations | Attribute-values |",
            "|---|---|---:|---|",
        ]
    )
    for persona, matching in sorted(cov.persona_tasks.items(), key=lambda item: item[0].persona_id):
        checks = sorted({f"{check.dimension_id}={check.value}" for task in matching for check in task.checks})
        lines.append(
            f"| `{_escape(persona.persona_id)}` | {_escape(persona.source)} | **{len(matching)}** "
            f"| {'<br>'.join(f'`{_escape(check)}`' for check in checks)} |"
        )
    lines.extend(["", "</details>"])
    lines += _footer_lines(revision)
    return "\n".join(lines)


def generate(
    repo: Path = REPO,
    revision: str = "",
    provenance: dict[Path, TaskProvenance] | None = None,
) -> str:
    """The committed document -- every table, no size ceiling."""
    tasks = load_tasks(repo)
    dimensions, schema_value_count = load_schema(repo)
    return render_document(tasks, dimensions, schema_value_count, revision, provenance)


def generate_issue_body(repo: Path = REPO, revision: str = "") -> str:
    """The pinned issue body -- headline numbers and a link to the document."""
    tasks = load_tasks(repo)
    dimensions, schema_value_count = load_schema(repo)
    return render_issue_body(tasks, dimensions, schema_value_count, revision)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help=f"write the full document here instead of stdout (committed as {DOC_PATH})",
    )
    parser.add_argument(
        "--issue-output",
        type=Path,
        help="also write the short pinned-issue body here (Snapshot plus a link "
             "to the document); GitHub rejects an issue body over "
             f"{MAX_ISSUE_BODY_BYTES:,} bytes, which is why the tables live in a file",
    )
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument(
        "--with-github-attribution",
        action="store_true",
        help="add contributor/reviewer provenance using Git history and the GitHub API",
    )
    parser.add_argument(
        "--github-repository",
        default=os.environ.get("GITHUB_REPOSITORY", "MatrAIx-ai/Agent_PersonaBench"),
        help="GitHub owner/name (default: GITHUB_REPOSITORY)",
    )
    args = parser.parse_args(argv)
    all_tasks = load_tasks(REPO)
    provenance = None
    if args.with_github_attribution:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        provenance = load_task_provenance(
            REPO, all_tasks, GitHubClient(args.github_repository, token)
        )
    dimensions, schema_value_count = load_schema(REPO)
    document = render_document(
        all_tasks, dimensions, schema_value_count, args.revision, provenance
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding="utf-8")
        print(f"wrote {args.output} ({len(document.encode('utf-8')):,} bytes)")
    else:
        sys.stdout.write(document)

    if args.issue_output:
        body = render_issue_body(all_tasks, dimensions, schema_value_count, args.revision)
        size = len(body.encode("utf-8"))
        args.issue_output.parent.mkdir(parents=True, exist_ok=True)
        args.issue_output.write_text(body, encoding="utf-8")
        print(f"wrote {args.issue_output} ({size:,} bytes, limit {MAX_ISSUE_BODY_BYTES:,})")
        if size > MAX_ISSUE_BODY_BYTES:
            # Fail here rather than let `gh issue edit` fail with an opaque
            # "GraphQL: Body is too long (updateIssue)" after the body is built.
            print(
                f"error: issue body is {size:,} bytes, over GitHub's "
                f"{MAX_ISSUE_BODY_BYTES:,}-byte limit by {size - MAX_ISSUE_BODY_BYTES:,}. "
                f"Keep render_issue_body() to a summary -- the tables belong in "
                f"{DOC_PATH}.",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
