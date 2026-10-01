"""Render a story as a reading page: the journey map, the narrative, and the code, side by side.

    python3 codestory/render.py <story-dir>        → <story-dir>/index.html

The map is drawn from the recorded trace, grouped by the chapters' trace spans, so it can't disagree with the
story. Code comes from the repository at the pinned commit. No model calls. Standard library only.
"""

from __future__ import annotations

import ast
import collections
import html
import json
import re
import sys
from pathlib import Path

from verify import git, repo_path

HELPER_CALLS = 5   # a function called this often is plumbing (want_bytes); leave it off the map
MAP_DEPTH = 4      # deeper calls stay in the chapters, not on the map


def is_noise(node: ast.If) -> bool:
    """Decisions a flowchart shouldn't show: default-filling (`x is None`) and flags echoing an earlier decision."""
    t = node.test
    if isinstance(t, ast.Name):
        return True
    return (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], (ast.Is, ast.IsNot))
            and isinstance(t.comparators[0], ast.Constant) and t.comparators[0].value is None)


def summarize(stmts: list[ast.stmt]) -> str:
    """What a branch does, in a few words: the raise or return if there is one, else its first statement."""
    for s in stmts:
        for x in ast.walk(s):
            if isinstance(x, ast.Raise) and x.exc is not None:
                exc = x.exc.func if isinstance(x.exc, ast.Call) else x.exc
                return "raise " + ast.unparse(exc)
    for s in stmts:
        if isinstance(s, ast.Return):
            return "return " + (ast.unparse(s.value) if s.value else "None")
    return ast.unparse(stmts[0]).split("\n")[0] if stmts else "carry on"


def decisions(source: str, fn_line: int, ran: set[int]) -> list[dict]:
    """The `if`s and `try`s that ran in the function defined at fn_line, and which way each went."""
    tree = ast.parse(source)
    fn = next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.lineno == fn_line), None)
    if fn is None:
        return []
    parents = {id(c): p for p in ast.walk(fn) for c in ast.iter_child_nodes(p)}
    elifs = {id(n.orelse[0]) for n in ast.walk(fn) if isinstance(n, ast.If) and len(n.orelse) == 1
             and isinstance(n.orelse[0], ast.If)}
    lines_of = lambda stmts: {x.lineno for s in stmts for x in ast.walk(s) if hasattr(x, "lineno")}  # noqa: E731
    found = []
    for n in ast.walk(fn):
        if isinstance(n, ast.If) and n.lineno in ran and id(n) not in elifs and not is_noise(n):
            chain, node = [], n  # an if/elif/else chain becomes one decision
            while True:
                chain.append(node)
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    node = node.orelse[0]
                else:
                    break
            final_else = chain[-1].orelse
            taken = next((c for c in chain if lines_of(c.body) & ran), None)
            if len(chain) > 1:
                tests = [c.test for c in chain]
                lefts = {ast.unparse(t.left) for t in tests if isinstance(t, ast.Compare) and len(t.ops) == 1
                         and isinstance(t.ops[0], ast.Eq)}
                if len(lefts) == 1 and all(isinstance(t, ast.Compare) for t in tests):  # `x == a / elif x == b`
                    question = lefts.pop() + " == ?"
                    answer = ast.unparse(taken.test.comparators[0]) if taken else "none of them"
                else:
                    question, answer = ast.unparse(n.test), (ast.unparse(taken.test) if taken else "else")
                exit_ = summarize(final_else) if final_else else "no branch matches"
                side = "otherwise"
            else:
                yes = taken is not None
                answer = "yes" if yes else "no"
                side = "no" if yes else "yes"
                if yes:
                    untaken = final_else
                    if not untaken:  # a guard: `if ok: return x` then the fall-through is the other road
                        parent = parents.get(id(n))
                        body = next((getattr(parent, f) for f in ("body", "orelse", "finalbody")
                                     if n in getattr(parent, f, [])), [])
                        untaken = body[body.index(n) + 1:body.index(n) + 2]
                else:
                    untaken = n.body
                exit_ = summarize(untaken) if untaken else "carry on"
            found.append({"kind": "decision", "line": n.lineno, "end": chain[-1].end_lineno,
                          "question": question if len(chain) > 1 else ast.unparse(n.test),
                          "answer": answer, "side": side, "exit": exit_})
        elif isinstance(n, ast.Try) and n.lineno in ran and n.handlers:
            handler = n.handlers[0]
            caught = bool(lines_of(handler.body) & ran)
            found.append({"kind": "decision", "line": n.lineno, "end": n.end_lineno,
                          "question": ast.unparse(n.body[0]).split("\n")[0] + " fails?",
                          "answer": "yes" if caught else "no", "side": "no" if caught else "yes",
                          "exit": summarize(handler.body) if not caught else "carry on"})
    return sorted(found, key=lambda d: d["line"])


