# cfast-bin

[![PyPI](https://img.shields.io/pypi/v/cfast-bin)](https://pypi.org/project/cfast-bin/)
[![Build](https://github.com/bewygs/cfast-bin/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/bewygs/cfast-bin/actions/workflows/build.yml)

The [CFAST](https://github.com/firemodels/cfast) fire model, as a Python wheel.

`cfast-bin` is an **unofficial** repackaging of the NIST CFAST binaries. Each wheel ships the `cfast` executable that NIST built for that platform.

## Usage

```sh
pip install cfast-bin
cfast model.in
```

From Python:

```python
import subprocess
import cfast_bin

subprocess.run([cfast_bin.executable(), "model.in"], check=True)
print(cfast_bin.CFAST_BUILD)  # NIST build string, e.g. 8-Beta-343-gd3b43914c
```

## Platforms

| Platform | Requirement |
| --- | --- |
| Linux x86_64 | glibc ≥ 2.34 |
| macOS arm64 | macOS ≥ 26 |
| Windows x64 | — |

Requirements come from the NIST binaries and may change between CFAST versions.

## Versioning

Versions follow CFAST, so `8.0.0` contains the binaries of the CFAST 8.0.0 release and `8.0.0.post1` is a packaging-only fix of it. Nightly builds are versioned `8.0.0.dev<N>`, where `N` counts the CFAST commits since its `CFAST-8-Beta` tag.

## Licenses

- CFAST is NIST software, distributed under the [NIST notice](https://github.com/firemodels/cfast/blob/master/LICENSE.md). On Linux, the binary's RPATH is modified so that it finds the Intel runtime, and the wheel's `NOTICE` records this change.
- The Intel runtime on Linux is not bundled. It comes from the [`intel-cmplr-lib-rt`](https://pypi.org/project/intel-cmplr-lib-rt/) dependency.
- macOS wheels include the GCC runtime libraries (`libgfortran`, `libquadmath`, `libgcc_s`), under the GPLv3 with the GCC Runtime Library Exception.
- The code of this repository is under the MIT license.

## Development

```sh
uv run scripts/prepare.py --platform linux   # or macos, windows; --asset for a local bundle or URL
uv build --wheel
uv venv && uv pip install dist/*.whl pytest
.venv/bin/python -m pytest tests
```

`prepare.py` downloads the newest nightly bundle with `gh` and stages it into `src/cfast_bin/`. Extracting a macOS bundle outside macOS needs `7z`.
