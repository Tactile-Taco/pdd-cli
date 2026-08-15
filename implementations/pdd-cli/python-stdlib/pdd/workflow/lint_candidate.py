"""pdd workflow lint-candidate — declared-only implementation packaging gate.

Port of the authoring skill's scripts/check_candidate_manifest.py. Given an
implementation dir with candidate-manifest.json:
  1. manifest shape (implements[], host.class, files map)
  2. every declared file exists
  3. NO UNDECLARED FILES: every file under the impl dir (excluding
     node_modules/, .venv/, evidence/, validators/, dist/, .git/,
     __pycache__/, var/, data/) is claimed by a protocol set, `_app_shell`,
     or `host_files`. Unclaimed files are a packaging leak.
  4. per-protocol file hashes match the bound evidence's
     artifact.protocol_modules where that evidence exists.

Exit 0 = pass, 1 = fail, 2 = usage. No third-party deps.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXCLUDE_DIRS = {"node_modules", ".venv", "evidence", "validators", "dist",
                ".git", "__pycache__", "var", "data"}
HOST_CLASSES = {"browser-dom", "node-runtime", "storage"}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _lint_one(impl_dir: Path) -> int:
    mf = impl_dir / "candidate-manifest.json"
    if not mf.exists():
        print(f"FAIL: missing candidate-manifest.json in {impl_dir}")
        return 1
    try:
        data = json.loads(mf.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: candidate-manifest.json not valid JSON: {e}")
        return 1
    cm = data.get("candidate_manifest")
    if not isinstance(cm, dict):
        print("FAIL: top-level 'candidate_manifest' object missing")
        return 1

    errs = []
    impls = cm.get("implements")
    if not isinstance(impls, list) or not impls:
        errs.append("implements: non-empty list of {protocol, version, seam, evidence} required")
    host = cm.get("host") or {}
    if host.get("class") not in HOST_CLASSES:
        errs.append(f"host.class must be one of {sorted(HOST_CLASSES)}, got {host.get('class')!r}")
    files = cm.get("files")
    if not isinstance(files, dict) or not files:
        errs.append("files: map of protocol -> [relative paths] required")
        files = {}

    for proto, paths in files.items():
        for p in paths:
            f = (impl_dir / p).resolve()
            if not f.exists() or not f.is_relative_to(impl_dir.resolve()):
                errs.append(f"files[{proto}]: missing or outside impl dir: {p}")
    host_files = cm.get("host_files") or []
    for p in host_files:
        if not (impl_dir / p).exists():
            errs.append(f"host_files: missing: {p}")

    claimed = {(impl_dir / p).resolve() for paths in files.values() for p in paths}
    claimed |= {(impl_dir / p).resolve() for p in host_files}
    for f in impl_dir.rglob("*"):
        if not f.is_file():
            continue
        if any(x in f.parts for x in EXCLUDE_DIRS):
            continue
        if f.resolve() in claimed:
            continue
        if f.name == "candidate-manifest.json":
            continue
        errs.append(f"UNDECLARED FILE (not in files.* or _app_shell): {f.relative_to(impl_dir)}")

    for entry in impls or []:
        ev = entry.get("evidence")
        if not ev:
            continue
        ev_path = impl_dir / ev
        if not ev_path.exists():
            errs.append(f"evidence not found: {ev}")
            continue
        try:
            evd = json.loads(ev_path.read_text())
        except json.JSONDecodeError:
            errs.append(f"evidence not valid JSON: {ev}")
            continue
        mods = (evd.get("artifact") or {}).get("protocol_modules") or {}
        for rel, h in mods.items():
            f = impl_dir / rel
            if not f.exists():
                errs.append(f"evidence binds {rel} but file missing")
            elif _sha256(f) != h:
                errs.append(f"evidence hash mismatch for {rel} (artifact changed since validation)")

    for e in errs:
        print(f"FAIL: {e}")
    if not errs:
        print(f"PASS: {impl_dir.name} candidate manifest ({len(files)} file sets, all declared, hashes bound)")
    return 1 if errs else 0


def run(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow lint-candidate <implementation-dir>", file=sys.stderr)
        return 2
    impl_dir = Path(argv[0])
    if not impl_dir.is_dir():
        print(f"error: no such implementation dir {impl_dir}", file=sys.stderr)
        return 2
    return _lint_one(impl_dir)
