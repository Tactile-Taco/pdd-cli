"""pdd workflow validate — run the three-layer Validator Loop."""

from __future__ import annotations

import sys
from pathlib import Path

from .. import config as cfg
from .. import engine


def _evidence_root(bundle: Path, argv: list[str]) -> Path:
    if "--evidence-dir" in argv:
        idx = argv.index("--evidence-dir")
        if idx + 1 >= len(argv):
            sys.exit("usage error: --evidence-dir requires a value")
        return Path(argv[idx + 1]).resolve()
    try:
        ws = cfg.workspace_root(bundle)
        return cfg.evidence_root(ws)
    except FileNotFoundError:
        return bundle.parent / "evidence"


def run(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow validate <bundle-dir> --impl <impl-dir> "
              "[--sandbox] [--pbt-runs N]", file=sys.stderr)
        return 2
    bundle = Path(argv[0]).resolve()
    if not bundle.is_dir() or not (bundle / "protocol.yaml").exists():
        print(f"error: no bundle at {bundle}", file=sys.stderr)
        return 1
    if "--impl" not in argv:
        print("usage error: validate requires --impl <impl-dir>", file=sys.stderr)
        return 2
    impl = Path(argv[argv.index("--impl") + 1]).resolve()
    if not (impl / "candidate-manifest.json").exists():
        print(f"error: no candidate-manifest.json in {impl}", file=sys.stderr)
        return 1
    ev_root = _evidence_root(bundle, argv)
    args = ["pdd", str(bundle), str(impl)]
    if "--sandbox" in argv:
        args.append("--sandbox")
    if "--pbt-runs" in argv:
        args += ["--pbt-runs", argv[argv.index("--pbt-runs") + 1]]
    args += ["--evidence-dir", str(ev_root)]
    return engine.main(args)
