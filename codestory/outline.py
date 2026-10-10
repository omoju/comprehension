"""Stage 1: one model call. Read a repo, plan its story for one kind of reader.

    .venv/bin/python codestory/outline.py <path-to-repo> <story-dir> [--reader owner|maintainer|user]
                                         [--max-chapters N] [--repair] [--dry-run]

Needs <story-dir>/scenario.py and trace.txt from scenario.py. Chapters are spans of the trace.

Writes <story-dir>/outline.json: title, premise, reader, repo (url, commit, local path) and the chapters.
The plan is checked (spans, question threads, length); a plan that fails is handed back to the model with the
errors, in the same conversation, up to REPAIRS times. --repair starts from the existing outline.json instead of
planning afresh (the previous plan is kept as outline.prev.json). --dry-run writes the prompt to
<story-dir>/outline.prompt.md without calling the model.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import env  # noqa: F401  (loads .env)
import llm

MODEL = llm.DEFAULT_MODELS["anthropic"]  # the evaluation harness (eval/) calls the Anthropic API with this directly
CONTEXT_BUDGET = 400_000  # characters of source code to show the model (~100k tokens)
MAX_CHAPTERS = 10  # the length budget; "as many as the journey needs" gave 12-14 for 500-line libraries
MIN_CALLS = 5  # calls into the repo a chapter's span must cover; the itsdangerous story that read well never had fewer
REPAIRS = 2  # how many times a failing plan goes back to the model

# Generated or non-code files: they cost context and tell the story nothing.
NOISE = re.compile(
    r"(\.lock|lock\.json|lock\.yaml|\.sum|\.svg|\.png|\.jpe?g|\.gif|\.ico|\.min\.js|\.map)$"
    r"|(^|/)(vendor|node_modules|dist|build)/"
)

READERS = Path(__file__).resolve().parent / "readers"

SYSTEM = """You plan code stories. A code story explains a repository by following its data: the story stays with
the data, in close third person, as it travels through the code when the program is used as intended. The
protagonist is the main input, the value the caller hands in; setup before it appears is the world it enters and
gets little room. You
are given the repository and a trace of one real run of the intended use: every call into the repository's code,
in order, nested by depth, with the arguments it received and what it returned. The trace is the plot.

The formula: each chapter is a function. A chapter covers one contiguous span of the trace. Its input is the
data as it enters that span; its output is the data as it leaves, taken from the trace's real values. The next
chapter picks the data up exactly there. Chapters follow the trace's order. Nothing is introduced before the data
meets it; parts of the code the data doesn't pass through appear only as roads not taken, where the data passes
the branch (for example: what would have happened had the signature been wrong).

The story is for one particular reader, given with the request: what they care about decides where the story
slows down and where it moves quickly. Use as many chapters as this journey needs for this reader, within the
budget given with the request. Every chapter must earn its place: enough has to happen to the data in its span
to carry a chapter. A span of a few trace lines where the data merely passes through belongs inside its
neighbour; repetitive steps (the same helper called many times) are told once and then passed quickly.

