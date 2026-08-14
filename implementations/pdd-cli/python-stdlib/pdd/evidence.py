#!/usr/bin/env python3
"""Evidence Chain + Dynamic Evidence Ledger primitives (HMAC-signed, SHA-256 chained).

Byte-compatible port of the pdd-registry evidence chain (pdd-evidence-keeper
skill): canon, digest, sign, build_evidence, append_block, verify_ledger and
verify_evidence_object are algorithmically identical, so evidence signed by the
registry tooling verifies here and vice versa. The one difference: the key is
read lazily per operation (fail-closed) instead of at import time, so the CLI
stays usable for non-evidence commands without PDD_EVIDENCE_KEY set.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

KEY_ENV = "PDD_EVIDENCE_KEY"


def _require_key() -> bytes:
    key = os.environ.get(KEY_ENV)
    if not key:
        sys.exit(
            f"error: {KEY_ENV} is not set (or is empty); refusing to sign or verify evidence "
            "(fail closed). Export the same key used at signing time.")
    return key.encode()


def canon(x): return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(b): return "sha256:" + hashlib.sha256(b).hexdigest()


def digest_obj(x): return digest_bytes(canon(x))


def sign(d): return "hmac-sha256:" + hmac.new(_require_key(), d.encode(), hashlib.sha256).hexdigest()


def build_evidence(protocol, impl_digest, validators, results, meta):
    body = {"protocol": protocol, "implementation": {"artifact_digest": impl_digest},
            "validators": validators, "results": results,
            "provenance": {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **meta}}
    body["digest"] = digest_obj(body)
    body["signature"] = sign(body["digest"])
    return body


def append_block(ledger_path, protocol, impl_version, observations, decision):
    p = Path(ledger_path)
    prev = "sha256:" + "0" * 64
    if p.exists() and p.stat().st_size:
        prev = json.loads(p.read_text().strip().splitlines()[-1])["digest"]
    block = {"previous": prev, "protocol": protocol, "implementation_version": impl_version,
             "observations": observations, "decision": decision,
             "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    block["digest"] = digest_obj(block)
    block["signature"] = sign(block["digest"])
    with p.open("a") as f:
        f.write(json.dumps(block) + "\n")
    return block


def verify_ledger(ledger_path):
    prev = "sha256:" + "0" * 64
    lines = ([ln for ln in Path(ledger_path).read_text().strip().splitlines() if ln.strip()]
             if Path(ledger_path).exists() else [])
    if not lines:
        return {"ok": False, "blocks": 0, "reason": "empty-ledger"}
    n = 0
    for i, line in enumerate(lines):
        b = json.loads(line)
        if b["previous"] != prev:
            return {"ok": False, "diverged_at": i, "reason": "chain-link"}
        d = dict(b)
        dg = d.pop("digest")
        d.pop("signature", None)
        if digest_obj(d) != dg:
            return {"ok": False, "diverged_at": i, "reason": "digest"}
        if not hmac.compare_digest(sign(dg), b.get("signature", "")):
            return {"ok": False, "diverged_at": i, "reason": "signature"}
        prev = dg
        n = i + 1
    return {"ok": True, "blocks": n}


def verify_evidence_object(path):
    """Recompute digest + signature of one admission evidence object."""
    b = json.loads(Path(path).read_text())
    d = dict(b)
    dg = d.pop("digest")
    d.pop("signature", None)
    if digest_obj(d) != dg:
        return {"ok": False, "reason": "digest"}
    if not hmac.compare_digest(sign(dg), b.get("signature", "")):
        return {"ok": False, "reason": "signature"}
    return {"ok": True, "digest": dg}
