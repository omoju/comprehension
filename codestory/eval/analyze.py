"""§7–8: the metrics, their uncertainty, and the decision rule.

    .venv/bin/python codestory/eval/analyze.py           → eval/results.json and eval/results.md

Pooled over the out-of-sample repositories (itsdangerous reported separately). H1: contradicted claims per 1,000
words = (contradicted ÷ sampled) × (extracted ÷ words × 1000). H2: percentage score on path and on general
questions, paired by question. Uncertainty: 95% bootstrap intervals resampling whole repositories, 10,000
resamples, fixed seed. The decision uses the point estimates. No model calls. Standard library only.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from common import ARMS, EVAL, IN_SAMPLE, SEED

SCORE = {"correct": 1.0, "partly": 0.5, "wrong": 0.0}
RESAMPLES = 10_000


def per_repo(name: str) -> dict | None:
    j, g = EVAL / "judgments" / f"{name}.json", EVAL / "grades" / f"{name}.json"
    if not (j.exists() and g.exists()):
        return None
    judgments, grades = json.loads(j.read_text()), json.loads(g.read_text())
    row = {"repo": name}
    for arm in ARMS:
        claims = json.loads((EVAL / "claims" / f"{name}.{arm}.json").read_text())
        its = [i for i in judgments["items"] if i["arm"] == arm]
        contradicted = sum(1 for i in its if i["label"] == "contradicted")
        density = (contradicted / len(its)) * (claims["extracted"] / claims["words"] * 1000) if its else None
        scores = {k: [SCORE.get(x["grade"], 0) for x in grades["arms"][arm] if x["kind"] == k] for k in ("path", "general")}
        row[arm] = {"words": claims["words"], "extracted": claims["extracted"], "sampled": len(its),
                    "contradicted": contradicted, "supported": sum(1 for i in its if i["label"] == "supported"),
                    "unverifiable": sum(1 for i in its if i["label"] == "unverifiable"),
                    "density": density, "path": scores["path"], "general": scores["general"],
                    "jev_agree": sum(1 for i in its if i.get("jev_contradicted") is not None
                                     and (i["jev_contradicted"] >= 0.7) == (i["label"] == "contradicted")),
                    "jev_n": sum(1 for i in its if i.get("jev_contradicted") is not None)}
    return row


def pooled(rows: list[dict]) -> dict:
    out = {}
    for arm in ARMS:
        contr = sum(r[arm]["contradicted"] for r in rows)
        sampled = sum(r[arm]["sampled"] for r in rows)
        extracted = sum(r[arm]["extracted"] for r in rows)
        words = sum(r[arm]["words"] for r in rows)
        path = [s for r in rows for s in r[arm]["path"]]
        general = [s for r in rows for s in r[arm]["general"]]
        out[arm] = {"density": (contr / sampled) * (extracted / words * 1000) if sampled else None,
                    "path": 100 * sum(path) / len(path) if path else None,
                    "general": 100 * sum(general) / len(general) if general else None}
    return out


def bootstrap(rows: list[dict]) -> dict:
    rng = random.Random(SEED)
    stats = {"density_ratio": [], "path_diff": [], "general_diff": []}
    for _ in range(RESAMPLES):
        sample = [rng.choice(rows) for _ in rows]
        p = pooled(sample)
        if p["deepwiki"]["density"]:
            stats["density_ratio"].append(p["story"]["density"] / p["deepwiki"]["density"])
        if p["story"]["path"] is not None and p["deepwiki"]["path"] is not None:
            stats["path_diff"].append(p["story"]["path"] - p["deepwiki"]["path"])
        if p["story"]["general"] is not None and p["deepwiki"]["general"] is not None:
            stats["general_diff"].append(p["story"]["general"] - p["deepwiki"]["general"])
    def ci(xs):
        xs = sorted(xs)
        return [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]] if xs else None
    return {k: ci(v) for k, v in stats.items()}


def decide(p: dict) -> tuple[str, dict]:
    """§8, verbatim: ship / pivot / kill."""
    s, d = p["story"], p["deepwiki"]
    h1 = s["density"] is not None and d["density"] is not None and s["density"] <= 0.5 * d["density"]
    general_ok = s["general"] is not None and s["general"] >= d["general"] - 5
    path_ok = s["path"] is not None and s["path"] >= d["path"] + 10
    checks = {"H1: story density <= 1/2 DeepWiki": h1, "general: story >= DeepWiki - 5": general_ok, "path: story >= DeepWiki + 10": path_ok}
    return ("ship" if h1 and general_ok and path_ok else "pivot" if h1 else "kill"), checks


def main() -> None:
    names = [l.split()[0] for l in (EVAL.parent / "demo-repos.lock").read_text().splitlines() if l and not l.startswith("#")]
    rows = [r for r in (per_repo(n) for n in names) if r]
    out_sample = [r for r in rows if r["repo"] not in IN_SAMPLE]
    if not out_sample:
        print("no complete repositories yet")
        return
    p = pooled(out_sample)
    ci = bootstrap(out_sample)
    verdict, checks = decide(p)
    results = {"repos": rows, "pooled_out_of_sample": p, "pooled_all": pooled(rows), "ci95": ci,
               "decision": verdict, "checks": checks, "n_repos": len(out_sample)}
    (EVAL / "results.json").write_text(json.dumps(results, indent=2) + "\n")

    f = lambda x, d=1: "—" if x is None else f"{x:.{d}f}"  # noqa: E731
    md = [f"# Results · {len(out_sample)} out-of-sample repositories\n",
          "| | Story | DeepWiki |", "|---|---|---|",
          f"| contradicted claims / 1k words | {f(p['story']['density'], 2)} | {f(p['deepwiki']['density'], 2)} |",
          f"| path questions | {f(p['story']['path'])}% | {f(p['deepwiki']['path'])}% |",
          f"| general questions | {f(p['story']['general'])}% | {f(p['deepwiki']['general'])}% |",
          "", f"95% CI (repos resampled): density ratio {ci['density_ratio']}, path diff {ci['path_diff']}, general diff {ci['general_diff']}",
          "", f"**Decision by §8: {verdict.upper()}**", ""] + [f"- {'✓' if v else '✗'} {k}" for k, v in checks.items()]
    md += ["", "## Per repository", "", "| repo | arm | words | claims | sampled | contradicted | unverifiable | density | path | general | Jev agrees |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for arm in ARMS:
            a = r[arm]
            md.append(f"| {r['repo']}{'*' if r['repo'] in IN_SAMPLE else ''} | {arm} | {a['words']:,} | {a['extracted']} | {a['sampled']} | {a['contradicted']} | {a['unverifiable']} "
                      f"| {f(a['density'], 2)} | {f(100 * sum(a['path']) / len(a['path']) if a['path'] else None)}% | {f(100 * sum(a['general']) / len(a['general']) if a['general'] else None)}% | {a['jev_agree']}/{a['jev_n']} |")
    md.append("\n\\* in-sample, excluded from the decision")
    (EVAL / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
