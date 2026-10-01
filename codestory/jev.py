"""Jev (TypeSafe) via Cloudflare Workers AI: cheap, fast, typed decisions. It never writes prose.

    export CLOUDFLARE_ACCOUNT_ID=...  CLOUDFLARE_API_TOKEN=...
    python3 codestory/jev.py          # smoke test

Question types (Cloudflare's names):
    noul    yes/no, answered as a probability            {"type": "noul", "instructions": ..., "criteria": {"true": ..., "false": ...}}
    choice  one of several named options                 {"type": "choice", "instructions": ..., "criteria": {"opt": "meaning", ...}}
    score   an ordered scale, low to high (2+ levels)    {"type": "score", "instructions": ..., "criteria": ["low", ..., "high"]}

Standard library only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import env  # noqa: F401  (loads .env)

MODEL = "typesafe/jev"
MAX_STATE_CHARS = 100_000  # Jev's context is 32k tokens; stay well under


class JevError(RuntimeError):
    pass


def decide(state: object, questions: dict) -> dict:
    """Ask Jev every question about one state, in a single call. Returns {question_name: answer}."""
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (account and token):
        raise JevError("set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN")
    if len(json.dumps(state)) > MAX_STATE_CHARS:
        raise JevError(f"state too large for Jev ({len(json.dumps(state)):,} chars)")

    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run",
        data=json.dumps({"model": MODEL, "input": {"state": state, "questions": questions}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        raise JevError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}") from e

    # Through the gateway the output is wrapped twice: {"result": {"state": ..., "result": {"answers": ...}}}
    result = body
    while "answers" not in result and isinstance(result.get("result"), dict):
        result = result["result"]
    if "answers" not in result:
        raise JevError(f"unexpected response: {json.dumps(body)[:500]}")
    return result["answers"]


if __name__ == "__main__":
    answers = decide(
        state={"sentence": "The separator defaults to a single dot.", "code": 'sep: str | bytes = b".",'},
        questions={
            "supported": {
                "type": "noul",
                "instructions": "Is `sentence` an accurate description of `code`?",
                "criteria": {"true": "accurate", "false": "inaccurate or not supported"},
            }
        },
    )
    print(json.dumps(answers, indent=2))
