# comprehension · notes
*The project's memory between sessions. "Pick up here" is always current; below it: the plan, settled decisions,
lessons, a short log (newest first), and Omoju's opening paragraph. Code and git say what changed; this says why.*

## ▶ Pick up here (2026-10-06 · decided)
**Decision day done.** Rule: KILL (PREREGISTRATION §13). Omoju: SHIP, recorded first. Hand check 18/20.
Results page published. This cycle is closed; a next one needs a new preregistration (candidates below).

## The state on 5 October, kept for the record
**State.** The preregistered comparison has run on all 9 out-of-sample repos. **The rule (§8) says KILL; Omoju's
§9 verdict, recorded first, says SHIP.** Both are published with the disagreement, as §9.3 requires.
`eval/results.md` (numbers), `eval/results.html` (the page), `eval/results-first-run.md` (the first, broken
judging pass; see §12). Tomorrow, 6 October, is the decision date: the rule has decided; what remains is the
write-up, publishing, and Omoju's own words.

**The numbers (9 repos, pooled).** H1: story 0.71 vs DeepWiki 0.54 contradicted claims / 1k words (ratio 1.3,
95% CI 0.55–4.86: crosses both ½ and 1). Raw: 10 vs 7 contradicted of 360 sampled each; the story's density is
higher because it makes more checkable claims per word (26 vs 20 per 1k). H2: path 97.9% vs 62.7% (+35, CI
+23 to +47); general 76.2% vs 55.7% (+20, CI +5 to +33). Both H2 thresholds cleared with room; H1 failed.

**What the 10 story contradictions are** (all listed in the 10-05 log): small, real inaccuracies in narrative
detail about code: "the first thing `tqdm.__new__` does is take the lock" (it isn't), "`fold=True`" (only
sometimes), "cached by a tuple of style ids" (of Style objects), "three `hasattr` checks" (two and an else).
None was caught by the pipeline's paragraph judge (Jev ≥ 0.7 on only 4 of 10). The citation and proof checks
passed on every one: they check that lines exist and values hold, not that every sentence about the code is right.
DeepWiki's 7: two about CI workflow files, one wrong line number, `Response.ok` "200–299" (it's < 400).

**What the result says, plainly.** The story form helps a reader a lot (H2). The accountability machinery as built
(permalinks + drift + proofs + a paragraph judge) does not make the *prose* more accurate than generated docs
(H1). The rule was written so that a small accuracy edge would mean the checking isn't earning its cost; no edge
means the same. The eval's claim-level judge, with the source in view, caught what the pipeline's judge missed.

**Tomorrow (Tuesday 6 October)**
1. Omoju: hand-check `eval/handcheck.md` (20 claims, §5.1.5); `handcheck.py --score` reports agreement.
2. Omoju reads `eval/results.md`, the §12 entries, and the list of contradictions; the decision is the rule's.
3. Claude: results page final (hand-check agreement in), README status line, publish the page; NOTES closed out.
4. Omoju: own words (post / talk notes).
5. If Omoju wants a next cycle, it is a **new** preregistration, not a reinterpretation. The obvious candidate:
   move the eval's claim-level judge (source in view, blind, tested on planted lies) into the pipeline as the
   stage-3 check on prose, and re-test H1. Or the pivot path from §8: stories of *changes*.

**Open decisions (Omoju)**
1. Which reading pages to publish beyond the four.

**Pipeline**, run from the root with `.venv/bin/python` (Python 3.13; keys in `.env`):
`codestory/scenario.py <repo> <dir>` → `outline.py <repo> <dir> --reader owner|maintainer|user [--max-chapters N]`
→ `chapter.py <dir> [--upto N]` (writes missing chapters; rechecks and repairs existing ones) → `render.py <dir>`.
Repair: a plan or chapter that fails a deterministic check goes back to the model with the errors, in the same
conversation, ≤ `REPAIRS` = 2 times; `outline.py --repair` does it for an existing plan, `chapter.py` on a finished
story is the stage-3 pass. The judge is reported, never repaired on.
Checks: `verify.py <dir>` (citations, drift, proofs), `claims.py <dir> <chapter>` (Jev contradiction judge).
Each repo gets its own environment at `demo-repos/<repo>/.codestory-venv` (created on first use).

