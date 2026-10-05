from __future__ import annotations

from playground.chatbot_task_config import (
    load_chatbot_task_config_for_task_path,
)
from playground.harbor.chat_eval import (
    chat_api_url_from_env,
    harbor_chat_task_config_from_env,
)


def test_load_chatbot_task_config_from_input_dir(tmp_path, monkeypatch) -> None:
    task_dir = tmp_path / "application" / "tasks" / "chat_openbb-corporate-action-honesty" / "input"
    task_dir.mkdir(parents=True)
    (task_dir / "chatbot.yaml").write_text(
        "\n".join(
            [
                "transport: external_http",
                "runtimeDefaults:",
                "  applicationId: finance_openbb",
                "  applicationContext: financial_research",
                "  domain: financial_research",
                "  maxTurns: 9",
                "connection:",
                "  baseUrlEnv: CHATBOT_UPSTREAM_FINANCE",
                "  legacyBaseUrlEnv: FINANCE_CHATBOT_URL",
                "  baseUrl: http://finance-chatbot:8000",
                "protocol:",
                "  sendMessage:",
                "    method: POST",
                "    path: /v1/messages",
                "    engineField: engine",
                "    staticBody:",
                "      applicationId: finance_openbb",
                "      applicationContext: financial_research",
                "  response:",
                "    replyField: reply",
                "structuredExposure:",
                "  fields:",
                "    - key: groundedItems",
                "      label: Suggested instruments",
                "      selector: groundedItems",
                "      format: item_list",
            ]
        ),
        encoding="utf-8",
    )
    config = load_chatbot_task_config_for_task_path(
        "application/tasks/chat_openbb-corporate-action-honesty",
        repo_root=tmp_path,
    )
    assert config is not None
    assert config.transport == "external_http"
    assert config.runtime_defaults.application_id == "finance_openbb"
    assert config.runtime_defaults.max_turns == 9
    assert config.protocol.engine_field == "engine"
    assert config.protocol.static_body["applicationId"] == "finance_openbb"
    assert config.structured_exposure[0].selector == "groundedItems"

    monkeypatch.setenv("CHATBOT_UPSTREAM_FINANCE", "http://finance.local:9000")
    assert chat_api_url_from_env("finance_openbb", task_config=config) == "http://finance.local:9000"


def test_harbor_chat_task_config_from_env_uses_task_path(tmp_path, monkeypatch) -> None:
    task_dir = tmp_path / "application" / "tasks" / "example-chat-api_support_chatbot" / "input"
    task_dir.mkdir(parents=True)
    (task_dir / "chatbot.yaml").write_text(
        "\n".join(
            [
                "transport: external_http",
                "runtimeDefaults:",
                "  applicationId: acme_support_api",
                "  applicationContext: customer_support",
                "  domain: customer_support",
                "connection:",
                "  baseUrlEnv: CHATBOT_API_URL",
                "  baseUrl: http://support-api:8000",
                "protocol:",
                "  sendMessage:",
                "    path: /v1/messages",
                "    staticBody:",
                "      applicationId: acme_support_api",
                "      applicationContext: customer_support",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "MATRIX_CHATBOT_TASK_PATH",
        "application/tasks/example-chat-api_support_chatbot",
    )
    config = harbor_chat_task_config_from_env(repo_root=tmp_path)
    assert config is not None
    assert config.connection.base_url == "http://support-api:8000"
    assert config.runtime_defaults.application_id == "acme_support_api"
    assert config.protocol.static_body["applicationContext"] == "customer_support"
