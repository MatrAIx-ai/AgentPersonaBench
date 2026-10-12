#!/usr/bin/env bash
# Pre-install Claude Code + runtime deps for persona-claude-code Docker tasks.
#
# Harbor builds each task from its own environment/ directory, so task Dockerfiles
# need a local copy of this file. Run scripts/sync_docker_snippets.py to update
# all managed task-local copies.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

if ! command -v curl >/dev/null \
    || ! command -v ps >/dev/null \
    || ! command -v python3 >/dev/null \
    || ! command -v pip >/dev/null; then
    apt-get update
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        procps \
        python3 \
        python3-pip
    rm -rf /var/lib/apt/lists/*
fi

curl -fsSL https://downloads.claude.ai/claude-code-releases/bootstrap.sh | bash -s --
echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc
export PATH="/root/.local/bin:$PATH"
claude --version

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
export PATH="/root/.local/bin:$PATH"
uvx --version

mkdir -p /installed-agent /app/input /app/output
