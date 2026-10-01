"""Check a code story against the code it tells.

    python3 codestory/verify.py stories/itsdangerous

Three checks, per chapter:
  1. citations  - every permalink into the repo points at lines that exist at the pinned commit
  2. drift      - the cited lines are unchanged in the repo's working tree (the code moved on; the story didn't)
  3. proofs     - every proof (proofs/NN.py or .sh, or an inline ```python proof block) runs and passes

Exit code 0 only if everything passes. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROOF_RE = re.compile(r"```(python|sh) proof\n(.*?)```", re.DOTALL)
PROOF_EXT = {"python": "py", "sh": "sh"}
# A heading or rule that only introduces the proof goes with it when the proof moves out.
PROOF_LEAD_IN = re.compile(r"(\n(-{3,}|#+ [^\n]*proof[^\n]*|[^\n]*runs against the real repository[^\n]*)\s*)+$", re.I)


def split_proofs(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Separate a chapter's story from its proofs: (story text, [(language, code), ...])."""
    proofs = PROOF_RE.findall(text)
    story = text
    for m in reversed(list(PROOF_RE.finditer(text))):
        before = PROOF_LEAD_IN.sub("", story[: m.start()].rstrip())
        story = before + story[m.end():]
    return story.rstrip() + "\n", proofs


def proof_files(chapter: Path) -> list[Path]:
    """proofs/01.py (and 01-2.py, ...) belong to 01-*.md."""
    return sorted((chapter.parent / "proofs").glob(f"{chapter.name[:2]}*.*"))


def write_proofs(chapter: Path, proofs: list[tuple[str, str]]) -> None:
    folder = chapter.parent / "proofs"
    folder.mkdir(exist_ok=True)
    for old in proof_files(chapter):
        old.unlink()
    for i, (lang, code) in enumerate(proofs, 1):
        suffix = "" if i == 1 else f"-{i}"
        (folder / f"{chapter.name[:2]}{suffix}.{PROOF_EXT[lang]}").write_text(code)


def read_proofs(chapter: Path) -> list[tuple[str, str]]:
    ext_lang = {v: k for k, v in PROOF_EXT.items()}
    return [(ext_lang[f.suffix[1:]], f.read_text()) for f in proof_files(chapter)]
RUNNERS = {"python": [sys.executable, "-c"], "sh": ["bash", "-c"]}

# Assertions that cannot fail. A proof full of these passes whatever the story says.
VACUOUS = re.compile(r"\bor\s+True\b|\bassert\s+(True|1)\b|\bassert\s+([\w.\[\]'\"]+)\s*==\s*\2\s*($|#)", re.M)


@dataclass
class Citation:
    commit: str
    path: str
    start: int
    end: int
    line: int  # line in the chapter file, for error messages

    def __str__(self) -> str:
        span = f"{self.start}" if self.start == self.end else f"{self.start}-{self.end}"
        return f"{self.path}:{span}"


@dataclass
class Report:
    chapter: str
    citations: int = 0
    proofs: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def repo_python(repo: Path) -> str:
    """The repo's own environment (created once, repo installed editable), so its dependencies are there."""
    venv = repo / ".codestory-venv"  # untracked, so invisible to git ls-files
    python = venv / "bin" / "python"
    if not python.exists():
        subprocess.run(["uv", "venv", "-q", "--python", "3.13", str(venv)], check=True)
        subprocess.run(["uv", "pip", "install", "-q", "--python", str(python), "-e", str(repo)], check=True)
    return str(python)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def find_citations(text: str, repo_url: str) -> list[Citation]:
    link_re = re.compile(
        re.escape(repo_url) + r"/blob/([0-9a-f]{7,40})/([^\s#)]+)#L(\d+)(?:-L(\d+))?"
    )
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in link_re.finditer(line):
            start = int(m.group(3))
            end = int(m.group(4) or start)
            found.append(Citation(m.group(1), m.group(2), start, end, lineno))
    return found


