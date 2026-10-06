"""Render the results page from eval/results.json and the records around it. No model calls.

    .venv/bin/python codestory/eval/results_page.py        → eval/results.html

Built so it can be generated without anyone reading the numbers first: it takes everything from files.
Sections: the question, the two tellings side by side (the rule's decision and Omoju's recorded verdict), the
measures with their intervals, per-repository rows, robustness, the judge's test and Omoju's hand check, what
changed after preregistration, and how to read a story yourself.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from common import ARMS, EVAL, IN_SAMPLE, ROOT, story_dir

PREREG = ROOT / "PREREGISTRATION.md"
PAGES = {  # published reading pages, for the "read one" section
    "itsdangerous": "https://claude.ai/artifact/JyeDNbyYZyMt1ivYxWwshL",
    "markupsafe": "https://claude.ai/artifact/XvZvFsbrfAkfmqxKV8krcs",
    "requests": "https://claude.ai/artifact/F39FKqTiN4o5G86Vq4xU5A",
    "rich": "https://claude.ai/artifact/PsTSWzUhRqCwLYjxXsqdNw",
}


def e(s) -> str:
    return html.escape(str(s))


def f(x, d=1, suffix="") -> str:
    return "—" if x is None else f"{x:.{d}f}{suffix}"


def pct(scores) -> float | None:
    return 100 * sum(scores) / len(scores) if scores else None


def omoju_sections() -> tuple[str, str]:
    text = PREREG.read_text()
    feel = re.search(r"\*What \"it helps\" would feel like.*?\*:\*\n((?:>.*\n?)+)", text)
    verdict = re.search(r"\*Verdict after reading, before any metric.*?\*:\*\n((?:>.*\n?)+)", text)
    clean = lambda m: re.sub(r"^>\s?", "", m.group(1), flags=re.M).strip() if m else ""  # noqa: E731
    return clean(feel), clean(verdict)


def deviations() -> list[str]:
    text = PREREG.read_text()
    section = text.split("## 12. Deviations", 1)[1]
    return [re.sub(r"\s+", " ", d).strip() for d in re.findall(r"^- (\*\*.*?)(?=^- \*\*|\Z)", section, re.M | re.S)]


def story_report(name: str) -> dict:
    rows = re.findall(r"^\| (\d+) \| \[.*?\]\(.*?\) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+)/(\d+) \| (\d+)s \| \$([\d.]+) \|",
                      (story_dir(name) / "report.md").read_text(), re.M)
    return {"chapters": len(rows), "repairs": sum(int(r[3]) for r in rows), "failing": sum(1 for r in rows if int(r[4])),
            "cost": sum(float(r[8]) for r in rows), "minutes": sum(int(r[7]) for r in rows) // 60,
            "citations": sum(int(r[2]) for r in rows)}


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


def main() -> None:
    R = json.loads((EVAL / "results.json").read_text())
    p, ci, checks = R["pooled_out_of_sample"], R["ci95"], R["checks"]
    feel, verdict = omoju_sections()
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
        rep = story_report(r["repo"])
        dw = json.loads((EVAL / "deepwiki" / r["repo"] / "meta.json").read_text())
        for arm in ARMS:
            a = r[arm]
            rows_html.append(
                f"<tr class='{arm}{' insample' if r['repo'] in IN_SAMPLE else ''}'>"
                f"<td>{e(r['repo'])}{'*' if r['repo'] in IN_SAMPLE else ''}</td><td>{arm}</td>"
                f"<td class='n'>{a['words']:,}</td><td class='n'>{a['extracted']}</td><td class='n'>{a['contradicted']}/{a['sampled']}</td>"
                f"<td class='n'>{a['unverifiable']}</td><td class='n'>{f(a['density'], 2)}</td>"
                f"<td class='n'>{f(pct(a['path']), 0, '%')}</td><td class='n'>{f(pct(a['general']), 0, '%')}</td>"
                f"<td class='n'>{a['jev_agree']}/{a['jev_n']}</td></tr>")
    robust = []
    for r in R["repos"]:
        rep = story_report(r["repo"])
        dw = json.loads((EVAL / "deepwiki" / r["repo"] / "meta.json").read_text())
        s = dw["source_refs"]
        robust.append(f"<tr><td>{e(r['repo'])}</td><td class='n'>{rep['chapters']}</td><td class='n'>{rep['citations']}</td>"
                      f"<td class='n'>{rep['repairs']}</td><td class='n'>{rep['failing']}</td><td class='n'>${rep['cost']:.2f}</td>"
                      f"<td class='n'>{rep['minutes']} min</td><td class='n'>{dw['words']:,}</td>"
                      f"<td class='n'>{100 * s['ok'] / s['total']:.0f}%</td></tr>")
    total_cost = sum(story_report(r["repo"])["cost"] for r in R["repos"])

    def check_li(label, ok):
        return f"<li class='{'ok' if ok else 'no'}'><span class='mark'>{'✓' if ok else '✗'}</span> {e(label)}</li>"

    page = f"""<title>CodeStories vs DeepWiki</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column, 68ch, with the two verdicts side by side and tables allowed to run wider. */
