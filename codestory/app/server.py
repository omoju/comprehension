"""codestory review: a local web app around review.py.

    .venv/bin/python codestory/app/server.py [--port 8765]

Sign in to GitHub and to a model provider, point at a pull request, read the change story written about it, write
your notes, ask the assistant about the story, then let it draft the review comments, approve them and post them to
the pull request, each on the right lines.

It listens on 127.0.0.1 only. Because it can post to GitHub as you, it guards against other web pages driving it:
the link it prints carries a secret that becomes a SameSite=Strict cookie, every API call needs that cookie and a
custom header (which no cross-site form can send), and the Host header must name this machine (no DNS rebinding).
A story is written by a model from a pull request, which could carry an injection: the app renders its text only
through a sanitizer, under a policy that runs no inline script; a story's own page, opened in a tab, is served
sandboxed (an opaque origin) with no network, so its scripts can't reach this API.
Data lives in ~/.codestory (see state.py). Standard library only.
"""

from __future__ import annotations

import argparse
import http.cookies
import json
import mimetypes
import re
import secrets
import shutil
import sys
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import agent  # noqa: E402
import comments  # noqa: E402
import github  # noqa: E402
import jobs  # noqa: E402
import providers  # noqa: E402
import repos  # noqa: E402
import state  # noqa: E402
from diff import repo_dir  # noqa: E402

STATIC = HERE / "static"
ROOT_DIR = HERE.parent.parent  # the comprehension project: story.py's relative paths start here
APP_CSP = ("default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' "
           "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: "
           "https://avatars.githubusercontent.com; frame-src 'self'; connect-src 'self'; base-uri 'none'; "
           "form-action 'none'; frame-ancestors 'none'")
STORY_CSP = ("sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; "
             "script-src 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'unsafe-inline' https://fonts.googleapis.com; "
             "font-src https://fonts.gstatic.com; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; "
             "frame-ancestors 'self'")  # sandbox: opened in a tab of its own, it still gets an opaque origin
