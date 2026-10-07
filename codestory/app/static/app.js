// codestory review: the page. Plain JavaScript; the server is codestory/app/server.py.
//
// Views: #/ (review a pull request, explain a repository, your stories), #/setup (GitHub and the model), and
// #/story/<id> (the story, read here, with the review beside it: notes, the assistant, the comments to post). Every
// piece of model-written text goes through DOMPurify; the page's policy runs no inline script.

"use strict";

// ---------------------------------------------------------------- small tools

const $ = (sel, root = document) => root.querySelector(sel);
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;  // only ever given sanitized HTML
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : String(kid));
  return el;
}
const md = (text) => DOMPurify.sanitize(marked.parse(text || ""), { FORBID_TAGS: ["style", "form", "input", "img"], FORBID_ATTR: ["style"] });
const ago = (t) => { const s = Date.now() / 1000 - t; return s < 90 ? "just now" : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 129600 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; };
const two = (n) => String(n).padStart(2, "0");
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
function debounce(fn, ms) { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; }

async function api(path, body) {
  const init = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-Codestory": "1" }, body: JSON.stringify(body) };
  const r = await fetch("/api/" + path, init);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `${r.status} ${r.statusText}`);
  return j;
}

// A POST answered with one JSON object per line, as they happen.
async function stream(path, body, onEvent) {
  const r = await fetch("/api/" + path, { method: "POST", headers: { "Content-Type": "application/json", "X-Codestory": "1" }, body: JSON.stringify(body || {}) });
  if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.error || r.statusText); }
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) { const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (line) onEvent(JSON.parse(line)); }
  }
}

const S = { session: null, story: null, data: null, sid: null, tab: "notes", picked: null, events: null };
const sidUrl = () => encodeURIComponent(S.sid);

// ---------------------------------------------------------------- the bar: the model, GitHub

async function loadSession() {
  S.session = await api("session");
  drawBar();
}

function drawBar() {
  const s = S.session;
  const right = $("#right");
  right.textContent = "";
  const ready = s.providers.filter((p) => p.ready);
  const chosen = s.providers.find((p) => p.chosen);
  const picker = h("select", { class: "picker", "aria-label": "The model that writes and answers", title: "The model that writes stories and answers questions" });
  for (const p of ready) {
    const group = h("optgroup", { label: p.name });
    const models = p.models && p.models.length ? p.models : [];
    if (!models.length || !p.model) group.append(h("option", { value: `${p.id}|`, selected: p.chosen && !p.model }, `${p.name}: its default`));
    for (const m of models) group.append(h("option", { value: `${p.id}|${m.id}`, selected: p.chosen && p.model === m.id }, m.name));
    picker.append(group);
  }
  if (!ready.length) picker.append(h("option", { value: "" }, "No model ready: open Setup"));
  picker.addEventListener("change", async () => {
    const [provider, model] = picker.value.split("|");
    if (!provider) return;
    picker.disabled = true;
    try { await api("providers", { provider, model }); await loadSession(); } catch (e) { alert(e.message); picker.disabled = false; }
  });
  const g = s.github.user;
  right.append(picker, h("a", { class: "who", href: "#/setup", title: g ? `GitHub: ${g.login}` : "Sign in to GitHub" },
    g ? [g.avatar ? h("img", { src: g.avatar, alt: "" }) : h("span", { class: "dot ok" }), h("span", {}, g.login)] : [h("span", { class: "dot bad" }), h("span", {}, "Sign in")]));
  if (chosen && !chosen.ready) right.prepend(h("a", { class: "chip red", href: "#/setup" }, `${chosen.name} isn't ready`));
}

async function route() {
  if (S.events) { S.events.close(); S.events = null; }
  closeSheet();
  const [, view, arg] = (location.hash || "#/").split("/");
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === (view || "home") || (view === "story" && a.dataset.nav === "home")));
  const root = $("#view");
  root.textContent = "";
  try {
    if (!S.session) await loadSession();
    if (view === "setup") return await viewSetup(root);
    if (view === "story" && arg) return await viewStory(root, decodeURIComponent(arg));
    return await viewHome(root);
  } catch (e) {
    root.append(h("div", { class: "page" }, h("div", { class: "note-box warn" }, e.message)));
  }
}
addEventListener("hashchange", route);

// ---------------------------------------------------------------- home

async function viewHome(root) {
  const s = S.session;
  const page = h("div", { class: "page" });
  root.append(page);
  page.append(h("section", { class: "hero" },
    h("span", { class: "eyebrow" }, "Code stories, checked against the code"),
    h("h1", {}, "Understand a change before you approve it."),
    h("p", { class: "lede" }, "codestory runs a pull request's own tests before and after the change, then tells the story of the difference, every claim linked to the line that proves it. Or point it at a repository to learn how it works.")));
  const ready = s.github.user && s.providers.some((p) => p.chosen && p.ready);
  if (!ready) page.append(h("div", { class: "note-box info" }, "First, sign in to GitHub and choose a model: ", h("a", { href: "#/setup" }, "Setup →")));

  // a pull request
  const url = h("input", { placeholder: "https://github.com/owner/repo/pull/123", "aria-label": "Pull request link" });
  const prOut = h("div");
  const look = h("button", { class: "btn", onclick: () => inspect(url.value, prOut, look) }, "Look it up");
  url.addEventListener("keydown", (e) => { if (e.key === "Enter") look.click(); });
  // a repository
  const repo = h("input", { placeholder: "https://github.com/owner/repo, owner/repo, or a local path", "aria-label": "Repository" });
  const reader = h("select", { "aria-label": "Who the story is for" },
    h("option", { value: "owner" }, "For an owner: what it guarantees, what could go wrong"),
    h("option", { value: "maintainer" }, "For a maintainer: how it works inside, where it's fragile"),
    h("option", { value: "user" }, "For a user: how to call it correctly"));
  const agree = h("input", { type: "checkbox", id: "agree-repo" });
  const repoMsg = h("div");
  const write = h("button", { class: "btn", disabled: true, onclick: async () => {
    write.disabled = true;
    try {
      const r = await api("stories", { kind: "repo", repo: repo.value, options: { reader: reader.value } });
      S.session = null;
      location.hash = `#/story/${encodeURIComponent(r.sid)}`;
    } catch (e) { repoMsg.replaceChildren(h("div", { class: "note-box warn" }, e.message)); write.disabled = false; }
  } }, "Write the story");
  agree.addEventListener("change", () => { write.disabled = !agree.checked || !repo.value.trim(); });
  repo.addEventListener("input", () => { write.disabled = !agree.checked || !repo.value.trim(); });

  page.append(h("div", { class: "grid2" },
    h("div", { class: "card action" }, h("span", { class: "label" }, "01 · Pull request"), h("h3", {}, "Review a pull request"),
      h("p", {}, "The story follows the change's own tests through the code before and after it. Then write your notes, ask questions, and post the review."),
      h("div", { class: "row" }, h("div", { class: "grow" }, url), look), prOut),
    h("div", { class: "card action" }, h("span", { class: "label" }, "02 · Repository"), h("h3", {}, "Explain a repository"),
      h("p", {}, "The story follows one real run of the code's intended use, from the input to the result, for the reader you choose."),
      repo, reader,
      h("label", { class: "row small muted", for: "agree-repo" }, agree, "I know this runs the repository's code on this machine."),
      h("div", {}, write), repoMsg)));

  const list = s.stories;
  const grid = h("div", { class: "stories" });
  list.forEach((st, i) => grid.append(storyCard(st, i === 0 && st.ready)));
  page.append(h("section", {}, h("div", { class: "section-head" }, h("span", { class: "num" }, "03"), h("h2", {}, "Your stories")),
    list.length ? grid : h("p", { class: "muted" }, "None yet. Start with a pull request or a repository above.")));

  const path = h("input", { placeholder: "a story directory review.py wrote, e.g. stories/ufo-pr313" });
  const msg = h("div");
  page.append(h("details", { class: "card" }, h("summary", {}, "Import a story you already have"),
    h("div", { class: "row", style: "margin-top:14px" }, h("div", { class: "grow" }, path),
      h("button", { class: "btn ghost", onclick: async () => { try { const r = await api("stories/import", { path: path.value }); S.session = null; location.hash = `#/story/${r.sid}`; } catch (e) { msg.replaceChildren(h("div", { class: "note-box warn" }, e.message)); } } }, "Import")), msg));
}

