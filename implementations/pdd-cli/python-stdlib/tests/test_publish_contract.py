"""S-001: publish payload conforms to the pdd-cli request schema.

The schema is inlined (mirroring pdd-bundles/pdd-cli/schemas/request.schema.json)
so the suite runs from the engine's temp copy, where the repo bundle tree is
absent. The bundle file is the source of truth; keep them in lockstep.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from pdd import evidence as ev
from pdd.registry import publish

REQUEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PublishRequest",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "namespace": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "minLength": 1},
        "bundle": {"type": "object", "additionalProperties": {"type": "string"},
                   "minProperties": 1},
        "evidence": {"type": "object", "additionalProperties": True,
                     "required": ["protocol", "implementation", "validators",
                                  "results", "digest", "signature"]},
        "validation_resource": {"type": ["string", "null"]},
        "discovery": {"type": ["object", "null"]},
    },
    "required": ["namespace", "name", "version", "bundle", "evidence"],
}


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(ev.KEY_ENV, "test-key")
    yield


def _evidence():
    return ev.build_evidence(
        {"name": "demo", "version": "1.0.0", "bundle_digest": "sha256:abc"},
        "sha256:impl", [{"id": "v", "version": "1"}], [], {})


def test_publish_payload_conforms_to_request_schema(tmp_path, key):
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "protocol.yaml").write_text(
        "protocol:\n  name: demo\n  version: 1.0.0\n  status: sealed\n  namespace: test-ns\n")
    (bundle / "invariants").mkdir()
    discovery = {"files": ["protocol.yaml"], "dependencies": [], "invariant_lineage": {},
                 "known_limitations": []}
    payload = publish.build_payload(bundle, _evidence(), discovery)
    jsonschema.validate(payload, REQUEST_SCHEMA)
    assert payload["namespace"] == "test-ns"
    assert payload["name"] == "demo"
    assert payload["discovery"] == discovery
    assert "protocol.yaml" in payload["bundle"]


def test_build_payload_requires_namespace(tmp_path, key):
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "protocol.yaml").write_text(
        "protocol:\n  name: demo\n  version: 1.0.0\n  status: sealed\n")
    with pytest.raises(ValueError):
        publish.build_payload(bundle, _evidence())


def test_publish_missing_bundle_is_operational_failure(handle):
    assert handle({"argv": ["registry", "publish", "some-dir"]}) == 1
