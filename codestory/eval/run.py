"""Run the whole evaluation for one repository, in the preregistered order, skipping steps already done.

    .venv/bin/python codestory/eval/run.py <repo> [<repo> ...]

Order matters (§5.2.1): questions are written before any arm is read. Then claims are extracted from both arms,
judged, the reader answers from each arm, and the answers are graded. analyze.py pools the results.
"""

from __future__ import annotations

import sys
import time

from common import ARMS, EVAL
from extract import extract
from judge import grade, judge_claims
from questions import write_questions
from read import read


def run(client, name: str) -> None:
    t0 = time.time()
    steps = [
        ("questions", EVAL / "questions" / f"{name}.json", lambda: write_questions(client, name)),
        *[(f"extract {arm}", EVAL / "claims" / f"{name}.{arm}.json", (lambda a=arm: extract(client, name, a))) for arm in ARMS],
        ("judge", EVAL / "judgments" / f"{name}.json", lambda: judge_claims(client, name)),
        *[(f"read {arm}", EVAL / "answers" / f"{name}.{arm}.json", (lambda a=arm: read(client, name, a))) for arm in ARMS],
        ("grade", EVAL / "grades" / f"{name}.json", lambda: grade(client, name)),
    ]
    for label, out, step in steps:
        if out.exists():
            print(f"{name:13} {label:17} (done)", flush=True)
            continue
        r = step()
        print(f"{name:13} {label:17} ${r.get('cost', 0):.2f}  {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    from common import client as make_client

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    client = make_client()
    for name in sys.argv[1:]:
        run(client, name)
