#!/usr/bin/env python3
"""pdd CLI dispatch — two namespaces + config.

  pdd workflow ...   the author-side loop (offline, path-based)
  pdd registry ...   the pdd-registry client (HTTP)
  pdd config ...     registry endpoint config

Exit-code contract (S-002): 0 success, 1 operational/validation/evidence
failure, 2 usage error. Failures print to stderr. SystemExit (from ported
helpers) is converted to an exit code so the Adapter surface never raises.
"""

from __future__ import annotations

import sys

USAGE = """pdd — Protocol-Driven Development CLI

  pdd workflow init <dir>                    scaffold a bundle from templates
  pdd workflow lint [bundle-dir]             hardened bundle linter
  pdd workflow lint-candidate <impl-dir>     declared-only implementation packaging gate
  pdd workflow seal <bundle-dir>             seal a bundle (lint must pass)
  pdd workflow validate <bundle-dir> --impl <impl-dir> [--sandbox] [--pbt-runs N]
  pdd workflow evidence build <bundle-dir> --impl <impl-dir> [--validation-resource URL]
  pdd workflow evidence verify <bundle-dir>
  pdd workflow evidence package <bundle-dir> -o <out-file>
  pdd workflow run <bundle-dir> --impl <impl-dir> [--sandbox]
  pdd workflow assembly verify <lock> [--bundles root]     structural + bundle-aware assembly checks
  pdd workflow assembly derive <lock> --protocols P1,P2 [-o out] [--bundles root]
  pdd workflow staleness [bundle-dir...]
  pdd workflow status [workspace-dir]

  pdd registry search <query> [--registry URL]
  pdd registry index [--registry URL]
  pdd registry implementations [--protocol N] [--host-class C] [--affinity A] [--evidence pass|any] [--registry URL]
  pdd registry inspect <bundle> [--invariants|--capabilities|--ledger] [--registry URL]
  pdd registry verify <bundle> [--registry URL]
  pdd registry publish <bundle-dir> --evidence <file> [--registry URL] [--token-env NAME]

  pdd config show
  pdd config set-registry <url>

Exit codes: 0 ok, 1 operational/validation failure, 2 usage error.
"""


def _code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    return 0 if exc.code is None else 1


def run(argv: list[str]) -> int:
    try:
        return _run(argv)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
        return _code(exc)


def _run(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0 if argv else 2
    head, rest = argv[0], argv[1:]
    if head == "workflow":
        from .workflow import dispatch
        return dispatch(rest)
    if head == "registry":
        from .registry import dispatch
        return dispatch(rest)
    if head == "config":
        from . import config_cmd
        return config_cmd.dispatch(rest)
    print(f"usage error: unknown command {head!r}", file=sys.stderr)
    return 2


def main() -> int:
    return run(sys.argv[1:])
