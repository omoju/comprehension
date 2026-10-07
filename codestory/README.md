# The CodeStories pipeline

A repository and a reader go in; a reading page comes out. Four stages, run from the root with `.venv/bin/python`
(keys in `.env`). Each script's docstring says how to run it. Blue is a model stage; amber is its deterministic
check, which hands failures back to the model in the same conversation, a bounded number of times.

```mermaid
flowchart TD
    A0[Repository at a pinned commit<br/>+ reader profile]
    A0 --> S1

    S1[1 · scenario.py<br/>Claude writes the intended use]
    S1 <-->|fails → retry ≤3| C1{{trace.py runs it<br/>gates: no tampering, harness alive, ≥5 calls}}
    S1 --> A1[scenario.py + trace.txt<br/>every call, its arguments, its return]

    A1 --> S2[2 · outline.py<br/>Claude plans chapters as spans of the trace]
    S2 <-->|fails → repair ≤2| C2{{check_plan<br/>spans in order · every question answered once<br/>≤10 chapters, each ≥5 calls}}
    S2 --> A2[outline.json<br/>title · premise · chapters]

    A2 --> S3[3 · chapter.py<br/>Claude writes each chapter, given the previous one]
    S3 <-->|fails → repair ≤2| C3{{verify.py<br/>citations exist · code unchanged · proofs run}}
    S3 -.->|advisory| J[claims.py — Jev judge<br/>contradiction per paragraph, reported only]
    S3 --> A3[NN-slug.md + proofs/NN.py + report.md]

    A3 --> S4[4 · render.py<br/>no model: flowchart from executed lines + AST]
    S4 --> A4[index.html<br/>premise · map of this run · code beside the text]

    classDef model fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef check fill:#fef3c7,stroke:#d97706,color:#78350f
    classDef judge fill:#f3f4f6,stroke:#6b7280,color:#374151
    class S1,S2,S3,S4 model
    class C1,C2,C3 check
    class J judge
```

## What flows where

| Stage | Reads | Model call | Check (deterministic) | Writes |
|---|---|---|---|---|
| 1 `scenario.py` | repo (filtered, cached) | "write the intended use" → script | `trace.py` runs it: no tracing hooks touched, tracer alive, ≥ 5 calls into the repo | `scenario.py`, `scenario.json`, `trace.full.json`, compressed `trace.json` + `trace.txt` |
| 2 `outline.py` | repo, scenario, numbered trace, reader | "plan the story" → JSON plan | `check_plan`: spans well-formed, ordered, non-overlapping; questions answered exactly once by a later chapter; ≤ `MAX_CHAPTERS`, each ≥ `MIN_CALLS` | `outline.json` (+ `outline.response*.json`, `outline.prev.json` on repair) |
| 3 `chapter.py` | repo, scenario, trace, reader, plan, previous chapter | "write chapter N" → Markdown + proof | `verify.py`: every permalink points at real lines at the pinned commit, those lines are unchanged, every proof runs and can fail | `NN-slug.md`, `proofs/NN.py`, `report.md`, `traces/NN.*.json` |
| 3 (advisory) | each citing paragraph + its cited lines | Jev: "is any claim contradicted?" | none; a judge with known false positives at the cut-off is reported, never repaired on | column in `report.md` |
| 4 `render.py` | outline, chapters, `trace.json`, repo source | none | n/a | `index.html` |

## The shape of a stage

Every model stage is the same loop:

1. Build the prompt with the stable part first (the repository, marked for caching), the changing part last.
2. Call the model.
3. Run a check that code can decide.
4. If it fails, append the model's answer and the check's verdict to the same conversation and ask again, at most
   `REPAIRS` times. The cached repository makes the retry cost a fraction of the first turn.
5. A stage that still fails exits non-zero. Nothing flows on to the next stage on trust.

The checks are the design: the model fills whatever gap the check leaves, so each check says what we actually want
(a minimum of calls per chapter, not just a cap on their count; an assert that can fail, not just an assert).

## A change instead of a repository

`review.py` tells the story of a change: a pull request, or any base and head. The repository explainer follows one
run of a repo's intended use; a change has its own intended use, the tests that come with it, so those tests are run
twice, on the base and on the head, and the story follows the same data through both versions.

