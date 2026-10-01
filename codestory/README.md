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
