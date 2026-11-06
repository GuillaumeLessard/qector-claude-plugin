#!/usr/bin/env python3
"""Build an offline wheelhouse for air-gapped QECTOR installs.

Run this on a connected build host, then carry the resulting directory
(wheels + ``SHA256SUMS`` + ``WHEELHOUSE.json``) to the lab machine and run
``scripts/install_offline.sh`` (POSIX) or ``scripts/install_offline.ps1``
(Windows). Nothing in the wheelhouse is executed on the build host.

Examples:
    # wheels for this interpreter / platform
    python scripts/build_wheelhouse.py --out wheelhouse

    # cross-download for a Windows lab box running CPython 3.12
    python scripts/build_wheelhouse.py --out wheelhouse-win --platform win_amd64 --python-version 3.12

    # verify a wheelhouse you received
    python scripts/build_wheelhouse.py --verify wheelhouse

The dependency set is ``requirements.lock`` (exact versions) so two build
hosts produce the same files; ``SHA256SUMS`` is what the lab verifies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sums(out: Path) -> dict[str, str]:
    sums = {p.name: _sha256(p) for p in sorted(out.iterdir()) if p.suffix in {".whl", ".gz", ".zip"}}
    (out / "SHA256SUMS").write_text("".join(f"{d}  {n}\n" for n, d in sums.items()), encoding="ascii")
    return sums


def build(out: Path, *, platform_tag: str | None, python_version: str | None, extra_index: str | None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "--dest", str(out), "--requirement", str(LOCK)]
    if platform_tag or python_version:
        cmd += ["--only-binary=:all:"]
        if platform_tag:
            cmd += ["--platform", platform_tag]
        if python_version:
            cmd += ["--python-version", python_version, "--implementation", "cp"]
    if extra_index:
        cmd += ["--extra-index-url", extra_index]
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        return result.returncode
    sums = _write_sums(out)
    manifest = {
        "built_at_unix": int(time.time()),
        "build_host": {"python": platform.python_version(), "platform": platform.platform()},
        "target": {"platform": platform_tag or "build host", "python_version": python_version or platform.python_version()[:4]},
        "requirements_lock_sha256": _sha256(LOCK),
        "files": sums,
    }
    (out / "WHEELHOUSE.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wheelhouse ready: {len(sums)} files in {out}")
    return 0


def verify(out: Path) -> int:
    sums_file = out / "SHA256SUMS"
    if not sums_file.is_file():
        print("SHA256SUMS missing")
        return 1
    failures = 0
    for line in sums_file.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        path = out / name.strip()
        if not path.is_file():
            print(f"MISSING  {name}")
            failures += 1
        elif _sha256(path) != digest:
            print(f"MISMATCH {name}")
            failures += 1
        else:
            print(f"OK       {name}")
    print("wheelhouse verification:", "PASS" if not failures else f"{failures} failure(s)")
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "wheelhouse")
    parser.add_argument("--platform", dest="platform_tag", default=None, help="pip platform tag, e.g. win_amd64, macosx_14_0_arm64, manylinux_2_28_x86_64")
    parser.add_argument("--python-version", default=None, help="Target CPython minor version, e.g. 3.12")
    parser.add_argument("--extra-index-url", default=None)
    parser.add_argument("--verify", type=Path, default=None, help="Verify an existing wheelhouse against its SHA256SUMS and exit.")
    args = parser.parse_args(argv)
    if args.verify:
        return verify(args.verify.resolve())
    return build(args.out.resolve(), platform_tag=args.platform_tag, python_version=args.python_version, extra_index=args.extra_index_url)


if __name__ == "__main__":
    raise SystemExit(main())
