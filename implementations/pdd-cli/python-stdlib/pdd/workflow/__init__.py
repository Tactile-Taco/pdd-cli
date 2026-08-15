"""pdd workflow — the author-side loop (offline, path-based)."""

from __future__ import annotations

import sys


def dispatch(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow requires a subcommand "
              "(init|lint|seal|validate|evidence|run|staleness|status)", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "init":
        from . import init
        return init.run(rest)
    if cmd == "lint":
        from . import lint
        return lint.run(rest)
    if cmd == "lint-candidate":
        from . import lint_candidate
        return lint_candidate.run(rest)
    if cmd == "seal":
        from . import seal
        return seal.run(rest)
    if cmd == "validate":
        from . import validate
        return validate.run(rest)
    if cmd == "evidence":
        if not rest:
            print("usage error: pdd workflow evidence requires a subcommand "
                  "(build|verify|package)", file=sys.stderr)
            return 2
        from . import evidence
        return evidence.dispatch(rest)
    if cmd == "run":
        from . import run
        return run.run(rest)
    if cmd == "assembly":
        if not rest:
            print("usage error: pdd workflow assembly requires a subcommand "
                  "(verify|derive)", file=sys.stderr)
            return 2
        from . import assembly
        return assembly.dispatch(rest)
    if cmd == "staleness":
        from . import staleness
        return staleness.run(rest)
    if cmd == "status":
        from . import status
        return status.run(rest)
    print(f"usage error: unknown workflow subcommand {cmd!r}", file=sys.stderr)
    return 2
