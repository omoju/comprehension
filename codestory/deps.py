"""A JavaScript package's dependencies, installed from its own lockfile, so its code and its tests can run.

    .venv/bin/python codestory/deps.py <package-dir>

The lockfile chooses the tool and pins every version, so nothing is resolved afresh: pnpm-lock.yaml → pnpm,
yarn.lock → yarn, package-lock.json → npm ci, and only without one, npm install. In a workspace the lockfile sits
at the repository root, and the install runs there, for every package at once. A package whose node_modules exists
is left alone. Standard library only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

LOCKFILES = (
    ("pnpm-lock.yaml", ["npx", "-y", "pnpm@10", "install", "--frozen-lockfile"]),
    ("yarn.lock", ["npx", "-y", "yarn@1", "install", "--frozen-lockfile"]),
    ("package-lock.json", ["npm", "ci"]),
)
TRACER_WEB = Path(__file__).resolve().parent / "ts" / "web"  # codestory's own Vitest


class InstallError(RuntimeError):
    pass


def lockfile(pkg: Path) -> tuple[Path, list[str]]:
    """Where to install and with what: the nearest lockfile at or above the package, up to the repository root."""
    for d in (pkg, *pkg.parents):
        for name, argv in LOCKFILES:
            if (d / name).exists():
                return d, argv
        if (d / ".git").exists():
            break
    return pkg, ["npm", "install"]


def run(argv: list[str], cwd: Path, log: Callable[[str], None]) -> None:
    log(f"installing dependencies in {cwd}: {' '.join(argv)}")
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise InstallError(f"{' '.join(argv)} failed in {cwd}:\n{(done.stderr or done.stdout).strip()[-2000:]}")


def install(path: Path | str, log: Callable[[str], None] = print) -> bool:
    """Install the package's dependencies if its node_modules is missing. True if an install ran."""
    pkg = Path(path).resolve()
    if (pkg / "node_modules").is_dir():
        return False
    where, argv = lockfile(pkg)
    run(argv, where, log)
    return True


def ensure_tracer(log: Callable[[str], None] = print) -> bool:
    """codestory's own Vitest (codestory/ts/web), which runs a package's specs without one of its own; once."""
    if (TRACER_WEB / "node_modules").is_dir():
        return False
    run(["npm", "install", "--legacy-peer-deps", "--no-audit", "--no-fund"], TRACER_WEB, log)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    try:
        print("installed" if install(sys.argv[1]) else "node_modules already there")
    except InstallError as e:
        print(e)
        sys.exit(1)
