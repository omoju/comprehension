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
    premise = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(o["premise"]))  # `x` → inline code chip
    return f"""<li>
  <a class="repo" href="{rel}/index.html"><span class="owner">{html.escape(owner)}/</span>{html.escape(name)}</a>
  <span class="headline">{html.escape(o['title'])}</span>
  {premise}
  <span class="meta">at <span class="sha">{repo['commit'][:7]}</span> · {len(rows)} chapters · {words:,} words · {cites} citations · for the {html.escape(o['reader'])}</span>
</li>"""


def main() -> None:
    entries = "\n".join(entry(r) for r in ORDER)
    # One source of truth for the look: the page links omojumiller.com's own stylesheet and uses its markup
    # (masthead, main > article.page-home > .post-body with marginal h2 heads). Only the stories list is styled here.
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CodeStories · Omoju Miller</title>
<meta name="description" content="Python libraries, each told as a story that follows its data through one real run, every claim pinned to lines, every chapter with a proof.">
<link rel="stylesheet" href="https://omojumiller.com/theme/css/style.css">
<style>
/* Only what the site's stylesheet has no rule for: the list of stories. */
ul.stories {{ list-style: none; padding-left: 0; margin-bottom: 1.15rem }}
ul.stories li {{ margin-bottom: 1.9rem; text-align: left; hyphens: none }}
ul.stories a.repo {{ display: block; font-size: 1.32rem; font-weight: 600; font-variant-caps: small-caps; letter-spacing: 0.045em; border-bottom: none; line-height: 1.3 }}
ul.stories a.repo .owner {{ font-weight: 400; color: var(--ink-faint) }}
ul.stories .headline {{ display: block; font-style: italic; color: var(--ink-soft); margin-bottom: 0.2rem }}
ul.stories .meta {{ display: block; font-size: 0.92rem; color: var(--ink-faint); font-variant-caps: small-caps; letter-spacing: 0.06em; margin-top: 0.1rem }}
.sha {{ font-family: var(--mono); font-size: 0.78em; color: var(--accent); background: var(--chip); padding: 0.12em 0.4em; border-radius: 4px; font-variant-numeric: normal; font-variant-caps: normal; letter-spacing: 0 }}
.page-home .post-body > p.aside {{ color: var(--ink-soft); font-size: 0.95rem; text-align: left; hyphens: none }}
.page-home .post-body > p.aside::first-letter, .page-home .post-body > p.aside::first-line {{ all: unset }}
</style></head><body>
<header>
  <h1><a href="https://omojumiller.com/">Omoju Miller</a></h1>
</header>
<main>
<article class="page-home">
  <div class="post-body">
  <h2>the stories</h2>
  <p>Python libraries, each told as a story that follows its data through one real run of the library's intended use.
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
  </div>
</article>
</main>
<footer><p>&copy; Omoju Miller. Stories by Claude, checked by code; <a href="https://github.com/omoju/comprehension">source and evaluation</a>.</p></footer>
</body></html>
"""
    (STORIES / "index.html").write_text(page)
    print(f"wrote stories/index.html ({len(ORDER)} stories)")


if __name__ == "__main__":
    main()