Characters are real things in the code the data meets (functions, classes, values). Facts are claims about
behaviour that can be checked against the code or the trace. Open questions are things the data wonders about
that a later chapter answers. Give each an id like "q3.1" (chapter 3, question 1); every question must be answered
by exactly one later chapter, which lists the id in its "answers"."""

OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "premise": {"type": "string", "description": "The problem the code exists to solve, as the story's opening situation."},
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer"},
                    "title": {"type": "string"},
                    "trace_lines": {"type": "array", "items": {"type": "integer"},
                                    "description": "[first, last] line numbers of the trace this chapter covers"},
                    "data_in": {"type": "string", "description": "the data as it enters, from the trace"},
                    "data_out": {"type": "string", "description": "the data as it leaves, from the trace"},
                    "code": {"type": "array", "items": {"type": "string"}, "description": "path or path:start-end"},
                    "inputs": {"type": "array", "items": {"type": "string"}},
                    "characters": {"type": "array", "items": {"type": "string"}},
                    "facts": {"type": "array", "items": {"type": "string"}},
                    "open_questions": {"type": "array", "items": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}, "question": {"type": "string"}},
                        "required": ["id", "question"], "additionalProperties": False}},
                    "answers": {"type": "array", "items": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}, "answer": {"type": "string"}},
                        "required": ["id", "answer"], "additionalProperties": False}},
                },
                "required": ["n", "title", "trace_lines", "data_in", "data_out", "code", "inputs", "characters", "facts", "open_questions", "answers"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "premise", "chapters"],
    "additionalProperties": False,
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


ROOT = Path(__file__).resolve().parent.parent


def relative_to_root(path: Path) -> str:
    """Paths stored in outputs are relative to the project root, so the files carry no machine-specific prefix."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def repo_info(repo: Path) -> dict:
    remote = git(repo, "remote", "get-url", "origin")
    url = re.sub(r"^git@github\.com:", "https://github.com/", remote).removesuffix(".git")
    return {"name": url.split("github.com/")[-1], "url": url, "commit": git(repo, "rev-parse", "HEAD"),
            "local_path": relative_to_root(repo), "import_path": "src" if (repo / "src").is_dir() else "."}


GUIDES = re.compile(r"(^|/)(readme[^/]*|pyproject\.toml|setup\.(py|cfg))$|^(docs|examples?)/", re.I)


def traced_files(story: Path) -> set[str]:
    """Files the data actually passes through, from the recorded trace."""
    trace = story / "trace.json"
    if not trace.exists():
        return set()
    found, stack = set(), [json.loads(trace.read_text())]
    while stack:
        node = stack.pop()
        found.add(node["file"])
        stack += node["calls"]
    return found


def repo_context(repo: Path, focus: set[str] | None = None, order: list[str] | None = None) -> str:
    """The repo as the model will see it: a file list, then as many files as fit, with line numbers.

    With a trace, the files the data passes through come first, then the README and docs, then the rest while the
    budget lasts: in a large repo the model sees what matters. Without one, the README and docs come first.
    `order` puts the named files before everything else, in that order."""
    files = []
    for path in git(repo, "ls-files").splitlines():
        if NOISE.search(path):
            continue
        try:
            text = (repo / path).read_text()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue  # binary or missing
        files.append((path, text))

    listing = "\n".join(f"{p}  ({t.count(chr(10))} lines)" for p, t in files)
    focus = focus or set()
    rank = {p: i for i, p in enumerate(order or [])}
    files.sort(key=lambda f: (rank.get(f[0], len(rank)), f[0] not in focus, not GUIDES.search(f[0])))  # stable: repo order within each group
    parts, used, skipped = [], 0, []
    for path, text in files:
        numbered = "\n".join(f"{i:5}  {line}" for i, line in enumerate(text.splitlines(), 1))
        block = f'<file path="{path}">\n{numbered}\n</file>'
        if used + len(block) > CONTEXT_BUDGET:
            skipped.append(path)
            continue
        parts.append(block)
        used += len(block)

    note = f"\n\n({len(skipped)} files not shown because of the context budget: {', '.join(skipped)})" if skipped else ""
    return f"<file_list>\n{listing}\n</file_list>\n\n" + "\n\n".join(parts) + note


def numbered_trace(story: Path) -> str:
    lines = (story / "trace.txt").read_text().splitlines()
    return "\n".join(f"{i:4}  {line}" for i, line in enumerate(lines, 1))


def span_errors(chapters: list[dict], trace_len: int) -> list[str]:
    """Chapters are numbered 1..k; spans are well-formed, in trace order, and don't overlap."""
    errors, last = [], 0
    if [c["n"] for c in chapters] != list(range(1, len(chapters) + 1)):
        errors.append(f"chapters are numbered {[c['n'] for c in chapters]}, not 1..{len(chapters)}")
    for c in chapters:
        span = c["trace_lines"]
        if len(span) != 2 or not (1 <= span[0] <= span[1] <= trace_len):
            errors.append(f"ch{c['n']} has a bad trace span {span} (trace has {trace_len} lines)")
            continue
        if span[0] <= last:
            errors.append(f"ch{c['n']} starts at trace line {span[0]}, before the previous chapter ended ({last})")
        last = span[1]
    return errors


