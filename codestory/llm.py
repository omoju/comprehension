"""One way to ask a model, whichever way you sign in.

Pick a provider with CODESTORY_PROVIDER (in .env or the environment) and, optionally, a model with CODESTORY_MODEL:

  anthropic   ANTHROPIC_API_KEY                  Claude on the Anthropic API: prompt caching, adaptive thinking,
                                                 server-side fallback. The default when ANTHROPIC_API_KEY is set.
  claude-cli  your Claude login                  `claude -p`, the Claude Code CLI, signed in with your claude.ai
                                                 account (run `claude` once to log in). The default otherwise.
  codex-cli   your ChatGPT login                 `codex exec`, the Codex CLI, signed in with your ChatGPT account
                                                 (`codex login`). CODEX_BIN if it is not on the PATH; the copy the
                                                 VS Code ChatGPT extension ships is found on its own.
  foundry     FOUNDRY_ENDPOINT                   a deployment on Azure AI Foundry, named by CODESTORY_MODEL. OpenAI
              + FOUNDRY_API_KEY                  models go through the Responses API; claude-* deployments through
              (or your `az login`)               Foundry's Anthropic Messages API. Without a key, an Entra token from
                                                 the Azure CLI is used.

The CLIs sign in for us. Their own login, token refresh and terms apply, and nothing here reads their credentials.

    ask(system, messages, schema=None) -> Reply

`messages` are Anthropic-style turns ({"role", "content": str | [{"type": "text", "text", "cache_control"?}]});
with a JSON `schema` the reply's text is a JSON document that matches it. Standard library only, except the
anthropic provider, which needs the `anthropic` package.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import env  # noqa: F401  (loads .env)

DEFAULT_MODELS = {"anthropic": "claude-opus-5-5", "claude-cli": "claude-opus-5-5"}  # Codex picks its own; Foundry
# needs a deployment. Claude Opus 5.5 needs Claude Code 2.1.280 or later for claude-cli (`claude update`).
CLAUDE_MODELS = [("claude-opus-5-5", "Claude Opus 5.5"), ("claude-sonnet-5-5", "Claude Sonnet 5.5"),
                 ("claude-fable-5-1", "Claude Fable 5.1"), ("claude-opus-4-8", "Claude Opus 4.8")]
NOT_CHAT = ("transcribe", "tts", "whisper", "image", "embedding", "dall", "flux", "sora", "realtime", "audio")
ANTHROPIC_PRICES = {"input": 5, "cache_write": 6.25, "cache_read": 0.5, "output": 25}  # $/M tokens, Opus
TIMEOUT = 1800  # seconds for one answer; a chapter at high effort can take minutes


class LLMError(RuntimeError):
    pass


@dataclass
class Reply:
    text: str  # the answer; a JSON document when a schema was given
    model: str
    provider: str
    usage: dict = field(default_factory=dict)  # input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens
    cost: float | None = None  # dollars, when known; a CLI on a subscription reports what the API would have charged
    raw: dict = field(default_factory=dict)  # the provider's own response, for traces/

    def record(self) -> dict:
        """What a stage keeps in traces/: enough to resume (usage, cost) and to audit (the raw response)."""
        return {"provider": self.provider, "model": self.model, "usage": self.usage, "cost": self.cost,
                "text": self.text, "raw": self.raw}


def provider() -> str:
    chosen = os.environ.get("CODESTORY_PROVIDER", "").strip()
    if chosen:
        if chosen not in PROVIDERS:
            raise LLMError(f"CODESTORY_PROVIDER={chosen!r}; choose one of {', '.join(PROVIDERS)}")
        return chosen
    return "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "claude-cli"


def model_name(which: str) -> str | None:
    return os.environ.get("CODESTORY_MODEL", "").strip() or DEFAULT_MODELS.get(which)


def ask(system: str, messages: list[dict], schema: dict | None = None, max_tokens: int = 32000,
        effort: str = "high") -> Reply:
    which = provider()
    reply = PROVIDERS[which](system, messages, schema, max_tokens, effort, model_name(which))
    if schema is not None:
        try:
            json.loads(reply.text)
        except json.JSONDecodeError as e:
            raise LLMError(f"{which}: the answer is not the JSON the schema asks for ({e}): {reply.text[:300]}")
    return reply


def models(which: str | None = None) -> list[dict]:
    """The models a provider offers, for a picker: [{"id", "name"}]. Codex's come from its own cache; Foundry's
    from the deployments on the endpoint (an empty list when they can't be read: type the name)."""
    which = which or provider()
    if which in ("anthropic", "claude-cli"):
        return [{"id": i, "name": n} for i, n in CLAUDE_MODELS]
    if which == "codex-cli":
        try:
            cache = json.loads((Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "models_cache.json").read_text())
            return [{"id": m["slug"], "name": m.get("display_name") or m["slug"]} for m in cache.get("models", [])
                    if m.get("visibility") == "list"]
        except (OSError, json.JSONDecodeError, KeyError):
            return []
    if which == "foundry":
        try:
            req = urllib.request.Request(f"{foundry_endpoint()}/openai/deployments?api-version=2022-12-01",
                                         headers=foundry_auth())
            with urllib.request.urlopen(req, timeout=30) as r:
                found = json.loads(r.read()).get("data", [])
        except (LLMError, urllib.error.URLError, json.JSONDecodeError, OSError):
            return []
        names = sorted({d.get("id") for d in found if d.get("id")} - {None})
        return [{"id": n, "name": n} for n in names if not any(x in n.lower() for x in NOT_CHAT)]
    return []


def describe() -> str:
    which = provider()
    return f"{which} ({model_name(which) or 'its default model'})"


# ---------------------------------------------------------------- shared helpers

def text_of(content) -> str:
    return content if isinstance(content, str) else "\n\n".join(b["text"] for b in content if b.get("type") == "text")


def transcript(messages: list[dict]) -> str:
    """A conversation as one prompt, for the providers that take one: a single turn is sent as it is; a repair
    conversation is laid out turn by turn, ending on the turn to answer."""
    if len(messages) == 1:
        return text_of(messages[0]["content"])
    turns = "\n\n".join(f"<{m['role']}>\n{text_of(m['content'])}\n</{m['role']}>" for m in messages)
    return (f"<conversation>\n{turns}\n</conversation>\n\nThe conversation above is between you (assistant) and "
            "the user. Write the assistant's next turn: answer the user's last message, in the format it asks for.")


def schema_instruction(schema: dict) -> str:
    return ("\n\nRespond with a single JSON document, and nothing else, that matches this JSON Schema:\n"
            + json.dumps(schema))


def strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    return t.strip()


def post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code} from {url.split('?')[0]}: {e.read().decode(errors='replace')[:800]}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"cannot reach {url.split('?')[0]}: {e.reason}") from e


