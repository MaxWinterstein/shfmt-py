"""Tests for the bdist_wheel overrides in setup.py.

This distribution ships a prebuilt shfmt binary and no Python source, so the
wheel must be tagged `py2.py3-none-<platform>`. If the overrides ever stop
being registered, the wheel silently becomes `py3-none-any` and the binary
gets published as if it were pure Python — these tests guard that tag.

See tests/test_fallback.py for why setup.py is loaded via importlib.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest
from setuptools.dist import Distribution

SETUP_PY = Path(__file__).parent.parent / "setup.py"


def _load_setup_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("setup_under_test", SETUP_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def setup_mod() -> types.ModuleType:
    return _load_setup_module()


@pytest.fixture
def wheel_cmd(setup_mod):
    dist = Distribution({"name": "shfmt-py", "version": "0.0.0"})
    cmd = setup_mod.bdist_wheel(dist)
    cmd.finalize_options()
    return cmd


def test_bdist_wheel_override_is_registered(setup_mod):
    """setup() must receive our subclass, not setuptools' stock command."""
    assert setup_mod.command_overrides["bdist_wheel"] is setup_mod.bdist_wheel


def test_wheel_is_not_pure_python(wheel_cmd):
    """root_is_pure=False is what keeps the platform tag off `any`."""
    assert wheel_cmd.root_is_pure is False


def test_tag_is_platform_specific_and_version_agnostic(wheel_cmd):
    """No Python source and no extensions, so the wheel works on any interpreter."""
    python_tag, abi_tag, platform_tag = wheel_cmd.get_tag()

    assert python_tag == "py2.py3"
    assert abi_tag == "none"
    assert platform_tag != "any", "binary distribution must not be tagged as pure Python"
