"""Step 0 for a change: what changed, and how one real run differs before and after it.

    python3 codestory/diff.py <repo> <base> <head> <story-dir> --pkg <package> --spec <spec> \\
        [--runner japa|vitest] [--link node_modules,...] [--include app/,...] [--timeout SECONDS]

The repository explainer follows one run of a repo's intended use. A change has its own intended use: the tests
that come with it. This step checks out <base> and <head> as worktrees, links the named dependencies from <repo>'s
package into each (so nothing is reinstalled), and runs the *head* spec under the TypeScript tracer on both sides.
A test that fails before and passes after is the change, stated as an executable claim.

Writes into <story-dir>:
  changes.json       functions the diff touches, per file: modified / added / removed, with base and head spans
  trace.base.json    trace.head.json    the two runs, in trace.py's shape
  diff.txt           the run with the change marked: `+` only after, `-` only before, `~` same call, other result,
                     `*` the function's code changed; unchanged stretches folded
  diff.json          per test: outcome before and after; changed functions the run reached, and those it never did
  diff.tree.json     the merged run as a tree, with each call's line in diff.txt and each test's executed lines

TypeScript (and JavaScript) packages tested with Japa (AdonisJS) or Vitest (Vite, Vue). Standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = Path(__file__).resolve().parent / "ts"

# How to run one spec file under the tracer, per test runner. Run from the package directory; {spec} is the spec's
# path relative to it, {suite} and {file} come from that path. The run reads CS_TRACE_OUT and CS_SOFT_IMPORTS.
RUNNERS = {
    "japa": ["node", "--enable-source-maps", "--import", str(TS / "register.mjs"),  # AdonisJS backend
             "--import", "ts-node-maintained/register/esm", "bin/test.ts", "{suite}", "--files={file}"],
    "vitest": ["node", str(TS / "vitest-run.mjs"), "{spec}"],  # Vite / Vue frontend
}
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def stored(path: Path) -> str:
    """A path as a story keeps it: relative to the project root, so it carries no machine-specific prefix."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def repo_dir(setup: dict) -> Path:
    """The repository a story's change.json names (an absolute path survives the join)."""
    return (ROOT / setup["repo"]).resolve()


def under(pkg: str, rel: str) -> str:
    """A path inside the package, from the repository root; "." is a package at the root."""
    return rel if pkg in ("", ".") else f"{pkg.rstrip('/')}/{rel}"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


# ---------------------------------------------------------------- what changed

def hunks(repo: Path, base: str, head: str, pkg: str) -> dict[str, dict[str, list[int]]]:
    """Changed line numbers per file: {"path": {"old": [...], "new": [...]}}. A pure deletion marks the line it
    follows (and the one after) on the side where nothing remains, so the enclosing function still counts."""
    out: dict[str, dict[str, list[int]]] = {}
    path = None
    for line in git(repo, "diff", "-U0", "--no-color", base, head, "--", pkg).splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("--- ") and line != "--- /dev/null":
            path = line[6:]
        m = HUNK.match(line)
        if m and path:
            a, b, c, d = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
            entry = out.setdefault(path, {"old": [], "new": []})
            entry["old"] += range(a, a + b) if b else [max(a, 1), a + 1]
            entry["new"] += range(c, c + d) if d else [max(c, 1), c + 1]
    return out


def function_spans(repo: Path, rev: str, paths: list[str], pkg_dir: Path) -> dict[str, list[dict]]:
    """{path: [{name, line, end}]} for each path that exists at rev, from the TypeScript parser."""
    with tempfile.TemporaryDirectory() as tmp:
        files = {}
        for p in paths:
            try:
                source = git(repo, "show", f"{rev}:{p}")
            except subprocess.CalledProcessError:
                continue  # not in this revision
            f = Path(tmp) / p.replace("/", "__")
            f.write_text(source)
            files[str(f)] = p
        if not files:
            return {}
        run = subprocess.run(["node", str(TS / "functions.mjs"), str(pkg_dir), *files], capture_output=True,
                             text=True, check=True)
        return {files[k]: v for k, v in json.loads(run.stdout).items()}


def innermost(spans: list[dict], line: int) -> dict | None:
    inside = [s for s in spans if s["line"] <= line <= s["end"]]
    return min(inside, key=lambda s: s["end"] - s["line"]) if inside else None


