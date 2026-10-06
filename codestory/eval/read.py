"""§5.2.3: the reader. A model answers the questions from one arm's text alone.

    .venv/bin/python codestory/eval/read.py <repo> [<repo> ...]      → eval/answers/<repo>.<arm>.json

No repository, no tools, no web. The text is the whole arm (all chapters without proofs; all DeepWiki pages).
Every question gets an answer; "the text does not say" is an allowed answer and is graded wrong (§5.2.4).
"""

from __future__ import annotations

import json
import sys

from common import ARMS, EVAL, arm_text, ask, save_trace, text_of, usage_cost

SYSTEM = """You answer questions about a software repository using only the documentation you are given. You
have not seen the code and cannot run it. Answer each question specifically (names, values, conditions), in a
few sentences at most. If the documentation does not settle a question, say so plainly rather than guessing;
if it gives partial information, give that and say what is missing."""

SCHEMA = {
    "type": "object",
    "properties": {"answers": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "answer": {"type": "string"}},
        "required": ["id", "answer"], "additionalProperties": False}}},
    "required": ["answers"], "additionalProperties": False,
}


def read(client, name: str, arm: str) -> dict:
    questions = json.loads((EVAL / "questions" / f"{name}.json").read_text())["questions"]
    listing = "\n".join(f"{q['id']}. {q['question']}" for q in questions)
    content = [{"type": "text", "text": f"<documentation>\n{arm_text(name, arm)}\n</documentation>", "cache_control": {"type": "ephemeral"}},
               {"type": "text", "text": f"<questions>\n{listing}\n</questions>\n\nAnswer every question from the documentation."}]
    response = ask(client, SYSTEM, content, SCHEMA)
    save_trace(EVAL / "answers" / "traces", f"{name}.{arm}", response)
    out = {"repo": name, "arm": arm, "answers": json.loads(text_of(response))["answers"], "cost": round(usage_cost(response.usage), 2)}
    (EVAL / "answers" / f"{name}.{arm}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    from common import client as make_client

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    client = make_client()
    for name in sys.argv[1:]:
        for arm in ARMS:
            r = read(client, name, arm)
            print(f"{name:13} {arm:9} {len(r['answers'])} answers  ${r['cost']:.2f}")
