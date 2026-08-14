"""B-002 / evidence primitives: HMAC-sign, SHA-256 chain, fail-closed.

The evidence algorithm is byte-compatible with the pdd-registry chain; these
tests pin the roundtrip and tamper-detection behavior.
"""

from __future__ import annotations

import json
import os

import pytest

from pdd import evidence as ev


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(ev.KEY_ENV, "test-key")
    yield


def test_build_and_verify_evidence_roundtrip(key, tmp_path):
    proto = {"name": "demo", "version": "1.0.0", "bundle_digest": "sha256:abc"}
    obj = ev.build_evidence(proto, "sha256:impl", [{"id": "v", "version": "1"}],
                            [{"invariant_id": "B-001", "outcome": "pass"}],
                            {"manifest": "demo", "discovery_digest": "sha256:disc"})
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps(obj))
    assert ev.verify_evidence_object(p)["ok"] is True


def test_tamper_detected(key, tmp_path):
    proto = {"name": "demo", "version": "1.0.0", "bundle_digest": "sha256:abc"}
    obj = ev.build_evidence(proto, "sha256:impl", [], [], {})
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps(obj))
    obj["results"] = [{"invariant_id": "B-001", "outcome": "fail"}]
    p.write_text(json.dumps(obj))
    assert ev.verify_evidence_object(p)["ok"] is False


def test_ledger_chain_verify(key, tmp_path):
    ledger = tmp_path / "runtime-ledger.jsonl"
    ev.append_block(ledger, json.dumps({"id": "demo", "version": "1.0.0"}),
                    "demo@abc", {"admission": "sha256:impl"}, "attest-pass")
    ev.append_block(ledger, json.dumps({"id": "demo", "version": "1.0.0"}),
                    "demo@abc", {"note": "runtime attestation"}, "attest-pass")
    assert ev.verify_ledger(ledger)["ok"] is True
    assert ev.verify_ledger(ledger)["blocks"] == 2


def test_ledger_tamper_detected(key, tmp_path):
    ledger = tmp_path / "runtime-ledger.jsonl"
    ev.append_block(ledger, json.dumps({"id": "demo", "version": "1.0.0"}),
                    "demo@abc", {"admission": "sha256:impl"}, "attest-pass")
    ev.append_block(ledger, json.dumps({"id": "demo", "version": "1.0.0"}),
                    "demo@abc", {"note": "runtime attestation"}, "attest-pass")
    lines = ledger.read_text().splitlines()
    block = json.loads(lines[0])
    block["observations"]["admission"] = "sha256:evil"
    ledger.write_text(json.dumps(block) + "\n" + "\n".join(lines[1:]) + "\n")
    assert ev.verify_ledger(ledger)["ok"] is False


def test_fail_closed_without_key(monkeypatch, tmp_path):
    """B-002: no key -> refusing to sign/verify is the contract."""
    monkeypatch.delenv(ev.KEY_ENV, raising=False)
    with pytest.raises(SystemExit):
        ev.build_evidence({"name": "x"}, "sha256:y", [], [], {})
    ledger = tmp_path / "runtime-ledger.jsonl"
    with pytest.raises(SystemExit):
        ev.append_block(ledger, json.dumps({"id": "x"}), "x@y", {}, "attest-pass")
