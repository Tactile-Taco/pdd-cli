"""pdd config: registry endpoint resolution (B-005)."""

from __future__ import annotations

import sys

from . import config as cfg


def dispatch(argv: list[str]) -> int:
    if not argv or argv[0] not in ("show", "set-registry"):
        print("usage error: pdd config show | set-registry <url>", file=sys.stderr)
        return 2
    if argv[0] == "show":
        info = cfg.show()
        for k, v in info.items():
            print(f"{k}: {v}")
        return 0
    if len(argv) < 2:
        print("usage error: pdd config set-registry <url>", file=sys.stderr)
        return 2
    try:
        cfg.set_registry(argv[1])
    except ValueError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    print(f"registry set to {argv[1]} ({cfg.config_path()})")
    return 0