def thread_errors(chapters: list[dict]) -> list[str]:
    """Every question answered exactly once, by a later chapter; every answer refers to a real, earlier question."""
    asked = {q["id"]: c["n"] for c in chapters for q in c["open_questions"]}
    answered: dict[str, int] = {}
    errors = []
    for c in chapters:
        for a in c["answers"]:
            if a["id"] not in asked:
                errors.append(f"ch{c['n']} answers {a['id']}, which was never asked")
            elif asked[a["id"]] >= c["n"]:
                errors.append(f"ch{c['n']} answers {a['id']} before or where it is asked")
            if a["id"] in answered:
                errors.append(f"{a['id']} answered twice (ch{answered[a['id']]}, ch{c['n']})")
            answered[a["id"]] = c["n"]
    errors += [f"{q} (ch{n}) is never answered" for q, n in asked.items() if q not in answered]
    return errors


def calls_in(trace: list[str], span: list[int]) -> int:
    """Calls in a span of the trace: every line that isn't a return value."""
    return sum(1 for line in trace[span[0] - 1 : span[1]] if not line.strip().startswith("→"))


def check_plan(plan: dict, trace: list[str], max_chapters: int) -> list[str]:
    """Everything code can decide about a plan. Empty means the plan may flow on to the chapters.

    The length budget has two sides. A cap on the count alone was met by merging the two thinnest spans and
    leaving chapters of one call; the minimum per chapter can't be met that way, since the trace fixes the total."""
    chapters = plan["chapters"]
    errors = span_errors(chapters, len(trace)) + thread_errors(chapters)
    if len(chapters) > max_chapters:
        errors.append(f"{len(chapters)} chapters, budget is {max_chapters}: merge the thinnest spans into their neighbours")
    for c in chapters:
        if len(c["trace_lines"]) == 2 and (n := calls_in(trace, c["trace_lines"])) < MIN_CALLS:
            errors.append(f"ch{c['n']} covers only {n} call{'s' if n != 1 else ''} (trace lines "
                          f"{c['trace_lines'][0]}-{c['trace_lines'][1]}); a chapter needs at least {MIN_CALLS}: "
                          f"fold it into a neighbour")
    return errors


def repair_request(errors: list[str]) -> str:
    return ("The plan failed these checks:\n" + "\n".join(f"- {e}" for e in errors)
            + "\n\nReturn the whole corrected plan, in the same format. Fix only what the checks name and whatever "
              "that forces (renumber chapters and question ids if chapters merge); keep the rest as it is.")


def repo_block(repo: Path, info: dict, story: Path | None = None) -> dict:
    """The repo as one content block, marked for caching. Same repo, same bytes, so later calls read it from cache."""
    focus = traced_files(story) if story else set()
    text = f"Repository: {info['name']} at commit {info['commit'][:7]}\n\n{repo_context(repo, focus)}"
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


def decode_escapes(value):
    """The model sometimes writes "\\u2014" as six characters of text instead of the dash, and JSON keeps the text.
    Decode such escapes in every string of the plan, so pages never print them."""
    if isinstance(value, str):
        return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
    if isinstance(value, list):
        return [decode_escapes(v) for v in value]
    if isinstance(value, dict):
        return {k: decode_escapes(v) for k, v in value.items()}
    return value


def plan_call(messages: list[dict]):
    return llm.ask(SYSTEM, messages, schema=OUTLINE_SCHEMA, max_tokens=64000)


def usage_line(u: dict, cost: float | None) -> str:
    return (f"{u.get('input_tokens', 0):,} tokens in (+{u.get('cache_read_input_tokens', 0):,} cached, "
            f"{u.get('cache_creation_input_tokens', 0):,} written to cache), {u.get('output_tokens', 0):,} out"
            + (f", ${cost:.2f}" if cost is not None else ""))


