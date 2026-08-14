"""pdd workflow lint — hardened bundle linter (Phase-2 gate).

Runs the ported check_bundle.py (pdd.lint) over one bundle dir, or over every
bundle under the workspace pdd-bundles/ when no dir is given.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .. import config as cfg


def run(argv: list[str]) -> int:
    target = argv[0] if argv else None
    if target is not None:
        bundle = Path(target)
        if not bundle.is_dir():
            print(f"error: no such bundle dir {bundle}", file=sys.stderr)
            return 1
        return _lint_one(bundle)
    try:
        ws = cfg.workspace_root()
    except FileNotFoundError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    bundles = sorted(p for p in (ws / "pdd-bundles").iterdir() if p.is_dir())
    if not bundles:
        print(f"error: no bundles under {ws / 'pdd-bundles'}", file=sys.stderr)
        return 1
    rc = 0
    for b in bundles:
        rc |= _lint_one(b)
    return rc


def _lint_one(bundle: Path) -> int:
    from .. import lint as lint_mod
    rc = lint_mod.main(str(bundle))
    return rc
