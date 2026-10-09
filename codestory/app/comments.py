"""From the reviewer's notes to a review on the pull request: draft the comments, check them, post them.

The model drafts; code checks what code can decide, as everywhere in codestory. GitHub only accepts a comment on a
line that is part of the pull request's diff, so every comment's file, side and lines are checked against the diff's
hunks, and every note must be used, by a comment or by the summary. A draft that fails goes back to the model with
the errors, in the same conversation, up to REPAIRS times. Opinions come only from the reviewer: the notes and their
side of the conversation. The story and the code supply the facts and the places.

When the pull request has moved on since the story was written, the notes' lines (cited on the story's head) are
carried to the pull request's current head by matching content, and the comments are posted against that head.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import state
from github import GitHub, GitHubError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm  # noqa: E402
from diff import repo_dir  # noqa: E402
from diff_verify import line_map  # noqa: E402

REPAIRS = 2
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

SYSTEM = """You turn a code reviewer's notes into the comments of a GitHub pull request review.

You are given the pull request (its diff, file by file), the code story the reviewer read (what the change does,
with evidence from its tests run before and after), the reviewer's notes, numbered, some pinned to lines, and the
conversation they had with an assistant about the story.

Write in the reviewer's voice: first person, direct, specific and civil. Every opinion must come from the reviewer's
notes or their side of the conversation; never add a concern, a compliment or a request of your own. The story and
the code supply facts and places: use them to make a note precise (name the function, the value, the case), not to
widen it. When the story or the conversation shows that part of a note rests on a wrong premise (a case it worries
about is already handled, say), write the comment from what is true, citing it, rather than repeating the question.

Each note that concerns particular code becomes a comment on the exact lines it concerns. A comment can only sit on
lines that are part of the diff: choose them from the ranges given for that file and side (RIGHT is the head, the
code after the change; LEFT is the base, for removed lines). Use start_line for a range of more than one line, else
null. When a note asks for a specific change you can write exactly, end the comment with a GitHub suggestion block
(```suggestion … ```) holding the replacement for exactly the commented lines; otherwise don't. Notes about the change
as a whole go in the summary. List in each comment's `notes`, and in `summary_notes`, the ids of the notes it carries;
every note must be carried somewhere. Keep the summary short.

The event: REQUEST_CHANGES if any note asks for a change before merging; APPROVE only if the reviewer says they
approve; otherwise COMMENT."""

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "summary_notes": {"type": "array", "items": {"type": "integer"}},
        "event": {"type": "string", "enum": ["COMMENT", "REQUEST_CHANGES", "APPROVE"]},
        "comments": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "side": {"type": "string", "enum": ["RIGHT", "LEFT"]},
                "line": {"type": "integer"},
                "start_line": {"type": ["integer", "null"]},
                "body": {"type": "string"},
                "notes": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["path", "side", "line", "start_line", "body", "notes"],
            "additionalProperties": False,
        }},
    },
    "required": ["summary", "summary_notes", "event", "comments"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- the diff's hunks: where comments can go

def hunks(patch: str | None) -> list[dict]:
    """[{"RIGHT": set(lines), "LEFT": set(lines)}] per hunk of one file's patch."""
    out, old, new = [], 0, 0
    for line in (patch or "").splitlines():
        m = HUNK.match(line)
        if m:
            old, new = int(m[1]), int(m[3])
            out.append({"RIGHT": set(), "LEFT": set()})
            continue
        if not out or line.startswith("\\"):
            continue
        if line.startswith("+"):
            out[-1]["RIGHT"].add(new)
            new += 1
        elif line.startswith("-"):
            out[-1]["LEFT"].add(old)
            old += 1
        else:
            out[-1]["RIGHT"].add(new)
            out[-1]["LEFT"].add(old)
            new += 1
            old += 1
    return out


def ranges(lines: set[int]) -> str:
    runs, start, prev = [], None, None
    for n in sorted(lines):
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            runs.append((start, prev))
            start = prev = n
    if start is not None:
        runs.append((start, prev))
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs)


