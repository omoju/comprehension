"""§5.2.1–2: write the comprehension questions and their keys, before any arm is read.

    .venv/bin/python codestory/eval/questions.py <repo> [<repo> ...]      → eval/questions/<repo>.json

The question writer sees the repository at the story's commit, the scenario and its trace: never a story, never
a DeepWiki page. 8 path questions (what happens to the data on this run) and 7 general questions (the owner's
goals: guarantees, failure modes, risky defaults). Every key is checked by code before any arm is read:
a path key is a Python check that runs against the repository and must pass; a general key names source lines
that must exist. Questions whose key fails are dropped and logged, not fixed by hand (§5.2.2, §10).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from common import EVAL, ask, save_trace, story_dir, text_of, usage_cost
from outline import numbered_trace, repo_block, repo_info
from verify import repo_python

N_PATH, N_GENERAL = 8, 7

SYSTEM = """You write comprehension questions about a repository for an evaluation. Later, readers who have seen
only a piece of documentation about the repository (not the code) will answer them, and a grader will compare
their answers with your keys. You see the repository, a scenario that uses it as intended, and a trace of that
run: every call into the repository's code with its arguments and return values.

Write two kinds of question:
- "path": about what happens to the data on this run: which function handles it, what value it has at a point,
  which branch is taken and why, what is returned, what would happen on a nearby wrong input. Each key must be
  observable by running code: give a "check", a short Python program that imports the package (the repository
  root is on PYTHONPATH), reproduces the relevant part of the scenario, and asserts the keyed answer. Standard
  library and the package only. The check must be able to fail if the key were wrong.
- "general": about the repository as a whole, from an owner's point of view: what it guarantees and under which
  conditions, how it can fail or be misused and what happens then, which defaults and design choices carry risk
  and why. Each key names the source lines that settle it, as "path:start-end" in the repository, and may add a
  check in the same form when the answer is observable.

Questions must be answerable from a good description of the code alone, without running it, and must have a
definite answer: no opinions, no "would you sign off". Vary difficulty. Do not ask about tests, typing, packaging
or CI. Write the key as the full answer a grader needs, with the specifics (names, values, conditions)."""

SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "p1..p8 for path, g1..g7 for general"},
            "kind": {"type": "string", "enum": ["path", "general"]},
            "question": {"type": "string"},
            "key": {"type": "string", "description": "the full answer, with specifics"},
            "lines": {"type": "array", "items": {"type": "string"}, "description": "path:start-end that settle it"},
            "check": {"type": "string", "description": "Python that asserts the key; required for path questions"},
        },
        "required": ["id", "kind", "question", "key", "lines", "check"], "additionalProperties": False}}},
    "required": ["questions"], "additionalProperties": False,
}


def check_lines(lines: list[str], repo: Path) -> str | None:
    for ref in lines:
        try:
            path, span = ref.rsplit(":", 1)
            start, _, end = span.partition("-")
            start, end = int(start), int(end or start)
        except ValueError:
            return f"malformed reference {ref!r}"
        f = repo / path
        if not f.is_file():
            return f"{path} does not exist"
        if not (1 <= start <= end <= len(f.read_text(errors="replace").splitlines())):
            return f"{ref} is outside the file"
    return None


def run_check(code: str, repo: Path, import_path: str) -> str | None:
    env_ = {**os.environ, "PYTHONPATH": str(repo / import_path)}
    try:
        run = subprocess.run([repo_python(repo), "-c", code], cwd=repo, env=env_, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "check timed out"
    if run.returncode != 0:
        return "check failed: " + ((run.stderr.strip() or run.stdout.strip()).splitlines() or ["(no output)"])[-1][:200]
    return None


def write_questions(client, name: str) -> dict:
    repo = EVAL.parent / "demo-repos" / name  # the story's commit, which is also what the questions describe
    story = story_dir(name)
    info = repo_info(repo)
    content = [repo_block(repo, info, story), {"type": "text", "text": (
        f"<scenario>\n{(story / 'scenario.py').read_text()}\n</scenario>\n\n<trace>\n{numbered_trace(story)}\n</trace>\n\n"
        f"Write {N_PATH} path questions and {N_GENERAL} general questions about this repository.")}]
    response = ask(client, SYSTEM, content, SCHEMA)
    save_trace(EVAL / "questions" / "traces", name, response)
    qs = json.loads(text_of(response))["questions"]

    kept, dropped = [], []
    for q in qs:
        problem = check_lines(q["lines"], repo) if q["lines"] else (None if q["kind"] == "path" else "no source lines")
        if not problem and q["kind"] == "path" and not q["check"].strip():
            problem = "path question without a check"
        if not problem and q["check"].strip():
            problem = run_check(q["check"], repo, info["import_path"])
        (dropped if problem else kept).append({**q, **({"dropped": problem} if problem else {})})

    out = {"repo": name, "commit": info["commit"], "questions": kept, "dropped": dropped,
           "cost": round(usage_cost(response.usage), 2)}
    (EVAL / "questions" / f"{name}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    import anthropic

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    client = anthropic.Anthropic()
    for name in sys.argv[1:]:
        r = write_questions(client, name)
        kinds = {k: sum(1 for q in r["questions"] if q["kind"] == k) for k in ("path", "general")}
        print(f"{name:13} kept {kinds['path']} path + {kinds['general']} general, dropped {len(r['dropped'])}  ${r['cost']:.2f}")
        for q in r["dropped"]:
            print(f"    - {q['id']}: {q['dropped']}")
