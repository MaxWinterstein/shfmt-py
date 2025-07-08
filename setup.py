#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import http
import os.path
import platform
import stat
import sys
import urllib.request

from distutils.command.build import build as orig_build
from distutils.core import Command
from setuptools import setup
from setuptools.command.install import install as orig_install

linux_arm = 'a93c1ed5be25ce9dd0fd62c4cf0af7453740d234725877b973e6c6a8c7598500'
linux_arm64 = '5f3fe3fa6a9f766e6a182ba79a94bef8afedafc57db0b1ad32b0f67fae971ba4'
linux_amd64 = 'd9fbb2a9c33d13f47e7618cf362a914d029d02a6df124064fff04fd688a745ea'
darwin_amd64 = 'c31548693de6584e6164b7ed5fbb7b4a083f2d937ca94b4e0ddf59aa461a85e4'
darwin_arm64 = 'd903802e0ce3ecbc82b98512f55ba370b0d37a93f3f78de394f5b657052b33dd'
windows_amd64_exe = 'c8bda517ba1c640ce4a715c0fa665439ddbe4357ba5e9b77b0e51e70e2b9c94b'
windows_386_exe = '92c1ef0af344a10f2cefe3ce4bc6793ae8b3719ac08fc01802bbd8eae105e534'

SHFMT_VERSION = '3.12.0'
POSTFIX_SHA256 = {
    ('linux', 'armv6hf'): (
        'linux_arm',
        linux_arm,
    ),
    ('linux', 'aarch64'): (
        'linux_arm64',
        linux_arm64,
    ),
    ('linux', 'x86_64'): (
        'linux_amd64',
        linux_amd64,
    ),
    ('darwin', 'x86_64'): (
        'darwin_amd64',
        darwin_amd64,
    ),
    ('darwin', 'arm64'): (
        'darwin_arm64',
        darwin_arm64,
    ),
    ('win32', 'AMD64'): (
        'windows_amd64.exe',
        windows_amd64_exe,
    ),
    ('win32', 'x86'): (
        'windows_386.exe',
        windows_386_exe,
    ),
}
POSTFIX_SHA256[('cygwin', 'x86_64')] = POSTFIX_SHA256[('win32', 'AMD64')]
POSTFIX_SHA256[('linux', 'armv7l')] = POSTFIX_SHA256[('linux', 'armv6hf')]
PY_VERSION = '2'


def get_download_url() -> tuple[str, str]:
    postfix, sha256 = POSTFIX_SHA256[(sys.platform, platform.machine())]
    url = (
        f'https://github.com/mvdan/sh/releases/download/'
        f'v{SHFMT_VERSION}/shfmt_v{SHFMT_VERSION}_{postfix}'
    )
    print(url)
    return url, sha256


def download(url: str, sha256: str) -> bytes:
    with urllib.request.urlopen(url) as resp:
        code = resp.getcode()
        if code != http.HTTPStatus.OK:
            raise ValueError(f'HTTP failure. Code: {code}')
        data = resp.read()

    checksum = hashlib.sha256(data).hexdigest()
    if checksum != sha256:
        raise ValueError(f'sha256 mismatch, expected {sha256}, got {checksum}')

    return data


def save_executable(data: bytes, base_dir: str):
    exe = 'shfmt' if sys.platform != 'win32' else 'shfmt.exe'
    output_path = os.path.join(base_dir, exe)
    os.makedirs(base_dir, exist_ok=True)

    with open(output_path, 'wb') as fp:
        fp.write(data)

    # Mark as executable.
    # https://stackoverflow.com/a/14105527
    mode = os.stat(output_path).st_mode
    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(output_path, mode)


class build(orig_build):
    sub_commands = orig_build.sub_commands + [('fetch_binaries', None)]


class install(orig_install):
    sub_commands = orig_install.sub_commands + [('install_shfmt', None)]


class fetch_binaries(Command):
    build_temp = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options('build', ('build_temp', 'build_temp'))

    def run(self):
        # save binary to self.build_temp
        url, sha256 = get_download_url()
        data = download(url, sha256)
        save_executable(data, self.build_temp)


class install_shfmt(Command):
    description = 'install the shfmt executable'
    outfiles = ()
    build_dir = install_dir = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        # this initializes attributes based on other commands' attributes
        self.set_undefined_options('build', ('build_temp', 'build_dir'))
        self.set_undefined_options(
            'install', ('install_scripts', 'install_dir'),
        )

    def run(self):
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

    def get_outputs(self):
        return self.outfiles


command_overrides = {
    'install': install,
    'install_shfmt': install_shfmt,
    'build': build,
    'fetch_binaries': fetch_binaries,
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
            return 'py2.py3', 'none', plat

    command_overrides['bdist_wheel'] = bdist_wheel

setup(version=f'{SHFMT_VERSION}.{PY_VERSION}', cmdclass=command_overrides)
