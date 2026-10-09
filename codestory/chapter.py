"""Stages 2 and 3: write the chapters, in order, and repair the ones that fail their checks.

    .venv/bin/python codestory/chapter.py <story-dir> [--only N | --upto N] [--no-repair]

Reads <story-dir>/outline.json, scenario.py and trace.txt, writes NN-slug.md per chapter (the story) and
proofs/NN.py (its proof, kept out of the reader's way), then checks each one: citations and proofs (verify.py)
and contradictions (claims.py, Jev). A chapter that fails a deterministic check goes back to the model with the
errors, in the same conversation, up to REPAIRS times. Existing chapters are kept, rechecked and repaired the
same way, so a second run over a finished story is the stage-3 pass. The judge's verdicts are reported, not
repaired on: it has known false positives at the cut-off. Results go to <story-dir>/report.md; full model
responses to traces/ (NN.response.json, then NN.repairK.response.json).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import env  # noqa: F401  (loads .env)
from claims import judge_text
from jev import JevError, configured as jev_configured
import llm
import style
from outline import READERS, REPAIRS, numbered_trace, repo_block, scenario_text
from verify import TS_SPEC_DIR, check_text, read_proofs, repo_path, split_proofs, ts_setup, write_proofs

SYSTEM = """You write one chapter of a code story at a time. The story follows the data as it travels through the
code when the program is used as intended, told in close third person: the narrator stays with the data and sees
what happens to it, but is not the data. You are given the repository, the scenario (the intended use), a trace
of that real run with every call, argument and return value, the plan, and the reader the story is for.

The protagonist is the main input: the value the caller hands to the code (here, whatever the scenario passes in to
be processed). Setup that happens before it appears, such as constructing objects and choosing keys, is the world
it is about to enter: tell it briefly, as setting, and keep the protagonist in view.

The formula: each chapter is a function. It covers one span of the trace. It begins with the data exactly as it
enters that span and ends with the data exactly as it leaves, and the next chapter picks it up there. Use the real
values: the reader should see what the data looks like at the moments that matter. Follow the order things happen
in, but spend the words on the decisive moments and pass through the plumbing in a clause. Where the data passes a
branch it doesn't take, the narrator may say briefly what would have happened; stay on the road. Don't re-tell
earlier chapters; don't run ahead into later ones.

Voice: the functions and classes the data meets are the other characters; say what they do to it and why. Plain,
concrete, warm; never cute at the expense of accuracy. The reader's concerns decide where the story slows down
and explains *why* the code does what it does.

When the narrator turns to the reader about their own concerns (for an owner: a guarantee, a risk, a default to
question, something to check before signing off), put it in a callout of its own: a blockquote whose first words
are the reader's role in bold, like `> **For the owner:** …`. Keep the journey in the narration and the advice in
the callouts. Use them where they matter, typically one or two per chapter, never more than three. Callouts are
written plainly, in the manner of a technical instruction: one topic per sentence, active voice, and any action
for the reader as an imperative ("Check that your templates quote all attribute values"), not a suggestion.
The narration keeps its own voice; only the callouts change register.

{writing}

