# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Repackages NIST's prebuilt CFAST binaries as platform wheels; nothing is compiled. The repo holds only staging and packaging logic, and most of it lives in `scripts/prepare.py`.

## Commands

```sh
uv run scripts/prepare.py --platform linux   # macos | windows; --asset <file|URL> skips the gh download
uv build --wheel
uv venv && uv pip install dist/*.whl pytest  # the glob assumes dist/ holds a single wheel
.venv/bin/python -m pytest tests             # one test: tests/test_installed.py::test_executable
uvx pre-commit run --all-files               # ruff check --fix + ruff format, the CI lint job
```

`prepare.py` downloads through `gh`, which must be authenticated. Any platform can be staged from Linux: the macOS `.dmg` is extracted with `7z`, the Windows PyInstaller installer with `pyinstxtractor-ng`. It is a PEP 723 script (Python ≥ 3.12, own deps), so always run it with `uv run`; the package and tests target Python ≥ 3.9.

## Two-phase build

1. `prepare.py` stages one platform into gitignored paths: `src/cfast_bin/{bin,lib,LICENSES}/`, `src/cfast_bin/_version.py`, `.wheel-tag`, and `build/examples/` (test inputs). Each run replaces the previous one, so the tree holds exactly one platform at a time.
2. Hatchling reads the version from `_version.py` (`[tool.hatch.version]`), and `hatch_build.py` reads `.wheel-tag` for the `py3-none-<tag>` wheel tag. The `artifacts` list in `pyproject.toml` pulls the gitignored package files into the wheel; `license-files` puts the staged `LICENSES/` in `.dist-info/licenses/`. Without step 1 the build fails, and so does `import cfast_bin` (no `_version.py`).

The wheel tag is read from the binary, never hardcoded: Linux takes the highest `GLIBC_2.N` symbol (`manylinux_2_N_x86_64`), macOS the highest `LC_BUILD_VERSION` minos across the executable and its dylibs. The README's platform requirements follow from these.

## Per-platform packaging

- **Linux**: the Intel Fortran runtime comes from the `intel-cmplr-lib-rt` dependency, which installs into `<prefix>/lib`. `patchelf` sets the binary's RPATH to `$ORIGIN/../../../../../lib`: up to `<prefix>` from `<prefix>/{lib,lib64}/pythonX.Y/site-packages/cfast_bin/bin/`, then `lib` (Fedora and RHEL install platform wheels under `lib64` outside venvs). Changing the package depth breaks it. `LICENSES/NOTICE` records this modification of the NIST binary. `test_intel_runtime_from_venv` checks the resolution with `ldd`.
- **macOS**: the GCC runtime dylibs ship in `lib/`, with the GPL-3.0 and GCC exception texts copied from `licenses/`. The `license` expression in `pyproject.toml` must stay in step with what the wheels ship.
- **Windows**: the executable only.

## Versions and releases

- Nightlies come from the `CFAST_TEST` release of `firemodels/test_bundles`: asset `CFAST-<major>-Beta-<N>-g<sha>-<suffix>` becomes version `<major>.0.0.dev<N>`. CI rebuilds them weekly.
- Releases: the GitHub release tag is the package version (`8.0.0`, `8.0.0.post1`). `publish.yml` calls the reusable `build.yml`, which runs `prepare.py --repo firemodels/cfast --tag CFAST-<version without .postN> --version <version>` (the `nist-tag` input overrides the tag).
- Nightly macOS binaries require a macOS newer than the GitHub runners: CI lets those tests fail, and `publish.yml` drops the macOS wheel from nightly uploads.

## Tests

`tests/` exercises the installed wheel, the way CI does after a pip or uv install: the venv's `cfast` console script, run on the examples in `build/examples/` (or `$CFAST_EXAMPLES`). `test_large_building` is a non-strict xfail because the NIST binary itself rejects that example in Beta-343.
