"""Step 1 for a TypeScript or JavaScript package: find the intended use, run it as one test, record the journey.

    .venv/bin/python codestory/scenario_ts.py <repo> <story-dir> [--pkg <package dir>]

scenario.py's counterpart. Claude writes one spec file that uses the package as intended (Vitest; Japa for an AdonisJS
app). It runs inside the package under a temporary name, so its imports resolve as the package's own tests' do, under
the TypeScript tracer (codestory/ts), and is removed again. The calls made while the test runs are the journey. A
rejected scenario goes back to Claude with the reason, in the same conversation, up to ATTEMPTS times. Writes
scenario.spec.ts, scenario.json (why, runner, pkg, include, attempts), trace.full.json, trace.json and trace.txt, as
scenario.py does; each attempt's raw trace is kept in traces/.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import env  # noqa: F401  (loads .env)
import deps
import llm
from diff_verify import VACUOUS, last_error, outcome
from outline import git, repo_block, repo_context, repo_info
from scenario import ATTEMPTS, MIN_CALLS, SCHEMA, asked, count_calls, save_story_trace
from verify import TS_SPEC_DIR, TS_TIMEOUT, run_spec, spec_name, ts_runner

# The scenario must not touch the instrument that measures it: the runtime's hooks or its settings.
TAMPERING = re.compile(r"__cs|\bCS_[A-Z]")
# The runner itself could not start (our setup, not the scenario): stop rather than ask the model to work around it.
HARNESS = re.compile(r"\[codestory\] (Vitest is not installed|could not load|usage:|no such spec)")
CODE_DIRS = ("src/", "lib/", "source/")
NOT_CODE = re.compile(r"^(tests?|__tests__|specs?|docs?|examples?|scripts?|dist|build|coverage|bench\w*|fixtures?)/"
                      r"|\.(spec|test)\.|\.d\.ts$|^\.|config\.[cm]?[jt]s$")
STORY_NAME = "scenario.spec.ts"

SYSTEM = """You choose the scenario for a code story. The story will follow the data as it travels through the
code when the package is used as intended, so the scenario decides the plot.

Write one test that uses this package exactly as intended, in its most typical, successful case: what the README,
docs or examples show first, or for an application, its main entry point with typical input. One representative
journey of data, start to finish, in a single test. It must run as-is: no network, no credentials, no user input, no
files outside the repository. Use realistic values. End with an assertion that the intended result came out.

The test runs under a tracer that records the journey; never refer to it (nothing named `__cs…` or `CS_…`).

Respond with JSON: "why" (one or two sentences: why this is the intended use, citing where the repo shows it)
and "script" (the whole spec file)."""

HOW = {
    "vitest": """The file is a Vitest spec: `import {{ it, expect }} from 'vitest'` and exactly one `it(...)`. It is
saved as {path} and run from {where} with Vitest. Import the package's source files ({include}) by relative path
from there, as the package's own tests do, never by the package's published name or from a build such as dist/:
the tracer records calls into the source.""",
    "japa": """The file is a Japa spec: `import {{ test }} from '@japa/runner'` and exactly one `test(...)`, with
`assert` from the test context. It is saved as {path} and run from {where} with `node ace test unit
--files=<its name>`, the application booted as for any unit test. Import application code ({include}) the way the
package's own tests do (its `#…` aliases, or relative paths). A unit test times out after 2000 ms: call
`.timeout(10000)` on the test if it needs longer.""",
}


def include_for(pkg_dir: Path, runner: str) -> str:
    """The package's own code, as the tracer's path prefixes (CS_INCLUDE): what is instrumented is what the story can
    follow. An AdonisJS app keeps it in app/, most packages in src/; a package with neither, in its top-level modules
    and folders, less tests, docs, builds and configuration."""
    if runner == "japa":
        return "app/"
    for d in CODE_DIRS:
        if (pkg_dir / d).is_dir():
            return d
    entries = sorted(p.name + "/" if p.is_dir() else p.name for p in pkg_dir.iterdir()
                     if p.name != "node_modules" and (p.is_dir() or re.search(r"\.([cm]?[jt]sx?|vue)$", p.name)))
    return ",".join(e for e in entries if not NOT_CODE.search(e)) or "-/"


def package_block(repo: Path, info: dict, pkg: str) -> dict:
    """The repository as one cached block, as scenario.py shows it; in a monorepo the package's files come first."""
    if pkg == ".":
        return repo_block(repo, info)
    focus = set(git(repo, "ls-files", "--", pkg).splitlines())
    text = f"Repository: {info['name']} at commit {info['commit'][:7]}\n\n{repo_context(repo, focus)}"
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


def static_errors(script: str) -> str | None:
    """What can be told without running it."""
    if TAMPERING.search(script):
        return "The file refers to the tracer (`__cs…` or `CS_…`). It must not; the tracer records the journey."
    if not re.search(r"\bexpect\s*\(|\bassert\b", script):
        return "The test asserts nothing. End with an assertion that the intended result came out."
    vacuous = [m.group(0).strip() for m in VACUOUS.finditer(script)]
    if vacuous:
        return f"An assertion can't fail: {vacuous[0]}. Assert the value the intended use produces."
    return None


