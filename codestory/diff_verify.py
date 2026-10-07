"""Check a change story against both sides of the change.

    .venv/bin/python codestory/diff_verify.py <story-dir> [--against <rev>] [--no-proofs]

Per chapter:
  citations  every permalink names the change's base or head commit and points at lines that exist there
  drift      with --against (say, the pull request's newer head): the cited head lines still read the same at <rev>,
             wherever they have moved. Lines are matched by content, so code that only moved is reported as moved.
  proofs     the chapter's proof (proofs/NN.ts, a whole spec file) passes on the head. A "changed" chapter's proof
             must also fail on the base: a proof that passes on both sides proves nothing about the change. A
             "preserved" chapter's proof must pass on both. All proofs run in one test run per side.
Exit code 0 only if everything passes. Standard library only.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from diff import checkout, repo_dir, run_traced
from verify import find_citations

PROOF_TS = re.compile(r"```(?:ts|typescript) proof\n(.*?)```", re.DOTALL)
PROOF_LEAD_IN = re.compile(r"(\n(-{3,}|#+ [^\n]*proof[^\n]*)\s*)+$", re.I)
PROOF_DIR = "tests/unit/codestory"  # inside the package; the unit suite's glob picks it up

# Assertions that cannot fail, in the shapes Japa's assert and Vitest's expect take.
VACUOUS = re.compile(
    r"\|\|\s*true\b|\bassert\.(?:isTrue|ok)\(\s*true\s*[,)]|\bexpect\(\s*true\s*\)\.toBe(?:Truthy)?\(\s*(?:true)?\s*\)"
    r"|\bassert\.(?:equal|strictEqual|deepEqual)\(\s*(?P<a>[\w.\[\]'\"]+)\s*,\s*(?P=a)\s*[,)]"
    r"|\bexpect\(\s*(?P<b>[\w.\[\]'\"]+)\s*\)\.to(?:Be|Equal|StrictEqual)\(\s*(?P=b)\s*\)", re.M)
MISSING_NAME = re.compile(r"is not a function|is not a constructor|Cannot read propert|is undefined|of undefined")


@dataclass
class Report:
    chapter: str
    citations: int = 0
    proofs: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    head: str = ""  # the proof's outcome on each side: pass, fail: <message>, not loaded, …
    base: str = ""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def split_proof(text: str) -> tuple[str, str | None]:
    """A chapter's story and its proof (the last ```ts proof block), apart."""
    found = list(PROOF_TS.finditer(text))
    if not found:
        return text.rstrip() + "\n", None
    m = found[-1]
    story = PROOF_LEAD_IN.sub("", text[:m.start()].rstrip()) + text[m.end():]
    return story.rstrip() + "\n", m.group(1)


