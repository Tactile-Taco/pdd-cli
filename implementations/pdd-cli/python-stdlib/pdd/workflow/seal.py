"""pdd workflow seal — flip a bundle to sealed (lint must pass first)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_BUNDLE_NAME_RE = re.compile(r"[A-Za-z0-9_-]+$")


def run(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow seal <bundle-dir>", file=sys.stderr)
        return 2
    d = Path(argv[0])
    if not d.is_dir() or not (d / "protocol.yaml").exists():
        print(f"error: no bundle at {d} (missing protocol.yaml)", file=sys.stderr)
        return 1
    if not _BUNDLE_NAME_RE.fullmatch(d.name):
        print(f"usage error: invalid bundle name {d.name!r} (must match [A-Za-z0-9_-])", file=sys.stderr)
        return 2
    from .lint import _lint_one
    if _lint_one(d) != 0:
        print("error: lint must pass before sealing", file=sys.stderr)
        return 1
    proto = d / "protocol.yaml"
    text = proto.read_text()
    if "status: sealed" in text:
        print(f"already sealed: {d.name}")
        return 0
    proto.write_text(text.replace("status: draft", "status: sealed").replace(
        "status: review", "status: sealed"))
    minutes = d / "negotiation-minutes.md"
    if not minutes.exists():
        minutes.write_text(
            f"# Negotiation Minutes — {d.name}\n\nSealed via `pdd workflow seal`.\n"
            f"No open conflicts; lint passed; versions pinned.\n")
    print(f"sealed: {d.name} (status: sealed in protocol.yaml)")
    return 0