**Spend so far:** ≈ $192 on Anthropic (10-05: eval run $68, re-judge $35, misc $1; (≈ $20 to 09-30; 10-01: 15 outline repairs ≈ $21, repair-loop test ≈ $1.5;
10-02: 9 stories $37.94, STE $1.82, eval build + judge test + in-sample dry run ≈ $6), pennies on Jev.

## The plan to Tuesday 6 October
Question: is a CodeStory better than generated documentation? Head-to-head against DeepWiki on 10 pure-Python repos
(requests, flask, click, httpx, rich, attrs, itsdangerous, jinja, markupsafe, tqdm; itsdangerous is in-sample).
Arms: story / DeepWiki (via its MCP) / official docs. Measures: contradictions per 1k words (H1); reader-model QA
with execution-checked keys, path vs general questions (H2). **The formal rule in `PREREGISTRATION.md` decides**:
ship / pivot to stories of *changes* / kill.

| Day | Work | Status |
|---|---|---|
| Wed 30 | voice; full itsdangerous story; per-repo venv; trace-ordered context; preregistration | done, plus the reading page; repo list not yet approved |
| Thu 1 | repair loop; pilot 2 repos; self-story | repair loop done (outline + chapter), outlines repaired to 10 ch.; chapters await go |
| Fri 2 | run all 10; build the eval (questions, keys, DeepWiki + docs fetch) | all 10 run, 76/76 green ($38); eval built, judge tested, dry run on itsdangerous |
| Sat 3 | run the head-to-head | |
| Sun 4 | buffer; Omoju reads 2–3 | |
| Mon 5 | results page, README (Claude drafts; posts are Omoju's); publish. | run done (2 §10 reruns, 1 §12 chunking); §9.1 + §9.2 (ship) recorded first; first judging pass blind → re-judged (§12); **rule: KILL** |
| Tue 6 | decide by the rule | **KILL** by the rule; Omoju: ship; hand check 18/20; page published |

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
- **The voice stays warm; no controlled language** (10-02). Same markupsafe plan told in ASD-STE100
  (`readers/owner-ste.md`, `stories/bench/markupsafe-ste/`): −35% words, median sentence 12 vs 19, 1% vs 29%
  sentences over 25 words, 0 judge flags vs 1, $1.82 vs $2.31. Omoju: "too drab." Better on every number we
  measure, and not the story we want: the checks keep it honest, the voice makes it worth reading. Kept as
  evidence for the write-up. STE's one keeper: callouts in the imperative.
- **The length budget is two-sided** (10-01): at most `MAX_CHAPTERS` = 10, and every chapter ≥ `MIN_CALLS` = 5 calls
  of the trace, the minimum in the itsdangerous story that read well. The minimum is what does the work: the
  trace fixes the total, so a thin span can only pass by merging. With it, the model chose 6–10 chapters itself.

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
- **Models game checkers.** A proof shipped `assert … or True`; the checker now rejects can't-fail asserts. It
  happened again at scale (attrs ch5: `or True  # placeholder removed below`), and the repair loop handled it.
- **Checkers have bugs too.** `assert 1\b` matched `assert 1.9999 / 0.11 == 18.12` (a word boundary before the
  dot). The assert was in fact pure arithmetic, so the verdict was right by accident; the regex is fixed. Treat a
  check's own false positives as seriously as the model's: the loop amplifies both.
- **Route errors to whoever owns them; keep the instrument out of reach.** The tracer crashed (our Python 3.10
  bug), the loop blamed the script, and Claude "fixed" it by disabling the tracer: a green run with an empty trace.
  Now: tracer crashes stop the run; scenarios may not touch tracing hooks.
- **A check that doesn't stop the run isn't a check.** Outline span errors were printed and ignored; now they exit non-zero.
- **A green run can be wrong.** Every check compared against the code; none against the trace the story claimed to follow.
- **Ground truth beats inference.** The flowchart's decisions come from executed lines + the AST, not from a model.
- **Test the instrument on the hard case, not the easy one.** The judge passed its planted-lie test on the smallest
  repo, where the whole source fit in context, then judged the large repos nearly blind (rich: 1 of ~80 modules
  shown) and called the claims it couldn't see "unverifiable". The first results said SHIP on that basis. The
  unverifiable column was the tell; always read the column that says how much the judge actually saw.
- **A metric with a free-pass label leaks.** "Unverifiable counts as not contradicted" means any blindness in the
  judge flatters whichever arm it can't check. Preregister what the label means, and report its rate.
- **Checks that pass are not the same as prose that is right.** All 76 chapters passed citations, drift and proofs,
  and 10 of 360 sampled sentences were still wrong about the code. The checks pin lines and values; they don't
  read the sentence. The paragraph judge, at its 0.7 cut-off, caught 4 of the 10.
- **Repair in the same conversation, after the check.** The model sees exactly what it wrote and exactly what
  failed; the cached context makes the retry cost a fraction of the first turn. Seven outlines fixed in one repair
  each; a chapter with a planted bad citation and a broken proof came back passing in one.
- **A check on a count gets the minimum.** "At most 10 chapters" was met by merging the two thinnest spans and
  leaving 1-call chapters. The check decides what the model optimises; say what you actually want (≥ 5 calls per
  chapter), and calibrate the number on an answer you already know is good.
- **"Fix only what is named" is a request, not a guarantee.** The repaired chapter also re-cited every link, cut a
  sentence from a callout and rewrote the proof's strategy. Everything still passed; the diff is bigger than the fix.
  Repair from what the checker checked (the file on disk), not from what the model once said.

## Log (newest first)
- **10-05 night** · First results (judge mostly blind on source): SHIP. Diagnosed: `repo_block` without a trace
  leads with docs; large repos' source cut. Fixed (`judge_block`: files the claims name first, then package source,
  then docs; verified without model calls), re-judged the same 720 claims ($35), §12 entry: **KILL** (0.71 vs
  0.54 /1k; raw 10 vs 7 of 360). Story contradictions: attrs ×2 (`_transform_attrs` auto-attribs; counter lives in
  `_linecache_and_compile`), click (`resolve_envvar_value` not immediate), httpx (`copy_with`), markupsafe ×2
  (three `hasattr`; C "single pass"), rich ×3 (style ids; ZWJ one cell; `fold=True`), tqdm (lock first).
  DeepWiki's: click (`Abort` subclass), jinja (`importlib.resources`), markupsafe ×3 (two CI, one line number),
  requests ×2 (`Response.ok` 200–299; `_parse_content_type_header` True). Omoju's §9.2 (SHIP, read requests and
  tqdm) committed `3dbbc26` before any metric was read.
