"""
Script to create the fully upgraded vanta_hub.py and upload to Mac M1 (51.159.121.126).
"""
import os
import paramiko

HUB_CODE = r'''"""
VANTA Sovereign Control Core // Central Web Hub & Telemetry Engine
- Multi-Tenant License Management (Issue, Revoke, HWID Reset, Ban/Unban, Expiry Extend, Bulk Creation)
- Live Health & Crash Diagnostic Stream with Error Inspector
- M1 Slot Allocation Matrix with Emergency Ghost Match Killing
- Bidirectional Telemetry Reporting from Windows Clients & Mac Orchestrator
- Multi-threaded ThreadingHTTPServer Architecture
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import hashlib
import urllib.request
import subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_FILE = "/Users/m1/vanta_auth.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Licenses table
    c.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT UNIQUE,
        role TEXT DEFAULT 'user', -- user, vip, reseller, admin
        reseller_id TEXT,
        hwid TEXT,
        hwid_reset_count INTEGER DEFAULT 0,
        max_resets INTEGER DEFAULT 3,
        status TEXT DEFAULT 'active', -- active, banned, expired
        created_at INTEGER,
        expires_at INTEGER,
        note TEXT,
        last_ip TEXT,
        last_seen INTEGER
    )
    """)

    # Audit Logs & Game Data table
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        license_key TEXT,
        event_type TEXT,
        client_ip TEXT,
        hwid TEXT,
        slot_id TEXT,
        game_data TEXT,
        details TEXT
    )
    """)

    # Live Health & Crash Diagnostics table
    c.execute("""
    CREATE TABLE IF NOT EXISTS diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        severity TEXT, -- INFO, WARN, ERROR, CRITICAL
        source TEXT,   -- CLIENT_WAD, GAME_LAUNCHER, ORCHESTRATOR, AUTH, PROXY
        message TEXT,
        details TEXT,
        client_ip TEXT,
        hwid TEXT,
        license_key TEXT,
        extra TEXT,    -- JSON blob (locale, exit_code, ping, etc.)
        resolved INTEGER DEFAULT 0
    )
    """)

    # Default admin key if empty
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

def log_diagnostic(severity, source, message, details="", client_ip="", hwid="", license_key="", extra="{}"):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        INSERT INTO diagnostics (timestamp, severity, source, message, details, client_ip, hwid, license_key, extra)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (int(time.time()), severity, source, message, details, client_ip, hwid, license_key, extra))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[DIAG ERR]", e)

init_db()

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VANTA // Sovereign Control Core</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #07090e;
            --surface: #0e121a;
            --surface-card: #131824;
            --surface-hover: #192030;
            --surface-border: #1f2738;
            --border-highlight: #2f3a52;
            --accent: #00f2fe;
            --accent-glow: rgba(0, 242, 254, 0.35);
            --danger: #ff3366;
            --danger-glow: rgba(255, 51, 102, 0.35);
            --warning: #ffaa00;
            --warning-glow: rgba(255, 170, 0, 0.3);
            --success: #00ffaa;
            --success-glow: rgba(0, 255, 170, 0.3);
            --text-main: #f0f4fc;
            --text-dim: #7e8c9f;
            --text-muted: #4e5a6e;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body { background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 24px 32px; overflow-x: hidden; }
        .container { max-width: 1440px; margin: 0 auto; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--surface-border); margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
        .brand { display: flex; align-items: center; gap: 14px; }
        .logo { font-size: 26px; font-weight: 800; letter-spacing: 2px; color: #fff; display: flex; align-items: center; gap: 8px; }
        .logo span { color: var(--accent); text-shadow: 0 0 16px var(--accent-glow); }
        .sys-badge { font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(0, 242, 254, 0.08); border: 1px solid var(--accent); font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent); display: flex; align-items: center; gap: 6px; }
        .pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); box-shadow: 0 0 8px var(--success); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
        
        .header-actions { display: flex; align-items: center; gap: 12px; }
        
        /* Banner */
        .emergency-banner { background: linear-gradient(90deg, rgba(255,51,102,0.12), rgba(255,170,0,0.08)); border: 1px solid rgba(255,51,102,0.3); border-radius: 10px; padding: 12px 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
        .banner-text { font-size: 13px; font-family: 'JetBrains Mono', monospace; color: #ffd1dc; }
        .banner-text strong { color: var(--danger); }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .stat-card { background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; padding: 20px; position: relative; overflow: hidden; transition: border-color 0.2s; }
        .stat-card:hover { border-color: var(--border-highlight); }
        .stat-card h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); margin-bottom: 10px; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
        .stat-val { font-size: 32px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }
        .stat-val span { font-size: 13px; color: var(--text-dim); font-weight: 400; margin-left: 6px; }
        .stat-pill { position: absolute; top: 18px; right: 18px; font-size: 10px; font-family: 'JetBrains Mono', monospace; padding: 3px 8px; border-radius: 4px; font-weight: 600; }
        
        /* Tabs */
        .tabs { display: flex; gap: 10px; border-bottom: 1px solid var(--surface-border); margin-bottom: 20px; padding-bottom: 8px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; color: var(--text-dim); padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; font-family: 'Outfit', sans-serif; display: flex; align-items: center; gap: 8px; }
        .tab-btn:hover { color: #fff; background: var(--surface); }
        .tab-btn.active { color: var(--accent); background: rgba(0, 242, 254, 0.1); border: 1px solid rgba(0, 242, 254, 0.3); text-shadow: 0 0 10px var(--accent-glow); }
        .tab-badge { background: #1e2536; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-main); }
        
        /* Content Sections */
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
        .search-box { background: #0c0f17; border: 1px solid var(--surface-border); border-radius: 8px; padding: 9px 14px; color: #fff; font-size: 13px; width: 280px; outline: none; font-family: 'JetBrains Mono', monospace; }
        .search-box:focus { border-color: var(--accent); }
        
        /* Buttons */
        .btn { padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; font-family: 'Outfit', sans-serif; }
        .btn-primary { background: var(--accent); color: #000; box-shadow: 0 0 14px var(--accent-glow); font-weight: 700; }
        .btn-primary:hover { opacity: 0.92; transform: translateY(-1px); }
        .btn-danger { background: rgba(255, 51, 102, 0.14); color: var(--danger); border: 1px solid var(--danger); }
        .btn-danger:hover { background: var(--danger); color: #fff; box-shadow: 0 0 14px var(--danger-glow); }
        .btn-warning { background: rgba(255, 170, 0, 0.14); color: var(--warning); border: 1px solid var(--warning); }
        .btn-warning:hover { background: var(--warning); color: #000; font-weight: 700; }
        .btn-action { background: #182030; color: var(--text-main); border: 1px solid var(--surface-border); }
        .btn-action:hover { background: #222b40; border-color: var(--border-highlight); color: #fff; }
        .btn-sm { padding: 4px 10px; font-size: 11px; border-radius: 6px; }
        
        /* Tables */
        .table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.5); }
        table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        th { background: #0c0f17; color: var(--text-dim); padding: 14px 18px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1px; font-weight: 600; border-bottom: 1px solid var(--surface-border); }
        td { padding: 13px 18px; border-bottom: 1px solid rgba(255,255,255,0.03); font-family: 'JetBrains Mono', monospace; vertical-align: middle; }
        tr:hover td { background: rgba(255,255,255,0.02); }
        
        /* Console / Diagnostic Stream */
        .console-wrap { background: #080b11; border: 1px solid var(--surface-border); border-radius: 12px; padding: 16px; font-family: 'JetBrains Mono', monospace; font-size: 12px; height: 520px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.6); }
        .log-entry { display: flex; align-items: flex-start; gap: 10px; padding: 6px 8px; border-radius: 6px; transition: background 0.15s; cursor: pointer; }
        .log-entry:hover { background: rgba(255,255,255,0.03); }
        .log-ts { color: var(--text-muted); font-size: 11px; min-width: 75px; }
        .log-sev { padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 10px; min-width: 60px; text-align: center; }
        .sev-CRITICAL { background: rgba(255,51,102,0.25); color: var(--danger); border: 1px solid var(--danger); text-shadow: 0 0 6px var(--danger-glow); }
        .sev-ERROR { background: rgba(255,100,50,0.2); color: #ff7744; border: 1px solid #ff7744; }
        .sev-WARN { background: rgba(255,170,0,0.2); color: var(--warning); border: 1px solid var(--warning); }
        .sev-INFO { background: rgba(0,242,254,0.15); color: var(--accent); border: 1px solid var(--accent); }
        .log-src { color: var(--text-dim); min-width: 120px; font-weight: 600; }
        .log-msg { color: var(--text-main); flex: 1; word-break: break-all; }
        .log-meta { color: var(--text-muted); font-size: 11px; margin-left: auto; }
        
        /* Badges & Pills */
        .status-pill { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-active { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-busy { background: var(--warning); box-shadow: 0 0 8px var(--warning); }
        .status-idle { background: #555; }
        .status-banned { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
        .badge { font-size: 11px; padding: 3px 8px; border-radius: 4px; background: rgba(255,255,255,0.05); font-family: 'JetBrains Mono', monospace; font-weight: 600; border: 1px solid var(--surface-border); }
        .badge-vip { border-color: var(--warning); color: var(--warning); background: rgba(255,170,0,0.1); }
        .badge-user { border-color: var(--accent); color: var(--accent); background: rgba(0,242,254,0.1); }
        .badge-reseller { border-color: #a855f7; color: #c084fc; background: rgba(168,85,247,0.1); }
        .badge-admin { border-color: var(--danger); color: var(--danger); background: rgba(255,51,102,0.1); }
        
        /* Slot Cards */
        .slots-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
        .slot-card { background: var(--surface); border: 1px solid var(--surface-border); border-radius: 12px; padding: 18px; position: relative; }
        .slot-card.active-game { border-color: var(--accent); box-shadow: 0 0 16px var(--accent-glow); }
        .slot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .slot-title { font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: #fff; }
        .slot-info-row { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }
        .slot-info-row span:last-child { color: var(--text-main); font-weight: 500; }
        
        /* Modal */
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .modal { background: var(--surface); border: 1px solid var(--border-highlight); border-radius: 14px; width: 90%; max-width: 600px; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.8); }
        .modal h2 { font-size: 18px; margin-bottom: 16px; color: #fff; }
        .modal-body { margin-bottom: 20px; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 6px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; }
        .form-control { width: 100%; background: #080b11; border: 1px solid var(--surface-border); border-radius: 8px; padding: 10px 14px; color: #fff; font-size: 13px; outline: none; }
        .form-control:focus { border-color: var(--accent); }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
        
        /* Toast Notifications */
        #toast { position: fixed; bottom: 24px; right: 24px; padding: 12px 20px; background: #182030; border: 1px solid var(--accent); border-radius: 8px; color: #fff; font-size: 13px; font-weight: 600; box-shadow: 0 8px 30px rgba(0,0,0,0.6); display: none; z-index: 2000; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="logo">VANTA <span>// SOVEREIGN</span></div>
                <div class="sys-badge">
                    <span class="pulse-dot"></span>
                    <span id="hostStatus">M1 APEX CORE // ONLINE</span>
                </div>
            </div>
            <div class="header-actions">
                <button class="btn btn-action btn-sm" onclick="toggleAutoRefresh()" id="refreshBtn">🔄 Auto-Refresh: ON (3s)</button>
                <button class="btn btn-danger btn-sm" onclick="killAllGhostMatches()">⚡ Kill Ghost Matches</button>
            </div>
        </header>

        <!-- KPI Metrics -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Active Concurrency</h3>
                <div class="stat-val" id="kpiSlots">0 <span>/ 5 Slots In-Flight</span></div>
                <span class="stat-pill" style="background:rgba(0,242,254,0.1); color:var(--accent);">ORCHESTRATOR</span>
            </div>
            <div class="stat-card">
                <h3>License Vault</h3>
                <div class="stat-val" id="kpiKeys">0 <span>Active Keys</span></div>
                <span class="stat-pill" style="background:rgba(0,255,170,0.1); color:var(--success);" id="kpiTotalKeys">0 Total</span>
            </div>
            <div class="stat-card">
                <h3>Live Health</h3>
                <div class="stat-val" id="kpiErrors" style="color:var(--success);">0 <span>Errors / 24h</span></div>
                <span class="stat-pill" style="background:rgba(255,51,102,0.1); color:var(--danger);" id="kpiCritical">0 CRITICAL</span>
            </div>
            <div class="stat-card">
                <h3>Host Environment</h3>
                <div class="stat-val" style="font-size:22px; font-family:'JetBrains Mono', monospace;" id="kpiHost">macOS M1 ARM64</div>
                <span class="stat-pill" style="background:rgba(255,170,0,0.1); color:var(--warning);">PORT 9000 & 8088</span>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('diags')">🚨 Diagnostics & Crashes <span class="tab-badge" id="diagCount">0</span></button>
            <button class="tab-btn" onclick="switchTab('slots')">⚡ M1 Slot Matrix <span class="tab-badge" id="slotActiveBadge">0 Active</span></button>
            <button class="tab-btn" onclick="switchTab('keys')">🔑 License Manager <span class="tab-badge" id="keysBadge">0</span></button>
            <button class="tab-btn" onclick="switchTab('audit')">📜 Security Audit Trail</button>
        </div>

        <!-- TAB 1: Live Diagnostics -->
        <div id="tab-diags" class="tab-content active">
            <div class="toolbar">
                <div style="display:flex; gap:8px; align-items:center;">
                    <button class="btn btn-action btn-sm" onclick="setDiagFilter('ALL')">ALL</button>
                    <button class="btn btn-danger btn-sm" onclick="setDiagFilter('CRITICAL')">CRITICAL ONLY</button>
                    <button class="btn btn-warning btn-sm" onclick="setDiagFilter('ERROR')">ERRORS</button>
                    <button class="btn btn-primary btn-sm" onclick="setDiagFilter('INFO')">INFO</button>
                </div>
                <div style="display:flex; gap:10px;">
                    <input type="text" class="search-box" id="diagSearch" placeholder="Filter telemetry messages..." onkeyup="renderDiagnostics()">
                    <button class="btn btn-action btn-sm" onclick="clearDiagnostics()">🧹 Clear Telemetry</button>
                </div>
            </div>
            <div class="console-wrap" id="diagConsole">
                <div style="color:var(--text-dim); text-align:center; padding-top:40px;">Connecting to telemetry stream...</div>
            </div>
        </div>

        <!-- TAB 2: Slot Matrix -->
        <div id="tab-slots" class="tab-content">
            <div class="toolbar">
                <span style="font-size:14px; font-weight:600; color:var(--text-dim); font-family:'JetBrains Mono', monospace;">M1 ISOLATED WORKERS (MAX 5 SLOTS)</span>
                <button class="btn btn-action btn-sm" onclick="fetchSlots()">🔄 Refresh Slots</button>
            </div>
            <div class="slots-grid" id="slotsGrid">
                <div style="color:var(--text-dim); grid-column: 1/-1; text-align:center; padding:40px;">Querying slot orchestrator on port 9000...</div>
            </div>
        </div>

        <!-- TAB 3: License Vault -->
        <div id="tab-keys" class="tab-content">
            <div class="toolbar">
                <div style="display:flex; gap:10px;">
                    <input type="text" class="search-box" id="keySearch" placeholder="Search key, note, HWID..." onkeyup="renderKeys()">
                    <select class="form-control" style="width:140px; padding:8px;" id="keyRoleFilter" onchange="renderKeys()">
                        <option value="ALL">All Roles</option>
                        <option value="user">User</option>
                        <option value="vip">VIP</option>
                        <option value="reseller">Reseller</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-primary" onclick="openCreateModal()">+ Create License</button>
                    <button class="btn btn-action" onclick="openBulkModal()">📦 Bulk Generator</button>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>LICENSE KEY</th>
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
                        <tr><td colspan="8" style="text-align:center; color:var(--text-dim);">Loading vault...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 4: Audit Logs -->
        <div id="tab-audit" class="tab-content">
            <div class="toolbar">
                <span style="font-size:14px; font-weight:600; color:var(--text-dim); font-family:'JetBrains Mono', monospace;">CLIENT SESSIONS & AUTHENTICATION EVENTS</span>
                <button class="btn btn-action btn-sm" onclick="fetchLogs()">🔄 Refresh Audit Trail</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>TIMESTAMP</th>
                            <th>EVENT TYPE</th>
                            <th>LICENSE KEY</th>
                            <th>IP ADDRESS</th>
                            <th>HWID</th>
                            <th>DETAILS / SESSION DATA</th>
                        </tr>
                    </thead>
                    <tbody id="logsTable">
                        <tr><td colspan="6" style="text-align:center; color:var(--text-dim);">Loading audit records...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Create License Modal -->
    <div class="modal-overlay" id="createModal">
        <div class="modal">
            <h2>Generate New License Key</h2>
            <div class="modal-body">
                <div class="form-group">
                    <label>Customer Name / Reference Note</label>
                    <input type="text" class="form-control" id="modalKeyNote" placeholder="e.g. VIP Discord #9924">
                </div>
                <div class="form-group">
                    <label>License Tier / Role</label>
                    <select class="form-control" id="modalKeyRole">
                        <option value="user">Standard User (1 Concurrent Match)</option>
                        <option value="vip" selected>VIP Member (Priority Slot & Telemetry)</option>
                        <option value="reseller">Reseller License</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Validity Duration</label>
                    <select class="form-control" id="modalKeyDays">
                        <option value="1">1 Day Trial</option>
                        <option value="7">7 Days (Weekly)</option>
                        <option value="30" selected>30 Days (Monthly)</option>
                        <option value="90">90 Days (Quarterly)</option>
                        <option value="365">365 Days (Annual / Lifetime)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Max HWID Resets Allowed</label>
                    <input type="number" class="form-control" id="modalKeyResets" value="3" min="1" max="10">
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-action" onclick="closeCreateModal()">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateKey()">Generate Key</button>
            </div>
        </div>
    </div>

    <!-- Bulk Generator Modal -->
    <div class="modal-overlay" id="bulkModal">
        <div class="modal">
            <h2>Bulk License Generator</h2>
            <div class="modal-body">
                <div class="form-group">
                    <label>Number of Keys to Generate</label>
                    <input type="number" class="form-control" id="bulkCount" value="5" min="1" max="50">
                </div>
                <div class="form-group">
                    <label>Role</label>
                    <select class="form-control" id="bulkRole">
                        <option value="user">Standard User</option>
                        <option value="vip" selected>VIP</option>
                        <option value="reseller">Reseller</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Duration (Days)</label>
                    <input type="number" class="form-control" id="bulkDays" value="30">
                </div>
                <div class="form-group">
                    <label>Batch Tag / Note</label>
                    <input type="text" class="form-control" id="bulkNote" placeholder="e.g. EUW Launch Batch 1">
                </div>
                <div class="form-group" id="bulkResultArea" style="display:none;">
                    <label>Generated Keys</label>
                    <textarea class="form-control" id="bulkResultKeys" rows="6" readonly style="font-family:'JetBrains Mono', monospace;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-action" onclick="closeBulkModal()">Close</button>
                <button class="btn btn-primary" id="btnBulkGen" onclick="submitBulkKeys()">Generate Batch</button>
            </div>
        </div>
    </div>

    <!-- Diagnostic Details Modal -->
    <div class="modal-overlay" id="diagDetailsModal">
        <div class="modal" style="max-width:750px;">
            <h2 id="diagModalTitle">Crash / Telemetry Event Inspector</h2>
            <div class="modal-body">
                <div class="form-group">
                    <label>Source & Severity</label>
                    <div id="diagModalMeta" style="font-family:'JetBrains Mono', monospace; font-size:13px; color:var(--accent);"></div>
                </div>
                <div class="form-group">
                    <label>Primary Error Message</label>
                    <div id="diagModalMsg" style="background:#080b11; padding:10px; border-radius:6px; font-family:'JetBrains Mono', monospace; font-size:12px; color:#fff; border:1px solid var(--surface-border);"></div>
                </div>
                <div class="form-group">
                    <label>Full Stack / Diagnostic Details</label>
                    <pre id="diagModalDetails" style="background:#080b11; padding:12px; border-radius:8px; font-family:'JetBrains Mono', monospace; font-size:11px; color:#ccc; max-height:240px; overflow-y:auto; border:1px solid var(--surface-border); white-space:pre-wrap;"></pre>
                </div>
                <div class="form-group">
                    <label>Client Environment & Extra Context</label>
                    <pre id="diagModalExtra" style="background:#080b11; padding:12px; border-radius:8px; font-family:'JetBrains Mono', monospace; font-size:11px; color:var(--text-dim); max-height:120px; overflow-y:auto; border:1px solid var(--surface-border); white-space:pre-wrap;"></pre>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="closeDiagModal()">Done</button>
            </div>
        </div>
    </div>

    <div id="toast">Operation Successful</div>

    <script>
        let allKeys = [];
        let allDiagnostics = [];
        let currentDiagFilter = 'ALL';
        let autoRefreshInterval = null;
        let isAutoRefresh = true;

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3000);
        }

        function switchTab(name) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.currentTarget.classList.add('active');
            document.getElementById('tab-' + name).classList.add('active');
        }

        function toggleAutoRefresh() {
            const btn = document.getElementById('refreshBtn');
            if (isAutoRefresh) {
                clearInterval(autoRefreshInterval);
                isAutoRefresh = false;
                btn.innerText = '⏸️ Auto-Refresh: OFF';
            } else {
                autoRefreshInterval = setInterval(fetchAll, 3000);
                isAutoRefresh = true;
                btn.innerText = '🔄 Auto-Refresh: ON (3s)';
            }
        }

        async function fetchAll() {
            await Promise.all([fetchStats(), fetchDiagnostics(), fetchSlots(), fetchKeys(), fetchLogs()]);
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                if (data.success) {
                    const s = data.stats;
                    document.getElementById('kpiSlots').innerHTML = `${s.active_slots} <span>/ ${s.total_slots} In-Flight</span>`;
                    document.getElementById('kpiKeys').innerHTML = `${s.active_keys} <span>Active Keys</span>`;
                    document.getElementById('kpiTotalKeys').innerText = `${s.total_keys} Total`;
                    document.getElementById('kpiErrors').innerHTML = `${s.error_diagnostics} <span>Errors / 24h</span>`;
                    document.getElementById('kpiCritical').innerText = `${s.critical_diagnostics} CRITICAL`;
                    if (s.critical_diagnostics > 0) {
                        document.getElementById('kpiErrors').style.color = 'var(--danger)';
                    } else {
                        document.getElementById('kpiErrors').style.color = 'var(--success)';
                    }
                }
            } catch(e) { console.error(e); }
        }

        async function fetchDiagnostics() {
            try {
                const res = await fetch('/api/diagnostics');
                const data = await res.json();
                if (data.success) {
                    allDiagnostics = data.diagnostics || [];
                    document.getElementById('diagCount').innerText = allDiagnostics.length;
                    renderDiagnostics();
                }
            } catch(e) { console.error(e); }
        }

        function setDiagFilter(f) {
            currentDiagFilter = f;
            renderDiagnostics();
        }

        function renderDiagnostics() {
            const q = document.getElementById('diagSearch').value.toLowerCase();
            const box = document.getElementById('diagConsole');
            let filtered = allDiagnostics;

            if (currentDiagFilter !== 'ALL') {
                filtered = filtered.filter(d => d.severity === currentDiagFilter);
            }
            if (q) {
                filtered = filtered.filter(d => 
                    d.message.toLowerCase().includes(q) || 
                    d.source.toLowerCase().includes(q) || 
                    (d.details && d.details.toLowerCase().includes(q))
                );
            }

            if (filtered.length === 0) {
                box.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding-top:40px;">No diagnostic reports matching current filter. All systems operational.</div>';
                return;
            }

            box.innerHTML = filtered.map(d => `
                <div class="log-entry" onclick="openDiagDetails(${d.id})">
                    <span class="log-ts">${new Date(d.timestamp * 1000).toLocaleTimeString()}</span>
                    <span class="log-sev sev-${d.severity}">${d.severity}</span>
                    <span class="log-src">[${d.source}]</span>
                    <span class="log-msg">${d.message}</span>
                    <span class="log-meta">${d.client_ip ? d.client_ip : ''} ${d.license_key ? '(' + d.license_key.substring(0,10) + '...)' : ''}</span>
                </div>
            `).join('');
        }

        function openDiagDetails(id) {
            const d = allDiagnostics.find(item => item.id === id);
            if (!d) return;
            document.getElementById('diagModalTitle').innerText = `Diagnostic Event #${d.id} // [${d.severity}]`;
            document.getElementById('diagModalMeta').innerText = `Source: ${d.source} | IP: ${d.client_ip || 'N/A'} | HWID: ${d.hwid || 'N/A'} | Key: ${d.license_key || 'N/A'}`;
            document.getElementById('diagModalMsg').innerText = d.message;
            document.getElementById('diagModalDetails').innerText = d.details || '(No extended stack trace)';
            try {
                const parsed = JSON.parse(d.extra || '{}');
                document.getElementById('diagModalExtra').innerText = JSON.stringify(parsed, null, 2);
            } catch {
                document.getElementById('diagModalExtra').innerText = d.extra || '{}';
            }
            document.getElementById('diagDetailsModal').style.display = 'flex';
        }

        function closeDiagModal() {
            document.getElementById('diagDetailsModal').style.display = 'none';
        }

        async function clearDiagnostics() {
            if (!confirm('Clear all diagnostics and telemetry logs?')) return;
            await fetch('/api/diagnostics/clear', { method: 'POST' });
            showToast('Diagnostics Cleared');
            fetchDiagnostics();
        }

        async function fetchSlots() {
            try {
                const res = await fetch('/api/slots');
                const data = await res.json();
                const slots = data.slots || {};
                const grid = document.getElementById('slotsGrid');
                const entries = Object.entries(slots);
                let activeCount = 0;

                if (entries.length === 0) {
                    grid.innerHTML = '<div style="color:var(--text-dim); grid-column:1/-1; text-align:center; padding:40px;">No slots currently allocated on M1 Orchestrator. Pool is ready.</div>';
                    document.getElementById('slotActiveBadge').innerText = '0 Active';
                    return;
                }

                grid.innerHTML = entries.map(([sid, s]) => {
                    const isGame = s.game_active;
                    const isBusy = s.status !== 'idle';
                    if (isBusy) activeCount++;
                    return `
                        <div class="slot-card ${isGame ? 'active-game' : ''}">
                            <div class="slot-header">
                                <span class="slot-title">SLOT // ${sid.substring(0,8).toUpperCase()}</span>
                                <span class="badge ${isGame ? 'badge-admin' : (isBusy ? 'badge-vip' : '')}">${s.status.toUpperCase()}</span>
                            </div>
                            <div class="slot-info-row">
                                <span>Proxy Port:</span>
                                <span>${s.proxy_port || '-'}</span>
                            </div>
                            <div class="slot-info-row">
                                <span>LCU Port:</span>
                                <span>${s.lcu_port || '-'}</span>
                            </div>
                            <div class="slot-info-row">
                                <span>UDP Relay Port:</span>
                                <span>${s.udp_proxy_port || '-'}</span>
                            </div>
                            <div class="slot-info-row">
                                <span>3D Game State:</span>
                                <span style="color:${isGame ? 'var(--success)' : 'var(--text-dim)'};">${isGame ? '🎮 IN GAME MATCH' : 'Waiting Game'}</span>
                            </div>
                            <div class="slot-info-row">
                                <span>Keepalive / Idle:</span>
                                <span>${s.last_poll_seconds}s ago</span>
                            </div>
                            <div style="margin-top:14px; display:flex; justify-content:flex-end;">
                                <button class="btn btn-danger btn-sm" onclick="killSlot('${sid}')">Force Kill Slot</button>
                            </div>
                        </div>
                    `;
                }).join('');
                document.getElementById('slotActiveBadge').innerText = `${activeCount} Active`;
            } catch(e) { console.error(e); }
        }

        async function killSlot(sid) {
            if (!confirm(`Force kill slot ${sid.substring(0,8)}?`)) return;
            const res = await fetch('/api/slots/kill', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ slot_id: sid })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Slot ${sid.substring(0,8)} terminated`);
                fetchSlots();
            } else {
                alert('Kill failed: ' + data.error);
            }
        }

        async function killAllGhostMatches() {
            if (!confirm('EMERGENCY: Force kill all background League matches, wine processes, and reset all M1 slots?')) return;
            const res = await fetch('/api/slots/reset', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast(`Reset ${data.cleared_slots || 0} slots & killed orphan processes`);
                fetchAll();
            } else {
                alert('Reset failed: ' + data.error);
            }
        }

        async function fetchKeys() {
            try {
                const res = await fetch('/api/keys');
                const data = await res.json();
                if (data.success) {
                    allKeys = data.keys || [];
                    document.getElementById('keysBadge').innerText = allKeys.length;
                    renderKeys();
                }
            } catch(e) { console.error(e); }
        }

        function renderKeys() {
            const q = document.getElementById('keySearch').value.toLowerCase();
            const roleFilter = document.getElementById('keyRoleFilter').value;
            const tbody = document.getElementById('keysTable');
            let filtered = allKeys;

            if (roleFilter !== 'ALL') {
                filtered = filtered.filter(k => k.role === roleFilter);
            }
            if (q) {
                filtered = filtered.filter(k => 
                    k.license_key.toLowerCase().includes(q) || 
                    (k.note && k.note.toLowerCase().includes(q)) || 
                    (k.hwid && k.hwid.toLowerCase().includes(q))
                );
            }

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-dim);">No keys match search.</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(k => `
                <tr>
                    <td style="color: var(--accent); font-weight: 700; cursor:pointer;" onclick="copyToClipboard('${k.license_key}')" title="Click to copy">
                        ${k.license_key} 📋
                    </td>
                    <td><span class="badge badge-${k.role}">${k.role.toUpperCase()}</span></td>
                    <td>${k.hwid ? k.hwid.substring(0, 16) + '...' : '<span style="color:#555;">Unbound</span>'}</td>
                    <td>${k.hwid_reset_count} / ${k.max_resets}</td>
                    <td><span class="status-pill status-${k.status}"></span>${k.status.toUpperCase()}</td>
                    <td>${new Date(k.expires_at * 1000).toLocaleDateString()}</td>
                    <td style="color: var(--text-dim);">${k.note || '-'}</td>
                    <td>
                        <button class="btn btn-action btn-sm" onclick="resetHwid('${k.license_key}')">Reset HWID</button>
                        <button class="btn btn-warning btn-sm" onclick="toggleBan('${k.license_key}')">${k.status === 'banned' ? 'Unban' : 'Ban'}</button>
                        <button class="btn btn-action btn-sm" onclick="extendKey('${k.license_key}')">+30d</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteKey('${k.license_key}')">Revoke</button>
                    </td>
                </tr>
            `).join('');
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            showToast('Key copied to clipboard');
        }

        function openCreateModal() { document.getElementById('createModal').style.display = 'flex'; }
        function closeCreateModal() { document.getElementById('createModal').style.display = 'none'; }
        function openBulkModal() { 
            document.getElementById('bulkResultArea').style.display = 'none';
            document.getElementById('btnBulkGen').style.display = 'inline-flex';
            document.getElementById('bulkModal').style.display = 'flex'; 
        }
        function closeBulkModal() { document.getElementById('bulkModal').style.display = 'none'; }

        async function submitCreateKey() {
            const note = document.getElementById('modalKeyNote').value;
            const role = document.getElementById('modalKeyRole').value;
            const days = parseInt(document.getElementById('modalKeyDays').value);
            const resets = parseInt(document.getElementById('modalKeyResets').value);
            const res = await fetch('/api/keys/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ note, role, days, max_resets: resets })
            });
            const data = await res.json();
            if (data.success) {
                closeCreateModal();
                showToast('Key Created: ' + data.license_key);
                fetchKeys();
                fetchStats();
            } else {
                alert('Creation failed: ' + data.error);
            }
        }

        async function submitBulkKeys() {
            const count = parseInt(document.getElementById('bulkCount').value);
            const role = document.getElementById('bulkRole').value;
            const days = parseInt(document.getElementById('bulkDays').value);
            const note = document.getElementById('bulkNote').value;
            const res = await fetch('/api/keys/bulk_create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ count, role, days, note })
            });
            const data = await res.json();
            if (data.success) {
                document.getElementById('bulkResultArea').style.display = 'block';
                document.getElementById('bulkResultKeys').value = data.keys.join('\\n');
                document.getElementById('btnBulkGen').style.display = 'none';
                showToast(`Generated ${data.keys.length} keys`);
                fetchKeys();
                fetchStats();
            } else {
                alert('Bulk creation failed: ' + data.error);
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
                showToast('HWID Reset Successful');
                fetchKeys();
            } else {
                alert('Reset failed: ' + data.error);
            }
        }

        async function toggleBan(key) {
            const res = await fetch('/api/keys/toggle_ban', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: key })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Status updated');
                fetchKeys();
                fetchStats();
            }
        }

        async function extendKey(key) {
            const res = await fetch('/api/keys/extend', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: key, days: 30 })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Extended license by +30 days');
                fetchKeys();
            }
        }

        async function deleteKey(key) {
            if (!confirm('Permanently revoke and delete key ' + key + '?')) return;
            const res = await fetch('/api/keys/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: key })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Key Revoked');
                fetchKeys();
                fetchStats();
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const tbody = document.getElementById('logsTable');
                if (!data.logs || data.logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color:var(--text-dim);">No audit records logged yet.</td></tr>';
                    return;
                }
                tbody.innerHTML = data.logs.slice(0, 50).map(l => `
                    <tr>
                        <td>${new Date(l.timestamp * 1000).toLocaleTimeString()}</td>
                        <td><span class="badge">${l.event_type.toUpperCase()}</span></td>
                        <td style="color: var(--accent);">${l.license_key ? l.license_key.substring(0, 16) + '...' : '-'}</td>
                        <td>${l.client_ip || '-'}</td>
                        <td>${l.hwid ? l.hwid.substring(0, 12) + '...' : '-'}</td>
                        <td style="color: var(--text-dim);">${l.details || l.game_data || '-'}</td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }

        // Initialize dashboard
        fetchAll();
        autoRefreshInterval = setInterval(fetchAll, 3000);
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/admin", "/reseller", "/dashboard"]:
            self._send_html(HTML_DASHBOARD)
            return

        elif path == "/api/stats":
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM licenses")
            total_keys = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM licenses WHERE status = 'active'")
            active_keys = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM licenses WHERE status = 'banned'")
            banned_keys = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM licenses WHERE status = 'expired'")
            expired_keys = c.fetchone()[0]

            now = int(time.time())
            since_24h = now - 86400
            c.execute("SELECT COUNT(*) FROM diagnostics WHERE timestamp > ? AND severity IN ('ERROR', 'CRITICAL')", (since_24h,))
            error_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM diagnostics WHERE timestamp > ? AND severity = 'CRITICAL'", (since_24h,))
            critical_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM audit_logs")
            total_logs = c.fetchone()[0]
            conn.close()

            # Query live slot count from orchestrator
            active_slots = 0
            try:
                with urllib.request.urlopen("http://127.0.0.1:9000/api/slots", timeout=1.5) as r:
                    sdata = json.loads(r.read().decode())
                    slots_dict = sdata.get("slots", {})
                    active_slots = sum(1 for s in slots_dict.values() if s.get("status") != "idle")
            except Exception:
                pass

            self._send_json(200, {
                "success": True,
                "stats": {
                    "total_keys": total_keys,
                    "active_keys": active_keys,
                    "banned_keys": banned_keys,
                    "expired_keys": expired_keys,
                    "active_slots": active_slots,
                    "total_slots": 5,
                    "error_diagnostics": error_count,
                    "critical_diagnostics": critical_count,
                    "total_logs": total_logs,
                    "m1_status": "ONLINE"
                }
            })

        elif path == "/api/keys":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM licenses ORDER BY id DESC")
            keys = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "keys": keys})

        elif path == "/api/diagnostics":
            params = parse_qs(parsed.query)
            severity_filter = params.get("severity", [None])[0]
            limit = int(params.get("limit", [100])[0])

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            if severity_filter:
                c.execute("SELECT * FROM diagnostics WHERE severity = ? ORDER BY id DESC LIMIT ?", (severity_filter, limit))
            else:
                c.execute("SELECT * FROM diagnostics ORDER BY id DESC LIMIT ?", (limit,))
            diags = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "diagnostics": diags})

        elif path == "/api/logs":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
            logs = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "logs": logs})

        elif path == "/api/slots":
            # Proxy query directly to local M1 Orchestrator on 9000
            try:
                with urllib.request.urlopen("http://127.0.0.1:9000/api/slots", timeout=2) as r:
                    data = json.loads(r.read().decode())
                    self._send_json(200, data)
            except Exception as e:
                self._send_json(500, {"success": False, "error": f"Orchestrator unreachable: {e}"})

        elif path == "/api/system/health":
            self._send_json(200, {"ok": True, "timestamp": int(time.time())})

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

        # Ingest Telemetry & Crash Report from Client or Orchestrator
        if path == "/api/telemetry/report":
            severity = payload.get("severity", "INFO").upper()
            source = payload.get("source", "CLIENT")
            msg = payload.get("message", "Telemetry Event")
            details = payload.get("details", "")
            key = payload.get("license_key", "")
            hwid = payload.get("hwid", "")
            extra_data = json.dumps(payload.get("extra", {}))

            log_diagnostic(severity, source, msg, details, client_ip, hwid, key, extra_data)
            if severity in ["CRITICAL", "ERROR"]:
                log_event(key, f"client_{severity.lower()}", client_ip, hwid, details=f"[{source}] {msg}")

            self._send_json(200, {"success": True, "received": True})

        # Client authentication & HWID check endpoint
        elif path == "/api/client/auth":
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
                log_event(key, "login_failed", client_ip, hwid, details="Key suspended or banned")
                self._send_json(403, {"success": False, "error": f"License is {row['status']}"})
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
                c.execute("UPDATE licenses SET hwid = ?, last_ip = ?, last_seen = ? WHERE id = ?", (hwid, client_ip, int(time.time()), row["id"]))
                conn.commit()
                log_event(key, "hwid_bound", client_ip, hwid, details="Initial HWID lock bound")
            elif bound_hwid != hwid:
                conn.close()
                log_event(key, "hwid_mismatch", client_ip, hwid, details=f"Expected {bound_hwid[:12]}, got {hwid[:12]}")
                self._send_json(403, {"success": False, "error": "HWID mismatch. Reset HWID in dashboard."})
                return
            else:
                c.execute("UPDATE licenses SET last_ip = ?, last_seen = ? WHERE id = ?", (client_ip, int(time.time()), row["id"]))
                conn.commit()

            conn.close()
            log_event(key, "login_success", client_ip, hwid, details="Client authorized")
            self._send_json(200, {
                "success": True,
                "role": row["role"],
                "expires_at": row["expires_at"],
                "m1_orchestrator": "http://51.159.121.126:9000"
            })

        # Single Key Generation
        elif path == "/api/keys/create":
            note = payload.get("note", "")
            role = payload.get("role", "user")
            days = int(payload.get("days", 30))
            max_resets = int(payload.get("max_resets", 3))
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else ("VANTA-RES-" if role == "reseller" else "VANTA-KEY-")
            key = prefix + uuid.uuid4().hex[:16].upper()

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
            INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
            VALUES (?, ?, 'root', NULL, ?, 'active', ?, ?, ?)
            """, (key, role, max_resets, now, expires, note))
            conn.commit()
            conn.close()

            log_event(key, "key_created", client_ip, details=f"Issued for {days} days, role={role}")
            self._send_json(200, {"success": True, "license_key": key, "expires_at": expires})

        # Bulk Key Generation
        elif path == "/api/keys/bulk_create":
            count = min(int(payload.get("count", 5)), 50)
            role = payload.get("role", "user")
            days = int(payload.get("days", 30))
            note = payload.get("note", "Bulk Created")
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else ("VANTA-RES-" if role == "reseller" else "VANTA-KEY-")

            generated = []
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            for _ in range(count):
                key = prefix + uuid.uuid4().hex[:16].upper()
                c.execute("""
                INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
                VALUES (?, ?, 'root', NULL, 3, 'active', ?, ?, ?)
                """, (key, role, now, expires, note))
                generated.append(key)
            conn.commit()
            conn.close()

            log_event("BULK", "bulk_keys_created", client_ip, details=f"Created {count} keys for {days} days")
            self._send_json(200, {"success": True, "keys": generated})

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

        # Toggle Ban/Active
        elif path == "/api/keys/toggle_ban":
            key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT status FROM licenses WHERE license_key = ?", (key,))
            row = c.fetchone()
            if row:
                new_status = "active" if row[0] == "banned" else "banned"
                c.execute("UPDATE licenses SET status = ? WHERE license_key = ?", (new_status, key))
                conn.commit()
                log_event(key, "status_changed", client_ip, details=f"Status switched to {new_status}")
            conn.close()
            self._send_json(200, {"success": True})

        # Extend Expiry
        elif path == "/api/keys/extend":
            key = payload.get("license_key")
            days = int(payload.get("days", 30))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE licenses SET expires_at = expires_at + ? WHERE license_key = ?", (days * 86400, key))
            conn.commit()
            conn.close()
            log_event(key, "key_extended", client_ip, details=f"Extended by {days} days")
            self._send_json(200, {"success": True})

        # Revoke/Delete key
        elif path == "/api/keys/delete":
            key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM licenses WHERE license_key = ?", (key,))
            conn.commit()
            conn.close()
            log_event(key, "key_deleted", client_ip, details="Key revoked")
            self._send_json(200, {"success": True})

        # Clear Diagnostics
        elif path == "/api/diagnostics/clear":
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM diagnostics")
            conn.commit()
            conn.close()
            self._send_json(200, {"success": True})

        # Slot Emergency Reset
        elif path == "/api/slots/reset":
            try:
                req = urllib.request.Request("http://127.0.0.1:9000/api/slots/reset", method="POST")
                with urllib.request.urlopen(req, timeout=5) as r:
                    res = json.loads(r.read().decode())
                self._send_json(200, res)
            except Exception as e:
                # If orchestrator endpoint is down, run local pkill
                subprocess.run("pkill -9 -f 'LeagueClient' || true", shell=True)
                subprocess.run("pkill -9 -f 'LeagueofLegends' || true", shell=True)
                self._send_json(200, {"success": True, "error": str(e), "message": "Local kill executed"})

        # Slot Specific Kill
        elif path == "/api/slots/kill":
            try:
                body = json.dumps(payload).encode()
                req = urllib.request.Request("http://127.0.0.1:9000/api/slots/kill", data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=3) as r:
                    res = json.loads(r.read().decode())
                self._send_json(200, res)
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})

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
    # Use ThreadingHTTPServer to handle concurrency cleanly
    server = ThreadingHTTPServer(("0.0.0.0", port), VantaHubHandler)
    print(f"[VANTA-HUB] Running Sovereign Hub on http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
'''

with open("vanta_hub_upgraded.py", "w", encoding="utf-8") as f:
    f.write(HUB_CODE)
print(f"Created local vanta_hub_upgraded.py ({len(HUB_CODE)} bytes)")

# Connect to Mac and upload
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_hub.py", "w") as f:
    f.write(HUB_CODE)
sftp.close()
print("Uploaded upgraded vanta_hub.py to Mac M1")

# Kill existing vanta_hub.py and restart
stdin, stdout, stderr = ssh.exec_command("pkill -9 -f vanta_hub.py || true; nohup python3 /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &")
stdout.channel.recv_exit_status()

# Verify hub is running and test endpoints
stdin, stdout, stderr = ssh.exec_command("sleep 1; ps aux | grep vanta_hub; curl -s http://127.0.0.1:8088/api/system/health; curl -s http://127.0.0.1:8088/api/stats")
out = stdout.read().decode("utf-8", "ignore")
print("Hub status & endpoint verification:\n", out)
ssh.close()