def flow(story: Path, outline: dict, files: dict) -> list[dict]:
    """The flowchart, in execution order: start, steps, decisions, the data the caller holds, end."""
    tree = json.loads((story / "trace.json").read_text())
    ran_lines = {f: set(ls) for f, ls in tree.get("lines", {}).items()}
    lines = (story / "trace.txt").read_text().splitlines()
    line = next(i for i, text in enumerate(lines, 1) if text.startswith("scenario("))  # older traces: stdout comes first
    counts = collections.Counter()

    def count(node):
        counts[node["fn"]] += 1
        for child in node["calls"]:
            count(child)

    count(tree)
    spans = [(c["n"], c["trace_lines"][0], c["trace_lines"][-1]) for c in outline["chapters"]]
    items = [{"kind": "start", "label": "The caller runs the intended use", "chapter": None}]
    current = [None]

    def shown(node, depth):
        return depth == 1 or (depth <= MAP_DEPTH and counts[node["fn"]] < HELPER_CALLS)

    def walk(node, depth):
        nonlocal line
        here = node.get("tl", line)  # compressed traces carry their own line numbers
        line += 1
        visible = depth and shown(node, depth)
        if visible:
            chapter = next((n for n, a, b in spans if a <= here <= b), current[0])
            current[0] = chapter
            returned = re.sub(r" object at 0x[0-9a-f]+", "", node.get("returned", ""))  # addresses change every run
            src = files.get(node["file"])
            items.append({"kind": "step", "fn": node["fn"] + (f" ×{node['repeat']}" if "repeat" in node else ""), "file": node["file"], "line": node["line"],
                          "end": function_end(src, node["line"]) if src else node["line"], "depth": depth,
                          "returned": returned, "chapter": chapter})
        # this function's decisions and its calls, interleaved in the order they happen
        events = []
        if visible and node["file"] in files:
            for d in decisions(files[node["file"]], node["line"], ran_lines.get(node["file"], set())):
                events.append((d["line"], 0, d))
        for i, child in enumerate(node["calls"]):
            at = int(str(child.get("called_from") or ":0").rsplit(":", 1)[-1] or 0)
            events.append((at, 1, i))
        order = sorted(range(len(events)), key=lambda k: (events[k][0], events[k][1], k))
        pending_children = [e for e in events if e[1] == 1]
        for k in order:
            at, kind, what = events[k]
            if kind == 0:
                items.append({**what, "file": node["file"], "chapter": current[0]})
            else:
                walk(node["calls"][what], depth + 1)
        if "returned" in node or "raised" in node:
            line += 1
        if depth == 1:
            value = re.sub(r" object at 0x[0-9a-f]+", "", node.get("returned", ""))
            if value and value != "None":
                items.append({"kind": "data", "label": value, "chapter": current[0]})

    walk(tree, 0)
    last = next((i["label"] for i in reversed(items) if i["kind"] == "data"), "the result")
    items.append({"kind": "end", "label": "The caller holds " + last, "chapter": None})
    return items