def check(draft: dict, files: dict[str, list[dict]], note_ids: set[int]) -> list[str]:
    """Everything code can decide about a draft. Empty means GitHub will take it."""
    errors = []
    for i, c in enumerate(draft["comments"], 1):
        where = f"comment {i} ({c['path']}:{c['line']} {c['side']})"
        if c["path"] not in files:
            errors.append(f"{where}: {c['path']} is not a file of this pull request with a diff")
            continue
        hs = files[c["path"]]
        hit = [h for h in hs if c["line"] in h[c["side"]]]
        if not hit:
            errors.append(f"{where}: line {c['line']} is not in the diff on the {c['side']} side; the {c['side']} "
                          f"lines you can use in {c['path']} are {ranges(set().union(*(h[c['side']] for h in hs))) or 'none'}")
        elif c["start_line"] is not None:
            if c["start_line"] >= c["line"]:
                errors.append(f"{where}: start_line {c['start_line']} must come before line {c['line']} (or be null)")
            elif not all(n in hit[0][c["side"]] for n in range(c["start_line"], c["line"] + 1)):
                errors.append(f"{where}: lines {c['start_line']}-{c['line']} are not all in one hunk of the diff")
        if not c["body"].strip():
            errors.append(f"{where}: the comment is empty")
        bad = [n for n in c["notes"] if n not in note_ids]
        if bad:
            errors.append(f"{where}: notes {bad} don't exist")
    used = {n for c in draft["comments"] for n in c["notes"]} | set(draft["summary_notes"])
    errors += [f"note {n} is carried by no comment and not by the summary" for n in sorted(note_ids - used)]
    return errors


# ---------------------------------------------------------------- the notes, at the pull request's current head

def carry(notes: list[dict], sid: str, pr_head: str) -> list[dict]:
    """Notes pinned to lines on the story's head, carried to the pull request's current head by content."""
    setup = state.read_json(state.story_dir(sid) / "changes.json", {})
    story_head = setup.get("head")
    if not story_head or story_head == pr_head:
        return notes
    repo, cache, out = repo_dir(setup), {}, []

    def lines_at(rev, path):
        if (rev, path) not in cache:
            from subprocess import run
            done = run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True, text=True)
            cache[(rev, path)] = done.stdout.splitlines() if done.returncode == 0 else None
        return cache[(rev, path)]

    for n in notes:
        a = n.get("anchor")
        if not a or a["side"] != "head":
            out.append(n)
            continue
        old, new = lines_at(story_head, a["path"]), lines_at(pr_head, a["path"])
        if old is None or new is None:
            out.append({**n, "moved": "the file is gone at the pull request's head"})
            continue
        m = line_map(old, new)
        start, end = m.get(a["start"]), m.get(a["end"])
        if start and end:
            out.append({**n, "anchor": {**a, "start": start, "end": end}})
        else:
            out.append({**n, "anchor": {**a, "changed": True},
                        "moved": "those lines changed in a later push; place the comment by the note's meaning"})
    return out


# ---------------------------------------------------------------- drafting

def context(sid: str, pr: dict, files: list[dict], notes: list[dict], existing: list[dict]) -> str:
    from agent import story_brief
    st = state.app_state(sid)
    turns = st.get("chat", {}).get("turns", [])[-24:]
    parts = [story_brief(sid)]
    parts.append("<notes>\n" + "\n".join(
        f"{n['id']}. {n['text']}"
        + (f"\n   pinned to {n['anchor']['path']} lines {n['anchor']['start']}-{n['anchor']['end']} on the "
           f"{'RIGHT (head)' if n['anchor']['side'] == 'head' else 'LEFT (base)'}" if n.get("anchor") else "")
        + (f"\n   (about chapter {n['chapter']})" if n.get("chapter") else "")
        + (f"\n   quoting: “{n['quote'][:300]}”" if n.get("quote") else "")
        + (f"\n   ({n['moved']})" if n.get("moved") else "")
        for n in notes) + "\n</notes>")
    if turns:
        parts.append("<conversation>\n" + "\n\n".join(f"{t['role']}: {t['text'][:2000]}" for t in turns) + "\n</conversation>")
    if existing:
        parts.append("<existing_comments>\n" + "\n".join(f"- {c['path']}:{c['line']} by {c['author']}: {c['body'][:200]}"
                                                         for c in existing[:40]) + "\n</existing_comments>\n"
                     "Don't repeat what an existing comment already says.")
    diff, used = [], 0
    for f in files:
        if not f["patch"]:
            continue
        hs = hunks(f["patch"])
        right = ranges(set().union(*(h["RIGHT"] for h in hs)))
        left = ranges(set().union(*(h["LEFT"] for h in hs)))
        block = (f'<file path="{f["path"]}" status="{f["status"]}">\nlines you can comment on: RIGHT {right or "none"}; '
                 f'LEFT {left or "none"}\n{f["patch"]}\n</file>')
        if used + len(block) > 300_000:
            diff.append(f'<file path="{f["path"]}">(patch not shown: budget) RIGHT {right}; LEFT {left}</file>')
            continue
        diff.append(block)
        used += len(block)
    parts.append(f"<pull_request_diff head=\"{pr['head']['sha']}\">\n" + "\n".join(diff) + "\n</pull_request_diff>")
    return "\n\n".join(parts)


