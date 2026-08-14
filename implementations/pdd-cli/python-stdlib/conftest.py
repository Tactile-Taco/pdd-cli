# Candidate root conftest: pytest inserts this directory into sys.path, so
# the engine's behavioral layer (which runs the suite from a temp copy with
# cwd outside the repo tree) can `import pdd`.
import pytest

from pdd import Adapter


@pytest.fixture
def handle():
    return Adapter().handle
