#!/usr/bin/env bash
# Rewrite the pre-commit `rev:` in README.md to the release being built, and
# pin the package version to that same tag.
#
# README.md is the PyPI long_description, so the `rev:` in it is what users
# copy off the project page. sync_readme_to_release.yml rewrites that line only
# *after* a release is published, which is too late for the artifacts built
# from the tag: v4.0.0 shipped `rev: v3.13.0.3`, and v3.13.0.3 shipped
# `rev: v3.13.0.1`. Rewriting it here, in the build tree only, makes each
# artifact advertise itself.
#
# Pinning the version is not optional. The rewrite leaves the working tree
# dirty, and setuptools-scm treats a dirty tree as "past the tag": building
# v4.0.0 dirty yields 4.0.1.dev0 instead of 4.0.0. SETUPTOOLS_SCM_PRETEND_VERSION
# keeps the published version exactly the tag. Verified both ways locally.
#
# Expects $TAG (e.g. v4.1.0) and, when running under Actions, $GITHUB_ENV.
set -euo pipefail

: "${TAG:?TAG must be set to the release tag, e.g. v4.1.0}"

python - <<'PY'
import os
import pathlib
import re

tag = os.environ["TAG"]
readme = pathlib.Path("README.md")
text = readme.read_text(encoding="utf-8")

# Same shape as the sed in sync_readme_to_release.yml, so the two agree on
# what a rev line looks like.
new_text, count = re.subn(
    r"(rev:\s+)v?[0-9]+(?:\.[0-9]+)+",
    lambda m: m.group(1) + tag,
    text,
)
if not count:
    raise SystemExit("::error::no pre-commit `rev:` line found in README.md")

readme.write_text(new_text, encoding="utf-8")
print(f"stamped {count} rev line(s) to {tag}")
PY

# Strip a leading "v": tags are v4.1.0, PEP 440 versions are 4.1.0.
version="${TAG#v}"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "SETUPTOOLS_SCM_PRETEND_VERSION=${version}" >>"$GITHUB_ENV"
  echo "pinned SETUPTOOLS_SCM_PRETEND_VERSION=${version}"
fi
