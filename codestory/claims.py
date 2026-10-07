"""Does each passage tell the truth about the code it cites? Jev judges, one paragraph at a time.

    python3 codestory/claims.py stories/itsdangerous 01-once-upon-a-time.md [--dry-run]

verify.py proves the cited lines exist and haven't changed. It can't tell whether the sentence around a link
says something true about those lines. This asks Jev, per paragraph: given these exact lines, is every claim
here accurate? Answers are probabilities; below THRESHOLD a paragraph is flagged for a human or a rewrite.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jev import decide
from verify import find_citations, git, repo_path

# A contradiction is a lie: the story is wrong. "supported" is informational: narrative paragraphs always say more
# than the lines they link to, so it scores low on true prose too. The cut-off sits in the gap seen on
# planted-lie tests (lies 0.77-0.93, truths 0.12-0.51; Jev varies ~0.03 run to run). Fit on 14 paragraphs: provisional.
CONTRADICTED_FAIL = 0.7

_SCOPE = ("Read `passage`, then `code` (the exact source lines it links to). Storytelling (characters, "
          "metaphors) is fine; consider only factual claims about behaviour, names, values and order. ")

QUESTIONS = {
    "contradicted": {
        "type": "noul",
        "instructions": _SCOPE + "Does any claim in `passage` contradict what `code` shows?",
        "criteria": {
            "true": "at least one claim is contradicted by `code`",
            "false": "no claim is contradicted by `code`",
        },
    },
    "supported": {
        "type": "noul",
        "instructions": _SCOPE + "Is every factual claim in `passage` directly supported by `code`?",
        "criteria": {
            "true": "every factual claim can be confirmed from `code` alone",
            "false": "some claim cannot be confirmed from `code` alone",
        },
    },
}


def paragraphs_with_citations(text: str, outline: dict, repo: Path) -> list[dict]:
    """One judging state per paragraph that cites code: the prose (links reduced to their text) + cited lines."""
    commit = outline["repo"]["commit"]
    states = []
    for para in re.split(r"\n\s*\n", text):
        cites = find_citations(para, outline["repo"]["url"])
        if not cites:
            continue
        code = []
        for c in cites:
            lines = git(repo, "show", f"{commit}:{c.path}").splitlines()[c.start - 1 : c.end]
            code.append({"where": str(c), "lines": "\n".join(lines)})
        prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", para).strip()  # [text](url) -> text
        states.append({"passage": prose, "code": code})
    return states


def judge_text(text: str, outline: dict, repo: Path) -> list[dict]:
    """Judge every citing paragraph. Returns one result per paragraph, in order."""
    results = []
    for state in paragraphs_with_citations(text, outline, repo):
        a = decide(state, QUESTIONS)
        contra = a["contradicted"]["noul"]
        results.append({"first": state["passage"].splitlines()[0][:60], "contradicted": contra,
                        "supported": a["supported"]["noul"], "failed": contra >= CONTRADICTED_FAIL})
    return results


def main(story_dir: str, chapter: str, dry_run: bool) -> int:
    story = Path(story_dir)
    outline = json.loads((story / "outline.json").read_text())
    states = paragraphs_with_citations((story / chapter).read_text(), outline, repo_path(outline))

    failed = 0
    for i, state in enumerate(states, 1):
        first = state["passage"].splitlines()[0][:60]
        if dry_run:
            print(f"--- paragraph {i}: {first}…\n{json.dumps(state, indent=2)[:1200]}\n")
            continue
        a = decide(state, QUESTIONS)
        contra, sup = a["contradicted"]["noul"], a["supported"]["noul"]
        mark = "FAIL" if contra >= CONTRADICTED_FAIL else "ok  "
        failed += mark == "FAIL"
        print(f"  {mark} contradicted {contra:.2f}  supported {sup:.2f}  ¶{i} {first}…")

    if not dry_run:
        print(f"\n  {len(states)} paragraphs, {failed} contradicted (threshold {CONTRADICTED_FAIL})")
    return 1 if failed else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*args, dry_run="--dry-run" in sys.argv))
