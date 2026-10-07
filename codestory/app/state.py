"""Where the review app keeps things, and how it reads and writes them.

Everything lives under CODESTORY_HOME (default ~/.codestory), outside this repository, so a story about a private
repository can never be committed here by accident:

    config.json        provider and model, Foundry endpoint, GitHub sign-in method, registered local checkouts
    secrets.json       API keys and a GitHub token, when you give them (mode 600)
    stories/<id>/      one story per pull request: review.py's output, plus app.json (notes, chat, drafted comments)
    repos/<owner>/<name>/   repositories the app cloned for you

Standard library only. Writes are atomic (write, then rename), so a crash never leaves half a file.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

HOME = Path(os.environ.get("CODESTORY_HOME", Path.home() / ".codestory")).expanduser()
STORIES = HOME / "stories"
REPOS = HOME / "repos"
CONFIG = HOME / "config.json"
SECRETS = HOME / "secrets.json"
_lock = threading.RLock()

DEFAULT_CONFIG = {"provider": "", "models": {}, "foundry_endpoint": "", "github": {"method": "gh", "client_id": ""},
                  "repos": {}}  # models: the model chosen for each provider, remembered when you switch


def setup() -> None:
    for d in (HOME, STORIES, REPOS):
        d.mkdir(parents=True, exist_ok=True)
    os.chmod(HOME, 0o700)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return json.loads(json.dumps(default))  # a fresh copy


def write_json(path: Path, value, private: bool = False) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, indent=1)
            f.write("\n")
        if private:
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)


def config() -> dict:
    return {**DEFAULT_CONFIG, **read_json(CONFIG, DEFAULT_CONFIG)}


def save_config(cfg: dict) -> None:
    write_json(CONFIG, cfg)


def chosen_model(cfg: dict) -> str:
    """The model chosen for the chosen provider ("" for the provider's default)."""
    return (cfg.get("models") or {}).get(cfg.get("provider") or "", "") or cfg.get("model", "")


def secrets() -> dict:
    return read_json(SECRETS, {})


def save_secrets(values: dict) -> None:
    write_json(SECRETS, values, private=True)


def apply_model_settings() -> None:
    """Put the chosen provider, model and keys where llm.py reads them (this process and the jobs it starts)."""
    cfg, sec = config(), secrets()
    pairs = {"CODESTORY_PROVIDER": cfg.get("provider"), "CODESTORY_MODEL": chosen_model(cfg),
             "FOUNDRY_ENDPOINT": cfg.get("foundry_endpoint"), "ANTHROPIC_API_KEY": sec.get("anthropic_api_key"),
             "FOUNDRY_API_KEY": sec.get("foundry_api_key")}
    for key, value in pairs.items():
        if value:
            os.environ[key] = value
        elif key in ("CODESTORY_PROVIDER", "CODESTORY_MODEL"):
            os.environ.pop(key, None)  # cleared in the app: fall back to llm.py's default


# ---------------------------------------------------------------- stories

def story_id(owner: str, name: str, number: int) -> str:
    return f"{owner}__{name}__pr{number}"


def repo_story_id(target: dict) -> str:
    if target.get("path"):
        name = re.sub(r"[^\w.-]+", "-", Path(target["path"]).name)
        return f"local__{name}__repo"
    return f"{target['owner']}__{target['name']}__repo"


def story_dir(sid: str) -> Path:
    if not re.fullmatch(r"[\w.-]+", sid):
        raise ValueError(f"not a story id: {sid!r}")
    return STORIES / sid


def app_state(sid: str) -> dict:
    """The review around a story: the pull request, the notes, the chat, the drafted comments, what was posted."""
    return read_json(story_dir(sid) / "app.json", {"pr": {}, "notes": [], "chat": {"turns": [], "session": None},
                                                  "draft": None, "posted": []})


def save_app_state(sid: str, value: dict) -> None:
    write_json(story_dir(sid) / "app.json", value)


def list_stories() -> list[dict]:
    out = []
    for d in sorted(STORIES.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True) if STORIES.exists() else []:
        if not d.is_dir():
            continue
        st = read_json(d / "app.json", {})
        outline = read_json(d / "outline.json", {})
        premise = outline.get("premise", "")
        out.append({"id": d.name, "kind": "repo" if st.get("repo") else "pr", "pr": st.get("pr", {}),
                    "repo": st.get("repo", {}),
                    "title": outline.get("title") or st.get("pr", {}).get("title") or d.name,
                    "premise": re.split(r"(?<=[.!?])\s", premise, maxsplit=1)[0] if premise else "",
                    "ready": (d / "index.html").exists(), "updated": d.stat().st_mtime,
                    "notes": len(st.get("notes", [])), "posted": len(st.get("posted", []))})
    return out


def now() -> float:
    return round(time.time(), 3)
