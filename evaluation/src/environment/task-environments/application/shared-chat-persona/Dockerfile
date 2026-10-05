FROM ubuntu:24.04

COPY install-claude-code.sh /tmp/install-claude-code.sh
RUN bash /tmp/install-claude-code.sh && rm /tmp/install-claude-code.sh

ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app
