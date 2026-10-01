"""Stage 2: write the chapters, in order. Each is a function of the plan and what came before.

    .venv/bin/python codestory/chapter.py <story-dir> [--only N | --upto N]

Reads <story-dir>/outline.json, scenario.py and trace.txt, writes NN-slug.md per chapter (the story) and
proofs/NN.py (its proof, kept out of the reader's way), then checks each one:
citations and proofs (verify.py) and contradictions (claims.py, Jev). No repair yet: this is the baseline
that stage 3's loop has to beat. Results go to <story-dir>/report.md; full model traces to traces/.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import env  # noqa: F401  (loads .env)
from claims import judge_text
from outline import MODEL, READERS, numbered_trace, repo_block
from verify import check_text, read_proofs, repo_path, split_proofs, write_proofs

SYSTEM = """You write one chapter of a code story at a time. The story follows the data as it travels through the
code when the program is used as intended, told in close third person: the narrator stays with the data and sees
what happens to it, but is not the data. You are given the repository, the scenario (the intended use), a trace
of that real run with every call, argument and return value, the plan, and the reader the story is for.

The protagonist is the main input: the value the caller hands to the code (here, whatever the scenario passes in to
be processed). Setup that happens before it appears, such as constructing objects and choosing keys, is the world
it is about to enter: tell it briefly, as setting, and keep the protagonist in view.

The formula: each chapter is a function. It covers one span of the trace. It begins with the data exactly as it
enters that span and ends with the data exactly as it leaves, and the next chapter picks it up there. Use the real
values from the trace: the reader should see what the data looks like at each step. Follow the trace's order.
Where the data passes a branch it doesn't take, the narrator may say briefly what would have happened; stay on
the road. Don't re-tell earlier chapters; don't run ahead into later ones.

Voice: the functions and classes the data meets are the other characters; say what they do to it and why. Plain,
concrete, warm; never cute at the expense of accuracy. The reader's concerns decide where the story slows down
and explains *why* the code does what it does.

When the narrator turns to the reader about their own concerns (for an owner: a guarantee, a risk, a default to
question, something to check before signing off), put it in a callout of its own: a blockquote whose first words
are the reader's role in bold, like `> **For the owner:** …`. Keep the journey in the narration and the advice in
the callouts. Use them where they matter, typically one or two per chapter, never more than three.

