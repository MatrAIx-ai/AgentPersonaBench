#!/usr/bin/env bash
# Re-vendor the leaderboard's brand marks from @lobehub/icons-static-svg (MIT).
#
# Same source as the deployment app's leaderboard
# (matraix-deployment/.../components/leaderboard/vendorLogos.tsx), so a model
# wears the same mark on both surfaces. Each file is a single-path 24x24 SVG
# drawing in `currentColor`.
#
# The SVGs are committed to evaluation/assets/vendors/ and INLINED into
# leaderboard/index.html at render time — the page has to open from disk with
# no network, so an <img src> or CDN link would leave a hole in it offline.
# This script only exists to refresh them or to add a vendor.
#
# Left column is the `provider` id an arm config records; right column is the
# lobehub icon slug. Brand colours are NOT fetched — they live in VENDORS in
# evaluation/leaderboard.py, mirroring the deployment app's own table.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
DEST=evaluation/assets/vendors
mkdir -p "$DEST"

for pair in \
  "anthropic:anthropic" \
  "openai:openai" \
  "gemini:gemini" \
  "dashscope:qwen" \
  "zai:zai" \
  "deepseek:deepseek" \
  "openrouter:openrouter"
do
  provider="${pair%%:*}"; slug="${pair##*:}"
  url="https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/${slug}.svg"
  if curl -sSf -m 20 -o "$DEST/$provider.svg" "$url"; then
    printf '  %-12s <- %-12s %s bytes\n' "$provider" "$slug" "$(wc -c < "$DEST/$provider.svg" | tr -d ' ')"
  else
    echo "  FAILED $provider (slug '$slug' — check it still exists upstream)" >&2
  fi
done
