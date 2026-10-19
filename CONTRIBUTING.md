# Contributing to comprehension

Thanks for arriving. This file says where the project is going, what help is wanted, and how to work here. The
README has the short version; `NOTES.md` has the decisions and the lessons; `codestory/README.md` has the pipeline.

## Where it is going

1. **Stories of libraries** (done, being refined): one real run of a repository's intended use, told as a story with
   every claim pinned to lines and a proof per chapter. `codestory/story.py <repo>` does it in one command.
2. **Stories of changes** (under way): `codestory/review.py` runs a pull request's own tests on the base and the head
   and tells the change: what it makes true, what it keeps true, and what no test reaches. Python with pytest and
   TypeScript/JavaScript with Japa or Vitest work today.
3. **Stories of applications** (next): record one run of a running system (its requests, its clock, its external
   calls) and replay the recording, so a story can follow a request through a service without the world attached.

Every cycle starts with a preregistration (`PREREGISTRATION.md` is cycle 1's): hypotheses, measures and a kill rule,
committed before any result exists. Cycle 1's rule said kill on accuracy and the comprehension result was strong;
both are published. Cycle 2's preregistration is being written; its first candidate is the judge below.

## What help is wanted

### Run it on a repository you know, and report what's wrong
The most valuable contribution, and it needs no code. Make a story of a repository you understand well, read it,
and open an issue for each thing that is wrong. Include: the repository and commit; the story's chapter and the
sentence; the lines it cites; what is actually true; and, if you can, a proof (a few lines that run) of the true
behaviour. The pipeline's checks pin lines and values; they do not read the sentence, so this is how the sentences
get checked.

### Test runners for `review.py`
A runner is three things: an entry in `RUNNERS` in `codestory/diff.py` (how to run one test file, with
`CS_TRACE_OUT`, `CS_INCLUDE` and `CS_LINES` in the environment); a tracer that records one run per test in
`trace.py`'s shape (`codestory/py/pytest_trace.py` for pytest, `codestory/ts/` for Node); and a proof format the
verifier can run on both sides (`diff_verify.py`: the fence name, the file name the runner will collect, where it is
saved). Wanted: Jest, Mocha, Go test, cargo test, JUnit, RSpec.

### Tracers for other languages
`trace.py` is the Python tracer; its output shape is the contract: a tree of calls, each with `fn`, `file`, `line`,
`args` (short reprs), `calls`, `returned` or `raised`, and at the root `lines` (file → line numbers that ran). A tracer
for Go, Rust, Ruby or Java that writes that shape makes every later stage work for that language. The TypeScript one
(`codestory/ts/`) shows an instrumentation approach; the Python one uses the interpreter's hooks.

### The contradiction judge inside the pipeline
`codestory/eval/judge.py` labels claims against the source, blind, and was tested on planted lies before use. It
caught the ten wrong sentences cycle 1's checks missed. Making it a stage-3 check in `chapter.py` (claims extracted
from a chapter, judged with the cited source in view, failures sent back with the repair loop) is the first cycle 2
candidate. It needs: extraction per chapter, a cost budget, and a test that the loop doesn't rewrite true sentences.

### Reader profiles
`codestory/readers/*.md` decide what a story slows down for and what the callouts are about. Each ends with "after
reading, they can…", which doubles as the evaluation's question source. Wanted: a security reviewer, an on-call
engineer, a newcomer in their first week.

### Applications
Recording and replay. Open an issue first; this one needs a design conversation.

## How to work here

- **Open an issue first** for anything beyond a small fix, so the shape is agreed before the work.
- **Branch and pull request.** `main` is not pushed to directly. One change per PR, with a description someone can
  read in a minute.
- **CI** runs `python3 codestory/verify.py --no-proofs stories/*/`: every story's citations must still point at
  real, unchanged lines at its pinned commit. Proofs are not run in CI (they need each repository's own
  environment); run them locally with `verify.py <story>` when you touch a story.
- **Plain formats, swappable models.** Markdown, JSON and git permalinks; `codestory/llm.py` is the one place a
  model is asked, and four providers already plug in there. Nothing that only works inside one vendor's platform.
- **Public by default.** No secrets (`.env` is ignored and must stay so), no private data, no real people's
  details. A story of private code goes under `stories/private/`, which is ignored.
- **Checks before generation.** A model output gets a deterministic check wherever one is possible; a model judge
  only for what's left, and a judge is tested on known answers before it is trusted. If you add a model call, say
  what checks its output.
- **Contributor License Agreement.** Your first pull request will get a comment asking you to read
  [`CLA.md`](CLA.md) and accept it by replying with one sentence; a check blocks merge until then. You keep your
  copyright; you grant the maintainer the rights needed to relicense or move the project (to a foundation, say)
  without tracking down every contributor. It is adapted from Apache's individual CLA.
- **Hand-written or agent-written, both welcome.** The rule "Claude writes the code" in `CLAUDE.md` describes how
  this repository was made, not a requirement on you. Write however you work; the diff, the tests and the checks
  are what's reviewed. Say in the PR whether an agent wrote the change.

## Getting set up

Python 3.13 and `uv`; a model (see `.env.example`; the simplest path is an Anthropic API key). Then the commands in
the README. A story of a small library costs $2–6 and takes 10–25 minutes; a change story about the same.
