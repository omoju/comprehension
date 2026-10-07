# comprehension

Prototypes for the future of code comprehension. Premise: more and more code is written by agents and read by
nobody, and reading code you didn't write doesn't scale. Comprehension has to become something you can check,
not something you take on trust.

## CodeStories

A repository explained as a story that follows its data through one real run of its intended use.

- **The plot is a run.** A model writes the intended-use scenario; a tracer records every call into the repository
  with its arguments and return values. Chapters are spans of that trace.
- **Every claim links to the lines**, as a permalink at a pinned commit. A checker verifies that the lines exist
  and haven't changed; if the code moves on, the story fails like a test and points at the passage.
- **Every chapter has an executable proof** (`proofs/NN.py`) that replays the run up to that point and asserts the
  values the story shows. Proofs that can't fail are rejected.
- **Checks before generation.** Each model stage has a deterministic check; what fails goes back to the model with
  the verdict, at most twice. A model judge (Jev) is used only for what code can't decide, is tested on planted
  lies before it is trusted, and is reported rather than acted on.
- **The reader is chosen per run** (`codestory/readers/`): the owner, the maintainer, the user. The reader decides
  where the story slows down.

Pipeline and data flow: [`codestory/README.md`](codestory/README.md). Running log and current state:
[`NOTES.md`](NOTES.md).

### Run it

Python 3.13, [`uv`](https://docs.astral.sh/uv/) on the path, keys in `.env` (copy `.env.example`).

```bash
sh codestory/restore_repos.sh                     # the demo repositories at the exact commits the stories cite
.venv/bin/python codestory/scenario.py demo-repos/markupsafe stories/mine
.venv/bin/python codestory/outline.py  demo-repos/markupsafe stories/mine --reader owner
.venv/bin/python codestory/chapter.py  stories/mine
.venv/bin/python codestory/render.py   stories/mine                      # → stories/mine/index.html
.venv/bin/python codestory/verify.py   stories/mine                      # citations, drift, proofs
```

Ten stories exist in `stories/` (itsdangerous in `stories/itsdangerous-close-third/`, the rest in `stories/bench/`).

### Is it better than generated documentation?

A preregistered head-to-head against DeepWiki on ten pure-Python repositories: [`PREREGISTRATION.md`](PREREGISTRATION.md)
fixes the hypotheses, measures and decision rule before any result; `codestory/eval/` is the harness; `eval/`
holds every intermediate (questions, claims, judgments, answers, grades, every model response).

**Decided 6 October 2026: the rule said kill.** Stories helped a reader a great deal (path questions 98% vs 63%,
general 76% vs 56%) but were not more accurate than DeepWiki's pages (0.71 vs 0.54 contradicted claims per 1,000
words; 10 vs 7 of 360 sampled). Omoju's verdict, recorded before the numbers, was ship; the preregistration says
the rule stands, and both are published. The numbers, both judging passes, and every deviation:
`eval/results.md`, `PREREGISTRATION.md` §12–13. Two interactive explainers walk through how each measure was
produced: `eval/explainer/index.html` (comprehension, H2) and `eval/explainer/h1.html` (accuracy, H1).

## Rules of the project

Two-week cycles with a date and a kill criterion set in advance. Plain formats (Markdown, JSON, git permalinks)
and swappable models. Demonstrations before documents. Public by default: no private data, no secrets.
Claude writes the code, the technical docs and the stories; the essays and talks are Omoju's.
