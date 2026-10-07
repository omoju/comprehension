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


def card(rel: str) -> str:
    d = STORIES / rel
    o = json.loads((d / "outline.json").read_text())
    rows = re.findall(r"^\| (\d+) \| \[.*?\]\(.*?\) \| (\d+) \| (\d+) \|", (d / "report.md").read_text(), re.M)
    words, cites = sum(int(r[1]) for r in rows), sum(int(r[2]) for r in rows)
    repo = o["repo"]
    return f"""<a class="card" href="{rel}/index.html">
  <div class="repo">{html.escape(repo['name'])} <span class="sha">@ {repo['commit'][:7]}</span></div>
  <h2>{html.escape(o['title'])}</h2>
  <p>{html.escape(o['premise'])}</p>
  <div class="meta">{len(rows)} chapters · {words:,} words · {cites} citations · reader: {html.escape(o['reader'])}</div>
</a>"""


def main() -> None:
    cards = "\n".join(card(r) for r in ORDER)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>CodeStories</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{ --bg: #f7f5f0; --sheet: #fff; --ink: #1d1b17; --muted: #5f5b53; --rule: #d9d4c9; --accent: #1f5f8b;
  --serif: "Source Serif 4", Georgia, serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: #15140f; --sheet: #1f1d18; --ink: #ece7dc; --muted: #a39d90; --rule: #3a362e; --accent: #7fb3d9; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg: #15140f; --sheet: #1f1d18; --ink: #ece7dc; --muted: #a39d90; --rule: #3a362e; --accent: #7fb3d9; color-scheme: dark }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.6 var(--serif); padding-block: 40px 80px; padding-inline: 16px }}
main {{ max-width: 1100px; margin: 0 auto }}
.kicker {{ font: 500 12px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted) }}
h1 {{ font: 600 34px/1.15 var(--serif); margin: 6px 0 10px }}
.lede {{ color: var(--muted); max-width: 70ch; font-size: 18px; margin: 0 0 28px }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px }}
.card {{ display: block; background: var(--sheet); border: 1px solid var(--rule); border-radius: 12px; padding: 18px 20px; color: inherit; text-decoration: none; min-width: 0 }}
.card:hover, .card:focus-visible {{ border-color: var(--accent); outline: none }}
.card .repo {{ font: 500 12.5px var(--mono); color: var(--accent) }} .card .sha {{ color: var(--muted); font-weight: 400 }}
.card h2 {{ font: 600 20px/1.25 var(--serif); margin: 8px 0 8px; text-wrap: balance }}
.card p {{ margin: 0 0 12px; font-size: 15px; color: var(--muted); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden }}
.card .meta {{ font: 12px/1.4 var(--mono); color: var(--muted) }}
.foot {{ margin-top: 36px; color: var(--muted); font-size: 15px; max-width: 70ch }}
</style></head><body><main>
<div class="kicker">comprehension · codestories</div>
<h1>Ten repositories, told as stories</h1>
<p class="lede">Each page follows one real run of a library's intended use: a control-flow chart of that run on the left, the story
in the middle, the code it cites on the right. Every claim links to lines at a pinned commit; every chapter has a proof you
can run. Written by Claude, checked by code; the comparison that decided their fate is in the repository.</p>
<div class="grid">
{cards}
</div>
<p class="foot">The three-pane layout needs a window about 1,360px wide; narrower screens show the code as a sheet you open from the text.
Pages are static and self-contained: the code you see is embedded from the repository at the pinned commit.</p>
</main></body></html>
"""
    (STORIES / "index.html").write_text(page)
    print(f"wrote stories/index.html ({len(ORDER)} stories)")


if __name__ == "__main__":
    main()
