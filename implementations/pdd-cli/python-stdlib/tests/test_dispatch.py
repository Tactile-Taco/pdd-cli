"""S-002 / B-001: exit-code envelope and deterministic dispatch.

The Adapter surface never raises and returns codes in {0, 1, 2}; usage errors
exit 2; identical argv produces identical results.
"""

from __future__ import annotations

import pytest

from pdd import Adapter


def test_empty_argv_is_usage_error(handle):
    assert handle({"argv": []}) == 2


def test_no_command_is_usage_error(handle):
    assert handle({"argv": []}) == 2


def test_unknown_command_is_usage_error(handle):
    assert handle({"argv": ["frobnicate"]}) == 2


def test_unknown_workflow_subcommand_is_usage_error(handle):
    assert handle({"argv": ["workflow", "frobnicate"]}) == 2


def test_unknown_registry_subcommand_is_usage_error(handle):
    assert handle({"argv": ["registry", "frobnicate"]}) == 2


def test_bad_adapter_request_returns_usage_error():
    assert Adapter().handle("not a dict") == 2
    assert Adapter().handle({"argv": "not a list"}) == 2
    assert Adapter().handle({"argv": [1, 2, 3]}) == 2


def test_config_show_succeeds(handle, capsys):
    assert handle({"argv": ["config", "show"]}) == 0
    out = capsys.readouterr().out
    assert "registry:" in out


def test_dispatch_is_deterministic(handle, capsys):
    first = handle({"argv": ["config", "show"]})
    capsys.readouterr()
    second = handle({"argv": ["config", "show"]})
    assert first == second == 0


def test_missing_bundle_is_operational_failure(handle):
    assert handle({"argv": ["workflow", "validate", "bundle-x"]}) == 1


def test_help_exits_zero(handle):
    assert handle({"argv": ["--help"]}) == 0
