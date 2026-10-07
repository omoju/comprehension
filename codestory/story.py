"""One command: a repository in, a CodeStory out.

    .venv/bin/python codestory/story.py <github-url | local path> [--reader owner|maintainer|user] [--open]

Clones the repository into demo-repos/<name> (a URL) or uses the directory you name, then runs the pipeline:
scenario (find and trace the intended use) → outline (plan the chapters) → chapters (write, check, repair) →
render (the three-pane reading page). The story goes to stories/<name>/ and the page to stories/<name>/index.html.
Needs: Python 3.13, uv, ANTHROPIC_API_KEY in .env. Optional: Cloudflare keys for the contradiction judge.
Python repositories only; the intended use must run without network access or credentials.
A story costs roughly $2–6 in model calls and takes 10–25 minutes. Each stage is resumable: rerun to continue.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import env  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
HERE = Path(__file__).resolve().parent


def fail(msg: str) -> int:
    print(f"\n✗ {msg}")
    return 1


def obtain(target: str) -> Path | None:
    """A local directory, or a GitHub URL cloned into demo-repos/<name>."""
    p = Path(target)
    if p.is_dir():
        return p.resolve()
    m = re.match(r"^(?:https?://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", target)
    if not m:
        return None
    name = m.group(2)
    dest = ROOT / "demo-repos" / name
    if not (dest / ".git").is_dir():
        print(f"cloning {m.group(1)}/{name} → demo-repos/{name}")
        subprocess.run(["git", "clone", "-q", f"https://github.com/{m.group(1)}/{name}.git", str(dest)], check=True)
    return dest


def step(label: str, argv: list[str]) -> bool:
    print(f"\n== {label}", flush=True)
    t0 = time.time()
    ok = subprocess.run([PY, *argv], cwd=ROOT).returncode == 0
    print(f"   {'done' if ok else 'FAILED'} in {time.time() - t0:.0f}s", flush=True)
    return ok


def main(argv: list[str]) -> int:
    opt = lambda f, d: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    reader = opt("--reader", "owner")
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (argv[i - 1:i] or [""])[0] != "--reader"]
    if len(args) != 1:
        print(__doc__)
        return 2
    if not shutil.which("uv"):
        return fail("uv is not on the PATH (https://docs.astral.sh/uv/); it builds the repository's environment")
    if not (ROOT / ".env").exists():
        return fail("no .env at the project root: copy .env.example and set ANTHROPIC_API_KEY")
    repo = obtain(args[0])
    if repo is None:
        return fail(f"{args[0]!r} is neither a directory nor a GitHub URL")
    if not any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")):
        return fail("only Python repositories are supported so far (no pyproject.toml / setup.py found)")
    if not (HERE / "readers" / f"{reader}.md").exists():
        return fail(f"no reader profile {reader!r}; see codestory/readers/")

    story = ROOT / "stories" / repo.name
    story.mkdir(parents=True, exist_ok=True)
    rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)  # noqa: E731
    print(f"repository: {rel(repo)}\nstory:      {rel(story)}\nreader:     {reader}")

    if not (story / "trace.txt").exists():
        if not step("scenario: find the intended use and trace one run", [str(HERE / "scenario.py"), str(repo), str(story)]):
            return fail("no working scenario; see stories/<name>/traces/ for the attempts")
    else:
        print("\n== scenario: already traced")
    if not (story / "outline.json").exists():
        if not step("outline: plan the chapters", [str(HERE / "outline.py"), str(repo), str(story), "--reader", reader]):
            return fail("the plan failed its checks after repair; see stories/<name>/outline.response*.json")
    else:
        print("\n== outline: already planned")
    if not step("chapters: write, check, repair", [str(HERE / "chapter.py"), str(story)]):
        print("   some chapters still fail a check after repair; see stories/<name>/report.md (the page is rendered anyway)")
    if not step("render: the reading page", [str(HERE / "render.py"), str(story)]):
        return fail("render failed")

    page = story / "index.html"
    print(f"\n✓ {rel(page)}\n  report: {rel(story / 'report.md')}")
    if "--open" in argv:
        webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
