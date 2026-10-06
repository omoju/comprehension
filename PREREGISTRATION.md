# Preregistration · CodeStories vs. DeepWiki

**Status:** draft, 2026-09-30. Becomes binding when committed to git, before any comparison is run. The commit
hash and timestamp are the record that this plan came first. Changes after that go in *Deviations*, never in place.

**Decision date:** Tuesday 6 October 2026.

---

## 1. Question

Is a CodeStory (a narrative that follows the data through one real run of a repository's intended use, with every
claim linked to pinned source lines and every chapter backed by an executable proof) a better way to understand
a codebase than generated documentation?

Comparison point: **DeepWiki** (Cognition), generated wiki documentation organised by the code's structure, with
links to source files.

## 2. Hypotheses

- **H1 · Accountability.** CodeStories contain far fewer claims that contradict the code than DeepWiki pages.
- **H2 · Comprehension.** A reader given a CodeStory answers questions about the code at least as well as a reader
  given DeepWiki on general questions, and clearly better on questions about the intended-use path.

H1 is the core claim. H2 is the new, riskier one.

## 3. Repositories

Ten pure-Python repositories that have a DeepWiki page, install with `pip install -e .`, and have an intended use
that runs without network access or credentials. They are used in this order, and a repository that fails these
entry conditions *before any results are seen* is replaced by the next alternate.

| # | Repository | | # | Alternate |
|---|---|---|---|---|
| 1 | psf/requests | | A1 | pallets/werkzeug |
| 2 | pallets/flask | | A2 | pytest-dev/pluggy |
| 3 | pallets/click | | A3 | marshmallow-code/marshmallow |
| 4 | encode/httpx | | | |
| 5 | Textualize/rich | | | |
| 6 | python-attrs/attrs | | | |
| 7 | pallets/itsdangerous | | | |
| 8 | pallets/jinja | | | |
| 9 | pallets/markupsafe | | | |
| 10 | tqdm/tqdm | | | |

*Approved by Omoju, 2026-09-30.*

`itsdangerous` was used to develop the pipeline and tune its prompts, so it is **in-sample**. Results are
reported with and without it; the decision uses the nine without it.

Scenarios needing network access (requests, httpx) must use a local transport or mock server that ships with the
repository or the standard library. If that is impossible, the repository is replaced before results are seen.

## 4. Arms

| Arm | What | Pinned to |
|---|---|---|
| **Story** | CodeStory from the pipeline at the committed version of this repo. Reader profile: `owner`. Narration: close third person following the main input. | the repository commit the story's permalinks name |
| **DeepWiki** | All pages of the repository's DeepWiki, fetched through the public DeepWiki MCP server (`read_wiki_contents`), with the fetch date recorded. | the commit DeepWiki's source links name; if none, the default branch on the fetch date |
| **Docs** *(optional; first to be cut)* | The repository's official documentation. | the docs version matching the story's commit |

Each arm is judged against the code at the commit that arm documents, so no arm is penalised for describing an
older or newer version.

## 5. Measures

### 5.1 Accuracy (H1)

1. From each arm's text, extract atomic factual claims about the code (behaviour, names, values, order), with
   one extraction prompt used for every arm.
2. Sample up to 40 claims per repository per arm, with a fixed random seed.
3. The judge labels each sampled claim **contradicted**, **supported** or **unverifiable** against the code at that
   arm's pinned commit, seeing the claim and the relevant source but not which arm the claim came from.
4. **Primary metric: contradicted claims per 1,000 words**, estimated as
   (contradicted ÷ sampled) × (claims extracted ÷ words × 1,000).
5. Omoju hand-checks 20 randomly chosen judged claims (10 per arm); the agreement rate is reported.

### 5.2 Comprehension (H2)

1. **Questions are written before any arm is shown to the reader model,** from the repository and the scenario's
   trace only, by a model that never sees any arm's text. Per repository:
   - 8 **path questions**: about what happens to the data on the intended-use run.
   - 7 **general questions**: from the owner profile's goals (guarantees, failure modes, risky defaults), about the
     repository as a whole.