function storyCard(st, featured) {
  const where = st.kind === "repo" ? `Repository · ${st.repo.owner ? `${st.repo.owner}/${st.repo.name}` : st.repo.path || st.id}` : `Pull request · ${st.pr.owner}/${st.pr.name} #${st.pr.number}`;
  return h("a", { class: "card story-card" + (featured ? " featured" : ""), href: `#/story/${encodeURIComponent(st.id)}` },
    h("span", { class: "label" }, where),
    h("h3", {}, st.title || st.pr.title || st.id),
    st.premise ? h("p", {}, st.premise) : null,
    h("div", { class: "foot" },
      h("span", { class: "chip " + (st.ready ? "blue" : "plain") }, st.ready ? "Ready to read" : "Not written yet"),
      st.notes ? h("span", { class: "chip plain" }, plural(st.notes, "note")) : null,
      st.posted ? h("span", { class: "chip plain" }, plural(st.posted, "review") + " posted") : null,
      h("span", { class: "chip plain" }, ago(st.updated))));
}

async function inspect(url, out, btn) {
  out.replaceChildren(h("p", { class: "muted" }, "Reading the pull request…"));
  btn.disabled = true;
  try {
    const r = await api("pr/inspect", { url });
    const pr = r.pr;
    const box = h("div", { class: "inspect" });
    box.append(h("div", { style: "display:grid;gap:6px" }, h("span", { class: "label" }, `${pr.owner}/${pr.name} #${pr.number} · ${pr.author} · ${pr.merged ? "merged" : pr.state}`),
      h("a", { href: pr.url, target: "_blank", rel: "noopener", style: "font:600 20px/1.3 var(--display);letter-spacing:-0.02em;color:var(--ink)" }, pr.title)));
    box.append(h("dl", { class: "kv" },
      h("dt", {}, "Change"), h("dd", { class: "mono small" }, `${pr.base.sha.slice(0, 7)} → ${pr.head.sha.slice(0, 7)} · ${plural(r.files, "file")}`),
      h("dt", {}, "Its tests"), h("dd", {}, r.tests.length ? r.tests.map((t) => h("div", { class: "mono small" }, t)) : h("span", { class: "muted" }, "none: name a test file in the options, or there's no run to follow")),
      h("dt", {}, "Runs in"), h("dd", {}, h("span", { class: "mono small" }, r.checkout.path), " ",
        h("span", { class: "muted small" }, r.checkout.managed ? (r.checkout.exists ? "a clone this app keeps" : "cloned, with its dependencies installed") : "your checkout"))));
    if (r.story) box.append(h("div", { class: "note-box ok" }, "There is already a story for this pull request. ", h("a", { href: `#/story/${r.story}` }, "Open it →")));
    r.warnings.forEach((w) => box.append(h("div", { class: "note-box info" }, w)));
    const reg = { path: h("input", { value: r.checkout.managed ? "" : r.checkout.path, placeholder: "/path/to/your/checkout" }),
      link: h("input", { value: r.checkout.link || "", placeholder: "node_modules (and venv,.env if its tests need them)" }),
      pkg: h("input", { value: r.checkout.pkg || "", placeholder: "the package: . or app/ (blank: guess)" }),
      runner: h("select", {}, ["", "japa", "vitest"].map((x) => h("option", { value: x, selected: x === (r.checkout.runner || "") }, x || "Guess the test runner"))),
      specs: h("input", { placeholder: "test files, comma-separated (blank: the ones the change touches)" }) };
    const regMsg = h("div");
    box.append(h("details", {}, h("summary", {}, "Options: your own checkout, the package, the tests"),
      h("div", { style: "display:grid;gap:12px;margin-top:14px" },
        h("label", { class: "field" }, "Your checkout of this repository", reg.path),
        h("label", { class: "field" }, "What its worktrees borrow from it", reg.link),
        h("label", { class: "field" }, "Package", reg.pkg), h("label", { class: "field" }, "Test runner", reg.runner),
        h("label", { class: "field" }, "Tests", reg.specs),
        h("div", { class: "row" }, h("button", { class: "btn ghost small", onclick: async () => {
          try { await api("repos", { owner: pr.owner, name: pr.name, path: reg.path.value, link: reg.link.value, pkg: reg.pkg.value, runner: reg.runner.value }); regMsg.replaceChildren(h("span", { class: "chip green" }, "Saved: this repository's stories run in your checkout")); }
          catch (e) { regMsg.replaceChildren(h("div", { class: "note-box warn" }, e.message)); } } }, "Use my checkout"), regMsg))));
    const agree = h("input", { type: "checkbox", id: "agree-pr" });
    const go = h("button", { class: "btn blue", disabled: true, onclick: async () => {
      go.disabled = true;
      try {
        const specs = reg.specs.value.split(",").map((x) => x.trim()).filter(Boolean);
        const res = await api("stories", { url, options: { pkg: reg.pkg.value.trim(), runner: reg.runner.value, link: reg.link.value.trim(), specs, fresh: !!r.story } });
        S.session = null;
        location.hash = `#/story/${encodeURIComponent(res.sid)}`;
      } catch (e) { box.append(h("div", { class: "note-box warn" }, e.message)); go.disabled = false; }
    } }, r.story ? "Write it again" : "Write the story");
    agree.addEventListener("change", () => { go.disabled = !agree.checked; });
    box.append(h("div", { class: "row" }, h("label", { class: "row small muted", for: "agree-pr" }, agree, "I know this runs the pull request's code here."), go));
    out.replaceChildren(box);
  } catch (e) { out.replaceChildren(h("div", { class: "note-box warn" }, e.message)); }
  btn.disabled = false;
}