Accountability, which is not optional:
- Every claim about the code links to the exact lines that show it, as a permalink in this form:
  [text](REPO_URL/blob/COMMIT/path/to/file#L10-L14). Use the full commit hash given. Line numbers must be the real
  ones from the numbered source you are shown. Link the lines that prove the claim, not a nearby area.
- Values you show must be the ones in the trace. Say only what the code and trace show; mark inference as such.
- End with a proof: a fenced code block whose info string is exactly the proof language given (for example
  ```python proof). It replays the scenario up to the end of this chapter's span and asserts the values the data
  had along the way, exactly as the trace records them. Use only the standard library and the repository's own
  package; test frameworks may not be installed. Every assert must be able to fail if the story were wrong:
  no `or True`, no `assert True`, no asserting a value equals itself.

Format: Markdown, starting with "# Chapter N · Title", then a one-line blockquote "**Enters as:** <data_in>",
then the story, then a blockquote "**Leaves as:** <data_out>", then the proof. Nothing else."""


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]


def proof_language(repo: Path) -> str:
    return "python" if any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")) else "sh"


def write_chapter(client, n: int, outline: dict, repo: Path, story: Path, previous: str | None):
    chapter = next(c for c in outline["chapters"] if c["n"] == n)
    info = outline["repo"]
    lang = proof_language(repo)
    profile = (READERS / f"{outline['reader']}.md").read_text()
    plan = json.dumps({k: outline[k] for k in ("title", "premise", "chapters")}, indent=1)

    content = [
        repo_block(repo, info, story),  # cached: same for every chapter
        {"type": "text", "cache_control": {"type": "ephemeral"},  # cached: same for every chapter of this story
         "text": (f"<scenario>\n{(story / 'scenario.py').read_text()}\n</scenario>\n\n"
                  f"<trace>\n{numbered_trace(story)}\n</trace>\n\n"
                  f"<reader>\n{profile}\n</reader>\n\n<plan>\n{plan}\n</plan>")},
        {"type": "text", "text": (
            (f"<previous_chapter>\n{previous}\n</previous_chapter>\n\n" if previous else "")
            + f"Write chapter {n}: {chapter['title']}. It covers trace lines "
            f"{chapter['trace_lines'][0]}-{chapter['trace_lines'][-1]}.\n"
            f"REPO_URL = {info['url']}\nCOMMIT = {info['commit']}\n"
            f"Proof language: {lang}. The scenario is shown above; the proof runs from the repository root"
            + (f" with PYTHONPATH={info.get('import_path', '.')}." if lang == "python" else ", with bash.")
        )},
    ]

    start = time.time()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        response = stream.get_final_message()
    seconds = time.time() - start

    (story / "traces").mkdir(exist_ok=True)
    (story / "traces" / f"{n:02}.response.json").write_text(response.to_json())
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"chapter {n}: model stopped early: {response.stop_reason}")
    text, proofs = split_proofs(next(b.text for b in response.content if b.type == "text").strip() + "\n")
    path = story / f"{n:02}-{slug(chapter['title'])}.md"
    path.write_text(text)  # the story, for the reader
    write_proofs(path, proofs)  # the evidence, for the checker: proofs/NN.py
    return path, text, proofs, response.usage, seconds


def main(story_arg: str, only: int | None, upto: int | None = None) -> int:
    import anthropic

    story = Path(story_arg)
    outline = json.loads((story / "outline.json").read_text())
    repo = repo_path(outline)
    client = anthropic.Anthropic()

    rows, previous, cache = [], None, {}
    for c in outline["chapters"]:
        n = c["n"]
        if only and n != only:
            continue
        if upto and n > upto:
            break
        if only and n > 1:  # still hand over the previous chapter if it exists
            prev = sorted(story.glob(f"{n - 1:02}-*.md"))
            previous = prev[0].read_text() if prev else None
        existing = sorted(story.glob(f"{n:02}-*.md"))
        if existing and not only:  # resumable: a stopped run picks up where it left off, paying only for new chapters
            path, text = existing[0], existing[0].read_text()
            proofs = read_proofs(path)
            u, secs = json.loads((story / "traces" / f"{n:02}.response.json").read_text())["usage"], 0
            u = type("Usage", (), {k: u.get(k) or 0 for k in
                     ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")})
        else:
            path, text, proofs, u, secs = write_chapter(client, n, outline, repo, story, previous)
        previous = text

        v = check_text(text, path.name, outline, repo, cache, proofs)
        judged = judge_text(text, outline, repo)
        lies = [j for j in judged if j["failed"]]
        cost = (u.input_tokens * 5 + u.cache_creation_input_tokens * 6.25 + u.cache_read_input_tokens * 0.5
                + u.output_tokens * 25) / 1e6
        rows.append({"n": n, "file": path.name, "words": len(text.split()), "citations": v.citations,
                     "proofs": v.proofs, "errors": v.errors, "contradicted": lies, "judged": len(judged),
                     "seconds": round(secs), "cost": cost, "cached": u.cache_read_input_tokens})
        status = "ok" if not (v.errors or lies) else f"{len(v.errors)} check errors, {len(lies)} contradicted"
        print(f"  {n:2}. {path.name}  {len(text.split())} words, {v.citations} citations, {secs:.0f}s, "
              f"${cost:.2f}  → {status}", flush=True)

    lines = [f"# Report · {outline['title']} · reader: {outline['reader']}\n",
             "| # | chapter | words | citations | check errors | contradicted ¶ | time | cost |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['n']} | [{r['file']}]({r['file']}) | {r['words']} | {r['citations']} | {len(r['errors'])} "
                     f"| {len(r['contradicted'])}/{r['judged']} | {r['seconds']}s | ${r['cost']:.2f} |")
    lines.append(f"\n**Total:** ${sum(r['cost'] for r in rows):.2f}, {sum(r['seconds'] for r in rows)}s\n")
    for r in rows:
        if r["errors"] or r["contradicted"]:
            lines.append(f"\n## {r['file']}")
            lines += [f"- ✗ {e}" for e in r["errors"]]
            lines += [f"- contradicted ({j['contradicted']:.2f}): “{j['first']}…”" for j in r["contradicted"]]
    (story / "report.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    flag = lambda f: int(argv[argv.index(f) + 1]) if f in argv else None  # noqa: E731
    only, upto = flag("--only"), flag("--upto")
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1:i] not in (["--only"], ["--upto"])]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], only, upto))
