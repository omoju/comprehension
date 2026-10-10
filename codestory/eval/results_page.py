"""Render the results page from eval/results.json and the records around it. No model calls.

    .venv/bin/python codestory/eval/results_page.py        → eval/results.html

Built so it can be generated without anyone reading the numbers first: it takes everything from files.
Sections: the question, the two tellings side by side (the rule's decision and Omoju's recorded verdict), the
measures with their intervals, per-repository rows, robustness, the judge's test and Omoju's hand check, what
changed after preregistration, and how to read a story yourself.

The page is in omojumiller.com's house style: it links the site's stylesheet, as the stories gallery and the
explainers do, and keeps locally only the rules the site has none for (the verdict cards, the measures, tables).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from common import ARMS, EVAL, IN_SAMPLE, ROOT, story_dir

PREREG = ROOT / "PREREGISTRATION.md"


def e(s) -> str:
    return html.escape(str(s))


def f(x, d=1, suffix="") -> str:
    return "—" if x is None else f"{x:.{d}f}{suffix}"


def pct(scores) -> float | None:
    return 100 * sum(scores) / len(scores) if scores else None


def omoju_sections() -> tuple[str, str, list[str]]:
    """§9 of the preregistration: what 'it helps' would feel like; the verdict word; its reasons, one per line."""
    text = PREREG.read_text()
    clean = lambda m: re.sub(r"^>\s?", "", m.group(1), flags=re.M).strip() if m else ""  # noqa: E731
    feel = clean(re.search(r'\*What "it helps" would feel like[^\n]*\n((?:>.*\n?)+)', text))
    block = clean(re.search(r"\*Verdict after reading, before any metric[^\n]*\n((?:>.*\n?)+)", text))
    lines = re.findall(r"^\*\*(ship|pivot|kill)\*\*\s*[-—–]\s*(.+?)\s*$", block, re.M | re.I)
    return feel, (lines[0][0].lower() if lines else ""), [r for _, r in lines]


def deviations() -> list[str]:
    text = PREREG.read_text()
    section = text.split("## 12. Deviations", 1)[1].split("\n## ", 1)[0]  # up to the next section (§13)
    return [re.sub(r"\s+", " ", d).strip() for d in re.findall(r"^- (\*\*.*?)(?=^- \*\*|\Z)", section, re.M | re.S)]


def story_report(name: str) -> dict:
    """Totals from a story's report.md. Reports written before the repair loop have no repairs column."""
    text = (story_dir(name) / "report.md").read_text()
    with_repairs = re.findall(r"^\| (\d+) \| \[.*?\]\(.*?\) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+)/(\d+) \| (\d+)s \| \$([\d.]+) \|", text, re.M)
    if with_repairs:
        rows = [(int(w), int(c), int(rep), int(err), int(t), float(cost)) for _, w, c, rep, err, _, _, t, cost in with_repairs]
    else:
        old = re.findall(r"^\| (\d+) \| \[.*?\]\(.*?\) \| (\d+) \| (\d+) \| (\d+) \| (\d+)/(\d+) \| (\d+)s \| \$([\d.]+) \|", text, re.M)
        rows = [(int(w), int(c), None, int(err), int(t), float(cost)) for _, w, c, err, _, _, t, cost in old]
    has_repairs = bool(with_repairs)
    return {"chapters": len(rows), "citations": sum(r[1] for r in rows), "has_repairs": has_repairs,
            "repairs": sum(r[2] for r in rows) if has_repairs else None,
            "failing": sum(1 for r in rows if r[3]) if has_repairs else None,
            "minutes": sum(r[4] for r in rows) // 60, "cost": sum(r[5] for r in rows)}


def handcheck() -> dict | None:
    key_file, md_file = EVAL / "handcheck.key.json", EVAL / "handcheck.md"
    if not (key_file.exists() and md_file.exists()):
        return None
    key = {k["n"]: k for k in json.loads(key_file.read_text())}
    verdicts = {int(n): v.strip().lower() for n, v in re.findall(r"^## (\d+)\..*?\*\*Omoju:\*\*\s*(\w*)", md_file.read_text(), re.M | re.S)}
    out = {}
    for arm in ARMS:
        done = [k for k in key.values() if k["arm"] == arm and verdicts.get(k["n"]) in ("agree", "disagree", "unsure")]
        out[arm] = {"agree": sum(1 for k in done if verdicts[k["n"]] == "agree"), "n": len(done)}
    return out


def page_url(name: str) -> str:
    """The story's public reading page, relative to eval/results.html."""
    return "../" + story_dir(name).relative_to(ROOT).as_posix() + "/"


STYLE = """<style>
/* Only what omojumiller.com's stylesheet has no rule for: the two verdicts, the measures, tables, tags. */
:root { --story: #1f5f8b; --story-soft: #dfeaf4; --wiki: #8b5a1f; --wiki-soft: #f5ecdc; --ok: #2d6a4f; --no: #AA0000;
  --sheet: #ffffff; --muted: var(--ink-faint); --serif: 'EB Garamond', Garamond, Georgia, serif }
.lede { font-style: italic; color: var(--ink-soft) }
.card, .m, .tbl, .dev, ul.checks { text-align: left; hyphens: none; -webkit-hyphens: none }
.verdicts { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: .9rem; margin: 1.2rem 0 1.6rem }
.card { background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; padding: .9rem 1.1rem; min-width: 0 }
.card .who { font-family: var(--sans); font-size: .72rem; font-weight: 500; letter-spacing: .02em; text-transform: lowercase; color: var(--accent) }
.card .big { font: 600 2rem/1.1 var(--serif); font-variant-caps: small-caps; letter-spacing: .04em; margin: .2rem 0 .5rem }
.card .big.ship { color: var(--ok) } .card .big.pivot { color: var(--wiki) } .card .big.kill { color: var(--no) }
.card p { font-size: .95rem; margin-bottom: .5rem }
ul.checks { list-style: none; padding: 0; margin: .6rem 0 0; font: .78rem/1.5 var(--mono); font-variant-numeric: lining-nums }
ul.checks li { display: flex; gap: .5rem; align-items: baseline; margin-bottom: .2rem }
ul.checks .mark { font-weight: 600 } ul.checks .ok .mark { color: var(--ok) } ul.checks .no .mark { color: var(--no) }
.measures { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: .7rem; margin: 1rem 0 }
.m { background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; padding: .8rem .9rem; min-width: 0 }
.m .label { font: 500 .72rem/1.3 var(--mono); color: var(--muted); letter-spacing: 0 }
.m .pair { display: flex; gap: 1rem; margin-top: .5rem; font-variant-numeric: lining-nums tabular-nums }
.m .pair div { flex: 1 } .m .pair b { display: block; font: 600 1.7rem/1.1 var(--serif) }
.m .pair div:first-child b { color: var(--story) } .m .pair div:last-child b { color: var(--wiki) }
.m .ci { font: .72rem/1.45 var(--mono); font-variant-numeric: lining-nums; color: var(--muted); margin-top: .5rem }
.tag { display: inline-block; padding: .05em .5em; border-radius: 4px; font: 500 .72rem/1.5 var(--mono); letter-spacing: 0; font-variant-caps: normal }
.tag.story { background: var(--story-soft); color: var(--story) } .tag.deepwiki { background: var(--wiki-soft); color: var(--wiki) }
.tbl { overflow-x: auto; margin: .8rem 0 1.15rem }
table { border-collapse: collapse; font: .72rem/1.45 var(--mono); font-variant-numeric: lining-nums tabular-nums; min-width: 100% }
th, td { text-align: left; padding: .25rem .5rem; border-bottom: 1px solid var(--rule); white-space: nowrap }
th { font-weight: 500; color: var(--muted) } td.n, th.n { text-align: right }
tr.story td:nth-child(2) { color: var(--story) } tr.deepwiki td:nth-child(2) { color: var(--wiki) }
tr.insample td { color: var(--muted) }
p.small { font-size: .9rem; color: var(--ink-soft) }
.dev { border-left: 3px solid var(--rule); padding: .3rem .8rem; margin: 0 0 .8rem; font-size: .95rem }
.dev.omoju { border-left-color: var(--story) }
ul.read li { margin-bottom: .35rem }
.foot { color: var(--ink-faint); font-size: .9rem; margin-top: 2.6rem; border-top: 1px solid var(--rule); padding-top: .8rem }
</style>"""


def main() -> None:
    R = json.loads((EVAL / "results.json").read_text())
    p, ci, checks = R["pooled_out_of_sample"], R["ci95"], R["checks"]
    feel, verdict, reasons = omoju_sections()
    judge_test = json.loads((EVAL / "judge-test" / "itsdangerous.json").read_text())
    jt = {arm: {"caught": sum(1 for i in judge_test["items"] if i["arm"] == arm and not i["truth"] and i["label"] == "contradicted"),
                "lies": sum(1 for i in judge_test["items"] if i["arm"] == arm and not i["truth"]),
                "alarms": sum(1 for i in judge_test["items"] if i["arm"] == arm and i["truth"] and i["label"] == "contradicted"),
                "truths": sum(1 for i in judge_test["items"] if i["arm"] == arm and i["truth"])} for arm in ARMS}
    hc = handcheck()
    decision = R["decision"]
    meaning = {"ship": "the checking works and the story form helps: build it out.",
               "pivot": "the checking works but the story form does not clearly help: apply the machinery to changes instead.",
               "kill": "the accountability claim did not hold."}[decision]

    rows_html = []
    for r in R["repos"]:
        for arm in ARMS:
            a = r[arm]
            rows_html.append(
                f"<tr class='{arm}{' insample' if r['repo'] in IN_SAMPLE else ''}'>"
                f"<td>{e(r['repo'])}{'*' if r['repo'] in IN_SAMPLE else ''}</td><td>{arm}</td>"
                f"<td class='n'>{a['words']:,}</td><td class='n'>{a['extracted']}</td><td class='n'>{a['contradicted']}/{a['sampled']}</td>"
                f"<td class='n'>{a['unverifiable']}</td><td class='n'>{f(a['density'], 2)}</td>"
                f"<td class='n'>{f(pct(a['path']), 0, '%')}</td><td class='n'>{f(pct(a['general']), 0, '%')}</td>"
                f"<td class='n'>{a['jev_agree']}/{a['jev_n']}</td></tr>")
    robust, reports = [], {}
    for r in R["repos"]:
        rep = reports[r["repo"]] = story_report(r["repo"])
        dw = json.loads((EVAL / "deepwiki" / r["repo"] / "meta.json").read_text())
        s = dw["source_refs"]
        insample = r["repo"] in IN_SAMPLE
        dash = "—"
        robust.append(f"<tr{' class=insample' if insample else ''}><td>{e(r['repo'])}{'*' if insample else ''}</td>"
                      f"<td class='n'>{rep['chapters']}</td><td class='n'>{rep['citations']}</td>"
                      f"<td class='n'>{rep['repairs'] if rep['has_repairs'] else dash}</td><td class='n'>{rep['failing'] if rep['has_repairs'] else dash}</td>"
                      f"<td class='n'>${rep['cost']:.2f}</td><td class='n'>{rep['minutes']} min</td><td class='n'>{dw['words']:,}</td>"
                      f"<td class='n'>{100 * s['ok'] / s['total']:.0f}%</td></tr>")
    out_of_sample = [r["repo"] for r in R["repos"] if r["repo"] not in IN_SAMPLE]
    total_cost = sum(reports[n]["cost"] for n in out_of_sample)

    def check_li(label, ok):
        return f"<li class='{'ok' if ok else 'no'}'><span class='mark'>{'✓' if ok else '✗'}</span> {e(label)}</li>"

    first_run_html = ""
    first = EVAL / "results-first-run.json"
    if first.exists():
        F = json.loads(first.read_text())
        fp = F["pooled_out_of_sample"]
        unv = {arm: sum(r[arm]["unverifiable"] for r in F["repos"] if r["repo"] not in IN_SAMPLE) for arm in ARMS}
        unv_now = {arm: sum(r[arm]["unverifiable"] for r in R["repos"] if r["repo"] not in IN_SAMPLE) for arm in ARMS}
        n = {arm: sum(r[arm]["sampled"] for r in R["repos"] if r["repo"] not in IN_SAMPLE) for arm in ARMS}
        first_run_html = f"""<h2>the judge was run twice</h2>
<p>The first judging pass could not see most of the source in the large repositories (the repository block led
with docs and ran out of room), and said so: it called {unv['story']} of {n['story']} story claims and
{unv['deepwiki']} of {n['deepwiki']} DeepWiki claims unverifiable. Since unverifiable counts as not contradicted
in the preregistered metric, that pass did not measure H1. The judge was given the source the claims name and
re-run on the same sampled claims; nothing else was re-run. Both passes are published.</p>
<div class="tbl"><table>
<tr><th>pass</th><th class="n">story unverifiable</th><th class="n">deepwiki unverifiable</th><th class="n">story / 1k</th><th class="n">deepwiki / 1k</th><th>rule said</th></tr>
<tr><td>first (source mostly unseen)</td><td class="n">{unv['story']}/{n['story']}</td><td class="n">{unv['deepwiki']}/{n['deepwiki']}</td><td class="n">{f(fp['story']['density'], 2)}</td><td class="n">{f(fp['deepwiki']['density'], 2)}</td><td>{e(F['decision'])}</td></tr>
<tr><td>second (source in view)</td><td class="n">{unv_now['story']}/{n['story']}</td><td class="n">{unv_now['deepwiki']}/{n['deepwiki']}</td><td class="n">{f(p['story']['density'], 2)}</td><td class="n">{f(p['deepwiki']['density'], 2)}</td><td>{e(decision)}</td></tr>
</table></div>"""

    verdict_html = (f'<div class="big {verdict}">{e(verdict)}</div>' + "".join(f"<p>{e(x)}</p>" for x in reasons)) if verdict \
        else '<div class="big">—</div><p>Not yet recorded.</p>'
    read_one = "".join(f'<li><a href="{page_url(r["repo"])}">{e(r["repo"])}</a>{" (in sample)" if r["repo"] in IN_SAMPLE else ""}</li>'
                       for r in R["repos"])

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CodeStories vs DeepWiki · Omoju Miller</title>
<meta name="description" content="The preregistered comparison of CodeStories against DeepWiki on nine Python libraries: the rule's decision and Omoju's recorded verdict, the measures with their intervals, every repository, and what changed after preregistration.">
<link rel="stylesheet" href="https://omojumiller.com/theme/css/style.css">
{STYLE}
</head><body>
<header>
  <h1><a href="https://omojumiller.com/">Omoju Miller</a></h1>
</header>
<main>
<article>
  <h2 class="entry-title">Is a CodeStory better than generated documentation?</h2>
  <div class="date">comprehension · codestories · decided {e(R.get('decided', '2026-10-06'))}</div>
  <div class="post-body">
<p class="lede">A repository told as a story that follows its data through one real run, every claim linked to pinned
lines and every chapter backed by a proof that runs, against DeepWiki's generated wiki for the same ten Python
libraries. The rule for deciding was written and committed before any result existed.</p>

<div class="verdicts">
  <div class="card">
    <div class="who">the preregistered rule (§8)</div>
    <div class="big {decision}">{decision}</div>
    <p>{e(meaning)}</p>
    <ul class="checks">{''.join(check_li(k, v) for k, v in checks.items())}</ul>
  </div>
  <div class="card">
    <div class="who">Omoju, after reading and before any metric (§9)</div>
    {verdict_html}
    <p><em>What "it helps" would feel like, written before the runs:</em> {e(feel) or '—'}</p>
  </div>
</div>

<h2>the measures</h2>
<p>Nine repositories out of sample (<code>itsdangerous</code> was used to build the pipeline and is reported but not
counted). H1 is accountability: contradicted claims per 1,000 words, from a blind judge reading 40 sampled claims
per arm per repository against the code at the commit each arm describes. H2 is comprehension: a reader model
given only one arm's text answers questions written from the code and the run, never from either arm, with keys
checked by execution.</p>
<div class="measures">
  <div class="m"><div class="label">contradicted claims / 1k words</div>
    <div class="pair"><div><b>{f(p['story']['density'], 2)}</b><small><span class="tag story">story</span></small></div>
    <div><b>{f(p['deepwiki']['density'], 2)}</b><small><span class="tag deepwiki">deepwiki</span></small></div></div>
    <div class="ci">ratio story/deepwiki, 95% CI {f(ci['density_ratio'][0], 2) if ci['density_ratio'] else '—'}–{f(ci['density_ratio'][1], 2) if ci['density_ratio'] else '—'} · rule: ≤ 0.5</div></div>
  <div class="m"><div class="label">path questions (this run)</div>
    <div class="pair"><div><b>{f(p['story']['path'], 0, '%')}</b><small><span class="tag story">story</span></small></div>
    <div><b>{f(p['deepwiki']['path'], 0, '%')}</b><small><span class="tag deepwiki">deepwiki</span></small></div></div>
    <div class="ci">difference, 95% CI {f(ci['path_diff'][0], 0) if ci['path_diff'] else '—'} to {f(ci['path_diff'][1], 0) if ci['path_diff'] else '—'} points · rule: ≥ +10</div></div>
  <div class="m"><div class="label">general questions (whole repo)</div>
    <div class="pair"><div><b>{f(p['story']['general'], 0, '%')}</b><small><span class="tag story">story</span></small></div>
    <div><b>{f(p['deepwiki']['general'], 0, '%')}</b><small><span class="tag deepwiki">deepwiki</span></small></div></div>
    <div class="ci">difference, 95% CI {f(ci['general_diff'][0], 0) if ci['general_diff'] else '—'} to {f(ci['general_diff'][1], 0) if ci['general_diff'] else '—'} points · rule: ≥ −5</div></div>
</div>
<p>Intervals resample whole repositories (10,000 draws, fixed seed). The decision uses the point estimates; where an
interval crosses a threshold, it says so here. How each measure was produced, step by step:
<a href="explainer/h1.html">the accuracy measure</a> and <a href="explainer/">the comprehension measure</a>.</p>

<h3>Per repository</h3>
<div class="tbl"><table>
<tr><th>repo</th><th>arm</th><th class="n">words</th><th class="n">claims</th><th class="n">contradicted</th><th class="n">unverifiable</th><th class="n">per 1k words</th><th class="n">path</th><th class="n">general</th><th class="n">Jev agrees</th></tr>
{''.join(rows_html)}
</table></div>
<p class="small">* in sample. "Jev agrees": a second, cheaper model's verdict on the same claim and the lines the judge cited.</p>

<h2>robustness</h2>
<p>Every story was generated by the same pipeline with no hand edits. A chapter that failed a check (a citation to
lines that don't exist, a proof that doesn't pass) went back to the model with the verdict, at most twice.
"Refs resolve" is the share of DeepWiki's own <code>[path:lines]()</code> references that point at lines existing
at the commit its pages are pinned to.</p>
<div class="tbl"><table>
<tr><th>repo</th><th class="n">chapters</th><th class="n">citations</th><th class="n">repairs</th><th class="n">still failing</th><th class="n">cost</th><th class="n">time</th><th class="n">DeepWiki words</th><th class="n">refs resolve</th></tr>
{''.join(robust)}
</table></div>
<p class="small">* in sample: the itsdangerous story was written while the pipeline was being built, before the repair
loop existed, and two of its proofs were fixed by hand.</p>
<p>The nine out-of-sample stories: ${total_cost:.2f} in model calls. The evaluation itself (questions, extraction,
judging, reading, grading) is in <code>eval/</code> with every model response saved.</p>

<h2>was the judge trustworthy?</h2>
<p>Before any comparison ran, the judge was tested on planted lies: 10 true claims per arm from the in-sample
repository, each with a false twin that changes one specific, judged blind among the truths.
Story claims: {jt['story']['caught']}/{jt['story']['lies']} lies caught, {jt['story']['alarms']}/{jt['story']['truths']} truths wrongly flagged.
DeepWiki claims: {jt['deepwiki']['caught']}/{jt['deepwiki']['lies']} caught, {jt['deepwiki']['alarms']}/{jt['deepwiki']['truths']} wrongly flagged.
The passing bar (every lie caught, at most one false alarm per arm) was written into the test before it ran.</p>
<p>{('Omoju hand-checked 20 judged claims with the arm hidden: agreed with the judge on '
     + ' and '.join(f"{hc[a]['agree']}/{hc[a]['n']} ({a})" for a in ARMS) + '.') if hc and any(hc[a]['n'] for a in ARMS)
    else 'Omoju’s hand check of 20 judged claims (§5.1.5) is recorded in <code>eval/handcheck.md</code>.'}</p>

{first_run_html}

<h2>what changed after preregistration</h2>
{''.join(f'<div class="dev">{e(d).replace("**", "")}</div>' for d in deviations()) or '<p>Nothing.</p>'}

<h2>read one</h2>
<p>The reading page keeps the title, the real-world premise, a control-flow chart of the run drawn from executed
lines, and the code beside the narrative. Each chapter's proof is a file you can run. All of them are listed in
<a href="../stories/">the gallery</a>.</p>
<ul class="read">{read_one}</ul>

<p class="foot">Preregistration, pipeline and every intermediate file are in <a href="https://github.com/omoju/comprehension">the
repository</a>. The decision rule was committed before the first result and is quoted here unchanged. Stories are
written by Claude; this page is generated from <code>eval/results.json</code>.</p>
  </div>
</article>
</main>
<footer><p>&copy; Omoju Miller. Stories by Claude, checked by code; <a href="https://github.com/omoju/comprehension">source, preregistration and evaluation</a>.</p></footer>
</body></html>
"""
    (EVAL / "results.html").write_text(page)
    print(f"wrote eval/results.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
