"""Protocol adapter: the single entry surface under test (B-001..B-005).

The Validator Loop exercises handle(request) — never internal methods.
request is {"argv": [...]}; the return value is the process exit code.
Imports are lazy so the sandbox smoke (pdd config show) needs no
third-party deps in the docker image.
"""

from __future__ import annotations


class Adapter:
    def handle(self, request: dict) -> int:
        if not isinstance(request, dict):
            return 2
        argv = (request or {}).get("argv") or []
        if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            return 2
        from .cli import run
        return run(argv)
