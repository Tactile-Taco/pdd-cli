"""pdd workflow run — sandboxed smoke run of a candidate (docker, network none,
read-only fs, resource-capped). Port of the pdd-registry `pdd run`."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_SANDBOX_DOCKER_FLAGS = ["--memory", "256m", "--pids-limit", "64", "--cpus", "1",
                         "--cap-drop", "ALL", "--user", "65534:65534"]


def run(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow run <bundle-dir> --impl <impl-dir> [--sandbox]",
              file=sys.stderr)
        return 2
    bundle = Path(argv[0]).resolve()
    if "--impl" not in argv:
        print("usage error: run requires --impl <impl-dir>", file=sys.stderr)
        return 2
    impl = Path(argv[argv.index("--impl") + 1]).resolve()
    if not (impl / "candidate-manifest.json").exists():
        print(f"error: no candidate-manifest.json in {impl}", file=sys.stderr)
        return 1
    if not (shutil.which("docker") and "--sandbox" in argv):
        print("pdd workflow run --sandbox requires docker; refusing a local (unsandboxed) smoke run",
              file=sys.stderr)
        return 1
    manifest = json.loads((impl / "candidate-manifest.json").read_text())
    entry_module = manifest.get("entry_module")
    entry_class = manifest.get("entry_class")
    smoke = manifest.get("smoke") or {}
    if not (entry_module and entry_class and smoke.get("method")):
        print("candidate-manifest.json must declare entry_module/entry_class/smoke", file=sys.stderr)
        return 1
    ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    if not (ident.fullmatch(entry_module) and ident.fullmatch(entry_class)
            and ident.fullmatch(smoke.get("method"))):
        print(f"entry_module/entry_class/smoke.method must be Python identifiers, got "
              f"{entry_module!r}/{entry_class!r}/{smoke.get('method')!r}", file=sys.stderr)
        return 1
    assert_expr = smoke.get("assert_expr", "True")
    from ..engine import _assert_safe_expression
    try:
        _assert_safe_expression(assert_expr)
    except SystemExit as exc:
        print(f"smoke.assert_expr rejected: {exc}", file=sys.stderr)
        return 1
    args_lit = json.dumps(smoke.get("args") or {})
    if smoke.get("call_style") == "single_dict":
        call = f"{entry_class}().{smoke['method']}({args_lit})"
    else:
        call = f"{entry_class}().{smoke['method']}(**{args_lit})"
    code = ("import sys; sys.path.insert(0,'.'); "
            f"from {entry_module} import {entry_class}; "
            f"r = {call}; "
            f"assert {assert_expr}; print('run: ok')")
    r = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--read-only",
         *_SANDBOX_DOCKER_FLAGS,
         "--security-opt", "no-new-privileges",
         "-v", f"{impl.resolve()}:/candidate:ro", "-w", "/candidate",
         "python:3.12-slim@sha256:d657ab0ade19f404a6ccc883ab399540de667aff751748ce23c07330c5a89e64",
         "python", "-c", code],
        capture_output=True, text=True, timeout=300)
    print(r.stdout.strip() or r.stderr.strip()[:500])
    return r.returncode
