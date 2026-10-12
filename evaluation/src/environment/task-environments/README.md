# Task environments

Runtime environment definitions the harness resolves for a task's
`[environment].definition` in `task.toml`. Harbor (and the in-repo fallback in
`evaluation/src/backend/service/task_environment.py`) resolves a definition to
`environment/task-environments/<definition>`. Nothing here is Python the harness
imports; it's Docker material that tasks run inside.

| definition | what | used by |
|---|---|---|
| `application/shared-chat-persona` | chat persona-agent runtime | chat tasks |
| `application/shared-survey-form` | survey-form runtime | survey tasks |
| `application/shared-web-playwright` | Playwright web runtime | web tasks |
| `application/shared-os-app-linux` | Linux CUA desktop base (Xvfb + XFCE + xdotool + scrot) every **app** task builds `FROM` | app tasks (as a base image) |

Names mirror the authoritative definitions in `MatrAIx-Persona-8B`.

## Building the app base image (once)

App tasks' `environment/Dockerfile` start `FROM matraix/shared-os-app-linux:local`.
Build that base image first:

```bash
docker build -t matraix/shared-os-app-linux:local \
  environment/task-environments/application/shared-os-app-linux
```

Each app task then extends it (adds `python3-tk` + the task's GUI) via its own
`tasks/.../environment/Dockerfile`.

## Where task-specific environments live

Per-task environments (an app's native GUI + its Dockerfile) live **with the task**
at `tasks/.../<name>/environment/`, not here. Only genuinely shared bases live here.
