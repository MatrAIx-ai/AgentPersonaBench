# Shared chat persona agent

Matraix Playground **persona agent** runtime for chatbot tasks (Claude Code / shell /
`/app/input` + `/app/output`).

Chat endpoint hosting does **not** live here. Point optional local compose at
`application/chatbot-api-sidecar_<sut> or chatbot-mcp-sidecar_<sut>` via `[environment].local_compose`, or use an
external URL in `input/chatbot.yaml` (`connection.baseUrl`).
