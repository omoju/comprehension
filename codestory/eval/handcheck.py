"""§5.1.5: pull 20 judged claims (10 per arm, fixed seed) into one file for Omoju's hand check.

    .venv/bin/python codestory/eval/handcheck.py            → eval/handcheck.md
    .venv/bin/python codestory/eval/handcheck.py --score    reads the verdicts back and reports agreement

Each item shows the claim, the judge's label and reason, and the lines it cited, with the arm hidden. Omoju
writes `agree`, `disagree` or `unsure` after `Omoju:` on each item. No model calls. Standard library only.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from common import ARMS, EVAL, IN_SAMPLE, ROOT, SEED

PER_ARM = 10


def items() -> list[dict]:
    pool = []
    for f in sorted((EVAL / "judgments").glob("*.json")):
        if f.stem in IN_SAMPLE:
            continue
        for it in json.loads(f.read_text())["items"]:
            if it["label"] != "unjudged":
                pool.append({**it, "repo": f.stem})
    rng = random.Random(f"{SEED}:handcheck")
    chosen = []
    for arm in ARMS:
        chosen += rng.sample([p for p in pool if p["arm"] == arm], PER_ARM)
    rng.shuffle(chosen)
    return chosen


def cited(it: dict) -> str:
    out = []
    for ref in it["lines"][:4]:
        try:
            path, span = ref.rsplit(":", 1)
            start, _, end = span.partition("-")
            lines = (ROOT / it["tree"] / path).read_text(errors="replace").splitlines()[int(start) - 1 : int(end or start)]
            out.append(f"{ref}\n```\n" + "\n".join(lines[:40]) + ("\n…" if len(lines) > 40 else "") + "\n```")
        except (ValueError, OSError):
            out.append(f"{ref} (could not be read)")
    return "\n".join(out) or "(no lines cited)"


def write() -> None:
    chosen = items()
    md = ["# Hand check · 20 judged claims (§5.1.5)\n",
          "Write `agree`, `disagree` or `unsure` after **Omoju:** on each item. The arm is hidden; the key is in "
          "`eval/handcheck.key.json`.\n"]
    key = []
    for n, it in enumerate(chosen, 1):
        key.append({"n": n, "id": it["id"], "repo": it["repo"], "arm": it["arm"], "label": it["label"]})
        md += [f"## {n}. {it['repo']}", "", f"**Claim:** {it['claim']}", "",
               f"**Judge:** {it['label']} — {it['reason']}", "", cited(it), "", "**Omoju:** ", ""]
    (EVAL / "handcheck.md").write_text("\n".join(md))
    (EVAL / "handcheck.key.json").write_text(json.dumps(key, indent=2) + "\n")
    print(f"wrote eval/handcheck.md ({len(chosen)} items)")


def score() -> None:
    key = {k["n"]: k for k in json.loads((EVAL / "handcheck.key.json").read_text())}
    text = (EVAL / "handcheck.md").read_text()
    verdicts = {int(n): v.strip().lower() for n, v in re.findall(r"^## (\d+)\..*?\*\*Omoju:\*\*\s*(\w*)", text, re.M | re.S)}
    for arm in ARMS:
        ks = [k for k in key.values() if k["arm"] == arm]
        done = [k for k in ks if verdicts.get(k["n"]) in ("agree", "disagree", "unsure")]
        agree = sum(1 for k in done if verdicts[k["n"]] == "agree")
        print(f"{arm:9} {agree}/{len(done)} agree ({len(ks) - len(done)} unanswered)")
        for k in done:
            if verdicts[k["n"]] != "agree":
                print(f"    #{k['n']} {k['repo']} judge said {k['label']}, Omoju: {verdicts[k['n']]}")


if __name__ == "__main__":
    score() if "--score" in sys.argv else write()
