"""One command: a repository in, a CodeStory out.

    .venv/bin/python codestory/story.py <github-url | local path> [--reader owner|maintainer|user] [--out DIR]
                                        [--pkg DIR] [--open]

Clones the repository into demo-repos/<name> (a URL) or uses the directory you name, then runs the pipeline:
scenario (find and trace the intended use) → outline (plan the chapters) → chapters (write, check, repair) →
render (the three-pane reading page). The story goes to --out (default stories/<name>/), the page to index.html there.
A Python package (pyproject.toml / setup.py) runs as a script under trace.py. A TypeScript or JavaScript package
(package.json at the root, or in the --pkg directory of a monorepo) runs as one spec file under the TypeScript tracer
(scenario_ts.py: Vitest, or Japa for AdonisJS), its dependencies installed from its lockfile if node_modules is
missing, and its chapters prove themselves with spec files too.
Needs: Python 3.13, a model sign-in (llm.py, .env), uv for Python and Node 20.6+ for TypeScript. Optional: Cloudflare
keys for the contradiction judge. The intended use must run without network access or credentials.
A story costs roughly $2–6 in model calls and takes 10–25 minutes. Each stage is resumable: rerun to continue.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import env  # noqa: F401
import deps

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


def language(repo: Path, pkg: str | None) -> str | None:
    """"python" or "ts": how the story runs the code. --pkg names a JavaScript package inside a monorepo."""
    if pkg is None and any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")):
        return "python"
    return "ts" if (repo / (pkg or ".") / "package.json").exists() else None


def record_package(story: Path) -> None:
    """The outline carries the package and test runner the scenario ran in, so the chapters' proofs run there too."""
    setup = json.loads((story / "scenario.json").read_text())
    outline = json.loads((story / "outline.json").read_text())
    want = {"pkg": setup["pkg"], "runner": setup["runner"]}
    if any(outline["repo"].get(k) != v for k, v in want.items()):
        outline["repo"].update(want)
        (story / "outline.json").write_text(json.dumps(outline, indent=2) + "\n")


def main(argv: list[str]) -> int:
    opt = lambda f, d: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    reader, out, pkg = opt("--reader", "owner"), opt("--out", None), opt("--pkg", None)
    valued = {"--reader", "--out", "--pkg"}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (argv[i - 1:i] or [""])[0] not in valued]
    if len(args) != 1:
        print(__doc__)
        return 2
    if not (ROOT / ".env").exists():
        return fail("no .env at the project root: copy .env.example and set ANTHROPIC_API_KEY")
    repo = obtain(args[0])
    if repo is None:
        return fail(f"{args[0]!r} is neither a directory nor a GitHub URL")
    kind = language(repo, pkg)
    if kind is None:
        return fail(f"no package to run: neither a Python one (pyproject.toml / setup.py) nor a JavaScript or "
                    f"TypeScript one (package.json in {pkg or 'the root'})")
    if kind == "python" and not shutil.which("uv"):
        return fail("uv is not on the PATH (https://docs.astral.sh/uv/); it builds the repository's environment")
    if kind == "ts" and not shutil.which("node"):
        return fail("node is not on the PATH (Node 20.6 or later); it runs the TypeScript tracer")
    if not (HERE / "readers" / f"{reader}.md").exists():
        return fail(f"no reader profile {reader!r}; see codestory/readers/")

    story = Path(out).resolve() if out else ROOT / "stories" / repo.name
    story.mkdir(parents=True, exist_ok=True)
    rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)  # noqa: E731
    print(f"repository: {rel(repo)}" + (f" (package {pkg})" if pkg else "")
          + f"\nstory:      {rel(story)}\nreader:     {reader}")

    scenario = [str(HERE / "scenario.py"), str(repo), str(story)]
    if kind == "ts":
        scenario = [str(HERE / "scenario_ts.py"), str(repo), str(story), *(["--pkg", pkg] if pkg else [])]
        try:
            deps.install(repo / (pkg or "."), log=lambda m: print(f"   {m}", flush=True))
            deps.ensure_tracer(log=lambda m: print(f"   {m}", flush=True))
        except deps.InstallError as e:
            return fail(str(e))
    if not (story / "trace.txt").exists():
        if not step("scenario: find the intended use and trace one run", scenario):
            return fail(f"no working scenario; see {rel(story / 'traces')}/ for the attempts")
    else:
        print("\n== scenario: already traced")
    if not (story / "outline.json").exists():
        if not step("outline: plan the chapters", [str(HERE / "outline.py"), str(repo), str(story), "--reader", reader]):
            return fail(f"the plan failed its checks after repair; see {rel(story)}/outline.response*.json")
    else:
        print("\n== outline: already planned")
    if kind == "ts":
        record_package(story)
    if not step("chapters: write, check, repair", [str(HERE / "chapter.py"), str(story)]):
        print(f"   some chapters still fail a check after repair; see {rel(story / 'report.md')} (the page is rendered "
              "anyway)")
    if not step("render: the reading page", [str(HERE / "render.py"), str(story)]):
        return fail("render failed")

    page = story / "index.html"
    print(f"\n✓ {rel(page)}\n  report: {rel(story / 'report.md')}")
    if "--open" in argv:
        webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