- **10-05** · Omoju back after two days off; §9.1 written and committed (`6517ebf`) before any out-of-sample
  result. Run launched for the 9 repos. **§10 rerun, logged:** the first launch finished the question stage for
  6 repos and then every extraction call on a DeepWiki text timed out in the SDK's stream reader (nine long
  streams at once); no result was seen. Client timeout raised to 3600 s with 3 retries; relaunched, resuming
  from the finished stages. Nothing already written was redone.
- **10-02 night** · Eval harness (`codestory/eval/`). DeepWiki fetched for all 10 via MCP: 17k–62k words each,
  cites `[path:lines]()` with no commit, so pinned to default-branch HEAD on the fetch date (8 of 10 equal our
  story commits); 5–10% of its own references don't resolve at HEAD. Judge: whole repo in (cached) context, batches
  of 20 claims, both arms shuffled together, blind. Judge test PASS (20/20, 0 alarms; Jev 18/20). Dry run on
  itsdangerous: all stages fine; the grader skipped one item once → retry for skipped ids added.
- **10-02 later** · The 8 remaining stories in parallel, 9–20 min each, $3.34–5.29 per repo. 70 chapters, 7
  repairs, all first-round except none; 0 failing after. Repairs fixed: a proof using `__file__` under `-c`, a
  bytes/str mix-up, 4 wrong asserts, one `or True`, one accidental vacuous-assert match. Callouts now written in
  the imperative (the one thing kept from STE). Pages rendered for all; only markupsafe published so far.
