"""The local checkout a story runs in, and getting it ready for a pull request.

A repository you registered (config.json `repos`, e.g. your own working copy) is used as it is: the app fetches the
pull request's commits into it and touches nothing else. Any other repository is cloned under ~/.codestory/repos and
its dependencies are installed from its own lockfile (npm, pnpm or yarn), since a story runs the change's tests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

import state
from github import GitHub, GitHubError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import deps  # noqa: E402

def checkout_for(owner: str, name: str) -> dict:
    """{path, managed, link, pkg, runner}: a registered checkout, or the one this app manages."""
    reg = state.config()["repos"].get(f"{owner}/{name}")
    if reg:
        return {"managed": False, "link": reg.get("link") or "", "pkg": reg.get("pkg") or "",
                "runner": reg.get("runner") or "", "path": str(Path(reg["path"]).expanduser())}
    return {"managed": True, "link": "", "pkg": "", "runner": "", "path": str(state.REPOS / owner / name)}


def register(owner: str, name: str, path: str, link: str = "", pkg: str = "", runner: str = "") -> dict:
    p = Path(path).expanduser().resolve()
    if not (p / ".git").exists():
        raise GitHubError(f"{p} is not a git checkout")
    cfg = state.config()
    cfg["repos"][f"{owner}/{name}"] = {"path": str(p), "link": link, "pkg": pkg, "runner": runner}
    state.save_config(cfg)
    return checkout_for(owner, name)


def forget(owner: str, name: str) -> None:
    cfg = state.config()
    cfg["repos"].pop(f"{owner}/{name}", None)
    state.save_config(cfg)


def run(argv: list[str], log: Callable[[str], None], cwd: Path | None = None, env: dict | None = None,
        timeout: int = 1800) -> None:
    shown, i = [], 0
    while i < len(argv):  # the -c credential settings are plumbing: leave them out of the log
        if argv[i] == "-c":
            i += 2
            continue
        shown.append(argv[i] if " " not in argv[i] else repr(argv[i]))
        i += 1
    log("$ " + " ".join(shown))
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        log(line.rstrip())
    if proc.wait(timeout=timeout) != 0:
        raise GitHubError(f"{Path(argv[0]).name} {argv[1] if len(argv) > 1 else ''} failed (exit {proc.returncode})")


def has_commit(path: Path, sha: str) -> bool:
    return subprocess.run(["git", "-C", str(path), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def prepare(gh: GitHub, pr: dict, log: Callable[[str], None]) -> dict:
    """Make the checkout hold the pull request's base and head, with dependencies when the app manages it."""
    repo = checkout_for(pr["owner"], pr["name"])
    path = Path(repo["path"])
    git = ["git", *gh.git_args()]
    if not (path / ".git").exists():
        if not repo["managed"]:
            raise GitHubError(f"the registered checkout {path} is gone")
        path.parent.mkdir(parents=True, exist_ok=True)
        log(f"cloning {pr['owner']}/{pr['name']} into {path}")
        run([*git, "clone", "-q", f"https://github.com/{pr['owner']}/{pr['name']}.git", str(path)], log,
            env=gh.git_env())
    missing = [s for s in (pr["base"]["sha"], pr["head"]["sha"]) if not has_commit(path, s)]
    if missing:
        log(f"fetching the pull request's commits ({', '.join(s[:7] for s in missing)})")
        run([*git, "-C", str(path), "fetch", "-q", "origin", f"pull/{pr['number']}/head", pr["base"]["sha"]], log,
            env=gh.git_env())
    if repo["managed"]:
        run(["git", "-C", str(path), "checkout", "-q", "--detach", pr["head"]["sha"]], log)
        install(path, log)
    ensure_vitest(log)
    return repo


def prepare_repo(gh: GitHub, owner: str, name: str, log: Callable[[str], None]) -> dict:
    """A checkout of a repository's default branch, for a story of the whole repository. A registered checkout is
    used as it stands; a managed clone is fetched and moved to the default branch's head."""
    repo = checkout_for(owner, name)
    path = Path(repo["path"])
    git = ["git", *gh.git_args()]
    if not (path / ".git").exists():
        if not repo["managed"]:
            raise GitHubError(f"the registered checkout {path} is gone")
        path.parent.mkdir(parents=True, exist_ok=True)
        log(f"cloning {owner}/{name} into {path}")
        run([*git, "clone", "-q", f"https://github.com/{owner}/{name}.git", str(path)], log, env=gh.git_env())
    if repo["managed"]:
        run([*git, "-C", str(path), "fetch", "-q", "origin"], log, env=gh.git_env())
        run(["git", "-C", str(path), "remote", "set-head", "origin", "--auto"], log, env=gh.git_env())
        run(["git", "-C", str(path), "checkout", "-q", "--detach", "origin/HEAD"], log)
        install(path, log)
    ensure_vitest(log)
    return repo


def install(path: Path, log: Callable[[str], None]) -> None:
    """A managed clone's dependencies (deps.py): the package at the root, and each top-level package beside it."""
    for d in [path, *sorted(p for p in path.iterdir() if p.is_dir() and (p / "package.json").exists())]:
        if (d / "package.json").exists():
            deps.install(d, log)


def ensure_vitest(log: Callable[[str], None]) -> None:
    deps.ensure_tracer(log)  # codestory brings its own Vitest (codestory/ts/web)
