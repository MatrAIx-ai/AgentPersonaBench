#!/usr/bin/env python3
"""Build MatrAIx Persona 1M inverted indexes (dim → row_id postings).

Usage (from repo root)::

    PYTHONPATH=.:application/playground:src:environment/runtime:packages/playground/src \\
      .venv/bin/python -m backend.service.build_persona_1m_indexes

    # or
    .../python application/playground/backend/service/build_persona_1m_indexes.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="MatrAIx repo root (default: auto-detect from this file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Indexes output directory (default: persona/datasets/matraix-persona-1m/indexes)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=20_000,
        help="Print progress every N rows (0 disables)",
    )
    parser.add_argument(
        "--enrich-source",
        action="store_true",
        help="Only add/replace ``source`` postings on an existing index (no full rebuild)",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root
    if repo_root is None:
        # application/playground/backend/service/this_file → repo root
        repo_root = Path(__file__).resolve().parents[4]
    repo_root = repo_root.resolve()

    # Ensure imports resolve when run as a script.
    for path in (
        repo_root,
        repo_root / "application" / "playground",
        repo_root / "src",
        repo_root / "environment" / "runtime",
        repo_root / "packages" / "playground" / "src",
    ):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)

    if args.enrich_source:
        from backend.service.persona_1m_index import enrich_source_postings

        result = enrich_source_postings(
            repo_root=repo_root,
            index_dir=args.output.resolve() if args.output else None,
            progress_every=max(0, int(args.progress_every)),
        )
        print(json_dumps_safe(result))
        return 0

    from backend.service.persona_1m_index import build_indexes

    manifest = build_indexes(
        repo_root=repo_root,
        output_dir=args.output.resolve() if args.output else None,
        progress_every=max(0, int(args.progress_every)),
    )
    print(json_dumps_safe(manifest))
    return 0


def json_dumps_safe(payload: dict) -> str:
    import json

    return json.dumps(
        {k: v for k, v in payload.items() if k != "shards"} | {"shardCount": len(payload.get("shards") or [])},
        indent=2,
    )


if __name__ == "__main__":
    raise SystemExit(main())
