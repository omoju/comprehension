"""The reviewer's assistant: questions about a story, answered from the story and the code on both sides.

With a CLI provider the assistant is that CLI's own agent, read-only: Claude Code with Read, Grep and Glob over the
story and the two checkouts (base and head), or Codex in its read-only sandbox. The conversation is resumed turn by
turn. With an API provider it is a conversation with the story in its context and no tools.

The checkouts the assistant reads are plain worktrees with nothing linked into them (no node_modules, no .env), so a
secret the tests need can't end up in an answer, or in a comment on the pull request.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import state

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm  # noqa: E402
from diff import ROOT, repo_dir, worktree  # noqa: E402

SYSTEM = """You help a reviewer understand one pull request, through the code story written about it. The story
follows the change's own tests, run before the change (the base) and after it (the head). The reviewer reads the
story, asks you questions, and writes notes that will become review comments.

Answer from evidence. Read the story's files and the code, on the side the question is about, before you answer; cite
file and line ("src/utils.ts:318 on the head"). Say when the runs don't show something: a test that doesn't reach a
function says nothing about it. Be direct and brief: a few sentences, or a short list. You can't change files.

When the reviewer says what they think of the change, help them make it precise (which line, what exactly is wrong,
what would fix it), but don't put opinions in their mouth: the comments will be in their voice.

Where things are:
{places}

The story so far:
{story}"""

AGENT_TOOLS = "Read,Grep,Glob"


def story_brief(sid: str) -> str:
    """The story in a few thousand words: the pull request, the plan, the tests, the notes."""
    d = state.story_dir(sid)
    st = state.app_state(sid)
    pr = st.get("pr", {})
    outline = state.read_json(d / "outline.json", {})
    summary = state.read_json(d / "diff.json", {})
    if st.get("repo"):
        info = outline.get("repo", {})
        lines = [f"Repository: {info.get('name') or st['repo'].get('path')} at {info.get('commit', '')[:7]}, "
                 f"told for the {outline.get('reader') or st['repo'].get('reader', 'owner')}"]
    else:
        lines = [f"Pull request: {pr.get('owner')}/{pr.get('name')}#{pr.get('number')} · {pr.get('title', '')}",
                 f"Author: {pr.get('author', '?')} · base {pr.get('base', {}).get('sha', '')[:7]} → head "
                 f"{pr.get('head', {}).get('sha', '')[:7]}"]
    if pr.get("body"):
        lines.append("Description:\n" + pr["body"][:3000])
    if outline:
        lines += [f"Story: {outline['title']}", f"Premise: {outline['premise']}", f"Verdict: {outline.get('verdict', '')}"]
        for c in outline.get("chapters", []):
            lines.append(f"  Chapter {c['n']} ({c.get('kind', '')}): {c['title']} — before: {c.get('before', '')} "
                         f"| after: {c.get('after', '')}")
        for u in outline.get("unexercised", []):
            lines.append(f"  Not reached by any test: {u['function']} — {u['check']}")
    for t in summary.get("tests", []):
        lines.append(f"  Test: {t['test']} (before: {t['before']}, after: {t['after']})")
    for n in st.get("notes", []):
        where = f" [{n['anchor']['path']}:{n['anchor']['start']} on the {n['anchor']['side']}]" if n.get("anchor") else ""
        lines.append(f"  Reviewer's note {n['id']}{where}: {n['text']}")
    return "\n".join(lines)


def checkouts(sid: str) -> dict[str, Path]:
    """Plain worktrees (nothing linked in) for the assistant to read: the base and the head of a change, or the
    repository at the story's commit."""
    setup = state.read_json(state.story_dir(sid) / "changes.json", {})
    if not setup:
        outline = state.read_json(state.story_dir(sid) / "outline.json", {})
        info = outline.get("repo", {})
        if not info.get("commit"):
            return {}
        repo = (ROOT / info["local_path"]).resolve()
        name = re.sub(r"[^\w.-]+", "-", repo.name)
        return {"repository": worktree(repo, info["commit"], ROOT / "demo-repos" / ".worktrees" / f"{name}-{info['commit'][:10]}")}
    repo = repo_dir(setup)
    out = {}
    for side in ("base", "head"):
        out[side] = worktree(repo, setup[side], ROOT / "demo-repos" / ".worktrees" / f"{repo.name}-{setup[side][:10]}")
    return out


def places(sid: str, trees: dict[str, Path]) -> str:
    d = state.story_dir(sid)
    rows = [f"- The story: {d} (chapters NN-*.md; outline.json the plan; diff.txt the two runs merged, `+` only after, "
            "`-` only before, `~` other values; diff.json each test before and after; report.md the checks; "
            "trace.base.json and trace.head.json every call with its arguments and result; proofs/ each chapter's proof)"]
    for side, path in trees.items():
        rows.append(f"- The code at the story's commit: {path}" if side == "repository" else f"- The code on the {side}: {path}")
    return "\n".join(rows)


