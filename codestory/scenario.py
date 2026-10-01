"""Step 1: find the intended use, run it, record the data's journey.

    .venv/bin/python codestory/scenario.py <repo> <story-dir>

Claude writes a small script that uses the repo as intended (its "main"). The harness runs it under the tracer.
If it fails, the error goes back to Claude and it tries again: the first feedback loop. Writes scenario.py,
scenario.json (why this scenario), trace.json and trace.txt into <story-dir>. Python repos only, for now.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import env  # noqa: F401  (loads .env)
from outline import MODEL, repo_block, repo_info
from trace import compress, render
from verify import repo_python

ATTEMPTS = 3
TRACER = Path(__file__).resolve().parent / "trace.py"
MIN_CALLS = 5  # a real journey passes through more of the repo than this

# The scenario must not touch the instrument that measures it.
TAMPERING = re.compile(r"\bsys\.(settrace|gettrace|setprofile|getprofile)\b|\bf_trace\b|\bthreading\.settrace\b")

SYSTEM = """You choose the scenario for a code story. The story will follow the data as it travels through the
code when the program is used as intended, so the scenario decides the plot.

The script runs under a tracer that records the journey; never touch tracing or profiling hooks.

Write a short Python script that uses this repository exactly as intended, in its most typical, successful case:
what the README, docs or examples show first, or for an application, its main entry point with typical input.
One representative journey of data, start to finish. It must run as-is from the repository root with the
package importable: no network, no credentials, no user input, no files outside the repository. Use realistic
values. End with an assert that the intended result came out.

Respond with JSON: "why" (one or two sentences: why this is the intended use, citing where the repo shows it)
and "script" (the Python source)."""

SCHEMA = {
    "type": "object",
    "properties": {"why": {"type": "string"}, "script": {"type": "string"}},
    "required": ["why", "script"],
    "additionalProperties": False,
}


def run_traced(repo: Path, story: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [repo_python(repo), str(TRACER), str(repo), str(story / "scenario.py"), str(story / "trace.json")],
        cwd=repo, capture_output=True, text=True, timeout=120,
    )


def save_story_trace(story: Path) -> int:
    """trace.full.json keeps everything; trace.json and trace.txt are the compressed trace the story is planned from."""
    full = json.loads((story / "trace.json").read_text())
    (story / "trace.full.json").write_text(json.dumps(full, indent=1) + "\n")
    tree = compress(full)
    text = render(tree)  # also numbers each call ("tl") so every later step agrees on line numbers
    tree["lines"] = full.get("lines", {})
    (story / "trace.json").write_text(json.dumps(tree, indent=1) + "\n")
    (story / "trace.txt").write_text("\n".join(text) + "\n")
    return len(text)


def count_calls(tree: dict) -> int:
    return len(tree["calls"]) + sum(count_calls(c) for c in tree["calls"])


def harness_failed(run: subprocess.CompletedProcess) -> bool:
    """Did the tracer itself crash (our bug), rather than the scenario (the model's)?"""
    frames = re.findall(r'File "([^"]+)", line \d+', run.stderr)
    return bool(frames) and frames[-1] == str(TRACER)


def main(repo_arg: str, story_arg: str) -> int:
    import anthropic

    repo, story = Path(repo_arg).resolve(), Path(story_arg).resolve()
    story.mkdir(parents=True, exist_ok=True)
    if not any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")):
        print("only Python repositories are supported so far")
        return 2

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": [repo_block(repo, repo_info(repo)),
                                             {"type": "text", "text": "Write the scenario."}]}]
    for attempt in range(1, ATTEMPTS + 1):
        with client.beta.messages.stream(
            model=MODEL, max_tokens=32000, system=SYSTEM, messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        (story / "traces").mkdir(exist_ok=True)
        (story / "traces" / f"scenario-{attempt}.response.json").write_text(response.to_json())
        if response.stop_reason != "end_turn":
            print(f"model stopped early: {response.stop_reason}")
            return 1

        answer = json.loads(next(b.text for b in response.content if b.type == "text"))
        (story / "scenario.py").write_text(answer["script"].rstrip() + "\n")
        (story / "scenario.json").write_text(json.dumps({"why": answer["why"], "attempts": attempt}, indent=2) + "\n")

        # Three gates, in order: is the script allowed, did the harness work, did the journey really happen?
        if TAMPERING.search(answer["script"]):
            error = "The script touches tracing or profiling hooks. It must not; the tracer records the journey."
        else:
            run = run_traced(repo, story)
            if harness_failed(run):  # our bug: stop, don't ask the model to work around it
                print(f"  attempt {attempt}: the tracer crashed (harness bug, not the scenario):\n{run.stderr[-2000:]}")
                return 3
            calls = count_calls(json.loads((story / "trace.json").read_text())) if run.returncode == 0 else 0
            if run.returncode == 0 and calls >= MIN_CALLS:
                lines = save_story_trace(story)
                print(f"  attempt {attempt}: ran, {calls} calls traced → {lines} lines in {story / 'trace.txt'}")
                return 0
            error = ((run.stderr.strip() or run.stdout.strip())[-3000:] if run.returncode
                     else f"The script ran, but only {calls} calls into the repository's code were recorded. "
                          "It must exercise the code's intended use.")
        print(f"  attempt {attempt}: rejected: {error.splitlines()[-1][:120]}")

        # The loop: keep the conversation, add what went wrong, ask again.
        messages += [{"role": "assistant", "content": response.content},
                     {"role": "user", "content": f"The script was rejected:\n\n{error}\n\nFix it. Same requirements."}]
    print(f"no working scenario after {ATTEMPTS} attempts")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
