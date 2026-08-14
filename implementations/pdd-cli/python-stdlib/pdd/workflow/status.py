"""pdd workflow status — per-protocol loop state table (resumability).

For each bundle in the workspace: status, lint result, sealed?, admission
evidence present, staleness. The workflow skill mandates a per-protocol status
table so multi-protocol work is resumable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .. import config as cfg


def run(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print("usage: pdd workflow status [workspace-dir]")
        return 0
    if argv:
        ws = Path(argv[0]).resolve()
        if not (ws / "pdd-bundles").is_dir():
            print(f"error: {ws} is not a workspace (no pdd-bundles/)", file=sys.stderr)
            return 1
    else:
        try:
            ws = cfg.workspace_root()
        except FileNotFoundError as exc:
            print(f"usage error: {exc}", file=sys.stderr)
            return 2
    bundles = sorted(p for p in (ws / "pdd-bundles").iterdir() if p.is_dir())
    if not bundles:
        print(f"no bundles under {ws / 'pdd-bundles'}")
        return 0
    ev_root = cfg.evidence_root(ws)
    print(f"{'bundle':24} {'status':10} {'lint':6} {'evidence':8} {'stale':6}")
    rc = 0
    for b in bundles:
        name = b.name
        status = _protocol_status(b)
        lint = "PASS" if _lint_ok(b) else "FAIL"
        evidence = "yes" if (ev_root / name / "admission").is_dir() else "no"
        from .staleness import _fresh
        stale = "no" if _fresh(b) else ("yes" if evidence == "yes" else "-")
        if stale == "yes":
            rc = 1
        print(f"{name:24} {status:10} {lint:6} {evidence:8} {stale:6}")
    return rc


def _protocol_status(b: Path) -> str:
    try:
        text = b.joinpath("protocol.yaml").read_text()
    except OSError:
        return "?"
    for line in text.splitlines():
        if line.strip().startswith("status:"):
            return line.split(":", 1)[1].strip()
    return "?"


def _lint_ok(b: Path) -> bool:
    try:
        from .lint import _lint_one
        return _lint_one(b) == 0
    except Exception:  # noqa: BLE001
        return False
