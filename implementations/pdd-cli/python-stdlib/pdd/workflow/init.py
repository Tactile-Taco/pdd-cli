"""pdd workflow init — scaffold a bundle from the template set."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .. import config as cfg


def run(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow init <dir>", file=sys.stderr)
        return 2
    target = Path(argv[0])
    if target.exists():
        print(f"error: {target} already exists; refusing to overwrite", file=sys.stderr)
        return 1
    templates = Path(__file__).resolve().parent.parent / "templates"
    if not templates.is_dir():
        print(f"error: template set not found at {templates}", file=sys.stderr)
        return 1
    shutil.copytree(templates, target)
    print(f"scaffolded bundle at {target} (edit protocol.yaml, then: "
          f"pdd workflow lint {target} && pdd workflow seal {target})")
    return 0