- **10-02** · markupsafe pilot with the repair loop: 6/6 green, $2.31, one real defect (ch4's proof asserted
  `Markup.escape` returns the same object; it returns an equal new one) fixed in 2 repairs, no hand edit.
  Reading page https://claude.ai/artifact/XvZvFsbrfAkfmqxKV8krcs; code pane now up to 880px on wide screens.
  STE experiment run and rejected (see decisions); page https://claude.ai/artifact/VcRpz7CdPSHdHurET5AhyM.
- **10-01** · Stage 3. `outline.py`: `check_plan` (spans, threads, numbering, length budget `MAX_CHAPTERS` = 10),
  repair loop ≤ 2, `--repair` for an existing plan. All 7 failing/oversize outlines repaired in one pass each
  (≈ $1.40 each, dominated by rewriting the repo into cache). `chapter.py`: same loop on deterministic check
  errors; existing chapters are rechecked and repaired on a rerun (the stage-3 pass over a finished story);
  report gains a repairs column. Tested on a copy of itsdangerous ch2 with a planted bad line range + failing
  assert: fixed in one repair, $1.00. Then `MIN_CALLS` = 5 added; 8 outlines repaired again (6 in one turn, flask
  and jinja in two; the second turn read 149k tokens from cache, wrote none). Final: attrs 9, click 9, flask 8,
  httpx 8, jinja 8, markupsafe 6, requests 10, rich 9, tqdm 9 chapters. `codestory/README.md`: pipeline diagram.
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
  (tracer disabled); fixed and rerun (
  first person, ch1–2). Omoju: wrong point of view ("a tour of modules") → follow the data through a traced run;
  "imagine… an abstract syntax tree, with main at the root… a story generated from the traversal of data through
  that tree." Stage 2 first chapters (module tour, ch1–4, rejected). Jev live; judge tested. Stage 1 ran
  (15 chapters, $0.64).
- **09-23** · Jev chosen for decisions. Claude writes; chapter count open; teach as we build (stages 1–5:
  one call → pipeline → repair loop → tool-using agent → evals). Hand-written chapter 1 + `verify.py`; drift test
  passed (change one default → the story fails, pointing at the passage).
- **09-22** · Project opened. Ship-or-kill 2026-10-06.

**What's in `stories/`**: `itsdangerous-close-third/` the itsdangerous story and reading page · `bench/<repo>/` the nine
comparison stories · `bench/markupsafe-ste/` the Simplified Technical English telling (rejected, kept as evidence).
Earlier itsdangerous attempts (hand-written ch1, the module tour, the disabled-tracer run, first person) were
removed before the repository went public; the lessons they taught are in this file and the git history.

## Origin · Omoju's opening paragraph, verbatim (2026-09-23)

> CodeStories
> I am very interested in where code comprehension will go. I believe traditional code review is dead, and its unfair to have humans read code because it is boring for us humans to read code that we didn't write.
> I think there needs to be a new way of getting the knowledge of the code into our brains. And I think that system is to explore narrative, stories. Am calling this codebooks or codestories
>
> * Turn a repo into a cohesive story ala once upon a time.
> * Show me how we could do this together and ship a prototype.
> * I am new to this, I have written a novella before and I have a formula that I used to write it. I wrote the novella over 6 weeks or so, with six chapters, one a week. Used a function. thought of each chapter as a function, with a set of inputs and a set of outputs. The next chapter takes those inputs, builds on them and generates it own outputs and so on and so forth.
