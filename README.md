[![PyPI version](https://img.shields.io/pypi/v/shfmt-py.svg)](https://pypi.org/project/shfmt-py)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/shfmt-py.svg)](https://pypi.org/project/shfmt-py)
[![Downloads](https://static.pepy.tech/badge/shfmt-py/month)](https://pepy.tech/project/shfmt-py)
[![License](https://img.shields.io/pypi/l/shfmt-py.svg)](https://github.com/MaxWinterstein/shfmt-py/blob/master/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/MaxWinterstein/shfmt-py/master.svg)](https://results.pre-commit.ci/latest/github/MaxWinterstein/shfmt-py/master)

# shfmt-py

`pip install shfmt-py` puts [shfmt], the shell script formatter, on the `PATH` of your Python
environment and gives you a ready-made [pre-commit] hook.

This is packaging only — no patches, no Python API, nothing to `import`, no `python -m shfmt`. On
common platforms the wheel bundles upstream's binary; elsewhere the build downloads and
checksum-verifies it, or — where no build is pinned for your platform — copies an existing `shfmt`
from your `PATH` unverified ("How the binary gets installed" below has the details). For what
`shfmt` does and which flags it takes, run `shfmt --help` or read the [upstream docs][shfmt].

Modeled after [shellcheck-py], adapted for `shfmt`.

## Install

```bash
pip install shfmt-py
```

Or as a standalone tool, isolated from any project environment:

```bash
uv tool install shfmt-py
# or
pipx install shfmt-py
```

Requires Python 3.9 or newer; the binary itself has no Python runtime dependency. CI covers
CPython 3.9, 3.13 and 3.14 on Linux, macOS (arm64 and x86_64) and Windows.

The distribution installs exactly one executable — `shfmt`, or `shfmt.exe` on Windows — into the
environment's scripts directory, so it is on `PATH` whenever that environment is active.
`pip uninstall shfmt-py` removes it again.

## Pre-commit hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/MaxWinterstein/shfmt-py
  rev: v4.1.0rc1
  hooks:
    - id: shfmt
```

`rev` is the `shfmt-py` release tag, not the `shfmt` version. `pre-commit autoupdate` moves it to
the newest tag; `pre-commit run --all-files` formats the whole repository.

The hook runs on every file [identify] tags as `shell`, excluding `csh` and `tcsh`. It defaults to
`args: [-w]`, which rewrites files in place.

### Overriding args

pre-commit **replaces** the default `args`; it does not extend them. Drop `-w` by accident and
`shfmt` prints the formatted script to stdout, changes nothing and exits 0 — the hook goes green
while your files stay unformatted. So re-add it:

```yaml
- repo: https://github.com/MaxWinterstein/shfmt-py
  rev: v4.1.0rc1
  hooks:
    - id: shfmt
      args: [-w, -i, "2", -ci, -bn] # -w must be re-added
```

Those flags — two-space indent, indented `case` arms, binary operators allowed to start a line —
are the set the upstream manual describes as closely resembling Google's shell style. Quote the `2`:
pre-commit expects every argument to be a string, and YAML would otherwise make it an integer.

For a check-only run that reports instead of rewriting, swap the `args` above for:

```yaml
    - id: shfmt
      args: [-d] # print a diff and fail; no -w on purpose
```

### EditorConfig

`shfmt` reads formatting options from `.editorconfig`. Two of its behaviors matter for hook users:

- **Any parser or printer flag turns EditorConfig off entirely** — `-i`, `-ci`, `-s`, `-ln` and
  friends disable every EditorConfig formatting option, not just the one you overrode. `-w`, `-d`
  and `-l` are generic flags and leave it alone, so the default `args: [-w]` keeps `.editorconfig`
  in charge. Configure your style in one place, not both.
- **`ignore = true` is skipped for explicitly named files**, and pre-commit always names files
  explicitly. Use `args: [-w, --apply-ignore]` to honor it, or pre-commit's own `exclude:`.

### Hook installs need network access

pre-commit installs `language: python` hooks by running `pip install .` inside its own clone, so it
never uses the published wheels. Installing the hook therefore downloads the binary from the
`mvdan/sh` GitHub release the first time a given `rev` is used, and caches the result afterwards.
Restricted runners need `github.com` **and** its release-asset host (`*.githubusercontent.com`)
reachable — a PyPI mirror is not enough.

## Command line

```bash
shfmt --version    # the upstream version this release bundles
shfmt -w script.sh # format in place
shfmt -d .         # print a diff, exit 1 if anything differs
shfmt -l .         # list files that differ, exit 1 if any do
```

`shfmt --help` prints the full flag list. Dialects, EditorConfig keys and the default style are
upstream's documentation, not this project's: see [mvdan/sh][shfmt] and its
[man page source][manual] (or run `man shfmt`).

## How the binary gets installed

Three paths, in this order:

1. **A matching wheel.** Published for Linux x86_64 and aarch64 (manylinux2014), macOS arm64 and
   x86_64, and Windows amd64. The binary is already inside the wheel, so nothing is fetched at
   install time and a PyPI mirror is enough.
2. **From source, platform in the download table.** The other platforms this package pins a
   download for — 32-bit Windows, Linux armv7 (hosts whose `uname -m` reports `armv7l`), Cygwin,
   and musl-based distros such as Alpine, which use the ordinary static Linux binaries — plus any
   install that bypasses wheels (`pip install --no-binary :all: shfmt-py`, or pre-commit). The
   build downloads the official release asset and verifies it against a sha256 pinned in
   [setup.py]. A mismatch aborts the install, and if GitHub is unreachable the install fails rather
   than silently using something else.
3. **From source, platform not in the download table.** FreeBSD, illumos, 32-bit x86 Linux, older
   32-bit ARM and other architectures with no pinned download here: the build copies whatever
   `shfmt` it finds on your `PATH` (on Windows it must be a real `.exe`). That copy is neither
   checksummed nor version-checked, so it may differ from the version this release pins —
   `shfmt --version` is worth a look. With no `shfmt` on `PATH`, the install fails with an error
   telling you to install one, instead of installing something broken.

For air-gapped environments, build one wheel per target platform on a machine that can reach GitHub
(`python -m build --wheel`; on Linux set `_PYTHON_HOST_PLATFORM=manylinux2014_x86_64`, as the
release workflow does, or the wheel comes out tagged `linux_x86_64`) and serve them from your
internal index. That covers `pip` / `uv` / `pipx` installs only: pre-commit builds the hook from
source and still reaches for GitHub, so an air-gapped runner additionally needs a mirror of the
`mvdan/sh` release asset or a pre-populated `~/.cache/pre-commit`.

## Versioning

Which `shfmt` do you have? Ask the binary — `shfmt --version` is always right. Before installing,
read `SHFMT_VERSION` in `setup.py` at that release's tag —
`https://github.com/MaxWinterstein/shfmt-py/blob/vX.Y.Z/setup.py`.

`shfmt-py` is independently versioned; the PyPI version does **not** mirror the bundled `shfmt`
version.

- **Major** — breaking change to `shfmt-py` itself (e.g. dropping a Python
  version, renaming the pre-commit hook id).
- **Minor** — new upstream `shfmt` release bundled.
- **Patch** — wrapper-only fix (hash regeneration, CI changes affecting users,
  etc.).

Releases `3.x.y.z` and earlier used a 4-segment scheme aligned with upstream `shfmt` — `3.13.0.3`
bundled `shfmt` 3.13.0. From `v4.0.0` onwards `shfmt-py` follows standard semver.

## FAQ

**The hook passes but nothing gets formatted.**

You set `args:` without `-w`. pre-commit replaces the default `args: [-w]` instead of extending it,
so re-add `-w` to your list.

**`shfmt: command not found` after `pip install`.**

The executable lands in the target environment's scripts directory. Activate that virtualenv, or
use `uv tool install shfmt-py` / `pipx install shfmt-py` to get it on your user `PATH`. If your OS
package manager also ships `shfmt`, `PATH` order decides which one runs — `shfmt --version` tells
you which one you got.

**It won't get updated via e.g. `Renovate Bot`.**

Releases `v4.0.0` and onwards use standard semver — no special Renovate config needed. For older
`3.x.y.z` releases you'll need `"versioning": "pep440"` (or see
[shfmt-py/update-via-renovate][renovate-example]). For the pre-commit hook, `pre-commit autoupdate`
works either way.

**I get something like `SSL: CERTIFICATE_VERIFY_FAILED` on macOS.**

This only happens on the from-source paths that download from GitHub at build time — which include
every pre-commit hook install — never when a wheel is used. Install certificates with e.g.
`"/Applications/Python 3.x/Install Certificates.command"` for the Python you are installing with.
See [this MerossIot comment][here1] or [this Stack Overflow answer][here2] for a solution.

## Issues

Formatting behavior, flags and feature requests belong upstream, at [mvdan/sh issues][sh-issues].
Packaging, wheels, platform coverage and the hook definition belong in
[this project's issue tracker][shfmt-py-issues].

## License

`shfmt-py` is MIT licensed; see [LICENSE]. The `shfmt` binary it ships or downloads is the work of
the [mvdan/sh][shfmt] project and is redistributed unmodified under its own
[BSD-3-Clause license][shfmt-license].

[shfmt]: https://github.com/mvdan/sh
[manual]: https://github.com/mvdan/sh/blob/master/cmd/shfmt/shfmt.1.scd
[sh-issues]: https://github.com/mvdan/sh/issues
[pre-commit]: https://pre-commit.com
[identify]: https://github.com/pre-commit/identify
[shellcheck-py]: https://github.com/shellcheck-py/shellcheck-py
[setup.py]: https://github.com/MaxWinterstein/shfmt-py/blob/master/setup.py
[shfmt-py-issues]: https://github.com/MaxWinterstein/shfmt-py/issues
[LICENSE]: https://github.com/MaxWinterstein/shfmt-py/blob/master/LICENSE
[shfmt-license]: https://github.com/mvdan/sh/blob/master/LICENSE
[renovate-example]: https://github.com/shfmt-py/update-via-renovate
[here1]: https://github.com/albertogeniola/MerossIot/issues/62#issuecomment-535769621
[here2]: https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error