def draft(sid: str, on_event=lambda e: None) -> dict:
    """Draft the review from the notes; check it; repair it. Saved as app.json's draft."""
    state.apply_model_settings()
    st = state.app_state(sid)
    if not st.get("notes"):
        raise GitHubError("write at least one note first: the comments come from your notes")
    gh = GitHub()
    old = st["pr"]
    pr = gh.pr(old["owner"], old["name"], old["number"])
    on_event({"type": "step", "text": f"reading the pull request's diff at {pr['head']['sha'][:7]}"})
    files = gh.files(pr["owner"], pr["name"], pr["number"])
    by_path = {f["path"]: hunks(f["patch"]) for f in files if f["patch"]}
    notes = carry(st["notes"], sid, pr["head"]["sha"])
    existing = gh.review_comments(pr["owner"], pr["name"], pr["number"])
    messages = [{"role": "user", "content": context(sid, pr, files, notes, existing)
                 + "\n\nDraft the review: the summary, the comments, the event."}]
    errors, result, attempts = [], None, 0
    for attempts in range(REPAIRS + 1):
        on_event({"type": "step", "text": "drafting the comments" if attempts == 0 else
                  f"repairing the draft ({len(errors)} problem{'s' if len(errors) != 1 else ''})"})
        reply = llm.ask(SYSTEM, messages, schema=SCHEMA, max_tokens=16000, effort="medium")
        result = json.loads(reply.text)
        errors = check(result, by_path, {n["id"] for n in notes})
        if not errors:
            break
        messages += [{"role": "assistant", "content": reply.text},
                     {"role": "user", "content": "The draft failed these checks:\n" + "\n".join(f"- {e}" for e in errors)
                      + "\n\nReturn the whole corrected draft. Fix what the checks name; keep the rest as it is."}]
    for c in result["comments"]:
        c["include"] = True
    d = {**result, "errors": errors, "repairs": attempts, "head": pr["head"]["sha"], "drafted": state.now(),
         "moved": pr["head"]["sha"] != state.read_json(state.story_dir(sid) / "changes.json", {}).get("head"),
         "hunks": {p: [{"RIGHT": sorted(h["RIGHT"]), "LEFT": sorted(h["LEFT"])} for h in hs] for p, hs in by_path.items()},
         "patches": {f["path"]: f["patch"] for f in files if f["patch"]}}
    st = {**state.app_state(sid), "pr": {**old, **pr}, "draft": d}
    state.save_app_state(sid, st)
    return d


def recheck(sid: str) -> dict:
    """Check the draft again after the reviewer edited it (moved a line, rewrote a body, dropped a comment)."""
    st = state.app_state(sid)
    d = st["draft"]
    by_path = {p: [{"RIGHT": set(h["RIGHT"]), "LEFT": set(h["LEFT"])} for h in hs] for p, hs in d["hunks"].items()}
    kept = {**d, "comments": [c for c in d["comments"] if c.get("include", True)]}
    notes = {n["id"] for n in st["notes"]}
    d["errors"] = [e for e in check(kept, by_path, notes) if not e.startswith("note ")]  # dropping one is your call
    st["draft"] = d
    state.save_app_state(sid, st)
    return d


def post(sid: str, event: str, pending: bool) -> dict:
    """Post the draft as one review: submitted with `event`, or pending, to finish on GitHub."""
    st = state.app_state(sid)
    d = recheck(sid)
    if d["errors"]:
        raise GitHubError("the draft still has problems: " + "; ".join(d["errors"][:3]))
    pr = st["pr"]
    gh = GitHub()
    now = gh.pr(pr["owner"], pr["name"], pr["number"])
    if now["head"]["sha"] != d["head"]:
        raise GitHubError(f"the pull request moved to {now['head']['sha'][:7]} since the draft; draft again")
    comments = []
    for c in d["comments"]:
        if not c.get("include", True):
            continue
        out = {"path": c["path"], "side": c["side"], "line": c["line"], "body": c["body"]}
        if c.get("start_line"):
            out.update(start_line=c["start_line"], start_side=c["side"])
        comments.append(out)
    payload = {"commit_id": d["head"], "body": d["summary"], "comments": comments}
    if not pending:
        payload["event"] = event
    r = gh.create_review(pr["owner"], pr["name"], pr["number"], payload)
    st = state.app_state(sid)
    st.setdefault("posted", []).append({**r, "event": None if pending else event, "comments": len(comments),
                                        "at": state.now()})
    state.save_app_state(sid, st)
    return r
