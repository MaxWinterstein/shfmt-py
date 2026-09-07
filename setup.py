#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import http
import logging
import os.path
import platform
import shutil
import stat
import sys
import urllib.request

from setuptools import Command, setup
from setuptools.command.bdist_wheel import bdist_wheel as orig_bdist_wheel
from setuptools.command.build import build as orig_build
from setuptools.command.install import install as orig_install

linux_arm = "ede6c4adefeda196d963906daa7c1f20094e6def7a98bcb9f4c74079babf1eca"
linux_arm64 = "5f2db09dae91fca848f7adbdd014632e921a383863a2ad7e0450ad3aba0c6489"
linux_amd64 = "76e77641faa025814b77f153b29796b8e6fa2fca03e0c76a691608b86c7ea7bf"
darwin_amd64 = "d33eee0da0f92835b3562e9767a05cee7e4eaeef47daa03bfd09da17b4b590a6"
darwin_arm64 = "b7c872db63553ccffc7253aba3ed7d4885a27d83f1ba567b1138c6315a5847e5"
windows_amd64_exe = "13629ce28442ca80b6b5a819f7574ab39e1c28c6e26734ca816c9714e04851df"
windows_386_exe = "b6f171113e7359f44d5ffdc93a90b93a7d405aa8847129a6982e10fe4d356f1e"

SHFMT_VERSION = "3.14.1"
POSTFIX_SHA256 = {
    ("linux", "armv6hf"): (
        "linux_arm",
        linux_arm,
    ),
    ("linux", "aarch64"): (
        "linux_arm64",
        linux_arm64,
    ),
    ("linux", "x86_64"): (
        "linux_amd64",
        linux_amd64,
    ),
    ("darwin", "x86_64"): (
        "darwin_amd64",
        darwin_amd64,
    ),
    ("darwin", "arm64"): (
        "darwin_arm64",
        darwin_arm64,
    ),
    ("win32", "AMD64"): (
        "windows_amd64.exe",
        windows_amd64_exe,
    ),
    ("win32", "x86"): (
        "windows_386.exe",
        windows_386_exe,
    ),
}
POSTFIX_SHA256[("cygwin", "x86_64")] = POSTFIX_SHA256[("win32", "AMD64")]
POSTFIX_SHA256[("linux", "armv7l")] = POSTFIX_SHA256[("linux", "armv6hf")]
# Package version is now derived from the latest git tag via setuptools-scm
# (configured in pyproject.toml). SHFMT_VERSION above stays — it's needed to
# construct the binary download URL.


def get_download_url() -> tuple[str, str]:
    postfix, sha256 = POSTFIX_SHA256[(sys.platform, platform.machine())]
    url = f"https://github.com/mvdan/sh/releases/download/v{SHFMT_VERSION}/shfmt_v{SHFMT_VERSION}_{postfix}"
    print(url)
    return url, sha256


def download(url: str, sha256: str) -> bytes:
    with urllib.request.urlopen(url) as resp:
        code = resp.getcode()
        if code != http.HTTPStatus.OK:
            raise ValueError(f"HTTP failure. Code: {code}")
        data = resp.read()

    checksum = hashlib.sha256(data).hexdigest()
    if checksum != sha256:
        raise ValueError(f"sha256 mismatch, expected {sha256}, got {checksum}")

    return data


def save_executable(data: bytes, base_dir: str):
    exe = "shfmt" if sys.platform != "win32" else "shfmt.exe"
    output_path = os.path.join(base_dir, exe)
    os.makedirs(base_dir, exist_ok=True)

    with open(output_path, "wb") as fp:
        fp.write(data)

    # Mark as executable.
    # https://stackoverflow.com/a/14105527
    mode = os.stat(output_path).st_mode
    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(output_path, mode)


logger = logging.getLogger(__name__)


def fall_back_to_path_shfmt(build_temp: str) -> None:
    """Copy a system-installed shfmt into build_temp.

    Used when the current platform has no pre-built binary in
    POSTFIX_SHA256 (e.g. FreeBSD). Raises RuntimeError if no
    shfmt is found on PATH either.
    """
    plat = f"{sys.platform}:{platform.machine()}"
    logger.warning("No pre-built shfmt for %s; looking for one on PATH", plat)
    system_shfmt = shutil.which("shfmt")
    if system_shfmt is None:
        raise RuntimeError(
            f"No pre-built shfmt for {plat} and no `shfmt` found on PATH. "
            f"Install shfmt manually (e.g. via your OS package manager) and retry.",
        )
    # On Windows, shutil.which honors PATHEXT and could find shfmt.bat / .cmd
    # / .com etc. Renaming any of those to shfmt.exe produces a file Windows
    # refuses to execute.
    if sys.platform == "win32" and not system_shfmt.lower().endswith(".exe"):
        raise RuntimeError(
            f"Found {system_shfmt} on PATH, but it isn't a .exe; install the official shfmt.exe for Windows and retry.",
        )
    exe_name = "shfmt.exe" if sys.platform == "win32" else "shfmt"
    os.makedirs(build_temp, exist_ok=True)
    shutil.copy2(system_shfmt, os.path.join(build_temp, exe_name))
    logger.info("Using %s as shfmt source for this build", system_shfmt)


class build(orig_build):
    sub_commands = orig_build.sub_commands + [("fetch_binaries", None)]


class install(orig_install):
    sub_commands = orig_install.sub_commands + [("install_shfmt", None)]


class fetch_binaries(Command):
    build_temp = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options("build", ("build_temp", "build_temp"))

    def run(self):
        # Try the pre-built binary for this platform first; fall back to a
        # system-installed shfmt on PATH if the platform isn't in the
        # download manifest (e.g. FreeBSD, illumos).
        try:
            url, sha256 = get_download_url()
        except KeyError:
            fall_back_to_path_shfmt(self.build_temp)
            return
        data = download(url, sha256)
        save_executable(data, self.build_temp)


class install_shfmt(Command):
    description = "install the shfmt executable"
    outfiles = ()
    build_dir = install_dir = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        # this initializes attributes based on other commands' attributes
        self.set_undefined_options("build", ("build_temp", "build_dir"))
        self.set_undefined_options(
            "install",
            ("install_scripts", "install_dir"),
        )

    def run(self):
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

    def get_outputs(self):
        return self.outfiles


# orig_bdist_wheel is imported unconditionally at the top of this file: the
# build-system requires setuptools>=70.1, which ships bdist_wheel as a built-in
# command. Guarding that import would silently skip the overrides below and
# produce a pure-python wheel that ships the binary under a py3-none-any tag;
# failing loudly on a missing import is the safer trade.
class bdist_wheel(orig_bdist_wheel):
    def finalize_options(self):
        orig_bdist_wheel.finalize_options(self)
        # Mark us as not a pure python package
        self.root_is_pure = False

    def get_tag(self):
        _, _, plat = orig_bdist_wheel.get_tag(self)
        # We don't contain any python source, nor any python extensions
        return "py2.py3", "none", plat


command_overrides = {
    "install": install,
    "install_shfmt": install_shfmt,
    "build": build,
    "fetch_binaries": fetch_binaries,
    "bdist_wheel": bdist_wheel,
}

if __name__ == "__main__":
    setup(cmdclass=command_overrides)
