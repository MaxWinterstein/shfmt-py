#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import http
import os.path
import platform
import stat
import sys
import urllib.request

from setuptools import Command, setup
from setuptools.command.build import build as orig_build
from setuptools.command.install import install as orig_install

linux_arm = "f6c23b95971bcc5ebf86411bccefb79f1e99f8efe7c722d980a3f244838b1398"
linux_arm64 = "32d92acaa5cd8abb29fc49dac123dc412442d5713967819d8af2c29f1b3857c7"
linux_amd64 = "fb096c5d1ac6beabbdbaa2874d025badb03ee07929f0c9ff67563ce8c75398b1"
darwin_amd64 = "6feedafc72915794163114f512348e2437d080d0047ef8b8fa2ec63b575f12af"
darwin_arm64 = "9680526be4a66ea1ffe988ed08af58e1400fe1e4f4aef5bd88b20bb9b3da33f8"
windows_amd64_exe = "60cd368533d0ad73fa86d93d5bbf95ef40587245ce684ed138c1b31557b5fe97"
windows_386_exe = "9b4f368b837feb883a3b2bf38a46a94dcab4bca4b7c3e19f6710e0e09a56ce7c"

SHFMT_VERSION = "3.13.1"
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
        # save binary to self.build_temp
        url, sha256 = get_download_url()
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


command_overrides = {
    "install": install,
    "install_shfmt": install_shfmt,
    "build": build,
    "fetch_binaries": fetch_binaries,
}


try:
    from wheel.bdist_wheel import bdist_wheel as orig_bdist_wheel
except ImportError:
    pass
else:

    class bdist_wheel(orig_bdist_wheel):
        def finalize_options(self):
            orig_bdist_wheel.finalize_options(self)
            # Mark us as not a pure python package
            self.root_is_pure = False

        def get_tag(self):
            _, _, plat = orig_bdist_wheel.get_tag(self)
            # We don't contain any python source, nor any python extensions
            return "py2.py3", "none", plat

    command_overrides["bdist_wheel"] = bdist_wheel

setup(cmdclass=command_overrides)
