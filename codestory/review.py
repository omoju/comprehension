"""One command: a change in, a change story out.

    .venv/bin/python codestory/review.py <repo> --pr N [options]
    .venv/bin/python codestory/review.py <repo> --base <rev> --head <rev> [options]

Options:
    --pkg DIR            the package inside the repo, "." for the root (default: the one the change touches that has
                         tests)
    --spec PATH          a spec, relative to the package, that exercises the change (repeatable; default: the test
                         files the change itself adds or edits)
    --reader NAME        who the story is for (default: reviewer; see codestory/readers/)
    --runner NAME        japa or vitest (default: japa for an AdonisJS package, else vitest)
    --link NAMES         what each worktree borrows from <repo>'s package, comma-separated (default: node_modules).
                         Anything else the tests need, such as a local .env, has to be named here.
    --max-chapters N     the length budget (default 8)
    --keep-worktrees     leave the base and head worktrees in place (by default they are removed at the end)
    --open               open the reading page

Stages, each resumable (rerun the same command to continue): diff.py traces the change's tests on the base and the
head → diff_outline.py plans → diff_chapter.py writes, checks (proofs on both sides) and repairs → render.py draws
the page at stories/<repo>-pr<N>/index.html. The model is chosen in .env: CODESTORY_PROVIDER and CODESTORY_MODEL
(see llm.py: an Anthropic key, your Claude or ChatGPT login through their CLIs, or Azure AI Foundry).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import env  # noqa: F401
import llm
from diff import git, release, under

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PY = sys.executable


def fail(msg: str) -> int:
    print(f"\n✗ {msg}")
    return 1


def step(label: str, argv: list[str]) -> bool:
    print(f"\n== {label}", flush=True)
    t0 = time.time()
    ok = subprocess.run([PY, *argv], cwd=ROOT).returncode == 0
    print(f"   {'done' if ok else 'FAILED'} in {time.time() - t0:.0f}s", flush=True)
    return ok


def pull_request(repo: Path, number: int) -> dict:
    """Base and head of a pull request, via the GitHub API (old gh versions have no SHA fields in `pr view`)."""
    remote = git(repo, "remote", "get-url", "origin").strip()
    slug = remote.split("github.com")[-1].lstrip(":/").removesuffix(".git")
    done = subprocess.run(["gh", "api", f"repos/{slug}/pulls/{number}", "--jq",
                           "{base: .base.sha, head: .head.sha, title: .title}"], capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"✗ gh api could not read pull request #{number}: {done.stderr.strip()}")
    pr = json.loads(done.stdout)
    for sha in (pr["base"], pr["head"]):
        if subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"]).returncode != 0:
            git(repo, "fetch", "-q", "origin", f"pull/{number}/head", pr["base"])
    pr["base"] = git(repo, "merge-base", pr["base"], pr["head"]).strip()  # what the branch actually forked from
    return pr


TEST_FILE = re.compile(r"\.(spec|test)\.[cm]?[jt]sx?$")


def guess_pkg(repo: Path, paths: list[str]) -> str | None:
    """The package the change touches: a top-level directory with a package.json (preferring one whose tests the
    change edits), else the repository root when it has one."""
    tops = sorted({p.split("/")[0] for p in paths if "/" in p and (repo / p.split("/")[0] / "package.json").exists()})
    with_tests = [t for t in tops if any(p.startswith(f"{t}/") and TEST_FILE.search(p) for p in paths)]
    if with_tests or tops:
        return (with_tests or tops)[0]
    return "." if (repo / "package.json").exists() else None


def changed_tests(repo: Path, head: str, pkg: str, paths: list[str]) -> list[str]:
    """The test files the change adds or edits in the package, relative to it, that still exist on the head."""
    prefix = under(pkg, "")
    return sorted(p[len(prefix):] for p in paths if p.startswith(prefix) and TEST_FILE.search(p)
                  and "node_modules/" not in p and git_has(repo, head, p))


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("repo")
    ap.add_argument("--pr", type=int), ap.add_argument("--base"), ap.add_argument("--head")
    ap.add_argument("--pkg"), ap.add_argument("--spec", action="append"), ap.add_argument("--reader", default="reviewer")
    ap.add_argument("--runner"), ap.add_argument("--link"), ap.add_argument("--max-chapters", default="8")
    ap.add_argument("--keep-worktrees", action="store_true"), ap.add_argument("--open", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    if a.help or not (a.pr or (a.base and a.head)):
        print(__doc__)
        return 2

    repo = Path(a.repo).resolve()
    if a.pr:
        pr = pull_request(repo, a.pr)
        base, head, title, name = pr["base"], pr["head"], pr["title"], f"{repo.name}-pr{a.pr}"
    else:
        base, head = git(repo, "rev-parse", a.base).strip(), git(repo, "rev-parse", a.head).strip()
        title, name = "", f"{repo.name}-{base[:7]}-{head[:7]}"
    paths = git(repo, "diff", "--name-only", base, head).splitlines()
    pkg = a.pkg or guess_pkg(repo, paths)
    if not pkg:
        return fail("the change touches no package with a package.json; name one with --pkg")
    specs = sorted(a.spec or changed_tests(repo, head, pkg, paths))
    if not specs:
        return fail(f"the change brings no test file in {pkg}: pass --spec with one that exercises it "
                    "(a change story needs a run to follow)")
    runner = a.runner or ("japa" if (repo / pkg / "adonisrc.ts").exists() else "vitest")
    link = a.link or "node_modules"

    story = ROOT / "stories" / name
    story.mkdir(parents=True, exist_ok=True)
    print(f"change:  {base[:7]} → {head[:7]}" + (f"  #{a.pr} {title}" if a.pr else ""))
    print(f"package: {pkg} ({runner}); specs: {', '.join(specs)}")
    print(f"story:   {story.relative_to(ROOT)}\nreader:  {a.reader}\nmodel:   {llm.describe()}")

    setup = None
    try:
        changes = story / "changes.json"
        same = changes.exists() and (json.loads(changes.read_text()).get("head"), json.loads(changes.read_text()).get("base")) == (head, base)
        if not (same and (story / "diff.json").exists()):
            argv = [str(HERE / "diff.py"), str(repo), base, head, str(story), "--pkg", pkg, "--runner", runner,
                    "--link", link] + [x for s in specs for x in ("--spec", s)]
            if not step("diff: run the change's tests on the base and the head, and compare", argv):
                return fail("the runs could not be traced; see the output above")
            for f in ("outline.json",):
                (story / f).unlink(missing_ok=True)  # a new change means a new plan
        else:
            print("\n== diff: already traced")
        setup = json.loads(changes.read_text())
        if title or a.pr:
            setup.update(title=title, number=a.pr)
            changes.write_text(json.dumps(setup, indent=1) + "\n")

        if not (story / "outline.json").exists():
            if not step("outline: plan the change story", [str(HERE / "diff_outline.py"), str(story), "--reader", a.reader,
                                                            "--max-chapters", a.max_chapters]):
                return fail("the plan failed its checks after repair; see outline.response*.json")
        else:
            print("\n== outline: already planned")
        if not step("chapters: write, check on both sides, repair", [str(HERE / "diff_chapter.py"), str(story)]):
            print("   some chapters still fail a check after repair; see report.md (the page is rendered anyway)")
        if not step("render: the reading page", [str(HERE / "render.py"), str(story)]):
            return fail("render failed")
    finally:
        if setup and not a.keep_worktrees:
            release(setup)

    page = story / "index.html"
    print(f"\n✓ {page.relative_to(ROOT)}\n  report: {(story / 'report.md').relative_to(ROOT)}")
    if a.open:
        webbrowser.open(page.as_uri())
    return 0


def git_has(repo: Path, rev: str, path: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{rev}:{path}"]).returncode == 0


if __name__ == "__main__":
    sys.exit(main())
