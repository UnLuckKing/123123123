import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_hub.py", "r") as f:
    code = f.read().decode("utf-8")

# Fix port 9191 to 9000
code = code.replace("http://127.0.0.1:9191/status", "http://127.0.0.1:9000/api/slots")
code = code.replace("http://51.159.121.126:9191", "http://51.159.121.126:9000")

# Add live diagnostic console and emergency cleanup button
old_hdr = """            <span class="badge">M1 MULTI-SLOT APEX</span>
        </div>
        <div class="badge">MASTER CONTROLLER</div>"""

new_hdr = """            <span class="badge">APEX ENTERPRISE V5.2</span>
        </div>
        <div style="display: flex; gap: 10px;">
            <button class="btn btn-danger" onclick="emergencyCleanup()">Kill Ghost Matches</button>
            <div class="badge">MASTER CONTROLLER</div>
        </div>"""

if old_hdr in code:
    code = code.replace(old_hdr, new_hdr)

diag_ui = """
        <div class="section-title">
            <span>Live Health & Crash Diagnostic Stream</span>
            <button class="btn btn-action" onclick="fetchDiagnostics()">Refresh Stream</button>
        </div>
        <div class="table-wrap" style="padding: 14px; font-family: 'JetBrains Mono', monospace; font-size: 12px; background: #0c0f17;" id="diagStream">
            <div style="color: var(--text-dim);">Listening for live telemetry and crash events...</div>
        </div>
"""

# Insert diagnostic UI above License Vault
target_anchor = '<div class="section-title">\n            <span>License & HWID Vault</span>'
if target_anchor in code and "Live Health & Crash Diagnostic Stream" not in code:
    code = code.replace(target_anchor, diag_ui + "\n        " + target_anchor)

# Add emergencyCleanup and fetchDiagnostics to script
new_js = """
        async function fetchDiagnostics() {
            try {
                const res = await fetch('/api/diagnostics');
                const data = await res.json();
                const box = document.getElementById('diagStream');
                if (data.diagnostics && data.diagnostics.length > 0) {
                    box.innerHTML = data.diagnostics.map(d => `
                        <div style="padding: 4px 0; border-bottom: 1px solid #1a2233;">
                            <span style="color:#555;">[${new Date(d.timestamp * 1000).toLocaleTimeString()}]</span>
                            <span style="color: ${d.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--accent)'}; font-weight:600;">[${d.severity}]</span>
                            <span style="color: var(--text-dim);">[${d.source}]</span>
                            <span>${d.message}</span>
                            ${d.license_key ? '<span style="color:#777;">(' + d.license_key.substring(0,10) + '...)</span>' : ''}
                        </div>
                    `).join('');
                } else {
                    box.innerHTML = '<div style="color: var(--text-dim);">No errors recorded. All systems operating at 100% health.</div>';
                }
            } catch(e) { console.error(e); }
        }

        async function emergencyCleanup() {
            if (!confirm('Kill all hanging League and Riot Client processes on Mac?')) return;
            const res = await fetch('/api/admin/emergency_cleanup', { method: 'POST' });
            const data = await res.json();
            alert(data.message || 'Cleanup completed');
            fetchAll();
        }
"""

if "async function deleteKey" in code and "emergencyCleanup" not in code:
    code = code.replace("async function deleteKey(key) {", new_js + "\n        async function deleteKey(key) {")
    code = code.replace("await Promise.all([fetchKeys(), fetchSlots(), fetchLogs()]);", "await Promise.all([fetchKeys(), fetchSlots(), fetchLogs(), fetchDiagnostics()]);")

# Add diagnostics DB table and emergency_cleanup endpoint
diag_table_code = """
    c.execute('''
    CREATE TABLE IF NOT EXISTS diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        severity TEXT,
        source TEXT,
        license_key TEXT,
        client_ip TEXT,
        message TEXT,
        meta_json TEXT
    )
    ''')
"""

if "CREATE TABLE IF NOT EXISTS audit_logs" in code and "CREATE TABLE IF NOT EXISTS diagnostics" not in code:
    code = code.replace("c.execute('''\n    CREATE TABLE IF NOT EXISTS audit_logs", diag_table_code + "\n    c.execute('''\n    CREATE TABLE IF NOT EXISTS audit_logs")

# Add endpoint handlers
handlers = """
        elif path == "/api/diagnostics":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM diagnostics ORDER BY id DESC LIMIT 50")
            diags = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "diagnostics": diags})
"""

if 'elif path == "/api/logs":' in code and 'elif path == "/api/diagnostics":' not in code:
    code = code.replace('elif path == "/api/logs":', handlers.strip() + '\n        elif path == "/api/logs":')

post_handlers = """
        elif path == "/api/admin/emergency_cleanup":
            subprocess.run(["pkill", "-9", "-f", "League"], capture_output=True)
            subprocess.run(["pkill", "-9", "-f", "Riot Client"], capture_output=True)
            self._send_json(200, {"success": True, "message": "Host processes cleaned successfully"})
        elif path == "/api/telemetry/report":
            severity = payload.get("severity", "INFO")
            source = payload.get("source", "CLIENT")
            msg = payload.get("message", "")
            key = payload.get("license_key", "")
            meta = json.dumps(payload.get("meta", {}))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO diagnostics (timestamp, severity, source, license_key, client_ip, message, meta_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (int(time.time()), severity, source, key, client_ip, msg, meta))
            conn.commit()
            conn.close()
            self._send_json(200, {"success": True})
"""

if 'elif path == "/api/client/log_game":' in code and 'emergency_cleanup' not in code:
    code = code.replace('elif path == "/api/client/log_game":', post_handlers.strip() + '\n        elif path == "/api/client/log_game":')

with sftp.open("/Users/m1/vanta_hub.py", "w") as f:
    f.write(code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_hub.py
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:8088/api/keys | head -c 100
echo ""
curl -s http://127.0.0.1:8088/api/slots
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
print("APPLIED ENHANCED ADMIN HUB")
