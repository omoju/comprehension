# Preregistration 2 · Change stories on pull requests

**Status:** draft, 19 October 2026. Becomes binding when committed to `main`, before the Action is published.
Changes after that go in *Deviations*, never in place. Cycle 1 is `PREREGISTRATION.md`; its rule said kill on
accuracy and named this pivot (§8).

**Gates:** build gate **Monday 2 November 2026**; decision **Monday 30 November 2026**.

---

## 1. Question

When a change story is posted on a pull request, where reviewers already are, do reviewers use it, and does it
change what happens to the change?

Cycle 1 showed a story helps a model reader understand code (+35 points on the run it narrates, +20 on the core
modules) and that the citation and proof checks do not make its prose more accurate than generated docs. Cycle 2
does not re-test either. It tests the product shape the Anthropic source-control write-up describes from the
other side: humans "examine the intent of the change" instead of reading lines, and nothing yet produces the
artifact they examine.

## 2. What is built

**A GitHub Action.** Added to a repository once. On every pull request it runs `codestory/review.py` in the
repository's own CI with the repository's own model key (a secret), and posts one comment: the verdict, the tests
that fail before and pass after, the changed functions no test reaches, the cost, and a link to the full story
page (hosted by the repository's own Pages or as a workflow artifact). Private code never leaves the runner.
Python with pytest and TypeScript/JavaScript with Japa or Vitest, as `review.py` supports today; a change with no
test of its own gets a comment saying so and nothing else.

Not built in this cycle: a hosted App, a web form, packaging. They come after, if the rule says ship.

## 3. Hypotheses

- **H1 · Adoption.** Repositories that add the Action keep it: they are still running it on new pull requests four
  weeks later.
- **H2 · Use.** Reviewers read it: a story comment gets a reaction or a reply, or its link is followed, on a
  meaningful share of pull requests.
- **H3 · Effect.** When the story reports a changed function no test reaches, a later commit on the same pull
  request adds a test that reaches it more often than the base rate of tests added after any review comment.

H1 is the core claim: a product people keep is the only evidence that it is one. H2 and H3 say why.

## 4. Subjects

Repositories are not chosen by us; they are whoever installs the Action after the announcement. Two rules so the
numbers mean something:

- A repository counts from its first pull request with a story comment. A repository with no pull request in the
  window is not a subject.
- Our own repositories (omoju/comprehension and any other of Omoju's) are **in-sample**: reported, never counted.

Target before the decision: **at least 5 counted repositories** and **30 pull requests with a story**. Below that
the decision is "not enough evidence," which is recorded as a kill of this product shape *for now*, not of the
idea (see §8).

## 5. Measures

Everything comes from GitHub's own records, by the repository's consent in installing the Action; nothing is sent
anywhere else.

### 5.1 Adoption (H1)
Per counted repository: the date of its first story comment, the number of pull requests with a story, and whether
a story was posted on a pull request opened in the last 7 days of the window. **Retained** = yes. Metric: share of
counted repositories retained.

### 5.2 Use (H2)
Per pull request with a story: did the comment receive a reaction (any) or a reply from someone other than its
author, and did a maintainer reference it (quote, link, or "see the story") in review? Metric: share of pull
requests with any of those. Link follows are counted only where the page is hosted somewhere that reports them.

### 5.3 Effect (H3)
Per pull request where the story listed at least one changed function no test reaches: did a later commit on the
same pull request add or change a test file, and did a rerun of the story then report that function as reached?
Metric: share of such pull requests where it did. Base rate: the share of pull requests where a test file changed
after the first review comment, in the same repositories, in the 60 days before the Action was installed (from
the repository's history).

### 5.4 Reported, not decisive
- Failures by cause: no test in the change; runner unsupported; scenario needed the network; proof could not run;
  model error. Share of pull requests where the Action produced a story at all.
- Cost: dollars and tokens per pull request, per stage and model, from the run's own report; the trend.
- Outside contributions: pull request authors, CLA signatures, reports filed through the template.
- Omoju's own read of ten story comments chosen at random, recorded before the metrics are compiled.

## 6. Models and versions

The repository's own choice through `CODESTORY_PROVIDER`; the Action's default is `claude-opus-5` through the
Anthropic API. The pipeline's commit is in every story's `changes.json`. Every model call is saved in the run's
`traces/`, kept as a workflow artifact for 30 days.

## 7. Analysis

Metrics are pooled over counted repositories. Uncertainty: with five to twenty repositories, intervals are wide;
they are reported (bootstrap over repositories, 10,000 resamples, fixed seed 20261130) and the decision uses point
estimates, as in cycle 1.

## 8. Decision rule

| Outcome | Condition |
|---|---|
| **Ship** | ≥ 5 counted repositories, **and** H1: ≥ 60% retained, **and** H2: ≥ 30% of pull requests with use, **and** H3: tests added after an unreached-function finding at ≥ 1.5× the base rate. Next: the hosted App, packaging, cycle 3. |
| **Pivot** | ≥ 5 repositories and H1 holds but H2 or H3 does not: people keep it but do not act on it. Next: change what the comment says, not where it goes. |
| **Kill** | ≥ 5 repositories and H1 fails: installed and abandoned. The PR surface is not it. |
| **Not enough evidence** | Fewer than 5 counted repositories or 30 pull requests by 30 November. Recorded as a kill *of this shape for now*; the Action stays available; no claims are made. |

The thresholds are set before any repository installs it. Reasons: 60% retention over four weeks is the floor for
"people keep it" in a tool that costs them money per run; 30% use is low on purpose, since silent reading is
invisible; 1.5× is the smallest effect worth the cost of the comment.

## 9. Build gate · 2 November

The Action is published on the Marketplace, with the README updated, by Monday 2 November, or the cycle stops and
this file records why. Omoju writes below, before the gate, what a reviewer finding the comment useful would look
like; and records a verdict (ship / pivot / kill) on the ten random story comments before any metric is compiled.

> *What "a reviewer found it useful" would look like (Omoju, before 2 November):*
>
> …

> *Verdict after reading ten story comments, before any metric (Omoju):*
>
> **…** — …

## 10. Exclusions and failures

- A repository that installs the Action and removes it before its first story is not a subject; it is counted in
  failures by cause if a run was attempted.
- A pull request where the Action failed to produce a story is excluded from H2 and H3 and counted in §5.4.
- Nothing is rerun to improve a number. Reruns after infrastructure failures are allowed and logged.
- Our own repositories are reported separately and excluded from every decision metric.

## 11. Known limitations

- Repositories self-select; early adopters are friendlier than the population.
- H2 undercounts silent readers; H3 can be confounded by review norms that already require tests.
- The cycle is longer than two weeks because adoption takes time; the build gate keeps the first half honest.
- Reactions and replies are GitHub-visible, so this measures use on repositories that are public or whose
  maintainers share their numbers; private repositories contribute counts only if their owners report them.

## 12. Deviations

*Changes after this file is committed, with date and reason. None yet.*
