"""The front page of the stories: one card per story, linking to its reading page.

    .venv/bin/python codestory/gallery.py        → stories/index.html

Reads each story's outline.json (title, premise, repo, commit) and report.md (chapters, words, citations).
No model calls. Standard library only.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "stories"
ORDER = ["itsdangerous-close-third", "bench/requests", "bench/flask", "bench/click", "bench/httpx", "bench/rich",
         "bench/attrs", "bench/jinja", "bench/markupsafe", "bench/tqdm", "tomli"]


def entry(rel: str) -> str:
    d = STORIES / rel
    o = json.loads((d / "outline.json").read_text())
    rows = re.findall(r"^\| (\d+) \| \[.*?\]\(.*?\) \| (\d+) \| (\d+) \|", (d / "report.md").read_text(), re.M)
    words, cites = sum(int(r[1]) for r in rows), sum(int(r[2]) for r in rows)
    repo = o["repo"]
    owner, name = repo["name"].split("/", 1)
    return f"""<li>
  <a class="repo" href="{rel}/index.html"><span class="owner">{html.escape(owner)}/</span>{html.escape(name)}</a>
  <span class="headline">{html.escape(o['title'])}</span>
  {html.escape(o['premise'])}
  <span class="meta">at <span class="sha">{repo['commit'][:7]}</span> · {len(rows)} chapters · {words:,} words · {cites} citations · for the {html.escape(o['reader'])}</span>
