"""GitHub for the review app: who you are, the pull request, its diff, and the review you post.

Two ways to sign in, chosen in config.json (`github.method`):

  gh     your GitHub CLI login (`gh auth login`). Every call is `gh api …`, so this app never holds a token.
  token  "Sign in with GitHub" in the app: the OAuth device flow, with the client id of an OAuth App you register
         (Settings → Developer settings → OAuth Apps, "Enable Device Flow"). The token is kept in secrets.json.

Git itself (fetching a pull request's commits, cloning) gets the same credentials non-interactively, so it never
waits on a credential prompt. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import state

API = "https://api.github.com"
SCOPES = "repo"  # read private repositories and post reviews on them

PR_URL = re.compile(r"^(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/pull/|#)(\d+)(?:[/?#].*)?$")


class GitHubError(RuntimeError):
    pass


def parse_pr(text: str) -> tuple[str, str, int]:
    """'https://github.com/o/r/pull/12', 'o/r/pull/12' or 'o/r#12' → (o, r, 12)."""
    m = PR_URL.match(text.strip())
    if not m:
        raise GitHubError(f"not a pull request link: {text!r} (expected https://github.com/<owner>/<repo>/pull/<n>)")
    return m[1], m[2], int(m[3])


class GitHub:
    def __init__(self):
        cfg, sec = state.config(), state.secrets()
        self.method = cfg["github"].get("method", "gh")
        self.token = sec.get("github_token") if self.method == "token" else None

    # ------------------------------------------------------------ transport

    def call(self, path: str, method: str = "GET", body: dict | None = None) -> dict | list | None:
        path = path.lstrip("/")
        if self.method == "token":
            return self._http(path, method, body)
        return self._gh(path, method, body)

    def _http(self, path, method, body):
        if not self.token:
            raise GitHubError("not signed in to GitHub")
        req = urllib.request.Request(f"{API}/{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"authorization": f"Bearer {self.token}", "accept": "application/vnd.github+json",
                                              "x-github-api-version": "2022-11-28", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise GitHubError(f"GitHub said {e.code}: {e.read().decode(errors='replace')[:600]}") from e
        except urllib.error.URLError as e:
            raise GitHubError(f"cannot reach GitHub: {e.reason}") from e
        return json.loads(raw) if raw else None

    def _gh(self, path, method, body):
        if not shutil.which("gh"):
            raise GitHubError("the GitHub CLI (gh) is not installed; install it, or sign in with GitHub in the app")
        argv = ["gh", "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
        if body is not None:
            argv += ["--input", "-"]
        done = subprocess.run(argv, input=json.dumps(body) if body is not None else None, capture_output=True,
                              text=True, timeout=120)
        if done.returncode != 0:
            raise GitHubError(f"gh api {method} {path}: {(done.stderr or done.stdout).strip()[:600]}")
        return json.loads(done.stdout) if done.stdout.strip() else None

    def pages(self, path: str, limit: int = 3000) -> list:
        out, page = [], 1
        sep = "&" if "?" in path else "?"
        while len(out) < limit:
            chunk = self.call(f"{path}{sep}per_page=100&page={page}")
            out += chunk or []
            if not chunk or len(chunk) < 100:
                return out
            page += 1
        return out

    # ------------------------------------------------------------ what the app needs

    def user(self) -> dict | None:
        try:
            u = self.call("user")
        except GitHubError:
            return None
        return {"login": u["login"], "name": u.get("name") or u["login"], "avatar": u.get("avatar_url")}

    def pr(self, owner: str, name: str, number: int) -> dict:
        p = self.call(f"repos/{owner}/{name}/pulls/{number}")
        return {"owner": owner, "name": name, "number": number, "title": p["title"], "body": p.get("body") or "",
                "url": p["html_url"], "state": p["state"], "merged": bool(p.get("merged_at")), "draft": p.get("draft"),
                "author": p["user"]["login"], "base": {"sha": p["base"]["sha"], "ref": p["base"]["ref"]},
                "head": {"sha": p["head"]["sha"], "ref": p["head"]["ref"],
                         "repo": (p["head"].get("repo") or {}).get("full_name") or "(deleted fork)"},
                "fork": (p["head"].get("repo") or {}).get("full_name") != f"{owner}/{name}",
                "private": p["base"]["repo"].get("private", False)}

    def files(self, owner: str, name: str, number: int) -> list[dict]:
        return [{"path": f["filename"], "status": f["status"], "patch": f.get("patch"),
                 "previous": f.get("previous_filename"), "additions": f["additions"], "deletions": f["deletions"]}
                for f in self.pages(f"repos/{owner}/{name}/pulls/{number}/files")]

    def review_comments(self, owner: str, name: str, number: int) -> list[dict]:
        return [{"path": c["path"], "line": c.get("line"), "side": c.get("side"), "body": c["body"],
                 "author": c["user"]["login"]}
                for c in self.pages(f"repos/{owner}/{name}/pulls/{number}/comments")]

    def create_review(self, owner: str, name: str, number: int, payload: dict) -> dict:
        r = self.call(f"repos/{owner}/{name}/pulls/{number}/reviews", "POST", payload)
        return {"id": r["id"], "state": r["state"], "url": r.get("html_url")}

    def delete_pending_review(self, owner: str, name: str, number: int, review_id: int) -> None:
        self.call(f"repos/{owner}/{name}/pulls/{number}/reviews/{review_id}", "DELETE")

    # ------------------------------------------------------------ git, with the same credentials

    def git_args(self) -> list[str]:
        """`git -c …` arguments that make git authenticate like this app, and never prompt."""
        if self.method == "token":
            return ["-c", "credential.helper=", "-c", "core.askPass=" + str(askpass())]
        return ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]

    def git_env(self) -> dict:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        if self.method == "token" and self.token:
            env["CODESTORY_GIT_TOKEN"] = self.token  # read by the askpass script; never on a command line
        return env


def askpass() -> Path:
    script = state.HOME / "askpass.sh"
    if not script.exists():
        script.write_text('#!/bin/sh\ncase "$1" in Username*) echo x-access-token ;; *) echo "$CODESTORY_GIT_TOKEN" ;; esac\n')
        os.chmod(script, 0o700)
    return script


# ---------------------------------------------------------------- "Sign in with GitHub": the OAuth device flow

def _form(url: str, fields: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST",
                                 headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise GitHubError(f"GitHub said {e.code}: {e.read().decode(errors='replace')[:300]}") from e


def device_start(client_id: str) -> dict:
    """Ask GitHub for a code the user enters at github.com/login/device."""
    r = _form("https://github.com/login/device/code", {"client_id": client_id, "scope": SCOPES})
    if "device_code" not in r:
        raise GitHubError(f"GitHub refused the device flow: {r.get('error_description') or r}")
    return {"device_code": r["device_code"], "user_code": r["user_code"], "verify": r["verification_uri"],
            "interval": r.get("interval", 5), "expires": r.get("expires_in", 900)}


def device_poll(client_id: str, device_code: str) -> dict:
    """One poll: {"status": "pending" | "slow_down" | "done" | "expired" | "denied"}; on done, the token is saved."""
    r = _form("https://github.com/login/oauth/access_token",
              {"client_id": client_id, "device_code": device_code,
               "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
    if "access_token" in r:
        sec = state.secrets()
        sec["github_token"] = r["access_token"]
        state.save_secrets(sec)
        cfg = state.config()
        cfg["github"] = {**cfg["github"], "method": "token"}
        state.save_config(cfg)
        return {"status": "done"}
    err = r.get("error", "")
    return {"status": {"authorization_pending": "pending", "slow_down": "slow_down", "expired_token": "expired",
                       "access_denied": "denied"}.get(err, "error"), "detail": r.get("error_description", err)}


def sign_out() -> None:
    sec = state.secrets()
    sec.pop("github_token", None)
    state.save_secrets(sec)
    cfg = state.config()
    cfg["github"] = {**cfg["github"], "method": "gh"}
    state.save_config(cfg)


def gh_status() -> dict:
    """Is the GitHub CLI installed, and signed in?"""
    if not shutil.which("gh"):
        return {"installed": False, "login": None}
    done = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, timeout=30)
    return {"installed": True, "login": done.stdout.strip() if done.returncode == 0 else None}
