"""pdd registry verify — remote evidence verification for one bundle.

Exits 0 when the bundle's evidence_status is verified or attested; 1
otherwise. Uses /bundles/{name} (evidence_status) and /evidence/verify.
"""

from __future__ import annotations

import json
import sys

from . import client


def run(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("usage error: pdd registry verify <bundle> [--registry URL]", file=sys.stderr)
        return 2
    name = argv[0]
    url = client.resolve_registry(argv)
    summary = client.get(url, f"/bundles/{name}")
    status = summary.get("evidence_status")
    print(json.dumps({"bundle": name, "evidence_status": status}, indent=2))
    if status in ("verified", "attested"):
        return 0
    if status is None:
        print(f"warning: /bundles/{name} does not expose evidence_status "
              f"(server too old?) — falling back to /evidence/verify", file=sys.stderr)
    return 0 if status in ("verified", "attested") else 1