TOKEN = secrets.token_urlsafe(24)
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    server_version = "codestory-review"

    # ------------------------------------------------------------ plumbing

    def log_message(self, fmt, *args):  # quiet: one line per API call
        if self.path.startswith("/api/"):
            sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

    def host_ok(self) -> bool:
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def cookie_ok(self) -> bool:
        c = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return "cs_token" in c and secrets.compare_digest(c["cs_token"].value, TOKEN)

    def send(self, code: int, body: bytes | str, ctype: str = "application/json", extra: dict | None = None):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def json(self, value, code: int = 200):
        self.send(code, json.dumps(value))

    def fail(self, code: int, message: str):
        self.json({"error": message}, code)

    def body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def stream_start(self, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def emit_line(self, value: dict):
        self.wfile.write((json.dumps(value) + "\n").encode())
        self.wfile.flush()

    # ------------------------------------------------------------ routing

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def route(self, method: str):
        if not self.host_ok():
            return self.fail(403, "wrong host")
        url = urllib.parse.urlsplit(self.path)
        path, query = url.path, urllib.parse.parse_qs(url.query)
        if path == "/" and query.get("t") == [TOKEN]:  # the printed link: set the cookie, drop the secret from the URL
            return self.send(303, "", "text/plain", {"Location": "/", "Set-Cookie":
                             f"cs_token={TOKEN}; HttpOnly; SameSite=Strict; Path=/"})
        if not self.cookie_ok():
            return self.send(401, "Open the link codestory review printed when it started.", "text/plain")
        if method == "POST" and self.headers.get("X-Codestory") != "1":
            return self.fail(403, "missing X-Codestory header")
        try:
            if method == "GET" and (path == "/" or path.startswith("/static/")):
                return self.static("index.html" if path == "/" else path[len("/static/"):])
            if method == "GET" and path.startswith("/s/"):
                return self.story_page(path[3:].strip("/"))
            if path.startswith("/api/"):
                return self.api(method, path[5:].strip("/").split("/"))
            self.fail(404, "not found")
        except (github.GitHubError, ValueError, KeyError, FileNotFoundError) as e:
            self.fail(400, str(e))
        except BrokenPipeError:
            pass
        except Exception as e:  # noqa: BLE001 — report it to the page rather than drop the connection
            traceback.print_exc()
            self.fail(500, f"{type(e).__name__}: {e}")

    def static(self, name: str):
        f = (STATIC / name).resolve()
        if not f.is_relative_to(STATIC) or not f.is_file():
            return self.fail(404, "not found")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        self.send(200, f.read_bytes(), ctype, {"Content-Security-Policy": APP_CSP} if ctype == "text/html" else None)

    def story_page(self, sid: str):
        """The story's own reading page (render.py's), for a tab of its own: sandboxed, no network."""
        page = state.story_dir(sid) / "index.html"
        if not page.exists():
            return self.fail(404, "this story has no page yet")
        self.send(200, page.read_text(), "text/html; charset=utf-8", {"Content-Security-Policy": STORY_CSP})

    # ------------------------------------------------------------ the API

    def api(self, method: str, parts: list[str]):
        head = parts[0]
        if head == "session" and method == "GET":
            return self.json(session())
        if head == "github":
            return self.api_github(method, parts[1:])
        if head == "providers":
            return self.api_providers(method, parts[1:])
        if head == "pr" and parts[1:] == ["inspect"]:
            return self.json(inspect(self.body()["url"]))
        if head == "repos" and method == "POST":
            b = self.body()
            if b.get("forget"):
                repos.forget(b["owner"], b["name"])
                return self.json({"ok": True})
            return self.json(repos.register(b["owner"], b["name"], b["path"], b.get("link", ""), b.get("pkg", ""),
                                            b.get("runner", "")))
        if head == "stories":
            return self.api_stories(method, parts[1:])
        self.fail(404, "no such API")

    def api_github(self, method, parts):
        b = self.body() if method == "POST" else {}
        if parts == ["device"] and b.get("action") == "start":
            client_id = b.get("client_id") or state.config()["github"].get("client_id")
            if not client_id:
                raise ValueError("give the client id of your GitHub OAuth App (with Device Flow enabled)")
            cfg = state.config()
            cfg["github"] = {**cfg["github"], "client_id": client_id}
            state.save_config(cfg)
            return self.json(github.device_start(client_id))
        if parts == ["device"] and b.get("action") == "poll":
            return self.json(github.device_poll(state.config()["github"]["client_id"], b["device_code"]))
        if parts == ["use-gh"]:
            github.sign_out()
            return self.json(session()["github"])
        self.fail(404, "no such API")

    def api_providers(self, method, parts):
        if parts == ["test"] and method == "POST":
            return self.json(providers.test())
        if not parts and method == "POST":
            b = self.body()
            cfg, sec = state.config(), state.secrets()
            for key in ("provider", "foundry_endpoint"):
                if key in b:
                    cfg[key] = (b[key] or "").strip()
            if "model" in b:  # remembered per provider
                cfg.setdefault("models", {})[b.get("provider") or cfg.get("provider", "")] = (b["model"] or "").strip()
            for key in ("anthropic_api_key", "foundry_api_key"):
                if b.get(key) is not None:
                    if b[key].strip():
                        sec[key] = b[key].strip()
                    else:
                        sec.pop(key, None)
            state.save_config(cfg)
            state.save_secrets(sec)
            state.apply_model_settings()
            return self.json(providers.status(fresh=True))
        return self.json(providers.status(fresh=True))

    def api_stories(self, method, parts):
        if not parts:
            if method == "GET":
                return self.json(state.list_stories())
            b = self.body()
            if b.get("kind") == "repo":
                job = jobs.start_repo(repo_target(b["repo"]), b.get("options") or {})
            else:
                pr = github.GitHub().pr(*github.parse_pr(b["url"]))
                job = jobs.start(pr, b.get("options") or {})
            return self.json({"sid": job.sid, "job": job.view()})
        if parts == ["import"] and method == "POST":
            return self.json(import_story(Path(self.body()["path"]).expanduser()))
        sid, rest = parts[0], parts[1:]
        state.story_dir(sid)  # validates the id
        if not rest and method == "GET":
            return self.json(story(sid))
        if rest == ["data"]:
            return self.json(story_data(sid))
        if rest == ["events"]:
            return self.events(sid)
        if rest == ["cancel"]:
            return self.json({"cancelled": jobs.cancel(sid)})
        if rest == ["notes"]:
            return self.json(notes(sid, self.body()))
        if rest == ["chat"]:
            return self.chat(sid, self.body())
        if rest == ["chat", "reset"]:
            st = state.app_state(sid)
            st["chat"] = {"turns": [], "session": None}
            state.save_app_state(sid, st)
            return self.json(st["chat"])
        if rest == ["draft"]:
            return self.draft(sid)
        if rest == ["draft", "edit"]:
            return self.json(edit_draft(sid, self.body()))
        if rest == ["post"]:
            b = self.body()
            return self.json(comments.post(sid, b.get("event", "COMMENT"), bool(b.get("pending"))))
        if rest == ["delete"]:
            jobs.cancel(sid)
            shutil.rmtree(state.story_dir(sid), ignore_errors=True)
            return self.json({"deleted": sid})
        self.fail(404, "no such API")

    # ------------------------------------------------------------ streams

    def events(self, sid: str):
        """Server-sent events: the job's log so far, then each new line and status, until it ends."""
        job, q = jobs.listen(sid)
        self.stream_start("text/event-stream")
        send = lambda e: (self.wfile.write(f"data: {json.dumps(e)}\n\n".encode()), self.wfile.flush())  # noqa: E731
        if not job:
            log = state.story_dir(sid) / "run.log"
            for line in (log.read_text().splitlines() if log.exists() else [])[-2000:]:
                send({"type": "line", "line": line})
            return send({"type": "status", "status": "idle"})
        try:
            for line in list(job.lines):
                send({"type": "line", "line": line, "stage": job.stage})
            send({"type": "status", **job.view()})
            while job.status in ("queued", "preparing", "running"):
                try:
                    send(q.get(timeout=15))
                except Exception:  # noqa: BLE001 — a keep-alive comment every 15 s
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            while not q.empty():
                send(q.get_nowait())
        finally:
            jobs.unlisten(job, q)

    def chat(self, sid: str, b: dict):
        self.stream_start("application/x-ndjson")
        try:
            answer = agent.ask(sid, b["message"], self.emit_line)
            self.emit_line({"type": "done", "text": answer})
        except Exception as e:  # noqa: BLE001
            self.emit_line({"type": "error", "text": str(e)[:800]})

    def draft(self, sid: str):
        self.stream_start("application/x-ndjson")
        try:
            d = comments.draft(sid, self.emit_line)
            self.emit_line({"type": "done", "draft": public_draft(d)})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.emit_line({"type": "error", "text": str(e)[:800]})


# ---------------------------------------------------------------- the API's answers

def session() -> dict:
    cfg = state.config()
    gh = github.GitHub()
    user = gh.user()
    return {"github": {"method": gh.method, "user": user, "client_id": cfg["github"].get("client_id", ""),
                       "gh": github.gh_status() if gh.method == "gh" else None},
            "providers": providers.status(), "model": state.chosen_model(cfg),
            "foundry_endpoint": cfg.get("foundry_endpoint", ""), "repos": cfg["repos"],
            "stories": state.list_stories(), "home": str(state.HOME)}


REPO_URL = re.compile(r"^(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def repo_target(text: str) -> dict:
    """'https://github.com/o/r', 'o/r' → {owner, name}; a local directory → {path}."""
    text = text.strip()
    if text.startswith(("/", "~", ".")):
        p = Path(text).expanduser().resolve()
        if not (p / ".git").exists():
            raise ValueError(f"{p} is not a git checkout")
        return {"path": str(p)}
    m = REPO_URL.match(text)
    if not m:
        raise ValueError(f"not a repository: {text!r} (a GitHub link, owner/name, or a local path)")
    return {"owner": m[1], "name": m[2]}


def story_data(sid: str) -> dict:
    """What the reader shows, from render.py's export (built on demand for older stories), with each proof."""
    import render
    d = state.story_dir(sid)
    f = d / "story.json"
    if not f.exists() or not (d / "index.html").exists() or f.stat().st_mtime < (d / "index.html").stat().st_mtime:
        if not (d / "outline.json").exists():
            raise FileNotFoundError("this story isn't written yet")
        f.write_text(json.dumps(render.story_data(d)) + "\n")
    data = json.loads(f.read_text())
    for ch in data["chapters"]:
        proof = next(iter(sorted((d / "proofs").glob(f"{ch['n']:02}.*"))), None) if (d / "proofs").exists() else None
        ch["proof"] = proof.read_text() if proof else ""
    verified = state.read_json(d / "verify.json", {})  # a change story's proof outcomes, by chapter
    for ch in data["chapters"]:
        ch["checked"] = verified.get(str(ch["n"]))
    return data


def inspect(url: str) -> dict:
    owner, name, number = github.parse_pr(url)
    gh = github.GitHub()
    pr = gh.pr(owner, name, number)
    files = gh.files(owner, name, number)
    checkout = repos.checkout_for(owner, name)
    sid = state.story_id(owner, name, number)
    me = (gh.user() or {}).get("login")
    warnings = ["Generating the story runs this pull request's code and tests on your machine."]
    if pr["fork"]:
        warnings.append(f"The change comes from a fork ({pr['head']['repo']}).")
    if me and pr["author"] != me:
        warnings.append(f"It was written by {pr['author']}, not you: read it before you run it.")
    tests = [f["path"] for f in files if re.search(r"\.(spec|test)\.[cm]?[jt]sx?$", f["path"])]
    return {"pr": pr, "checkout": {**checkout, "exists": (Path(checkout["path"]) / ".git").exists()},
            "files": len(files), "tests": tests, "warnings": warnings,
            "story": sid if (state.story_dir(sid) / "outline.json").exists() else None}


def story(sid: str) -> dict:
    d = state.story_dir(sid)
    st = state.app_state(sid)
    outline = state.read_json(d / "outline.json", {})
    job = jobs.JOBS.get(sid)
    return {"sid": sid, "kind": "repo" if st.get("repo") else "pr", "repo": st.get("repo", {}),
            "pr": st.get("pr", {}), "notes": st.get("notes", []), "chat": st.get("chat", {}),
            "draft": public_draft(st["draft"]) if st.get("draft") else None, "posted": st.get("posted", []),
            "ready": (d / "index.html").exists(), "title": outline.get("title"), "job": job.view() if job else None,
            "chapters": [{"n": c["n"], "title": c["title"]} for c in outline.get("chapters", [])]}


def public_draft(d: dict) -> dict:
    """The draft as the page needs it: each comment with the diff lines around it."""
    out = {k: v for k, v in d.items() if k not in ("hunks", "patches")}
    for c in out["comments"]:
        c["context"] = excerpt(d["patches"].get(c["path"]), c["side"], c.get("start_line") or c["line"], c["line"])
    return out


def excerpt(patch: str | None, side: str, start: int, end: int, around: int = 3) -> list[dict]:
    """The patch lines near [start, end] on one side: [{"kind": "+"|"-"|" ", "old", "new", "text", "hit"}]."""
    rows, old, new = [], 0, 0
    for line in (patch or "").splitlines():
        m = comments.HUNK.match(line)
        if m:
            old, new = int(m[1]), int(m[3])
            continue
        if line.startswith("\\"):
            continue
        kind = line[:1] or " "
        row = {"kind": kind, "old": old if kind != "+" else None, "new": new if kind != "-" else None, "text": line[1:]}
        n = row["new"] if side == "RIGHT" else row["old"]
        row["hit"] = n is not None and start <= n <= end and not (side == "RIGHT" and kind == "-") \
            and not (side == "LEFT" and kind == "+")
        rows.append(row)
        old += kind != "+"
        new += kind != "-"
    hits = [i for i, r in enumerate(rows) if r["hit"]]
    if not hits:
        return []
    return rows[max(0, hits[0] - around): hits[-1] + around + 1]


def notes(sid: str, b: dict) -> list:
    st = state.app_state(sid)
    ns = st.setdefault("notes", [])
    if b.get("action") == "add":
        n = b["note"]
        ns.append({"id": max([x["id"] for x in ns] or [0]) + 1, "text": n["text"].strip(), "anchor": n.get("anchor"),
                   "chapter": n.get("chapter"), "quote": n.get("quote"), "created": state.now()})
    elif b.get("action") == "edit":
        for x in ns:
            if x["id"] == b["note"]["id"]:
                x["text"] = b["note"]["text"].strip()
    elif b.get("action") == "delete":
        st["notes"] = ns = [x for x in ns if x["id"] != b["id"]]
    state.save_app_state(sid, st)
    return ns


def edit_draft(sid: str, b: dict) -> dict:
    st = state.app_state(sid)
    d = st["draft"]
    for key in ("summary", "event"):
        if key in b:
            d[key] = b[key]
    for i, edit in enumerate(b.get("comments") or []):
        if i < len(d["comments"]):
            c = d["comments"][i]
            for key in ("body", "include", "line", "start_line", "side"):
                if key in edit:
                    c[key] = edit[key]
    st["draft"] = d
    state.save_app_state(sid, st)
    return public_draft(comments.recheck(sid))


def import_story(path: Path) -> dict:
    """Bring a story written elsewhere into the app: a change story (review.py) or a repository story (story.py)."""
    outline = state.read_json(path / "outline.json", {})
    info = outline.get("repo", {})
    if not outline or not info.get("name"):
        raise ValueError(f"{path} has no story (no outline.json)")
    owner, name = info["name"].split("/", 1)
    if outline.get("mode") == "diff":
        if not info.get("number"):
            raise ValueError(f"{path} is a change story without a pull request number")
        sid = state.story_id(owner, name, int(info["number"]))
    else:
        sid = state.repo_story_id({"owner": owner, "name": name})
    dest = state.story_dir(sid)
    if dest.exists():
        raise ValueError(f"already imported as {sid}")
    shutil.copytree(path, dest)
    st = state.app_state(sid)
    if outline.get("mode") == "diff":
        setup = state.read_json(dest / "changes.json", {})
        setup["repo"] = str(repo_dir(setup))  # absolute: the copy no longer sits next to it
        state.write_json(dest / "changes.json", setup)
        try:
            st["pr"] = github.GitHub().pr(owner, name, int(info["number"]))
        except github.GitHubError:
            st["pr"] = {"owner": owner, "name": name, "number": int(info["number"]), "title": info.get("title", ""),
                        "base": {"sha": info["base"]}, "head": {"sha": info["head"]},
                        "url": f"{info['url']}/pull/{info['number']}"}
    else:
        outline["repo"]["local_path"] = str((ROOT_DIR / info["local_path"]).resolve())  # absolute, for the same reason
        state.write_json(dest / "outline.json", outline)
        st["repo"] = {"owner": owner, "name": name, "reader": outline.get("reader", "owner")}
    state.save_app_state(sid, st)
    return {"sid": sid}


def main() -> int:
    global PORT
    ap = argparse.ArgumentParser(description="codestory review: a local web app around review.py")
    ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    PORT = a.port
    state.setup()
    state.apply_model_settings()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.daemon_threads = True
    print(f"codestory review: http://127.0.0.1:{PORT}/?t={TOKEN}\n  (data in {state.HOME}; Ctrl-C to stop)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