def function_end(source: str, first: int) -> int:
    """Last line of the function or class defined at line `first` (Python only; else just that line)."""
    try:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                if first in (start, node.lineno):
                    return node.end_lineno or first
    except SyntaxError:
        pass
    return first


def build(story: Path) -> str:
    outline = json.loads((story / "outline.json").read_text())
    repo, info = repo_path(outline), outline["repo"]
    chapters = []
    for c in outline["chapters"]:
        found = sorted(story.glob(f"{c['n']:02}-*.md"))
        chapters.append({"n": c["n"], "title": c["title"], "data_in": c["data_in"], "data_out": c["data_out"],
                         "span": c["trace_lines"], "md": found[0].read_text() if found else None})

    link_re = re.compile(re.escape(info["url"]) + r"/blob/[0-9a-f]+/([^\s#)]+)#L\d+")
    trace = json.loads((story / "trace.json").read_text())
    traced, stack = set(), [trace]
    while stack:
        node = stack.pop()
        traced.add(node["file"])
        stack += node["calls"]
    wanted = traced | {m for ch in chapters if ch["md"] for m in link_re.findall(ch["md"])}
    files = {}
    for path in sorted(wanted):
        try:
            files[path] = git(repo, "show", f"{info['commit']}:{path}")
        except Exception:
            continue  # the scenario file, or a path that isn't in the repo
    items = flow(story, outline, files)

    data = {"title": outline["title"], "premise": outline["premise"], "reader": outline.get("reader", ""),
            "repo": {"name": info["name"], "url": info["url"], "commit": info["commit"]},
            "chapters": chapters, "flow": items, "files": files}
    payload = json.dumps(data).replace("</", "<\\/")
    name = outline["title"].split(":")[0].strip()  # the tab shows the story's name, not its subtitle
    return TEMPLATE.replace("__TITLE__", html.escape(name)).replace("__DATA__", payload)


