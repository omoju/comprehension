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
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

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
    if options.get("fresh"):
        for f in ("outline.json", "trace.txt", "trace.json", "scenario.json"):
            (story / f).unlink(missing_ok=True)
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
        path = job.repo.get("path") or repos.prepare_repo(gh, job.repo["owner"], job.repo["name"], job.log)["path"]
        argv = [sys.executable, "-u", str(STORY), path, "--reader", o.get("reader") or "owner",
                "--out", str(state.story_dir(job.sid))]
        return argv + (["--pkg", o["pkg"]] if o.get("pkg") else [])
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
                last = next((ln for ln in reversed(job.lines) if ln.startswith("✗")), f"{Path(argv[2]).name} exited {code}")
                job.set("failed", last.lstrip("✗ "))
        except (GitHubError, repos.deps.InstallError, OSError, subprocess.SubprocessError) as e:
            job.log(f"✗ {e}")
            job.set("cancelled" if job.cancelled else "failed", str(e))


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