// ---------------------------------------------------------------- setup

async function viewSetup(root) {
  await loadSession();
  const s = S.session;
  const page = h("div", { class: "page", style: "max-width:900px" }, h("section", { class: "hero" }, h("span", { class: "eyebrow" }, "Setup"), h("h1", {}, "Sign in, and choose the model.")));
  root.append(page);

  const g = s.github;
  const gh = h("section", { class: "card", style: "display:grid;gap:14px" }, h("div", { class: "section-head", style: "margin:0" }, h("span", { class: "num" }, "01"), h("h2", {}, "GitHub")));
  if (g.method === "token") {
    gh.append(h("p", { style: "margin:0" }, g.user ? ["Signed in with GitHub as ", h("b", {}, g.user.login), "."] : "Signed in with GitHub, but the token no longer works."),
      h("div", {}, h("button", { class: "btn ghost small", onclick: async () => { await api("github/use-gh", {}); S.session = null; route(); } }, "Use the GitHub CLI login instead")));
  } else {
    gh.append(h("p", { style: "margin:0" }, g.user ? ["Using your GitHub CLI login: ", h("b", {}, g.user.login), ". Nothing more to do."] :
      g.gh && g.gh.installed ? "The GitHub CLI isn't signed in: run gh auth login in a terminal, or sign in with GitHub below." : "The GitHub CLI isn't installed: sign in with GitHub below."));
    const cid = h("input", { value: g.client_id || "", placeholder: "the client id of your GitHub OAuth App" });
    const flow = h("div");
    gh.append(h("details", { open: !g.user }, h("summary", {}, "Sign in with GitHub instead"),
      h("p", { class: "small muted" }, "Register an OAuth App (GitHub → Settings → Developer settings → OAuth Apps), tick Enable Device Flow, and paste its client id. GitHub then gives you a code to enter on github.com."),
      h("div", { class: "row" }, h("div", { class: "grow" }, cid), h("button", { class: "btn", onclick: () => deviceFlow(cid.value, flow) }, "Sign in with GitHub")), flow));
  }
  page.append(gh);

  const card = h("section", { class: "card", style: "display:grid;gap:16px" }, h("div", { class: "section-head", style: "margin:0" }, h("span", { class: "num" }, "02"), h("h2", {}, "The model")),
    h("p", { class: "muted", style: "margin:0" }, "It writes the stories, answers your questions and drafts the comments. With a Claude or ChatGPT login, the assistant can also read the code itself."));
  let chosen = (s.providers.find((p) => p.chosen) || {}).id;
  const picks = {};
  const list = h("div", { class: "providers" });
  const draw = () => list.replaceChildren(...s.providers.map((p) => {
    const sel = h("select", { "aria-label": `${p.name} model`, onclick: (e) => e.stopPropagation() });
    if (!p.models.length || !p.model) sel.append(h("option", { value: "" }, p.id === "foundry" ? "Type the deployment below" : "Its default model"));
    for (const m of p.models) sel.append(h("option", { value: m.id, selected: (picks[p.id] ?? p.model) === m.id }, m.name));
    sel.addEventListener("change", () => { picks[p.id] = sel.value; });
    return h("div", { class: "provider" + (p.id === chosen ? " chosen" : ""), onclick: () => { chosen = p.id; draw(); } },
      h("span", { class: "dot " + (p.ready ? "ok" : "bad") }), h("span", { class: "name" }, p.name, p.agent ? h("span", { class: "chip plain", style: "margin-left:8px" }, "reads the code") : null),
      h("input", { type: "radio", name: "provider", checked: p.id === chosen, "aria-label": p.name }),
      h("span", { class: "detail" }, p.ready ? p.detail : `${p.detail}. ${p.how}`),
      p.ready && p.models.length ? sel : null);
  }));
  draw();
  const endpoint = h("input", { value: s.foundry_endpoint || "", placeholder: "Foundry endpoint: https://<resource>.services.ai.azure.com" });
  const deployment = h("input", { placeholder: "Foundry deployment, if it isn't listed above" });
  const fkey = h("input", { type: "password", placeholder: "Foundry API key (blank: your az login; unchanged if left empty)" });
  const akey = h("input", { type: "password", placeholder: "Anthropic API key (unchanged if left empty)" });
  const msg = h("div");
  card.append(list, h("details", {}, h("summary", {}, "Keys and endpoints"), h("div", { style: "display:grid;gap:10px;margin-top:12px" }, endpoint, deployment, fkey, akey)),
    h("div", { class: "row" },
      h("button", { class: "btn", onclick: async () => {
        try {
          const body = { provider: chosen, model: deployment.value.trim() || picks[chosen] || (s.providers.find((p) => p.id === chosen) || {}).model || "", foundry_endpoint: endpoint.value };
          if (fkey.value) body.foundry_api_key = fkey.value;
          if (akey.value) body.anthropic_api_key = akey.value;
          s.providers = await api("providers", body);
          msg.replaceChildren(h("span", { class: "chip green" }, "Saved"));
          await loadSession(); draw();
        } catch (e) { msg.replaceChildren(h("div", { class: "note-box warn" }, e.message)); }
      } }, "Save"),
      h("button", { class: "btn ghost", onclick: async (e) => { e.target.disabled = true; msg.replaceChildren(h("span", { class: "muted" }, "Asking the model…"));
        try { const t = await api("providers/test", {}); msg.replaceChildren(h("span", { class: "chip " + (t.ok ? "green" : "red") }, t.detail)); } catch (err) { msg.replaceChildren(h("div", { class: "note-box warn" }, err.message)); }
        e.target.disabled = false; } }, "Test it"), msg));
  page.append(card, h("p", { class: "muted small" }, `Everything is kept in ${s.home}.`));
}

async function deviceFlow(clientId, out) {
  try {
    const d = await api("github/device", { action: "start", client_id: clientId.trim() });
    out.replaceChildren(h("div", { class: "card", style: "margin-top:14px;display:grid;gap:10px" },
      h("div", {}, "Enter this code at ", h("a", { href: d.verify, target: "_blank", rel: "noopener" }, d.verify), ":"),
      h("div", { class: "code-big" }, d.user_code), h("div", { class: "muted small" }, "Waiting for GitHub…")));
    let wait = d.interval * 1000;
    const until = Date.now() + d.expires * 1000;
    while (Date.now() < until) {
      await new Promise((r) => setTimeout(r, wait));
      const p = await api("github/device", { action: "poll", device_code: d.device_code });
      if (p.status === "done") { S.session = null; return route(); }
      if (p.status === "slow_down") wait += 5000;
      else if (p.status !== "pending") throw new Error(`GitHub: ${p.detail || p.status}`);
    }
    throw new Error("the code expired; start again");
  } catch (e) { out.replaceChildren(h("div", { class: "note-box warn", style: "margin-top:12px" }, e.message)); }
}

