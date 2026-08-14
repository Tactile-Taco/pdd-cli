"""pdd registry index — catalog listing with optional filters."""

from __future__ import annotations

import json
import sys

from . import client


def run(argv: list[str]) -> int:
    params = {}
    for flag in ("status", "depends_on", "namespace", "tag"):
        if f"--{flag}" in argv:
            idx = argv.index(f"--{flag}")
            if idx + 1 >= len(argv):
                sys.exit(f"usage error: --{flag} requires a value")
            params[flag] = argv[idx + 1]
    url = client.resolve_registry(argv)
    result = client.get(url, "/bundles", params)
    print(json.dumps(result, indent=2))
    return 0
