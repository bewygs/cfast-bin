# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "patchelf; sys_platform != 'win32'",
#     "pyinstxtractor-ng; sys_platform != 'win32'",
# ]
# ///
"""Stage a NIST CFAST bundle into src/cfast_bin/ for `uv build --wheel`.

Takes the newest bundle of a GitHub release (the CFAST 8 nightlies by default),
or a local file or URL, then writes the binary, its libraries, the license
texts, the version file and the wheel tag.
"""

import argparse
import datetime
import json
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "cfast_bin"
SUFFIX = {"linux": "-linux.tar.gz", "macos": "-macos.dmg", "windows": "-windows.exe"}
BINARY = {"linux": "cfast8_linux", "macos": "cfast8_macos", "windows": "cfast.exe"}
EXAMPLES = ("Users_Guide_Example.in", "Large_Building.in")
# <prefix>/lib, where intel-cmplr-lib-rt installs, seen from
# <prefix>/{lib,lib64}/pythonX.Y/site-packages/cfast_bin/bin: Fedora and RHEL put
# platform wheels under lib64 outside venvs, but data files still go to lib
RPATH = "$ORIGIN/../../../../../lib"


def fetch(platform, asset, repo, tag, dest):
    if asset and not asset.startswith(("http://", "https://")):
        return Path(asset).resolve()
    if asset:
        path = dest / asset.rsplit("/", 1)[-1]
        urllib.request.urlretrieve(asset, path)
        return path
    release = [tag, "--repo", repo]
    view = ["gh", "release", "view", *release, "--json", "assets"]
    out = subprocess.run(view, check=True, capture_output=True, text=True).stdout
    assets = [
        a for a in json.loads(out)["assets"] if a["name"].endswith(SUFFIX[platform])
    ]
    if not assets:
        sys.exit(f"No *{SUFFIX[platform]} asset in release {tag} of {repo}")
    name = max(assets, key=lambda a: a["createdAt"])["name"]
    print(f"Downloading {name}")
    download = ["gh", "release", "download", *release, "--pattern", name, "--dir", dest]
    subprocess.run(download, check=True)
    return dest / name


def bundle_dir(path, platform):
    return next(path.glob(f"**/bin/{BINARY[platform]}")).parent.parent


