"""Write the chapters of a change story, then check them all and repair the ones that fail.

    .venv/bin/python codestory/diff_chapter.py <story-dir> [--only N] [--no-repair]

Reads outline.json (mode "diff") and diff.py's outputs; writes NN-slug.md per chapter and proofs/NN.ts, its proof:
a whole spec file in the package's own test runner. Chapters are written in order, each handed the one before.
Then every chapter is checked at once (diff_verify.py: citations on both sides; proofs in one run per side, since a
run boots the application), and each failing chapter goes back to the model with its errors, in its own
conversation, up to REPAIRS times. Existing chapters are kept and rechecked, so a second run is a repair pass.
Results go to report.md; every model answer to traces/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import env  # noqa: F401  (loads .env)
import llm
import style
from chapter import Usage, money, slug
from diff_outline import change_block, evidence_block, load, numbered
from diff_verify import Report, chapter_files, proof_name, split_proof, verify
from outline import READERS, REPAIRS

SYSTEM = """You write one chapter of a change story at a time. A change story follows the data through the change's
own tests, run twice: on the code before the change (the base) and after it (the head). It is told in close third
person: the narrator stays with the data and sees what happens to it on each side, but is not the data. You are
given the change (its diff, and every changed file on both sides with line numbers), the tests and how each ended
before and after, the two runs merged into one numbered trace (`+` happens only after the change, `-` only before,
`~` is the same call with other values and its `before` lines show the old ones, ` *` marks a function the change
edited), the plan, and the reader the story is for.

The formula: each chapter covers one span of the trace and turns on one difference. Open on what is at stake for
this data, then go straight to the moment the two versions part ways: what the head does with it, what the base did
instead, with the real values on both sides. Get there fast; the steps before it are a clause. Don't re-tell earlier
chapters; don't run ahead into later ones. If the plan marks the chapter "preserved", show the behaviour that stays
the same and why the change doesn't disturb it, briefly.

Voice: the functions and classes the data meets are the other characters; say what they do to it and why the change
made them do it differently. Plain, concrete, warm; never cute at the expense of accuracy. The reader's concerns
decide where the story slows down.

When the narrator turns to the reader about their own concerns (for a reviewer: a new guarantee, a risk, a default to
question, a caller that relied on the old behaviour, something to ask the author), put it in a callout of its own: a
blockquote whose first words are the reader's role in bold, like `> **For the reviewer:** …`. Keep the journey in
the narration and the advice in the callouts; typically one or two per chapter, never more than three. Callouts are
written plainly: one topic per sentence, active voice, and any action as an imperative.

{writing}

Accountability, which is not optional:
- Every claim about the code links to the exact lines that show it, as a permalink that starts with the prefix the
  request gives for that side (the repository's URL, `/blob/` and the side's full commit hash), then the file's path
  and its lines: [the new guard](<the prefix for the code after the change>src/utils.ts#L327-L330). Never write the
  words HEAD or BASE in a link. Line numbers must be the real ones from the numbered file of that side. Cite the code
  after the change for what it does now; cite the code before it only to show what it did then.
- Values you show must be the ones in the trace. Say only what the code and trace show; mark inference as such. The
  runs say nothing about code they never reached: don't claim behaviour for it.
- End with a proof: one fenced code block whose info string is exactly `ts proof`, holding a whole spec file, as the
  request describes. It runs once on the head and once on the base. A "changed" chapter's proof passes on the head
  and fails on the base: assert the values the trace shows on the head where the base's differ. A "preserved"
  chapter's proof passes on both. Every assertion must be able to fail if the story were wrong: never assert that a
  value equals itself, or that true is true.

Format: Markdown, starting with "# Chapter N · Title", then a blockquote "**Before:** <before>", a blank line, and a
blockquote
"**After:** <after>", then the story, then the proof. Nothing else."""

SYSTEM = SYSTEM.replace("{writing}", style.WRITING)

PROOF_HOW = {
    "japa": """The proof is a whole Japa spec file. It is saved as {pkg}/{path} and run from {pkg}/ with
`node ace test unit --files={name}`, once on the head and once on the base, with the application booted as for any
unit test. Import application code the way the change's own spec does (the package's `#services/…` style aliases, or
relative paths) and copy any helper you need into the file; use `test` (and `test.group` if you like) from
'@japa/runner', with `assert` from the test context. A unit test times out after 2000 ms: call `.timeout(10000)` on a
test that needs longer. On the base, a name the change adds is undefined rather than a failed import.""",
    "vitest": """The proof is a whole Vitest spec file. It is saved as {pkg}/{path} and run from {pkg}/ with Vitest,
