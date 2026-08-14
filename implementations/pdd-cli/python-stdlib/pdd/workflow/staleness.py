"""pdd workflow staleness — keyless freshness gate (B-003).

Exit 0 when the latest admission evidence attests the CURRENT on-disk bundle
digest; exit 1 on drift. No registry, no key. Wired into commit gates and CI:
any change under pdd-bundles/<name>/ without re-validation + re-attestation
is a violation this command catches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import config as cfg
from .. import engine


def run(argv: list[str]) -> int:
    targets = argv or []
    if targets and targets[0] in ("-h", "--help"):
        print("usage: pdd workflow staleness [bundle-dir...]")
        return 0
    if targets:
        dirs = [Path(t).resolve() for t in targets]
    else:
        try:
            ws = cfg.workspace_root()
        except FileNotFoundError as exc:
            print(f"usage error: {exc}", file=sys.stderr)
            return 2
        dirs = sorted(p for p in (ws / "pdd-bundles").iterdir() if p.is_dir())
    if not dirs:
        print("usage error: no bundle dirs to check", file=sys.stderr)
        return 2
    rc = 0
    for b in dirs:
        if not (b / "protocol.yaml").exists():
            print(f"skip: {b} is not a bundle (no protocol.yaml)")
            continue
        if _fresh(b):
            print(f"fresh: {b.name}")
        else:
            print(f"STALE: {b.name} — bundle digest changed without re-attestation")
            rc = 1
    return rc


def _fresh(bundle: Path) -> bool:
    current = engine.bundle_digest(bundle)
    try:
        ws = cfg.workspace_root(bundle)
        ev_root = cfg.evidence_root(ws)
    except FileNotFoundError:
        ev_root = bundle.parent / "evidence"
    adm_dir = ev_root / bundle.name / "admission"
    if not adm_dir.is_dir():
        return False
    latest = None
    latest_time = ""
    for f in adm_dir.glob("*.evidence.json"):
        try:
            obj = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        t = ((obj.get("provenance") or {}).get("time") or "")
        if t >= latest_time:
            latest = obj
            latest_time = t
    if latest is None:
        return False
    attested = (latest.get("protocol") or {}).get("bundle_digest")
    return attested == current
