"""Run pytest files under the tracer: each test is the root of a run, in trace.py's shape.

    <venv python> codestory/py/pytest_trace.py <pkg-dir> <test file> [<test file> ...]

Environment, as the TypeScript runtime reads it:
    CS_TRACE_OUT   where to write the trace ({"fn": "scenario", "calls": [one root per test]})
    CS_INCLUDE     comma-separated path prefixes inside <pkg-dir> whose functions are recorded ("" = all; "-/" = none)
    CS_LINES       "0" to skip recording executed lines (proof runs need only each test's outcome)

Each root is {"fn": "test: <nodeid>", "file", "line", "args": {}, "calls", "lines", "returned" | "raised"}; a test
that makes more than BUDGET calls is cut off and marked "runaway". Only the test body is traced (fixture setup is
the world the test enters, not the data's journey). Standard library plus pytest; runs inside the package's venv.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # codestory/, for trace.show
import re  # noqa: E402
from trace import show as _show  # noqa: E402

ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")


def show(value: object) -> str:
    """A short repr with memory addresses removed, so the same object on the base and the head compares equal."""
    return ADDRESS.sub("", _show(value))

BUDGET = 20_000
SKIP = ("/tests/", "/test/", "/.venv/", "/site-packages/", "/.codestory-venv/")


class Recorder:
    def __init__(self, pkg_dir: Path, include: list[str], lines: bool):
        self.pkg = pkg_dir.resolve()
        self.include = include
        self.lines = lines
        self.roots: list[dict] = []
        self.stack: list[dict] = []
        self.executed: dict[str, set[int]] = {}
        self.count = 0
        self.importing = 0
        self.collection_errors: list[str] = []

    def wanted(self, filename: str) -> bool:
        if not filename.startswith(str(self.pkg)) or any(s in filename for s in SKIP):
            return False
        rel = filename[len(str(self.pkg)) + 1:]
        if self.include == ["-/"]:
            return False
        return not self.include or any(rel.startswith(i) for i in self.include)

    def import_tracer(self, frame, event, arg):
        if event == "return":
            self.importing -= 1
        return self.import_tracer

    def tracer(self, frame, event, arg):
        if event != "call":
            return None
        code = frame.f_code
        if code.co_name == "<module>":
            self.importing += 1
            return self.import_tracer
        if self.importing or not self.wanted(code.co_filename) or not self.stack:
            return None
        root = self.roots[-1]
        if self.count >= BUDGET:
            root["runaway"] = True
            return None
        self.count += 1
        args = {}
        for name in code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]:
            if name in frame.f_locals:
                v = frame.f_locals[name]
                args[name] = f"<{type(v).__name__}>" if name in ("self", "cls") else show(v)
        rel = str(Path(code.co_filename).relative_to(self.pkg))
        node = {"fn": getattr(code, "co_qualname", code.co_name), "file": rel, "line": code.co_firstlineno,
                "args": args, "calls": []}
        self.stack[-1]["calls"].append(node)
        self.stack.append(node)
        executed = self.executed.setdefault(rel, set()) if self.lines else None

        def local(frame, event, arg):
            if event == "line":
                if executed is not None:
                    executed.add(frame.f_lineno)
            elif event == "return":
                node["returned"] = show(arg)
                if self.stack and self.stack[-1] is node:
                    self.stack.pop()
            elif event == "exception":
                node.setdefault("raised", show(arg[1]))
            return local

        return local

    def begin(self, nodeid: str, path: str, line: int) -> dict:
        root = {"fn": f"test: {nodeid}", "file": path, "line": line, "args": {}, "calls": [], "lines": {}}
        self.roots.append(root)
        self.stack = [root]
        self.executed = {}
        self.count = 0
        self.importing = 0
        sys.settrace(self.tracer)
        return root

    def end(self, root: dict, excinfo) -> None:
        sys.settrace(None)
        self.stack = []
        root["lines"] = {f: sorted(ls) for f, ls in sorted(self.executed.items())}
        if excinfo is None:
            root["returned"] = "None"
        else:
            root["raised"] = show(excinfo.value) if hasattr(excinfo, "value") else show(excinfo)


class Plugin:
    def __init__(self, rec: Recorder):
        self.rec = rec

    def pytest_runtest_logreport(self, report):  # a test whose fixtures fail never runs: record it as failed
        if report.when == "setup" and report.failed:
            path, line, _ = report.location
            try:
                rel = str(Path(path).resolve().relative_to(self.rec.pkg))
            except ValueError:
                rel = path
            text = getattr(report, "longreprtext", "") or str(report.longrepr)
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or ["setup failed"]
            self.rec.roots.append({"fn": f"test: {report.nodeid}", "file": rel, "line": (line or 0) + 1, "args": {},
                                   "calls": [], "lines": {}, "raised": "setup error: " + last[0].strip()[:160]})

    def pytest_collectreport(self, report):  # a file that fails to import on one side: every test in it "fails"
        if report.failed:
            self.rec.collection_errors.append(str(report.nodeid or report.fspath))

    def pytest_runtest_call(self, item):  # noqa: D401  (pytest hook)
        import pytest

        path = str(Path(str(item.fspath)).resolve())
        try:
            rel = str(Path(path).relative_to(self.rec.pkg))
        except ValueError:
            rel = path
        root = self.rec.begin(item.nodeid, rel, (item.location[1] or 0) + 1)
        try:
            item.runtest()
        except BaseException as e:  # noqa: BLE001  (pytest will re-raise through its own protocol)
            self.rec.end(root, type("E", (), {"value": e})())
            raise
        else:
            self.rec.end(root, None)
        return True


def main() -> int:
    import pytest

    pkg_dir = Path(sys.argv[1]).resolve()
    specs = sys.argv[2:]
    out = Path(os.environ["CS_TRACE_OUT"])
    include = [i.strip() for i in os.environ.get("CS_INCLUDE", "").split(",") if i.strip()]
    rec = Recorder(pkg_dir, include, os.environ.get("CS_LINES", "1") != "0")
    os.chdir(pkg_dir)
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))
    code = pytest.main(["-q", "-p", "no:cacheprovider", "--no-header", *specs], plugins=[Plugin(rec)])
    previous, errors = [], []
    if out.exists():  # one run per spec appends; several specs in one invocation share a file
        data = json.loads(out.read_text())
        previous, errors = data.get("calls", []), data.get("collection_errors", [])
    out.write_text(json.dumps({"fn": "scenario", "file": "scenario", "line": 1, "args": {},
                               "calls": previous + rec.roots, "lines": {},
                               "collection_errors": errors + rec.collection_errors}, indent=1) + "\n")
    return int(code)


if __name__ == "__main__":
    sys.exit(main())
