"""pdd registry — the pdd-registry client (HTTP, stdlib urllib)."""

from __future__ import annotations

import sys


def dispatch(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd registry requires a subcommand "
              "(search|index|inspect|verify|publish)", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "search":
        from . import search
        return search.run(rest)
    if cmd == "index":
        from . import index
        return index.run(rest)
    if cmd == "implementations":
        from . import implementations
        return implementations.run(rest)
    if cmd == "inspect":
        from . import inspect
        return inspect.run(rest)
    if cmd == "verify":
        from . import verify
        return verify.run(rest)
    if cmd == "publish":
        from . import publish
        return publish.run(rest)
    print(f"usage error: unknown registry subcommand {cmd!r}", file=sys.stderr)
    return 2