def story_slug(story: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", story.name.lower()).strip("_")


def proof_name(story: Path, n: int) -> str:
    """The proof's spec file name: unique per story and chapter, since the runner selects files by name suffix."""
    return f"cs_{story_slug(story)}_{n:02}.spec.ts"


def chapter_files(story: Path, n: int) -> tuple[Path | None, Path]:
    found = sorted(story.glob(f"{n:02}-*.md"))
    return (found[0] if found else None), story / "proofs" / f"{n:02}.ts"


# ---------------------------------------------------------------- citations and drift

def file_at(repo: Path, rev: str, path: str, cache: dict) -> list[str] | None:
    if (rev, path) not in cache:
        try:
            cache[(rev, path)] = git(repo, "show", f"{rev}:{path}").splitlines()
        except subprocess.CalledProcessError:
            cache[(rev, path)] = None
    return cache[(rev, path)]


def line_map(old: list[str], new: list[str]) -> dict[int, int]:
    """Where each unchanged line of `old` sits in `new` (1-based)."""
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    return {i1 + k + 1: j1 + k + 1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "equal" for k in range(i2 - i1)}


def check_citations(text: str, info: dict, repo: Path, cache: dict, report: Report, against: str | None) -> None:
    sides = {info["base"]: "base", info["head"]: "head"}
    for c in find_citations(text, info["url"]):
        report.citations += 1
        where = f"line {c.line}: {c}"
        rev = next((full for full in sides if full.startswith(c.commit) or c.commit.startswith(full)), None)
        if rev is None:
            report.errors.append(f"{where} cites commit {c.commit[:7]}, which is neither the base "
                                 f"({info['base'][:7]}) nor the head ({info['head'][:7]})")
            continue
        lines = file_at(repo, rev, c.path, cache)
        if lines is None:
            report.errors.append(f"{where} file does not exist on the {sides[rev]} ({rev[:7]})")
            continue
        if not (1 <= c.start <= c.end <= len(lines)):
            report.errors.append(f"{where} is outside the file on the {sides[rev]} ({len(lines)} lines)")
            continue
        if against and sides[rev] == "head":
            now = file_at(repo, against, c.path, cache)
            if now is None:
                report.errors.append(f"{where} file is gone at {against[:7]}")
                continue
            mapping = line_map(lines, now)
            span = [mapping.get(k) for k in range(c.start, c.end + 1)]
            if None in span or span != list(range(span[0], span[0] + len(span))):
                report.errors.append(f"{where} code has changed at {against[:7]}; re-read this passage")
            elif span[0] != c.start:
                report.warnings.append(f"{where} moved to L{span[0]}-L{span[-1]} at {against[:7]} (unchanged)")


# ---------------------------------------------------------------- proofs, on both sides

def outcome(test: dict) -> str:
    if test.get("runaway"):
        return "runaway"
    if "raised" in test and "returned" not in test:
        return f"fail: {test['raised']}"
    return "pass" if "returned" in test else "unfinished"


def run_proofs(story: Path, outline: dict, setup: dict, ns: list[int]) -> dict[int, dict[str, str]]:
    """Each chapter's proof, as a spec file, run once on each side. Returns {n: {"head": …, "base": …}}.

    All proofs share one run per side (each run boots the application). A proof can hang its run, as the base of a
    change that fixes a hang will: then the proofs that never got to run are rerun one per process, so one hang
    costs one chapter its result, not every chapter."""
    names = {proof_name(story, n): n for n in ns if chapter_files(story, n)[1].exists()}
    results = {n: {"head": "no proof", "base": "no proof"} for n in ns}
    for side in ("head", "base"):
        pkg_dir = checkout(setup, side)
        folder = pkg_dir / PROOF_DIR
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob(f"cs_{story_slug(story)}_*.spec.ts"):
            old.unlink()  # this story's earlier proofs
        for name, n in names.items():
            (folder / name).write_text(chapter_files(story, n)[1].read_text())
        got, timed_out = run_side(story, setup, pkg_dir, side, list(names))
        if timed_out:  # the proofs that never started get a run each
            for name in [x for x in names if x not in got]:
                alone, _ = run_side(story, setup, pkg_dir, side, [name])
                got.update(alone)
        for name, n in names.items():
            results[n][side] = got.get(name, "not loaded (the run timed out)")
    return results


def run_side(story: Path, setup: dict, pkg_dir: Path, side: str, names: list[str]) -> tuple[dict[str, str], bool]:
    """One run of the named proofs on one side: ({name: outcome} for each proof that recorded a test, timed out?)."""
    out = story / f"proofs.{side}.json"
    out.unlink(missing_ok=True)
    # No app code is instrumented (CS_INCLUDE matches nothing) and no lines are kept: only each test's outcome.
    code, tail = run_traced(pkg_dir, [f"{PROOF_DIR}/{name}" for name in names], out, soft=side == "base",
                            timeout=int(setup.get("timeout", 300)), runner=setup.get("runner", "japa"),
                            env_extra={"CS_INCLUDE": "-/", "CS_LINES": "0"})
    tests = json.loads(out.read_text())["calls"] if out.exists() else []
    got = {}
    for name in names:
        mine = [t for t in tests if Path(t["file"]).name == name]
        if mine:
            bad = [o for o in map(outcome, mine) if o != "pass"]
            got[name] = bad[0] if bad else "pass"
        elif code is not None:
            got[name] = f"not loaded: {last_error(tail, name)}"
    return got, code is None


def last_error(tail: str, name: str) -> str:
    """The runner's complaint about a spec that never loaded, as one line."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", tail)
    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    hits = [ln for ln in lines if re.search(r"Error|error TS|SyntaxError|Cannot find|is not", ln)]
    return (hits[0] if hits else (lines[-1] if lines else "no output"))[:300]


def judge_proof(kind: str, res: dict[str, str], report: Report) -> None:
    report.head, report.base = res["head"], res["base"]
    if res["head"] == "no proof":
        report.errors.append("no ```ts proof block")
        return
    if res["head"] != "pass":
        report.errors.append(f"proof fails on the head: {res['head']}")
    if kind == "changed" and res["base"] == "pass":
        report.errors.append("proof passes on the base too, so it does not show the change: assert something the "
                             "base gets wrong and the head gets right")
    elif kind == "changed" and res["head"] == "pass" and MISSING_NAME.search(res["base"]):
        report.warnings.append(f"on the base the proof fails only because a name the change adds is missing "
                               f"({res['base']}); it shows the name is new, not the behaviour")
    if kind == "preserved" and res["base"] != "pass":
        report.errors.append(f"a 'preserved' chapter's proof must pass on the base as well; there: {res['base']}")


# ---------------------------------------------------------------- the whole story

def verify(story: Path, ns: list[int] | None = None, proofs: bool = True, against: str | None = None) -> dict[int, Report]:
    outline = json.loads((story / "outline.json").read_text())
    setup = json.loads((story / "changes.json").read_text())
    repo, info = repo_dir(setup), outline["repo"]
    chapters = {c["n"]: c for c in outline["chapters"]}
    ns = sorted(chapters) if ns is None else ns
    reports, cache = {}, {}
    for n in ns:
        md, proof = chapter_files(story, n)
        r = reports[n] = Report(md.name if md else f"chapter {n} (not written)")
        if md is None:
            r.errors.append("not written")
            continue
        check_citations(md.read_text(), info, repo, cache, r, against)
        if r.citations == 0:
            r.warnings.append("no citations: nothing in this chapter can be checked against the code")
        if proof.exists():
            r.proofs = 1
            for m in VACUOUS.finditer(proof.read_text()):
                r.errors.append(f"proof can't fail: {m.group(0).strip()}")
    if proofs:
        for n, res in run_proofs(story, outline, setup, [n for n in ns if chapter_files(story, n)[0]]).items():
            judge_proof(chapters[n]["kind"], res, reports[n])
    return reports


def main(story_arg: str, against: str | None, proofs: bool) -> int:
    story = Path(story_arg).resolve()
    outline = json.loads((story / "outline.json").read_text())
    if against:
        against = git(repo_dir(json.loads((story / "changes.json").read_text())), "rev-parse", against).strip()
    print(f"{outline['title']}\n  base {outline['repo']['base'][:7]} → head {outline['repo']['head'][:7]}"
          + (f", checked against {against[:7]}" if against else "") + "\n")
    failed = False
    for n, r in verify(story, proofs=proofs, against=against).items():
        print(f"  {'FAIL' if r.errors else 'ok  '} {r.chapter}  ({r.citations} citations"
              + (f"; proof: head {r.head}, base {r.base}" if proofs and r.proofs else "") + ")")
        for e in r.errors:
            print(f"         ✗ {e}")
        for w in r.warnings:
            print(f"         ! {w}")
        failed |= bool(r.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    against = argv[argv.index("--against") + 1] if "--against" in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1:i] != ["--against"]]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], against, proofs="--no-proofs" not in argv))
