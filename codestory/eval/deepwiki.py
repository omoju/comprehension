"""Fetch the DeepWiki arm: every page of a repository's DeepWiki, through its public MCP server.

    .venv/bin/python codestory/eval/deepwiki.py owner/repo [owner/repo ...]      → eval/deepwiki/<repo>/

Writes structure.md (the topic list), contents.md (all pages, as DeepWiki returns them) and meta.json: the fetch
time, page and word counts, the source references ([path:start-end]() in DeepWiki's format) and the commit the
arm is pinned to. DeepWiki names no commit, so per PREREGISTRATION §4 the arm is pinned to the default branch on
the fetch date (GitHub API), which is checked out at eval/checkouts/<repo> for the judge. As a sanity check,
meta.json also counts how many of DeepWiki's source references point at lines that exist at that commit.
No model calls. Standard library only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eval" / "deepwiki"
CHECKOUTS = ROOT / "eval" / "checkouts"
MCP = "https://mcp.deepwiki.com/mcp"
SOURCE_REF = re.compile(r"\[([\w./+-]+):(\d+)(?:-(\d+))?\]\(\)")  # DeepWiki's citation: [path:start-end]()


def call(tool: str, **args) -> str:
    """One MCP tool call over plain HTTP; the server answers as a single server-sent event."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    req = urllib.request.Request(MCP, data=body.encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode()
    data = "".join(line[5:].strip() for line in raw.splitlines() if line.startswith("data:"))
    msg = json.loads(data)
    if "error" in msg:
        raise RuntimeError(f"{tool}: {msg['error']}")
    result = msg["result"]
    if result.get("isError"):
        raise RuntimeError(f"{tool}: {result['content'][0].get('text', result)}")
    return "\n".join(c["text"] for c in result["content"] if c["type"] == "text")


def default_branch_head(name: str) -> str:
    """The commit the default branch points at right now: what DeepWiki's pages are taken to describe."""
    req = urllib.request.Request(f"https://api.github.com/repos/{name}/commits/HEAD",
                                 headers={"Accept": "application/vnd.github.sha", "User-Agent": "codestories"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode().strip()


def checkout(name: str, commit: str) -> Path:
    """A worktree of demo-repos/<repo> at the arm's commit, so the judge reads the code the arm describes."""
    repo = ROOT / "demo-repos" / name.split("/")[1]
    target = CHECKOUTS / name.split("/")[1]
    if target.exists() and subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True,
                                          text=True).stdout.strip() == commit:
        return target
    subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin", commit], check=True)
    if target.exists():
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(target)], check=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(target), commit], check=True)
    return target


def reference_check(contents: str, tree: Path) -> dict:
    """How many of DeepWiki's [path:lines]() references point at lines that exist in the pinned tree."""
    refs = SOURCE_REF.findall(contents)
    ok = missing_file = out_of_range = 0
    lengths: dict[str, int | None] = {}
    for path, start, end in refs:
        if path not in lengths:
            f = tree / path
            lengths[path] = len(f.read_text(errors="replace").splitlines()) if f.is_file() else None
        n = lengths[path]
        if n is None:
            missing_file += 1
        elif int(end or start) > n:
            out_of_range += 1
        else:
            ok += 1
    return {"total": len(refs), "ok": ok, "missing_file": missing_file, "out_of_range": out_of_range}


def fetch(name: str) -> dict:
    out = OUT / name.split("/")[1]
    out.mkdir(parents=True, exist_ok=True)
    structure = call("read_wiki_structure", repoName=name)
    contents = call("read_wiki_contents", repoName=name)
    (out / "structure.md").write_text(structure + "\n")
    (out / "contents.md").write_text(contents + "\n")
    commit = default_branch_head(name)
    tree = checkout(name, commit)
    meta = {"repo": name, "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pages": contents.count("\n# Page: ") + contents.startswith("# Page: "), "words": len(contents.split()),
            "commit": commit, "commit_basis": "default branch HEAD on the fetch date (DeepWiki names no commit)",
            "checkout": str(tree.relative_to(ROOT)), "source_refs": reference_check(contents, tree)}
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    for name in sys.argv[1:]:
        try:
            m = fetch(name)
            s = m["source_refs"]
            print(f"{name:28} {m['pages']:3} pages {m['words']:7,} words  pinned {m['commit'][:7]}  "
                  f"refs {s['ok']}/{s['total']} resolve ({s['missing_file']} missing files, {s['out_of_range']} past end)")
        except Exception as e:  # keep going: one missing wiki shouldn't stop the others
            print(f"{name:28} FAILED: {e}")
