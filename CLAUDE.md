# comprehension · working rules

## What this is
Prototypes for the future of code comprehension, by Omoju Miller. The premise: reading code you didn't write is slow
and unrewarding, more and more code is written by agents and read by nobody, and traditional code review doesn't
scale to that. Comprehension has to become something you can check, not something you take on trust.

The first prototype is **CodeStories**: a repository explained as a story that follows its data through one real run
of its intended use. Every claim links to the exact lines at a pinned commit, every chapter has an executable proof,
and the story fails like a test when the code changes. Started 2026-09-22. **Ship-or-kill date: Tuesday 6 October
2026**, decided by the rule in `PREREGISTRATION.md`.

## Rules
- **Two-week cycles, a date, a kill criterion.** Cut scope before moving the date. Set the kill rule before seeing results.
- **Protocols, not lock-in.** Plain formats (Markdown, JSON, git permalinks) and swappable models. Nothing that only
  works inside one vendor's platform.
- **Smallest demonstration first.** Working on real repositories beats a document. Demo before docs.
- **Interruptible.** Work in pieces that can be dropped for a week and picked up. `NOTES.local.md` always says where we
  are; `NOTES.md` is the public record and carries no working state.
- **Pull requests for new work.** The repository is public; changes go on a branch and arrive on `main` through a
  pull request, so each change has a description and a diff someone can read.
- **Public by default.** Meant to be shown, talked about and used in a talk. No real people's private data, no secrets.
- **Omoju writes their own public words.** Claude writes the code, the technical docs and the generated stories; essays,
  posts and talks are Omoju's.
- **Checks before generation.** Every model output has a deterministic check where one is possible (run it, diff it,
  pin it), a model judge only for what's left, and a judge is tested on known answers before it is trusted.

## How CodeStories is shaped
- The reader is chosen per run (`codestory/readers/`); the reader decides emphasis.
- The story follows the main input through the run, in close third person; setup before it appears is brief setting.
  Reader-directed advice goes in `> **For the <reader>:**` callouts.
- Chapters are spans of the recorded trace; their count is whatever the journey needs.
- Proofs live in `proofs/NN.py`, outside the story.
- The reading page (`codestory/render.py`) keeps: title, real-world premise, the control-flow chart of the run,
  and the code beside the narrative.

## Start of a session
1. Read this file, then `NOTES.md` (the public record: decisions, lessons, log) and `NOTES.local.md` if it exists
   (working state for an open cycle; gitignored; "Pick up here" says where to resume).
2. Keys live in `.env` at the root (never commit it). The pipeline is in `codestory/`; each script's docstring says how to run it.