def changed_functions(repo: Path, base: str, head: str, pkg: str, include: list[str], pkg_dir: Path) -> dict:
    """Attribute every changed line to the innermost function containing it, on each side."""
    changed = {p: h for p, h in hunks(repo, base, head, pkg).items()
               if p.endswith((".ts", ".mts", ".js", ".mjs", ".vue")) and not re.search(r"\.(spec|test)\.", p)
               and any(p.startswith(under(pkg, i)) for i in include)}
    before = function_spans(repo, base, list(changed), pkg_dir)
    after = function_spans(repo, head, list(changed), pkg_dir)
    out = {}
    for path, lines in changed.items():
        old_names = {s["name"]: s for s in before.get(path, [])}
        new_names = {s["name"]: s for s in after.get(path, [])}
        touched_new = {s["name"] for n in lines["new"] if (s := innermost(after.get(path, []), n))}
        touched_old = {s["name"] for n in lines["old"] if (s := innermost(before.get(path, []), n))}
        module_level = sorted({n for n in lines["new"] if path in after and not innermost(after[path], n)})
        fns = []
        for name in sorted(touched_new | touched_old, key=lambda n: (new_names.get(n) or old_names[n])["line"]):
            kind = "added" if name not in old_names else "removed" if name not in new_names else "modified"
            fns.append({"name": name, "kind": kind,
                        "base": [old_names[name]["line"], old_names[name]["end"]] if name in old_names else None,
                        "head": [new_names[name]["line"], new_names[name]["end"]] if name in new_names else None})
        out[path] = {"functions": fns, "module_level_lines": module_level}
    return out


# ---------------------------------------------------------------- running both sides

def worktree(repo: Path, rev: str, where: Path) -> Path:
    if not (where / ".git").exists():
        where.parent.mkdir(parents=True, exist_ok=True)
        git(repo, "worktree", "add", "-q", "--detach", str(where), rev)
    return where


def checkout(setup: dict, side: str) -> Path:
    """The package directory of a worktree at the base or head of the change, with its dependencies linked."""
    repo, rev = repo_dir(setup), setup[side]
    wt = worktree(repo, rev, ROOT / "demo-repos" / ".worktrees" / f"{repo.name}-{rev[:10]}")
    link(repo / setup["pkg"], wt / setup["pkg"], [x.strip() for x in setup["link"].split(",") if x.strip()])
    return wt / setup["pkg"]


def release(setup: dict) -> None:
    """Remove the change's worktrees (links first, so nothing they point at is touched)."""
    repo = repo_dir(setup)
    for side in ("base", "head"):
        wt = ROOT / "demo-repos" / ".worktrees" / f"{repo.name}-{setup[side][:10]}"
        if not wt.exists():
            continue
        for name in [x.strip() for x in setup["link"].split(",") if x.strip()]:
            target = wt / setup["pkg"] / name
            if target.is_symlink():
                target.unlink()
        git(repo, "worktree", "remove", "--force", str(wt))


def link(src_pkg: Path, dst_pkg: Path, names: list[str]) -> None:
    for name in names:
        target, src = dst_pkg / name, src_pkg / name
        if src.exists() and not target.exists() and not target.is_symlink():
            target.symlink_to(src)


