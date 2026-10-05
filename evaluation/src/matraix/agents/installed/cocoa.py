"""CocoaAgent adapter for Harbor (single-container AIO Sandbox)."""

from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName
from harbor.models.trial.paths import EnvironmentPaths

_COCOA_PYTHON = "/opt/python3.12/bin/python3"
_COCOA_ROOT = "/opt/cocoa-agent"


class CocoaHarborAgent(BaseInstalledAgent):
    """Run CocoaAgent against the AIO Sandbox baked into the task image."""

    SUPPORTS_ATIF: bool = True
    _OUTPUT_FILENAME = "cocoa.txt"
    _TRAJECTORY_FILENAME = "trajectory.json"
    _RUNNER_PATH = "/installed-agent/cocoa_runner.py"

    def __init__(
        self,
        max_iterations: int | None = 30,
        sandbox_port: int | None = 8080,
        skip_docker: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._max_iterations = max_iterations
        self._sandbox_port = sandbox_port
        self._skip_docker = skip_docker

    @staticmethod
    def name() -> str:
        return AgentName.COCOA.value

    def get_version_command(self) -> str | None:
        return (
            f"{_COCOA_PYTHON} -c 'from agents.cocoa_agent import CocoaAgent' "
            "2>/dev/null && echo installed"
        )

    def parse_version(self, stdout: str) -> str:
        return stdout.strip() or "unknown"

    @property
    def _trajectory_path(self) -> PurePosixPath:
        return PurePosixPath(EnvironmentPaths.agent_dir / self._TRAJECTORY_FILENAME)

    async def install(self, environment: BaseEnvironment) -> None:
        check = await environment.exec(
            command=(
                f"{_COCOA_PYTHON} -c 'from executor import TaskExecutor' 2>/dev/null"
            ),
        )
        if check.return_code != 0:
            await self.exec_as_agent(
                environment,
                command=(
                    "set -euo pipefail; "
                    "if [ ! -d /opt/cocoa-agent-src ]; then "
                    "git clone --depth 1 "
                    "https://github.com/cocoabench/cocoa-agent.git /opt/cocoa-agent-src; "
                    "fi && "
                    f"{_COCOA_PYTHON} -m pip install --no-cache-dir "
                    "-r /opt/cocoa-agent-src/requirements.txt "
                    "openai anthropic colorama agent-sandbox && "
                    "ln -sfn /opt/cocoa-agent-src /opt/cocoa-agent"
                ),
            )

        runner_src = Path(__file__).parent / "cocoa_runner.py"
        local_copy = self.logs_dir / "cocoa_runner.py"
        local_copy.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")
        await environment.upload_file(
            source_path=local_copy,
            target_path=self._RUNNER_PATH,
        )
        await environment.exec(command=f"chmod +x {self._RUNNER_PATH}", user="root")

    def populate_context_post_run(self, context: AgentContext) -> None:
        trajectory_file = self.logs_dir / self._TRAJECTORY_FILENAME
        if not trajectory_file.is_file():
            return
        try:
            data = json.loads(trajectory_file.read_text(encoding="utf-8"))
            summary = data
            if isinstance(data, dict):
                extra = data.get("extra")
                if isinstance(extra, dict) and isinstance(extra.get("cocoa"), dict):
                    summary = extra["cocoa"]
                final_metrics = data.get("final_metrics") or {}
                if isinstance(final_metrics, dict):
                    context.cost_usd = final_metrics.get("total_cost_usd")
                    context.n_input_tokens = int(
                        final_metrics.get("total_prompt_tokens", 0) or 0
                    )
                    context.n_output_tokens = int(
                        final_metrics.get("total_completion_tokens", 0) or 0
                    )
                    context.n_cache_tokens = int(
                        final_metrics.get("total_cached_tokens", 0) or 0
                    )
                elif isinstance(data.get("api_cost_stats"), dict):
                    cost = data["api_cost_stats"]
                    context.cost_usd = cost.get("total_cost_usd")
                    context.n_input_tokens = int(cost.get("total_input_tokens", 0) or 0)
                    context.n_output_tokens = int(
                        cost.get("total_output_tokens", 0) or 0
                    )
            context.metadata = {**(context.metadata or {}), "cocoa": summary}
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        if not self.model_name:
            raise ValueError("No LLM model specified for cocoa")

        env: dict[str, str] = {
            "COCOA_ROOT": _COCOA_ROOT,
            "COCOA_SKIP_DOCKER": "true" if self._skip_docker else "false",
        }
        for key in (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "DASHSCOPE_API_KEY",
            "LLM_API_KEY",
            "LLM_BASE_URL",
            "DASHSCOPE_API_BASE",
        ):
            value = self._get_env(key)
            if value is not None:
                env[key] = value

        if self.model_name.startswith("dashscope/"):
            if "LLM_BASE_URL" not in env:
                env["LLM_BASE_URL"] = (
                    self._get_env("DASHSCOPE_API_BASE")
                    or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
            if (
                "LLM_API_KEY" not in env
                and "OPENAI_API_KEY" not in env
                and self._get_env("DASHSCOPE_API_KEY")
            ):
                env["LLM_API_KEY"] = self._get_env("DASHSCOPE_API_KEY")  # type: ignore[assignment]

        if not any(
            self._get_env(k)
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY", "DASHSCOPE_API_KEY")
        ):
            raise ValueError(
                "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_API_KEY for cocoa"
            )

        env["AGENT_LOGS_DIR"] = "/logs/agent"
        env["TRAJECTORY_PATH"] = f"/logs/agent/{self._TRAJECTORY_FILENAME}"
        if self._max_iterations is not None:
            env["MAX_ITERATIONS"] = str(self._max_iterations)
        if self._sandbox_port is not None:
            env["COCOA_SANDBOX_PORT"] = str(self._sandbox_port)

        escaped_instruction = shlex.quote(instruction)
        escaped_model = shlex.quote(self.model_name)
        command = f"""
{_COCOA_PYTHON} {self._RUNNER_PATH} \
    --instruction={escaped_instruction} \
    --model={escaped_model} \
    --trajectory-path="$TRAJECTORY_PATH" \
    2>&1 | stdbuf -oL tee /logs/agent/{self._OUTPUT_FILENAME}
"""
        await self.exec_as_agent(environment, command=command.strip(), env=env)
