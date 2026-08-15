"""Assembly (composition instance) verify/derive tests.

Structural checks are network-free and yaml-only; run with pytest from the
package root (pdd-cli implementations/pdd-cli/python-stdlib).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from pdd.workflow import assembly  # noqa: E402

VALID = textwrap.dedent("""\
    environment:
      server-platform: { runtime: node@24 }
      browser-platform: { framework: react@18 }
    stitches:
      - consumer: ui-surfaces@impl-react
        seam: design-system.token-provider
        provider: design-system@impl-react
      - consumer: public-api@impl-react
        seam: todo-engine.engine
        provider: todo-engine@impl-react
      - consumer: todo-engine@impl-react
        seam: todo-store.store
        provider: todo-store@impl-react
""")


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "assembly.lock"
    p.write_text(text)
    return p


def test_verify_valid_assembly(tmp_path):
    lock = _write(tmp_path, VALID)
    assert assembly.verify(lock, None) == 0


def test_verify_cycle_fails(tmp_path):
    cyc = textwrap.dedent("""\
        environment:
          server-platform: { runtime: node@24 }
        stitches:
          - consumer: a@impl1
            seam: b.cap
            provider: b@impl1
          - consumer: b@impl1
            seam: a.cap
            provider: a@impl1
    """)
    assert assembly.verify(_write(tmp_path, cyc), None) == 1


def test_verify_dangling_seam_fails(tmp_path):
    bad = VALID.replace("seam: todo-engine.engine", "seam: nope.engine")
    assert assembly.verify(_write(tmp_path, bad), None) == 1


def test_verify_duplicate_binding_fails(tmp_path):
    dup = VALID + ("  - consumer: ui-surfaces@impl-react\n"
                   "    seam: design-system.token-provider\n"
                   "    provider: design-system@impl-react\n")
    assert assembly.verify(_write(tmp_path, dup), None) == 1


def test_derive_subset_with_closure(tmp_path):
    lock = _write(tmp_path, VALID)
    out = tmp_path / "derived.lock"
    assert assembly.derive(lock, ["public-api", "todo-engine", "todo-store"], out, None) == 0
    data = yaml.safe_load(out.read_text())
    kept = data["derived_protocols"]
    assert set(kept) == {"public-api", "todo-engine", "todo-store"}
    assert len(data["stitches"]) == 2
    assert data["derived_from"].endswith("assembly.lock")


def test_derive_unknown_protocol_fails(tmp_path):
    lock = _write(tmp_path, VALID)
    assert assembly.derive(lock, ["nope"], tmp_path / "x.lock", None) == 1
    assert not (tmp_path / "x.lock").exists()


def _write_bundle(bundles: Path, name: str, seams: dict) -> None:
    d = bundles / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "protocol.yaml").write_text(
        "protocol: { name: %s, version: 1.0.0, status: sealed }\nseams:\n"
        % name + "".join(
            "  %s:\n    kind: %s\n    handshake: %s\n"
            % (sn, s.get("kind", "inline"), sn)
            + ("    host: { class: %s }\n" % s["host"]["class"] if s.get("host") else "")
            for sn, s in seams.items()))


def test_bundle_aware_host_class_mismatch(tmp_path):
    lock = _write(tmp_path, VALID)
    bundles = tmp_path / "bundles"
    _write_bundle(bundles, "design-system",
                  {"token-provider": {"kind": "inline", "host": {"class": "browser-dom"}}})
    _write_bundle(bundles, "todo-engine",
                  {"engine": {"kind": "inline", "host": {"class": "node-runtime"}}})
    _write_bundle(bundles, "todo-store",
                  {"store": {"kind": "inline", "host": {"class": "node-runtime"}}})
    assert assembly.verify(lock, bundles) == 0  # browser + server platforms present
    _write_bundle(bundles, "design-system",
                  {"token-provider": {"kind": "inline", "host": {"class": "storage"}}})
    assert assembly.verify(lock, bundles) == 1  # no storage platform in env