once on the head and once on the base. Import application code by relative path from {pkg}/tests/unit/codestory/ (or
the package's aliases), and use `describe`, `it` and `expect` from 'vitest'. On the base, a name the change adds is
undefined rather than a failed import.""",
}


def chapter_request(n: int, outline: dict, story: Path, changes: dict, summary: dict, trace: list[str],
                    previous: str | None) -> list[dict]:
    """The user turn that asks for chapter n: the change (cached, the same for every chapter), the story's context
    (cached, the same for every chapter of this story), then this chapter's request."""
    chapter = next(c for c in outline["chapters"] if c["n"] == n)
    info = outline["repo"]
    profile = (READERS / f"{outline['reader']}.md").read_text()
    plan = json.dumps({k: outline[k] for k in ("title", "premise", "verdict", "chapters", "unexercised")}, indent=1)
    name = proof_name(story, n)
    how = PROOF_HOW[changes.get("runner", "japa")].format(pkg=changes["pkg"], path=f"tests/unit/codestory/{name}",
                                                          name=name)
    return [
        change_block(story, changes, info),
        {"type": "text", "cache_control": {"type": "ephemeral"},
         "text": (f"{evidence_block(changes, summary)}\n\n<trace>\n{numbered(trace)}\n</trace>\n\n"
                  f"<reader>\n{profile}\n</reader>\n\n<plan>\n{plan}\n</plan>")},
        {"type": "text", "text": (
            (f"<previous_chapter>\n{previous}\n</previous_chapter>\n\n" if previous else "")
            + f"Write chapter {n}: {chapter['title']} (kind: {chapter['kind']}). It covers trace lines "
            f"{chapter['trace_lines'][0]}-{chapter['trace_lines'][-1]}.\n"
            f"Links to the code after the change start with: {info['url']}/blob/{info['head']}/\n"
            f"Links to the code before the change start with: {info['url']}/blob/{info['base']}/\n\n{how}")},
    ]


def readable(story: Path, reports: dict[int, Report]) -> dict[int, Report]:
    """The checks on how a chapter reads (style.py), added to the checks on what it claims; a chapter with no
    citations, or citations by branch name, fails here rather than passing with a warning."""
    url = json.loads((story / "outline.json").read_text())["repo"]["url"]
    for n, r in reports.items():
        md = chapter_files(story, n)[0]
        if md:
            text = md.read_text()
            r.errors += style.check_links(text, url) + style.check_chapter(text)
    return reports


def repair_request(r: Report) -> str:
    return ("The chapter failed these checks:\n" + "\n".join(f"- {e}" for e in r.errors)
            + (f"\n\nThe proof's outcome: on the head, {r.head}; on the base, {r.base}." if r.head else "")
            + "\n\nReturn the whole corrected chapter, in the same format. Fix what the checks name: re-read the cited "
              "lines on the side the link names and fix the link or the claim; make the proof pass on the head and, "
              "for a changed chapter, fail on the base; where it is too long, cut the plumbing and the repeated cases, "
              "not the decisive moment. Keep everything else that passed as it is.")


def ask(messages: list[dict], n: int, story: Path, name: str) -> tuple[llm.Reply, float]:
    start = time.time()
    reply = llm.ask(SYSTEM, messages, max_tokens=32000)
    (story / "traces").mkdir(exist_ok=True)
    (story / "traces" / f"{n:02}.{name}.json").write_text(json.dumps(reply.record(), indent=1))
    return reply, time.time() - start


def save(raw: str, n: int, outline: dict, story: Path) -> str:
    """Split the model's answer into the chapter (NN-slug.md) and its proof (proofs/NN.ts); return the chapter."""
    chapter = next(c for c in outline["chapters"] if c["n"] == n)
    text, proof = split_proof(raw)
    for old in story.glob(f"{n:02}-*.md"):
        old.unlink()
    (story / f"{n:02}-{slug(chapter['title'])}.md").write_text(text)
    proof_file = chapter_files(story, n)[1]
    proof_file.parent.mkdir(exist_ok=True)
    if proof is not None:
        proof_file.write_text(proof)
    else:
        proof_file.unlink(missing_ok=True)
    return text


def joined(n: int, story: Path) -> str:
    """A finished chapter as the model would have written it: the story, then its proof."""
    md, proof = chapter_files(story, n)
    text = md.read_text() if md else ""
    return text.rstrip() + "\n" + (f"\n```ts proof\n{proof.read_text()}```\n" if proof.exists() else "")


def main(story_arg: str, only: int | None, repairs: int) -> int:
    story = Path(story_arg).resolve()
    outline = json.loads((story / "outline.json").read_text())
    changes, trace, summary = load(story)
    print(f"  model: {llm.describe()}")

    ns = [c["n"] for c in outline["chapters"] if not only or c["n"] == only]
    convo: dict[int, list[dict]] = {}
    usage = {n: Usage() for n in ns}
    secs = {n: 0.0 for n in ns}
    repaired = {n: 0 for n in ns}
    previous = None
    for n in ns:
        if only and n > 1:
            prev = chapter_files(story, n - 1)[0]
            previous = prev.read_text() if prev else None
        convo[n] = [{"role": "user", "content": chapter_request(n, outline, story, changes, summary, trace, previous)}]
        md = chapter_files(story, n)[0]
        if md and not only:  # resumable: a finished chapter is kept and rechecked below
            for record in sorted((story / "traces").glob(f"{n:02}.*.json")):
                usage[n].add_record(json.loads(record.read_text()))
            previous = md.read_text()
            print(f"  {n:2}. {md.name}  (kept)", flush=True)
            continue
        reply, secs[n] = ask(convo[n], n, story, "response")
        usage[n].add(reply.usage, reply.cost)
        previous = save(reply.text.strip() + "\n", n, outline, story)
        print(f"  {n:2}. {chapter_files(story, n)[0].name}  {len(previous.split())} words, {secs[n]:.0f}s, "
              f"{money(usage[n].cost)}", flush=True)

    # Check everything at once (a proof run boots the app, once per side), then repair what failed, then recheck it.
    print("\n  checking: citations, how it reads, and proofs on the head and the base…", flush=True)
    reports = readable(story, verify(story, ns))
    for attempt in range(1, repairs + 1):
        failing = [n for n in ns if reports[n].errors]
        if not failing:
            break
        for n in failing:
            print(f"  {n:2}. ✗ {len(reports[n].errors)} errors, repair {attempt}/{repairs}: {reports[n].errors[0]}",
                  flush=True)
            convo[n] += [{"role": "assistant", "content": joined(n, story)},
                         {"role": "user", "content": repair_request(reports[n])}]
            reply, more = ask(convo[n], n, story, f"repair{attempt}")
            secs[n] += more
            usage[n].add(reply.usage, reply.cost)
            repaired[n] += 1
            save(reply.text.strip() + "\n", n, outline, story)
        reports.update(readable(story, verify(story, failing)))

    lines = [f"# Report · {outline['title']} · reader: {outline['reader']}\n",
             f"Change {outline['repo']['base'][:7]} → {outline['repo']['head'][:7]} · model: {llm.describe()}\n",
             "| # | chapter | kind | words | citations | proof on head | proof on base | repairs | errors | time | cost |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    kinds = {c["n"]: c["kind"] for c in outline["chapters"]}
    for n in ns:
        r, md = reports[n], chapter_files(story, n)[0]
        words = len(md.read_text().split()) if md else 0
        cell = lambda s: s.replace("|", "\\|")[:80]  # noqa: E731
        lines.append(f"| {n} | [{r.chapter}]({r.chapter}) | {kinds[n]} | {words} | {r.citations} | {cell(r.head)} "
                     f"| {cell(r.base)} | {repaired[n]} | {len(r.errors)} | {secs[n]:.0f}s | {money(usage[n].cost)} |")
    costs = [usage[n].cost for n in ns]
    total = None if any(c is None for c in costs) else sum(costs)
    lines.append(f"\n**Total:** {money(total)}, {sum(secs.values()):.0f}s, {sum(repaired.values())} repairs\n")
    for n in ns:
        r = reports[n]
        if r.errors or r.warnings:
            lines.append(f"\n## {r.chapter}")
            lines += [f"- ✗ {e}" for e in r.errors] + [f"- ! {w}" for w in r.warnings]
    (story / "report.md").write_text("\n".join(lines) + "\n")
    (story / "verify.json").write_text(json.dumps({str(n): {"head": r.head, "base": r.base, "errors": r.errors,
                                                            "warnings": r.warnings} for n, r in reports.items()},
                                                  indent=1) + "\n")  # the page shows each proof's outcome
    for n in ns:
        r = reports[n]
        print(f"  {n:2}. {'FAIL' if r.errors else 'ok  '} {r.chapter}: {r.citations} citations; proof head {r.head}, "
              f"base {r.base}" + (f"; {repaired[n]} repairs" if repaired[n] else ""))
        for e in r.errors:
            print(f"        ✗ {e}")
    return 1 if any(reports[n].errors for n in ns) else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    only = int(argv[argv.index("--only") + 1]) if "--only" in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1:i] != ["--only"]]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], only, repairs=0 if "--no-repair" in argv else REPAIRS))
