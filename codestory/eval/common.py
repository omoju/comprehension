"""Shared pieces of the evaluation: the repositories, the arms' texts, and one way to call the model.

Everything here follows PREREGISTRATION.md; section numbers in comments refer to it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "codestory"))  # the pipeline's modules: env (keys), outline (repo block, MODEL)

import env  # noqa: E402, F401
from outline import MODEL, repo_block  # noqa: E402

EVAL = ROOT / "eval"
ARMS = ("story", "deepwiki")
SEED = 20261006  # the decision date; fixed before any result (§5.1.2)
IN_SAMPLE = {"itsdangerous"}  # §3: used to build the pipeline; reported, never decisive


def repos() -> dict[str, dict]:
    """name -> {url, commit} from demo-repos.lock: the story arm's pins."""
    out = {}
    for line in (ROOT / "demo-repos.lock").read_text().splitlines():
        if line and not line.startswith("#"):
            name, url, commit = line.split()
            out[name] = {"url": url.removesuffix(".git"), "commit": commit, "github": url.split("github.com/")[1].removesuffix(".git")}
    return out


def story_dir(name: str) -> Path:
    return ROOT / "stories" / ("itsdangerous-close-third" if name == "itsdangerous" else f"bench/{name}")


def story_text(name: str) -> str:
    """The story as a reader gets it: all chapters in order, proofs left out (they live in proofs/)."""
    return "\n\n".join(p.read_text() for p in sorted(story_dir(name).glob("[0-9][0-9]-*.md")))


def deepwiki_text(name: str) -> str:
    return (EVAL / "deepwiki" / name / "contents.md").read_text()


def arm_text(name: str, arm: str) -> str:
    return story_text(name) if arm == "story" else deepwiki_text(name)


def arm_commit(name: str, arm: str) -> str:
    """§4: each arm is judged against the commit it documents."""
    if arm == "story":
        return json.loads((story_dir(name) / "outline.json").read_text())["repo"]["commit"]
    return json.loads((EVAL / "deepwiki" / name / "meta.json").read_text())["commit"]


def arm_tree(name: str, arm: str) -> Path:
    """A checkout at the arm's commit. Stories: demo-repos/<name> (pinned there); DeepWiki: eval/checkouts/<name>."""
    return ROOT / "demo-repos" / name if arm == "story" else EVAL / "checkouts" / name


def words(text: str) -> int:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)  # code blocks aren't prose
    return len(text.split())


def client():
    """A client that waits: extraction over a 60k-word page runs for many minutes, and nine run at once."""
    import anthropic

    return anthropic.Anthropic(timeout=3600, max_retries=3)


def ask(client, system: str, content, schema: dict | None = None, max_tokens: int = 32000, tools=None, messages=None):
    """One model turn, with the settings the preregistration names (§6). Returns the response."""
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system, thinking={"type": "adaptive"},
                  betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                  messages=messages or [{"role": "user", "content": content}])
    kwargs["output_config"] = {"effort": "high", **({"format": {"type": "json_schema", "schema": schema}} if schema else {})}
    if tools:
        kwargs["tools"] = tools
    with client.beta.messages.stream(**kwargs) as stream:
        return stream.get_final_message()


def text_of(response) -> str:
    return next(b.text for b in response.content if b.type == "text")


def save_trace(folder: Path, name: str, response) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(response.to_json())


def usage_cost(u) -> float:
    return (u.input_tokens * 5 + (u.cache_creation_input_tokens or 0) * 6.25 + (u.cache_read_input_tokens or 0) * 0.5
            + u.output_tokens * 25) / 1e6