// ---------------------------------------------------------------- a story: the desk

async function viewStory(root, sid) {
  if (S.sid !== sid) { S.picked = null; S.tab = "notes"; S.data = null; }
  S.sid = sid;
  S.story = await api(`stories/${sidUrl()}`);
  const st = S.story;
  const running = st.job && ["queued", "preparing", "running"].includes(st.job.status);
  if (!st.ready || running) return viewRun(root, sid);
  S.data = await api(`stories/${sidUrl()}/data`);
  const desk = h("div", { class: "desk" });
  const reader = h("article", { class: "reader", "aria-label": "The story" });
  const panel = h("aside", { class: "panel", "aria-label": "Your review" });
  desk.append(reader, panel);
  root.append(desk);
  drawReader(reader);
  drawPanel();
}

const D = () => S.data;
const isChange = () => D().mode === "diff";
const revOf = (side) => (side === "base" ? D().repo.base : D().repo.head || D().repo.commit);
const sideOfRev = (rev) => (isChange() && rev === D().repo.base ? "base" : "head");
const fileAt = (rev, path) => D().files[`${rev}:${path}`];

function drawReader(reader) {
  const d = D(), st = S.story;
  const box = h("div", { class: "reader-in" });
  reader.replaceChildren(box);
  const where = isChange() ? `Pull request · ${d.repo.name}${d.number ? ` #${d.number}` : ""}` : `Repository · ${d.repo.name}`;
  box.append(h("header", { class: "cover" },
    h("span", { class: "eyebrow" }, `${where} · for the ${d.reader || "reader"}`),
    h("h1", {}, d.title),
    h("p", { class: "premise", html: DOMPurify.sanitize(marked.parseInline(d.premise || "")) })));
  box.append(stats());
  if (isChange() && d.verdict) box.append(h("section", { class: "verdict" }, h("span", { class: "label" }, "The verdict"), h("p", { html: DOMPurify.sanitize(marked.parseInline(d.verdict)) })));
  box.append(h("nav", { class: "contents", "aria-label": "Chapters" }, d.chapters.map((c) => h("a", { href: "#", onclick: (e) => { e.preventDefault(); $(`#ch-${c.n}`).scrollIntoView({ block: "start" }); } },
    h("span", { class: "num" }, two(c.n)), h("span", {}, c.title), c.kind ? h("span", { class: "chip " + (c.kind === "changed" ? "blue" : "plain") }, c.kind === "changed" ? "Changed" : "Unchanged") : h("span")))));
  for (const c of d.chapters) box.append(chapterEl(c));
  box.append(evidence());
  box.append(h("footer", { class: "row small muted", style: "justify-content:space-between;border-top:1px solid var(--line);padding-top:20px" },
    h("span", {}, isChange() ? `Base ${d.repo.base.slice(0, 7)} → head ${d.repo.head.slice(0, 7)}` : `At ${d.repo.commit.slice(0, 7)}`),
    h("span", { class: "row" }, h("a", { href: `/s/${sidUrl()}/`, target: "_blank", rel: "noopener" }, "The page on its own ↗"),
      st.pr && st.pr.url ? h("a", { href: st.pr.url, target: "_blank", rel: "noopener" }, "On GitHub ↗") : h("a", { href: d.repo.url, target: "_blank", rel: "noopener" }, "On GitHub ↗"))));
  reader.addEventListener("mouseup", (e) => selectionNote(reader, e));
}

function stats() {
  const d = D();
  const items = [];
  if (isChange()) {
    const flipped = d.tests.filter((t) => t.before !== "pass" && t.after === "pass").length;
    const holding = d.chapters.filter((c) => c.checked && c.checked.head === "pass" && (c.kind === "preserved" ? c.checked.base === "pass" : c.checked.base !== "pass")).length;
    items.push([flipped, flipped === 1 ? "test now passes that failed before" : "tests now pass that failed before"]);
    items.push([Object.keys(d.changed || {}).length, "files changed"]);
    items.push([d.unexercised.length, d.unexercised.length === 1 ? "change no test reaches" : "changes no test reaches", d.unexercised.length > 0]);
    items.push([`${holding}/${d.chapters.length}`, "chapters whose proof holds on both sides"]);
  } else {
    const steps = d.flow.filter((i) => i.kind === "step").length;
    items.push([d.chapters.length, "chapters"]);
    items.push([steps, "calls on the map of the run"]);
    items.push([new Set(Object.keys(d.files).map((k) => k.split(":").slice(1).join(":"))).size, "files the story cites"]);
  }
  return h("section", { class: "stats" }, items.map(([n, label, alert]) => h("div", { class: "stat" + (alert ? " alert" : "") }, h("b", {}, String(n)), h("span", {}, label))));
}

