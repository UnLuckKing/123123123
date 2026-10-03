"""
VANTA Full Multi-Tenant Management & Reseller Hub
- Master Admin & Reseller Panels
- License Management (Generate, Delete, HWID Reset, Expiry)
- Hardware ID (HWID) Locking & Validation
- Live Slot Telemetry & Audit Logs (User events, game session data, IP, timestamps)
- REST API for client authentication & M1 slot dispatching
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import hashlib
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_FILE = "/Users/m1/vanta_auth.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Keys table
    c.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT UNIQUE,
        role TEXT DEFAULT 'user', -- user, reseller, admin
        reseller_id TEXT,
        hwid TEXT,
        hwid_reset_count INTEGER DEFAULT 0,
        max_resets INTEGER DEFAULT 3,
        status TEXT DEFAULT 'active', -- active, banned, expired
        created_at INTEGER,
        expires_at INTEGER,
        note TEXT
    )
    """)

    # Audit Logs & Game Data table
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        license_key TEXT,
        event_type TEXT, -- login, slot_allocated, game_start, game_end, hwid_reset, error
        client_ip TEXT,
        hwid TEXT,
        slot_id TEXT,
        game_data TEXT, -- JSON blob of session details, champion, region
        details TEXT
    )
    """)

    # Default admin key if empty
        c.execute("""
    CREATE TABLE IF NOT EXISTS diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        severity TEXT,
        source TEXT,
        license_key TEXT,
        client_ip TEXT,
        message TEXT,
        meta_json TEXT
    );
