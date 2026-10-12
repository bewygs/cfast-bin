"""Minimal tests of the installed wheel"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import cfast_bin

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = Path(os.environ.get("CFAST_EXAMPLES", ROOT / "build" / "examples"))
# The venv's console script, not the bare binary
CFAST = shutil.which("cfast", path=str(Path(sys.executable).parent))


def cfast(cwd, input_file):
    return subprocess.run([CFAST, input_file], cwd=cwd, capture_output=True, text=True)


def run_example(tmp_path, name):
    shutil.copy(EXAMPLES / f"{name}.in", tmp_path)
    result = cfast(tmp_path, f"{name}.in")
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmp_path.glob(f"{name}_*.csv"))


def test_executable():
    assert Path(cfast_bin.executable()).is_file()
    assert cfast_bin.CFAST_BUILD


def test_users_guide_example(tmp_path):
    run_example(tmp_path, "Users_Guide_Example")


@pytest.mark.xfail(
    strict=False,
    reason="Beta-343 example rejected by the NIST binary itself (&OUTP on line 149)",
)
def test_large_building(tmp_path):
    run_example(tmp_path, "Large_Building")


def test_rejected_input(tmp_path):
    (tmp_path / "bad.in").write_text("&FOO /\n")
    assert cfast(tmp_path, "bad.in").returncode != 0


@pytest.mark.skipif(sys.platform != "linux", reason="Intel runtime on Linux only")
def test_intel_runtime_from_venv():
    ldd = subprocess.run(
        ["ldd", cfast_bin.executable()], capture_output=True, text=True, check=True
    ).stdout
    for name in ("libimf.so", "libintlc.so.5"):
        match = re.search(rf"{re.escape(name)} => (\S+)", ldd)
        assert match, ldd
        assert Path(match[1]).resolve() == Path(sys.prefix, "lib", name).resolve()