// A chapter's markdown without what the page draws itself: its heading and the before/after (or enters/leaves) lines.
function chapterBody(text) {
  const blocks = (text || "").replace(/^#\s+Chapter[^\n]*\n/, "").split(/\n\s*\n/);
  return blocks.filter((b) => !/^\s*>\s*\*\*(Before|After|Enters as|Leaves as):?\*\*/i.test(b)).join("\n\n");
}

function chapterEl(c) {
  const sec = h("section", { class: "chapter", id: `ch-${c.n}` });
  sec.append(h("div", { class: "chapter-head" },
    h("div", { class: "top" }, h("span", { class: "num" }, `Chapter ${two(c.n)}`), c.kind ? h("span", { class: "chip " + (c.kind === "changed" ? "blue" : "plain") }, c.kind === "changed" ? "Changed" : "Unchanged") : null),
    h("h2", {}, c.title)));
  const pair = isChange() ? [["before", "Before", c.data_in], ["after", "After", c.data_out]] : [["before", "Enters as", c.data_in], ["after", "Leaves as", c.data_out]];
  sec.append(h("div", { class: "ba" }, pair.map(([cls, label, text]) => h("div", { class: cls }, h("span", { class: "label" }, label), h("span", { html: DOMPurify.sanitize(marked.parseInline(text || "")) })))));
  if (c.run && c.run.length) {
    sec.append(h("div", { class: "run" }, h("span", { class: "label" }, "What the run shows"), c.run.map((m) => {
      const args = Object.entries(m.args || {}).map(([k, v]) => v).join(", ");
      return h("div", { class: "run-row" }, h("span", { class: "call" }, `${m.fn}(${args})`),
        h("span", { class: "vals" }, m.before ? h("span", { class: "was" }, m.before) : null, m.after ? h("span", { class: "now" }, m.after) : null,
          m.mark === "+" ? h("span", { class: "muted" }, "only after the change") : m.mark === "-" ? h("span", { class: "muted" }, "only before the change") : null));
    })));
  }
  const prose = h("div", { class: "prose", html: md(chapterBody(c.md)) });
  dressProse(prose, c.n);
  sec.append(prose);
  sec.append(proofEl(c));
  return sec;
}

function dressProse(prose, n) {
  for (const q of prose.querySelectorAll("blockquote")) {
    const lead = q.querySelector("p > strong:first-child");
    const m = lead && lead.textContent.match(/^for the ([\w -]+):?$/i);
    if (!m) continue;
    lead.remove();
    const callout = h("div", { class: "callout" }, h("span", { class: "hand" }, `for the ${m[1].toLowerCase()} →`));
    callout.append(...q.childNodes);
    q.replaceWith(callout);
  }
  const url = D().repo.url.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const cite = new RegExp(`^${url}/blob/([0-9a-f]+)/([^#]+)#L(\\d+)(?:-L(\\d+))?`);
  for (const a of prose.querySelectorAll("a[href]")) {
    const m = a.getAttribute("href").match(cite);
    if (!m) { a.target = "_blank"; a.rel = "noopener"; continue; }
    const rev = [D().repo.base, D().repo.head, D().repo.commit].find((r) => r && (r.startsWith(m[1]) || m[1].startsWith(r))) || m[1];
    a.className = "cite";
    a.title = isChange() ? (sideOfRev(rev) === "base" ? "the code before the change" : "the code after the change") : "the code";
    a.addEventListener("click", (e) => { e.preventDefault(); togglePeek(a, { path: m[2], side: sideOfRev(rev), start: +m[3], end: +(m[4] || m[3]) }, n); });
  }
}

function proofEl(c) {
  if (!c.proof && !c.checked) return h("div");
  const k = c.checked;
  let chip = null;
  if (k && k.head) {
    const ok = k.head === "pass" && (c.kind === "preserved" ? k.base === "pass" : k.base !== "pass");
    const what = c.kind === "preserved" ? "passes before and after the change" : "fails before the change, passes after it";
    chip = h("span", { class: "chip " + (ok ? "green" : "red") }, ok ? `Proof holds: ${what}` : `Proof: after ${k.head}; before ${k.base}`);
  } else if (c.proof) chip = h("span", { class: "chip plain" }, "Proof");
  return h("div", { class: "proof" }, chip, c.proof ? h("details", {}, h("summary", { class: "small" }, "The proof, a test you can run"), h("pre", {}, c.proof)) : null);
}

function evidence() {
  const d = D();
  if (!isChange()) {
    return d.scenario ? h("section", { style: "display:grid;gap:14px" }, h("div", { class: "section-head", style: "margin:0" }, h("span", { class: "num" }, "↳"), h("h2", { style: "font-size:26px" }, "The run the story follows")),
      h("details", { class: "card" }, h("summary", {}, "The intended use, as it was run"), h("pre", { class: "prose", style: "margin-top:12px" }, d.scenario))) : h("div");
  }
  const pill = (s) => h("span", { class: "chip " + (s === "pass" ? "green" : /^(fail|runaway|unfinished)/.test(s) ? "red" : "plain") }, s.length > 40 ? s.slice(0, 39) + "…" : s);
  return h("section", { style: "display:grid;gap:18px" },
    h("div", { class: "section-head", style: "margin:0" }, h("span", { class: "num" }, "↳"), h("h2", { style: "font-size:26px" }, "The evidence")),
    h("div", { class: "card", style: "padding:8px 20px" }, h("div", { class: "contents", style: "border-top:0" }, d.tests.map((t) => h("div", { style: "display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line-soft)" },
      h("span", { class: "small" }, t.test), pill(t.before), pill(t.after))))),
    d.unexercised.length ? h("div", { class: "card", style: "display:grid;gap:10px" }, h("span", { class: "label" }, "Changed, but no test reaches it"),
      d.unexercised.map((u) => h("div", {}, h("code", {}, u.function), " ", h("span", { class: "muted" }, u.check)))) : null);
}

// ---- code: a peek under the passage, or the sheet for a whole file

function codeLines(path, side, start, end, around) {
  const rev = revOf(side);
  const src = fileAt(rev, path);
  if (src === undefined) return h("div", { class: "lines" }, h("div", { class: "muted small", style: "padding:10px 16px" }, "This file isn't part of the story's snapshot."));
  const all = src.split("\n");
  const from = around == null ? 1 : Math.max(1, start - around), to = around == null ? all.length : Math.min(all.length, end + around);
  const changed = isChange() && D().changed[path] ? new Set(D().changed[path][side]) : null;
  const box = h("div", { class: "lines" });
  for (let i = from; i <= to; i++) {
    box.append(h("div", { class: "ln" + (changed && changed.has(i) ? " chg" : "") + (i >= start && i <= end ? " hl" : ""), "data-n": i }, h("span", {}, String(i)), h("span", {}, all[i - 1] || " ")));
  }
  return box;
}

function otherSide(a) {
  const to = a.side === "head" ? "base" : "head";
  if (fileAt(revOf(to), a.path) === undefined) return null;
  const fwd = (D().maps || {})[a.path] || {};
  const map = to === "base" ? fwd : Object.fromEntries(Object.entries(fwd).map(([k, v]) => [v, +k]));
  const near = (n) => { for (let k = n; k > 0; k--) if (map[k] !== undefined) return map[k] + (n - k); return n; };
  const start = near(a.start);
  return { path: a.path, side: to, start, end: Math.max(start, near(a.end)) };
}

function codeHead(a, onSide, extra) {
  const other = isChange() ? otherSide(a) : null;
  const lines = a.start === a.end ? `line ${a.start}` : `lines ${a.start}–${a.end}`;
  return h("div", { class: "peek-head" },
    h("span", { class: "where" }, `${a.path} · ${lines}`),
    h("span", { class: "tools" },
      isChange() ? h("span", { class: "side-toggle" },
        h("button", { class: a.side === "base" ? "on" : "", disabled: a.side !== "base" && !other, onclick: () => a.side !== "base" && other && onSide(other) }, "Before"),
        h("button", { class: a.side === "head" ? "on" : "", disabled: a.side !== "head" && !other, onclick: () => a.side !== "head" && other && onSide(other) }, "After")) : null,
      ...extra));
}

function togglePeek(link, a, chapter) {
  const host = link.closest("p, li, blockquote, .callout") || link;
  const open = host.nextElementSibling && host.nextElementSibling.classList.contains("peek") ? host.nextElementSibling : null;
  document.querySelectorAll("a.cite.on").forEach((x) => x.classList.remove("on"));
  if (open && open.dataset.key === JSON.stringify(a)) { open.remove(); return; }
  if (open) open.remove();
  link.classList.add("on");
  const draw = (cur) => {
    const peek = h("div", { class: "peek", "data-key": JSON.stringify(a) },
      codeHead(cur, (o) => peek.replaceWith(draw(o)), [
        h("button", { class: "pin", onclick: () => pick({ anchor: { path: cur.path, side: cur.side, start: cur.start, end: cur.end }, quote: link.textContent, chapter }) }, "Note this"),
        h("button", { class: "pin", onclick: () => openSheet(cur) }, "Whole file"),
        h("a", { class: "pin", href: `${D().repo.url}/blob/${revOf(cur.side)}/${cur.path}#L${cur.start}${cur.end !== cur.start ? "-L" + cur.end : ""}`, target: "_blank", rel: "noopener" }, "GitHub ↗")]),
      codeLines(cur.path, cur.side, cur.start, cur.end, 5));
    return peek;
  };
  host.after(draw(a));
}

function openSheet(a) {
  closeSheet();
  const sheet = h("div", { class: "sheet", role: "dialog", "aria-label": a.path });
  const fill = (cur) => {
    sheet.replaceChildren(codeHead(cur, fill, [
      h("button", { class: "pin", onclick: () => pick({ anchor: { path: cur.path, side: cur.side, start: cur.start, end: cur.end }, quote: `${cur.path}:${cur.start}` }) }, "Note this"),
      h("button", { class: "pin", onclick: closeSheet, "aria-label": "Close" }, "Close ✕")]),
      codeLines(cur.path, cur.side, cur.start, cur.end, null));
    const row = sheet.querySelector(`.ln[data-n="${cur.start}"]`);
    if (row) row.scrollIntoView({ block: "center" });
  };
  document.body.append(sheet);
  fill(a);
  sheet.tabIndex = -1;
  sheet.focus();
}
function closeSheet() { document.querySelectorAll(".sheet").forEach((s) => s.remove()); }
addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });

