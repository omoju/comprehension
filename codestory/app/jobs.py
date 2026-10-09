"""Story generation as a background job: prepare the checkout, run review.py (a pull request) or story.py (a whole
repository), stream its log to the page.

One job runs at a time (a test suite that boots a server can't share its ports with another); the rest wait in
line. Every log line goes to stories/<id>/run.log and to whoever is listening. A job can be cancelled: its whole
process tree is stopped, test runs included (diff.py starts those in process groups of their own).
"""

from __future__ import annotations

import collections
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import repos
import state
from github import GitHub, GitHubError

REVIEW = Path(__file__).resolve().parent.parent / "review.py"
STORY = Path(__file__).resolve().parent.parent / "story.py"
_line = threading.Lock()  # one story at a time
JOBS: dict[str, "Job"] = {}


class Job:
    def __init__(self, sid: str, pr: dict, options: dict, repo: dict | None = None):
        self.sid, self.pr, self.options, self.repo = sid, pr, options, repo
        self.kind = "repo" if repo else "pr"
        self.status = "queued"  # queued, preparing, running, done, failed, cancelled
        self.stage = ""
        self.error = ""
        self.started = state.now()
        self.ended = None
        self.lines = collections.deque(maxlen=4000)
        self.listeners: list[queue.Queue] = []
        self.proc: subprocess.Popen | None = None
        self.cancelled = False
        self.log_file = state.story_dir(sid) / "run.log"
        self.after: Callable[[], None] | None = None  # cleanup once the run ends, however it ends

    def view(self) -> dict:
        return {"sid": self.sid, "status": self.status, "stage": self.stage, "error": self.error,
                "started": self.started, "ended": self.ended}

    def emit(self, event: dict) -> None:
        for q in list(self.listeners):
            q.put(event)

    def log(self, line: str) -> None:
        self.lines.append(line)
        with self.log_file.open("a") as f:
            f.write(line + "\n")
        if line.startswith("== "):
            self.stage = line[3:].split(":")[0]
        self.emit({"type": "line", "line": line, "stage": self.stage})

    def set(self, status: str, error: str = "") -> None:
        self.status, self.error = status, error
        if status in ("done", "failed", "cancelled"):
            self.ended = state.now()
        self.emit({"type": "status", **self.view()})


def start(pr: dict, options: dict) -> Job:
    sid = state.story_id(pr["owner"], pr["name"], pr["number"])
    if sid in JOBS and JOBS[sid].status in ("queued", "preparing", "running"):
        return JOBS[sid]
    story = state.story_dir(sid)
    story.mkdir(parents=True, exist_ok=True)
    st = state.app_state(sid)
    st["pr"] = pr
    state.save_app_state(sid, st)
    if pr.get("body", "").strip():  # the author's account of the change, for the story's stakes
        (story / "pr.md").write_text(f"# {pr['title']}\n\n{pr['body'].strip()}\n")
    if options.get("fresh"):
        for f in ("outline.json", "changes.json", "diff.json"):  # plan again from a fresh trace
            (story / f).unlink(missing_ok=True)
    job = JOBS[sid] = Job(sid, pr, options)
    (story / "run.log").write_text("")
    threading.Thread(target=_run, args=(job,), daemon=True, name=f"job-{sid}").start()
    return job


def start_repo(target: dict, options: dict) -> Job:
    """A story of a whole repository (story.py): target is {owner, name} on GitHub, or {path} of a local checkout."""
    sid = state.repo_story_id(target)
    if sid in JOBS and JOBS[sid].status in ("queued", "preparing", "running"):
        return JOBS[sid]
    story = state.story_dir(sid)
    story.mkdir(parents=True, exist_ok=True)
    if options.get("fresh") or (options.get("about") or "").strip():  # a new run to follow: everything but the notes
        for f in story.iterdir():
            if f.name not in ("app.json", "run.log"):
                shutil.rmtree(f) if f.is_dir() else f.unlink()
    st = state.app_state(sid)
    st["repo"] = {**target, "reader": options.get("reader") or "owner"}
    state.save_app_state(sid, st)
    job = JOBS[sid] = Job(sid, {}, options, repo=target)
    (story / "run.log").write_text("")
    threading.Thread(target=_run, args=(job,), daemon=True, name=f"job-{sid}").start()
    return job