TEMPLATE = r"""<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a reading desk. The journey map pinned left, the story in the middle, the source open on the right. */
:root {
  --paper: #f5f6f8; --sheet: #ffffff; --ink: #1c2230; --muted: #5d6679; --rule: #dde1e8;
  --route: #2f4db3; --route-soft: #e6ebfa; --mark: #fff0bf; --mark-edge: #e3b93a; --faint: #9aa2b1;
  --serif: "Newsreader", Georgia, "Times New Roman", serif;
  --sans: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --paper: #12151c; --sheet: #181c25; --ink: #e4e7ee; --muted: #9ba3b4; --rule: #2a303c;
  --route: #8ea4ff; --route-soft: #202a47; --mark: #3b3219; --mark-edge: #b8902a; --faint: #5f6878; color-scheme: dark } }
:root[data-theme="dark"] {
  --paper: #12151c; --sheet: #181c25; --ink: #e4e7ee; --muted: #9ba3b4; --rule: #2a303c;
  --route: #8ea4ff; --route-soft: #202a47; --mark: #3b3219; --mark-edge: #b8902a; --faint: #5f6878; color-scheme: dark }

* { box-sizing: border-box }
body { background: var(--paper); color: var(--ink); font: 15px/1.5 var(--sans); padding-inline: 16px; padding-block: 0 }
a { color: var(--route) }
button { font: inherit; color: inherit }
:focus-visible { outline: 2px solid var(--route); outline-offset: 2px }

header.top { max-width: 1480px; margin: 0 auto; padding-block: 28px 20px; display: grid; gap: 8px; border-bottom: 1px solid var(--rule) }
.eyebrow { font: 500 12px/1.2 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted) }
h1 { font: 600 clamp(28px, 4vw, 40px)/1.1 var(--serif); margin: 0; text-wrap: balance }
.premise { font: 17px/1.55 var(--serif); color: var(--muted); max-width: 72ch; margin: 0 }

.desk { max-width: 1480px; margin: 0 auto; display: grid; grid-template-columns: 380px minmax(0, 1fr) minmax(0, 440px); gap: 28px; align-items: start; padding-block: 20px 80px }

/* The flowchart */
.map { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 12px); max-height: calc(100vh - 24px); overflow: auto; padding-right: 4px }
.map h2 { font: 600 12px/1.2 var(--sans); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 4px 0 4px }
.legend { font: 11px/1.4 var(--sans); color: var(--muted); margin: 0 0 8px }
#chart { display: block; width: 100%; max-width: 380px; height: auto }
#chart text { font-family: var(--mono); font-size: 10.5px; fill: var(--ink) }
#chart .band rect { fill: transparent; stroke: none }
#chart .band.active rect { fill: var(--route-soft) }
#chart .band text { font: 600 11px var(--sans); fill: var(--muted) }
#chart .band.active text { fill: var(--route) }
#chart .band.unwritten text { fill: var(--faint) }
#chart .node { cursor: pointer }
#chart .node .shape { fill: var(--sheet); stroke: var(--ink); stroke-width: 1.2 }
#chart .node:hover .shape, #chart .node:focus .shape { stroke: var(--route); stroke-width: 2 }
#chart .node.data .shape { fill: var(--route-soft); stroke: var(--route) }
#chart .node.term .shape { fill: var(--ink); stroke: var(--ink) }
#chart .node.term text { fill: var(--sheet) }
#chart .val { fill: var(--muted) }
#chart .wire { stroke: var(--ink); stroke-width: 1.2; fill: none }
#chart .road { stroke: var(--faint); stroke-width: 1.1; stroke-dasharray: 4 3; fill: none }
#chart .exit rect { fill: none; stroke: var(--faint); stroke-dasharray: 4 3 }
#chart .exit text, #chart .ans.side { fill: var(--muted) }
#chart .ans { font-family: var(--sans); font-size: 10.5px; font-weight: 600 }
#chart marker path { fill: var(--ink) }
#chart marker#dash path { fill: var(--faint) }

/* The story */
.story { min-width: 0 }
.chapter { background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 26px clamp(18px, 4vw, 44px) 30px; margin-bottom: 22px; scroll-margin-top: 16px }
.chapter .prose { max-width: 66ch; font: 18px/1.62 var(--serif) }
.chapter h1 { font-size: 28px; margin-bottom: 14px }
.chapter h2, .chapter h3 { font: 600 20px/1.3 var(--serif); margin: 28px 0 8px }
.chapter p { margin: 0 0 14px }
.chapter p.active { box-shadow: -14px 0 0 -11px var(--mark-edge) }
.chapter code { font: .82em var(--mono); background: var(--paper); padding: 1px 4px; border-radius: 3px; overflow-wrap: anywhere }
.chapter pre { font: 13px/1.5 var(--mono); background: var(--paper); padding: 12px; border-radius: 6px; overflow-x: auto }
.chapter pre code { background: none; padding: 0 }
.chapter blockquote { margin: 0 0 18px; padding: 10px 14px; border-left: 3px solid var(--route); background: var(--route-soft); font: 14px/1.5 var(--sans); border-radius: 0 6px 6px 0; overflow-wrap: anywhere }
.chapter blockquote p { margin: 0 }
.chapter blockquote.aside { border-left-color: var(--mark-edge); background: var(--mark); font: 16px/1.55 var(--serif); padding: 12px 16px }
.chapter blockquote.aside strong:first-child { display: block; font: 600 11px/1.2 var(--sans); letter-spacing: .06em; text-transform: uppercase; color: var(--ink); margin-bottom: 4px }
.chapter table { border-collapse: collapse; font: 14px/1.4 var(--sans); display: block; overflow-x: auto }
.chapter td, .chapter th { border-bottom: 1px solid var(--rule); padding: 6px 10px; text-align: left; vertical-align: top }
a.cite { text-decoration: none; border-bottom: 1.5px solid var(--mark-edge); color: inherit; cursor: pointer }
a.cite:hover, a.cite.on { background: var(--mark) }
.pending { color: var(--muted); font: 15px/1.5 var(--sans) }
.pending .io { font: 13px/1.5 var(--mono); overflow-wrap: anywhere; margin-top: 8px }

/* The code */
.code { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 12px); background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; display: grid; grid-template-rows: auto minmax(0, 1fr); max-height: calc(100vh - 24px); min-width: 0 }
.code-head { display: flex; gap: 10px; align-items: baseline; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--rule); font: 12.5px/1.3 var(--mono); min-width: 0 }
.code-head .where { overflow-wrap: anywhere }
.code-head .close { display: none; background: none; border: 1px solid var(--rule); border-radius: 4px; padding: 2px 8px; cursor: pointer }
.code-body { overflow: auto; font: 12.5px/1.55 var(--mono); padding-block: 8px }
.ln { display: grid; grid-template-columns: 3.2em 1fr; white-space: pre; padding-right: 14px }
.ln span:first-child { color: var(--faint); text-align: right; padding-right: 12px; user-select: none; font-variant-numeric: tabular-nums }
.ln.hl { background: var(--mark) }
.ln.hl span:first-child { color: var(--ink) }
.code-empty { padding: 16px; color: var(--muted); font: 14px/1.5 var(--sans) }

@media (max-width: 1360px) {
  .desk { grid-template-columns: 340px minmax(0, 1fr) }
  .code { position: fixed; left: 12px; right: 12px; bottom: calc(env(safe-area-inset-bottom, 0px) + 12px); top: auto; max-height: 46vh; z-index: 5; box-shadow: 0 10px 40px rgba(0,0,0,.25) }
  .code:not(.open) { display: none }
  .code-head .close { display: inline-block }
}
@media (max-width: 760px) {
  .desk { grid-template-columns: minmax(0, 1fr) }
  .map { position: static; max-height: none }
  .chapter .prose { font-size: 17px }
}
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth } }
</style>

<header class="top">
  <div class="eyebrow" id="meta"></div>
  <h1 id="title"></h1>
  <p class="premise" id="premise"></p>
</header>
<div class="desk">
  <nav class="map" aria-label="Control flow"><h2>Control flow of this run</h2><p class="legend">Boxes are calls, diamonds are decisions, dashed exits are roads not taken. Click anything to see its code.</p><svg id="chart" role="img" aria-label="Flowchart of the data's path through the code"></svg></nav>
  <main class="story" id="story"></main>
  <aside class="code" id="code" aria-label="Source code">
    <div class="code-head"><span class="where" id="where">Source</span><span><a id="gh" target="_blank" rel="noopener">GitHub ↗</a> <button class="close" id="close">Close</button></span></div>
    <div class="code-body" id="codebody"><div class="code-empty">Click an underlined phrase in the story, or a step on the map, to see its code here.</div></div>
  </aside>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script type="application/json" id="data">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const short = (s, n) => s.length > n ? s.slice(0, n - 1) + "…" : s;
const permalink = (path, a, b) => `${D.repo.url}/blob/${D.repo.commit}/${path}#L${a}` + (b && b !== a ? `-L${b}` : "");

$("meta").textContent = `${D.repo.name} @ ${D.repo.commit.slice(0, 7)} · written for the ${D.reader}`;
$("title").textContent = D.title;
$("premise").innerHTML = marked.parseInline(D.premise);

// ---- flowchart: laid out top to bottom on one spine; roads not taken exit to the right
const NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.append(e); return e; };
function wrap(text, width) {  // monospace, so characters are a fair measure
  const out = []; let line = "";
  for (let word of String(text).split(/(?<=[ .,(])/)) {
    if ((line + word).length > width && line) { out.push(line.trimEnd()); line = ""; }
    while (word.length > width && !line) { out.push(word.slice(0, width)); word = word.slice(width); }
    line += word;
  }
  if (line) out.push(line.trimEnd());
  return out;
}
const svg = $("chart");
const CX = 112, BOX = 210, SIDE_X = 240, SIDE_W = 136, GAP = 26;
const bandOf = {}; let y = 10, prevBottom = null, prevChapter = undefined;
const defs = el("defs", {}, svg);
for (const [id, cls] of [["arrow", ""], ["dash", ""]]) {
  const m = el("marker", { id, viewBox: "0 0 8 8", refX: 7, refY: 4, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, defs);
  el("path", { d: "M0,0 L8,4 L0,8 z" }, m);
}
const bandsLayer = el("g", {}, svg), wires = el("g", {}, svg), nodes = el("g", {}, svg);
const chapterTitle = Object.fromEntries(D.chapters.map((c) => [c.n, c]));
function textLines(g, lines, x, y0, anchor, cls) {
  lines.forEach((t, i) => { const e = el("text", { x, y: y0 + i * 13, "text-anchor": anchor }, g); if (cls) e.setAttribute("class", cls); e.textContent = t; });
}
function connect(fromY, toY, label) {
  el("line", { x1: CX, y1: fromY, x2: CX, y2: toY - 1, class: "wire", "marker-end": "url(#arrow)" }, wires);
  if (label) { const t = el("text", { x: CX + 6, y: fromY + 14, class: "ans" }, wires); t.textContent = label; }
}
let pendingLabel = null;
for (const it of D.flow) {
  if (it.chapter !== prevChapter && it.chapter != null) {  // a chapter starts: open its band
    y += prevBottom == null ? 0 : 8;
    bandOf[it.chapter] = { top: y, bottom: y };
    y += 20;
  }
  if (it.chapter != null) prevChapter = it.chapter;
  const top = y + (prevBottom == null ? 0 : GAP);
  const g = el("g", { class: "node", tabindex: 0 }, nodes);
  let h;
  if (it.kind === "start" || it.kind === "end") {
    const lines = wrap(it.label, 30); h = 14 + lines.length * 13;
    g.classList.add("term");
    el("rect", { x: CX - BOX / 2, y: top, width: BOX, height: h, rx: h / 2, class: "shape" }, g);
    textLines(g, lines, CX, top + 17, "middle");
  } else if (it.kind === "data") {
    const lines = wrap(it.label, 28).slice(0, 3); h = 14 + lines.length * 13;
    g.classList.add("data");
    const k = 10;
    el("path", { d: `M${CX - BOX / 2 + k},${top} H${CX + BOX / 2} L${CX + BOX / 2 - k},${top + h} H${CX - BOX / 2} Z`, class: "shape" }, g);
    textLines(g, lines, CX, top + 17, "middle");
    g.onclick = () => {};
  } else if (it.kind === "step") {
    const name = it.fn.length > 28 && it.fn.includes(".") ? [it.fn.slice(0, it.fn.lastIndexOf(".")), it.fn.slice(it.fn.lastIndexOf("."))] : wrap(it.fn, 28);
    const val = it.returned && it.returned !== "None" ? ["→ " + (it.returned.length > 26 ? it.returned.slice(0, 25) + "…" : it.returned)] : [];
    h = 12 + (name.length + val.length) * 13;
    el("rect", { x: CX - BOX / 2, y: top, width: BOX, height: h, rx: 3, class: "shape" }, g);
    textLines(g, name, CX, top + 16, "middle");
    textLines(g, val, CX, top + 16 + name.length * 13, "middle", "val");
    const title = el("title", {}, g); title.textContent = `${it.fn}  (${it.file}:${it.line})` + (it.returned ? `\nreturns ${it.returned}` : "");
    g.onclick = () => { showCode(it.file, it.line, it.end); if (it.chapter) $("ch-" + it.chapter).scrollIntoView(); };
  } else {  // decision
    let lines = wrap(it.question, 16);
    if (lines.length > 3) lines = [...lines.slice(0, 2), lines[2].slice(0, 15) + "…"];
    h = 34 + lines.length * 13;
    const hw = 100;
    el("path", { d: `M${CX},${top} L${CX + hw},${top + h / 2} L${CX},${top + h} L${CX - hw},${top + h / 2} Z`, class: "shape" }, g);
    textLines(g, lines, CX, top + h / 2 - (lines.length - 1) * 6 + 4, "middle");
    // the road not taken
    const ex = el("g", { class: "exit" }, g);
    const exitLines = wrap(it.exit, 20).slice(0, 3);
    const eh = 10 + exitLines.length * 13, ey = top + h / 2 - eh / 2;
    el("path", { d: `M${CX + hw},${top + h / 2} H${SIDE_X - 1}`, class: "road", "marker-end": "url(#dash)" }, ex);
    const sa = el("text", { x: CX + hw + 5, y: top + h / 2 - 5, class: "ans side" }, ex); sa.textContent = it.side;
    el("rect", { x: SIDE_X, y: ey, width: SIDE_W, height: eh, rx: 3 }, ex);
    textLines(ex, exitLines, SIDE_X + 6, ey + 15, "start");
    sa.setAttribute("x", CX + hw + 3);
    const title = el("title", {}, g); title.textContent = `${it.question}\ntaken: ${it.answer}\notherwise (${it.side}): ${it.exit}\n${it.file}:${it.line}`;
    g.onclick = () => { showCode(it.file, it.line, it.end); if (it.chapter) $("ch-" + it.chapter).scrollIntoView(); };
  }
  if (prevBottom != null) connect(prevBottom, top, pendingLabel);
  pendingLabel = it.kind === "decision" ? it.answer : null;
  if (pendingLabel && pendingLabel.length > 18) pendingLabel = pendingLabel.slice(0, 17) + "…";
  prevBottom = top + h; y = prevBottom;
  if (it.chapter != null && bandOf[it.chapter]) bandOf[it.chapter].bottom = y;
}
y += 12;
for (const [n, b] of Object.entries(bandOf)) {
  const ch = chapterTitle[n];
  const g = el("g", { class: "band" + (ch && ch.md ? "" : " unwritten"), id: "band-" + n }, bandsLayer);
  el("rect", { x: 0, y: b.top, width: 380, height: b.bottom - b.top + 8, rx: 6 }, g);
  const t = el("text", { x: 6, y: b.top + 14 }, g);
  t.textContent = `${n} · ${ch ? (ch.title.length > 48 ? ch.title.slice(0, 47) + "…" : ch.title) : ""}`;
  g.style.cursor = "pointer";
  g.onclick = () => $("ch-" + n).scrollIntoView();
}
svg.setAttribute("viewBox", `0 0 380 ${y}`);
svg.setAttribute("height", y);

// ---- story
const story = $("story");
const cite = new RegExp(D.repo.url.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "/blob/[0-9a-f]+/([^#]+)#L(\\d+)(?:-L(\\d+))?");
for (const ch of D.chapters) {
  const sec = document.createElement("section");
  sec.className = "chapter"; sec.id = "ch-" + ch.n; sec.dataset.n = ch.n;
  const prose = document.createElement("div"); prose.className = "prose";
  if (ch.md) {
    prose.innerHTML = marked.parse(ch.md);
    for (const q of prose.querySelectorAll("blockquote")) {  // "**For the owner:** …" callouts
      const lead = q.querySelector("p > strong:first-child");
      if (lead && /^for the /i.test(lead.textContent)) q.classList.add("aside");
    }
    for (const a of prose.querySelectorAll("a[href]")) {
      const m = a.getAttribute("href").match(cite);
      if (!m) { a.target = "_blank"; a.rel = "noopener"; continue; }
      a.className = "cite";
      a.dataset.path = m[1]; a.dataset.a = m[2]; a.dataset.b = m[3] || m[2];
      a.onclick = (e) => { e.preventDefault(); pick(a, true); };
    }
  } else {
    prose.innerHTML = `<h1></h1><div class="pending">This chapter is planned but not written yet.<div class="io"></div></div>`;
    prose.querySelector("h1").textContent = `Chapter ${ch.n} · ${ch.title}`;
    prose.querySelector(".io").textContent = `enters as ${ch.data_in}\nleaves as ${ch.data_out}`;
  }
  sec.append(prose);
  story.append(sec);
}

// ---- code panel
const panel = $("code");
let pinned = null;
function showCode(path, a, b) {
  a = +a; b = +b;
  const src = D.files[path];
  $("where").textContent = `${path}:${a}${b !== a ? "-" + b : ""}`;
  $("gh").href = permalink(path, a, b);
  const body = $("codebody");
  body.textContent = "";
  if (src === undefined) { body.innerHTML = '<div class="code-empty">This file is not part of the repository snapshot.</div>'; return; }
  const frag = document.createDocumentFragment();
  src.split("\n").forEach((text, i) => {
    const row = document.createElement("div");
    row.className = "ln" + (i + 1 >= a && i + 1 <= b ? " hl" : "");
    const n = document.createElement("span"); n.textContent = i + 1;
    const t = document.createElement("span"); t.textContent = text || " ";
    row.append(n, t); frag.append(row);
  });
  body.append(frag);
  const first = body.children[Math.max(0, a - 1)];
  if (first) body.scrollTop += first.getBoundingClientRect().top - body.getBoundingClientRect().top - body.clientHeight * 0.3;
  panel.classList.add("open");
}
function pick(a, byClick) {
  document.querySelectorAll("a.cite.on").forEach((x) => x.classList.remove("on"));
  a.classList.add("on");
  if (byClick) pinned = a.closest("p, li, td, blockquote");
  showCode(a.dataset.path, a.dataset.a, a.dataset.b);
}
$("close").onclick = () => panel.classList.remove("open");

// ---- follow the reader: current chapter on the map, current paragraph's code on the right
const wide = () => window.matchMedia("(min-width: 1361px)").matches;
let current = null, activePara = null;
function follow() {
  const mid = window.innerHeight * 0.4;
  let sec = null;
  for (const s of document.querySelectorAll(".chapter")) { const r = s.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid) sec = s; }
  if (sec && sec.dataset.n !== current) {
    current = sec.dataset.n;
    document.querySelectorAll(".band.active").forEach((b) => b.classList.remove("active"));
    const band = $("band-" + current);
    if (band) {
      band.classList.add("active");
      const map = document.querySelector(".map");
      if (window.matchMedia("(min-width: 761px)").matches) {
        const r = band.getBoundingClientRect(), m = map.getBoundingClientRect();
        if (r.top < m.top || r.top > m.bottom - 80) map.scrollTop += r.top - m.top - 40;
      }
    }
  }
  if (!wide()) return;  // on narrow screens the code opens only when asked
  let para = null;
  for (const p of document.querySelectorAll(".chapter p")) {
    if (!p.querySelector("a.cite")) continue;
    const r = p.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid - 40) { para = p; break; }
  }
  if (para && para !== activePara) {
    if (activePara) activePara.classList.remove("active");
    activePara = para; para.classList.add("active");
    if (pinned !== para) { pinned = null; pick(para.querySelector("a.cite"), false); }
  }
}
let ticking = false;
addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; follow(); }); } }, { passive: true });
addEventListener("resize", follow);
follow();
if (wide()) { const first = document.querySelector("a.cite"); if (first && !activePara) pick(first, false); }
</script>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    story = Path(sys.argv[1])
    out = story / "index.html"
    out.write_text(build(story))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