// Select text in the story to note it.
function selectionNote(reader, e) {
  document.querySelectorAll(".float-note").forEach((b) => b.remove());
  if (e.target.closest("button, a, .peek")) return;
  const sel = getSelection();
  const text = sel.toString().trim();
  if (text.length < 3 || !sel.rangeCount || !reader.contains(sel.anchorNode)) return;
  const rect = sel.getRangeAt(0).getBoundingClientRect(), box = reader.getBoundingClientRect();
  const ch = sel.anchorNode.parentElement && sel.anchorNode.parentElement.closest(".chapter");
  const btn = h("button", { class: "btn small float-note", style: `left:${rect.left - box.left + rect.width / 2}px;top:${rect.top - box.top + reader.scrollTop - 8}px`,
    onmousedown: (ev) => ev.preventDefault(), onclick: () => { btn.remove(); pick({ anchor: null, quote: text.slice(0, 600), chapter: ch ? +ch.id.slice(3) : null }); } }, "Note this");
  reader.append(btn);
}

function pick(p) {
  S.picked = p;
  S.tab = "notes";
  drawPanel();
  const ta = $(".panel textarea");
  if (ta) ta.focus();
}

// ---------------------------------------------------------------- the review panel

function drawPanel() {
  const panel = $(".panel");
  if (!panel) return;
  const st = S.story;
  const tabs = [["notes", `Notes${st.notes.length ? ` · ${st.notes.length}` : ""}`], ["ask", "Ask"]];
  if (st.kind !== "repo") tabs.push(["review", "Review"]);
  if (!tabs.some(([id]) => id === S.tab)) S.tab = "notes";
  const body = h("div", { class: "pane" });
  panel.replaceChildren(
    h("div", { class: "tabs", role: "tablist" }, tabs.map(([id, label]) => h("button", { class: "tab" + (S.tab === id ? " on" : ""), role: "tab", "aria-selected": S.tab === id,
      onclick: () => { S.tab = id; drawPanel(); } }, label))),
    body);
  const desk = $(".desk");
  if (desk) desk.classList.toggle("wide", S.tab === "review" && !!st.draft);
  ({ notes: drawNotes, ask: drawAsk, review: drawReview })[S.tab](body);
}

const pinLabel = (a) => `${a.path}:${a.start}${a.end && a.end !== a.start ? "–" + a.end : ""}${isChange() ? (a.side === "base" ? " · before" : " · after") : ""}`;

// ---- notes

function drawNotes(body) {
  const st = S.story;
  const p = S.picked;
  const text = h("textarea", { rows: 4, placeholder: p ? "What do you think about this?" : "A concern, a question for the author, something to change, or why it's fine." });
  const pinIt = h("input", { type: "checkbox", checked: !!(p && p.anchor) });
  if (p) {
    body.append(h("div", { class: "picked" },
      h("div", { class: "row", style: "justify-content:space-between" }, h("span", { class: "label" }, "Your note is about"), h("button", { class: "link small", onclick: () => { S.picked = null; drawPanel(); } }, "clear")),
      p.anchor ? h("button", { class: "pin", style: "justify-self:start", onclick: () => openSheet(p.anchor) }, pinLabel(p.anchor)) : p.chapter ? h("span", {}, `Chapter ${two(p.chapter)}`) : null,
      p.quote ? h("div", { class: "q" }, p.quote) : null,
      p.anchor && st.kind !== "repo" ? h("label", { class: "row small" }, pinIt, "Put the comment on these lines") : null));
  } else {
    body.append(h("p", { class: "muted small", style: "margin:0" }, "Click an underlined passage in the story to see its code, then Note this. Or select any text."));
  }
  const add = h("button", { class: "btn small", onclick: async () => {
    if (!text.value.trim()) return text.focus();
    const q = S.picked || {};
    const note = { text: text.value, anchor: pinIt.checked && q.anchor ? q.anchor : null, chapter: q.chapter || null, quote: q.quote || null };
    st.notes = await api(`stories/${sidUrl()}/notes`, { action: "add", note });
    S.picked = null;
    drawPanel();
  } }, "Add note");
  text.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) add.click(); });
  body.append(text, h("div", { class: "row", style: "justify-content:space-between" }, add, st.kind !== "repo" ? h("span", { class: "muted small" }, "Your notes become the review.") : null));
  for (const n of [...st.notes].reverse()) {
    const t = h("div", { class: "text" }, n.text);
    body.append(h("div", { class: "note" }, t,
      h("div", { class: "meta" }, h("span", { class: "mono" }, `#${n.id}`),
        n.anchor ? h("button", { class: "pin", onclick: () => openSheet(n.anchor) }, pinLabel(n.anchor)) : h("span", {}, n.chapter ? `Chapter ${two(n.chapter)}` : "The whole change"),
        h("button", { class: "link", onclick: () => editNote(n, t) }, "Edit"),
        h("button", { class: "link", onclick: async () => { st.notes = await api(`stories/${sidUrl()}/notes`, { action: "delete", id: n.id }); drawPanel(); } }, "Delete"))));
  }
}

