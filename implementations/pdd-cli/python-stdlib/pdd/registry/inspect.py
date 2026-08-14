"""pdd registry inspect — per-bundle views (summary, invariants, capabilities,
ledger). Mirrors the server's /bundles/{name} surface."""

from __future__ import annotations

import json
import sys

from . import client


def run(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("usage error: pdd registry inspect <bundle> "
              "[--invariants|--capabilities|--ledger] [--registry URL]", file=sys.stderr)
        return 2
    name = argv[0]
    url = client.resolve_registry(argv)
    view = None
    if "--invariants" in argv:
        view = "invariants"
    elif "--capabilities" in argv:
        view = "capabilities"
    elif "--ledger" in argv:
        view = "ledger"
    if view:
        result = client.get(url, f"/bundles/{name}/{view}")
    else:
        result = client.get(url, f"/bundles/{name}")
    print(json.dumps(result, indent=2))
    return 0
