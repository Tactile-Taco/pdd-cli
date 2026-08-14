"""B-001: property-based dispatch determinism (hypothesis).

handle(argv) must never raise, must return a code in {0, 1, 2}, and must be
deterministic for identical argv.
"""

from __future__ import annotations

import os
import random

from hypothesis import given, settings
from hypothesis import strategies as st

from pdd import Adapter


@settings(max_examples=200, deadline=None)
@given(st.lists(st.text(min_size=0, max_size=40), max_size=5))
def test_handle_returns_valid_code_without_raising(argv):
    os.environ["PDD_REGISTRY"] = "http://127.0.0.1:1"
    try:
        code = Adapter().handle({"argv": argv})
        assert code in (0, 1, 2)
    finally:
        del os.environ["PDD_REGISTRY"]


@settings(max_examples=100, deadline=None)
@given(st.lists(st.text(min_size=0, max_size=40), max_size=4))
def test_handle_is_deterministic(argv):
    os.environ["PDD_REGISTRY"] = "https://determinism.example"
    try:
        assert Adapter().handle({"argv": argv}) == Adapter().handle({"argv": argv})
    finally:
        del os.environ["PDD_REGISTRY"]
