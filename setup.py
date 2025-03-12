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

linux_arm = '00a243112f22a94594a82cb9399b086cf51441e3d9fef98b1203d633863506ed'
linux_arm64 = 'b3976121710fd4b12bf641b0a7fb2686da598fb0da9f148c641b61b54cfa3407'
linux_amd64 = '1904ec6bac715c1d05cd7f6612eec8f67a625c3749cb327e5bfb4127d09035ff'
darwin_amd64 = '810a76cb7c78351e021c8025f344b12149d8426ce51609a179af68109ed5698e'
darwin_arm64 = 'af206d234dff5d05d9ac355529b2b33a7a78e13fab9b59db777746aab3e72530'
windows_amd64_exe = 'd11a0880588304496065110cb67ce2375cfcd5433e76dec505ce1fa21adf47cc'
windows_386_exe = 'facfb70de36cc3b15d59938fd840d6eaa8dc5446767f043265038a49eb719ec7'

SHFMT_VERSION = '3.11.0'
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
