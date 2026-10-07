# comprehension

Prototypes for the future of code comprehension. Premise: more and more code is written by agents and read by
nobody, and reading code you didn't write doesn't scale. Comprehension has to become something you can check,
not something you take on trust.

## CodeStories

A repository explained as a story that follows its data through one real run of its intended use.

**Read one first:** [`stories/index.html`](stories/index.html) lists the ten. Each reading page has three panes: the
control-flow chart of the run, the story, and the code it cites, side by side (on a window about 1,360px wide; narrower
screens open the code as a sheet). The pages are static files; with GitHub Pages enabled for this repository
(Settings → Pages → Source: GitHub Actions) they are served at [https://omojumiller.com/comprehension/stories/](https://omojumiller.com/comprehension/stories/).

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

### Make a story of your own repository

Python 3.13 and [`uv`](https://docs.astral.sh/uv/) on the path; a model: an Anthropic API key, or your Claude or
ChatGPT login (through the `claude` or `codex` CLI), or a deployment on Azure AI Foundry (see `.env.example`). Then:

```bash
git clone https://github.com/omoju/comprehension.git && cd comprehension
uv venv .venv --python 3.13 && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env            # choose CODESTORY_PROVIDER and its keys; the Cloudflare keys are optional
.venv/bin/python codestory/story.py https://github.com/<owner>/<repo> --open
```

One command does the whole run: it clones the repository, has the model write and trace its intended use, plans the
chapters, writes each one, checks every citation and runs every proof (sending failures back to the model up to twice),
and renders the three-pane page at `stories/<repo>/index.html`. `--reader owner|maintainer|user` picks who the story
is for (default: owner). Each stage is resumable: if it stops, run the same command again.

What to expect: **$2–6 in model calls and 10–25 minutes** for a library of a few thousand lines; `stories/<repo>/report.md`
lists every chapter with its checks, repairs and cost. The contradiction judge (Jev, on Cloudflare) runs only if
its keys are in `.env`; without them the report says it was skipped.

What it can't do yet: repositories that aren't Python; intended uses that need the network, credentials or services
(the scenario must run offline; for HTTP libraries the pipeline found local transports on its own, but it can fail);
repositories much over 400,000 characters of source (the model sees the traced files first, the rest as room allows);
and, as the comparison below found, it does not make every sentence right: read the report, run the proofs, and
treat a chapter like any other claim about code.

The stages one at a time, if you want them:

```bash
.venv/bin/python codestory/scenario.py demo-repos/markupsafe stories/mine
.venv/bin/python codestory/outline.py  demo-repos/markupsafe stories/mine --reader owner
.venv/bin/python codestory/chapter.py  stories/mine
.venv/bin/python codestory/render.py   stories/mine                      # → stories/mine/index.html, the three-pane page
.venv/bin/python codestory/verify.py   stories/mine                      # citations, drift, proofs
sh codestory/restore_repos.sh                                            # the ten demo repositories at their pinned commits
```

Ten stories exist in `stories/` (itsdangerous in `stories/itsdangerous-close-third/`, the rest in `stories/bench/`).

### Tell the story of a change

The same machinery explains a pull request instead of a repository. A change has its own intended use, the tests
that come with it, so `review.py` runs them on the code before the change and after it, and the story follows the same
data through both versions, for a reviewer: what the change makes true, what it keeps true, and what no test reaches.

```bash
.venv/bin/python codestory/review.py <repo> --pr <number> --open      # or --base <rev> --head <rev>
```

Each chapter's proof is a whole test file in the repository's own runner, and it is run on both sides: a chapter
that claims a difference must pass after the change and fail before it, so a proof can't merely restate the code.
TypeScript and JavaScript packages tested with Japa (AdonisJS) or Vitest (Vite, Vue) so far. An example from a
public repository: [`stories/ufo-pr313/`](stories/ufo-pr313/) (unjs/ufo, "prevent false prefix matches").
Pipeline: [`codestory/README.md`](codestory/README.md#a-change-instead-of-a-repository).

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

## License

MIT. The stories quote the repositories they describe under those projects' own licenses, with permalinks as attribution.
