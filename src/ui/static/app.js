const app = document.getElementById("app");

function route() {
  const hash = location.hash.slice(1);
  const run = hash.match(/^\/run\/(.+)$/);
  const memo = hash.match(/^\/memo\/(.+)$/);
  if (run) return renderRun(decodeURIComponent(run[1]));
  if (memo) return renderMemo(decodeURIComponent(memo[1]));
  return renderHome();
}

async function renderHome() {
  const rows = await (await fetch("/api/memos")).json();
  app.innerHTML = `
    <h1>Look up a company</h1>
    <p class="lead">Type a name or ticker. For a United States filer the filings are pulled, the numbers are checked, and a memo is written. One company at a time.</p>
    <form class="search" id="lookup">
      <input name="q" placeholder="NVIDIA" autocomplete="off" autofocus>
      <button type="submit">Write memo</button>
    </form>
    <h2>Memos</h2>
    <ul class="list">${rows.length ? rows.map(row).join("") : "<li class='meta'>None yet.</li>"}</ul>
  `;
  document.getElementById("lookup").addEventListener("submit", (event) => {
    event.preventDefault();
    const q = new FormData(event.target).get("q").trim();
    if (q) location.hash = `/run/${encodeURIComponent(q)}`;
  });
}

function row(item) {
  const when = item.timestamp.replace("T", " ").slice(0, 16);
  const action = item.action ? item.action : "";
  return `<li><a href="#/memo/${encodeURIComponent(item.entry_id)}">
    <span class="ticker">${escapeHtml(item.ticker)}</span>
    <span class="badge ${escapeHtml(item.conclusion)}">${escapeHtml(item.conclusion)}</span>
    <span class="when">${escapeHtml(when)}</span>
    <span class="act">${escapeHtml(action)}</span>
  </a></li>`;
}

function renderRun(query) {
  app.innerHTML = `
    <p class="busy">Writing a memo for ${escapeHtml(query)}…</p>
    <p class="lead">The model is paced so it stays inside a free-tier limit. A first run often takes several minutes. Keep this tab open.</p>
    <pre class="log" id="log"></pre>
    <p class="error" id="err" hidden></p>
  `;
  const log = document.getElementById("log");
  const err = document.getElementById("err");
  const source = new EventSource(`/api/run?q=${encodeURIComponent(query)}`);
  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "log") {
      log.textContent += (log.textContent ? "\n" : "") + data.text;
      log.scrollTop = log.scrollHeight;
    } else if (data.type === "done") {
      source.close();
      location.hash = `/memo/${encodeURIComponent(data.entry_id)}`;
    } else if (data.type === "error") {
      source.close();
      err.hidden = false;
      err.textContent = data.message;
    }
  };
  source.onerror = () => {
    source.close();
    err.hidden = false;
    err.textContent = "The connection dropped before the memo finished.";
  };
}

async function renderMemo(entryId) {
  const res = await fetch(`/api/memos/${encodeURIComponent(entryId)}`);
  if (!res.ok) {
    app.innerHTML = `<p class="error">No memo ${escapeHtml(entryId)}</p>`;
    return;
  }
  const item = await res.json();
  const html = marked.parse(item.markdown, { gfm: true });
  const past = item.actions.map((a) =>
    `<li>${escapeHtml(a.recorded_at.replace("T", " ").slice(0, 16))} — ${escapeHtml(a.action)}: ${escapeHtml(a.reason)}</li>`
  ).join("");
  app.innerHTML = `
    <p class="meta">${escapeHtml(item.listing)} · ${escapeHtml(item.timestamp.replace("T", " ").slice(0, 16))} UTC
      · <span class="badge ${escapeHtml(item.conclusion)}">${escapeHtml(item.conclusion)}</span></p>
    <form class="actions" id="act">
      <select name="action">
        <option value="watched">Watched</option>
        <option value="skipped">Skipped</option>
        <option value="bought">Bought</option>
      </select>
      <input name="reason" required placeholder="Why, in a sentence">
      <button type="submit">Record</button>
      <a class="ghost" href="#/">Back</a>
    </form>
    ${past ? `<ul class="list">${past}</ul>` : ""}
    <article class="memo">${html}</article>
  `;
  document.getElementById("act").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.target));
    const posted = await fetch(`/api/memos/${encodeURIComponent(entryId)}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!posted.ok) {
      alert((await posted.json()).detail || "Could not record");
      return;
    }
    renderMemo(entryId);
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

window.addEventListener("hashchange", route);
route();
