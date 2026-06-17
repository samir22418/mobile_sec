from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/admin", response_class=HTMLResponse)
def admin_console() -> str:
    return ADMIN_HTML


ADMIN_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AEGIS Admin</title>
  <style>
    :root {
      color-scheme: dark;
      --bg:      #080D13;
      --surface: #111922;
      --surface2: #182535;
      --ink:     #F4F8FB;
      --muted:   #8FA0B2;
      --line:    #203040;
      --blue:    #64D2FF;
      --violet:  #A78BFA;
      --green:   #46D39A;
      --red:     #FF6B6B;
      --yellow:  #F4B740;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(ellipse 80% 50% at 20% -10%, rgba(100,210,255,.06) 0%, transparent 60%),
                  linear-gradient(180deg, #080D13 0%, #111922 44%, #080D12 100%);
      min-height: 100vh;
      color: var(--ink);
      font-family: Inter, "Segoe UI", system-ui, sans-serif;
      letter-spacing: 0;
    }
    header {
      padding: 24px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(13,20,28,.92);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      gap: 14px;
    }
    header svg { flex-shrink: 0; }
    header div { flex: 1; }
    h1 {
      margin: 0;
      font-size: 26px;
      line-height: 1.2;
      background: linear-gradient(90deg, #64D2FF, #A78BFA);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    header p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto 48px;
      display: grid;
      gap: 18px;
    }
    section {
      background: rgba(17,25,34,.84);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 4px 24px rgba(0,0,0,.45);
    }
    h2 {
      margin: 0 0 14px;
      font-size: 16px;
      font-weight: 600;
      color: var(--ink);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    input {
      width: 100%;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      color: var(--ink);
      font: inherit;
      background: var(--surface2);
    }
    input:focus {
      outline: 2px solid rgba(100,210,255,.18);
      border-color: var(--blue);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
    }
    button {
      min-height: 42px;
      border: 1px solid var(--blue);
      border-radius: 6px;
      padding: 9px 14px;
      background: rgba(100,210,255,.14);
      color: var(--blue);
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      transition: background 120ms;
    }
    button:hover { background: rgba(100,210,255,.22); }
    button.secondary {
      background: transparent;
      color: var(--muted);
      border-color: var(--line);
    }
    button.secondary:hover { background: var(--surface2); color: var(--ink); }
    button.danger {
      border-color: var(--red);
      background: transparent;
      color: var(--red);
    }
    button.danger:hover { background: rgba(255,107,107,.12); }
    button:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .status {
      min-height: 24px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }
    .status.ok { color: var(--green); }
    .status.error { color: var(--red); }
    .token-output {
      display: none;
      margin-top: 14px;
      border: 1px solid rgba(100,210,255,.25);
      border-radius: 8px;
      background: rgba(100,210,255,.06);
      padding: 14px;
    }
    .token-output.visible { display: block; }
    code {
      display: block;
      overflow-wrap: anywhere;
      white-space: normal;
      margin-top: 8px;
      padding: 12px;
      border-radius: 6px;
      background: var(--bg);
      border: 1px solid var(--line);
      color: var(--blue);
      font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
      font-size: 13px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      font-weight: 650;
      background: var(--surface2);
      color: var(--muted);
    }
    .pill.active {
      background: rgba(70,211,154,.15);
      color: var(--green);
    }
    .pill.revoked {
      background: rgba(255,107,107,.15);
      color: var(--red);
    }
    .help {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
      margin-bottom: 12px;
    }
    @media (max-width: 760px) {
      header { padding: 18px 16px 14px; }
      main { width: calc(100% - 20px); margin-top: 12px; }
      .grid { grid-template-columns: 1fr; }
      table, thead, tbody, th, td, tr { display: block; }
      th { display: none; }
      td { border-bottom: 0; padding: 6px 0; }
      tr { border-bottom: 1px solid var(--line); padding: 10px 0; }
    }
  </style>
</head>
<body>
  <header>
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
      <defs><linearGradient id="hg" x1="16" y1="2" x2="16" y2="30" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#64D2FF"/><stop offset="100%" stop-color="#A78BFA"/></linearGradient></defs>
      <path d="M16 2L27 6.8V17C27 23 22 27.8 16 29.8C10 27.8 5 23 5 17V6.8Z" fill="#111922"/>
      <path d="M16 2L27 6.8V17C27 23 22 27.8 16 29.8C10 27.8 5 23 5 17V6.8Z" fill="none" stroke="url(#hg)" stroke-width="1.5"/>
      <path d="M16 10L20.5 22H11.5L16 10Z" fill="none" stroke="url(#hg)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
      <line x1="13" y1="18.5" x2="19" y2="18.5" stroke="url(#hg)" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    <div>
      <h1>AEGIS Admin</h1>
      <p>Manage device enrollment tokens for the Android Connect Device screen.</p>
    </div>
  </header>
  <main>
    <section>
      <h2>Admin Access</h2>
      <div class="grid">
        <label>
          Analyst token
          <input id="analystToken" type="password" autocomplete="off" placeholder="sample-token" />
        </label>
      </div>
      <div class="actions">
        <button id="saveAnalystToken">Save Token</button>
        <button id="clearAnalystToken" class="secondary">Clear</button>
      </div>
      <div id="authStatus" class="status"></div>
    </section>

    <section>
      <h2>Create Device Token</h2>
      <div class="grid">
        <label>
          Label
          <input id="label" placeholder="Lab phone 01" />
        </label>
        <label>
          Device ID
          <input id="deviceId" placeholder="android-lab-001" />
        </label>
        <label>
          Expires at
          <input id="expiresAt" type="datetime-local" />
        </label>
      </div>
      <div class="actions">
        <button id="createToken">Create Enrollment Token</button>
        <button id="refreshTokens" class="secondary">Refresh List</button>
      </div>
      <div id="createStatus" class="status"></div>
      <div id="tokenOutput" class="token-output">
        <strong>Copy this token now. It will not appear again.</strong>
        <code id="newToken"></code>
        <div class="actions">
          <button id="copyToken" class="secondary">Copy Token</button>
        </div>
      </div>
    </section>

    <section>
      <h2>Enrollment Tokens</h2>
      <div class="help">The list never shows raw token values, only metadata. Revoke a token if it should no longer enroll devices.</div>
      <div id="listStatus" class="status"></div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Label</th>
            <th>Device</th>
            <th>Status</th>
            <th>Created</th>
            <th>Last Used</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="tokenRows"></tbody>
      </table>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    function getAnalystToken() {
      return localStorage.getItem("aegis_analyst_token") || $("analystToken").value.trim();
    }

    function setStatus(element, message, kind = "") {
      element.className = `status ${kind}`;
      element.textContent = message;
    }

    function authHeaders() {
      const token = getAnalystToken();
      if (!token) {
        throw new Error("Enter the analyst token first.");
      }
      return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      };
    }

    function formatDate(value) {
      if (!value) return "--";
      return new Date(value).toLocaleString();
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: {
          ...authHeaders(),
          ...(options.headers || {})
        }
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail?.message || body.detail?.error || body.detail || response.statusText;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return body;
    }

    async function createToken() {
      setStatus($("createStatus"), "Creating token...");
      $("tokenOutput").classList.remove("visible");
      try {
        const expiresAt = $("expiresAt").value;
        const body = {
          label: $("label").value.trim() || "New device",
          device_id: $("deviceId").value.trim() || null,
          expires_at: expiresAt ? new Date(expiresAt).toISOString() : null
        };
        const result = await api("/api/v1/enrollment-tokens", {
          method: "POST",
          body: JSON.stringify(body)
        });
        $("newToken").textContent = result.token;
        $("tokenOutput").classList.add("visible");
        setStatus($("createStatus"), "Token created. Copy it into the Android app.", "ok");
        await loadTokens();
      } catch (error) {
        setStatus($("createStatus"), error.message, "error");
      }
    }

    async function loadTokens() {
      setStatus($("listStatus"), "Loading tokens...");
      try {
        const result = await api("/api/v1/enrollment-tokens");
        const rows = result.items.map((item) => {
          const status = item.is_active
            ? '<span class="pill active">Active</span>'
            : '<span class="pill revoked">Revoked</span>';
          const action = item.is_active
            ? `<button class="danger" data-revoke="${item.id}">Revoke</button>`
            : "";
          return `<tr>
            <td>${item.id}</td>
            <td>${escapeHtml(item.label)}</td>
            <td>${escapeHtml(item.device_id || "--")}</td>
            <td>${status}</td>
            <td>${formatDate(item.created_at)}</td>
            <td>${formatDate(item.last_used_at)}</td>
            <td>${action}</td>
          </tr>`;
        }).join("");
        $("tokenRows").innerHTML = rows || '<tr><td colspan="7">No enrollment tokens yet.</td></tr>';
        setStatus($("listStatus"), `${result.items.length} token(s) loaded.`, "ok");
      } catch (error) {
        setStatus($("listStatus"), error.message, "error");
      }
    }

    async function revokeToken(id) {
      if (!confirm(`Revoke token ${id}?`)) return;
      try {
        await api(`/api/v1/enrollment-tokens/${id}/revoke`, { method: "POST" });
        await loadTokens();
      } catch (error) {
        setStatus($("listStatus"), error.message, "error");
      }
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    $("saveAnalystToken").addEventListener("click", async () => {
      const token = $("analystToken").value.trim();
      if (!token) {
        setStatus($("authStatus"), "Enter an analyst token.", "error");
        return;
      }
      localStorage.setItem("aegis_analyst_token", token);
      setStatus($("authStatus"), "Analyst token saved in this browser.", "ok");
      await loadTokens();
    });

    $("clearAnalystToken").addEventListener("click", () => {
      localStorage.removeItem("aegis_analyst_token");
      $("analystToken").value = "";
      setStatus($("authStatus"), "Analyst token cleared.");
      $("tokenRows").innerHTML = "";
    });

    $("createToken").addEventListener("click", createToken);
    $("refreshTokens").addEventListener("click", loadTokens);
    $("copyToken").addEventListener("click", async () => {
      await navigator.clipboard.writeText($("newToken").textContent);
      setStatus($("createStatus"), "Token copied.", "ok");
    });
    $("tokenRows").addEventListener("click", (event) => {
      const id = event.target?.dataset?.revoke;
      if (id) revokeToken(id);
    });

    const saved = localStorage.getItem("aegis_analyst_token");
    if (saved) {
      $("analystToken").value = saved;
      setStatus($("authStatus"), "Analyst token loaded from this browser.", "ok");
      loadTokens();
    }
  </script>
</body>
</html>
"""
