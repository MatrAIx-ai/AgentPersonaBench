"""browser-use agent adapter for Harbor (Docker web browsing)."""

from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.agents.utils import get_api_key_var_names_from_model_name
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName
from harbor.models.trial.paths import EnvironmentPaths


class BrowserUseHarborAgent(BaseInstalledAgent):
    """Run the browser-use library inside the task container."""

    SUPPORTS_ATIF: bool = True
    _OUTPUT_FILENAME = "browser_use.txt"
    _TRAJECTORY_FILENAME = "trajectory.json"
    _VENV_PYTHON = "/opt/browser-use-venv/bin/python"
    _RUNNER_PATH = "/installed-agent/browser_use_runner.py"

    def __init__(
        self,
        max_steps: int | None = 50,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._max_steps = max_steps

    @staticmethod
    def name() -> str:
        return AgentName.BROWSER_USE.value

    def get_version_command(self) -> str | None:
        return (
            f"{self._VENV_PYTHON} -m pip show browser-use 2>/dev/null | grep ^Version:"
        )

    def parse_version(self, stdout: str) -> str:
        text = stdout.strip()
        if text.startswith("Version:"):
            return text.removeprefix("Version:").strip()
        return text

    @property
    def _trajectory_path(self) -> PurePosixPath:
        return PurePosixPath(EnvironmentPaths.agent_dir / self._TRAJECTORY_FILENAME)

    async def install(self, environment: BaseEnvironment) -> None:
        check = await environment.exec(
            command=(
                f"[ -x {self._VENV_PYTHON} ] && "
                f"{self._VENV_PYTHON} -c 'import browser_use' 2>/dev/null"
            ),
        )
        if check.return_code != 0:
            version_spec = f"=={self._version}" if self._version else ""
            await self.exec_as_root(
                environment,
                command=(
                    "mkdir -p /opt && "
                    'if ! python3 -c "import ensurepip" 2>/dev/null; then '
                    "apt-get update -qq && apt-get install -y python3-venv; "
                    "fi"
                ),
                env={"DEBIAN_FRONTEND": "noninteractive"},
            )
            agent_user = environment.default_user or "root"
            await self.exec_as_root(
                environment,
                command=(
                    "mkdir -p /opt/browser-use-venv && "
                    f"chown {agent_user}:{agent_user} /opt/browser-use-venv"
                ),
            )
            await self.exec_as_agent(
                environment,
                command=(
                    "set -euo pipefail; "
                    "python3 -m venv /opt/browser-use-venv && "
                    "source /opt/browser-use-venv/bin/activate && "
                    "export PIP_DEFAULT_TIMEOUT=180 && "
                    "pip install --upgrade pip && "
                    f"pip install 'browser-use{version_spec}'"
                ),
            )

        runner_src = Path(__file__).parent / "browser_use_runner.py"
        local_copy = self.logs_dir / "browser_use_runner.py"
        local_copy.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")
        await environment.upload_file(
            source_path=local_copy,
            target_path=self._RUNNER_PATH,
        )
        await environment.exec(
            command=f"chmod +x {self._RUNNER_PATH}",
            user="root",
        )

    def populate_context_post_run(self, context: AgentContext) -> None:
        trajectory_file = self.logs_dir / self._TRAJECTORY_FILENAME
        if not trajectory_file.is_file():
            return
        try:
            data = json.loads(trajectory_file.read_text(encoding="utf-8"))
            summary = data
            if isinstance(data, dict):
                extra = data.get("extra")
                if isinstance(extra, dict) and isinstance(
                    extra.get("browser_use"), dict
                ):
                    summary = extra["browser_use"]
                final_metrics = data.get("final_metrics") or {}
                if isinstance(final_metrics, dict):
                    context.cost_usd = final_metrics.get("total_cost_usd")
                    context.n_input_tokens = final_metrics.get("total_prompt_tokens", 0)
                    context.n_output_tokens = final_metrics.get(
                        "total_completion_tokens", 0
                    )
                    context.n_cache_tokens = final_metrics.get("total_cached_tokens", 0)
            context.metadata = {**(context.metadata or {}), "browser_use": summary}
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
            raise ValueError("No LLM model specified for browser-use")

        env: dict[str, str] = {}
        for key_name in get_api_key_var_names_from_model_name(self.model_name):
            value = self._get_env(key_name)
            if value is not None:
                env[key_name] = value

        if not any(
            self._get_env(name)
            for name in (
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "LLM_API_KEY",
                "DASHSCOPE_API_KEY",
            )
        ):
            raise ValueError(
                "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, DASHSCOPE_API_KEY, or LLM_API_KEY for browser-use"
            )

        llm_api_key = self._get_env("LLM_API_KEY")
        if (
            llm_api_key
            and "ANTHROPIC_API_KEY" not in env
            and "OPENAI_API_KEY" not in env
            and "DASHSCOPE_API_KEY" not in env
        ):
            if self.model_name.startswith("anthropic/"):
                env["ANTHROPIC_API_KEY"] = llm_api_key
            elif self.model_name.startswith("dashscope/"):
                env["DASHSCOPE_API_KEY"] = llm_api_key
            else:
                env["OPENAI_API_KEY"] = llm_api_key

        env["AGENT_LOGS_DIR"] = "/logs/agent"
        env["TRAJECTORY_PATH"] = f"/logs/agent/{self._TRAJECTORY_FILENAME}"
        if self._max_steps is not None:
            env["MAX_STEPS"] = str(self._max_steps)

        if self._version:
            env["BROWSER_USE_VERSION"] = self._version

        persona_system = self._get_env("PERSONA_SYSTEM")
        if persona_system:
            env["PERSONA_SYSTEM"] = persona_system

        escaped_instruction = shlex.quote(instruction)
        escaped_model = shlex.quote(self.model_name)
        command = f"""
{self._VENV_PYTHON} {self._RUNNER_PATH} \
    --instruction={escaped_instruction} \
    --model={escaped_model} \
    --trajectory-path="$TRAJECTORY_PATH" \
    2>&1 | stdbuf -oL tee /logs/agent/{self._OUTPUT_FILENAME}
"""
        await self.exec_as_agent(environment, command=command.strip(), env=env)
