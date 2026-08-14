"""B-003: staleness gate — latest admission evidence vs on-disk bundle digest."""

from __future__ import annotations

import json
import os

import pytest

from pdd import engine
from pdd import evidence as ev
from pdd.workflow import staleness


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(ev.KEY_ENV, "test-key")
    yield


def _mini_bundle(tmp_path, name="demo"):
    b = tmp_path / "bundle" / name
    b.mkdir(parents=True)
    (b / "protocol.yaml").write_text(f"protocol:\n  name: {name}\n  version: 1.0.0\n  status: sealed\n")
    return b


def _attest(bundle, tmp_path, key):
    """Build an admission evidence object attesting the current bundle digest."""
    digest = engine.bundle_digest(bundle)
    obj = ev.build_evidence(
        {"name": bundle.name, "version": "1.0.0", "bundle_digest": digest},
        "sha256:impl", [{"id": "v", "version": "1"}],
        [{"invariant_id": "B-003", "outcome": "pass"}], {})
    # _fresh falls back to <bundle.parent>/evidence when the bundle is not in
    # a workspace — so evidence lives at <bundle.parent>/evidence/<name>/.
    adm = bundle.parent / "evidence" / bundle.name / "admission"
    adm.mkdir(parents=True)
    (adm / "x.evidence.json").write_text(json.dumps(obj))


def test_fresh_when_evidence_attests_current_digest(tmp_path, key):
    bundle = _mini_bundle(tmp_path)
    _attest(bundle, tmp_path, key)
    assert staleness._fresh(bundle) is True


def test_stale_after_bundle_change(tmp_path, key):
    bundle = _mini_bundle(tmp_path)
    _attest(bundle, tmp_path, key)
    (bundle / "protocol.yaml").write_text(
        (bundle / "protocol.yaml").read_text() + "# changed\n")
    assert staleness._fresh(bundle) is False


def test_stale_when_no_evidence(tmp_path, key):
    bundle = _mini_bundle(tmp_path)
    assert staleness._fresh(bundle) is False


def test_staleness_command_exit_codes(tmp_path, key):
    bundle = _mini_bundle(tmp_path)
    _attest(bundle, tmp_path, key)
    os.chdir(tmp_path)
    assert staleness.run([str(bundle)]) == 0
    (bundle / "protocol.yaml").write_text(
        (bundle / "protocol.yaml").read_text() + "# changed\n")
    assert staleness.run([str(bundle)]) == 1
