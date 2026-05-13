[![PyPI version](https://img.shields.io/pypi/v/shfmt-py.svg)](https://pypi.org/project/shfmt-py)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/shfmt-py.svg)](https://pypi.org/project/shfmt-py)
[![Downloads](https://img.shields.io/pypi/dm/shfmt-py.svg)](https://pypi.org/project/shfmt-py)
[![License](https://img.shields.io/github/license/MaxWinterstein/shfmt-py.svg)](https://github.com/MaxWinterstein/shfmt-py/blob/master/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/MaxWinterstein/shfmt-py/master.svg)](https://results.pre-commit.ci/latest/github/MaxWinterstein/shfmt-py/master)

# shfmt-py

Python-installable wrapper for [shfmt], the shell script formatter.

Internally this package downloads the pre-built `shfmt` binary for your platform at install time.

Modeled after [shellcheck-py], adapted for `shfmt`.

## Installation

```bash
pip install shfmt-py
```

## Usage

### CLI

After installation, the `shfmt` binary is available on your `PATH` (or `shfmt.exe` on Windows).

### As pre-commit hook

See [pre-commit] for instructions.

Sample `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/maxwinterstein/shfmt-py
  rev: v3.13.0.3
  hooks:
    - id: shfmt
```

## Versioning

`shfmt-py` is independently versioned. The PyPI version does **not** directly
mirror the bundled `shfmt` version — check each GitHub release's notes for the
exact `shfmt` version that release bundles.

- **Major** — breaking change to `shfmt-py` itself (e.g. dropping a Python
  version, renaming the pre-commit hook id).
- **Minor** — new upstream `shfmt` release bundled.
- **Patch** — wrapper-only fix (hash regeneration, CI changes affecting users,
  etc.).

Releases `3.x.y.z` and earlier used a 4-segment scheme aligned with upstream
`shfmt`. From `v4.0.0` onwards `shfmt-py` follows standard semver.

## FAQ

Q: It won't get updated via e.g. `Renovate Bot`

A: Releases `v4.0.0` and onwards use standard semver — no special Renovate
config needed. For older `3.x.y.z` releases you'll need
`"versioning": "pep440"` (or see https://github.com/shfmt-py/update-via-renovate).

Q: I get something like `SSL: CERTIFICATE_VERIFY_FAILED` on macOS

A: Install certificates with e.g.: `"/Applications/Python 3.9/Install Certificates.command"`. See [here][here1] or [here][here2] for a solution.


[shfmt]: https://github.com/mvdan/sh
[pre-commit]: https://pre-commit.com
[shellcheck-py]: https://github.com/shellcheck-py/shellcheck-py
[here1]: https://github.com/albertogeniola/MerossIot/issues/62#issuecomment-535769621
[here2]: https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error