:root {{
  --bg: #f7f5f0; --sheet: #ffffff; --ink: #1d1b17; --muted: #5d5a53; --rule: #d9d4c9;
  --story: #1f5f8b; --story-soft: #e3eef6; --wiki: #8b5a1f; --wiki-soft: #f6ede0;
  --ok: #2d6a4f; --no: #a23b2a; --mark: #fff4d6;
  --serif: "Source Serif 4", Georgia, "Times New Roman", serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #15140f; --sheet: #1e1c17; --ink: #ece7dc; --muted: #a39d90; --rule: #3a362e;
  --story: #7fb3d9; --story-soft: #1b2b38; --wiki: #d9a05c; --wiki-soft: #332718;
  --ok: #7cc49a; --no: #e08674; --mark: #3b3418; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #15140f; --sheet: #1e1c17; --ink: #ece7dc; --muted: #a39d90; --rule: #3a362e;
  --story: #7fb3d9; --story-soft: #1b2b38; --wiki: #d9a05c; --wiki-soft: #332718;
  --ok: #7cc49a; --no: #e08674; --mark: #3b3418; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font: 17px/1.6 var(--serif); margin: 0; padding-block: 40px 96px; padding-inline: 16px }}
main {{ max-width: 68ch; margin: 0 auto }}
h1 {{ font: 600 34px/1.15 var(--serif); margin: 0 0 8px; text-wrap: balance }}
h2 {{ font: 600 22px/1.25 var(--serif); margin: 48px 0 12px; text-wrap: balance }}
h3 {{ font: 600 17px/1.3 var(--serif); margin: 24px 0 8px }}
p {{ margin: 0 0 14px }}
.kicker {{ font: 500 12px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 14px }}
.lede {{ font-size: 19px; color: var(--muted) }}
.verdicts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin: 24px 0 }}
.card {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; padding: 18px 20px; min-width: 0 }}
.card .who {{ font: 500 12px/1.2 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted) }}
.card .big {{ font: 600 32px/1.1 var(--serif); margin: 6px 0 10px; text-transform: capitalize }}
.card .big.ship {{ color: var(--ok) }} .card .big.pivot {{ color: var(--wiki) }} .card .big.kill {{ color: var(--no) }}
.card p {{ font-size: 15.5px; margin-bottom: 8px }}
ul.checks {{ list-style: none; padding: 0; margin: 10px 0 0; font: 14px/1.5 var(--mono) }}
ul.checks li {{ display: flex; gap: 10px; align-items: baseline }}
ul.checks .mark {{ font-weight: 500 }} ul.checks .ok .mark {{ color: var(--ok) }} ul.checks .no .mark {{ color: var(--no) }}
.measures {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 18px 0 }}
.m {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; padding: 14px 16px; min-width: 0 }}
.m .label {{ font: 500 12px/1.3 var(--mono); color: var(--muted); letter-spacing: .04em }}
.m .pair {{ display: flex; gap: 18px; margin-top: 8px; font-variant-numeric: tabular-nums }}
.m .pair div {{ flex: 1 }} .m .pair b {{ display: block; font: 600 26px/1.1 var(--serif) }}
.m .pair small {{ font: 12px/1.2 var(--mono); color: var(--muted) }}
.m .ci {{ font: 12.5px/1.4 var(--mono); color: var(--muted); margin-top: 8px }}
.tag {{ display: inline-block; padding: 1px 7px; border-radius: 4px; font: 500 12px/1.4 var(--mono) }}
.tag.story {{ background: var(--story-soft); color: var(--story) }} .tag.deepwiki {{ background: var(--wiki-soft); color: var(--wiki) }}
.tbl {{ overflow-x: auto; margin: 14px 0 }}
table {{ border-collapse: collapse; font: 13.5px/1.45 var(--mono); min-width: 100% }}
th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--rule); white-space: nowrap }}
th {{ font-weight: 500; color: var(--muted) }} td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums }}
tr.story td:nth-child(2) {{ color: var(--story) }} tr.deepwiki td:nth-child(2) {{ color: var(--wiki) }}
tr.insample td {{ color: var(--muted) }}
blockquote {{ margin: 12px 0; padding: 10px 16px; border-left: 3px solid var(--rule); color: var(--ink); background: var(--sheet); border-radius: 0 8px 8px 0 }}
blockquote.omoju {{ border-left-color: var(--story) }}
code {{ font: 14px var(--mono) }}
.foot {{ color: var(--muted); font-size: 14.5px; margin-top: 56px; border-top: 1px solid var(--rule); padding-top: 14px }}
a {{ color: var(--story) }}
</style>
<main>
<div class="kicker">comprehension · codestories · decided {e(R.get('decided', '2026-10-06'))}</div>
<h1>Is a CodeStory better than generated documentation?</h1>
<p class="lede">A repository told as a story that follows its data through one real run, every claim linked to pinned
lines and every chapter backed by a proof that runs, against DeepWiki's generated wiki for the same ten Python
libraries. The rule for deciding was written and committed before any result existed.</p>

