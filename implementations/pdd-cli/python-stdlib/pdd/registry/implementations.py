"""pdd registry implementations — ranked implementation picker (HTTP).

Filters + ranks candidate realizations from /implementations:
  --protocol <name>     implementations implementing this protocol
  --host-class <cls>    host class match (browser-dom|node-runtime|storage|language)
  --affinity <text>     substring match across affinity values (e.g. react, node@24)
  --evidence pass|any   require bound evidence: pass = every protocol passes;
                        any = at least one evidence record
Ranked by: protocol coverage desc, evidence passes desc, name asc.
"""

from __future__ import annotations

import json
import sys

from . import client


def run(argv: list[str]) -> int:
    params = {}
    for flag in ("protocol", "host_class", "affinity", "evidence"):
        if f"--{flag}" in argv:
            idx = argv.index(f"--{flag}")
            if idx + 1 >= len(argv):
                sys.exit(f"usage error: --{flag} requires a value")
            params[flag] = argv[idx + 1]
    url = client.resolve_registry(argv)
    result = client.get(url, "/implementations", params)
    print(json.dumps(result, indent=2))
    return 0