function editNote(n, el) {
  const ta = h("textarea", { rows: 4 }, n.text);
  const save = h("button", { class: "btn small", onclick: async () => { S.story.notes = await api(`stories/${sidUrl()}/notes`, { action: "edit", note: { id: n.id, text: ta.value } }); drawPanel(); } }, "Save");
  el.replaceWith(h("div", { style: "display:grid;gap:8px" }, ta, h("div", {}, save)));
  ta.focus();
}

// ---- the assistant

function drawAsk(body) {
  const chat = h("div", { class: "chat" });
  const turns = (S.story.chat && S.story.chat.turns) || [];
  if (!turns.length) chat.append(h("p", { class: "muted small", style: "margin:0" }, "Ask about the story or the code: why a branch matters, what a test proves, what happens for another input. The assistant reads the story and the code."));
  for (const t of turns) chat.append(turnEl(t.role, t.text));
  const q = h("textarea", { rows: 3, placeholder: "Ask a question…" });
  const send = h("button", { class: "btn small", onclick: () => ask(q, chat, send) }, "Ask");
  q.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send.click(); } });
  body.append(chat, h("div", { class: "composer" }, q, h("div", { class: "row", style: "justify-content:space-between" }, send,
    turns.length ? h("button", { class: "link small", onclick: async () => { S.story.chat = await api(`stories/${sidUrl()}/chat/reset`, {}); drawPanel(); } }, "Start over") : null)));
  setTimeout(() => { body.scrollTop = body.scrollHeight; }, 0);
}

function turnEl(role, text) {
  const b = h("div", { class: "body" + (role === "assistant" ? " md" : "") });
  if (role === "assistant") { b.innerHTML = md(text); linkify(b); } else b.textContent = text;
  return h("div", { class: "turn " + role }, b);
}

// file:line in an answer becomes a button that opens the code.
function linkify(root) {
  const re = /([\w@./-]+\.(?:ts|tsx|mts|js|mjs|vue|py|json))(?::(\d+)(?:-(\d+))?)/g;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) { re.lastIndex = 0; if (re.test(walker.currentNode.nodeValue)) nodes.push(walker.currentNode); }
  for (const node of nodes) {
    const frag = document.createDocumentFragment();
    const s = node.nodeValue;
    let last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(s))) {
      frag.append(s.slice(last, m.index));
      const near = s.slice(m.index, m.index + 120).toLowerCase();
      const side = isChange() && /\b(base|before)\b/.test(near) && !/\b(head|after)\b/.test(near) ? "base" : "head";
      const path = resolvePath(m[1]);
      const a = { path, start: +m[2], end: +(m[3] || m[2]), side };
      frag.append(path ? h("button", { class: "codelink", onclick: () => openSheet(a) }, m[0]) : m[0]);
      last = m.index + m[0].length;
    }
    frag.append(s.slice(last));
    node.replaceWith(frag);
  }
}

// A path as the assistant wrote it ("src/utils.ts" or "utils.ts") → the story's file it names.
function resolvePath(p) {
  const paths = [...new Set(Object.keys(D().files).map((k) => k.slice(k.indexOf(":") + 1)))];
  return paths.find((x) => x === p) || paths.find((x) => x.endsWith("/" + p)) || null;
}

async function ask(q, chat, send) {
  const text = q.value.trim();
  if (!text) return;
  q.value = "";
  send.disabled = true;
  chat.append(turnEl("user", text));
  const activity = h("div", { class: "activity" }, "Thinking…");
  const live = h("div", { class: "turn assistant" }, activity);
  chat.append(live);
  live.scrollIntoView({ block: "end" });
  let answer = "";
  try {
    await stream(`stories/${sidUrl()}/chat`, { message: text }, (e) => {
      if (e.type === "tool") activity.append(h("div", {}, `${e.name} ${e.detail}`));
      else if (e.type === "done") answer = e.text;
      else if (e.type === "error") answer = `(error: ${e.text})`;
      live.scrollIntoView({ block: "end" });
    });
  } catch (e) { answer = `(error: ${e.message})`; }
  live.replaceWith(turnEl("assistant", answer));
  S.story.chat = (await api(`stories/${sidUrl()}`)).chat;
  send.disabled = false;
}

// ---- the review: draft from the notes, edit, post

function drawReview(body) {
  const st = S.story;
  const d = st.draft;
  for (const p of st.posted || []) body.append(h("div", { class: "note-box ok" }, `Posted a ${p.event ? p.event.toLowerCase().replace("_", " ") : "pending"} review with ${plural(p.comments, "comment")}. `, p.url ? h("a", { href: p.url, target: "_blank", rel: "noopener" }, "See it on GitHub ↗") : null));
  const steps = h("div", { class: "activity" });
  const go = h("button", { class: d ? "btn ghost small" : "btn", disabled: !st.notes.length, onclick: async () => {
    go.disabled = true;
    steps.replaceChildren(h("div", {}, "Starting…"));
    try {
      await stream(`stories/${sidUrl()}/draft`, {}, (e) => {
        if (e.type === "step") steps.append(h("div", {}, e.text));
        else if (e.type === "done") { st.draft = e.draft; drawPanel(); }
        else if (e.type === "error") steps.replaceChildren(h("div", { class: "note-box warn" }, e.text));
      });
    } catch (e) { steps.replaceChildren(h("div", { class: "note-box warn" }, e.message)); }
    go.disabled = false;
  } }, d ? "Draft again from my notes" : `Draft the review from ${plural(st.notes.length, "note")}`);
  if (!d) {
    body.append(h("p", { class: "muted", style: "margin:0" }, st.notes.length ? "Each note becomes a comment on the lines it's about, or a line in the summary. Opinions come only from your notes; nothing is posted until you say so." : "Write some notes first: the review comes from your notes."), h("div", {}, go), steps);
    return;
  }
  if (d.moved) body.append(h("div", { class: "note-box info" }, `The pull request moved on since the story; these comments sit on its current head (${d.head.slice(0, 7)}).`));
  const summary = h("textarea", { rows: 4 }, d.summary);
  const event = h("select", { style: "width:auto" }, [["COMMENT", "Comment"], ["REQUEST_CHANGES", "Request changes"], ["APPROVE", "Approve"]].map(([v, l]) => h("option", { value: v, selected: d.event === v }, l)));
  const errs = h("div", { style: "display:grid;gap:8px" });
  const showErrors = () => errs.replaceChildren(...(st.draft.errors || []).map((e) => h("div", { class: "note-box warn small" }, e)));
  const save = debounce(async () => {
    const edits = d.comments.map((c) => ({ body: c.body, include: c.include !== false }));
    const nd = await api(`stories/${sidUrl()}/draft/edit`, { summary: summary.value, event: event.value, comments: edits });
    st.draft.errors = nd.errors;
    showErrors();
  }, 500);
  summary.addEventListener("input", save);
  event.addEventListener("change", save);
  body.append(h("label", { class: "field" }, "The summary", summary));
  d.comments.forEach((c) => body.append(commentEl(c, save)));
  if (!d.comments.length) body.append(h("p", { class: "muted small", style: "margin:0" }, "No line comments: everything went into the summary."));
  showErrors();
  const result = h("div");
  const post = async (pending) => {
    const n = d.comments.filter((c) => c.include !== false).length;
    if (!pending && !confirm(`Post this review to ${st.pr.owner}/${st.pr.name} #${st.pr.number}: ${event.selectedOptions[0].textContent.toLowerCase()}, ${plural(n, "comment")}?`)) return;
    try {
      const r = await api(`stories/${sidUrl()}/post`, { event: event.value, pending });
      S.story = await api(`stories/${sidUrl()}`);
      drawPanel();
      if (r.url) window.open(r.url, "_blank", "noopener");
    } catch (e) { result.replaceChildren(h("div", { class: "note-box warn" }, e.message)); }
  };
  body.append(errs,
    h("div", { class: "row" }, h("span", { class: "label" }, "As"), event),
    h("div", { class: "row" }, h("button", { class: "btn blue", onclick: () => post(false) }, "Post review"),
      h("button", { class: "btn ghost", onclick: () => post(true), title: "Creates the review on GitHub without submitting it: finish it there." }, "Save as pending")),
    result,
    h("div", { class: "row", style: "justify-content:space-between" }, h("span", { class: "muted small" }, `Drafted ${ago(d.drafted)}${d.repairs ? `, after ${plural(d.repairs, "repair")}` : ""}.`), go),
    steps);
}