</li>"""


def main() -> None:
    entries = "\n".join(entry(r) for r in ORDER)
    # The page follows omojumiller.com's own stylesheet (themes/minimalist in omoju/omoju.github.io): EB Garamond,
    # paper and ink, small-caps heads, a marginal section head in the one accent colour, a fleuron for a rule.
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CodeStories · Omoju Miller</title>
<meta name="description" content="Ten Python libraries, each told as a story that follows its data through one real run, every claim pinned to lines, every chapter with a proof.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800&family=Inter:wght@400;500;600&display=swap">
<style>
:root {{ --ink: #211f1b; --ink-soft: #3d3931; --ink-faint: #56514a; --paper: #fdfdfa; --rule: #cdc8bd; --accent: #AA0000; --link: #483D8B;
  --sans: 'Inter', -apple-system, 'Helvetica Neue', sans-serif; --serif: 'EB Garamond', Garamond, Georgia, serif;
  --mono: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', monospace; --chip: #efede6 }}
* {{ margin: 0; padding: 0; box-sizing: border-box }}
body {{ font-family: var(--serif); font-size: 20px; line-height: 1.62; color: var(--ink); background: var(--paper); max-width: 53rem; margin: 0 auto; padding: 4rem 2rem;
  font-variant-numeric: oldstyle-nums proportional-nums; font-feature-settings: "onum" 1, "kern" 1, "liga" 1; text-rendering: optimizeLegibility; -webkit-font-smoothing: antialiased }}
header, main, footer {{ padding-left: 11rem }}
header {{ margin-bottom: 3rem; border-bottom: 1px solid var(--rule); padding-bottom: 1.2rem }}
h1 {{ font-size: 2.05rem; font-weight: 500; line-height: 1.25; font-variant-caps: small-caps; letter-spacing: 0.055em; margin-bottom: 0.4rem }}
h1 a {{ color: inherit; text-decoration: none }}
h1 a:hover {{ color: var(--accent) }}
main {{ margin-bottom: 4rem; position: relative }}
main > h2 {{ float: left; clear: left; width: 8.5rem; margin-left: -11rem; margin-top: 0.45rem; margin-bottom: 0.6rem; font-family: var(--sans); font-size: 0.78rem; font-weight: 500;
  text-transform: lowercase; text-align: right; letter-spacing: 0.02em; line-height: 1.3; color: var(--accent) }}
.title {{ font-size: 1.32rem; font-weight: 600; font-variant-caps: small-caps; letter-spacing: 0.045em; margin-bottom: 0.7rem; padding-bottom: 0.25rem; border-bottom: 1px solid var(--rule) }}
p {{ margin-bottom: 1.15rem; text-align: justify; hyphens: auto; -webkit-hyphens: auto }}
p.lede::first-letter {{ float: left; font-size: 3.4em; line-height: 0.82; padding: 0.06em 0.08em 0 0; margin-right: 0.04em; color: var(--accent); font-weight: 500 }}
p.lede::first-line {{ font-variant-caps: small-caps; letter-spacing: 0.03em }}
main a {{ color: var(--link); text-decoration: none; border-bottom: 1px solid rgba(72, 61, 139, 0.3); transition: border-color 0.15s ease, color 0.15s ease }}
main a:hover {{ color: var(--accent); border-bottom-color: var(--accent) }}
ul.stories {{ list-style: none; margin-bottom: 1.15rem }}
ul.stories li {{ margin-bottom: 1.9rem; text-align: left; hyphens: none }}
ul.stories a.repo {{ display: block; font-size: 1.32rem; font-weight: 600; font-variant-caps: small-caps; letter-spacing: 0.045em; border-bottom: none; line-height: 1.3 }}
ul.stories a.repo .owner {{ font-weight: 400; color: var(--ink-faint) }}
ul.stories .headline {{ display: block; font-style: italic; color: var(--ink-soft); margin-bottom: 0.2rem }}
ul.stories .meta {{ display: block; font-size: 0.92rem; color: var(--ink-faint); font-variant-caps: small-caps; letter-spacing: 0.06em; margin-top: 0.1rem }}
code, .sha {{ font-family: var(--mono); font-size: 0.78em; color: var(--accent); background: var(--chip); padding: 0.12em 0.4em; border-radius: 4px; font-variant-numeric: normal; font-variant-caps: normal; letter-spacing: 0 }}
hr {{ border: none; text-align: center; margin: 2.6rem 0 }} hr::before {{ content: "❧"; color: var(--ink-faint); font-size: 1.2rem }}
.aside {{ color: var(--ink-soft); font-size: 0.95rem; text-align: left; hyphens: none }}
footer {{ border-top: 1px solid var(--rule); padding-top: 1.2rem; color: var(--ink-faint); font-size: 0.92rem }} footer a {{ color: inherit }}
@media (max-width: 60rem) {{ header, main, footer {{ padding-left: 0 }} main > h2 {{ float: none; width: auto; margin: 1.6rem 0 0.6rem; text-align: left }} body {{ padding: 2.4rem 1.2rem; font-size: 18px }} }}
</style></head><body>
<header>
  <h1><a href="https://omojumiller.com/">Omoju Miller</a></h1>
</header>
<main>
  <h2>the stories</h2>
  <div class="title">CodeStories</div>
  <p class="lede">Ten Python libraries, each told as a story that follows its data through one real run of the library's intended use.
  The page you open has three panes: a control-flow chart of that run, the story, and the code it cites, side by side. Every
  claim links to lines at a pinned commit; every chapter ends in a proof you can run. The stories were written by Claude and
  checked by code; the comparison that decided their fate, preregistered and run against DeepWiki, is in
  <a href="https://github.com/omoju/comprehension">the repository</a>.</p>
  <ul class="stories">
{entries}
  </ul>
  <hr>
  <h2>reading them</h2>
  <p class="aside">The three panes need a window about 1,360 pixels wide; on a narrower screen the code opens as a sheet from the text.
  Each page is a single static file with the cited code embedded from the repository at the pinned commit, so nothing on it
  can drift from what the story was checked against. The proofs live beside each story as <code>proofs/NN.py</code>.</p>
</main>
<footer><p>&copy; Omoju Miller. Stories by Claude, checked by code; <a href="https://github.com/omoju/comprehension">source and evaluation</a>.</p></footer>
</body></html>
"""
    (STORIES / "index.html").write_text(page)
    print(f"wrote stories/index.html ({len(ORDER)} stories)")


if __name__ == "__main__":
    main()
