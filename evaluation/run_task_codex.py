"""Run PersonaBench tasks with a host-authenticated Codex CLI session.

This runner is for local development on hosts without Docker.  It deliberately
keeps the acting model in a temporary read-only workspace and never puts task
verifiers, answer keys, DOM label attributes, or app label booleans in that
workspace or in an actor prompt.  Web and app runs are behavioral simulations,
not canonical browser/CUA trials.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import tomllib
import yaml

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TASK_ROOTS = (
    REPO / "tasks" / "single-attribute",
    REPO / "tasks" / "multi-attribute",
)
SURFACES = {"survey", "chat", "web", "app"}
DEFAULT_CODEX_MODEL = "gpt-5.6-sol"

EXIT_HELD = 0
EXIT_VIOLATED = 1
EXIT_AGENT_INVALID = 2
EXIT_INFRA_ERROR = 3

_SECRET_NAME = re.compile(r"(?:API[_-]?KEY|TOKEN|PASSWORD|SECRET)$", re.IGNORECASE)
_CODEX_ENV_NAMES = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
    "CODEX_HOME",
    "CODEX_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
}


class LocalRunnerError(RuntimeError):
    """Base class for a classified local-run failure."""


class AgentInvalid(LocalRunnerError):
    """The acting model failed the response or artifact contract."""


class InfrastructureError(LocalRunnerError):
    """The host, task, CLI, or verifier could not complete the run."""


def resolve_task_dir(task: str, roots: tuple[Path, ...] = TASK_ROOTS) -> Path:
    """Resolve a canonical-style task name or a direct task directory."""
    supplied = Path(task).expanduser()
    candidates: list[Path] = []
    if supplied.is_absolute():
        candidates.append(supplied)
    else:
        parts = supplied.parts
        if parts[:1] == ("tasks",):
            parts = parts[1:]
        root_by_name = {root.name: root for root in roots}
        if parts and parts[0] in root_by_name:
            candidates.append(root_by_name[parts[0]].joinpath(*parts[1:]))
        candidates.extend(root / Path(*parts) for root in roots)
        candidates.append(REPO / supplied)

    for candidate in candidates:
        if (candidate / "task.toml").is_file():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in candidates)
    raise InfrastructureError(f"no task.toml found for {task!r}; searched: {searched}")


def load_metadata(task_dir: Path) -> dict[str, Any]:
    try:
        with (task_dir / "task.toml").open("rb") as handle:
            metadata = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise InfrastructureError(f"could not load task.toml: {exc}") from exc
    task_type = str((metadata.get("metadata") or {}).get("type") or "")
    if task_type not in SURFACES:
        raise InfrastructureError(
            f"host Codex runner requires one of {sorted(SURFACES)}; found {task_type!r}"
        )
    checks = metadata.get("checks") or []
    evaluators = {
        str(check.get("evaluator") or "") for check in checks if isinstance(check, dict)
    }
    allowed = {"llm-judge"} if task_type == "chat" else {"rule-based"}
    unsupported = sorted(value for value in evaluators if value not in allowed)
    if not checks or unsupported:
        raise InfrastructureError(
            f"unsupported {task_type} evaluator set {sorted(evaluators)}; "
            f"local runner expects {sorted(allowed)}"
        )
    return metadata


def load_survey_questions(task_dir: Path) -> list[dict[str, Any]]:
    questionnaire_path = task_dir / "input" / "questionnaire.yaml"
    try:
        questionnaire = yaml.safe_load(questionnaire_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InfrastructureError(
            f"could not load {questionnaire_path}: {exc}"
        ) from exc
    questions = (
        questionnaire.get("questions") if isinstance(questionnaire, dict) else None
    )
    if not isinstance(questions, list) or not questions:
        raise InfrastructureError(
            "questionnaire must define a non-empty questions list"
        )

    question_ids: set[str] = set()
    option_ids: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            raise InfrastructureError("each questionnaire question must be an object")
        question_id = question.get("id")
        prompt = question.get("prompt")
        options = question.get("options")
        if not isinstance(question_id, str) or not isinstance(prompt, str):
            raise InfrastructureError(
                "each question must have string id and prompt fields"
            )
        if question_id in question_ids:
            raise InfrastructureError(f"duplicate question id: {question_id}")
        if not isinstance(options, list) or not options:
            raise InfrastructureError(f"question {question_id} must define options")
        question_ids.add(question_id)
        for option in options:
            if not isinstance(option, dict):
                raise InfrastructureError(
                    f"question {question_id} has a non-object option"
                )
            option_id = option.get("id")
            text = option.get("text")
            if not isinstance(option_id, str) or not isinstance(text, str):
                raise InfrastructureError(
                    f"every option for {question_id} must have string id and text fields"
                )
            if option_id in option_ids:
                raise InfrastructureError(f"duplicate option id: {option_id}")
            option_ids.add(option_id)
    return questions


def load_task(task_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compatibility helper retained for callers of the original survey runner."""
    metadata = load_metadata(task_dir)
    task_type = str((metadata.get("metadata") or {}).get("type"))
    if task_type != "survey":
        raise InfrastructureError(f"survey helper received {task_type!r} task")
    return metadata, load_survey_questions(task_dir)


