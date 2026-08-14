"""HTTP client for the pdd-registry instance (stdlib urllib only).

The server API is read-only except POST /publish (bearer token). Errors are
surfaced as exit-1 failures with the server's message; the fail-closed
discipline applies: connection or protocol failures are never silent.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from .. import config as cfg


def resolve_registry(argv: list[str]) -> str:
    if "--registry" in argv:
        idx = argv.index("--registry")
        if idx + 1 >= len(argv):
            sys.exit("usage error: --registry requires a value")
        return argv[idx + 1].rstrip("/")
    return cfg.registry_url().rstrip("/")


def get(url: str, path: str, params: dict | None = None, timeout: int = 30) -> dict:
    full = url + path
    if params:
        full += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:500]
        sys.exit(f"registry error {exc.code} on {path}: {body}")
    except urllib.error.URLError as exc:
        sys.exit(f"registry unreachable at {url}: {exc.reason}")
    except ValueError as exc:
        sys.exit(f"registry returned non-JSON on {path}: {exc}")


def post(url: str, path: str, payload: dict, token: str, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url + path, data=data, method="POST",
        headers={"Accept": "application/json",
                 "Content-Type": "application/json",
                 "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:500]
        sys.exit(f"publish rejected ({exc.code}): {body}")
    except urllib.error.URLError as exc:
        sys.exit(f"registry unreachable at {url}: {exc.reason}")