""")

    c.execute("SELECT COUNT(*) FROM licenses WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        admin_key = "VANTA-ADMIN-" + uuid.uuid4().hex[:12].upper()
        c.execute("""
        INSERT INTO licenses (license_key, role, reseller_id, status, created_at, expires_at, note)
        VALUES (?, 'admin', 'root', 'active', ?, ?, 'Master Admin Key')
        """, (admin_key, int(time.time()), int(time.time()) + 315360000))
        print(f"[AUTH] Created Default Admin Key: {admin_key}")

    conn.commit()
    conn.close()

def log_event(license_key, event_type, client_ip="", hwid="", slot_id="", game_data="{}", details=""):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        INSERT INTO audit_logs (timestamp, license_key, event_type, client_ip, hwid, slot_id, game_data, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (int(time.time()), license_key, event_type, client_ip, hwid, slot_id, game_data, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[LOG ERR]", e)

init_db()

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VANTA // Sovereign Control Core</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090a0f;
            --surface: #11141c;
            --surface-border: #1e2433;
            --accent: #00f2fe;
            --accent-glow: rgba(0, 242, 254, 0.25);
            --danger: #ff3366;
            --success: #00ffaa;
            --text-main: #f0f4fc;
            --text-dim: #7a879e;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body { background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 24px; }
        .container { max-width: 1300px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 24px; border-bottom: 1px solid var(--surface-border); margin-bottom: 28px; }
        .logo { font-size: 24px; font-weight: 700; letter-spacing: 2px; color: var(--accent); text-shadow: 0 0 16px var(--accent-glow); display: flex; align-items: center; gap: 10px; }
        .badge { font-size: 11px; padding: 4px 8px; border-radius: 4px; background: rgba(0, 242, 254, 0.1); border: 1px solid var(--accent); font-family: 'JetBrains Mono', monospace; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 28px; }
        .card { background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; padding: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); }
        .card h3 { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; }
        .metric { font-size: 32px; font-weight: 700; color: var(--text-main); }
        .metric span { font-size: 14px; color: var(--text-dim); font-weight: 400; margin-left: 6px; }
        
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
        .table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; margin-bottom: 28px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        th { background: #151924; color: var(--text-dim); padding: 14px 16px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1px; }
        td { padding: 14px 16px; border-top: 1px solid var(--surface-border); font-family: 'JetBrains Mono', monospace; }
        tr:hover { background: rgba(255,255,255,0.02); }
        .btn { padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; font-weight: 600; transition: 0.2s; font-family: 'Outfit', sans-serif; }
        .btn-primary { background: var(--accent); color: #000; box-shadow: 0 0 12px var(--accent-glow); }
        .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-danger { background: rgba(255, 51, 102, 0.15); color: var(--danger); border: 1px solid var(--danger); }
        .btn-danger:hover { background: var(--danger); color: #fff; }
        .btn-action { background: #1e2433; color: var(--text-main); margin-right: 6px; border: 1px solid #2e384d; }
        .btn-action:hover { background: #2a3449; }
        .form-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
        input, select { background: #0c0e14; border: 1px solid var(--surface-border); border-radius: 6px; padding: 10px 14px; color: #fff; font-size: 13px; outline: none; }
        input:focus, select:focus { border-color: var(--accent); }
        .status-pill { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-active { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-busy { background: #ffaa00; box-shadow: 0 0 8px #ffaa00; }
        .status-idle { background: #555; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">VANTA <span>// CORE</span> <span class="badge">M1 MULTI-SLOT APEX</span></div>
            <div>
                <span id="roleBadge" class="badge">MASTER CONTROLLER</span>
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <h3>Active Slots</h3>
                <div class="metric" id="activeSlots">0 <span>/ 10 Online</span></div>
            </div>
            <div class="card">
                <h3>Total Licenses</h3>
                <div class="metric" id="totalKeys">0 <span>Registered</span></div>
            </div>
            <div class="card">
                <h3>Active Games</h3>
                <div class="metric" id="activeGames">0 <span>In-Game Sessions</span></div>
            </div>
            <div class="card">
                <h3>Host Telemetry</h3>
                <div class="metric" style="font-size: 20px; font-family: 'JetBrains Mono', monospace;" id="hostInfo">macOS M1 // Ready</div>
            </div>
        </div>

        <div class="section-title">
            <span>License & HWID Vault</span>
            <button class="btn btn-primary" onclick="generateKey()">+ Generate License</button>
        </div>

        <div class="form-row card" style="margin-bottom: 16px; padding: 14px;">
            <input type="text" id="newKeyNote" placeholder="Customer Note / Name (e.g. Ahmet)" style="flex: 2;">
            <select id="newKeyRole" style="flex: 1;">
                <option value="user">Standard User (1 Session)</option>
                <option value="reseller">Reseller License</option>
            </select>
            <select id="newKeyDuration" style="flex: 1;">
                <option value="1">1 Day</option>
                <option value="7">7 Days</option>
                <option value="30" selected>30 Days</option>
                <option value="365">Lifetime (1 Year)</option>
            </select>
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>KEY</th>
                        <th>ROLE</th>
                        <th>HWID LOCK</th>
                        <th>RESETS</th>
                        <th>STATUS</th>
                        <th>EXPIRES</th>
                        <th>NOTE</th>
                        <th>ACTIONS</th>
                    </tr>
                </thead>
                <tbody id="keysTable">
                    <tr><td colspan="8" style="text-align: center; color: var(--text-dim);">Loading vault...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section-title">
            <span>Live M1 Slot Allocation Matrix (10 Slots)</span>
            <button class="btn btn-action" onclick="fetchSlots()">Refresh Slots</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>SLOT</th>
                        <th>STATUS</th>
                        <th>PROXY PORT</th>
                        <th>LCU PORT</th>
                        <th>OWNER PUUID</th>
                        <th>LAST HEARTBEAT</th>
                    </tr>
                </thead>
                <tbody id="slotsTable">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-dim);">Querying M1 orchestrator...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section-title">
            <span>Audit & Game Session Logs</span>
            <button class="btn btn-action" onclick="fetchLogs()">Refresh Logs</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>TIME</th>
                        <th>EVENT</th>
                        <th>LICENSE</th>
                        <th>IP</th>
                        <th>HWID</th>
                        <th>DETAILS / GAME DATA</th>
                    </tr>
                </thead>
                <tbody id="logsTable">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-dim);">Querying logs...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function fetchAll() {
            await Promise.all([fetchKeys(), fetchSlots(), fetchLogs()]);
        }

        async function fetchKeys() {
            try {
                const res = await fetch('/api/keys');
                const data = await res.json();
                document.getElementById('totalKeys').innerHTML = `${data.keys.length} <span>Registered</span>`;
                const tbody = document.getElementById('keysTable');
                if (data.keys.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No keys issued yet.</td></tr>';
                    return;
                }
                tbody.innerHTML = data.keys.map(k => `
                    <tr>
                        <td style="color: var(--accent); font-weight: 600;">${k.license_key}</td>
                        <td><span class="badge">${k.role.toUpperCase()}</span></td>
                        <td>${k.hwid ? k.hwid.substring(0, 16) + '...' : '<span style="color:#555;">Unbound</span>'}</td>
                        <td>${k.hwid_reset_count} / ${k.max_resets}</td>
                        <td><span class="status-pill status-${k.status === 'active' ? 'active' : 'idle'}"></span>${k.status}</td>
                        <td>${new Date(k.expires_at * 1000).toLocaleDateString()}</td>
                        <td style="color: var(--text-dim);">${k.note || '-'}</td>
                        <td>
                            <button class="btn btn-action" onclick="resetHwid('${k.license_key}')">Reset HWID</button>
                            <button class="btn btn-danger" onclick="deleteKey('${k.license_key}')">Revoke</button>
                        </td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }

        async function fetchSlots() {
            try {
                const res = await fetch('/api/slots');
                const data = await res.json();
                const slots = data.slots || {};
                let activeCount = 0;
                const tbody = document.getElementById('slotsTable');
                tbody.innerHTML = Object.entries(slots).map(([sid, s]) => {
                    const isBusy = s.status !== 'idle';
                    if (isBusy) activeCount++;
                    return `
                        <tr>
                            <td><strong>${sid.toUpperCase()}</strong></td>
                            <td><span class="status-pill status-${isBusy ? 'busy' : 'idle'}"></span>${s.status.toUpperCase()}</td>
                            <td>${s.proxy_port}</td>
                            <td>${s.lcu_port}</td>
                            <td>${s.owner || '<span style="color:#555;">None</span>'}</td>
                            <td>${s.last_seen !== null ? s.last_seen + 's ago' : '-'}</td>
                        </tr>
                    `;
                }).join('');
                document.getElementById('activeSlots').innerHTML = `${activeCount} <span>/ 10 Online</span>`;
            } catch(e) { console.error(e); }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const tbody = document.getElementById('logsTable');
                if (!data.logs || data.logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No logs yet.</td></tr>';
                    return;
                }
                tbody.innerHTML = data.logs.slice(0, 50).map(l => `
                    <tr>
                        <td>${new Date(l.timestamp * 1000).toLocaleTimeString()}</td>
                        <td><span class="badge">${l.event_type.toUpperCase()}</span></td>
                        <td style="color: var(--accent);">${l.license_key ? l.license_key.substring(0, 14) + '...' : '-'}</td>
                        <td>${l.client_ip || '-'}</td>
                        <td>${l.hwid ? l.hwid.substring(0, 10) + '...' : '-'}</td>
                        <td style="color: var(--text-dim);">${l.details || l.game_data || '-'}</td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }

        async function generateKey() {
            const note = document.getElementById('newKeyNote').value;
            const role = document.getElementById('newKeyRole').value;
            const days = parseInt(document.getElementById('newKeyDuration').value);
            const res = await fetch('/api/keys/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ note, role, days })
            });
            const data = await res.json();
            if (data.success) {
                alert('Key Generated: ' + data.license_key);
                fetchKeys();
            } else {
                alert('Failed: ' + data.error);
            }
        }

        async function resetHwid(key) {
            if (!confirm('Reset HWID lock for ' + key + '?')) return;
            const res = await fetch('/api/keys/reset_hwid', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: key })
            });
            const data = await res.json();
            if (data.success) {
                alert('HWID Reset Successful');
                fetchKeys();
            } else {
                alert('Reset failed: ' + data.error);
            }
        }

        async function deleteKey(key) {
            if (!confirm('Revoke and delete key ' + key + '?')) return;
            const res = await fetch('/api/keys/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: key })
            });
            const data = await res.json();
            if (data.success) {
                fetchKeys();
            }
        }

        fetchAll();
        setInterval(fetchAll, 3000);
    </script>
</body>
</html>
"""

class VantaHubHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/admin", "/reseller", "/dashboard"]:
            self._send_html(HTML_DASHBOARD)
        elif path == "/api/keys":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM licenses ORDER BY id DESC")
            keys = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "keys": keys})
        elif path == "/api/logs":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
            logs = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "logs": logs})
        elif path == "/api/slots":
            # Proxy to local orchestrator on 9191
            try:
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:9000/api/slots", timeout=2) as r:
                    data = json.loads(r.read().decode())
                    self._send_json(200, data)
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {}

        client_ip = self.client_address[0]

        # Client authentication & HWID check endpoint
        if path == "/api/client/auth":
            key = payload.get("license_key", "").strip()
            hwid = payload.get("hwid", "").strip()

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM licenses WHERE license_key = ?", (key,))
            row = c.fetchone()

            if not row:
                conn.close()
                log_event(key, "login_failed", client_ip, hwid, details="Invalid key")
                self._send_json(401, {"success": False, "error": "Invalid License Key"})
                return

            if row["status"] != "active":
                conn.close()
                log_event(key, "login_failed", client_ip, hwid, details="Key suspended or expired")
                self._send_json(403, {"success": False, "error": "License is inactive or suspended"})
                return

            if row["expires_at"] < time.time():
                c.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                log_event(key, "login_failed", client_ip, hwid, details="License expired")
                self._send_json(403, {"success": False, "error": "License has expired"})
                return

            # HWID Binding check
            bound_hwid = row["hwid"]
            if not bound_hwid:
                # First time binding
                c.execute("UPDATE licenses SET hwid = ? WHERE id = ?", (hwid, row["id"]))
                conn.commit()
                log_event(key, "hwid_bound", client_ip, hwid, details="Initial HWID lock bound")
            elif bound_hwid != hwid:
                conn.close()
                log_event(key, "hwid_mismatch", client_ip, hwid, details=f"Expected {bound_hwid[:12]}, got {hwid[:12]}")
                self._send_json(403, {"success": False, "error": "HWID mismatch. Reset HWID in dashboard."})
                return

            conn.close()
            log_event(key, "login_success", client_ip, hwid, details="Client authorized")
            self._send_json(200, {
                "success": True,
                "role": row["role"],
                "expires_at": row["expires_at"],
                "m1_orchestrator": "http://51.159.121.126:9000"
            })

        # Key generation
        elif path == "/api/keys/create":
            note = payload.get("note", "")
            role = payload.get("role", "user")
            days = int(payload.get("days", 30))
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-RES-" if role == "reseller" else "VANTA-VIP-"
            key = prefix + uuid.uuid4().hex[:16].upper()

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
            INSERT INTO licenses (license_key, role, reseller_id, hwid, status, created_at, expires_at, note)
            VALUES (?, ?, 'root', NULL, 'active', ?, ?, ?)
            """, (key, role, now, expires, note))
            conn.commit()
            conn.close()

            log_event(key, "key_created", client_ip, details=f"Issued for {days} days, role={role}")
            self._send_json(200, {"success": True, "license_key": key, "expires_at": expires})

        # HWID Reset
        elif path == "/api/keys/reset_hwid":
            key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE licenses SET hwid = NULL, hwid_reset_count = hwid_reset_count + 1 WHERE license_key = ?", (key,))
            conn.commit()
            conn.close()
            log_event(key, "hwid_reset", client_ip, details="HWID unlocked by dashboard")
            self._send_json(200, {"success": True})

        # Revoke key
        elif path == "/api/keys/delete":
            key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM licenses WHERE license_key = ?", (key,))
            conn.commit()
            conn.close()
            log_event(key, "key_deleted", client_ip, details="Key revoked")
            self._send_json(200, {"success": True})

        # Telemetry and Game Data logging from Client
        elif path == "/api/client/log_game":
            key = payload.get("license_key")
            event = payload.get("event", "game_data")
            hwid = payload.get("hwid", "")
            slot_id = payload.get("slot_id", "")
            game_data = json.dumps(payload.get("data", {}))
            details = payload.get("details", "")
            log_event(key, event, client_ip, hwid, slot_id, game_data, details)
            self._send_json(200, {"success": True})

        else:
            self._send_json(404, {"error": "Not Found"})

def main():
    port = 8088
    server = ThreadingHTTPServer(("0.0.0.0", port), VantaHubHandler)
    print(f"[VANTA-HUB] Running on http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