<div class="verdicts">
  <div class="card">
    <div class="who">The preregistered rule (§8)</div>
    <div class="big {decision}">{decision}</div>
    <p>{e(meaning)}</p>
    <ul class="checks">{''.join(check_li(k, v) for k, v in checks.items())}</ul>
  </div>
  <div class="card">
    <div class="who">Omoju, after reading and before any metric (§9)</div>
    <div class="big">{e(verdict.split('—')[0].strip('* ').lower()) if verdict and '…' not in verdict.split('—')[0] else '—'}</div>
    <p>{e(verdict.split('—', 1)[1].strip()) if verdict and '—' in verdict else 'Not yet recorded.'}</p>
    <p><em>What "it helps" would feel like, written before the runs:</em> {e(feel) or '—'}</p>
  </div>
</div>

<h2>The measures</h2>
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
interval crosses a threshold, it says so here.</p>

<h3>Per repository</h3>
<div class="tbl"><table>
<tr><th>repo</th><th>arm</th><th class="n">words</th><th class="n">claims</th><th class="n">contradicted</th><th class="n">unverifiable</th><th class="n">per 1k words</th><th class="n">path</th><th class="n">general</th><th class="n">Jev agrees</th></tr>
{''.join(rows_html)}
</table></div>
<p><small>* in sample. "Jev agrees": a second, cheaper model's verdict on the same claim and the lines the judge cited.</small></p>

<h2>Robustness</h2>
<p>Every story was generated by the same pipeline with no hand edits. A chapter that failed a check (a citation to
lines that don't exist, a proof that doesn't pass) went back to the model with the verdict, at most twice.
"Refs resolve" is the share of DeepWiki's own <code>[path:lines]()</code> references that point at lines existing
at the commit its pages are pinned to.</p>
<div class="tbl"><table>
<tr><th>repo</th><th class="n">chapters</th><th class="n">citations</th><th class="n">repairs</th><th class="n">still failing</th><th class="n">cost</th><th class="n">time</th><th class="n">DeepWiki words</th><th class="n">refs resolve</th></tr>
{''.join(robust)}
</table></div>
<p>All ten stories: ${total_cost:.2f} in model calls. The evaluation itself (questions, extraction, judging, reading,
grading) is in <code>eval/</code> with every model response saved.</p>

<h2>Was the judge trustworthy?</h2>
<p>Before any comparison ran, the judge was tested on planted lies: 10 true claims per arm from the in-sample
repository, each with a false twin that changes one specific, judged blind among the truths.
Story claims: {jt['story']['caught']}/{jt['story']['lies']} lies caught, {jt['story']['alarms']}/{jt['story']['truths']} truths wrongly flagged.
DeepWiki claims: {jt['deepwiki']['caught']}/{jt['deepwiki']['lies']} caught, {jt['deepwiki']['alarms']}/{jt['deepwiki']['truths']} wrongly flagged.
The passing bar (every lie caught, at most one false alarm per arm) was written into the test before it ran.</p>
<p>{('Omoju hand-checked 20 judged claims with the arm hidden: agreed with the judge on '
     + ' and '.join(f"{hc[a]['agree']}/{hc[a]['n']} ({a})" for a in ARMS) + '.') if hc and any(hc[a]['n'] for a in ARMS)
    else 'Omoju’s hand check of 20 judged claims (§5.1.5) is recorded in <code>eval/handcheck.md</code>.'}</p>

<h2>What changed after preregistration</h2>
{''.join(f'<blockquote>{e(d).replace("**", "")}</blockquote>' for d in deviations()) or '<p>Nothing.</p>'}

<h2>Read one</h2>
<p>The reading page keeps the title, the real-world premise, a control-flow chart of the run drawn from executed
lines, and the code beside the narrative. Each chapter's proof is a file you can run.</p>
<ul>{''.join(f'<li><a href="{u}">{e(n)}</a></li>' for n, u in PAGES.items())}</ul>

<div class="foot">Preregistration, pipeline and every intermediate file are in the repository. The decision rule
was committed before the first result and is quoted here unchanged. Stories are written by Claude; this page is
generated from <code>eval/results.json</code>.</div>
</main>
"""
    (EVAL / "results.html").write_text(page)
    print(f"wrote eval/results.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