def print_plan(plan: dict, reader: str, errors: list[str]) -> None:
    print(f"{plan['title']}  [{reader}]: {len(plan['chapters'])} chapters")
    for c in plan["chapters"]:
        print(f"  {c['n']:2}. {c['title']}  [trace {c['trace_lines'][0]}-{c['trace_lines'][-1]}]")
    for e in errors:
        print(f"  ! {e}")


def main(repo_arg: str, story_arg: str, reader: str, max_chapters: int, repair: bool, dry_run: bool) -> int:
    repo, story = Path(repo_arg), Path(story_arg)
    info = repo_info(repo)
    profile = (READERS / f"{reader}.md").read_text()
    scenario = (story / "scenario.py").read_text()
    trace = (story / "trace.txt").read_text().splitlines()
    # Stable first, variable last: the repo block is cached, and runs for other readers reuse it.
    content = [repo_block(repo, info, story), {"type": "text", "text": (
        f"<scenario>\n{scenario}\n</scenario>\n\n<trace>\n{numbered_trace(story)}\n</trace>\n\n"
        f"<reader>\n{profile}\n</reader>\n\nPlan the story for this reader, in at most {max_chapters} chapters, "
        f"each covering at least {MIN_CALLS} calls of the trace.")}]
    messages: list[dict] = [{"role": "user", "content": content}]

    if dry_run:
        (story / "outline.prompt.md").write_text(f"# system\n\n{SYSTEM}\n\n# user\n\n" + "\n\n".join(b["text"] for b in content))
        print("prompt written")
        return 0

    usage = []
    print(f"model: {llm.describe()}")

    def ask(name: str) -> dict:
        reply = plan_call(messages)
        (story / f"outline.response{name}.json").write_text(json.dumps(reply.record(), indent=1))  # usage, model, raw
        usage.append((name or "plan", reply))
        return decode_escapes(json.loads(reply.text))

    if repair:  # the existing plan stands in for the model's first answer
        previous = json.loads((story / "outline.json").read_text())
        (story / "outline.prev.json").write_text(json.dumps(previous, indent=2) + "\n")
        plan = {k: previous[k] for k in ("title", "premise", "chapters")}
    else:
        plan = ask("")
    errors = check_plan(plan, trace, max_chapters)
    print_plan(plan, reader, errors)

    # The repair loop: the plan goes back with its verdict, in the same conversation, so the model sees exactly
    # what it wrote and exactly what failed. The repo block is read from cache, so a repair costs a tenth of a plan.
    done = len(list(story.glob("outline.response.repair*.json")))  # earlier --repair passes keep their responses
    for attempt in range(1, REPAIRS + 1):
        if not errors:
            break
        print(f"\nrepair {attempt}/{REPAIRS}")
        messages += [{"role": "assistant", "content": json.dumps(plan)},
                     {"role": "user", "content": repair_request(errors)}]
        plan = ask(f".repair{done + attempt}")
        errors = check_plan(plan, trace, max_chapters)
        print_plan(plan, reader, errors)

    if not errors:
        outline = {"title": plan["title"], "premise": plan["premise"], "reader": reader, "repo": info,
                   "chapters": plan["chapters"]}
        (story / "outline.json").write_text(json.dumps(outline, indent=2) + "\n")

    for name, reply in usage:
        print(f"\n{name}: {usage_line(reply.usage, reply.cost)}")
    return 1 if errors else 0  # a plan that fails its checks must not flow on to the chapters


if __name__ == "__main__":
    argv = sys.argv[1:]
    opt = lambda f, default: argv[argv.index(f) + 1] if f in argv else default  # noqa: E731
    reader = opt("--reader", "owner")
    max_chapters = int(opt("--max-chapters", MAX_CHAPTERS))
    skip = {"--reader", "--max-chapters"}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (argv[i - 1:i] or [""])[0] not in skip]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*args, reader=reader, max_chapters=max_chapters, repair="--repair" in argv, dry_run="--dry-run" in argv))