def run(argv: list[str], stdin: str, env_drop: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    child_env = {k: v for k, v in os.environ.items() if k not in env_drop}
    try:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=TIMEOUT, env=child_env)
    except FileNotFoundError as e:
        raise LLMError(f"{argv[0]} is not installed or not on the PATH") from e
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"{Path(argv[0]).name} gave no answer within {TIMEOUT}s") from e


# ---------------------------------------------------------------- anthropic: the API, with an API key

def anthropic_api(system, messages, schema, max_tokens, effort, model) -> Reply:
    try:
        import anthropic
    except ImportError as e:
        raise LLMError("the anthropic provider needs the anthropic package: uv pip install -r requirements.txt") from e
    client = anthropic.Anthropic()
    output_config = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    with client.beta.messages.stream(
        model=model, max_tokens=max_tokens, system=system, messages=messages,
        thinking={"type": "adaptive"}, output_config=output_config,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    ) as stream:
        response = stream.get_final_message()
    if response.stop_reason != "end_turn":
        raise LLMError(f"model stopped early: {response.stop_reason}")
    u = response.usage
    usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
             "cache_read_input_tokens": u.cache_read_input_tokens or 0,
             "cache_creation_input_tokens": u.cache_creation_input_tokens or 0}
    p = ANTHROPIC_PRICES
    cost = (usage["input_tokens"] * p["input"] + usage["cache_creation_input_tokens"] * p["cache_write"]
            + usage["cache_read_input_tokens"] * p["cache_read"] + usage["output_tokens"] * p["output"]) / 1e6
    text = next(b.text for b in response.content if b.type == "text").strip()
    return Reply(text, response.model, "anthropic", usage, cost, json.loads(response.to_json()))


# ---------------------------------------------------------------- claude-cli: your Claude login