function commentEl(c, save) {
  const ta = h("textarea", { rows: Math.min(14, 3 + Math.ceil(c.body.length / 60)) }, c.body);
  const inc = h("input", { type: "checkbox", checked: c.include !== false, "aria-label": "include this comment" });
  const el = h("div", { class: "comment" + (c.include === false ? " off" : "") });
  ta.addEventListener("input", () => { c.body = ta.value; save(); });
  inc.addEventListener("change", () => { c.include = inc.checked; el.classList.toggle("off", !inc.checked); save(); });
  const a = { path: c.path, start: c.start_line || c.line, end: c.line, side: c.side === "LEFT" ? "base" : "head" };
  el.append(
    h("div", { class: "comment-head" }, h("button", { class: "link where", onclick: () => openSheet(a), title: "show the whole file" }, `${c.path}:${c.start_line ? c.start_line + "–" : ""}${c.line}`),
      h("span", { class: "chip " + (c.side === "RIGHT" ? "blue" : "red") }, c.side === "RIGHT" ? "After" : "Before")),
    h("div", { class: "hunk" }, (c.context || []).map((r) => h("div", { class: (r.kind === "+" ? "k-add" : r.kind === "-" ? "k-del" : "") + (r.hit ? " hit" : "") },
      h("span", {}, r.old ?? ""), h("span", {}, r.new ?? ""), h("span", {}, r.kind), h("span", {}, r.text)))),
    ta,
    h("div", { class: "comment-foot" }, h("label", { class: "row" }, inc, "Include"), h("span", {}, c.notes.length ? `From ${c.notes.map((n) => "#" + n).join(", ")}` : "")));
  return el;
}

// ---------------------------------------------------------------- the run, live

const STAGES = {
  pr: [["preparing", "Get the code"], ["diff", "Run its tests, before and after"], ["outline", "Plan the story"], ["chapters", "Write and check"], ["render", "Make the page"]],
  repo: [["preparing", "Get the code"], ["scenario", "Run its intended use"], ["outline", "Plan the story"], ["chapters", "Write and check"], ["render", "Make the page"]],
};

function viewRun(root, sid) {
  const st = S.story;
  const page = h("div", { class: "page", style: "gap:28px" });
  root.append(page);
  const pr = st.pr || {};
  const name = st.kind === "repo" ? (st.repo.owner ? `${st.repo.owner}/${st.repo.name}` : st.repo.path) : `${pr.owner}/${pr.name} #${pr.number}`;
  page.append(h("section", { class: "hero" }, h("span", { class: "eyebrow" }, `${st.kind === "repo" ? "Repository" : "Pull request"} · ${name}`),
    h("h1", { style: "font-size:clamp(32px,4vw,48px)" }, st.kind === "repo" ? "Writing the story of this repository" : pr.title || "Writing the story")));
  const stages = STAGES[st.kind === "repo" ? "repo" : "pr"];
  const steps = h("div", { class: "steps" });
  const status = h("div");
  const log = h("pre", { class: "log", "aria-label": "log" });
  const cancel = h("button", { class: "btn danger small", onclick: async () => { cancel.disabled = true; await api(`stories/${sidUrl()}/cancel`, {}); } }, "Cancel");
  page.append(steps, status, h("div", { class: "row" }, cancel, h("a", { href: "#/" }, "← Your stories")), log);
  let now = st.job ? (st.job.status === "preparing" ? "preparing" : st.job.stage) : "";
  const draw = (done) => {
    const at = stages.findIndex(([k]) => now && now.startsWith(k));
    steps.replaceChildren(...stages.map(([k, label], i) => h("div", { class: "step" + (done || i < at ? " done" : i === at ? " now" : "") }, h("span", { class: "num" }, done || i < at ? "✓" : two(i + 1)), h("b", {}, label))));
  };
  draw(false);
  const es = new EventSource(`/api/stories/${sidUrl()}/events`);
  S.events = es;
  es.onmessage = (m) => {
    const e = JSON.parse(m.data);
    if (e.type === "line") {
      const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
      log.append(e.line + "\n");
      if (e.stage) now = e.stage;
      draw(false);
      if (stick) log.scrollTop = log.scrollHeight;
    } else if (e.type === "status") {
      if (e.status === "preparing") { now = "preparing"; draw(false); }
      if (e.status === "done") { es.close(); draw(true); status.replaceChildren(h("span", { class: "chip green" }, "Written. Opening it…")); setTimeout(route, 900); }
      else if (e.status === "failed") { es.close(); cancel.remove(); status.replaceChildren(h("div", { class: "note-box warn" }, `It stopped: ${e.error || "see the log"}`)); }
      else if (e.status === "cancelled") { es.close(); cancel.remove(); status.replaceChildren(h("div", { class: "note-box info" }, "Cancelled.")); }
      else if (e.status === "idle") { es.close(); cancel.remove(); if (!st.ready) status.replaceChildren(h("div", { class: "note-box info" }, "Nothing is being written for this story right now.")); }
    }
  };
}

route();