def extract(platform, asset, tmp):
    """Unpack the parts of the bundle we need and return the directory holding bin/."""
    out = tmp / "bundle"
    if platform == "linux":
        wanted = re.compile(r"/CFAST8/(bin/cfast8_linux$|Examples/)")
        with tarfile.open(asset) as tar:
            members = [m for m in tar if wanted.search(m.name)]
            tar.extractall(out, members, filter="data")
    elif platform == "macos" and sys.platform == "darwin":
        mnt = tmp / "dmg"
        subprocess.run(
            ["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", mnt, asset],
            check=True,
        )
        try:
            src = bundle_dir(mnt, platform)
            for name in ("bin", "lib", "Examples"):
                shutil.copytree(src / name, out / name, symlinks=True)
        finally:
            subprocess.run(["hdiutil", "detach", mnt], check=True)
    elif platform == "macos":
        dirs = [f"*/CFAST8/{name}" for name in ("bin", "lib", "Examples")]
        subprocess.run(
            ["7z", "x", "-y", f"-o{out}", asset, *dirs],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    elif sys.platform == "win32":
        subprocess.run(
            [asset, "--silent", "--overwrite", "--install-dir", out], check=True
        )
    else:
        subprocess.run(
            ["pyinstxtractor-ng", asset], cwd=tmp, check=True, stdout=subprocess.DEVNULL
        )
        with zipfile.ZipFile(next(tmp.glob("*_extracted/payload.zip"))) as payload:
            payload.extractall(
                out,
                [n for n in payload.namelist() if n.startswith(("bin/", "Examples/"))],
            )
    return bundle_dir(out, platform)


def stage(platform, bundle, asset_name):
    for name in ("bin", "lib", "LICENSES"):
        shutil.rmtree(PKG / name, ignore_errors=True)
    exe = PKG / "bin" / ("cfast.exe" if platform == "windows" else "cfast")
    exe.parent.mkdir()
    shutil.copy2(bundle / "bin" / BINARY[platform], exe)
    exe.chmod(0o755)

    licenses = PKG / "LICENSES"
    licenses.mkdir()
    shutil.copy2(ROOT / "licenses" / "CFAST-LICENSE.md", licenses)
    if platform == "linux":
        subprocess.run(
            ["patchelf", "--force-rpath", "--set-rpath", RPATH, exe], check=True
        )
        (licenses / "NOTICE").write_text(
            f"cfast_bin/bin/cfast is the {BINARY[platform]} executable of the NIST CFAST bundle\n"
            f"{asset_name}, modified by the cfast-bin build on {datetime.date.today()}:\n"
            f"its RPATH was set to {RPATH} so that it loads the Intel runtime\n"
            "installed by the intel-cmplr-lib-rt package. Nothing else was changed.\n"
        )
    if platform == "macos":
        (PKG / "lib").mkdir()
        for dylib in (bundle / "lib").glob("*.dylib"):
            shutil.copy2(dylib, PKG / "lib")
        for name in ("GPL-3.0.txt", "GCC-exception-3.1.txt"):
            shutil.copy2(ROOT / "licenses" / name, licenses)

    examples = ROOT / "build" / "examples"
    shutil.rmtree(examples, ignore_errors=True)
    examples.mkdir(parents=True)
    for name in EXAMPLES:
        shutil.copy2(bundle / "Examples" / name, examples)
    return exe


def macos_minos(path):
    data = path.read_bytes()
    start = 0
    if data[:4] == b"\xca\xfe\xba\xbe":  # universal binary: read its arm64 slice
        slices = [
            struct.unpack_from(">iiI", data, 8 + 20 * i)
            for i in range(struct.unpack_from(">I", data, 4)[0])
        ]
        start = next(offset for cputype, _, offset in slices if cputype == 0x0100000C)
    magic, ncmds = struct.unpack_from("<I12xI", data, start)
    if magic != 0xFEEDFACF:
        sys.exit(f"{path} is not a 64-bit Mach-O file")
    offset = start + 32
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, offset)
        if cmd == 0x32:  # LC_BUILD_VERSION
            return struct.unpack_from("<I", data, offset + 12)[0] >> 16
        offset += size
    sys.exit(f"No LC_BUILD_VERSION in {path}")


def wheel_tag(platform, exe):
    if platform == "linux":
        glibc = max(int(v) for v in re.findall(rb"GLIBC_2\.(\d+)", exe.read_bytes()))
        return f"manylinux_2_{glibc}_x86_64"
    if platform == "macos":
        minos = max(macos_minos(p) for p in [exe, *(PKG / "lib").glob("*.dylib")])
        return f"macosx_{minos}_0_arm64"
    return "win_amd64"


def versions(asset_name, platform, version):
    build = asset_name.removeprefix("CFAST-").removesuffix(SUFFIX[platform])
    if version is None:
        match = re.fullmatch(r"(\d+)-Beta-(\d+)-g[0-9a-f]+", build)
        if not match:
            sys.exit(f"Cannot derive a version from {asset_name}: pass --version")
        version = f"{match[1]}.0.0.dev{match[2]}"
    return version, build


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--platform", required=True, choices=SUFFIX)
    parser.add_argument(
        "--asset",
        help="local bundle or URL, instead of the newest asset of the release",
    )
    parser.add_argument("--repo", default="firemodels/test_bundles")
    parser.add_argument("--tag", default="CFAST_TEST", help="release tag")
    parser.add_argument(
        "--version", help="package version (derived from the asset name for nightlies)"
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        asset = fetch(args.platform, args.asset, args.repo, args.tag, tmp)
        version, build = versions(asset.name, args.platform, args.version)
        exe = stage(args.platform, extract(args.platform, asset, tmp), asset.name)
    tag = wheel_tag(args.platform, exe)
    (PKG / "_version.py").write_text(
        f'__version__ = "{version}"\nCFAST_BUILD = "{build}"\n'
    )
    (ROOT / ".wheel-tag").write_text(f"{tag}\n")
    print(f"cfast-bin {version} ({build}): {tag}")


if __name__ == "__main__":
    main()