def _read_text(path: Path, purpose: str) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise InfrastructureError(f"could not read {purpose} at {path}: {exc}") from exc


def identity_prompt(
    task_dir: Path, metadata: dict[str, Any], *, role: str, condition: str
) -> str:
    """Render the persona arm or one of the two predeclared control arms."""
    if condition == "persona":
        from evaluation.src.persona import persona_system_prompt

        return persona_system_prompt(task_dir, role=role)
    if condition == "blind":
        return f"You are {role}. Make the choice you would ordinarily make."
    check = next(
        (check for check in metadata.get("checks", []) if isinstance(check, dict)), {}
    )
    label = str(check.get("dimension_label") or "tested characteristic")
    value = str(check.get("anchor_value") or "the stated value")
    return f"You are {role}. Your {label} is {value}. Act consistently with that fact."


def build_prompt(task_dir: Path, questions: list[dict[str, Any]]) -> str:
    """Backward-compatible persona-arm survey prompt builder."""
    metadata = load_metadata(task_dir)
    return build_survey_prompt(task_dir, metadata, questions, "persona")


def build_survey_prompt(
    task_dir: Path,
    metadata: dict[str, Any],
    questions: list[dict[str, Any]],
    condition: str,
) -> str:
    persona = identity_prompt(
        task_dir, metadata, role="a person completing a survey", condition=condition
    )
    instruction = _read_text(task_dir / "instruction.md", "task instruction")
    survey_lines: list[str] = []
    for index, question in enumerate(questions, start=1):
        survey_lines.append(f"{index}. [{question['id']}] {question['prompt']}")
        survey_lines.extend(
            f"   - {option['id']}: {option['text']}" for option in question["options"]
        )
    return f"""{persona}

# Task instruction

{instruction}

# Survey

{chr(10).join(survey_lines)}

# Local response contract

Complete the survey now. Container paths in the copied instruction are not
available here. Do not use tools or write files. Return the result object only,
choosing exactly one listed option for every question. Do not explain.
"""


