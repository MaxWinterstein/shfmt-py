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

linux_arm = '774b9a86cff4844179328cfbab2f602e75dcb68132e918e5271d015b3295c9c7'
linux_arm64 = '2091a31afd47742051a77bf7cfd175533ab07e924c20ef3151cd108fa1cab5b0'
linux_amd64 = '70aa99784703a8d6569bbf0b1e43e1a91906a4166bf1a79de42050a6d0de7551'
darwin_amd64 = 'b6890a0009abf71d36d7c536ad56e3132c547ceb77cd5d5ee62b3469ab4e9417'
darwin_arm64 = '650970603b5946dc6041836ddcfa7a19d99b5da885e4687f64575508e99cf718'
windows_amd64_exe = '62241aaf6b0ca236f8625d8892784b73fa67ad40bc677a1ad1a64ae395f6a7d5'
windows_386_exe = 'f3e32b2a320a3053837add32803d7fb3b730d3f10b84a867d327a549ef068fa0'

SHFMT_VERSION = '3.13.0'
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
