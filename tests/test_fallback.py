"""Tests for the FreeBSD-style PATH fallback in setup.py.

setup.py is loaded via importlib (rather than `import setup`) so we can give
the module its own name and avoid colliding with anything else in sys.modules.
The `if __name__ == "__main__":` guard at the bottom of setup.py keeps the
real setup() call from running during these tests.
"""

from __future__ import annotations

import importlib.util
import sys
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
    return _load_setup_module()


def _exe_basename() -> str:
    return "shfmt.exe" if sys.platform == "win32" else "shfmt"


def test_fallback_copies_system_shfmt(setup_mod, tmp_path, monkeypatch):
    """When the platform is unsupported but shfmt is on PATH, copy it to build_temp."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_shfmt = bin_dir / _exe_basename()
    fake_shfmt.write_text("#!/bin/sh\necho fake-shfmt\n")
    fake_shfmt.chmod(0o755)

    monkeypatch.setenv("PATH", str(bin_dir))
    if sys.platform == "win32":
        monkeypatch.setenv("PATHEXT", ".EXE")

    build_temp = tmp_path / "build"
    setup_mod.fall_back_to_path_shfmt(str(build_temp))

    copied = build_temp / _exe_basename()
    assert copied.exists(), "fall_back_to_path_shfmt did not copy the binary"
    assert copied.read_bytes() == fake_shfmt.read_bytes(), "copy is not byte-identical"


def test_fallback_raises_when_no_shfmt_on_path(setup_mod, tmp_path, monkeypatch):
    """When neither the platform manifest nor PATH has shfmt, raise a clear error."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    if sys.platform == "win32":
        monkeypatch.setenv("PATHEXT", ".EXE")

    with pytest.raises(RuntimeError, match=r"no `shfmt` found on PATH"):
        setup_mod.fall_back_to_path_shfmt(str(tmp_path / "build"))
