"""The model providers, as the review app shows them: is each one ready, and how to make it ready.

The app never signs in to a model provider for you. The CLIs keep their own login (`claude auth login`,
`codex login`, `az login`); keys you type are kept in secrets.json. This module only asks each one where it stands.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import state

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm  # noqa: E402


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess | None:
    try:
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


_cache: dict = {}
TTL = 60  # seconds: asking three CLIs where they stand takes a few seconds


def status(fresh: bool = False) -> list[dict]:
    """One row per provider: {id, name, ready, detail, how} — `how` says what to do when it isn't ready."""
    if not fresh and _cache.get("at", 0) > time.time() - TTL:
        return _mark(_cache["rows"])
    rows = _status()
    state.apply_model_settings()
    for r in rows:  # what each one offers, for the model picker (Foundry's: the deployments on its endpoint)
        r["models"] = llm.models(r["id"]) if r["ready"] or r["id"] != "foundry" else []
    _cache.update(at=time.time(), rows=rows)
    return _mark(rows)


def _mark(rows: list[dict]) -> list[dict]:
    cfg = state.config()
    chosen = cfg.get("provider") or llm.provider()
    picked = cfg.get("models") or {}
    return [{**r, "chosen": r["id"] == chosen,
             "model": picked.get(r["id"]) or llm.DEFAULT_MODELS.get(r["id"], "")} for r in rows]


def _status() -> list[dict]:
    cfg, sec = state.config(), state.secrets()
    rows = []

    claude = shutil.which(os.environ.get("CLAUDE_BIN", "claude"))
    done = _run([claude, "auth", "status"]) if claude else None
    who = None
    if done and done.returncode == 0:
        try:
            info = json.loads(done.stdout)
            who = info.get("email") if info.get("loggedIn") else None
        except json.JSONDecodeError:
            who = None
    rows.append({"id": "claude-cli", "name": "Claude (your login)", "agent": True, "ready": bool(who),
                 "detail": f"signed in as {who}" if who else ("not signed in" if claude else "Claude Code CLI not installed"),
                 "how": "Run `claude auth login` in a terminal." if claude else "Install Claude Code, then run `claude auth login`."})

    try:
        codex = llm.codex_bin()
    except llm.LLMError:
        codex = None
    done = _run([codex, "login", "status"]) if codex else None
    line = (done.stdout or done.stderr).strip().splitlines()[0] if done and (done.stdout or done.stderr).strip() else ""
    ok = bool(done and done.returncode == 0 and "logged in" in line.lower())
    rows.append({"id": "codex-cli", "name": "ChatGPT (your login)", "agent": True, "ready": ok,
                 "detail": line or ("not signed in" if codex else "Codex CLI not found"),
                 "how": "Run `codex login` in a terminal." if codex else "Install the Codex CLI, then run `codex login`."})

    endpoint, key = cfg.get("foundry_endpoint"), sec.get("foundry_api_key")
    az_user = None
    if endpoint and not key and shutil.which("az"):
        done = _run(["az", "account", "show", "--query", "user.name", "-o", "tsv"], timeout=60)
        az_user = done.stdout.strip() if done and done.returncode == 0 else None
    ready = bool(endpoint and (key or az_user) and cfg.get("model"))
    rows.append({"id": "foundry", "name": "Azure AI Foundry", "agent": False, "ready": ready,
                 "detail": (f"{cfg.get('model') or '(no deployment chosen)'} at {endpoint}, "
                            + ("API key" if key else f"az login as {az_user}" if az_user else "not signed in"))
                 if endpoint else "no endpoint set",
                 "how": "Set the endpoint and the deployment name below, then an API key or `az login`."})

    rows.append({"id": "anthropic", "name": "Anthropic API", "agent": False, "ready": bool(sec.get("anthropic_api_key")),
                 "detail": "API key set" if sec.get("anthropic_api_key") else "no API key",
                 "how": "Paste an API key below."})
    return rows


def test() -> dict:
    """A one-line answer from the chosen provider, to prove the whole path works."""
    state.apply_model_settings()
    schema = {"type": "object", "properties": {"word": {"type": "string"}}, "required": ["word"],
              "additionalProperties": False}
    try:
        r = llm.ask("You answer in the requested format.", [{"role": "user", "content": 'The JSON object for "ok".'}],
                    schema=schema, max_tokens=2000, effort="low")
    except llm.LLMError as e:
        return {"ok": False, "detail": str(e)[:500]}
    return {"ok": json.loads(r.text).get("word") == "ok", "detail": f"{r.provider} · {r.model} answered {r.text}"}
