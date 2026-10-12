# cfast-bin

The [CFAST](https://github.com/firemodels/cfast) fire model, as a Python wheel.

`cfast-bin` is an **unofficial** repackaging of the binaries built and published by NIST. Nothing is recompiled: each wheel contains the `cfast` executable taken from the NIST bundle for its platform.

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
| macOS arm64 | Release versions only |
| Windows x64 | — |

Requirements come from the NIST binaries and may change between CFAST versions. Nightly versions have no macOS wheel: the NIST nightly binary requires macOS 28, which is not released yet.

## Versioning

The version follows CFAST: `8.0.0` contains the binaries of the CFAST 8.0.0 release, and `8.0.0.post1` a packaging-only fix of it. Nightly builds are versioned `8.0.0.dev<N>`, where `N` is the NIST Beta number.

## Licenses

- CFAST is NIST software, distributed under the [NIST notice](https://github.com/firemodels/cfast/blob/master/LICENSE.md). On Linux, the binary's RPATH is modified so that it finds the Intel runtime; the wheel's `NOTICE` records this change.
- The Intel runtime on Linux is not included: it is installed from [`intel-cmplr-lib-rt`](https://pypi.org/project/intel-cmplr-lib-rt/).
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