def ask(sid: str, message: str, on_event: Callable[[dict], None]) -> str:
    """One turn of the conversation. Streams {"type": "tool"|"text"} events; returns the answer, saves the turn."""
    state.apply_model_settings()
    which = llm.provider()
    st = state.app_state(sid)
    chat = st.setdefault("chat", {"turns": [], "session": None})
    if chat.get("provider") not in (None, which):
        chat["session"] = None  # a session belongs to the provider that started it
    trees = checkouts(sid) if which in ("claude-cli", "codex-cli") else {}
    system = SYSTEM.format(places=places(sid, trees), story=story_brief(sid))
    if which == "claude-cli":
        answer, session = _claude(sid, system, message, chat.get("session"), trees, on_event)
    elif which == "codex-cli":
        answer, session = _codex(sid, system, message, chat.get("session"), on_event)
    else:
        history = [{"role": t["role"], "content": t["text"]} for t in chat["turns"][-20:]]
        reply = llm.ask(system, history + [{"role": "user", "content": message}], max_tokens=8000, effort="medium")
        answer, session = reply.text, None
        on_event({"type": "text", "text": answer})
    chat["turns"] += [{"role": "user", "text": message, "at": state.now()},
                      {"role": "assistant", "text": answer, "at": state.now()}]
    chat["session"], chat["provider"] = session, which
    st = {**state.app_state(sid), "chat": chat}  # notes may have changed meanwhile
    state.save_app_state(sid, st)
    return answer


def _claude(sid, system, message, session, trees, on_event) -> tuple[str, str | None]:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(system)
    argv = [os.environ.get("CLAUDE_BIN", "claude"), "-p", "--output-format", "stream-json", "--verbose",
            "--tools", AGENT_TOOLS, "--allowedTools", AGENT_TOOLS, "--setting-sources", "", "--strict-mcp-config",
            "--system-prompt-file", f.name]
    for path in trees.values():
        argv += ["--add-dir", str(path)]
    argv += ["--model", llm.model_name("claude-cli")]  # Claude Opus 5.5 unless another model is chosen
    if session:
        argv += ["--resume", session]
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    proc = subprocess.Popen(argv, cwd=state.story_dir(sid), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)
    proc.stdin.write(message)
    proc.stdin.close()
    answer, sid_out, texts = "", session, []
    for line in proc.stdout:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "system" and e.get("session_id"):
            sid_out = e["session_id"]
        elif e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "tool_use":
                    on_event({"type": "tool", "name": b["name"], "detail": tool_detail(b.get("input", {}))})
                elif b.get("type") == "text" and b["text"].strip():
                    texts.append(b["text"])
                    on_event({"type": "text", "text": b["text"]})
        elif e.get("type") == "result":
            answer = e.get("result") or "\n\n".join(texts)
            if e.get("is_error"):
                answer = f"(the assistant failed: {answer})"
    proc.wait()
    os.unlink(f.name)
    if not answer:
        answer = "(no answer: " + (proc.stderr.read().strip()[-400:] or f"claude exited {proc.returncode}") + ")"
    return answer, sid_out


def _codex(sid, system, message, session, on_event) -> tuple[str, str | None]:
    base = [llm.codex_bin(), "exec"]
    if session:
        argv = base + ["resume", session, "--json", "--skip-git-repo-check", "-"]
        prompt = message
    else:
        argv = base + ["--json", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(state.story_dir(sid)),
                       "-c", 'model_reasoning_effort="medium"', "-"]
        prompt = f"<instructions>\n{system}\n</instructions>\n\n{message}"
    if os.environ.get("CODESTORY_MODEL"):
        argv[2:2] = ["-m", os.environ["CODESTORY_MODEL"]]
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(prompt)
    proc.stdin.close()
    answer, thread = "", session
    for line in proc.stdout:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "thread.started":
            thread = e.get("thread_id") or thread
        item = e.get("item") or {}
        if e.get("type") == "item.completed" and item.get("type") == "command_execution":
            on_event({"type": "tool", "name": "shell", "detail": str(item.get("command", ""))[:120]})
        elif e.get("type") == "item.completed" and item.get("type") == "agent_message":
            answer = item.get("text", "")
            on_event({"type": "text", "text": answer})
    proc.wait()
    if not answer:
        answer = "(no answer: " + (proc.stderr.read().strip()[-400:] or f"codex exited {proc.returncode}") + ")"
    return answer, thread


def tool_detail(inp: dict) -> str:
    for key in ("file_path", "pattern", "path", "query"):
        if inp.get(key):
            return str(inp[key])[:120]
    return json.dumps(inp)[:120]
