"""Shared fixtures for the setup.py tests.

setup.py is loaded via importlib (rather than `import setup`) so we can give
the module its own name and avoid colliding with anything else in sys.modules.
The `if __name__ == "__main__":` guard at the bottom of setup.py keeps the real
setup() call from running when we do.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest

SETUP_PY = Path(__file__).parent.parent / "setup.py"


def _load_setup_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("setup_under_test", SETUP_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def setup_mod() -> types.ModuleType:
    """A freshly loaded setup.py, so tests cannot leak state into each other."""
    return _load_setup_module()
