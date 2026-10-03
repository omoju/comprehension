"""§5.1.1–2: extract atomic claims from each arm's text, then sample 40 per repository per arm.

    .venv/bin/python codestory/eval/extract.py <repo> [<repo> ...]      → eval/claims/<repo>.<arm>.json

One extraction prompt for every arm. A claim is one checkable statement about the code: behaviour, a name, a
value, an order. Narrative, advice and opinions are not claims. The sample uses a fixed seed (§5.1.2); the
extraction count and the word count are kept, since the primary metric scales by claims per word (§5.1.4).
"""

from __future__ import annotations

import json
import random
import sys

from common import ARMS, EVAL, SEED, arm_text, ask, save_trace, text_of, usage_cost, words

SAMPLE = 40

SYSTEM = """You extract factual claims from documentation about a software repository, for checking against the
code. A claim is one atomic, checkable statement about the code: what a function or class does, a name, a value,
a default, a condition, an order of operations, what is returned or raised. Rewrite each so it stands alone:
name the function, class, file or value it is about, and resolve "it" and "this". One fact per claim.

Not claims: narrative and metaphor, advice to the reader, opinions, descriptions of the documentation itself,
statements about tests, CI, packaging or project history, and example input the text invents (only what the code
does with it). Where a passage makes several claims, list each. Be exhaustive: every checkable statement in the
text, in order of appearance. For each, quote the exact phrase of the text it comes from (a few words) so it
can be found again."""

SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "items": {
        "type": "object",
        "properties": {"claim": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["claim", "quote"], "additionalProperties": False}}},
    "required": ["claims"], "additionalProperties": False,
}


def extract(client, name: str, arm: str) -> dict:
    text = arm_text(name, arm)
    response = ask(client, SYSTEM, f"<text>\n{text}\n</text>\n\nList every checkable claim in the text.", SCHEMA, max_tokens=64000)
    save_trace(EVAL / "claims" / "traces", f"{name}.{arm}", response)
    claims = json.loads(text_of(response))["claims"]
    rng = random.Random(f"{SEED}:{name}:{arm}")  # fixed, per repo and arm, so a rerun samples the same claims
    sample = rng.sample(range(len(claims)), min(SAMPLE, len(claims)))
    out = {"repo": name, "arm": arm, "words": words(text), "extracted": len(claims),
           "sample": sorted(sample), "claims": claims, "stop_reason": response.stop_reason,
           "cost": round(usage_cost(response.usage), 2)}
    (EVAL / "claims" / f"{name}.{arm}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    import anthropic

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    client = anthropic.Anthropic()
    for name in sys.argv[1:]:
        for arm in ARMS:
            r = extract(client, name, arm)
            print(f"{name:13} {arm:9} {r['words']:7,} words → {r['extracted']:4} claims "
                  f"({1000 * r['extracted'] / r['words']:.0f}/1k words), sampled {len(r['sample'])}  ${r['cost']:.2f}"
                  + ("" if r["stop_reason"] == "end_turn" else f"  ! stopped: {r['stop_reason']}"))
