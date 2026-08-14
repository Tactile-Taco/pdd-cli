"""B-001/B-005: config resolution order and B-002: no secrets in output.

Registry URL resolution: $PDD_REGISTRY > config file > baked default.
"""

from __future__ import annotations

import json
import os

import pytest

from pdd import config as cfg


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point the config file at a temp dir and clear env per test."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("PDD_REGISTRY", raising=False)
    yield


def test_default_when_nothing_set():
    assert cfg.registry_url() == cfg.DEFAULT_REGISTRY


def test_env_wins_over_config_file(tmp_path, monkeypatch):
    cfg.set_registry("https://config.example")
    monkeypatch.setenv("PDD_REGISTRY", "https://env.example")
    assert cfg.registry_url() == "https://env.example"
    assert cfg.show()["registry_source"] == "env"


def test_config_file_wins_over_default():
    cfg.set_registry("https://config.example")
    assert cfg.registry_url() == "https://config.example"
    assert cfg.show()["registry_source"] == "config-file"


def test_config_resolution_order_property():
    """B-001: order env > file > default regardless of prior state."""
    cfg.set_registry("https://config.example")
    assert cfg.registry_url() == "https://config.example"
    os.environ["PDD_REGISTRY"] = "https://env.example"
    assert cfg.registry_url() == "https://env.example"
    del os.environ["PDD_REGISTRY"]
    assert cfg.registry_url() == "https://config.example"


def test_set_registry_rejects_non_http(monkeypatch):
    with pytest.raises(ValueError):
        cfg.set_registry("not-a-url")


def test_config_show_never_prints_secrets(handle, capsys, monkeypatch):
    """B-002: tokens/keys live in env and are never echoed by config show."""
    monkeypatch.setenv("PDD_EVIDENCE_KEY", "super-secret-key-material")
    monkeypatch.setenv("PDD_PUBLISH_TOKEN", "super-secret-token-material")
    assert handle({"argv": ["config", "show"]}) == 0
    out = capsys.readouterr().out
    assert "super-secret" not in out
    assert "PDD_EVIDENCE_KEY" not in out
    assert "PDD_PUBLISH_TOKEN" not in out
