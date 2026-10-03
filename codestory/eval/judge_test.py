"""Test the judge on known answers before trusting it (CLAUDE.md: a judge is tested before it is trusted).

    .venv/bin/python codestory/eval/judge_test.py [<repo>]       default: itsdangerous (in-sample, so it costs nothing)

Takes N true claims per arm from the extraction (the sampled ones) and asks a model to write a falsified twin of
each: the same sentence with one specific changed (a name, value, default, order, condition) so that the code
contradicts it. The judge then labels all 4N claims blind, in the usual batches. Reports the confusion matrix
for Claude's labels and Jev's probabilities. Passing bar, set before running: every planted lie labelled
contradicted, and no more than one true claim labelled contradicted, per arm.
"""

from __future__ import annotations

import json
import random
import sys

from common import ARMS, EVAL, SEED, arm_commit, arm_tree, ask, save_trace, text_of, usage_cost
from judge import judge_claims

N = 10

SYSTEM = """You write test cases for a fact checker. For each true statement about a repository's code, write a
false twin: the same statement with exactly one specific changed (a name, a value, a default, an order, a
condition, or a behaviour) so that the code contradicts it. The twin must be plausible, the same length and
style, and definitely false about this repository, not merely vaguer. Do not negate with "not"; change the
specific."""

SCHEMA = {"type": "object", "properties": {"twins": {"type": "array", "items": {"type": "string"}}},
          "required": ["twins"], "additionalProperties": False}


def main(name: str) -> int:
    import anthropic

    client = anthropic.Anthropic()
    items, cost = [], 0.0
    for arm in ARMS:
        data = json.loads((EVAL / "claims" / f"{name}.{arm}.json").read_text())
        rng = random.Random(f"{SEED}:{name}:{arm}:test")
        truths = [data["claims"][i]["claim"] for i in rng.sample(data["sample"], min(N, len(data["sample"])))]
        response = ask(client, SYSTEM, "True statements:\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(truths))
                       + f"\n\nWrite the {len(truths)} false twins, in order.", SCHEMA)
        save_trace(EVAL / "judge-test" / "traces", f"{name}.{arm}.twins", response)
        cost += usage_cost(response.usage)
        twins = json.loads(text_of(response))["twins"]
        for i, (t, f) in enumerate(zip(truths, twins)):
            common = {"arm": arm, "commit": arm_commit(name, arm), "tree": str(arm_tree(name, arm))}
            items.append({"id": f"{arm}:t{i}", "claim": t, "truth": True, **common})
            items.append({"id": f"{arm}:f{i}", "claim": f, "truth": False, **common})

    # Reuse the real judge on these items by handing them in as the sampled claims.
    import judge as J
    J.sampled_claims = lambda _name: random.Random(SEED).sample(items, len(items))  # type: ignore[assignment]
    result = judge_claims(client, name)
    cost += result["cost"]
    (EVAL / "judge-test" / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    (EVAL / "judgments" / f"{name}.json").unlink()  # a test, not a result: run.py must still judge the real claims

    ok = True
    for arm in ARMS:
        its = [i for i in result["items"] if i["arm"] == arm]
        lies = [i for i in its if not i["truth"]]
        truths = [i for i in its if i["truth"]]
        caught = sum(1 for i in lies if i["label"] == "contradicted")
        false_alarms = sum(1 for i in truths if i["label"] == "contradicted")
        jev = [i for i in its if i.get("jev_contradicted") is not None]
        jev_caught = sum(1 for i in jev if not i["truth"] and i["jev_contradicted"] >= 0.7)
        jev_alarms = sum(1 for i in jev if i["truth"] and i["jev_contradicted"] >= 0.7)
        print(f"{arm:9} Claude: {caught}/{len(lies)} lies caught, {false_alarms}/{len(truths)} truths called lies   "
              f"Jev: {jev_caught}/{sum(1 for i in jev if not i['truth'])} caught, {jev_alarms}/{sum(1 for i in jev if i['truth'])} alarms")
        for i in its:
            if (i["truth"] and i["label"] == "contradicted") or (not i["truth"] and i["label"] != "contradicted"):
                print(f"    {'MISSED LIE ' if not i['truth'] else 'FALSE ALARM'} [{i['label']}] {i['claim'][:110]}\n      → {i['reason'][:150]}")
        ok &= caught == len(lies) and false_alarms <= 1
    print(f"\n${cost:.2f}   {'PASS' if ok else 'FAIL'}: {'the judge may be used' if ok else 'fix the judge before the comparison'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "itsdangerous"))