def repo_path(outline: dict) -> Path:
    return (ROOT / outline["repo"]["local_path"]).resolve()  # absolute paths survive the join


def check_chapter(chapter: Path, outline: dict, repo: Path, file_cache: dict) -> Report:
    text = chapter.read_text()
    proofs = PROOF_RE.findall(text) + read_proofs(chapter)  # inline (older chapters) or in proofs/
    return check_text(text, chapter.name, outline, repo, file_cache, proofs)


def check_text(text: str, name: str, outline: dict, repo: Path, file_cache: dict,
               proofs: list[tuple[str, str]] | None = None) -> Report:
    report = Report(name)
    pinned = outline["repo"]["commit"]

    for c in find_citations(text, outline["repo"]["url"]):
        report.citations += 1
        where = f"line {c.line}: {c}"
        if not pinned.startswith(c.commit) and not c.commit.startswith(pinned):
            report.errors.append(f"{where} cites commit {c.commit[:7]}, story is pinned to {pinned[:7]}")
            continue
        if c.path not in file_cache:
            try:
                then = git(repo, "show", f"{pinned}:{c.path}").splitlines()
            except subprocess.CalledProcessError:
                then = None
            now_file = repo / c.path
            now = now_file.read_text().splitlines() if now_file.exists() else None
            file_cache[c.path] = (then, now)
        then, now = file_cache[c.path]
        if then is None:
            report.errors.append(f"{where} file does not exist at {pinned[:7]}")
            continue
        if not (1 <= c.start <= c.end <= len(then)):
            report.errors.append(f"{where} is outside the file ({len(then)} lines)")
            continue
        if now is None:
            report.errors.append(f"{where} file has been deleted since the story was written")
        elif then[c.start - 1 : c.end] != now[c.start - 1 : c.end]:
            report.errors.append(f"{where} code has changed since {pinned[:7]}; re-read this passage")

    env = {**os.environ, "PYTHONPATH": str(repo / outline["repo"].get("import_path", "."))}
    for i, (lang, block) in enumerate(PROOF_RE.findall(text) if proofs is None else proofs, 1):
        report.proofs += 1
        for m in VACUOUS.finditer(block):
            line = block[: m.start()].count("\n") + 1
            report.errors.append(f"proof {i} line {line} can't fail: {block.splitlines()[line - 1].strip()}")
        try:
            runner = [repo_python(repo), "-c"] if lang == "python" else RUNNERS[lang]
            run = subprocess.run([*runner, block], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            report.errors.append(f"proof {i} timed out after 60s")
            continue
        if run.returncode != 0:
            output = (run.stderr.strip() or run.stdout.strip()).splitlines() or ["(no output)"]
            last = output[-1]
            report.errors.append(f"proof {i} failed: {last}")

    if report.citations == 0:
        report.warnings.append("no citations: nothing in this chapter can be checked against the code")
    if report.proofs == 0:
        report.warnings.append("no proof block")
    return report


def main(story_dir: str) -> int:
    story = Path(story_dir).resolve()
    outline = json.loads((story / "outline.json").read_text())
    repo = repo_path(outline)
    if not repo.exists():
        print(f"repo not found at {repo}; clone {outline['repo']['url']} there first")
        return 2

    head = git(repo, "rev-parse", "HEAD").strip()
    print(f"{outline['title']}\n  story pinned to {outline['repo']['commit'][:7]}, repo is at {head[:7]}\n")

    cache: dict = {}
    failed = False
    for chapter in sorted(story.glob("[0-9][0-9]-*.md")):
        r = check_chapter(chapter, outline, repo, cache)
        mark = "FAIL" if r.errors else "ok  "
        print(f"  {mark} {r.chapter}  ({r.citations} citations, {r.proofs} proofs)")
        for e in r.errors:
            print(f"         ✗ {e}")
        for w in r.warnings:
            print(f"         ! {w}")
        failed |= bool(r.errors)

    written = len(list(story.glob("[0-9][0-9]-*.md")))
    print(f"\n  {written}/{len(outline['chapters'])} chapters written")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