def claude_cli(system, messages, schema, max_tokens, effort, model) -> Reply:
    with tempfile.TemporaryDirectory() as tmp:
        prompt_file = Path(tmp) / "system.md"
        prompt_file.write_text(system)
        argv = [os.environ.get("CLAUDE_BIN", "claude"), "-p", "--system-prompt-file", str(prompt_file),
                "--tools", "", "--output-format", "json", "--no-session-persistence", "--strict-mcp-config",
                "--setting-sources", "", "--effort", effort]
        if model:
            argv += ["--model", model]
        if schema is not None:
            argv += ["--json-schema", json.dumps(schema)]
        # Nested inside a Claude Code session, the CLI must not think it is that session.
        done = run(argv, transcript(messages), env_drop=("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"))
    try:
        out = json.loads(done.stdout)
    except json.JSONDecodeError:
        raise LLMError(f"claude -p failed (exit {done.returncode}): {(done.stderr or done.stdout)[-800:]}")
    if out.get("is_error") or out.get("subtype") != "success":
        raise LLMError(f"claude -p: {out.get('subtype')}: {str(out.get('result'))[:800]}")
    text = json.dumps(out["structured_output"]) if schema is not None and "structured_output" in out \
        else strip_fence(out.get("result", "")) if schema is not None else out.get("result", "").strip()
    u = out.get("usage", {})
    usage = {k: u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                       "cache_creation_input_tokens")}
    models = [m for m in out.get("modelUsage", {}) if not m.startswith("claude-haiku")]  # haiku names the session
    return Reply(text, models[0] if models else (model or "claude"), "claude-cli", usage, out.get("total_cost_usd"), out)


# ---------------------------------------------------------------- codex-cli: your ChatGPT login

def codex_bin() -> str:
    found = os.environ.get("CODEX_BIN") or shutil.which("codex")
    if found:
        return found
    bundled = sorted(glob.glob(os.path.expanduser("~/.vscode-server/extensions/openai.chatgpt-*/bin/*/codex"))
                     + glob.glob(os.path.expanduser("~/.vscode/extensions/openai.chatgpt-*/bin/*/codex")))
    if bundled:
        return bundled[-1]
    raise LLMError("no codex CLI found: install it (npm i -g @openai/codex) or set CODEX_BIN")


def codex_cli(system, messages, schema, max_tokens, effort, model) -> Reply:
    with tempfile.TemporaryDirectory() as tmp:
        last = Path(tmp) / "answer.txt"
        work = Path(tmp) / "empty"  # nothing to explore: the answer comes from the prompt alone
        work.mkdir()
        argv = [codex_bin(), "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                "--sandbox", "read-only", "-C", str(work), "-o", str(last), "--json",
                "-c", f'model_reasoning_effort="{effort}"']
        if model:
            argv += ["-m", model]
        if schema is not None:
            (Path(tmp) / "schema.json").write_text(json.dumps(schema))
            argv += ["--output-schema", str(Path(tmp) / "schema.json")]
        prompt = (f"<instructions>\n{system}\n</instructions>\n\nDo not run commands or read files: everything you "
                  f"need is in this message.\n\n{transcript(messages)}")
        done = run(argv + ["-"], prompt)
        answer = last.read_text() if last.exists() else ""
    events = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
    failed = [e for e in events if e.get("type") in ("error", "turn.failed")]
    if done.returncode != 0 or failed or not answer.strip():
        detail = json.dumps(failed[-1]) if failed else (done.stderr or done.stdout)[-800:]
        raise LLMError(f"codex exec failed (exit {done.returncode}): {detail[:800]}")
    u = next((e["usage"] for e in reversed(events) if e.get("type") == "turn.completed"), {})
    usage = {"input_tokens": u.get("input_tokens", 0) - u.get("cached_input_tokens", 0),
             "output_tokens": u.get("output_tokens", 0), "cache_read_input_tokens": u.get("cached_input_tokens", 0),
             "cache_creation_input_tokens": u.get("cache_write_input_tokens", 0)}
    text = strip_fence(answer) if schema is not None else answer.strip()
    return Reply(text, model or "codex default", "codex-cli", usage, None, {"events": events})


# ---------------------------------------------------------------- foundry: Azure AI Foundry, key or az login

_token: dict = {}


