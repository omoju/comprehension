"""Plan the story of a change: chapters are spans of the before-and-after run, told for one reader.

    .venv/bin/python codestory/diff_outline.py <story-dir> [--reader reviewer] [--max-chapters N] [--repair]
                                               [--dry-run]

Needs changes.json, diff.txt and diff.json from diff.py. The repository explainer plans from one run; a change is
planned from two runs of the change's own tests, base and head, merged into one trace (diff.txt): `+` happens only
after the change, `-` only before, `~` is the same call with other values, ` *` marks a function the change edited.

Writes <story-dir>/outline.json (mode "diff"). Checks, beyond the repository planner's spans and question threads:
every chapter covers some change; every changed function the run reaches is explained by a chapter; every test that
fails before and passes after is claimed as a chapter's evidence; and every changed function the run never reaches
is named as unexercised, so the story can't pass over what it has no evidence for. A plan that fails goes back to
the model with the errors, in the same conversation, up to REPAIRS times. --dry-run writes the prompt only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import env  # noqa: F401  (loads .env)
import llm
from diff import repo_dir
from outline import CONTEXT_BUDGET, NOISE, READERS, REPAIRS, git, relative_to_root, thread_errors, usage_line
from style import check_summary, words

MAX_CHAPTERS = 5
DIFF_CONTEXT = 6  # lines of context around each hunk in the diff the model reads
DIFF_BUDGET = 800_000  # characters of diff; past it, tests and data go first (one PR's whole diff was 617k)

SYSTEM = """You plan code stories about a change. A code story explains code by following its data through a real
run, in close third person: the story stays with the data as it travels through the code. A change story runs the
change's own tests twice, on the code before the change (the base) and after it (the head), and follows the same
data through both versions. The protagonist is the input the tests hand in; the plot is what happens to it now
that did not happen before, and what still happens the same way where a reader might worry it broke.

You are given the change (its diff, and every changed file in full on both sides, with line numbers), the tests
and how each ended before and after, and the two runs merged into one numbered trace. In that trace a line that
starts with `+` happens only after the change, `-` only before it, and `~` is the same call with other arguments or
another result (its `before` lines show the old values); a line ending in ` *` is a call to a function the change
edited. Unchanged stretches are folded into "… N unchanged calls". Each test's section starts with a `##` line that
says how it ended before and after.