Accountability, which is not optional:
- Every claim about the code links to the exact lines that show it, as a permalink in this form:
  [text](REPO_URL/blob/COMMIT/path/to/file#L10-L14), with REPO_URL and COMMIT replaced by the values the request gives
  (COMMIT is a full 40-character hash; never write the word COMMIT, HEAD or a branch name). Line numbers must be the real
  ones from the numbered source you are shown. Link the lines that prove the claim, not a nearby area.
- Values you show must be the ones in the trace. Say only what the code and trace show; mark inference as such.
- End with a proof: a fenced code block whose info string is exactly the proof language given (for example
  ```python proof). It replays the scenario up to the end of this chapter's span and asserts the values the data
  had along the way, exactly as the trace records them. Use only the standard library and the repository's own
  package; test frameworks may not be installed. Every assert must be able to fail if the story were wrong:
  no `or True`, no `assert True`, no asserting a value equals itself.

Format: Markdown, starting with "# Chapter N · Title", then a one-line blockquote "**Enters as:** <data_in>",
then the story, then a blockquote "**Leaves as:** <data_out>", then the proof. Nothing else."""


SYSTEM = SYSTEM.replace("{writing}", style.WRITING)
CHAPTER_WORDS = 650  # a repository chapter carries more than a change's


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]


def proof_language(repo: Path, story: Path | None = None) -> str:
    """A TypeScript story (its scenario is a spec file) proves itself in its own test runner."""
    if story is not None and (story / "scenario.spec.ts").exists():
        return "ts"
    return "python" if any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")) else "sh"


# A TypeScript proof is a whole spec file, like the scenario; the runner is the one exception to the standard library.
PROOF_TS = {
    "vitest": ("the proof is a whole Vitest spec file, written like the scenario: `it` and `expect` from 'vitest' "
               "(installed: the one exception to the standard-library rule). It is saved as {path} and run from "
               "{where} with Vitest, so import the package's code exactly as the scenario does. It replays the "
               "scenario up to the end of this chapter's span and `expect`s the values the trace shows (written as "
               "JavaScript values); it must pass."),
    "japa": ("the proof is a whole Japa spec file, written like the scenario: `test` from '@japa/runner' (installed: "
             "the one exception to the standard-library rule), with `assert` from the test context. It is saved as "
             "{path} and run from {where} with `node ace test unit --files=<its name>`, the application booted as "
             "for any unit test, so import application code exactly as the scenario does; call `.timeout(10000)` on "
             "a test that needs longer than 2000 ms. It replays the scenario up to the end of this chapter's span "
             "and asserts the values the trace shows; it must pass."),
}


def chapter_request(n: int, outline: dict, repo: Path, story: Path, previous: str | None) -> list[dict]:
    """The user turn that asks for chapter n. Rebuilt byte-for-byte on a repair pass, so the cache still hits."""
    chapter = next(c for c in outline["chapters"] if c["n"] == n)
    info = outline["repo"]
    lang = proof_language(repo, story)
    profile = (READERS / f"{outline['reader']}.md").read_text()
    plan = json.dumps({k: outline[k] for k in ("title", "premise", "chapters")}, indent=1)
    if lang == "ts":
        ts = ts_setup(outline, repo)
        where = "the repository root" if ts["pkg"] == "." else f"{ts['pkg']}/"
        path = f"{'' if ts['pkg'] == '.' else ts['pkg'] + '/'}{TS_SPEC_DIR[ts['runner']]}codestory-proof-<id>.spec.ts"
        how = PROOF_TS[ts["runner"]].format(path=path, where=where)
    else:
        how = "the proof runs from the repository root" + (
            f" with PYTHONPATH={info.get('import_path', '.')}." if lang == "python" else ", with bash.")

    return [
        repo_block(repo, info, story),  # cached: same for every chapter
        {"type": "text", "cache_control": {"type": "ephemeral"},  # cached: same for every chapter of this story
         "text": (f"<scenario>\n{scenario_text(story)}\n</scenario>\n\n"
                  f"<trace>\n{numbered_trace(story)}\n</trace>\n\n"
                  f"<reader>\n{profile}\n</reader>\n\n<plan>\n{plan}\n</plan>")},
        {"type": "text", "text": (
            (f"<previous_chapter>\n{previous}\n</previous_chapter>\n\n" if previous else "")
            + f"Write chapter {n}: {chapter['title']}. It covers trace lines "
            f"{chapter['trace_lines'][0]}-{chapter['trace_lines'][-1]}.\n"
            f"REPO_URL = {info['url']}\nCOMMIT = {info['commit']}\n"
            f"Proof language: {lang}. The scenario is shown above; {how}"
        )},
    ]


def repair_request(errors: list[str]) -> str:
    return ("The chapter failed these checks:\n" + "\n".join(f"- {e}" for e in errors)
            + "\n\nReturn the whole corrected chapter, in the same format. Fix what the checks name: re-read the "
              "cited lines and fix the link or the claim, make the proof run and assert what the trace shows. Keep "
              "the span, the Enters/Leaves lines and everything that passed as they are.")


def response_text(reply) -> str:
    return reply.text.strip() + "\n"


def ask(messages: list[dict], n: int, story: Path, name: str):
    """One model turn; the full response (usage, model, the provider's raw answer) is kept in traces/."""
    start = time.time()
    reply = llm.ask(SYSTEM, messages, max_tokens=32000)
    (story / "traces").mkdir(exist_ok=True)
    (story / "traces" / f"{n:02}.{name}.json").write_text(json.dumps(reply.record(), indent=1))
    return reply, time.time() - start


def save_chapter(raw: str, n: int, outline: dict, story: Path):
    """Split the model's answer into the story (NN-slug.md) and its evidence (proofs/NN.py)."""
    chapter = next(c for c in outline["chapters"] if c["n"] == n)
    text, proofs = split_proofs(raw)
    path = story / f"{n:02}-{slug(chapter['title'])}.md"
    path.write_text(text)
    write_proofs(path, proofs)
    return path, text, proofs


def join_proofs(text: str, proofs: list[tuple[str, str]]) -> str:
    """The inverse of split_proofs: a chapter as the model would have written it, proofs at the end."""
    return text.rstrip() + "\n" + "".join(f"\n```{lang} proof\n{code}```\n" for lang, code in proofs)


def last_response(n: int, story: Path) -> Path | None:
    """The model's latest answer for chapter n: the repair if there was one, else the first response."""
    files = sorted((story / "traces").glob(f"{n:02}.*.json"), key=lambda p: (p.stem.count("repair"), p.stem))
    return files[-1] if files else None


class Usage:
    """Tokens and cost summed over a chapter's turns (first write plus repairs). Cost is None when the provider
    doesn't say (a Foundry deployment, the Codex CLI): the report then shows tokens only."""

    FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

    def __init__(self):
        for f in self.FIELDS:
            setattr(self, f, 0)
        self.cost: float | None = 0.0

    def add(self, u: dict | None, cost: float | None = 0.0) -> None:
        for f in self.FIELDS:
            setattr(self, f, getattr(self, f) + ((u or {}).get(f) or 0))
        self.cost = None if cost is None or self.cost is None else self.cost + cost

    def add_record(self, record: dict) -> None:
        """A turn kept in traces/: this module's records, or the Anthropic responses older stories kept."""
        u = record.get("usage") or {}
        if "provider" in record:
            self.add(u, record.get("cost"))
        else:
            p = llm.ANTHROPIC_PRICES
            self.add(u, ((u.get("input_tokens") or 0) * p["input"] + (u.get("cache_creation_input_tokens") or 0)
                         * p["cache_write"] + (u.get("cache_read_input_tokens") or 0) * p["cache_read"]
                         + (u.get("output_tokens") or 0) * p["output"]) / 1e6)


def money(cost: float | None) -> str:
    return f"${cost:.2f}" if cost is not None else "—"


def main(story_arg: str, only: int | None, upto: int | None = None, repairs: int = REPAIRS) -> int:
    story = Path(story_arg)
    outline = json.loads((story / "outline.json").read_text())
    repo = repo_path(outline)
    print(f"  model: {llm.describe()}")

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

        messages = [{"role": "user", "content": chapter_request(n, outline, repo, story, previous)}]
        usage, secs, repaired = Usage(), 0.0, 0
        existing = sorted(story.glob(f"{n:02}-*.md"))
        if existing and not only:  # resumable: a finished chapter is kept, rechecked and, if it fails, repaired
            path, text = existing[0], existing[0].read_text()
            proofs = read_proofs(path)
            last = last_response(n, story)
            if last:
                usage.add_record(json.loads(last.read_text()))
            raw = join_proofs(text, proofs)  # what the checker checked, hand edits included, stands as the model's turn
        else:
            reply, secs = ask(messages, n, story, "response")
            usage.add(reply.usage, reply.cost)
            raw = response_text(reply)
            path, text, proofs = save_chapter(raw, n, outline, story)

        v = check_text(text, path.name, outline, repo, cache, proofs)
        v.errors += style.check_links(text, outline["repo"]["url"]) + style.check_chapter(text, CHAPTER_WORDS)
        # Stage 3: the chapter goes back with its verdict, in the same conversation, while the context is cached.
        # Only deterministic failures count; the judge below is reported, not acted on.
        while v.errors and repaired < repairs and raw is not None:
            repaired += 1
            print(f"      ✗ {len(v.errors)} check errors, repair {repaired}/{repairs}: {v.errors[0]}", flush=True)
            messages += [{"role": "assistant", "content": raw}, {"role": "user", "content": repair_request(v.errors)}]
            reply, more = ask(messages, n, story, f"repair{repaired}")
            secs += more
            usage.add(reply.usage, reply.cost)
            raw = response_text(reply)
            path, text, proofs = save_chapter(raw, n, outline, story)
            v = check_text(text, path.name, outline, repo, cache, proofs)
            v.errors += style.check_links(text, outline["repo"]["url"]) + style.check_chapter(text, CHAPTER_WORDS)
        previous = text

        if jev_configured():
            try:
                judged = judge_text(text, outline, repo)
            except JevError as e:  # the judge is advisory: a failure is reported, not fatal
                judged, judge_note = [], f"judge failed: {e}"
            else:
                judge_note = ""
        else:
            judged, judge_note = [], "judge skipped: no Cloudflare keys in .env"
        lies = [j for j in judged if j["failed"]]
        rows.append({"n": n, "file": path.name, "words": len(text.split()), "citations": v.citations,
                     "proofs": v.proofs, "errors": v.errors, "contradicted": lies, "judged": len(judged),
                     "seconds": round(secs), "cost": usage.cost, "repairs": repaired, "judge_note": judge_note})
        status = "ok" if not (v.errors or lies) else f"{len(v.errors)} check errors, {len(lies)} contradicted"
        if repaired:
            status += f" after {repaired} repair{'s' if repaired > 1 else ''}"
        print(f"  {n:2}. {path.name}  {len(text.split())} words, {v.citations} citations, {secs:.0f}s, "
              f"{money(usage.cost)}  → {status}", flush=True)

    lines = [f"# Report · {outline['title']} · reader: {outline['reader']}\n",
             "| # | chapter | words | citations | repairs | check errors | contradicted ¶ | time | cost |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        judged = f"{len(r['contradicted'])}/{r['judged']}" if r["judged"] or not r["judge_note"] else "—"
        lines.append(f"| {r['n']} | [{r['file']}]({r['file']}) | {r['words']} | {r['citations']} | {r['repairs']} "
                     f"| {len(r['errors'])} | {judged} | {r['seconds']}s | {money(r['cost'])} |")
    costs = [r["cost"] for r in rows]
    total = None if any(c is None for c in costs) else sum(costs)
    lines.append(f"\n**Total:** {money(total)}, {sum(r['seconds'] for r in rows)}s, "
                 f"{sum(r['repairs'] for r in rows)} repairs · model: {llm.describe()}\n")
    notes = {r["judge_note"] for r in rows if r["judge_note"]}
    if notes:
        lines.append("Contradiction judge: " + "; ".join(sorted(notes)) + "\n")
    for r in rows:
        if r["errors"] or r["contradicted"]:
            lines.append(f"\n## {r['file']}")
            lines += [f"- ✗ {e}" for e in r["errors"]]
            lines += [f"- contradicted ({j['contradicted']:.2f}): “{j['first']}…”" for j in r["contradicted"]]
    (story / "report.md").write_text("\n".join(lines) + "\n")
    return 1 if any(r["errors"] for r in rows) else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    flag = lambda f: int(argv[argv.index(f) + 1]) if f in argv else None  # noqa: E731
    only, upto = flag("--only"), flag("--upto")
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1:i] not in (["--only"], ["--upto"])]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], only, upto, repairs=0 if "--no-repair" in argv else REPAIRS))
