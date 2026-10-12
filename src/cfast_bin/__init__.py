"""NIST CFAST binaries, unofficially repackaged as Python wheels."""

import os
import subprocess
import sys
from pathlib import Path

from ._version import CFAST_BUILD, __version__

__all__ = ["CFAST_BUILD", "__version__", "executable", "main"]


def executable() -> str:
    """Return the absolute path of the bundled CFAST executable."""
    name = "cfast.exe" if sys.platform == "win32" else "cfast"
    return str(Path(__file__).resolve().parent / "bin" / name)


def main() -> None:
    args = [executable(), *sys.argv[1:]]
    if sys.platform == "win32":
        sys.exit(subprocess.call(args))
    os.execv(args[0], args)