The formula: each chapter is a function. A chapter covers one contiguous span of the trace and explains one
difference the data meets: kind "changed" for behaviour the change makes different, kind "preserved" for behaviour
it keeps where the reader would reasonably worry (a chapter of either kind must cover at least one marked line).
`before` and `after` say what the data experiences on each side, in one short sentence each (at most 25 words), with
the real values from the trace. Order the chapters by what the reader needs first: the heart of the change, then its
edge cases, then what stays the same (spans may come in any order, but must not overlap). Use as few chapters as the
change needs for this reader, within the budget: a small fix may need two. Repetition (the same difference in
several tests) is told once. Chapter titles are plain-language claims a reader can take in at a glance ("A third
read of the same photo is turned away"), not function names.

The evidence must be accounted for:
- Every changed function the run reaches is explained by some chapter: list its name, exactly as in the change
  list, in that chapter's `changed_functions`.
- Every test that fails (or never finishes) before and passes after is evidence for the change: list its title,
  exactly as given, in the `tests` of the chapter that explains it.
- Every changed function the run never reaches goes in `unexercised`, with what the reader should check by hand.
  The run says nothing about those functions, so the chapters must not pretend it does. A file's changes outside
  any function (named "<path> (outside functions)" in the change list) may go there too, when they matter.

`premise` is the stakes, as a concrete situation in the world, in at most 70 words: who meets this code, with what,
and what went wrong (or was missing) for them before the change. Take it from the pull request's description when
it says. `verdict` is at most 70 words for the reader: what the change makes true, the evidence in one phrase, and
the risk that remains. Both are prose for a person, not a list of functions.
Characters are real things in the code the data meets. Facts are claims a reader can check against the code or the
trace. Open questions are what the data or the reader wonders about that a later chapter answers; give each an id
like "q2.1" (chapter 2, question 1); every question is answered by exactly one later chapter, which lists the id in
its "answers". The story is for one particular reader, given with the request: what they care about decides where
it slows down."""

QUESTION = {"type": "object", "properties": {"id": {"type": "string"}, "question": {"type": "string"}},
            "required": ["id", "question"], "additionalProperties": False}
ANSWER = {"type": "object", "properties": {"id": {"type": "string"}, "answer": {"type": "string"}},
          "required": ["id", "answer"], "additionalProperties": False}
STRINGS = {"type": "array", "items": {"type": "string"}}

DIFF_OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "premise": {"type": "string", "description": "What was wrong or missing before the change, as the opening situation."},
        "verdict": {"type": "string"},
        "chapters": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "n": {"type": "integer"},
                "title": {"type": "string"},
                "trace_lines": {"type": "array", "items": {"type": "integer"},
                                "description": "[first, last] line numbers of the trace this chapter covers"},
                "kind": {"type": "string", "enum": ["changed", "preserved"]},
                "before": {"type": "string", "description": "what the data experiences on the base, from the trace"},
                "after": {"type": "string", "description": "what the data experiences on the head, from the trace"},
                "changed_functions": STRINGS,
                "tests": STRINGS,
                "code": {"type": "array", "items": {"type": "string"}, "description": "path or path:start-end"},
                "characters": STRINGS,
                "facts": STRINGS,
                "open_questions": {"type": "array", "items": QUESTION},
                "answers": {"type": "array", "items": ANSWER},
            },
            "required": ["n", "title", "trace_lines", "kind", "before", "after", "changed_functions", "tests", "code",
                         "characters", "facts", "open_questions", "answers"],
            "additionalProperties": False,
        }},
        "unexercised": {"type": "array", "items": {
            "type": "object",
            "properties": {"function": {"type": "string"}, "check": {"type": "string"}},
            "required": ["function", "check"], "additionalProperties": False}},
    },
    "required": ["title", "premise", "verdict", "chapters", "unexercised"],
    "additionalProperties": False,
}

MARKED = re.compile(r"^[+\-~]| \*$")


def outside(path: str) -> str:
    """The name a file's changes outside any function go by, in the change list and in `unexercised`."""
    return f"{path} (outside functions)"


def load(story: Path) -> tuple[dict, list[str], dict]:
    changes = json.loads((story / "changes.json").read_text())
    trace = (story / "diff.txt").read_text().splitlines()
    summary = json.loads((story / "diff.json").read_text())
    return changes, trace, summary


def numbered(lines: list[str]) -> str:
    return "\n".join(f"{i:4}  {line}" for i, line in enumerate(lines, 1))


TRACE_BUDGET = 400_000  # characters of trace shown; enough to keep every difference of a 14.6k-line trace
LINE_MAX = 240  # a line that differs
CONTEXT_LINE_MAX = 140  # a line that leads to one, or a call that's the same on both sides
CALL = re.compile(r"^.\s*([A-Za-z_$][\w$.]*)\(")
RESULT = re.compile(r"^.\s*(before )?→")


def changed_names(changes: dict) -> set[str]:
    return {f["name"] for c in changes["files"].values() for f in c["functions"]}


def trace_view(trace: list[str], budget: int = TRACE_BUDGET, lo: int = 1, hi: int | None = None,
               focus: set[str] = frozenset()) -> str:
    """Lines lo..hi of the merged trace as the model sees them, numbered as in the trace. Within the budget they are
    shown whole. A change that adds a feature can trace thousands of new calls (one gave 1.9M characters, past the
    model's context), so a bigger trace is folded, losing as little of the change as it can:

    - A call whose whole subtree repeats an earlier one, word for word, becomes a pointer to the first (lossless).
    - Then lines are kept in this order until the budget is spent: the tests; every line that differs (`~`, `-`)
      with the calls that lead to it; the first call of each function in `focus` (the changed functions); the
      results of those calls; then the rest, shallowest first. Long lines are clipped.
    - Each run of lines left out becomes one ⋮ line naming the lines it stands for, how many differ, and the
      functions called in it, so a chapter's span can still take them in."""
    hi = hi or len(trace)
    whole = "\n".join(f"{i:4}  {trace[i - 1]}" for i in range(lo, hi + 1))
    if len(whole) <= budget:
        return whole
    lines = range(lo - 1, hi)  # 0-based from here on

    def indent(line: str) -> int:
        return len(line) - 1 - len(line[1:].lstrip(" ")) if line and line[0] != "#" else 0

    ind = {i: indent(trace[i]) for i in lines}
    structural = {i for i in lines if not trace[i].strip() or trace[i].startswith("#") or ind[i] <= 1}
    end, parent, stack = {}, {}, []
    for i in lines:
        while stack and (i in structural or ind[i] <= ind[stack[-1]]):
            end[stack.pop()] = i - 1
        parent[i] = stack[-1] if stack else None
        if i not in structural:
            stack.append(i)
    for i in stack:
        end[i] = hi - 1

    repeats, covered, seen = {}, set(), {}  # repeats: root -> (first, its end)
    i = lo - 1
    while i < hi:
        if i not in structural and end[i] > i:
            key = "\n".join(x[0] + x[1 + ind[i]:] for x in trace[i:end[i] + 1])
            if key in seen:
                repeats[i] = seen[key]
                covered.update(range(i, end[i] + 1))
                i = end[i] + 1
                continue
            seen[key] = (i, end[i])
        i += 1

    def results(i: int) -> list[int]:
        return [j for j in range(i + 1, end.get(i, i) + 1) if ind[j] == ind[i] + 2 and RESULT.match(trace[j])]

    order, first, short = [], set(), {f.split(".")[-1] for f in focus}
    order += [(0, 0, i) for i in structural]
    for i in lines:
        name = (m := CALL.match(trace[i])) and m.group(1)
        if name and i not in covered and name not in first and (name in focus or name.split(".")[-1] in short):
            first.add(name)
            order.append((1, ind[i], i))
    order += [(2, ind[i], i) for i in lines if i not in covered and trace[i][:1] in "~-" and i not in structural]
    order += [(3, ind[i], i) for i in lines if i not in covered and i not in structural]
    order.sort()

    def keep(k: int) -> set[int]:
        kept = set()
        for tier, _, i in order[:k]:
            todo = [i] + (results(i) if tier == 1 else [])
            while todo:
                j = todo.pop()
                if j is not None and j not in kept:
                    kept.add(j)
                    todo.append(parent.get(j))
        return kept

    def render(kept: set[int]) -> list[str]:
        out, run = [], []

        def flush() -> None:
            if run:
                calls = list(dict.fromkeys(m.group(1) for j in run if (m := CALL.match(trace[j]))))
                marked = sum(1 for j in run if MARKED.search(trace[j]))
                names = ", ".join(calls[:3]) + (f" +{len(calls) - 3}" if len(calls) > 3 else "")
                out.append(f"      ⋮ {run[0] + 1}-{run[-1] + 1}" + (f", {marked} marked" if marked else "")
                           + (f": {names}" if names and len(run) > 2 else ""))
                run.clear()
        i = lo - 1
        while i < hi:
            if i in kept:
                flush()
                most = LINE_MAX if MARKED.search(trace[i]) else CONTEXT_LINE_MAX
                out.append(f"{i + 1:4}  {trace[i] if len(trace[i]) <= most else trace[i][:most] + ' …'}")
                i += 1
            elif i in repeats:  # a repeat is its own ⋮ line, pointing at the first
                flush()
                f, e = repeats[i]
                name = (m := CALL.match(trace[i])) and m.group(1)
                out.append(f"      ⋮ {i + 1}-{end[i] + 1}{f' {name}' if name else ''}: same as {f + 1}-{e + 1}")
                i = end[i] + 1
            else:
                run.append(i)
                i += 1
        flush()
        return out

    size = lambda rendered: sum(len(x) + 1 for x in rendered)  # noqa: E731
    low, high = 0, len(order)
    while low < high:  # the most lines, in order, that fit
        mid = (low + high + 1) // 2
        if size(render(keep(mid))) <= budget:
            low = mid
        else:
            high = mid - 1
    kept = keep(low)
    out = render(kept)
    differ = [i for i in lines if trace[i][:1] in "~-"]
    seen_diff = sum(1 for i in differ if i in kept or i in covered)
    return "\n".join(out) + (
        f"\n      (folded to fit: {len(whole):,} characters in full; {len(kept):,} of {len(lines):,} lines shown, "
        f"{len(covered):,} are repeats of shown lines; {seen_diff:,} of the {len(differ):,} lines that differ are "
        "shown or repeated. \"⋮ a-b\" stands for trace lines a to b, not shown (with how many differ and what they "
        "call); "
        "\"same as c-d\" means they repeat lines c to d word for word. A span can include them.)")


def change_info(changes: dict) -> dict:
    repo = repo_dir(changes)
    url = re.sub(r"^git@github\.com:", "https://github.com/", git(repo, "remote", "get-url", "origin")).removesuffix(".git")
    return {"name": url.split("github.com/")[-1], "url": url, "base": changes["base"], "head": changes["head"],
            "commit": changes["head"], "local_path": relative_to_root(repo), "pkg": changes["pkg"],
            "title": changes.get("title", ""), "number": changes.get("number")}


def changed_paths(changes: dict) -> list[str]:
    """Every file the change touches in the package (code, specs, config), minus generated noise."""
    repo = repo_dir(changes)
    paths = git(repo, "diff", "--name-only", changes["base"], changes["head"], "--", changes["pkg"]).splitlines()
    return [p for p in paths if not NOISE.search(p)]


def traced_paths(story: Path) -> set[str]:
    found = set()
    for side in ("base", "head"):
        f = story / f"trace.{side}.json"
        if f.exists():
            stack = [json.loads(f.read_text())]
            while stack:
                n = stack.pop()
                found.add(n["file"])
                stack += n["calls"]
    return found


def budgeted_diff(repo: Path, base: str, head: str, paths: list[str]) -> str:
    """The change's diff, whole within DIFF_BUDGET. Past it, files are kept code first, then tests, then data and
    docs, and the ones left out are named with their size, so the plan can still list what they change."""
    if not paths:
        return ""
    diff = git(repo, "diff", f"-U{DIFF_CONTEXT}", "--no-color", base, head, "--", *paths)
    if len(diff) <= DIFF_BUDGET:
        return diff
    files = re.split(r"\n(?=diff --git )", diff)
    path = lambda f: f.split("\n", 1)[0].rsplit(" b/", 1)[-1]  # noqa: E731
    rank = lambda f: (bool(re.search(r"\.(spec|test)\.\w+$", path(f))),  # noqa: E731
                      not re.search(r"\.([cm]?[jt]sx?|vue|py)$", path(f)))
    kept, left, used = set(), [], 0
    for i in sorted(range(len(files)), key=lambda i: rank(files[i])):
        if used + len(files[i]) <= DIFF_BUDGET:
            kept.add(i)
            used += len(files[i])
        else:
            left.append(f"{path(files[i])} ({files[i].count(chr(10))} lines of diff)")
    return "\n".join(files[i] for i in sorted(kept)) + (
        f"\n\n({len(left)} files' diffs not shown because of the budget: {', '.join(left)})" if left else "")


def change_block(story: Path, changes: dict, info: dict) -> dict:
    """The change as the model reads it, one cached block: the diff; every changed file in full on the head and
    the base (numbered, so links can cite either side); then the unchanged files the runs pass through."""
    repo = repo_dir(changes)
    base, head = changes["base"], changes["head"]
    paths = changed_paths(changes)
    diff = budgeted_diff(repo, base, head, paths)
    described = (story / "pr.md").read_text()[:6000] if (story / "pr.md").exists() else ""
    parts = [f"Repository: {info['name']} ({info['url']}), the change {base[:7]}..{head[:7]} in {changes['pkg']}/"
             + (f"\nPull request #{info['number']}: {info['title']}" if info.get("number") else "")
             + (f"\n<pull_request_description>\n{described}\n</pull_request_description>" if described else ""),
             f"<diff>\n{diff}\n</diff>"]
    used, skipped = sum(len(p) for p in parts), []

    def add(path: str, rev: str, side: str) -> None:
        nonlocal used
        try:
            text = git(repo, "show", f"{rev}:{path}")
        except Exception:
            return  # added or deleted on this side
        lines = "\n".join(f"{i:5}  {line}" for i, line in enumerate(text.splitlines(), 1))
        block = f'<file path="{path}" side="{side}" commit="{rev}">\n{lines}\n</file>'
        if used + len(block) > CONTEXT_BUDGET:
            skipped.append(f"{path} ({side})")
            return
        parts.append(block)
        used += len(block)

    for path in paths:
        add(path, head, "head")
    for path in paths:
        add(path, base, "base")
    for path in sorted(traced_paths(story) - set(paths)):
        if "/" in path:  # not the scenario root
            add(path, head, "head (unchanged)")
    if skipped:
        parts.append(f"({len(skipped)} files not shown because of the context budget: {', '.join(skipped)})")
    return {"type": "text", "text": "\n\n".join(parts), "cache_control": {"type": "ephemeral"}}


def evidence_block(changes: dict, summary: dict) -> str:
    """The change list, the tests' outcomes and what the run never reached, for the planner and the writers."""
    fn_lines = []
    for path, c in changes["files"].items():
        for f in c["functions"]:
            where = f"head {f['head'][0]}-{f['head'][1]}" if f["head"] else f"base {f['base'][0]}-{f['base'][1]}"
            fn_lines.append(f"- {f['name']}  ({f['kind']}, {path}, {where})")
        if c["module_level_lines"]:
            fn_lines.append(f"- {outside(path)}  (lines {c['module_level_lines']} on the head: declarations, settings "
                            "or a template, not in any function; the trace can't show them)")
    tests = [f"- {t['test']}  (before: {t['before']}, after: {t['after']})" for t in summary["tests"]]
    never = [f"- {c['function']}  ({c['kind']}, {c['file']})" for c in summary["coverage"] if not c["reached"]]
    return ("<changed_functions>\n" + "\n".join(fn_lines) + "\n</changed_functions>\n\n<tests>\n" + "\n".join(tests)
            + "\n</tests>\n\n<never_reached>\n" + ("\n".join(never) or "(none: the run reaches every changed function)")
            + "\n</never_reached>")


def spans_apart(chapters: list[dict], trace_len: int) -> list[str]:
    """Chapters numbered 1..k, spans well-formed and inside the trace, no two overlapping; any order (the reader's)."""
    errors = []
    if [c["n"] for c in chapters] != list(range(1, len(chapters) + 1)):
        errors.append(f"chapters are numbered {[c['n'] for c in chapters]}, not 1..{len(chapters)}")
    taken = []
    for c in chapters:
        span = c["trace_lines"]
        if len(span) != 2 or not (1 <= span[0] <= span[1] <= trace_len):
            errors.append(f"ch{c['n']} has a bad trace span {span} (trace has {trace_len} lines)")
            continue
        for n, a, b in taken:
            if span[0] <= b and a <= span[1]:
                errors.append(f"ch{c['n']}'s span {span} overlaps ch{n}'s [{a}, {b}]")
        taken.append((c["n"], span[0], span[1]))
    return errors


def check_diff_plan(plan: dict, trace: list[str], changes: dict, summary: dict, max_chapters: int) -> list[str]:
    """Everything code can decide about a change story's plan. Empty means it may flow on to the chapters."""
    chapters = plan["chapters"]
    errors = spans_apart(chapters, len(trace)) + thread_errors(chapters)
    errors += check_summary("premise", plan["premise"]) + check_summary("verdict", plan["verdict"])
    for c in chapters:
        for side in ("before", "after"):
            if words(c[side]) > 30:
                errors.append(f"ch{c['n']}'s {side} runs {words(c[side])} words; one short sentence, at most 25")
    if len(chapters) > max_chapters:
        errors.append(f"{len(chapters)} chapters, budget is {max_chapters}: merge the thinnest into their neighbours")
    known = {f["name"] for c in changes["files"].values() for f in c["functions"]}
    reached = {c["function"] for c in summary["coverage"] if c["reached"]}
    never = {c["function"] for c in summary["coverage"] if not c["reached"]}
    titles = {t["test"] for t in summary["tests"]}
    for c in chapters:
        span = c["trace_lines"]
        if len(span) == 2 and 1 <= span[0] <= span[1] <= len(trace) and \
                not any(MARKED.search(line) for line in trace[span[0] - 1:span[1]]):
            errors.append(f"ch{c['n']} (trace lines {span[0]}-{span[1]}) covers no marked line (+, -, ~ or *): "
                          "it shows no difference; fold it into a neighbour or move its span onto the change")
        errors += [f"ch{c['n']} lists changed function {f!r}, which is not in the change list" for f in
                   c["changed_functions"] if f not in known]
        errors += [f"ch{c['n']} lists test {t!r}, which is not one of the tests" for t in c["tests"] if t not in titles]
    explained = {f for c in chapters for f in c["changed_functions"]}
    errors += [f"changed function {f!r} is reached by the run but no chapter explains it (list it in a chapter's "
               "changed_functions)" for f in sorted(reached - explained)]
    claimed = {t for c in chapters for t in c["tests"]}
    errors += [f"test {t!r} fails before and passes after, but no chapter claims it as evidence"
               for t in summary["proofs"] if t not in claimed]
    listed = {u["function"] for u in plan["unexercised"]}
    errors += [f"{f!r} is never reached by the run: list it in unexercised" for f in sorted(never - listed)]
    outsides = {outside(p) for p, c in changes["files"].items() if c["module_level_lines"]}
    errors += [f"unexercised lists {f!r}, which the run does reach" for f in sorted((listed - never) & known)]
    errors += [f"unexercised lists {f!r}, which is neither a changed function nor a file's changes outside functions "
               "(use the names in the change list)" for f in sorted(listed - never - known - outsides)]
    return errors


def print_plan(plan: dict, reader: str, errors: list[str]) -> None:
    print(f"{plan['title']}  [{reader}]: {len(plan['chapters'])} chapters")
    for c in plan["chapters"]:
        print(f"  {c['n']:2}. {c['title']}  [{c['kind']}, trace {c['trace_lines'][0]}-{c['trace_lines'][-1]}]")
    for u in plan["unexercised"]:
        print(f"   unexercised: {u['function']}")
    for e in errors:
        print(f"  ! {e}")


def drop_written(story: Path) -> None:
    """Chapters belong to the plan that asked for them: a new plan discards the old chapters, their proofs, their
    model answers and the reports on them, or the chapter stage would keep them and repair them toward the new plan."""
    import shutil
    for f in story.glob("[0-9][0-9]-*.md"):
        f.unlink()
    for d in ("proofs", "traces"):
        shutil.rmtree(story / d, ignore_errors=True)
    for f in ("report.md", "verify.json", "story.json", "index.html", "proofs.base.json", "proofs.head.json"):
        (story / f).unlink(missing_ok=True)


def repair_request(errors: list[str]) -> str:
    return ("The plan failed these checks:\n" + "\n".join(f"- {e}" for e in errors)
            + "\n\nReturn the whole corrected plan, in the same format. Fix only what the checks name and whatever "
              "that forces (renumber chapters and question ids if chapters merge); keep the rest as it is.")


def main(story_arg: str, reader: str, max_chapters: int, repair: bool, dry_run: bool) -> int:
    story = Path(story_arg)
    changes, trace, summary = load(story)
    info = change_info(changes)
    profile = (READERS / f"{reader}.md").read_text()
    content = [change_block(story, changes, info), {"type": "text", "text": (
        f"{evidence_block(changes, summary)}\n\n<trace>\n{trace_view(trace, focus=changed_names(changes))}\n</trace>"
        f"\n\n<reader>\n{profile}\n</reader>"
        f"\n\nPlan the story of this change for this reader, in at most {max_chapters} chapters.")}]
    messages: list[dict] = [{"role": "user", "content": content}]

    if dry_run:
        (story / "outline.prompt.md").write_text(f"# system\n\n{SYSTEM}\n\n# user\n\n" + "\n\n".join(b["text"] for b in content))
        print(f"prompt written ({sum(len(b['text']) for b in content):,} characters)")
        return 0

    print(f"model: {llm.describe()}")
    replies = []

    def ask(name: str) -> dict:
        reply = llm.ask(SYSTEM, messages, schema=DIFF_OUTLINE_SCHEMA, max_tokens=64000)
        (story / f"outline.response{name}.json").write_text(json.dumps(reply.record(), indent=1))
        replies.append((name or "plan", reply))
        return json.loads(reply.text)

    if repair:  # the existing plan stands in for the model's first answer
        previous = json.loads((story / "outline.json").read_text())
        (story / "outline.prev.json").write_text(json.dumps(previous, indent=2) + "\n")
        plan = {k: previous[k] for k in DIFF_OUTLINE_SCHEMA["required"]}
    else:
        plan = ask("")
    errors = check_diff_plan(plan, trace, changes, summary, max_chapters)
    print_plan(plan, reader, errors)

    done = len(list(story.glob("outline.response.repair*.json")))
    for attempt in range(1, REPAIRS + 1):
        if not errors:
            break
        print(f"\nrepair {attempt}/{REPAIRS}")
        messages += [{"role": "assistant", "content": json.dumps(plan)},
                     {"role": "user", "content": repair_request(errors)}]
        plan = ask(f".repair{done + attempt}")
        errors = check_diff_plan(plan, trace, changes, summary, max_chapters)
        print_plan(plan, reader, errors)

    if not errors:
        outline = {"mode": "diff", "title": plan["title"], "premise": plan["premise"], "verdict": plan["verdict"],
                   "reader": reader, "repo": info, "chapters": plan["chapters"], "unexercised": plan["unexercised"]}
        (story / "outline.json").write_text(json.dumps(outline, indent=2) + "\n")
        drop_written(story)
    for name, reply in replies:
        print(f"\n{name}: {usage_line(reply.usage, reply.cost)}")
    return 1 if errors else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    opt = lambda f, default: argv[argv.index(f) + 1] if f in argv else default  # noqa: E731
    skip = {"--reader", "--max-chapters"}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (argv[i - 1:i] or [""])[0] not in skip]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    try:
        sys.exit(main(args[0], opt("--reader", "reviewer"), int(opt("--max-chapters", MAX_CHAPTERS)),
                      repair="--repair" in argv, dry_run="--dry-run" in argv))
    except llm.LLMError as e:
        print(f"\n✗ the model could not plan it: {e}")
        sys.exit(1)
