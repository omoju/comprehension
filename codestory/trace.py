"""Run the intended use of a Python repo and record the data's path through its code.

    python3 codestory/trace.py <repo> <scenario.py> <out.json>

The scenario is a small script that uses the code as intended (the "main"). Every call into a function defined
in the repo (outside tests) is recorded: where it is, who called it and from which line, the arguments it
received and what it returned. Values are shown as short reprs. The result is a tree rooted at the scenario:
the traversal the story is told from.

Standard library only. Runs the scenario in this process, so run it via subprocess from the harness.
"""

from __future__ import annotations

import collections
import json
import reprlib
import runpy
import sys
from pathlib import Path

_repr = reprlib.Repr()
_repr.maxstring = 80
_repr.maxother = 80
_repr.maxlist = _repr.maxdict = _repr.maxtuple = 6


def show(value: object) -> str:
    try:
        return _repr.repr(value)
    except Exception:  # a repr that raises tells the story nothing
        return f"<{type(value).__name__}>"


def trace(repo: Path, scenario: Path) -> dict:
    repo = repo.resolve()
    skip = ("/tests/", "/test/", "/.venv/", "/site-packages/")
    root = {"fn": "scenario", "file": scenario.name, "line": 1, "args": {}, "calls": [], "lines": {}}
    executed = collections.defaultdict(set)  # file -> line numbers that ran: which way each branch went
    stack = [root]

    def in_repo(filename: str) -> bool:
        return filename.startswith(str(repo)) and not any(s in filename for s in skip)

    importing = [0]  # import-time code (module and class bodies) is setup, not the data's journey

    def import_tracer(frame, event, arg):
        if event == "return":
            importing[0] -= 1
        return import_tracer

    def tracer(frame, event, arg):
        if event != "call":
            return None
        if frame.f_code.co_name == "<module>" and frame.f_code.co_filename != str(scenario):
            importing[0] += 1
            return import_tracer
        if importing[0] or not in_repo(frame.f_code.co_filename):
            return None
        code = frame.f_code
        caller = frame.f_back
        args = {}
        for name in code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]:
            if name in frame.f_locals:
                v = frame.f_locals[name]
                args[name] = f"<{type(v).__name__}>" if name in ("self", "cls") else show(v)
        node = {
            "fn": getattr(code, "co_qualname", code.co_name),  # co_qualname is 3.11+
            "file": str(Path(code.co_filename).relative_to(repo)),
            "line": code.co_firstlineno,
            "called_from": f"{Path(caller.f_code.co_filename).name}:{caller.f_lineno}" if caller else None,
            "args": args,
            "calls": [],
        }
        stack[-1]["calls"].append(node)
        stack.append(node)

        rel = node["file"]

        def local(frame, event, arg):
            if event == "line":
                executed[rel].add(frame.f_lineno)
            elif event == "return":
                node["returned"] = show(arg)
                stack.pop()
            elif event == "exception":
                node.setdefault("raised", show(arg[1]))  # may still be caught inside; "returned" says if it was
            return local

        return local

    sys.settrace(tracer)
    try:
        runpy.run_path(str(scenario), run_name="__main__")
    finally:
        sys.settrace(None)
    root["lines"] = {f: sorted(ls) for f, ls in sorted(executed.items())}
    return root


COMPREHENSIONS = ("<genexpr>", "<listcomp>", "<dictcomp>", "<setcomp>", "<lambda>")
BUDGET = 800  # lines of trace text a story is planned from


def compress(tree: dict, budget: int = BUDGET) -> dict:
    """Keep the plot, drop the plumbing. Three steps, each only if needed:
    1. comprehension and lambda frames fold into their parent (their calls move up);
    2. a run of identical sibling calls becomes the first call plus one "×N more" line;
    3. if still over budget, cut at the deepest depth that fits; below it, "… N nested calls"."""
    tree = json.loads(json.dumps(tree))  # don't touch the caller's copy

    def fold(node):
        calls = []
        for c in node["calls"]:
            fold(c)
            calls.extend(c["calls"] if c["fn"].rsplit(".", 1)[-1] in COMPREHENSIONS else [c])
        node["calls"] = calls

    def collapse(node):
        calls, i = [], 0
        while i < len(node["calls"]):
            j = i
            while j + 1 < len(node["calls"]) and node["calls"][j + 1]["fn"] == node["calls"][i]["fn"]:
                j += 1
            first = node["calls"][i]
            collapse(first)
            calls.append(first)
            if j > i:
                rest = node["calls"][i + 1:j + 1]
                returns = {r.get("returned") for r in rest}
                calls.append({"fn": first["fn"], "file": first["file"], "line": first["line"], "args": {},
                              "calls": [], "repeat": len(rest),
                              "returned": returns.pop() if len(returns) == 1 else "(various)"})
            i = j + 1
        node["calls"] = calls

    def descendants(node):
        return sum(1 + descendants(c) for c in node["calls"]) + node.get("elided", 0)

    def cut(node, depth, limit):
        if depth == limit and node["calls"]:
            node["elided"] = descendants(node)
            node["calls"] = []
        for c in node["calls"]:
            cut(c, depth + 1, limit)

    fold(tree)
    collapse(tree)
    if len(render(tree)) > budget:
        for limit in range(30, 0, -1):
            trial = json.loads(json.dumps(tree))
            cut(trial, 0, limit)
            if len(render(trial)) <= budget:
                tree = trial
                break
    return tree


def render(node: dict, depth: int = 0, out: list[str] | None = None) -> list[str]:
    """The tree as text: one line per call, indented by depth. Records each call's line number as "tl"."""
    out = [] if out is None else out
    pad = "  " * depth
    if "repeat" in node:
        out.append(f"{pad}… {node['fn']} ×{node['repeat']} more  [{node['file']}:{node['line']}]")
        node["tl"] = len(out)
        return out
    args = ", ".join(f"{k}={v}" for k, v in node["args"].items() if v not in ("<self>",))
    out.append(f"{pad}{node['fn']}({args})  [{node['file']}:{node['line']}]")
    node["tl"] = len(out)
    for child in node["calls"]:
        render(child, depth + 1, out)
    if node.get("elided"):
        out.append(f"{pad}  … {node['elided']} nested calls")
    if "returned" in node:
        out.append(f"{pad}  → {node['returned']}")
    if "raised" in node and "returned" not in node:
        out.append(f"{pad}  ✗ raised {node['raised']}")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    repo, scenario, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
    sys.path.insert(0, str(repo.resolve() / ("src" if (repo / "src").is_dir() else "")))
    tree = trace(repo, scenario)
    out.write_text(json.dumps(tree, indent=1) + "\n")
    print("\n".join(render(tree)))
