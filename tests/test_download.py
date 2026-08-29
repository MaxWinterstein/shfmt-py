"""Tests for the integrity check in setup.py's download().

This is the security-critical path of the whole distribution: on every install
that builds from source, download() is what decides whether the bytes fetched
from GitHub become the shfmt binary on the user's PATH. CI only ever downloads
*correct* binaries, so an inverted comparison or a mismatch downgraded to a
warning would go green everywhere while silently accepting any payload.

No network: urlopen is stubbed, so these assert the logic rather than GitHub.
"""

from __future__ import annotations

import hashlib

import pytest

PAYLOAD = b"#!/bin/sh\necho not really shfmt\n"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


class _FakeResponse:
    """Minimal stand-in for the object urlopen returns.

    Implements the context-manager protocol for real, because download() uses
    `with urllib.request.urlopen(url) as resp:` — a MagicMock would satisfy
    that by accident and prove nothing.
    """

    def __init__(self, data: bytes, code: int = 200) -> None:
        self._data = data
        self._code = code

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def getcode(self) -> int:
        return self._code

    def read(self) -> bytes:
        return self._data


@pytest.fixture
def fake_urlopen(setup_mod, monkeypatch):
    """Point setup.py's urlopen at a canned response."""

    def _install(data: bytes, code: int = 200):
        monkeypatch.setattr(
            setup_mod.urllib.request,
            "urlopen",
            lambda url: _FakeResponse(data, code),
        )

    return _install


def test_download_returns_bytes_when_checksum_matches(setup_mod, fake_urlopen):
    fake_urlopen(PAYLOAD)

    assert setup_mod.download("https://example.invalid/shfmt", PAYLOAD_SHA256) == PAYLOAD


def test_download_rejects_a_checksum_mismatch(setup_mod, fake_urlopen):
    """The one that matters: wrong bytes must abort the install, not warn."""
    fake_urlopen(b"totally different bytes")

    with pytest.raises(ValueError, match="sha256 mismatch"):
        setup_mod.download("https://example.invalid/shfmt", PAYLOAD_SHA256)


def test_download_mismatch_message_names_both_checksums(setup_mod, fake_urlopen):
    """A bare 'mismatch' leaves the user with nothing to compare against."""
    fake_urlopen(b"totally different bytes")
    actual = hashlib.sha256(b"totally different bytes").hexdigest()

    with pytest.raises(ValueError) as excinfo:
        setup_mod.download("https://example.invalid/shfmt", PAYLOAD_SHA256)

    assert PAYLOAD_SHA256 in str(excinfo.value)
    assert actual in str(excinfo.value)


def test_download_rejects_a_non_ok_status(setup_mod, fake_urlopen):
    """An error page hashes to something; it must not be mistaken for a binary."""
    fake_urlopen(b"<html>404</html>", code=404)

    with pytest.raises(ValueError, match="HTTP failure"):
        setup_mod.download("https://example.invalid/shfmt", PAYLOAD_SHA256)


def test_every_pinned_platform_has_a_64_hex_digit_sha256(setup_mod):
    """Guards the hand-maintained table the update bot rewrites."""
    assert setup_mod.POSTFIX_SHA256, "platform table is empty"

    for key, (postfix, sha256) in setup_mod.POSTFIX_SHA256.items():
        assert len(sha256) == 64, f"{key} -> {postfix}: sha256 is not 64 chars"
        assert not set(sha256) - set("0123456789abcdef"), f"{key} -> {postfix}: not lowercase hex"