def foundry_auth() -> dict:
    key = os.environ.get("FOUNDRY_API_KEY", "").strip()
    if key:
        return {"api-key": key}
    if _token.get("expires", 0) < time.time() + 300:
        az = shutil.which("az")
        if not az:
            raise LLMError("foundry: set FOUNDRY_API_KEY, or install the Azure CLI and `az login`")
        done = subprocess.run([az, "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com",
                               "-o", "json"], capture_output=True, text=True, timeout=120)
        if done.returncode != 0:
            raise LLMError(f"foundry: no FOUNDRY_API_KEY and `az account get-access-token` failed: {done.stderr[-400:]}")
        tok = json.loads(done.stdout)
        _token.update(value=tok["accessToken"], expires=float(tok.get("expires_on") or time.time() + 3000))
    return {"authorization": f"Bearer {_token['value']}"}


def foundry_endpoint() -> str:
    endpoint = os.environ.get("FOUNDRY_ENDPOINT", "").strip().rstrip("/")
    if not endpoint:
        raise LLMError("foundry: set FOUNDRY_ENDPOINT, e.g. https://<resource>.openai.azure.com")
    return endpoint.removesuffix("/openai/v1").removesuffix("/openai").removesuffix("/anthropic")


def foundry(system, messages, schema, max_tokens, effort, model) -> Reply:
    if not model:
        raise LLMError("foundry: set CODESTORY_MODEL to the name of your deployment")
    if model.startswith("claude"):
        return foundry_claude(system, messages, schema, max_tokens, effort, model)
    body = {"model": model, "instructions": system, "max_output_tokens": max_tokens, "store": False,
            "reasoning": {"effort": effort},
            "input": [{"role": m["role"], "content": [{"type": "input_text" if m["role"] == "user" else "output_text",
                                                       "text": text_of(m["content"])}]} for m in messages]}
    if schema is not None:
        body["text"] = {"format": {"type": "json_schema", "name": "answer", "schema": schema, "strict": True}}
    url = f"{foundry_endpoint()}/openai/v1/responses?api-version=preview"
    try:
        out = post(url, body, foundry_auth())
    except LLMError as e:
        if "reasoning" not in str(e):
            raise
        body.pop("reasoning")  # a deployment without reasoning controls
        out = post(url, body, foundry_auth())
    if out.get("status") not in (None, "completed"):
        raise LLMError(f"foundry {model}: response {out.get('status')}: {json.dumps(out.get('incomplete_details'))}")
    text = "".join(c.get("text", "") for item in out.get("output", []) if item.get("type") == "message"
                   for c in item.get("content", []) if c.get("type") == "output_text").strip()
    u = out.get("usage", {})
    cached = (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
    usage = {"input_tokens": u.get("input_tokens", 0) - cached, "output_tokens": u.get("output_tokens", 0),
             "cache_read_input_tokens": cached, "cache_creation_input_tokens": 0}
    return Reply(text, out.get("model", model), "foundry", usage, None, out)


def foundry_claude(system, messages, schema, max_tokens, effort, model) -> Reply:
    """Claude deployed on Foundry, through its Anthropic Messages API. Structured output is asked for in the
    prompt and checked by the caller, since Foundry's surface may not take output_config."""
    body = {"model": model, "max_tokens": max_tokens, "system": system + (schema_instruction(schema) if schema else ""),
            "messages": messages, "thinking": {"type": "adaptive"}}
    out = post(f"{foundry_endpoint()}/anthropic/v1/messages", body,
               {**foundry_auth(), "anthropic-version": "2023-06-01"})
    if out.get("stop_reason") not in ("end_turn", None):
        raise LLMError(f"foundry {model}: stopped early: {out.get('stop_reason')}")
    text = "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text").strip()
    u = out.get("usage", {})
    usage = {k: u.get(k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                            "cache_creation_input_tokens")}
    return Reply(strip_fence(text) if schema else text, out.get("model", model), "foundry", usage, None, out)


PROVIDERS = {"anthropic": anthropic_api, "claude-cli": claude_cli, "codex-cli": codex_cli, "foundry": foundry}


if __name__ == "__main__":  # smoke test: python codestory/llm.py
    schema = {"type": "object", "properties": {"word": {"type": "string"}}, "required": ["word"],
              "additionalProperties": False}
    r = ask("You answer in the requested format.", [{"role": "user", "content": 'The JSON object for the word "ok".'}],
            schema=schema, max_tokens=2000, effort="low")
    print(f"{r.provider} · {r.model} · {r.text} · usage {r.usage} · cost {r.cost}")
