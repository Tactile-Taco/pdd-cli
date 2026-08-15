"""B-004: workflow (local) commands perform no network I/O.

The import graph of pdd.workflow + the local-only modules must never touch
urllib/socket/requests — networking is confined to pdd.registry.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parent.parent / "pdd"

# Modules reachable from `pdd workflow ...` without the registry namespace,
# relative to the pdd package dir.
LOCAL_MODULES = [
    "cli.py",
    "adapter.py",
    "config.py",
    "config_cmd.py",
    "evidence.py",
    "engine.py",
    "lint.py",
    "lint_validate.py",
    "workflow/__init__.py",
    "workflow/init.py",
    "workflow/lint.py",
    "workflow/seal.py",
    "workflow/validate.py",
    "workflow/evidence.py",
    "workflow/assembly.py",
    "workflow/run.py",
    "workflow/staleness.py",
    "workflow/status.py",
]

NETWORK_MODULES = {"urllib", "socket", "requests", "http"}


def _imports(path: Path) -> set:
    tree = ast.parse(path.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


@pytest.mark.parametrize("rel", LOCAL_MODULES)
def test_local_module_has_no_network_imports(rel):
    src = PKG / rel
    assert src.exists(), f"{rel} missing"
    assert not (_imports(src) & NETWORK_MODULES), f"{rel} imports network module"


def test_registry_modules_may_use_urllib():
    src = PKG / "registry" / "client.py"
    assert "urllib" in _imports(src)


def test_local_graph_does_not_reach_registry_client():
    """The workflow dispatch must not import pdd.registry (only via lazy
    top-level dispatch, which selects one namespace per invocation)."""
    tree = ast.parse((PKG / "workflow" / "__init__.py").read_text())
    imports = " ".join(
        a.name for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) for a in node.names)
    assert "registry" not in imports
