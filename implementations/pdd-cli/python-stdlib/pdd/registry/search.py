"""pdd registry search — ranked catalog search."""

from __future__ import annotations

import json
import sys

from . import client


def run(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("usage error: pdd registry search <query> [--registry URL]", file=sys.stderr)
        return 2
    query = argv[0]
    url = client.resolve_registry(argv)
    result = client.get(url, "/search", {"q": query})
    print(json.dumps(result, indent=2))
    return 0 if result.get("count") else 1
