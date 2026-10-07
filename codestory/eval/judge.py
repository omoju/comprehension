"""The judge: §5.1.3 labels claims against the code; §5.2.4 grades answers against keys. Blind in both roles.

    .venv/bin/python codestory/eval/judge.py claims <repo> [<repo> ...]    → eval/judgments/<repo>.json
    .venv/bin/python codestory/eval/judge.py grade  <repo> [<repo> ...]    → eval/grades/<repo>.json

Claims: the sampled claims of both arms are shuffled together (fixed seed), grouped by the commit they describe,
and judged in batches of BATCH with the whole repository at that commit in context (the same cached repo block
the pipeline uses). The judge never sees which arm a claim came from. Each verdict is contradicted / supported /
unverifiable with the lines that decide it. Jev then gives a second, independent probability of contradiction
from the claim and those lines alone (§6); agreement is reported, Claude's label decides.

Grades: each answer is compared with its key, correct / partly / wrong, without the arm being named.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from common import ARMS, EVAL, ROOT, SEED, arm_commit, arm_tree, ask, save_trace, text_of, usage_cost
from jev import JevError, decide
from outline import NOISE, git, repo_context, repo_info

BATCH = 20

CLAIMS_SYSTEM = """You check claims about a software repository against its source code. You are shown the
repository at one commit, then a numbered list of claims. For each claim decide:
- "contradicted": the code shows the claim is false (a different name, value, default, order, behaviour).
- "supported": the code shows the claim is true.
- "unverifiable": the code shown cannot settle it (it is about something outside the repository, too vague to
  check, or in a file not shown).
