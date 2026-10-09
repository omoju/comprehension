"""How a story should read, for every writer stage, and the parts of it code can check.

The checks ran on accountability (every claim cited, every proof able to fail); this adds readability, in the same
manner: what can be counted is counted, and a chapter that fails goes back to the model with the numbers.
"""

from __future__ import annotations

import re

WRITING = """How it should read, which matters as much as being right:
- Write for a smart, busy reader who will stop at the first dull paragraph. Every paragraph earns its place.
- Open with what is at stake, as a concrete situation in the world: who calls this, with what, and what goes wrong
  (or right) for them. Use the pull request's description or the README when they say it.
- Tell the decisive moments, not every step. When the data passes through plumbing, say so in a clause and move on.
  Never list every call; never narrate a function that changes nothing that matters.
- When cases repeat, tell one fully and dismiss the others in a sentence.
- Never mention the trace, its line numbers, spans, the plan or the chapters' machinery: the reader sees only the
  story and the code. Values, names and lines are what you cite.
- Link the words that name the thing ("the guard reads one character past the base"), never "head l.292" or
  "see here"; at most one link per sentence.
- Plain words, short sentences, short paragraphs (four sentences at most). Explain a term the first time it appears.
  Concrete values in `code`.
- End a chapter on what it means, in one sentence, not on a summary of what was said."""

LIMITS = {"chapter_words": 520, "paragraph_words": 110, "summary_words": 70}
TRACE_TALK = re.compile(r"\btrace\s*(?:l(?:ines?)?\.?\s*)?\d|\(trace\b|\bthe trace (?:shows|records|says)\b|"
                        r"\btrace lines?\b|\bspan of the trace\b", re.I)
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def prose(text: str) -> str:
    """A chapter without its heading, quotes, code blocks and link targets: the words a reader reads."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = LINK.sub(r"\1", text)
    return "\n".join(line for line in text.splitlines() if not line.startswith(("#", ">")))


def words(text: str) -> int:
    return len(re.findall(r"[\w`'’-]+", text))


def check_chapter(text: str, limit: int = LIMITS["chapter_words"]) -> list[str]:
    """What code can decide about how a chapter reads. Empty means it may stand."""
    errors = []
    body = prose(text)
    n = words(body)
    if n > limit:
        errors.append(f"the chapter runs {n} words; tell it in at most {limit}: keep the decisive moments, cut the "
                      "plumbing and the repeated cases")
    for para in (p for p in re.split(r"\n\s*\n", body) if p.strip()):
        if (m := words(para)) > LIMITS["paragraph_words"]:
            errors.append(f"a paragraph runs {m} words (\"{para.strip()[:60]}…\"); split it or cut it to at most "
                          f"{LIMITS['paragraph_words']}")
    talk = [m.group(0) for m in TRACE_TALK.finditer(text)]
    if talk:
        errors.append(f"it mentions the trace {len(talk)} time{'s' if len(talk) > 1 else ''} (\"{talk[0]}\"…); the "
                      "reader never sees it: cite the code and give the values instead")
    bad_links = [t for t in LINK.findall(text) if re.fullmatch(r"\s*(head|base|here|this|link|see|l\.?\s*\d[\d\-–]*)"
                                                                r"[\s\w.\-–]*", t, re.I)]
    for t in bad_links[:3]:
        errors.append(f"a link reads \"{t}\"; link the words that name the thing instead")
    return errors


def check_links(text: str, repo_url: str) -> list[str]:
    """Accountability before style: a chapter cites the code, and names each commit by its hash. A link to
    `…/blob/HEAD/…` or `…/blob/BASE/…` looks right and points at whatever the branch holds today, so the checker
    can't hold the chapter to the lines it read."""
    revs = re.findall(re.escape(repo_url) + r"/blob/([^/\s)]+)/", text)
    if not revs:
        return [f"there are no links to the code: link the claims to the lines that show them ({repo_url}/blob/<the "
                "full commit hash given>/path#L10-L14)"]
    bad = sorted({r for r in revs if not re.fullmatch(r"[0-9a-f]{7,40}", r)})
    return [f"links name the commit as {', '.join(repr(b) for b in bad)}; use the full commit hash given in the request "
            "(the link prefixes are spelled out there)"] if bad else []


def check_summary(name: str, text: str, limit: int = LIMITS["summary_words"]) -> list[str]:
    n = words(text)
    return [f"the {name} runs {n} words; at most {limit}"] if n > limit else []
