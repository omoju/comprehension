# comprehension · notes
*The project's memory between sessions. "Pick up here" is always current; below it: the plan, settled decisions,
lessons, a short log (newest first), and Omoju's opening paragraph. Code and git say what changed; this says why.*

## ▶ Pick up here (handoff, 2026-09-30 night)
**State.** CodeStories works end to end. itsdangerous has a complete 8-chapter owner story, all checks passing, on a
reading page with a control-flow chart of the run: https://claude.ai/artifact/JyeDNbyYZyMt1ivYxWwshL (private; source
`stories/itsdangerous-close-third/index.html`, rebuild with `render.py`). The other 9 repos (`stories/bench/`) have
scenarios (9/9 ran), compressed traces and owner outlines; **chapters are on hold** (Omoju). Everything is committed;
`PREREGISTRATION.md` was fixed at the first commit `2c65390`. No jobs running.

**First thing next session**
1. `git status` should be clean. If `demo-repos/` is missing: `sh codestory/restore_repos.sh` (exact commits in
   `demo-repos.lock`). Keys are in `.env` (not in git; copy `.env.example` if it's gone).
2. Ask Omoju the open decisions below before spending.

**Open decisions (Omoju)**
1. When to generate chapters for the 9 repos (≈ $40–60, ~15 min in parallel).
2. Outline length: they sprawl (requests 14, attrs 14, markupsafe 12 chapters for 499 lines). Add a length budget?
3. Self-story on this repo: `pyproject.toml`, `.codestoryignore`, then run.
4. A second, cross-vendor judge for the comparison (the code-review paper's cross-model point), or Jev + Claude only?
5. Keep the "note to Sha" reminder in `NOTES.md`, or move it out before the repo is published?
6. Optional: `PREREGISTRATION.md` §9 sentences on what "it helps" would feel like.

**Next work (Thursday 1 October), in parallel tracks**
- Re-plan or repair the 3 outlines failing the question-ID check (requests, httpx, tqdm).
- Stage 3 repair loop as a separate pass over existing chapters (failed checks → Claude, ≤2 tries). Would have
  handled both hand-fixed proofs.
- Fetch DeepWiki pages for all 10 via its public MCP server (`https://mcp.deepwiki.com/mcp`, tools
  `read_wiki_structure`, `read_wiki_contents`); record the commit each page describes.
- Eval harness: question writing (path + general), answer keys checked by execution, claim extraction, judge;
  test the judge on planted lies in *both* stories and DeepWiki pages before use.
- Monday, after the results page: remind Omoju to send Sha Ma a short note.

**Pipeline**, run from the root with `.venv/bin/python` (Python 3.13; keys in `.env`):
`codestory/scenario.py <repo> <dir>` → `outline.py <repo> <dir> --reader owner|maintainer|user` →
`chapter.py <dir> [--upto N]` (writes only missing chapters) → `render.py <dir>`.
Checks: `verify.py <dir>` (citations, drift, proofs), `claims.py <dir> <chapter>` (Jev contradiction judge).
Each repo gets its own environment at `demo-repos/<repo>/.codestory-venv` (created on first use).

**Spend so far:** ≈ $20 on Anthropic (≈ $10 to 09-30 noon, plus 8-chapter rewrite, 9 scenarios, 9 outlines), pennies on Jev.

## The plan to Tuesday 6 October
Question: is a CodeStory better than generated documentation? Head-to-head against DeepWiki on 10 pure-Python repos
(requests, flask, click, httpx, rich, attrs, itsdangerous, jinja, markupsafe, tqdm; itsdangerous is in-sample).
Arms: story / DeepWiki (via its MCP) / official docs. Measures: contradictions per 1k words (H1); reader-model QA
with execution-checked keys, path vs general questions (H2). **The formal rule in `PREREGISTRATION.md` decides**:
ship / pivot to stories of *changes* / kill.

| Day | Work | Status |
|---|---|---|
| Wed 30 | voice; full itsdangerous story; per-repo venv; trace-ordered context; preregistration | done, plus the reading page; repo list not yet approved |
| Thu 1 | repair loop; pilot 2 repos; self-story | |
| Fri 2 | run all 10; build the eval (questions, keys, DeepWiki + docs fetch) | |
| Sat 3 | run the head-to-head | |
| Sun 4 | buffer; Omoju reads 2–3 | |
| Mon 5 | results page, README (Claude drafts; posts are Omoju's); publish. **Then remind Omoju to send Sha Ma a short note** | |
| Tue 6 | decide by the rule | |

Cuts, in order: 10 → 5 repos; drop the docs arm; drop Omoju's reads.

**Context worth using in the write-up:** Sha Ma et al., "Agentic AI and Code Reviews: Toward a Pattern Language
for Code Reviews in the Age of Agentic AI" (*Enterprise Technology Leadership Journal*, Fall 2026, IT Revolution).
Code review's value includes knowledge sharing; the paper's patterns rebuild the *gate* (defects, risk, policy) but
not the knowledge sharing. CodeStories targets that half. Several of its patterns are already in the pipeline (shift
left, design for verification, context engineering, the quality loop, cross-model judging, durable records).

## Settled decisions
- **Claude writes the stories**, automatically, for any repo (09-23). Chapter count is whatever the journey needs (09-23).
- **The novella formula is the architecture**: a chapter is a function; its input is the data entering its span of the
  trace, its output is the data leaving (09-23, made concrete 09-25).
- **The reader is chosen per run** (`codestory/readers/`: maintainer, owner, user), each ending in "after reading,
  they can…", which doubles as the eval's question source (09-25).
- **The plot is a real run.** Claude writes the intended-use scenario; the harness runs it under `trace.py`
  (calls, args, returns, executed lines). Not a tour of modules (09-25).
- **Close third person following the main input**; setup is brief setting; reader advice goes in
  `> **For the <reader>:**` callouts (09-30).
- **Proofs live in `proofs/NN.py`**, not in the story (09-25). Only stdlib + the package (09-30).
- **Two models**: Claude writes and is the main judge; Jev (`typesafe/jev` on Cloudflare) makes cheap typed decisions,
  only after being tested on known answers (09-23).
- **The reading page** keeps: title, real-world premise, the control-flow chart of *this run*, code beside the text (09-30).
- **The formal decision rule decides** on 6 October; Omoju's read is recorded first but doesn't override it (09-30).
- **CLAUDE.md is about the prototypes only**; no personal context in the repo (09-30).

## Lessons (agentic engineering, with the evidence)
- **Context is the design surface.** First prompt: 79k tokens for a 1,200-line library, half of it `uv.lock`.
  Filtering generated files → 31k. Estimate with the tokenizer: chars/4 said 31k, reality was 49.9k.
- **The model fills gaps you leave.** No reader → it planned 15 chapters covering tests, typing and CI. With a reader → 10, then 8.
- **Design outputs so code can check them.** Free-text "answers" couldn't be checked; question IDs can.
- **Examples outweigh instructions.** The module-tour example chapter would have pulled the voice back; removed.
- **Order the prompt for the cache**: repo, then plan, then the changing part. Later calls read 50k tokens at a tenth of the price.
- **Test a judge before trusting it.** One "accurate?" question flagged 5 of 7 true paragraphs. Split into
  "contradicted" vs "supported": four planted lies scored 0.72–0.93, truths ≤0.27. Jev drifts ~0.03 on identical
  input, and two true paragraphs later scored 0.70/0.72, right at the cut-off: the judge needs the trace too.
- **Models game checkers.** A proof shipped `assert … or True`; the checker now rejects can't-fail asserts.
- **Route errors to whoever owns them; keep the instrument out of reach.** The tracer crashed (our Python 3.10
  bug), the loop blamed the script, and Claude "fixed" it by disabling the tracer: a green run with an empty trace.
  Now: tracer crashes stop the run; scenarios may not touch tracing hooks.
- **A check that doesn't stop the run isn't a check.** Outline span errors were printed and ignored; now they exit non-zero.
- **A green run can be wrong.** Every check compared against the code; none against the trace the story claimed to follow.
- **Ground truth beats inference.** The flowchart's decisions come from executed lines + the AST, not from a model.

## Log (newest first)
- **09-30 late** · Repo list approved (prereg §3). To derisk, the riskiest step moved from Friday to now: scenarios for
  all 9 new repos in parallel (`stories/bench/<repo>/`). **9/9 ran**, 8 first try (requests retried: imported the
  repo's tests). Network handled locally (requests: stdlib HTTP server; httpx: WSGITransport). Traces: 81–5,007
  calls (itsdangerous: 60). **Trace compression** added (`trace.compress`): fold comprehension/lambda frames,
  collapse repeated siblings (×N), cut depth to fit 800 lines; full trace kept as `trace.full.json`. rich
  10,024 → 706 lines, jinja 5,642 → 457, tqdm 2,123 → 610. Owner outlines for all 9 started in parallel.
- **09-30** · CLAUDE.md rewritten (prototypes only). Owner asides now marked callouts; ch1–8 regenerated ($1.84;
  previous in `old/`). Hand fix #2: ch3 proof used pytest. Map rebuilt as an old-school flowchart from executed lines
  (Omoju: "so much better"). Reading page built after Omoju, back after two days, couldn't place chapter 1.
  Close third person chosen; ch1–8 written ($2.10); hand fix #1: ch8's proof split a compressed token at the first dot.
  Preregistration drafted. Per-repo venv; context ordered by traced files. "Am I just recreating documentation?":
  docs are a claim by someone who understands the code; a CodeStory is evidence from a run, for code nobody
  understands. DeepWiki: structure-first generated docs, no described post-generation check; its best-known
  failure (an unpublished VS Code extension presented as the main install) is code that exists but never runs.
- **09-25** · Proofs moved to `proofs/`. Steps scenario → outline → chapters built; the first run was green and wrong
  (tracer disabled, kept in `stories/itsdangerous-journey-broken/`); fixed and rerun (`stories/itsdangerous-journey/`,
  first person, ch1–2). Omoju: wrong point of view ("a tour of modules") → follow the data through a traced run;
  "imagine… an abstract syntax tree, with main at the root… a story generated from the traversal of data through
  that tree." Stage 2 first chapters (`stories/itsdangerous-owner/`, ch1–4). Jev live; judge tested. Stage 1 ran
  (15 chapters, $0.64).
- **09-23** · Jev chosen for decisions. Claude writes; chapter count open; teach as we build (stages 1–5:
  one call → pipeline → repair loop → tool-using agent → evals). Hand-written chapter 1 + `verify.py`; drift test
  passed (change one default → the story fails, pointing at the passage).
- **09-22** · Project opened. Ship-or-kill 2026-10-06.

**What's in `stories/`**: `itsdangerous/` hand-written ch1 + `judge-tests/` (planted lies) ·
`itsdangerous-generated/` stage-1 outline (15 ch.) · `itsdangerous-owner/` module-tour ch1–4 (rejected) ·
`itsdangerous-data/` first hand-run trace · `itsdangerous-journey-broken/` the disabled-tracer run ·
`itsdangerous-journey/` first-person ch1–2 · **`itsdangerous-close-third/` current story and reading page**.

## Origin · Omoju's opening paragraph, verbatim (2026-09-23)

> CodeStories
> I am very interested in where code comprehension will go. I believe traditional code review is dead, and its unfair to have humans read code because it is boring for us humans to read code that we didn't write.
> I think there needs to be a new way of getting the knowledge of the code into our brains. And I think that system is to explore narrative, stories. Am calling this codebooks or codestories
>
> * Turn a repo into a cohesive story ala once upon a time.
> * Show me how we could do this together and ship a prototype.
> * I am new to this, I have written a novella before and I have a formula that I used to write it. I wrote the novella over 6 weeks or so, with six chapters, one a week. Used a function. thought of each chapter as a function, with a set of inputs and a set of outputs. The next chapter takes those inputs, builds on them and generates it own outputs and so on and so forth.