Read the actual lines before deciding; do not rely on what a library usually does. A claim that is true but
imprecise is supported; a claim that is wrong in any specific is contradicted. For each verdict give the lines
that decide it as "path:start-end" (one or more), and one sentence of reason. Judge every claim."""

CLAIMS_SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "n": {"type": "integer"},
            "label": {"type": "string", "enum": ["contradicted", "supported", "unverifiable"]},
            "lines": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
        },
        "required": ["n", "label", "lines", "reason"], "additionalProperties": False}}},
    "required": ["verdicts"], "additionalProperties": False,
}

JEV_QUESTION = {"contradicted": {
    "type": "noul",
    "instructions": "Read `claim`, then `code` (source lines from the repository it describes). Does `code` show "
                    "that `claim` is false in any specific (name, value, default, order, behaviour)?",
    "criteria": {"true": "the code contradicts the claim", "false": "the code does not contradict the claim"},
}}

GRADE_SYSTEM = """You grade answers to questions about a software repository. For each item you see the question,
the key (the correct answer, written by someone who read the code), and a reader's answer. Grade the answer:
- "correct": it states what the key states, in substance; extra correct detail is fine.
- "partly": it has the main point but misses or muddles a specific the key names, or is incomplete.
- "wrong": it contradicts the key, answers a different question, or says it does not know.
Grade on substance, not wording. Do not reward confident prose. Give one sentence of reason per item."""

GRADE_SCHEMA = {
    "type": "object",
    "properties": {"grades": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "grade": {"type": "string", "enum": ["correct", "partly", "wrong"]},
                       "reason": {"type": "string"}},
        "required": ["id", "grade", "reason"], "additionalProperties": False}}},
    "required": ["grades"], "additionalProperties": False,
}


def lines_text(tree: Path, refs: list[str]) -> str:
    """The cited lines, for Jev. Bad references are skipped: Jev then sees less, and says so by its score."""
    out = []
    for ref in refs:
        try:
            path, span = ref.rsplit(":", 1)
            start, _, end = span.partition("-")
            start, end = int(start), int(end or start)
            text = (tree / path).read_text(errors="replace").splitlines()[start - 1 : end]
            out.append(f"# {ref}\n" + "\n".join(text))
        except (ValueError, OSError, IndexError):
            continue
    return "\n\n".join(out)


IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def judge_block(tree: Path, claims: list[str]) -> dict:
    """The repository for the judge, source first: the files these claims name, then every other non-test source
    file, then docs. Without this, the shared repo block led with README and docs and, in the large repositories,
    left out the very files the claims were about (the first run's "unverifiable" column)."""
    info = repo_info(tree)
    paths = [p for p in git(tree, "ls-files").splitlines() if not NOISE.search(p)]
    skip = re.compile(r"(^|/)(tests?|examples?|docs?|benchmarks?|scripts?|tools?)/|(^|/)(test_|conftest|setup\.py|bench)")
    source = [p for p in paths if p.endswith(".py") and not skip.search(p)]
    names = {t for c in claims for t in IDENT.findall(c)}
    joined = " ".join(claims)

    def score(p: str) -> tuple:
        """Lower sorts first: files the claims name by module or path, then files defining the most named things."""
        stem = Path(p).stem.lstrip("_")
        by_name = stem.lower() in {n.lower() for n in names} or Path(p).name in joined
        try:
            text = (tree / p).read_text()
        except (UnicodeDecodeError, OSError):
            return (2, 0)
        defined = sum(1 for n in names if f"def {n}(" in text or f"class {n}(" in text or f"class {n}:" in text)
        return (0 if by_name else 1 if defined else 2, -defined)

    ranked = sorted(source, key=score)
    first = [p for p in ranked if score(p)[0] < 2]
    focus = set(first) | set(source)
    text = f"Repository: {info['name']} at commit {info['commit'][:7]}\n\n{repo_context(tree, focus, order=first)}"
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


def sampled_claims(name: str) -> list[dict]:
    items = []
    for arm in ARMS:
        data = json.loads((EVAL / "claims" / f"{name}.{arm}.json").read_text())
        for i in data["sample"]:
            items.append({"id": f"{arm}:{i}", "arm": arm, "claim": data["claims"][i]["claim"],
                          "commit": arm_commit(name, arm), "tree": str(arm_tree(name, arm).relative_to(ROOT))})
    random.Random(f"{SEED}:{name}:judge").shuffle(items)
    return items


def judge_claims(client, name: str) -> dict:
    items = sampled_claims(name)
    cost = 0.0
    by_tree: dict[str, list[dict]] = {}
    for it in items:
        by_tree.setdefault(it["tree"], []).append(it)
    for tree, group in by_tree.items():
        tree_path = ROOT / tree
        for b in range(0, len(group), BATCH):
            batch = group[b : b + BATCH]
            block = judge_block(tree_path, [it["claim"] for it in batch])
            listing = "\n".join(f"{i + 1}. {it['claim']}" for i, it in enumerate(batch))
            response = ask(client, CLAIMS_SYSTEM, [block, {"type": "text", "text": f"<claims>\n{listing}\n</claims>\n\nJudge every claim."}],
                           CLAIMS_SCHEMA)
            save_trace(EVAL / "judgments" / "traces", f"{name}.{tree_path.name}.{b // BATCH}", response)
            cost += usage_cost(response.usage)
            verdicts = {v["n"]: v for v in json.loads(text_of(response))["verdicts"]}
            for i, it in enumerate(batch):
                v = verdicts.get(i + 1)
                it["label"] = v["label"] if v else "unjudged"  # §10: logged, not silently dropped
                it["lines"], it["reason"] = (v["lines"], v["reason"]) if v else ([], "no verdict returned")
                code = lines_text(tree_path, it["lines"])
                try:  # the second judge sees only the claim and the lines Claude cited
                    it["jev_contradicted"] = decide({"claim": it["claim"], "code": code}, JEV_QUESTION)["contradicted"]["noul"] if code else None
                except JevError as e:
                    it["jev_contradicted"] = None
                    it["jev_error"] = str(e)[:200]
    out = {"repo": name, "items": items, "cost": round(cost, 2)}
    (EVAL / "judgments" / f"{name}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def grade(client, name: str) -> dict:
    questions = {q["id"]: q for q in json.loads((EVAL / "questions" / f"{name}.json").read_text())["questions"]}
    out, cost = {"repo": name, "arms": {}}, 0.0
    for arm in ARMS:
        answers = json.loads((EVAL / "answers" / f"{name}.{arm}.json").read_text())["answers"]
        items = [{"id": a["id"], "question": questions[a["id"]]["question"], "key": questions[a["id"]]["key"],
                  "answer": a["answer"]} for a in answers if a["id"] in questions]
        grades: dict[str, dict] = {}
        for attempt in range(2):  # a grader that skips an item is asked once more for just the ones it skipped
            todo = [it for it in items if it["id"] not in grades]
            if not todo:
                break
            response = ask(client, GRADE_SYSTEM, f"<items>\n{json.dumps(todo, indent=1)}\n</items>\n\nGrade every item.", GRADE_SCHEMA)
            save_trace(EVAL / "grades" / "traces", f"{name}.{arm}" + (f".retry{attempt}" if attempt else ""), response)
            cost += usage_cost(response.usage)
            grades.update({g["id"]: g for g in json.loads(text_of(response))["grades"] if g["id"] in {it["id"] for it in todo}})
        out["arms"][arm] = [{"id": it["id"], "kind": questions[it["id"]]["kind"], **grades.get(it["id"], {"grade": "ungraded", "reason": ""})}
                            for it in items]
    out["cost"] = round(cost, 2)
    (EVAL / "grades" / f"{name}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


SCORE = {"correct": 1.0, "partly": 0.5, "wrong": 0.0}

if __name__ == "__main__":
    from common import client as make_client

    if len(sys.argv) < 3 or sys.argv[1] not in ("claims", "grade"):
        print(__doc__)
        sys.exit(2)
    client = make_client()
    for name in sys.argv[2:]:
        if sys.argv[1] == "claims":
            r = judge_claims(client, name)
            for arm in ARMS:
                its = [i for i in r["items"] if i["arm"] == arm]
                c = sum(1 for i in its if i["label"] == "contradicted")
                u = sum(1 for i in its if i["label"] == "unverifiable")
                agree = [i for i in its if i.get("jev_contradicted") is not None]
                same = sum(1 for i in agree if (i["jev_contradicted"] >= 0.7) == (i["label"] == "contradicted"))
                print(f"{name:13} {arm:9} {c:2} contradicted, {u:2} unverifiable of {len(its)}; Jev agrees on {same}/{len(agree)}")
            print(f"{'':13} ${r['cost']:.2f}")
        else:
            r = grade(client, name)
            for arm in ARMS:
                for kind in ("path", "general"):
                    g = [SCORE.get(x["grade"], 0) for x in r["arms"][arm] if x["kind"] == kind]
                    print(f"{name:13} {arm:9} {kind:8} {100 * sum(g) / max(len(g), 1):5.1f}%  ({len(g)} q)")
            print(f"{'':13} ${r['cost']:.2f}")