def run_traced(pkg_dir: Path, specs: str | list[str], out: Path, soft: bool, timeout: int,
               runner: str = "japa", env_extra: dict | None = None) -> tuple[int | None, str]:
    """Run spec files (of one suite) under the tracer, in one run. The run gets its own process group: on timeout
    the group gets SIGTERM (the app shuts down and the tracer writes what it has), then SIGKILL, so no child
    (a database server, a worker pool) is orphaned. Returns (exit code, or None on timeout; the output's tail)."""
    specs = [specs] if isinstance(specs, str) else specs
    parts = Path(specs[0]).parts  # tests/<suite>/<file>
    suite = parts[1] if len(parts) > 2 and parts[0] == "tests" else "unit"
    template = RUNNERS[runner]
    argv = [a.format(suite=suite, file=",".join(Path(s).name for s in specs), spec=specs[0]) for a in template]
    if any("{spec}" in a for a in template):
        argv += specs[1:]  # a runner that takes paths takes the rest as further arguments
    env = {**os.environ, "CS_TRACE_OUT": str(out), "CS_SOFT_IMPORTS": "1" if soft else "0", **(env_extra or {})}
    proc = subprocess.Popen(argv, cwd=pkg_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            output, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
        code = None
    try:
        os.killpg(proc.pid, signal.SIGKILL)  # whatever the run left behind (a crash skips the app's own shutdown)
    except ProcessLookupError:
        pass
    return code, (output or "")[-3000:]


# ---------------------------------------------------------------- the two runs, side by side

def key(n: dict) -> tuple[str, str]:
    return n["fn"], n["file"]


def verdict(test: dict | None) -> str:
    """How a test ended: pass, fail, runaway (hit the call budget), unfinished (the run died or was stopped)."""
    if test is None:
        return "absent"
    if test.get("runaway"):
        return "runaway"
    if "raised" in test and "returned" not in test:
        return "fail"
    return "pass" if "returned" in test else "unfinished"


def outcome(n: dict) -> str:
    if "raised" in n and "returned" not in n:
        return f"raised {n['raised']}"
    return f"→ {n['returned']}" if "returned" in n else "✗ never returned (the run hung or died here)"


def mark(n: dict, sign: str) -> dict:
    return {**n, "mark": sign, "calls": [mark(c, sign) for c in n["calls"]]}


def signature(n: dict) -> tuple[str, str, str]:
    return n["fn"], n["file"], json.dumps(n.get("args"), sort_keys=True)


def align(b: dict, h: dict) -> dict:
    """Merge two runs of the same call. Children pair up in two passes: first calls with the same function *and*
    arguments (so a call inserted among look-alikes reads as one insertion, not a shifted row of changes), then,
    inside each gap, calls to the same function."""
    node = {**h, "mark": " ", "calls": []}
    if outcome(b) != outcome(h) or b.get("args") != h.get("args"):
        node["mark"], node["before"] = "~", {"args": b.get("args"), "outcome": outcome(b)}
    bc, hc = b["calls"], h["calls"]
    exact = difflib.SequenceMatcher(None, [signature(c) for c in bc], [signature(c) for c in hc], autojunk=False)
    for op, i1, i2, j1, j2 in exact.get_opcodes():
        if op == "equal":
            node["calls"] += [align(x, y) for x, y in zip(bc[i1:i2], hc[j1:j2])]
            continue
        gb, gh = bc[i1:i2], hc[j1:j2]
        loose = difflib.SequenceMatcher(None, [key(c) for c in gb], [key(c) for c in gh], autojunk=False)
        for op2, k1, k2, l1, l2 in loose.get_opcodes():
            if op2 == "equal":
                node["calls"] += [align(x, y) for x, y in zip(gb[k1:k2], gh[l1:l2])]
            else:
                node["calls"] += [mark(x, "-") for x in gb[k1:k2]] + [mark(y, "+") for y in gh[l1:l2]]
    return node


def interesting(n: dict, touched: set) -> bool:
    return n["mark"] != " " or key(n) in touched or any(interesting(c, touched) for c in n["calls"])


def render(n: dict, touched: set, depth: int = 0, out: list | None = None) -> list[str]:
    out = [] if out is None else out
    pad = "  " * depth
    star = " *" if key(n) in touched else ""
    args = ", ".join(f"{k}={v}" for k, v in n.get("args", {}).items())
    out.append(f"{n['mark']} {pad}{n['fn']}({args})  [{n['file']}:{n['line']}]{star}")
    n["tl"] = len(out)  # this call's line in diff.txt, so the page can place it in a chapter's span
    if n["mark"] == "~":
        b = n["before"]
        if b["args"] != n.get("args"):
            out.append(f"~ {pad}  before: ({', '.join(f'{k}={v}' for k, v in (b['args'] or {}).items())})")
        out.append(f"~ {pad}  before {b['outcome']}")
    i, calls = 0, n["calls"]
    while i < len(calls):
        c = calls[i]
        if interesting(c, touched):
            render(c, touched, depth + 1, out)
            i += 1
            continue
        j = i
        while j < len(calls) and not interesting(calls[j], touched):
            j += 1
        names = sorted({x["fn"].rsplit(".", 1)[-1] for x in calls[i:j]})
        out.append(f"  {pad}  … {j - i} unchanged call{'s' if j - i > 1 else ''} ({', '.join(names[:4])}"
                   f"{', …' if len(names) > 4 else ''})")
        i = j
    sign = "~" if n["mark"] == "~" else n["mark"]
    out.append(f"{sign} {pad}  {outcome(n)}")
    return out


def reached(tree: dict) -> set:
    found, stack = set(), [tree]
    while stack:
        n = stack.pop()
        found.add(key(n))
        stack += n["calls"]
    return found


def compare(base: dict, head: dict, changes: dict) -> tuple[list[str], dict, list[dict]]:
    touched = {(f["name"], path) for path, c in changes.items() for f in c["functions"]}
    tests_b = {(t["fn"], t.get("line")): t for t in base["calls"]}  # titles can repeat across describe blocks
    base_died = bool(base.get("crashed") or base.get("timed_out"))
    lines, tests, trees = [], [], []
    for t in head["calls"]:
        b = tests_b.get((t["fn"], t.get("line")))
        merged = align(b, t) if b else mark(t, "+")
        before, after = verdict(b), verdict(t)
        if before == "absent" and base_died:
            before = "not run"  # the base run died before reaching it
        tests.append({"test": t["fn"].removeprefix("test: "), "before": before, "after": after})
        lines.append(f"## {t['fn']}   (before: {before}, after: {after})")
        if interesting(merged, touched):
            render(merged, touched, 0, lines)
        else:
            lines.append("  (no difference, touches nothing changed)")
        lines.append("")
        trees.append({"test": t["fn"].removeprefix("test: "), "before": before, "after": after, "tree": merged,
                      "lines": {"head": t.get("lines", {}), "base": (b or {}).get("lines", {})}})
    seen_head, seen_base = reached(head), reached(base)
    coverage = []
    for path, c in changes.items():
        for f in c["functions"]:
            side = seen_base if f["kind"] == "removed" else seen_head
            coverage.append({"file": path, "function": f["name"], "kind": f["kind"],
                             "reached": (f["name"], path) in side})
    return lines, {"tests": tests, "coverage": coverage, "touched": sorted(f"{p}::{n}" for n, p in touched),
                   "proofs": [t["test"] for t in tests
                              if t["before"] in ("fail", "runaway", "unfinished") and t["after"] == "pass"]}, trees


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("repo"), ap.add_argument("base"), ap.add_argument("head"), ap.add_argument("story")
    ap.add_argument("--pkg", required=True, help="package directory inside the repo (has package.json)")
    ap.add_argument("--spec", action="append", required=True, help="spec path relative to the package")
    ap.add_argument("--link", default="node_modules", help="comma-separated names to link from the repo's package")
    ap.add_argument("--include", help="comma-separated prefixes (in the package) to trace "
                                      "(default: app/ for japa, src/ for vitest)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per spec run before it is stopped")
    ap.add_argument("--runner", choices=sorted(RUNNERS), default="japa", help="test runner of the package")
    a = ap.parse_args()

    repo, story = Path(a.repo).resolve(), Path(a.story).resolve()
    story.mkdir(parents=True, exist_ok=True)
    base, head = git(repo, "rev-parse", a.base).strip(), git(repo, "rev-parse", a.head).strip()
    a.include = a.include or ("src/" if a.runner == "vitest" else "app/")
    include = [i.strip() for i in a.include.split(",") if i.strip()]
    print(f"{repo.name}: {base[:7]}..{head[:7]} in {a.pkg}/")

    changes = changed_functions(repo, base, head, a.pkg, include, repo / a.pkg)
    setup = {"repo": stored(repo), "base": base, "head": head, "pkg": a.pkg, "specs": a.spec, "runner": a.runner,
             "link": a.link, "include": a.include, "timeout": a.timeout}  # enough for later stages to rerun
    (story / "changes.json").write_text(json.dumps({**setup, "files": changes}, indent=1) + "\n")
    n = sum(len(c["functions"]) for c in changes.values())
    print(f"  {n} changed functions in {len(changes)} files")

    trees = {}
    for side, rev in (("base", base), ("head", head)):
        pkg_dir = checkout(setup, side)
        for spec in a.spec:  # the head's tests describe the change; run them on both sides
            dst = pkg_dir / spec
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(git(repo, "show", f"{head}:{under(a.pkg, spec)}"))
        out = story / f"trace.{side}.json"
        out.unlink(missing_ok=True)
        merged = {"fn": "scenario", "file": "scenario", "line": 1, "args": {}, "calls": [], "lines": {}}
        for spec in a.spec:
            code, tail = run_traced(pkg_dir, spec, out, soft=side == "base", timeout=a.timeout, runner=a.runner,
                                    env_extra={"CS_INCLUDE": a.include})
            if code is None:
                print(f"  {side}: {spec} still running after {a.timeout}s; stopped (what ran is kept)")
                merged.setdefault("timed_out", []).append(spec)
            elif code not in (0, 1):  # 1 is "some tests failed"; anything else, the process itself died
                print(f"  {side}: {spec} crashed (exit {code}); keeping the trace written before it died")
                merged.setdefault("crashed", []).append(spec)
            if not out.exists():
                print(f"  {side}: no trace from {spec} (exit {code}):\n{tail}")
                return 1
            merged["calls"] += json.loads(out.read_text())["calls"]
        out.write_text(json.dumps(merged, indent=1) + "\n")
        trees[side] = merged
        print(f"  {side}: {len(merged['calls'])} tests traced")

    lines, summary, merged = compare(trees["base"], trees["head"], changes)
    (story / "diff.txt").write_text("\n".join(lines) + "\n")
    (story / "diff.tree.json").write_text(json.dumps(merged) + "\n")
    (story / "diff.json").write_text(json.dumps(summary, indent=1) + "\n")
    hit = sum(c["reached"] for c in summary["coverage"])
    print(f"  {len(summary['proofs'])} tests fail before and pass after (the change's proofs)")
    print(f"  the run reaches {hit} of {len(summary['coverage'])} changed functions")
    for c in summary["coverage"]:
        if not c["reached"]:
            print(f"    never reached: {c['function']} ({c['kind']}, {c['file']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
