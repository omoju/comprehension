# codestory review

A local web app around `review.py` and `story.py`. Point it at a pull request, read the change story written about
it, write your notes, ask an assistant about the story, then let it draft the review comments from your notes, approve
them, and post them to the pull request, each on the lines it concerns. Or point it at a repository and read the story
of one run through it, with the same notes and assistant.

```bash
./review                       # from the repository root: sets up .venv the first time, then starts the app and opens it
```

`./review` needs `uv` (and Node 20.6+ for TypeScript); it passes `--port` and `--no-open` through. Without it:
`.venv/bin/python codestory/app/server.py [--open]` prints `http://127.0.0.1:8765/?t=…`; open that link.

Standard library only; the page uses marked and DOMPurify from cdnjs and its fonts from Google Fonts. Data lives in `~/.codestory`
(`CODESTORY_HOME` to move it), outside this repository, so a story about a private repository can't be committed
here by accident.

## Signing in

- **GitHub.** Your GitHub CLI login (`gh auth login`) by default: every call goes through `gh api`, so the app never
  holds a token. Or "Sign in with GitHub" in the app: the OAuth device flow, with the client id of an OAuth App you
  register (Developer settings → OAuth Apps, Enable Device Flow); the token is kept in `~/.codestory/secrets.json`.
  Git fetches use the same credentials and never wait on a prompt.
- **The model.** The providers of `llm.py`: your Claude login (`claude auth login`), your ChatGPT login
  (`codex login`), Azure AI Foundry (an endpoint and a deployment; a key or `az login`), or an Anthropic API key. The
  app only reports where each stands; the CLIs keep their own logins. The model menu in the top bar lists what each
  ready provider offers (Claude's models, the Codex models your login lists, your Foundry deployments) and remembers
  a choice per provider; Claude Opus 5.5 is the default.

## From a pull request to a review

1. **Look it up.** Paste the link. The app shows the change, the tests it brings, and where the story will run: your
   own checkout if you registered one for that repository (with what its worktrees borrow, such as `venv,.env`), or
   a clone it keeps under `~/.codestory/repos`, with dependencies installed from the lockfile. Writing the story runs
   the pull request's code and tests on your machine, and the app asks you to say you know that.
2. **The story is written.** `review.py` runs as a job, one at a time, its log streamed to the page; cancelling stops
   the whole process tree, test runs included.
3. **Read and note.** The story opens in the app: the premise, the verdict, then each chapter with what changed
   before and after and what the run shows. Click a link to the code to open it under the paragraph, before or
   after the change, and note it; a note can also be about the change as a whole.
4. **Ask.** The assistant answers from the story and the code on both sides. With a Claude or ChatGPT login it is
   that CLI's own agent, read-only (Claude Code with Read, Grep and Glob; Codex in its read-only sandbox), over plain
   worktrees of the base and the head with nothing linked in, so no secret a test needs can reach an answer. With an
   API provider it answers with the story in context. A `file:line` in an answer opens that code in the story.
5. **Draft, edit, post.** The draft turns each note into a comment on the lines it concerns, or into the summary.
   Code checks what GitHub will accept: every comment sits on lines in the pull request's diff, on the right side,
   with a valid range, and every note is carried somewhere; failures go back to the model, as everywhere in
   codestory. Opinions come only from your notes and your side of the conversation. If the pull request moved on
   since the story, pinned notes are carried to its new head by content. You edit, untick, choose Comment, Request
   changes or Approve, and post, or save a pending review to finish on GitHub.

## A repository

"Explain a repository" takes a GitHub link, `owner/name` or a local path, and who the story is for. The app clones
it (or uses your checkout), installs what it needs, and runs `story.py`: a Python or a TypeScript repository, told
along one run of its own tests. Notes and the assistant work as for a pull request; there is nothing to post.

## Safety

It listens on 127.0.0.1 only. Because it can post to GitHub as you, the link it prints carries a secret that becomes a
SameSite=Strict cookie; every API call needs that cookie and a custom header no cross-site form can send, and the Host
header must name this machine. A story is written by a model from a pull request, which could carry a prompt
injection: the app renders model text only through DOMPurify, under a content policy that allows no other scripts,
and the story's standalone page (`/s/<id>/`) is served sandboxed, with an opaque origin and no network access, so its
scripts can't reach the app's API.