def _command(job: Job, gh: GitHub) -> list[str]:
    """Prepare the checkout and say how to write the story."""
    o = job.options
    if job.kind == "repo":
        path = job.repo.get("path")
        if not path:
            prepared = repos.prepare_repo(gh, job.repo["owner"], job.repo["name"], job.log)
            path = prepared["path"]
            if prepared.get("source"):
                job.after = lambda: repos.finish_repo(prepared, state.story_dir(job.sid), job.log)
        argv = [sys.executable, "-u", str(STORY), path, "--reader", o.get("reader") or "owner",
                "--out", str(state.story_dir(job.sid))]
        pkg = (o.get("pkg") or "").strip().strip("/")
        if pkg and (Path(pkg).is_absolute() or ".." in Path(pkg).parts):
            raise GitHubError(f"{pkg!r} is not a folder inside the repository")
        about = (o.get("about") or "").strip()
        return argv + (["--pkg", pkg] if pkg else []) + (["--about", about] if about else [])
    repo = repos.prepare(gh, job.pr, job.log)
    argv = [sys.executable, "-u", str(REVIEW), repo["path"], "--pr", str(job.pr["number"]),
            "--base", job.pr["base"]["sha"], "--head", job.pr["head"]["sha"], "--title", job.pr["title"],
            "--out", str(state.story_dir(job.sid))]
    for flag, value in (("--pkg", o.get("pkg") or repo["pkg"]), ("--runner", o.get("runner") or repo["runner"]),
                        ("--link", o.get("link") or repo["link"])):
        if value:
            argv += [flag, value]
    for spec in o.get("specs") or []:
        argv += ["--spec", spec]
    return argv


def _run(job: Job) -> None:
    with _line:
        if job.cancelled:
            return job.set("cancelled")
        try:
            job.set("preparing")
            gh = GitHub()
            argv = _command(job, gh)
            if job.cancelled:
                return job.set("cancelled")
            job.set("running")
            state.apply_model_settings()
            env = {**gh.git_env(), "PYTHONUNBUFFERED": "1"}
            job.proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
                                        start_new_session=True)
            for line in job.proc.stdout:
                job.log(line.rstrip())
            code = job.proc.wait()
            if job.cancelled:
                job.set("cancelled")
            elif code == 0:
                job.set("done")
            else:
                job.set("failed", failure(job.lines) or f"{Path(argv[2]).name} exited {code}")
        except (GitHubError, repos.deps.InstallError, OSError, subprocess.SubprocessError) as e:
            job.log(f"✗ {e}")
            job.set("cancelled" if job.cancelled else "failed", str(e))
        finally:
            if job.after:
                try:
                    job.after()
                except (OSError, subprocess.SubprocessError) as e:
                    job.log(f"cleanup: {e}")


def failure(lines: list[str]) -> str:
    """Why a run failed, in one line: the exception a traceback in the failed stage ends with, or else that stage's
    first ✗ line. review.py's own ✗ line comes last and only names the stage, so it is the fallback."""
    start = max((i for i, ln in enumerate(lines) if ln.startswith("== ")), default=0)
    stage = lines[start:]
    if any(ln.startswith("Traceback") for ln in stage):
        raised = [ln for ln in stage if re.match(r"^[\w.]+(Error|Exception|Exit)\b.*: ", ln)]
        if raised:
            return raised[-1][:600]
    marked = [ln for ln in stage if ln.startswith("✗")] or [ln for ln in lines if ln.startswith("✗")]
    return marked[0].lstrip("✗ ")[:600] if marked else ""


def cancel(sid: str) -> bool:
    job = JOBS.get(sid)
    if not job or job.status not in ("queued", "preparing", "running"):
        return False
    job.cancelled = True
    if job.proc and job.proc.poll() is None:
        for pid in reversed(descendants(job.proc.pid)):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        time.sleep(3)
        for pid in reversed(descendants(job.proc.pid)):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    return True


def descendants(pid: int) -> list[int]:
    """pid and every process below it, whatever session or group it started."""
    out = subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True).stdout
    children = collections.defaultdict(list)
    for line in out.splitlines():
        p, pp = map(int, line.split())
        children[pp].append(p)
    found, stack = [], [pid]
    while stack:
        p = stack.pop()
        found.append(p)
        stack += children.get(p, [])
    return found


def listen(sid: str) -> tuple[Job | None, queue.Queue | None]:
    job = JOBS.get(sid)
    if not job:
        return None, None
    q: queue.Queue = queue.Queue()
    job.listeners.append(q)
    return job, q


def unlisten(job: Job, q: queue.Queue) -> None:
    if q in job.listeners:
        job.listeners.remove(q)
