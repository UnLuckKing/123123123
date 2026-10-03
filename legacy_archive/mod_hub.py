import os

with open("vanta_hub_backup.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. ThreadingHTTPServer
code = code.replace(
    "from http.server import HTTPServer, BaseHTTPRequestHandler",
    "from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler"
)
code = code.replace(
    'server = HTTPServer(("0.0.0.0", port), VantaHubHandler)',
    'server = ThreadingHTTPServer(("0.0.0.0", port), VantaHubHandler)'
)

# 2. Fix Orchestrator port 9191 -> 9000
code = code.replace("http://127.0.0.1:9191/status", "http://127.0.0.1:9000/api/slots")
code = code.replace("http://51.159.121.126:9191", "http://51.159.121.126:9000")

# 3. Add diagnostics table
diag_table = """
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
"""
idx = code.find("CREATE TABLE IF NOT EXISTS audit_logs")
if idx != -1:
    end_idx = code.find("c.execute(\"SELECT COUNT(*)", idx)
    code = code[:end_idx] + '    c.execute("""' + diag_table + '""")\n\n    ' + code[end_idx:]

with open("vanta_hub_mod.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Modified vanta_hub_mod.py")