2. **Answer keys are checked by execution** wherever the answer is observable (a value, an exception, a
   return type). The rest are keyed to specific source lines. Questions without a checkable key are dropped
   before any arm is read.
3. **Reader:** a model given one arm's text and the question, with no repository, tools or web access.
4. **Grading:** the judge compares each answer with the key, not knowing which arm produced it. Scores are
   correct / partly / wrong, counting 1 / 0.5 / 0.
5. **Metrics:** percentage score on path questions and on general questions, per arm, pooled over repositories.

### 5.3 Robustness (reported, not decisive)

- The number of repositories for which the pipeline produces a complete, passing story (repair loop included).
- Cost and wall-clock time per repository.

## 6. Models and versions

| Role | Model |
|---|---|
| Story generation | `claude-opus-5`, adaptive thinking, effort `high` |
| Question writing, reader, judge | `claude-opus-5` |
| Second judge (accuracy only) | Jev (`typesafe/jev`, Cloudflare Workers AI); agreement with the primary judge is reported |

The pipeline's git commit and every prompt are recorded with the results. Every model call is saved in `traces/`.

## 7. Analysis

- Metrics are pooled over the nine out-of-sample repositories.
- Uncertainty: 95% bootstrap confidence intervals, resampling whole repositories (10,000 resamples, fixed seed).
- Comprehension differences are paired: the same question under each arm.
- The decision uses point estimates. When a confidence interval crosses a threshold, the write-up says so.

## 8. Decision rule

| Outcome | Condition |
|---|---|
| **Ship** | H1: story contradiction density ≤ **½** of DeepWiki's, **and** general questions: story ≥ DeepWiki − **5 points**, **and** path questions: story ≥ DeepWiki + **10 points**. |
| **Pivot** | H1 holds, H2 does not: the checking works but the story form doesn't help. Next: apply the checking machinery to *changes*, i.e. stories of how a pull request changes the data's path. |
| **Kill** | H1 does not hold. |

Reasons for the thresholds: the pipeline checks every chapter against the code, so a small accuracy edge would mean
the checking isn't earning its cost. A story covers one path, so it may lose a little on breadth, but not much. And
if it can't clearly win on its own path, the form isn't earning its place.

## 9. Omoju's judgment (recorded, not decisive)

**The decision is the rule in §8.** Omoju's own read is recorded next to it as a second signal. To keep it
independent of the numbers:

1. **Before any results exist**, Omoju writes below what "it helps" would feel like.
2. After reading, and **before seeing any metric**, Omoju records a verdict (ship / pivot / kill) with a sentence of
   reasons.
3. Metrics are then revealed and the rule decides. If Omoju's verdict and the rule disagree, the rule stands, and
   both are published with the disagreement.

> *What "it helps" would feel like (Omoju, to fill in before the runs):*
> I get a reasonable understanding of the code base, I know what the critical paths are, I know where the security boundaries are. 
> …

## 10. Exclusions and failures

- A repository whose pipeline run fails after the repair loop counts against robustness and is left out of H1/H2.
  It is not replaced once any result has been seen.
- A question the reader cannot parse, or a claim the judge cannot place in the code, is logged, not silently dropped.
- Nothing is rerun to get a better result. A rerun after an infrastructure failure (API error, timeout) is allowed and logged.

## 11. Known limitations

- Model readers stand in for human readers; the blind reads by Omoju are the only human signal.
- Both the judge and the story writer are Claude models. The judge's agreement with Jev and with Omoju's hand
  check is the guard against a shared blind spot.
- DeepWiki pages cover the whole repository; a story covers one path. The two question sets exist to show that
  trade-off, not to hide it.
- Ten small-to-mid pure-Python libraries say nothing about large, multi-language systems.

## 12. Deviations

*Changes after this file is committed, with date and reason. None yet.*
