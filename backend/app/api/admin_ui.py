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
      color-scheme: light;
      --bg: #f7f9fc;
      --surface: #ffffff;
      --ink: #182033;
      --muted: #617089;
      --line: #d8e0eb;
      --blue: #2563eb;
      --green: #16a34a;
      --red: #dc2626;
      --yellow: #d97706;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }
    header {
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    h1 {
      margin: 0;
      font-size: 30px;
      line-height: 1.2;
    }
    header p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 15px;
    }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto 48px;
      display: grid;
      gap: 18px;
    }
    section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 18px;
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
      background: #fff;
    }
    input:focus {
      outline: 2px solid rgba(37, 99, 235, 0.18);
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
      background: var(--blue);
      color: #fff;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--blue);
    }
    button.danger {
      border-color: var(--red);
      background: #fff;
      color: var(--red);
    }
    button:disabled {
      opacity: 0.55;
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
      border: 1px solid #b7c7ee;
      border-radius: 8px;
      background: #eef4ff;
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
      background: #ffffff;
      border: 1px solid var(--line);
      color: var(--ink);
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
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
      font-size: 12px;
      text-transform: uppercase;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      font-weight: 650;
      background: #e5e7eb;
      color: #374151;
    }
    .pill.active {
      background: #dcfce7;
      color: #166534;
    }
    .pill.revoked {
      background: #fee2e2;
      color: #991b1b;
    }
    .help {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    @media (max-width: 760px) {
      header { padding: 22px 16px 16px; }
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
    <h1>AEGIS Admin</h1>
    <p>Create device enrollment tokens for the Android Connect Device screen.</p>
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