def rejection(tests: list[dict], code: int | None, tail: str, name: str, include: str) -> str | None:
    """Did the journey happen? None if the test passed and went through enough of the package's code."""
    if not tests:
        if code is None:
            return f"The test did not finish within {TS_TIMEOUT} seconds and was stopped."
        return f"The spec file did not load: {last_error(tail, name)}\n\nThe runner's output ends:\n{tail[-2000:]}"
    if len(tests) != 1:
        return f"The file ran {len(tests)} tests. Write exactly one: one journey, start to finish."
    result = outcome(tests[0])
    if result != "pass":
        return f"The test did not pass ({result}).\n\nThe runner's output ends:\n{tail[-2000:]}"
    calls = count_calls(tests[0])
    if calls < MIN_CALLS:
        return (f"The test passed, but only {calls} calls into the package's code ({include}) were recorded. It must "
                "exercise the code's intended use, through its source files.")
    return None


def save(story: Path, test: dict, name: str) -> int:
    """The test's calls become the scenario's, as a script's calls are in trace.py, and the file the run used is
    named as the story keeps it. Then the trace is saved, compressed and numbered as scenario.py's is."""

    def rename(node: dict) -> None:
        if str(node.get("called_from") or "").startswith(name + ":"):
            node["called_from"] = STORY_NAME + node["called_from"][len(name):]
        for child in node["calls"]:
            rename(child)

    root = {"fn": "scenario", "file": STORY_NAME, "line": 1, "args": {}, "calls": test["calls"],
            "lines": test.get("lines", {})}
    rename(root)
    (story / "trace.json").write_text(json.dumps(root, indent=1) + "\n")
    return save_story_trace(story)


def main(repo_arg: str, story_arg: str, pkg_arg: str = ".", about: str = "") -> int:
    repo, story = Path(repo_arg).resolve(), Path(story_arg).resolve()
    pkg_dir = (repo / pkg_arg).resolve()
    if not (pkg_dir / "package.json").exists():
        print(f"no package.json in {pkg_dir}")
        return 2
    pkg = str(pkg_dir.relative_to(repo)) if pkg_dir != repo else "."
    runner = ts_runner(pkg_dir)
    include = include_for(pkg_dir, runner)
    try:
        deps.install(pkg_dir)
        if runner == "vitest":
            deps.ensure_tracer()
    except deps.InstallError as e:
        print(f"  {e}")
        return 3
    story.mkdir(parents=True, exist_ok=True)
    (story / "traces").mkdir(exist_ok=True)

    print(f"  model: {llm.describe()}\n  package: {pkg}/ · runner: {runner} · traced: {include}")
    where = "the repository root" if pkg == "." else f"{pkg}/"
    path = f"{'' if pkg == '.' else pkg + '/'}{TS_SPEC_DIR[runner]}codestory-scenario-<id>.spec.ts"
    how = HOW[runner].format(path=path, where=where, include=include)
    messages = [{"role": "user", "content": [package_block(repo, repo_info(repo), pkg),
                                             {"type": "text", "text": f"{how}\n\nWrite the scenario.{asked(about)}"}]}]
    for attempt in range(1, ATTEMPTS + 1):
        try:
            reply = llm.ask(SYSTEM, messages, schema=SCHEMA, max_tokens=32000)
        except llm.LLMError as e:
            print(f"  model call failed: {e}")
            return 1
        (story / "traces" / f"scenario-{attempt}.response.json").write_text(json.dumps(reply.record(), indent=1))
        answer = json.loads(reply.text)
        script = answer["script"].rstrip() + "\n"
        (story / STORY_NAME).write_text(script)
        (story / "scenario.json").write_text(json.dumps({"why": answer["why"], "runner": runner, "pkg": pkg,
                                                         "include": include, "attempts": attempt}, indent=2) + "\n")

        # The gates, in order: is the file allowed, did the runner work, did the test pass, did the journey happen?
        error = static_errors(script)
        if error is None:
            name = spec_name("scenario")
            raw = story / "traces" / f"scenario-{attempt}.trace.json"
            tests, code, tail = run_spec(script, pkg_dir, runner, name, raw, include=include, lines=True)
            if not tests and code is not None and not HARNESS.search(tail):
                # It didn't load. A boot can fail for reasons of its own (a sign-in, a port), so it gets a second run
                # before the model is told; a real mistake in the file fails the same way twice.
                print(f"  attempt {attempt}: the file didn't load; running it once more", flush=True)
                tests, code, tail = run_spec(script, pkg_dir, runner, name, raw, include=include, lines=True)
            (story / "traces" / f"scenario-{attempt}.log").write_text(tail)
            if HARNESS.search(tail):  # our setup, not the scenario: stop
                print(f"  attempt {attempt}: the test runner could not start (harness, not the scenario):\n{tail}")
                return 3
            error = rejection(tests, code, tail, name, include)
            if error is None:
                lines = save(story, tests[0], name)
                print(f"  attempt {attempt}: passed, {count_calls(tests[0])} calls traced → {lines} lines in "
                      f"{story.name}/trace.txt")
                return 0
        print(f"  attempt {attempt}: rejected: {error.splitlines()[0][:160]}")

        # The loop: keep the conversation, add what went wrong, ask again.
        messages += [{"role": "assistant", "content": reply.text},
                     {"role": "user", "content": f"The scenario was rejected:\n\n{error}\n\nFix it. Same requirements."}]
    print(f"no working scenario after {ATTEMPTS} attempts")
    return 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    pkg = argv[argv.index("--pkg") + 1] if "--pkg" in argv else "."
    about = argv[argv.index("--about") + 1] if "--about" in argv else ""
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1:i] not in (["--pkg"], ["--about"])]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], args[1], pkg, about))