```bash
.venv/bin/python codestory/review.py demo-repos/ufo --pr 313    # or --base <rev> --head <rev>
```

| Stage | Reads | Model call | Check (deterministic) | Writes |
|---|---|---|---|---|
| 1 `diff.py` | the change; its specs | none | the specs run under the tracer on a worktree of each side; the head's specs run on the base too, with imports of what the change adds softened to `undefined` | `changes.json` (changed functions per file), `trace.base.json`, `trace.head.json`, `diff.txt` (the merged run: `+` only after, `-` only before, `~` other values, ` *` an edited function), `diff.json` (each test before and after; changed functions the run never reaches), `diff.tree.json` |
| 2 `diff_outline.py` | diff, both sides of every changed file, `diff.txt`, the evidence, reader | "plan the change story" → JSON plan | `check_diff_plan`: spans as before; every chapter covers a marked line; every changed function the run reaches is explained; every test that fails before and passes after is claimed as evidence; every function the run never reaches is listed as unexercised | `outline.json` (mode `diff`) |
| 3 `diff_chapter.py` | the same, plan, previous chapter | "write chapter N" → Markdown + a whole spec file | `diff_verify.py`, for all chapters at once: permalinks name the base or the head and point at real lines there; each proof passes on the head, and a "changed" chapter's fails on the base (one that passes on both proves nothing) | `NN-slug.md`, `proofs/NN.ts`, `report.md`, `verify.json` |
| 4 `render.py` | all of the above | none | n/a | `index.html`: the verdict and the evidence, the map of the change, chapters with Before/After, the code of either side |

`diff_verify.py <story> --against <rev>` rechecks a finished story against a newer push: cited lines are matched by
content, so code that only moved is reported as moved, not changed.

## TypeScript, and a change's two runs

`codestory/ts/` traces TypeScript and JavaScript (Node 20.6 or later). `register.mjs` installs a module loader hook
ahead of the package's own TypeScript loader, and `instrument.mjs` rewrites each named function as
`return __cs$(…, () => { body })` without adding a line, so every line number stays the file's own and a permalink
needs no source map. `runtime.mjs` records the calls (with AsyncLocalStorage, so awaited calls nest under their
caller) in `trace.py`'s shape, and, through `coverage.mjs`, the lines each test ran (V8 coverage, mapped back through
the source maps). A test is the root of a run: the calls made while it runs are what is recorded. Two test runners
so far: Japa, for AdonisJS (`register.mjs`), and Vitest, for Vite and Vue, `.vue` script blocks included
(`vite-plugin.mjs`, `vitest-run.mjs`; run `npm install --legacy-peer-deps` in `codestory/ts/web` once, so the traced
repository needs no test runner of its own).

`diff.py` uses it to trace a change. It checks out the base and the head as worktrees, runs the head's tests on both
(on the base, imports of what the change adds become `undefined`, so only the tests that use them fail), and compares
the two runs call by call:

```bash
python3 codestory/diff.py <repo> <base> <head> <out-dir> --pkg <package> --spec <test file> [--runner vitest]
```

It writes the merged run (`diff.txt`: `+` happens only after the change, `-` only before, `~` is the same call with
other values, ` *` marks a function the change edited), each test's outcome before and after, and the changed
functions no test reaches. No model is involved. `decisions.mjs` is `render.py`'s branch finder for
TypeScript: which way each `if`, `switch` and `try` went, from the lines a test ran.

## Models

`llm.py` is the one place a stage asks a model. `CODESTORY_PROVIDER` chooses how you sign in (see `.env.example`):
`anthropic` (an API key), `claude-cli` (your Claude login, through the Claude Code CLI), `codex-cli` (your ChatGPT
login, through the Codex CLI), or `foundry` (a deployment on Azure AI Foundry, with a key or your
`az login`). The CLIs sign in for us: their own login and terms apply, and nothing here reads their credentials.
The `anthropic` provider marks the repository block for prompt caching and asks for server-side fallback; the CLIs
and Foundry cache on their own terms. A CLI on a subscription reports what the API would have charged; Foundry and
Codex report tokens only.