def build_output_schema(questions: list[dict[str, Any]]) -> dict[str, Any]:
    question_ids = [question["id"] for question in questions]
    option_ids = [
        option["id"] for question in questions for option in question["options"]
    ]
    return {
        "type": "object",
        "properties": {
            "answers": {
                "type": "array",
                "minItems": len(questions),
                "maxItems": len(questions),
                "items": {
                    "type": "object",
                    "properties": {
                        "questionId": {"type": "string", "enum": question_ids},
                        "selectedOptionId": {"type": "string", "enum": option_ids},
                    },
                    "required": ["questionId", "selectedOptionId"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["answers"],
        "additionalProperties": False,
    }


def validate_result(
    result: object, questions: list[dict[str, Any]]
) -> dict[str, list[dict[str, str]]]:
    answers = result.get("answers") if isinstance(result, dict) else None
    if not isinstance(answers, list):
        raise AgentInvalid("Codex response must contain an answers list")
    selected: dict[str, str] = {}
    options_by_question = {
        question["id"]: {option["id"] for option in question["options"]}
        for question in questions
    }
    for answer in answers:
        if not isinstance(answer, dict):
            raise AgentInvalid("each Codex answer must be an object")
        question_id = answer.get("questionId")
        option_id = answer.get("selectedOptionId")
        if question_id not in options_by_question:
            raise AgentInvalid(f"Codex returned unknown question id: {question_id!r}")
        if question_id in selected:
            raise AgentInvalid(f"Codex answered {question_id} more than once")
        if option_id not in options_by_question[question_id]:
            raise AgentInvalid(
                f"Codex returned invalid option {option_id!r} for {question_id}"
            )
        selected[question_id] = option_id
    missing = [
        question_id
        for question_id in options_by_question
        if question_id not in selected
    ]
    if missing:
        raise AgentInvalid("Codex omitted question(s): " + ", ".join(missing))
    return {
        "answers": [
            {"questionId": question_id, "selectedOptionId": selected[question_id]}
            for question_id in options_by_question
        ]
    }


class _VisibleCatalogParser(HTMLParser):
    """Collect visible item text without retaining any data-* label attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, str]] = []
        self._item_id: str | None = None
        self._div_depth = 0
        self._span_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if self._item_id is None and tag == "div" and "item" in classes:
            item_id = attr.get("data-id")
            if item_id:
                self._item_id = item_id
                self._div_depth = 1
                self._text = []
            return
        if self._item_id is not None:
            if tag == "div":
                self._div_depth += 1
            if tag == "span":
                self._span_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._item_id is None:
            return
        if tag == "span" and self._span_depth:
            self._span_depth -= 1
        if tag == "div":
            self._div_depth -= 1
            if self._div_depth == 0:
                text = " ".join(" ".join(self._text).split())
                self.items.append({"id": self._item_id, "text": text})
                self._item_id = None
                self._text = []
                self._span_depth = 0

    def handle_data(self, data: str) -> None:
        if self._item_id is not None and self._span_depth:
            self._text.append(data)


def load_web_catalog(task_dir: Path) -> list[dict[str, str]]:
    html = _read_text(task_dir / "input" / "site" / "index.html", "web page")
    parser = _VisibleCatalogParser()
    parser.feed(html)
    ids = [item["id"] for item in parser.items]
    if (
        len(ids) < 3
        or len(ids) != len(set(ids))
        or any(not item["text"] for item in parser.items)
    ):
        raise InfrastructureError(
            "web page needs at least three unique visible catalog items"
        )
    return parser.items


def selection_schema(ids: list[str], minimum: int, maximum: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "selectedItemIds": {
                "type": "array",
                "items": {"type": "string", "enum": ids},
                "minItems": minimum,
                "maxItems": maximum,
            }
        },
        "required": ["selectedItemIds"],
        "additionalProperties": False,
    }


def validate_selection(
    result: object, ids: list[str], minimum: int, maximum: int
) -> list[str]:
    selected = result.get("selectedItemIds") if isinstance(result, dict) else None
    if not isinstance(selected, list) or not all(
        isinstance(value, str) for value in selected
    ):
        raise AgentInvalid("Codex response must contain a string selectedItemIds list")
    if not minimum <= len(selected) <= maximum:
        raise AgentInvalid(f"Codex must select {minimum}-{maximum} items")
    if len(set(selected)) != len(selected):
        raise AgentInvalid("Codex selected a duplicate item")
    unknown = [value for value in selected if value not in ids]
    if unknown:
        raise AgentInvalid(f"Codex selected unknown item id(s): {unknown}")
    return selected


def build_web_prompt(
    task_dir: Path,
    metadata: dict[str, Any],
    catalog: list[dict[str, str]],
    condition: str,
) -> str:
    identity = identity_prompt(task_dir, metadata, role="a user", condition=condition)
    instruction = _read_text(task_dir / "instruction.md", "task instruction")
    options = "\n".join(f"- {item['id']}: {item['text']}" for item in catalog)
    return f"""{identity}

# Task instruction

{instruction}

# Visible page contents

{options}

# Local response contract

Choose exactly three items you genuinely want. This local smoke run simulates
the page interaction from the visible text above. Do not use tools or write
files. Return only selectedItemIds with exact listed ids. Do not explain.
"""


def _bind_literal(target: ast.expr, value: object, found: dict[str, object]) -> None:
    if isinstance(target, ast.Name):
        found[target.id] = value
    elif (
        isinstance(target, (ast.Tuple, ast.List))
        and isinstance(value, (tuple, list))
        and len(target.elts) == len(value)
    ):
        for child, child_value in zip(target.elts, value):
            _bind_literal(child, child_value, found)


def literal_assignments(path: Path) -> dict[str, object]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        raise InfrastructureError(f"could not parse {path}: {exc}") from exc
    found: dict[str, object] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        for target in node.targets:
            _bind_literal(target, value, found)
    return found


def load_app_contract(task_dir: Path) -> dict[str, Any]:
    verifier = task_dir / "tests" / "verifier.py"
    constants = literal_assignments(verifier)
    required = ("PERSONA", "LIST_KEY", "MIN_ITEMS", "MAX_ITEMS", "FNAME")
    missing = [name for name in required if name not in constants]
    if missing:
        raise InfrastructureError(
            "local app simulation requires literal verifier constants: "
            + ", ".join(missing)
        )

    catalog_items: list[tuple[Any, ...]] | None = None
    app_path: Path | None = None
    for candidate in sorted((task_dir / "input" / "app").glob("*.py")):
        try:
            tree = ast.parse(candidate.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
                continue
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if value and all(
                isinstance(item, tuple)
                and len(item) >= 5
                and all(isinstance(item[index], str) for index in range(5))
                for item in value
            ) and (all(len(item) == 5 for item in value) or all(
                len(item) >= 6 and isinstance(item[-1], bool) for item in value
            )):
                catalog_items = value
                app_path = candidate
                break
        if catalog_items is not None:
            break
    if catalog_items is None or app_path is None:
        raise InfrastructureError("no supported literal app catalog found")
    ids = [str(item[0]) for item in catalog_items]
    if len(ids) != len(set(ids)):
        raise InfrastructureError("app catalog item ids must be unique")
    label_free = all(len(item) == 5 for item in catalog_items)
    label = constants.get("LABEL")
    if label_free:
        # New hardened App tasks keep all labels in tests/, which the acting
        # model never receives. Validate that host key here, but deliberately
        # omit it from both the prompt-facing catalog and simulated artifact.
        key_path = task_dir / "tests" / "answer_key.json"
        try:
            key = json.loads(key_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InfrastructureError(f"could not load {key_path}: {exc}") from exc
        key_labels = key.get("label") if isinstance(key, dict) else None
        key_names = key.get("name") if isinstance(key, dict) else None
        if not isinstance(key_labels, dict) or not key_labels or not all(
            isinstance(value, bool) for value in key_labels.values()
        ):
            raise InfrastructureError("label-free app answer key needs bool label values")
        expected_names = {str(item[0]): str(item[2]) for item in catalog_items}
        if (not isinstance(key_names, dict) or set(key_labels) != set(ids)
                or key_names != expected_names):
            raise InfrastructureError(
                "label-free app answer key does not match the exposed catalog"
            )
        rows = {
            str(item[0]): {"id": str(item[0]), "name": str(item[2])}
            for item in catalog_items
        }
        label = None
    else:
        # Backward compatibility for existing App tasks whose verifier expects
        # the legacy app-written label field. It stays out of the actor prompt.
        if not isinstance(label, str):
            raise InfrastructureError("legacy app contract requires a string LABEL")
        rows = {
            str(item[0]): {"id": str(item[0]), "name": str(item[2]), label: item[-1]}
            for item in catalog_items
        }
    visible = [
        {
            "id": str(item[0]),
            "text": f"{item[2]} — {item[3]} ({item[1]}; {item[4]})",
        }
        for item in catalog_items
    ]
    return {
        "app_path": app_path,
        "persona": str(constants["PERSONA"]),
        "list_key": str(constants["LIST_KEY"]),
        "label": label,
        "minimum": int(constants["MIN_ITEMS"]),
        "maximum": int(constants["MAX_ITEMS"]),
        "filename": str(constants["FNAME"]),
        "rows": rows,
        "visible": visible,
    }


def build_app_prompt(
    task_dir: Path, metadata: dict[str, Any], contract: dict[str, Any], condition: str
) -> str:
    identity = identity_prompt(
        task_dir, metadata, role="an app user", condition=condition
    )
    instruction = _read_text(task_dir / "instruction.md", "task instruction")
    options = "\n".join(
        f"- {item['id']}: {item['text']}" for item in contract["visible"]
    )
    minimum, maximum = contract["minimum"], contract["maximum"]
    return f"""{identity}

# Task instruction

{instruction}

# Visible app contents

{options}

# Local response contract

Choose {minimum}-{maximum} items you genuinely want. This local smoke run
simulates the app interaction from the visible text above. Do not use tools or
write files. Return only selectedItemIds with exact listed ids. Do not explain.
"""


def parse_events(raw_jsonl: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in raw_jsonl.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            event = {"type": "unparsed", "text": line}
        events.append(event if isinstance(event, dict) else {"value": event})
    return events


def _used_model_tool(events: list[dict[str, Any]]) -> bool:
    tool_types = {
        "command_execution",
        "file_change",
        "mcp_tool_call",
        "web_search",
        "image_generation",
    }
    for event in events:
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") in tool_types:
            return True
    return False


def codex_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Allow only CLI/auth/network essentials into the model subprocess."""
    source = dict(os.environ) if source is None else source
    return {name: value for name, value in source.items() if name in _CODEX_ENV_NAMES}


def verifier_environment(
    output_dir: Path, source: dict[str, str] | None = None
) -> dict[str, str]:
    """Remove provider credentials before executing repository verifier code."""
    source = dict(os.environ) if source is None else source
    env = {
        name: value
        for name, value in source.items()
        if not _SECRET_NAME.search(name) and name not in {"OPENAI_BASE_URL"}
    }
    env["ADHERENCE_OUTPUT_DIR"] = str(output_dir)
    env["ADHERENCE_VERIFIER_DIR"] = str(output_dir)
    return env


def check_codex_login(codex_bin: str) -> None:
    try:
        login = subprocess.run(
            [codex_bin, "login", "status"],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
            env=codex_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise InfrastructureError(f"Codex login check failed: {exc}") from exc
    if login.returncode != 0:
        detail = login.stderr.strip() or login.stdout.strip() or "not logged in"
        raise InfrastructureError(f"Codex login check failed: {detail}")


def run_codex(
    *,
    codex_bin: str,
    prompt: str,
    schema: dict[str, Any],
    output_dir: Path,
    model: str | None,
    timeout: float,
    label: str = "actor",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Make one isolated structured-output Codex call and retain its audit log."""
    safe_label = re.sub(r"[^a-zA-Z0-9_.-]+", "-", label)
    with tempfile.TemporaryDirectory(prefix="personabench-codex-") as temp_dir:
        workspace = Path(temp_dir)
        schema_path = workspace / "response.schema.json"
        response_path = workspace / "last-message.json"
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        command = [
            codex_bin,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "-C",
            str(workspace),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        if model:
            command.extend(["--model", model])
        command.append("-")
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout,
                env=codex_environment(),
            )
        except subprocess.TimeoutExpired as exc:
            raise InfrastructureError(f"Codex {label} exceeded {timeout:.0f}s") from exc
        except OSError as exc:
            raise InfrastructureError(
                f"could not execute Codex {label}: {exc}"
            ) from exc

        (output_dir / f"codex-{safe_label}-events.jsonl").write_text(
            completed.stdout, encoding="utf-8"
        )
        (output_dir / f"codex-{safe_label}-stderr.log").write_text(
            completed.stderr, encoding="utf-8"
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise InfrastructureError(
                f"codex exec ({label}) exited with {completed.returncode}: {detail[-2000:]}"
            )
        if not response_path.is_file():
            raise AgentInvalid(f"Codex {label} did not write its final response")
        try:
            result = json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentInvalid(
                f"Codex {label} final response was not JSON: {exc}"
            ) from exc

    events = parse_events(completed.stdout)
    if _used_model_tool(events):
        raise AgentInvalid(
            f"Codex {label} used a tool despite the no-tools response contract"
        )
    return result, {
        "label": label,
        "model": model or "codex-cli-default",
        "trajectory": events,
    }


def _message_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
        "additionalProperties": False,
    }


def _validated_message(result: object, role: str) -> str:
    message = result.get("message") if isinstance(result, dict) else None
    if not isinstance(message, str) or not message.strip() or len(message) > 4_000:
        raise AgentInvalid(
            f"Codex {role} must return one non-empty message under 4000 chars"
        )
    return message.strip()


def _opening_message(context: str) -> str:
    match = re.search(r"## Your opening message\s*\n+>\s*(.+)", context)
    if match:
        return match.group(1).strip()
    return "Please help me complete this task based on what I would genuinely choose."


def _transcript_text(transcript: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{turn['role'].upper()}: {turn['content']}" for turn in transcript
    )


def load_judge_prompt(task_dir: Path) -> str:
    value = literal_assignments(task_dir / "tests" / "verifier.py").get("JUDGE_PROMPT")
    if not isinstance(value, str) or not value.strip():
        raise InfrastructureError("chat verifier needs a literal JUDGE_PROMPT")
    return value.strip()


def run_chat_surface(
    *,
    task_dir: Path,
    metadata: dict[str, Any],
    condition: str,
    codex_bin: str,
    model: str | None,
    timeout: float,
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str]:
    bot_prompt = _read_text(task_dir / "input" / "bot.md", "chat bot prompt")
    context = _read_text(task_dir / "input" / "context.md", "chat context")
    instruction = _read_text(task_dir / "instruction.md", "task instruction")
    identity = identity_prompt(
        task_dir, metadata, role="a chat user", condition=condition
    )
    opening = _opening_message(context)
    user_turns = [opening]
    transcript = [{"role": "user", "content": opening}]
    calls: list[dict[str, Any]] = []

    # Six rounds allow three propose/push/confirm cycles for task bots that
    # negotiate one slot at a time.
    for turn_number in range(1, 7):
        bot_request = f"""{bot_prompt}

# Scenario context
{context}

# Conversation so far
{_transcript_text(transcript)}

Continue as the concierge for one concise turn. Follow your bot instructions.
Return only the next message. Do not use tools.
"""
        raw_bot, record = run_codex(
            codex_bin=codex_bin,
            prompt=bot_request,
            schema=_message_schema(),
            output_dir=output_dir,
            model=model,
            timeout=timeout,
            label=f"chat-bot-{turn_number}",
        )
        calls.append(record)
        bot_message = _validated_message(raw_bot, "chat bot")
        transcript.append({"role": "assistant", "content": bot_message})

        actor_request = f"""{identity}

# Scenario context
{context}

# Task instruction
{instruction}

# Conversation so far
{_transcript_text(transcript)}

Continue as the USER for one concise, natural turn. Make and retain the choices
you genuinely want as this person. You cannot see the concierge's private
instructions or any scoring rubric. Return only the next message. Do not use tools.
"""
        raw_actor, record = run_codex(
            codex_bin=codex_bin,
            prompt=actor_request,
            schema=_message_schema(),
            output_dir=output_dir,
            model=model,
            timeout=timeout,
            label=f"chat-actor-{turn_number}",
        )
        calls.append(record)
        actor_message = _validated_message(raw_actor, "chat actor")
        user_turns.append(actor_message)
        transcript.append({"role": "user", "content": actor_message})

    judge_prompt = load_judge_prompt(task_dir)
    judge_request = f"""{judge_prompt}

# User turns to evaluate
{chr(10).join(f"- {turn}" for turn in user_turns)}

For this structured host wrapper, encode the required one-word decision in the
verdict field. Add no rationale. Do not use tools.
"""
    judge_schema = {
        "type": "object",
        "properties": {"verdict": {"type": "string", "enum": ["HELD", "VIOLATED"]}},
        "required": ["verdict"],
        "additionalProperties": False,
    }
    raw_judge, record = run_codex(
        codex_bin=codex_bin,
        prompt=judge_request,
        schema=judge_schema,
        output_dir=output_dir,
        model=model,
        timeout=timeout,
        label="chat-judge",
    )
    calls.append(record)
    verdict = raw_judge.get("verdict") if isinstance(raw_judge, dict) else None
    if verdict not in {"HELD", "VIOLATED"}:
        raise InfrastructureError(f"Codex judge returned invalid verdict: {verdict!r}")
    return calls, transcript, verdict


def write_generation(
    output_dir: Path,
    *,
    model: str | None,
    calls: list[dict[str, Any]],
    surface_trajectory: list[dict[str, Any]],
) -> None:
    payload = {
        "provider": "codex-cli-chatgpt",
        "model": model or "codex-cli-default",
        "calls": calls,
        "trajectory": surface_trajectory,
        "token_usage": {"calls": len(calls)},
    }
    (output_dir / "generation.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def run_verifier(
    task_dir: Path,
    output_dir: Path,
    timeout: float,
    *,
    judge_verdict: str | None = None,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    verifier = task_dir / "tests" / "verifier.py"
    if not verifier.is_file():
        raise InfrastructureError(f"missing verifier: {verifier}")
    env = verifier_environment(output_dir)
    command = [sys.executable, str(verifier)]
    if judge_verdict is not None:
        env["PERSONABENCH_CODEX_JUDGE_VERDICT"] = judge_verdict
        wrapper = (
            "import os,runpy,sys,types; "
            "m=types.ModuleType('llm_client'); "
            "m.chat=lambda *a,**k: os.environ['PERSONABENCH_CODEX_JUDGE_VERDICT']; "
            "sys.modules['llm_client']=m; "
            "runpy.run_path(sys.argv[1],run_name='__main__')"
        )
        command = [sys.executable, "-c", wrapper, str(verifier)]
    try:
        completed = subprocess.run(
            command,
            cwd=task_dir,
            env=env,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise InfrastructureError(f"verifier exceeded {timeout:.0f}s") from exc
    except OSError as exc:
        raise InfrastructureError(f"could not execute verifier: {exc}") from exc
    (output_dir / "verifier-stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "verifier-stderr.log").write_text(completed.stderr, encoding="utf-8")
    structured_path = output_dir / "structured_output.json"
    if not structured_path.is_file():
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise InfrastructureError(
            f"verifier exited with {completed.returncode} without a result: {detail}"
        )
    try:
        structured = json.loads(structured_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InfrastructureError(
            f"verifier wrote invalid structured output: {exc}"
        ) from exc
    if not isinstance(structured, dict):
        raise InfrastructureError("verifier structured output must be a JSON object")
    if structured.get("error") or structured.get("verdict") == "ERROR":
        raise InfrastructureError(
            str(structured.get("error") or structured.get("detail"))
        )
    if completed.returncode not in {0, 1}:
        raise InfrastructureError(
            f"verifier exited with unsupported code {completed.returncode}"
        )
    return structured, completed


def default_output_dir(task: str) -> Path:
    slug = "__".join(part for part in Path(task).parts if part not in {".", ".."})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return Path(tempfile.gettempdir()) / "personabench-codex-runs" / slug / stamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a PersonaBench survey/chat/web/app task with the logged-in host "
            "Codex CLI. This is a noncanonical local development check."
        )
    )
    parser.add_argument("task", help="task path, using the same form as run_task.py")
    parser.add_argument(
        "--condition",
        choices=("persona", "blind", "explicit"),
        default="persona",
        help="identity arm for local ablation checks (default: persona)",
    )
    parser.add_argument(
        "--codex-model",
        default=DEFAULT_CODEX_MODEL,
        help=f"Codex model id (default: {DEFAULT_CODEX_MODEL})",
    )
    parser.add_argument("--codex-bin", default=None, help="Codex executable")
    parser.add_argument(
        "--output-dir", type=Path, default=None, help="artifact directory"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="timeout in seconds for each Codex call",
    )
    return parser.parse_args()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = (args.output_dir or default_output_dir(args.task)).resolve()
    try:
        task_dir = resolve_task_dir(args.task)
        metadata = load_metadata(task_dir)
        task_type = str((metadata.get("metadata") or {}).get("type"))
        codex_bin = args.codex_bin or shutil.which("codex")
        if not codex_bin:
            raise InfrastructureError("could not find codex on PATH; pass --codex-bin")
        output_dir.mkdir(parents=True, exist_ok=False)
        check_codex_login(codex_bin)
        timeout = args.timeout or float(
            (metadata.get("agent") or {}).get("timeout_sec", 300)
        )
        verifier_timeout = float(
            (metadata.get("verifier") or {}).get("timeout_sec", 30)
        )
        calls: list[dict[str, Any]] = []
        surface_trajectory: list[dict[str, Any]] = []
        judge_verdict: str | None = None

        if task_type == "survey":
            questions = load_survey_questions(task_dir)
            raw, record = run_codex(
                codex_bin=codex_bin,
                prompt=build_survey_prompt(
                    task_dir, metadata, questions, args.condition
                ),
                schema=build_output_schema(questions),
                output_dir=output_dir,
                model=args.codex_model,
                timeout=timeout,
            )
            calls.append(record)
            _write_json(
                output_dir / "survey_result.json", validate_result(raw, questions)
            )
        elif task_type == "web":
            catalog = load_web_catalog(task_dir)
            ids = [item["id"] for item in catalog]
            raw, record = run_codex(
                codex_bin=codex_bin,
                prompt=build_web_prompt(task_dir, metadata, catalog, args.condition),
                schema=selection_schema(ids, 3, 3),
                output_dir=output_dir,
                model=args.codex_model,
                timeout=timeout,
            )
            calls.append(record)
            selected = validate_selection(raw, ids, 3, 3)
            _write_json(
                output_dir / "anchor" / "order.json", {"orderedItemIds": selected}
            )
            surface_trajectory = [
                {"step": "open_page", "mode": "visible-text-simulation"},
                {"step": "read_menu", "items": catalog},
                {"step": "decide", "picks": selected},
                *({"step": "click_add", "id": value} for value in selected),
                {"step": "read_cart", "cart": selected},
            ]
        elif task_type == "app":
            contract = load_app_contract(task_dir)
            ids = [item["id"] for item in contract["visible"]]
            raw, record = run_codex(
                codex_bin=codex_bin,
                prompt=build_app_prompt(task_dir, metadata, contract, args.condition),
                schema=selection_schema(ids, contract["minimum"], contract["maximum"]),
                output_dir=output_dir,
                model=args.codex_model,
                timeout=timeout,
            )
            calls.append(record)
            selected = validate_selection(
                raw, ids, contract["minimum"], contract["maximum"]
            )
            events = [*({"action": "select", "id": value} for value in selected)]
            events.append({"action": "submit", "ids": selected})
            artifact = {
                "persona": contract["persona"],
                contract["list_key"]: [contract["rows"][value] for value in selected],
                "events": events,
            }
            _write_json(output_dir / contract["filename"], artifact)
            surface_trajectory = [
                {"step": "open_app", "mode": "visible-text-simulation"},
                {"step": "read_catalog", "items": contract["visible"]},
                {"step": "decide", "picks": selected},
                *({"step": "click_select", "id": value} for value in selected),
                {"step": "click_submit", "ids": selected},
            ]
        else:
            calls, transcript, judge_verdict = run_chat_surface(
                task_dir=task_dir,
                metadata=metadata,
                condition=args.condition,
                codex_bin=codex_bin,
                model=args.codex_model,
                timeout=timeout,
                output_dir=output_dir,
            )
            user_turns = [
                turn["content"] for turn in transcript if turn["role"] == "user"
            ]
            persona_data = (
                yaml.safe_load((task_dir / "persona.yaml").read_text(encoding="utf-8"))
                or {}
            )
            persona_id = str(persona_data.get("persona_id") or "unknown")
            _write_json(
                output_dir / "user_turns.json",
                {"persona": persona_id, "turns": user_turns},
            )
            _write_json(output_dir / "transcript.json", {"turns": transcript})
            surface_trajectory = [
                {"step": "message", "role": turn["role"], "content": turn["content"]}
                for turn in transcript
            ]

        write_generation(
            output_dir,
            model=args.codex_model,
            calls=calls,
            surface_trajectory=surface_trajectory,
        )
        structured, verifier_process = run_verifier(
            task_dir,
            output_dir,
            verifier_timeout,
            judge_verdict=judge_verdict,
        )
        verdict = structured.get("verdict")
        if verdict not in {"HELD", "VIOLATED"}:
            raise InfrastructureError(f"verifier returned invalid verdict: {verdict!r}")
        local_run = {
            "canonical": False,
            "runner": "host-codex-cli",
            "surface": task_type,
            "condition": args.condition,
            "task": args.task,
            "task_name": (metadata.get("task") or {}).get("name"),
            "codex_model": args.codex_model or "codex-cli-default",
            "authentication": "existing Codex CLI login",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reward": structured.get("reward"),
            "verdict": verdict,
            "verifier_exit_code": verifier_process.returncode,
            "exit_taxonomy": {
                "HELD": EXIT_HELD,
                "VIOLATED": EXIT_VIOLATED,
                "AGENT_INVALID": EXIT_AGENT_INVALID,
                "INFRA_ERROR": EXIT_INFRA_ERROR,
            },
            "limitations": [
                "No Harbor or Docker isolation",
                "Agent/model arm differs from the canonical benchmark configuration",
                "Web/app actions are visible-text simulations, not browser/CUA execution",
                "Host verifiers must be trusted repository code",
                "Suitable for local development, not a publishable benchmark trial",
            ],
        }
        _write_json(output_dir / "local_run.json", local_run)
    except AgentInvalid as exc:
        print(f"AGENT_INVALID: {exc}", file=sys.stderr)
        if output_dir.exists():
            print(f"partial artifacts: {output_dir}", file=sys.stderr)
        return EXIT_AGENT_INVALID
    except (
        InfrastructureError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as exc:
        print(f"INFRA_ERROR: {exc}", file=sys.stderr)
        if output_dir.exists():
            print(f"partial artifacts: {output_dir}", file=sys.stderr)
        return EXIT_INFRA_ERROR

    print(
        f"local Codex result: reward={structured.get('reward')} verdict={verdict} "
        f"condition={args.condition}"
    )
    print(f"artifacts: {output_dir}")
    print("note: this is a noncanonical local development run")
    return EXIT_HELD if verdict == "HELD" else EXIT_VIOLATED


if __name__ == "__main__":
    raise SystemExit(main())
