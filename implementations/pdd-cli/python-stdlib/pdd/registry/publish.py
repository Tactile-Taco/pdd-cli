"""pdd registry publish — submit a bundle + signed evidence to the registry.

Contract with the server's POST /publish:
  * bearer token (PDD_PUBLISH_TOKEN by default, or --token-env NAME)
  * idempotent by (namespace, name, version, bundle_digest): re-publishing
    the identical submission returns "already-published", not an error
  * the server recomputes the bundle digest from the submitted files and
    verifies the evidence object's signature against its own key
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .. import engine
from . import client


def build_payload(bundle_dir: Path, evidence: dict) -> dict:
    """Construct the POST /publish request body (S-001 schema conformance)."""
    proto = engine.load_yaml(bundle_dir / "protocol.yaml") or {}
    protocol = proto.get("protocol") or proto
    name = bundle_dir.name
    version = protocol.get("version") or "1.0.0"
    namespace = protocol.get("namespace")
    if not namespace:
        raise ValueError("protocol.yaml must declare `namespace` before publishing")
    bundle_files = {}
    for p in sorted(bundle_dir.rglob("*")):
        if p.is_file() and ".git" not in p.parts:
            bundle_files[p.relative_to(bundle_dir).as_posix()] = p.read_text()
    return {
        "namespace": namespace,
        "name": name,
        "version": version,
        "bundle": bundle_files,
        "evidence": evidence,
        "validation_resource": evidence.get("validation_resource"),
    }


def run(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("usage error: pdd registry publish <bundle-dir> --evidence <file> "
              "[--registry URL] [--token-env NAME]", file=sys.stderr)
        return 2
    bundle_dir = Path(argv[0]).resolve()
    if not (bundle_dir / "protocol.yaml").exists():
        print(f"error: no bundle at {bundle_dir} (missing protocol.yaml)", file=sys.stderr)
        return 1
    if "--evidence" not in argv:
        print("usage error: publish requires --evidence <file>", file=sys.stderr)
        return 2
    evidence_file = Path(argv[argv.index("--evidence") + 1]).resolve()
    if not evidence_file.exists():
        print(f"error: evidence file not found: {evidence_file}", file=sys.stderr)
        return 1
    token_env = "PDD_PUBLISH_TOKEN"
    if "--token-env" in argv:
        token_env = argv[argv.index("--token-env") + 1]
    token = os.environ.get(token_env)
    if not token:
        print(f"error: publish token missing — set ${token_env} "
              f"(never on the command line, B-002)", file=sys.stderr)
        return 1

    evidence = json.loads(evidence_file.read_text())
    for required in ("protocol", "implementation", "digest", "signature"):
        if required not in evidence:
            print(f"error: evidence object missing required field {required!r}", file=sys.stderr)
            return 1

    try:
        payload = build_payload(bundle_dir, evidence)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    url = client.resolve_registry(argv)
    result = client.post(url, "/publish", payload, token)
    print(json.dumps(result, indent=2))
    return 0
