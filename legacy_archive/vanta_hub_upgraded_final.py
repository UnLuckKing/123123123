"""
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
import urllib.error
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

    # Resellers table
    c.execute("""
    CREATE TABLE IF NOT EXISTS resellers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reseller_key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        credits INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        status TEXT DEFAULT 'active'
    )
    """)

    # Automatic column migrations
    for col, col_type in [("last_ip", "TEXT"), ("last_seen", "INTEGER"), ("reseller_id", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE licenses ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    try:
        c.execute("ALTER TABLE resellers ADD COLUMN discord_webhook TEXT")
    except Exception:
        pass

    c.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Cloud Config Sync table (Keybindings, settings per user)
    c.execute("""
    CREATE TABLE IF NOT EXISTS customer_configs (
        license_key TEXT PRIMARY KEY,
        config_data TEXT NOT NULL,
        updated_at INTEGER NOT NULL
    )
    """)

    # Sub-Resellers table (Affiliate / Tiering)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sub_resellers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_key TEXT NOT NULL,
        sub_key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        commission_pct REAL DEFAULT 15.0,
        credits INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL
    )
    """)

    # Crypto automated payment invoices (Section 31)
    c.execute("""
    CREATE TABLE IF NOT EXISTS crypto_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id TEXT UNIQUE NOT NULL,
        reseller_key TEXT NOT NULL,
        crypto_coin TEXT NOT NULL,
        amount_usd REAL NOT NULL,
        crypto_amount REAL NOT NULL,
        deposit_address TEXT NOT NULL,
        credits_to_add INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at INTEGER NOT NULL,
        confirmed_at INTEGER
    )
    """)

    # Reseller White-Label Branding (Section 38)
    c.execute("""
    CREATE TABLE IF NOT EXISTS reseller_branding (
        reseller_key TEXT PRIMARY KEY,
        brand_name TEXT NOT NULL,
        logo_url TEXT,
        discord_url TEXT,
        primary_color TEXT DEFAULT '#00f2fe',
        updated_at INTEGER NOT NULL
    )
    """)

    # Customer Support Tickets (Section 50)
    c.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT UNIQUE NOT NULL,
        license_key TEXT NOT NULL,
        reseller_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """)

    # Referral & Affiliate Reward Engine (Section 49)
    c.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_key TEXT NOT NULL,
        referee_key TEXT UNIQUE NOT NULL,
        bonus_days INTEGER DEFAULT 3,
        created_at INTEGER NOT NULL
    )
    """)

    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('maintenance_mode', 'false')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('maintenance_msg', 'Routine Vanguard telemetry synchronization in progress.')")

    conn.commit()
    conn.close()

def send_discord_webhook(webhook_url, title, description, color=0x00f2fe, fields=None):
    if not webhook_url or not webhook_url.startswith("http"):
        return
    try:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "VANTA // Sovereign Partner Engine"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        if fields:
            embed["fields"] = fields
        data = json.dumps({"embeds": [embed]}).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json", "User-Agent": "VantaHub/5.2"})
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        print(f"[DISCORD-WEBHOOK-ERROR] {e}")

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
            <button class="tab-btn" onclick="switchTab('resellers')">🤝 Reseller Hub <span class="tab-badge" id="resellerBadge">0</span></button>
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

        <!-- TAB 5: Reseller Hub -->
        <div id="tab-resellers" class="tab-content">
            <div class="toolbar">
                <div style="display:flex; gap:10px;">
                    <input type="text" class="search-box" id="resellerSearch" placeholder="Search reseller name or key..." onkeyup="renderResellers()">
                </div>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-primary" onclick="openCreateResellerModal()">+ Add New Reseller</button>
                    <button class="btn btn-action" onclick="fetchResellers()">🔄 Refresh</button>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>RESELLER NAME</th>
                            <th>ACCESS KEY</th>
                            <th>AVAILABLE CREDITS</th>
                            <th>KEYS ISSUED</th>
                            <th>STATUS</th>
                            <th>CREATED</th>
                            <th>ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody id="resellersTable">
                        <tr><td colspan="7" style="text-align:center; color:var(--text-dim);">Loading resellers...</td></tr>
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

    <!-- Create Reseller Modal -->
    <div class="modal-overlay" id="createResellerModal">
        <div class="modal">
            <h2>Add New Reseller Partner</h2>
            <div class="modal-body">
                <div class="form-group">
                    <label>Reseller / Partner Name</label>
                    <input type="text" class="form-control" id="resellerNameInput" placeholder="e.g. Nexus Store TR">
                </div>
                <div class="form-group">
                    <label>Initial License Credits (1 Credit = 1 Customer License)</label>
                    <input type="number" class="form-control" id="resellerInitialCredits" value="10" min="1" max="10000">
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-action" onclick="closeCreateResellerModal()">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateReseller()">Create Partner</button>
            </div>
        </div>
    </div>

    <!-- Add Credits Modal -->
    <div class="modal-overlay" id="addCreditsModal">
        <div class="modal">
            <h2>Top Up Reseller Balance</h2>
            <div class="modal-body">
                <div class="form-group">
                    <label>Reseller Partner</label>
                    <input type="text" class="form-control" id="addCreditsTargetName" readonly style="opacity:0.7;">
                    <input type="hidden" id="addCreditsTargetKey">
                </div>
                <div class="form-group">
                    <label>Credits to Add</label>
                    <input type="number" class="form-control" id="addCreditsAmount" value="20" min="1" max="10000">
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-action" onclick="closeAddCreditsModal()">Cancel</button>
                <button class="btn btn-primary" onclick="submitAddCredits()">Add Credits</button>
            </div>
        </div>
    </div>

    <!-- Reseller Portal Inspector Modal -->
    <div class="modal-overlay" id="resellerPortalModal">
        <div class="modal" style="max-width: 800px;">
            <h2 id="portalResellerTitle">Reseller Partner Portal</h2>
            <div class="modal-body">
                <div style="display:flex; justify-content:space-between; align-items:center; background:#080b11; padding:14px; border-radius:8px; margin-bottom:16px; border:1px solid var(--surface-border);">
                    <div>
                        <div style="font-size:11px; color:var(--text-dim); text-transform:uppercase;">Current Balance</div>
                        <div style="font-size:24px; font-weight:700; color:var(--accent);" id="portalResellerBalance">0 Credits</div>
                    </div>
                    <button class="btn btn-primary" onclick="portalGenerateKey()">⚡ Generate 30-Day License (1 Credit)</button>
                </div>
                <div style="font-size:12px; color:var(--text-dim); margin-bottom:8px; font-weight:600;">KEYS ISSUED BY THIS RESELLER:</div>
                <div style="max-height:260px; overflow-y:auto; border:1px solid var(--surface-border); border-radius:8px;">
                    <table>
                        <thead>
                            <tr>
                                <th>LICENSE KEY</th>
                                <th>HWID</th>
                                <th>STATUS</th>
                                <th>EXPIRES</th>
                            </tr>
                        </thead>
                        <tbody id="portalKeysTable">
                            <tr><td colspan="4" style="text-align:center;">No keys generated yet.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="closeResellerPortalModal()">Close</button>
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
            await Promise.all([fetchStats(), fetchDiagnostics(), fetchSlots(), fetchKeys(), fetchResellers(), fetchLogs()]);
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
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('Key copied: ' + text);
                }).catch(() => {
                    fallbackCopy(text);
                });
            } else {
                fallbackCopy(text);
            }
        }

        function fallbackCopy(text) {
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            textArea.style.left = "-999999px";
            textArea.style.top = "-999999px";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    showToast('Key copied: ' + text);
                } else {
                    prompt('Copy license key:', text);
                }
            } catch (err) {
                prompt('Copy license key:', text);
            }
            document.body.removeChild(textArea);
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

        let allResellers = [];
        let activePortalResellerKey = null;

        async function fetchResellers() {
            try {
                const res = await fetch('/api/admin/resellers');
                const data = await res.json();
                if (data.success) {
                    allResellers = data.resellers || [];
                    document.getElementById('resellerBadge').innerText = allResellers.length;
                    renderResellers();
                }
            } catch(e) { console.error(e); }
        }

        function renderResellers() {
            const q = document.getElementById('resellerSearch').value.toLowerCase();
            const tbody = document.getElementById('resellersTable');
            let filtered = allResellers;
            if (q) {
                filtered = filtered.filter(r => r.name.toLowerCase().includes(q) || r.reseller_key.toLowerCase().includes(q));
            }
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-dim);">No reseller partners registered yet.</td></tr>';
                return;
            }
            tbody.innerHTML = filtered.map(r => `
                <tr>
                    <td style="font-weight:700; color:#fff;">${r.name}</td>
                    <td style="color:var(--accent); cursor:pointer;" onclick="copyToClipboard('${r.reseller_key}')" title="Click to copy key">
                        ${r.reseller_key} 📋
                    </td>
                    <td style="color:var(--warning); font-weight:700; font-size:14px;">${r.credits} Credits</td>
                    <td><span class="badge badge-vip">${r.keys_count || 0} Keys</span></td>
                    <td><span class="status-pill status-${r.status}"></span>${r.status.toUpperCase()}</td>
                    <td>${new Date(r.created_at * 1000).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="openAddCreditsModal('${r.reseller_key}', '${r.name}')">+ Credits</button>
                        <button class="btn btn-action btn-sm" onclick="window.open('/reseller?key=' + encodeURIComponent('${r.reseller_key}'), '_blank')">Open Portal ↗</button>
                        <button class="btn btn-action btn-sm" onclick="copyToClipboard(window.location.origin + '/reseller?key=' + encodeURIComponent('${r.reseller_key}'))" title="Copy Partner Access Link">Copy Link</button>
                        <button class="btn btn-warning btn-sm" onclick="toggleReseller('${r.reseller_key}')">${r.status === 'active' ? 'Suspend' : 'Activate'}</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteReseller('${r.reseller_key}', '${r.name}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        }

        function openCreateResellerModal() {
            document.getElementById('createResellerModal').style.display = 'flex';
        }
        function closeCreateResellerModal() {
            document.getElementById('createResellerModal').style.display = 'none';
        }

        async function submitCreateReseller() {
            const name = document.getElementById('resellerNameInput').value.trim();
            const credits = parseInt(document.getElementById('resellerInitialCredits').value) || 0;
            if (!name) return alert('Please enter reseller name');
            const res = await fetch('/api/admin/reseller/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, credits })
            });
            const data = await res.json();
            if (data.success) {
                closeCreateResellerModal();
                showToast(`Reseller ${data.name} created!`);
                fetchResellers();
            } else {
                alert('Failed to create reseller: ' + data.error);
            }
        }

        function openAddCreditsModal(key, name) {
            document.getElementById('addCreditsTargetKey').value = key;
            document.getElementById('addCreditsTargetName').value = name;
            document.getElementById('addCreditsModal').style.display = 'flex';
        }
        function closeAddCreditsModal() {
            document.getElementById('addCreditsModal').style.display = 'none';
        }

        async function submitAddCredits() {
            const reseller_key = document.getElementById('addCreditsTargetKey').value;
            const credits = parseInt(document.getElementById('addCreditsAmount').value) || 0;
            const res = await fetch('/api/admin/reseller/add_credits', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key, credits })
            });
            const data = await res.json();
            if (data.success) {
                closeAddCreditsModal();
                showToast(`Credits added! New balance: ${data.credits}`);
                fetchResellers();
            } else {
                alert('Failed to add credits: ' + data.error);
            }
        }

        async function deleteReseller(key, name) {
            if (!confirm(`Permanently delete reseller partner '${name}' (${key})?`)) return;
            const res = await fetch('/api/admin/reseller/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: key })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Reseller '${name}' deleted`);
                fetchResellers();
            } else {
                alert('Delete failed: ' + data.error);
            }
        }

        async function toggleReseller(key) {
            const res = await fetch('/api/admin/reseller/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: key })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Reseller status updated: ' + data.status);
                fetchResellers();
            }
        }

        async function openResellerPortal(key) {
            activePortalResellerKey = key;
            const res = await fetch('/api/reseller/info?key=' + encodeURIComponent(key));
            const data = await res.json();
            if (data.success) {
                const r = data.reseller;
                document.getElementById('portalResellerTitle').innerText = `Portal // ${r.name} (${r.status.toUpperCase()})`;
                document.getElementById('portalResellerBalance').innerText = `${r.credits} Credits`;
                const tbody = document.getElementById('portalKeysTable');
                if (!r.keys || r.keys.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-dim);">No customer keys generated yet. Click Generate Key above.</td></tr>';
                } else {
                    tbody.innerHTML = r.keys.map(k => `
                        <tr>
                            <td style="color:var(--accent); font-weight:700; cursor:pointer;" onclick="copyToClipboard('${k.license_key}')">${k.license_key} 📋</td>
                            <td>${k.hwid ? k.hwid.substring(0,14) + '...' : '<span style="color:#555;">Unbound</span>'}</td>
                            <td><span class="status-pill status-${k.status}"></span>${k.status.toUpperCase()}</td>
                            <td>${new Date(k.expires_at * 1000).toLocaleDateString()}</td>
                        </tr>
                    `).join('');
                }
                document.getElementById('resellerPortalModal').style.display = 'flex';
            } else {
                alert('Portal error: ' + data.error);
            }
        }

        function closeResellerPortalModal() {
            document.getElementById('resellerPortalModal').style.display = 'none';
            activePortalResellerKey = null;
        }

        async function portalGenerateKey() {
            if (!activePortalResellerKey) return;
            const res = await fetch('/api/reseller/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: activePortalResellerKey, days: 30, role: 'user', note: 'Portal Web Generation' })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Key generated: ' + data.license_key);
                openResellerPortal(activePortalResellerKey);
                fetchResellers();
                fetchKeys();
                fetchStats();
            } else {
                alert('Generation failed: ' + data.error);
            }
        }

        // Initialize dashboard
        fetchAll();
        autoRefreshInterval = setInterval(fetchAll, 3000);
    </script>
</body>
</html>
"""

HTML_RESELLER_PORTAL = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VANTA // Reseller Partner Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #07090e;
            --surface: #0e121a;
            --surface-card: #131824;
            --surface-hover: #192030;
            --surface-border: #1f2738;
            --accent: #00f2fe;
            --accent-glow: rgba(0, 242, 254, 0.35);
            --danger: #ff3366;
            --warning: #ffaa00;
            --success: #00ffaa;
            --purple: #a855f7;
            --text-main: #f0f4fc;
            --text-dim: #7e8ba6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 1280px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--surface-border);
            margin-bottom: 24px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand h1 {
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
            color: #fff;
        }
        .brand span {
            color: var(--accent);
            text-shadow: 0 0 10px var(--accent-glow);
        }
        .badge {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
        }
        .badge-partner { background: rgba(0, 242, 254, 0.15); color: var(--accent); border: 1px solid var(--accent); }
        .badge-vip { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; }
        .badge-success { background: rgba(0, 255, 170, 0.15); color: var(--success); border: 1px solid var(--success); }
        .badge-warning { background: rgba(255, 170, 0, 0.15); color: var(--warning); border: 1px solid var(--warning); }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .credits-pill {
            background: var(--surface-card);
            border: 1px solid var(--surface-border);
            padding: 8px 18px;
            border-radius: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .credits-pill b { color: var(--warning); font-size: 16px; }

        /* Auth Screen */
        #authSection {
            max-width: 460px;
            margin: 80px auto;
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            padding: 36px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6);
        }
        #authSection h2 { font-size: 22px; margin-bottom: 8px; font-weight: 700; }
        #authSection p { color: var(--text-dim); font-size: 14px; margin-bottom: 24px; line-height: 1.5; }
        
        .form-control {
            width: 100%;
            background: #090c13;
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 12px 14px;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
            margin-bottom: 16px;
        }
        .form-control:focus { border-color: var(--accent); }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 0.5px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            font-family: 'Outfit', sans-serif;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            color: #000;
        }
        .btn-primary:hover { box-shadow: 0 0 15px var(--accent-glow); transform: translateY(-1px); }
        .btn-action { background: var(--surface-card); color: #fff; border: 1px solid var(--surface-border); }
        .btn-action:hover { background: var(--surface-hover); border-color: var(--accent); }
        .btn-warning { background: rgba(255, 170, 0, 0.15); color: var(--warning); border: 1px solid var(--warning); }
        .btn-warning:hover { background: rgba(255, 170, 0, 0.25); }
        .btn-danger { background: rgba(255, 51, 102, 0.15); color: var(--danger); border: 1px solid var(--danger); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }

        /* Dashboard Screen */
        #portalSection { display: none; width: 100%; }
        
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }
        .kpi-title { font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .kpi-value { font-size: 28px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }

        .tabs-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 12px;
        }
        .tab-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-dim);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .tab-btn:hover { color: #fff; background: var(--surface-hover); }
        .tab-btn.active { color: var(--accent); background: var(--surface-card); border-color: var(--accent); }

        .tab-pane { display: none; }
        .tab-pane.active { display: block; }

        .panels-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        @media (max-width: 960px) { .panels-grid { grid-template-columns: 1fr; } }

        .card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 24px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--surface-border);
        }
        .card-header h3 { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: 0.5px; }

        .form-group { margin-bottom: 16px; text-align: left; }
        .form-group label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }

        .table-wrap {
            overflow-x: auto;
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            background: var(--surface);
        }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
        th { background: #0c0f17; color: var(--text-dim); font-size: 11px; padding: 12px 14px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid var(--surface-border); }
        td { padding: 12px 14px; border-bottom: 1px solid var(--surface-border); font-family: 'JetBrains Mono', monospace; vertical-align: middle; }
        tr:hover td { background: var(--surface-hover); }

        .status-pill { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-active { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-expired { background: var(--danger); }

        .api-snippet {
            background: #06080d;
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #79c0ff;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            margin-top: 10px;
        }

        /* Success Mint Result Banner */
        .mint-result-card {
            background: rgba(0, 242, 254, 0.05);
            border: 1px solid var(--accent);
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 20px;
            display: none;
        }
        .mint-key-box {
            font-size: 18px;
            font-weight: 800;
            color: var(--accent);
            font-family: 'JetBrains Mono', monospace;
            padding: 12px;
            background: #080b11;
            border: 1px solid rgba(0,242,254,0.3);
            border-radius: 8px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--surface-card);
            border: 1px solid var(--accent);
            color: #fff;
            padding: 14px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            display: none;
            z-index: 10000;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>VANTA <span>// RESELLER</span></h1>
                <span class="badge badge-partner">Partner Portal</span>
            </div>
            <div class="header-actions" id="topBarUser" style="display:none;">
                <div class="credits-pill">
                    AVAILABLE: <b id="resellerCredits">0</b> CREDITS
                </div>
                <button class="btn btn-action btn-sm" onclick="logoutReseller()">Sign Out</button>
            </div>
        </header>

        <!-- Login Screen -->
        <div id="authSection">
            <h2>Partner Portal Sign In</h2>
            <p>Enter your Vanta Reseller Partner Access Key to manage client licenses, generate stock, and inspect hardware bindings.</p>
            <input type="text" class="form-control" id="resellerKeyInput" placeholder="VANTA-RSL-XXXXXXXXXXXXXXXX" onkeydown="if(event.key==='Enter') loginReseller()">
            <button class="btn btn-primary" style="width:100%;" onclick="loginReseller()">Access Partner Console</button>
        </div>

        <!-- Dashboard Screen -->
        <div id="portalSection">
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-title">Account Balance</div>
                    <div class="kpi-value" style="color:var(--warning);" id="kpiCredits">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Issued Licenses</div>
                    <div class="kpi-value" style="color:var(--accent);" id="kpiKeysCount">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Active Subscriptions</div>
                    <div class="kpi-value" style="color:var(--success);" id="kpiActiveCount">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Partner Status</div>
                    <div class="kpi-value" style="color:#fff;" id="kpiStatus">ACTIVE</div>
                </div>
            </div>

            <!-- Single Mint Result Box (When generated) -->
            <div class="mint-result-card" id="mintSuccessBox">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:700; color:var(--success);">✅ License Key Generated Successfully!</div>
                    <span style="cursor:pointer; color:var(--text-dim);" onclick="document.getElementById('mintSuccessBox').style.display='none'">✕ Dismiss</span>
                </div>
                <div class="mint-key-box">
                    <span id="mintedKeyDisplay">VANTA-KEY-XXXXXXXXXXXXXXXX</span>
                    <button class="btn btn-primary btn-sm" onclick="copyMintedKey()">📋 Copy Key</button>
                </div>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-action btn-sm" onclick="copyCustomerHandout()">📦 Copy Customer Handout (Discord / Shoppy Template)</button>
                </div>
            </div>

            <!-- Tabs Navigation -->
            <div class="tabs-nav">
                <button class="tab-btn active" onclick="switchPortalTab('keys')">🔑 Licenses & Stock</button>
                <button class="tab-btn" onclick="switchPortalTab('mint')">⚡ Mint New License</button>
                <button class="tab-btn" onclick="switchPortalTab('subs')">👥 Sub-Resellers</button>
                <button class="tab-btn" onclick="switchPortalTab('settings')">⚙️ Webhooks & API</button>
            </div>

            <!-- TAB 1: Keys Table -->
            <div class="tab-pane active" id="pane-keys">
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-header">
                        <h3>Issued Customer Licenses</h3>
                        <div style="display:flex; gap:10px; align-items:center;">
                            <input type="text" class="form-control" style="margin-bottom:0; width:260px; padding:6px 12px; font-size:13px;" id="keySearchInput" placeholder="Search key or note..." oninput="renderTable()">
                            <button class="btn btn-warning btn-sm" onclick="openBulkMintModal()">📦 Bulk Mint Stock</button>
                            <button class="btn btn-action btn-sm" onclick="loadResellerData()">🔄 Refresh</button>
                        </div>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>LICENSE KEY</th>
                                    <th>TIER</th>
                                    <th>CUSTOMER REF / NOTE</th>
                                    <th>BOUND HWID</th>
                                    <th>STATUS</th>
                                    <th>EXPIRES AT</th>
                                    <th>ACTIONS</th>
                                </tr>
                            </thead>
                            <tbody id="keysTableBody">
                                <tr><td colspan="7" style="text-align:center; color:var(--text-dim); padding:20px;">Loading client keys...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 2: Mint Panel -->
            <div class="tab-pane" id="pane-mint">
                <div class="panels-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3>⚡ Single License Mint</h3>
                            <span class="badge badge-partner">1 Credit Per Key</span>
                        </div>
                        <div class="form-group">
                            <label>Plan Duration</label>
                            <select class="form-control" id="mintDays">
                                <option value="1">1 Day Access (1 Credit)</option>
                                <option value="7">7 Days Weekly (1 Credit)</option>
                                <option value="30" selected>30 Days Monthly (1 Credit)</option>
                                <option value="90">90 Days Quarterly (1 Credit)</option>
                                <option value="365">1 Year / Lifetime (1 Credit)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>License Tier</label>
                            <select class="form-control" id="mintRole">
                                <option value="user">Standard User (Match Bypass)</option>
                                <option value="vip">VIP Member (Priority VM Queue)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Customer Reference / Order ID</label>
                            <input type="text" class="form-control" id="mintNote" placeholder="e.g. Discord: User#1337 or Sellix: #10492">
                        </div>
                        <button class="btn btn-primary" style="width:100%;" onclick="generateKey()">⚡ Generate Customer License</button>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h3>📦 Bulk Stock Minting</h3>
                            <span class="badge badge-warning">For Store Stock</span>
                        </div>
                        <p style="font-size:13px; color:var(--text-dim); margin-bottom:16px; line-height:1.6;">
                            Generate batches of license keys in line-by-line format for Sellix, Shoppy, Eldorado, or Discord stock channels.
                        </p>
                        <button class="btn btn-warning" style="width:100%;" onclick="openBulkMintModal()">📦 Open Bulk Generator</button>
                    </div>
                </div>
            </div>

            <!-- TAB 3: Sub-Resellers -->
            <div class="tab-pane" id="pane-subs">
                <div class="panels-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3>Add Sub-Partner</h3>
                            <span class="badge badge-partner">Network Expansion</span>
                        </div>
                        <div class="form-group">
                            <label>Sub-Reseller Name</label>
                            <input type="text" class="form-control" id="subName" placeholder="e.g. EU Region Sub-Distributor">
                        </div>
                        <div class="form-group">
                            <label>Commission Percentage (%)</label>
                            <input type="number" class="form-control" id="subCommission" value="15" min="0" max="50">
                        </div>
                        <div class="form-group">
                            <label>Credits to Allocate (Deducted from your balance)</label>
                            <input type="number" class="form-control" id="subCredits" value="5" min="0">
                        </div>
                        <button class="btn btn-primary" style="width:100%;" onclick="createSubReseller()">+ Create Sub-Reseller</button>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h3>My Sub-Resellers</h3>
                            <button class="btn btn-action btn-sm" onclick="loadSubResellers()">🔄 Refresh</button>
                        </div>
                        <div class="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>NAME</th>
                                        <th>KEY</th>
                                        <th>CREDITS</th>
                                        <th>COMMISSION</th>
                                    </tr>
                                </thead>
                                <tbody id="subsTableBody">
                                    <tr><td colspan="4" style="text-align:center; color:var(--text-dim); padding:16px;">Loading sub-resellers...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 4: Settings & Automation -->
            <div class="tab-pane" id="pane-settings">
                <div class="panels-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3>Discord Webhook Integration</h3>
                            <span class="badge badge-vip">Real-Time Alerts</span>
                        </div>
                        <p style="font-size:13px; color:var(--text-dim); margin-bottom:14px;">
                            Receive instant notifications on your Discord server whenever a customer redeems a license or resets HWID.
                        </p>
                        <div class="form-group">
                            <label>Discord Webhook URL</label>
                            <input type="text" class="form-control" id="discordWebhookInput" placeholder="https://discord.com/api/webhooks/...">
                        </div>
                        <button class="btn btn-primary" onclick="saveWebhookSettings()">Save Discord Webhook</button>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h3>Automated Store API</h3>
                            <span class="badge badge-partner">Sellix / Shoppy Integration</span>
                        </div>
                        <div class="form-group">
                            <label>Your Bearer Token</label>
                            <input type="text" class="form-control" id="apiTokenDisplay" readonly onclick="copyText(this.value)">
                        </div>
                        <div class="form-group">
                            <label>cURL Mint Command Snippet</label>
                            <div class="api-snippet" id="apiCurlSnippet">Loading API configuration...</div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Bulk Mint Modal -->
    <div style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; justify-content:center; align-items:center;" id="bulkModal">
        <div style="background:var(--surface); border:1px solid var(--surface-border); border-radius:14px; padding:28px; width:100%; max-width:550px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <h3 style="color:#fff;">📦 Bulk Mint Licenses (Store Stock)</h3>
                <span style="cursor:pointer; color:#aaa; font-size:20px;" onclick="closeBulkMintModal()">✕</span>
            </div>
            <div class="form-group">
                <label>Number of Keys to Mint</label>
                <select class="form-control" id="bulkCount">
                    <option value="5">5 Keys (5 Credits)</option>
                    <option value="10" selected>10 Keys (10 Credits)</option>
                    <option value="25">25 Keys (25 Credits)</option>
                    <option value="50">50 Keys (50 Credits)</option>
                    <option value="100">100 Keys (100 Credits)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Plan Duration</label>
                <select class="form-control" id="bulkDays">
                    <option value="1">1 Day Access</option>
                    <option value="7">7 Days Access</option>
                    <option value="30" selected>30 Days Access</option>
                    <option value="90">90 Days Access</option>
                    <option value="365">1 Year / Lifetime</option>
                </select>
            </div>
            <div class="form-group">
                <label>Stock Order Note / Batch ID</label>
                <input type="text" class="form-control" id="bulkNote" placeholder="e.g. Sellix Stock Batch #4">
            </div>
            <button class="btn btn-primary" style="width:100%;" onclick="executeBulkMint()">⚡ Confirm & Mint Stock</button>

            <!-- Results Output Area -->
            <div id="bulkResultsBox" style="display:none; margin-top:16px;">
                <label style="font-size:12px; color:var(--success); font-weight:700;">✅ Stock Generated Successfully! (Line-by-Line format for Sellix/Shoppy):</label>
                <textarea class="form-control" id="bulkOutputArea" rows="6" readonly style="font-size:12px; margin-top:6px;"></textarea>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-action btn-sm" style="flex:1;" onclick="copyBulkStock()">📋 Copy All to Clipboard</button>
                    <button class="btn btn-action btn-sm" style="flex:1;" onclick="downloadBulkTxt()">💾 Download stock.txt</button>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        // Check URL Query param ?key= first for seamless single-click login
        const urlParams = new URLSearchParams(window.location.search);
        const queryKey = urlParams.get('key');
        let currentResellerKey = queryKey || localStorage.getItem('vanta_reseller_key') || '';
        let resellerData = null;
        let lastMintedKey = '';

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        function copyText(str) {
            if (!str) return;
            navigator.clipboard.writeText(str);
            showToast('Copied to clipboard: ' + str);
        }

        function switchPortalTab(tabName) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            
            const targetPane = document.getElementById('pane-' + tabName);
            if (targetPane) targetPane.classList.add('active');
            
            event.currentTarget.classList.add('active');
            if (tabName === 'subs') loadSubResellers();
        }

        async function loginReseller() {
            const key = document.getElementById('resellerKeyInput').value.trim();
            if (!key) return alert('Please enter your reseller key');
            currentResellerKey = key;
            await loadResellerData();
        }

        function logoutReseller() {
            localStorage.removeItem('vanta_reseller_key');
            currentResellerKey = '';
            document.getElementById('authSection').style.display = 'block';
            document.getElementById('portalSection').style.display = 'none';
            document.getElementById('topBarUser').style.display = 'none';
        }

        async function loadResellerData() {
            if (!currentResellerKey) return;
            try {
                const res = await fetch('/api/reseller/info?key=' + encodeURIComponent(currentResellerKey));
                const data = await res.json();
                if (!data.success) {
                    alert('Authentication failed: ' + (data.error || 'Invalid key'));
                    logoutReseller();
                    return;
                }
                localStorage.setItem('vanta_reseller_key', currentResellerKey);
                resellerData = data.reseller;
                renderDashboard();
            } catch (err) {
                alert('Connection error to Sovereign Hub: ' + err);
            }
        }

        function renderDashboard() {
            document.getElementById('authSection').style.display = 'none';
            document.getElementById('portalSection').style.display = 'block';
            document.getElementById('topBarUser').style.display = 'flex';

            document.getElementById('resellerCredits').innerText = resellerData.credits || 0;
            document.getElementById('kpiCredits').innerText = resellerData.credits || 0;
            document.getElementById('kpiKeysCount').innerText = resellerData.keys ? resellerData.keys.length : 0;
            
            const activeCount = (resellerData.keys || []).filter(k => k && k.status === 'active').length;
            document.getElementById('kpiActiveCount').innerText = activeCount;
            document.getElementById('kpiStatus').innerText = (resellerData.status || 'ACTIVE').toUpperCase();

            document.getElementById('apiTokenDisplay').value = currentResellerKey;
            document.getElementById('apiCurlSnippet').innerText = 
`curl -X POST http://51.159.121.126:8088/api/v1/reseller/mint_key \
  -H "Authorization: Bearer ${currentResellerKey}" \
  -H "Content-Type: application/json" \
  -d '{"days": 30, "role": "user", "note": "Order #1042"}'`;

            if (resellerData.discord_webhook) {
                document.getElementById('discordWebhookInput').value = resellerData.discord_webhook;
            }

            renderTable();
        }

        function renderTable() {
            const tbody = document.getElementById('keysTableBody');
            const searchInput = document.getElementById('keySearchInput');
            const q = (searchInput ? searchInput.value : '').toLowerCase();
            const keys = (resellerData.keys || []).filter(k => {
                if (!k) return false;
                const lic = (k.license_key || '').toLowerCase();
                const note = (k.note || '').toLowerCase();
                return lic.includes(q) || note.includes(q);
            });

            if (keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-dim); padding:24px;">No issued keys found matching query.</td></tr>';
                return;
            }

            tbody.innerHTML = keys.map(k => {
                const licKey = k.license_key || 'UNKNOWN';
                const roleStr = (k.role || 'user').toUpperCase();
                const statusStr = (k.status || 'active').toLowerCase();
                const expDate = k.expires_at ? new Date(k.expires_at * 1000).toLocaleDateString() : 'Lifetime';
                const hwidDisplay = k.hwid ? `<span style="color:#aaa;">${k.hwid.substring(0,12)}...</span>` : '<span style="color:var(--success); font-weight:700;">Unbound</span>';
                
                return `
                <tr>
                    <td style="color:var(--accent); font-weight:700; cursor:pointer;" onclick="copyText('${licKey}')" title="Click to copy">
                        ${licKey} 📋
                    </td>
                    <td><span class="badge ${k.role === 'vip' ? 'badge-vip' : 'badge-partner'}">${roleStr}</span></td>
                    <td style="color:#fff;">${k.note || '—'}</td>
                    <td>${hwidDisplay}</td>
                    <td><span class="status-pill status-${statusStr}"></span>${statusStr.toUpperCase()}</td>
                    <td>${expDate}</td>
                    <td>
                        <button class="btn btn-action btn-sm" onclick="resetCustomerHWID('${licKey}')">Reset HWID</button>
                    </td>
                </tr>
                `;
            }).join('');
        }

        async function generateKey() {
            const days = parseInt(document.getElementById('mintDays').value) || 30;
            const role = document.getElementById('mintRole').value;
            const note = document.getElementById('mintNote').value.trim() || 'Reseller Portal Mint';

            if (resellerData.credits < 1) {
                return alert('Insufficient credits. Contact Root Admin to top up your balance.');
            }

            const res = await fetch('/api/reseller/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: currentResellerKey, days, role, note })
            });
            const data = await res.json();
            if (data.success) {
                lastMintedKey = data.license_key;
                document.getElementById('mintedKeyDisplay').innerText = data.license_key;
                document.getElementById('mintSuccessBox').style.display = 'block';
                showToast('Key generated: ' + data.license_key);
                loadResellerData();
            } else {
                alert('Generation failed: ' + data.error);
            }
        }

        function copyMintedKey() {
            if (lastMintedKey) copyText(lastMintedKey);
        }

        function copyCustomerHandout() {
            if (!lastMintedKey) return;
            const template = 
`━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 VANTA // ZERO-DETECTION LICENSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━
License Key: ${lastMintedKey}
Client Tier: Standard / VIP
Status: READY FOR ACTIVATION

Setup Instructions:
1. Launch VANTA.exe client
2. Enter your License Key above
3. Click 'Start Bypass'
━━━━━━━━━━━━━━━━━━━━━━━━━━━`;
            navigator.clipboard.writeText(template);
            showToast('Customer Handout copied to clipboard!');
        }

        async function resetCustomerHWID(license_key) {
            if (!confirm(`Reset Hardware ID binding for ${license_key}?`)) return;
            const res = await fetch('/api/reseller/reset_hwid', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: currentResellerKey, license_key })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Customer HWID successfully unbound!');
                loadResellerData();
            } else {
                alert('Reset failed: ' + data.error);
            }
        }

        async function saveWebhookSettings() {
            const webhook = document.getElementById('discordWebhookInput').value.trim();
            const res = await fetch('/api/reseller/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: currentResellerKey, discord_webhook: webhook })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Discord Webhook settings saved!');
            } else {
                alert('Failed to save settings: ' + data.error);
            }
        }

        async function loadSubResellers() {
            try {
                const res = await fetch('/api/reseller/sub/list?key=' + encodeURIComponent(currentResellerKey));
                const data = await res.json();
                const tbody = document.getElementById('subsTableBody');
                if (data.success && data.sub_resellers && data.sub_resellers.length > 0) {
                    tbody.innerHTML = data.sub_resellers.map(s => `
                        <tr>
                            <td style="color:#fff; font-weight:700;">${s.name}</td>
                            <td style="color:var(--accent); cursor:pointer;" onclick="copyText('${s.sub_key}')">${s.sub_key} 📋</td>
                            <td style="color:var(--warning);">${s.credits} Credits</td>
                            <td>${s.commission_pct}%</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-dim); padding:16px;">No sub-resellers created yet.</td></tr>';
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function createSubReseller() {
            const name = document.getElementById('subName').value.trim();
            const commission_pct = parseFloat(document.getElementById('subCommission').value) || 15;
            const credits = parseInt(document.getElementById('subCredits').value) || 0;

            if (!name) return alert('Please enter sub-reseller name');
            if (credits > (resellerData.credits || 0)) {
                return alert('Insufficient balance to allocate ' + credits + ' credits.');
            }

            const res = await fetch('/api/reseller/sub/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ parent_key: currentResellerKey, name, commission_pct, credits })
            });
            const data = await res.json();
            if (data.success) {
                alert(`Sub-Reseller created!\nKey: ${data.sub_key}\nCredits: ${data.credits}`);
                document.getElementById('subName').value = '';
                loadResellerData();
                loadSubResellers();
            } else {
                alert('Failed: ' + data.error);
            }
        }

        function openBulkMintModal() {
            document.getElementById('bulkModal').style.display = 'flex';
            document.getElementById('bulkResultsBox').style.display = 'none';
        }
        function closeBulkMintModal() {
            document.getElementById('bulkModal').style.display = 'none';
        }
        async function executeBulkMint() {
            const count = parseInt(document.getElementById('bulkCount').value) || 10;
            const days = parseInt(document.getElementById('bulkDays').value) || 30;
            const note = document.getElementById('bulkNote').value.trim() || 'Bulk Stock Batch';

            if (resellerData.credits < count) {
                return alert(`Insufficient credits. You need ${count} credits to mint this batch.`);
            }

            const res = await fetch('/api/reseller/bulk_generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ reseller_key: currentResellerKey, count, days, role: 'user', note })
            });
            const data = await res.json();
            if (data.success) {
                document.getElementById('bulkOutputArea').value = data.keys.join('\n');
                document.getElementById('bulkResultsBox').style.display = 'block';
                showToast(`Successfully minted ${data.count} keys!`);
                loadResellerData();
            } else {
                alert('Bulk mint failed: ' + data.error);
            }
        }
        function copyBulkStock() {
            const txt = document.getElementById('bulkOutputArea').value;
            navigator.clipboard.writeText(txt);
            showToast('All stock keys copied to clipboard!');
        }
        function downloadBulkTxt() {
            const txt = document.getElementById('bulkOutputArea').value;
            const blob = new Blob([txt], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `vanta_keys_batch_${Date.now()}.txt`;
            a.click();
        }

        if (currentResellerKey) {
            loadResellerData();
        }
    </script>
</body>
</html>"""

HTML_CUSTOMER_PORTAL = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VANTA // Client Access & License Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #07090e;
            --surface: #0e121a;
            --surface-card: #131824;
            --surface-hover: #192030;
            --surface-border: #1f2738;
            --accent: #00f2fe;
            --accent-glow: rgba(0, 242, 254, 0.35);
            --danger: #ff3366;
            --warning: #ffaa00;
            --success: #00ffaa;
            --text-main: #f0f4fc;
            --text-dim: #7e8ba6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 900px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--surface-border);
            margin-bottom: 24px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand h1 {
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
            color: #fff;
        }
        .brand span {
            color: var(--accent);
            text-shadow: 0 0 10px var(--accent-glow);
        }
        .badge {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
        }
        .badge-vip { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; }
        .badge-active { background: rgba(0, 255, 170, 0.15); color: var(--success); border: 1px solid var(--success); }
        .badge-expired { background: rgba(255, 51, 102, 0.15); color: var(--danger); border: 1px solid var(--danger); }

        /* Auth Screen */
        #authCard {
            max-width: 440px;
            margin: 80px auto;
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            padding: 36px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6);
        }
        #authCard h2 { font-size: 20px; margin-bottom: 8px; }
        #authCard p { color: var(--text-dim); font-size: 14px; margin-bottom: 24px; }

        .form-control {
            width: 100%;
            background: #090c13;
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 12px 14px;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
            margin-bottom: 16px;
        }
        .form-control:focus { border-color: var(--accent); }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 0.5px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            font-family: 'Outfit', sans-serif;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            color: #000;
        }
        .btn-primary:hover { box-shadow: 0 0 15px var(--accent-glow); transform: translateY(-1px); }
        .btn-action { background: var(--surface-card); color: #fff; border: 1px solid var(--surface-border); }
        .btn-action:hover { background: var(--surface-hover); border-color: var(--accent); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }

        /* Dashboard Screen */
        #portalCard { display: none; width: 100%; }

        .hero-card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }
        .hero-key {
            font-family: 'JetBrains Mono', monospace;
            font-size: 20px;
            font-weight: 700;
            color: var(--accent);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        .countdown-box {
            font-size: 32px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: #fff;
            margin: 10px 0 16px 0;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }

        .sub-card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 12px;
            padding: 24px;
            text-align: left;
        }
        .sub-card h3 { font-size: 16px; margin-bottom: 12px; color: #fff; }
        .sub-card p { font-size: 13px; color: var(--text-dim); margin-bottom: 16px; line-height: 1.5; }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot-green { background: var(--success); box-shadow: 0 0 8px var(--success); }

        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--surface-card);
            border: 1px solid var(--accent);
            color: #fff;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            display: none;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>VANTA <span>// CLIENT</span></h1>
                <span class="badge badge-active">Player Portal</span>
            </div>
            <div id="topActions" style="display:none;">
                <button class="btn btn-action btn-sm" onclick="logoutCustomer()">Sign Out</button>
            </div>
        </header>

        <!-- Auth View -->
        <div id="authCard">
            <h2>Player License Verification</h2>
            <p>Enter your Vanta License Key to check time remaining, manage your PC binding, and download the loader.</p>
            <input type="text" class="form-control" id="customerKeyInput" placeholder="VANTA-KEY-XXXXXXXXXXXXXXXX" onkeydown="if(event.key==='Enter') loginCustomer()">
            <button class="btn btn-primary" style="width:100%;" onclick="loginCustomer()">Verify License</button>
        </div>

        <!-- Dashboard View -->
        <div id="portalCard">
            <div class="hero-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="hero-key" onclick="copyKey()" id="heroKeyDisplay">
                        VANTA-KEY-XXXX 📋
                    </div>
                    <span class="badge" id="heroRoleBadge">VIP TIER</span>
                </div>
                <div class="countdown-box" id="heroCountdown">Calculating...</div>
                <div style="color:var(--text-dim); font-size:13px; font-family:'JetBrains Mono', monospace;" id="heroDates">
                    Valid until: --
                </div>
            </div>

            <div class="grid-2">
                <!-- HWID Security Card -->
                <div class="sub-card">
                    <h3>🔒 Hardware Lock (HWID)</h3>
                    <p id="hwidStatusText">Checking hardware status...</p>
                    <div style="margin-bottom:16px;">
                        <span class="badge badge-active" id="hwidResetsBadge">2 Resets Remaining</span>
                    </div>
                    <button class="btn btn-action" id="resetHwidBtn" onclick="resetCustomerHWID()">🔓 Reset PC Binding</button>
                </div>

                <!-- Client Loader Download Card -->
                <div class="sub-card">
                    <h3>⚡ Client Launcher</h3>
                    <p>Always run the launcher as Administrator before launching League of Legends.</p>
                    <a href="https://github.com" class="btn btn-primary" id="downloadBtn" target="_blank" style="margin-bottom:12px; width:100%;">
                        ⬇️ Download Vanta Loader (vanta.exe)
                    </a>
                    <div style="font-size:12px; color:var(--text-dim); font-family:'JetBrains Mono', monospace;">
                        Subsystem: Windows 10/11 64-bit | SHA-256 Verified
                    </div>
                </div>
            </div>

            <!-- System Status -->
            <div class="sub-card">
                <h3>🌐 Live Service Infrastructure</h3>
                <div class="status-indicator">
                    <span class="dot dot-green"></span>
                    <span>M1 Vanguard Attestation Cluster: <b>OPERATIONAL (0 Detentions)</b></span>
                </div>
                <div class="status-indicator">
                    <span class="dot dot-green"></span>
                    <span>Game Compatibility: <b>Patch 14.x / 15.x Live Compatible</b></span>
                </div>
                <div class="status-indicator">
                    <span class="dot dot-green"></span>
                    <span>Tutorial Reward Synchronization: <b>AUTOMATED</b></span>
                </div>
            </div>
        </div>
    </div>

    <!-- Bulk Mint Modal -->
    <div style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; justify-content:center; align-items:center;" id="bulkModal">
        <div style="background:var(--surface); border:1px solid var(--surface-border); border-radius:14px; padding:28px; width:100%; max-width:550px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <h3 style="color:#fff;">📦 Bulk Mint Licenses (Store Stock)</h3>
                <span style="cursor:pointer; color:#aaa; font-size:20px;" onclick="closeBulkMintModal()">✕</span>
            </div>
            <div class="form-group">
                <label>Number of Keys to Mint</label>
                <select class="form-control" id="bulkCount">
                    <option value="5">5 Keys (5 Credits)</option>
                    <option value="10" selected>10 Keys (10 Credits)</option>
                    <option value="25">25 Keys (25 Credits)</option>
                    <option value="50">50 Keys (50 Credits)</option>
                    <option value="100">100 Keys (100 Credits)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Plan Duration</label>
                <select class="form-control" id="bulkDays">
                    <option value="1">1 Day Access</option>
                    <option value="7">7 Days Access</option>
                    <option value="30" selected>30 Days Access</option>
                    <option value="365">1 Year / Lifetime</option>
                </select>
            </div>
            <div class="form-group">
                <label>Stock Order Note / Batch ID</label>
                <input type="text" class="form-control" id="bulkNote" placeholder="e.g. Sellix Stock Batch #4">
            </div>
            <button class="btn btn-primary" style="width:100%;" onclick="executeBulkMint()">⚡ Confirm & Mint Stock</button>

            <!-- Results Output Area -->
            <div id="bulkResultsBox" style="display:none; margin-top:16px;">
                <label style="font-size:12px; color:var(--success); font-weight:700;">✅ Stock Generated Successfully! (Line-by-Line format for Sellix/Shoppy):</label>
                <textarea class="form-control" id="bulkOutputArea" rows="6" readonly style="font-size:12px; margin-top:6px;"></textarea>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-action btn-sm" style="flex:1;" onclick="copyBulkStock()">📋 Copy All to Clipboard</button>
                    <button class="btn btn-action btn-sm" style="flex:1;" onclick="downloadBulkTxt()">💾 Download stock.txt</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Discord Webhook Settings Card inside Container -->
    <div class="toast" id="toast"></div>

    <script>
        let currentCustomerKey = localStorage.getItem('vanta_customer_key') || '';
        let licenseData = null;

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        function copyKey() {
            if (!licenseData) return;
            navigator.clipboard.writeText(licenseData.license_key);
            showToast('Copied License Key: ' + licenseData.license_key);
        }

        async function loginCustomer() {
            const key = document.getElementById('customerKeyInput').value.trim();
            if (!key) return alert('Please enter your license key');
            currentCustomerKey = key;
            await loadCustomerData();
        }

        function logoutCustomer() {
            localStorage.removeItem('vanta_customer_key');
            currentCustomerKey = '';
            document.getElementById('authCard').style.display = 'block';
            document.getElementById('portalCard').style.display = 'none';
            document.getElementById('topActions').style.display = 'none';
        }

        async function loadCustomerData() {
            if (!currentCustomerKey) return;
            try {
                const res = await fetch('/api/customer/info?key=' + encodeURIComponent(currentCustomerKey));
                const data = await res.json();
                if (!data.success) {
                    alert('License verification failed: ' + (data.error || 'Invalid key'));
                    logoutCustomer();
                    return;
                }
                localStorage.setItem('vanta_customer_key', currentCustomerKey);
                licenseData = data.license;
                renderPortal();
            } catch (err) {
                alert('Connection error: ' + err);
            }
        }

        function formatDuration(sec) {
            if (sec <= 0) return 'EXPIRED';
            const days = Math.floor(sec / 86400);
            const hours = Math.floor((sec % 86400) / 3600);
            const mins = Math.floor((sec % 3600) / 60);
            return `${days} Days, ${hours} Hours, ${mins} Mins`;
        }

        function renderPortal() {
            document.getElementById('authCard').style.display = 'none';
            document.getElementById('portalCard').style.display = 'block';
            document.getElementById('topActions').style.display = 'block';

            document.getElementById('heroKeyDisplay').innerHTML = `${licenseData.license_key} 📋`;
            const roleBadge = document.getElementById('heroRoleBadge');
            roleBadge.innerText = (licenseData.role || 'USER').toUpperCase() + ' TIER';
            roleBadge.className = 'badge ' + (licenseData.role === 'vip' ? 'badge-vip' : 'badge-active');

            document.getElementById('heroCountdown').innerText = formatDuration(licenseData.seconds_left);
            document.getElementById('heroDates').innerText = `Valid until: ${new Date(licenseData.expires_at * 1000).toLocaleString()}`;

            const hwidText = document.getElementById('hwidStatusText');
            if (licenseData.is_bound) {
                hwidText.innerHTML = `Locked to System: <b style="color:var(--accent); font-family:'JetBrains Mono', monospace;">${licenseData.hwid_masked}</b>`;
            } else {
                hwidText.innerHTML = `<b style="color:var(--success);">Unbound</b> — Ready for first app launch on your PC.`;
            }

            document.getElementById('hwidResetsBadge').innerText = `${licenseData.resets_remaining} Resets Remaining`;
            if (licenseData.resets_remaining <= 0) {
                document.getElementById('resetHwidBtn').disabled = true;
                document.getElementById('resetHwidBtn').innerText = 'Reset Limit Reached';
            }
        }

        async function resetCustomerHWID() {
            if (!confirm('Reset your PC binding? This will use 1 of your remaining reset allowances.')) return;
            const res = await fetch('/api/customer/reset_hwid', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ license_key: currentCustomerKey })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Hardware binding successfully reset!');
                loadCustomerData();
            } else {
                alert('Reset failed: ' + data.error);
            }
        }

        if (currentCustomerKey) {
            loadCustomerData();
        }
    </script>
</body>
</html>"""


# In-Memory Anti-Abuse Rate Limiter
FAILED_LOGIN_ATTEMPTS = {}
IP_BAN_LIST = {}

def record_failed_attempt(ip):
    now = time.time()
    attempts = [t for t in FAILED_LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
    attempts.append(now)
    FAILED_LOGIN_ATTEMPTS[ip] = attempts
    if len(attempts) >= 5:
        IP_BAN_LIST[ip] = now + 1800 # 30-minute jail
        print(f"[SECURITY-IDS] Jailed abusive IP {ip} for 30 minutes (5+ failed attempts)")

def is_ip_jailed(ip):
    now = time.time()
    jail_until = IP_BAN_LIST.get(ip, 0)
    if now < jail_until:
        return True, int(jail_until - now)
    elif ip in IP_BAN_LIST:
        del IP_BAN_LIST[ip]
    return False, 0

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

        if path in ["/", "/admin", "/dashboard"]:
            self._send_html(HTML_DASHBOARD)
            return

        elif path == "/reseller":
            self._send_html(HTML_RESELLER_PORTAL)
            return

        elif path in ["/customer", "/portal"]:
            self._send_html(HTML_CUSTOMER_PORTAL)
            return

        elif path == "/api/customer/preflight":
            self._send_json(200, {
                "success": True,
                "server_status": "ONLINE",
                "cluster_node": "51.159.121.126 (macOS M1 Silicon)",
                "game_compatibility": "Patch 14.x / 15.x Live",
                "vanguard_attenuation": "BYPASS_OPERATIONAL",
                "timestamp": int(time.time())
            })
            return

        elif path == "/api/customer/config/load":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            if not key:
                self._send_json(400, {"success": False, "error": "key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT config_data, updated_at FROM customer_configs WHERE license_key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if not row:
                self._send_json(404, {"success": False, "error": "No cloud configuration found for this license"})
                return
            self._send_json(200, {"success": True, "config": row[0], "updated_at": row[1]})
            return

        elif path == "/api/reseller/sub/list":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            if not key:
                self._send_json(400, {"success": False, "error": "key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM sub_resellers WHERE parent_key = ? ORDER BY id DESC", (key,))
            subs = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "sub_resellers": subs})
            return

        elif path == "/api/admin/financials":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM licenses")
            total_licenses = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM licenses WHERE status = 'active'")
            active_licenses = c.fetchone()[0]
            c.execute("SELECT role, COUNT(*) as cnt FROM licenses GROUP BY role")
            tier_counts = {r["role"]: r["cnt"] for r in c.fetchall()}
            c.execute("SELECT name, credits, created_at FROM resellers ORDER BY credits DESC LIMIT 10")
            leaderboard = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {
                "success": True,
                "total_licenses_issued": total_licenses,
                "active_subscriptions": active_licenses,
                "tier_breakdown": tier_counts,
                "top_resellers": leaderboard,
                "currency": "USD",
                "estimated_gmv": total_licenses * 15 # baseline estimated value
            })
            return

        elif path == "/api/customer/info":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            if not key:
                self._send_json(400, {"success": False, "error": "License key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, license_key, role, reseller_id, hwid, hwid_reset_count, max_resets, status, created_at, expires_at, note, last_seen FROM licenses WHERE license_key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if not row:
                self._send_json(404, {"success": False, "error": "Invalid License Key"})
                return
            lic = dict(row)
            now = int(time.time())
            if lic["status"] == "active" and lic["expires_at"] < now:
                lic["status"] = "expired"
            lic["is_bound"] = bool(lic.get("hwid"))
            lic["hwid_masked"] = (lic["hwid"][:8] + "..." + lic["hwid"][-4:]) if lic.get("hwid") else "Unbound"
            lic["resets_remaining"] = max(0, lic.get("max_resets", 3) - lic.get("hwid_reset_count", 0))
            lic["seconds_left"] = max(0, lic["expires_at"] - now)
            self._send_json(200, {"success": True, "license": lic})
            return
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

        elif path == "/api/admin/resellers":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM resellers ORDER BY id DESC")
            resellers = [dict(r) for r in c.fetchall()]
            for r in resellers:
                c.execute("SELECT COUNT(*) FROM licenses WHERE reseller_id = ?", (r["reseller_key"],))
                r["keys_count"] = c.fetchone()[0]
            conn.close()
            self._send_json(200, {"success": True, "resellers": resellers})

        elif path == "/api/reseller/info":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            if not key:
                self._send_json(400, {"success": False, "error": "key parameter required"})
                return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, reseller_key, name, credits, created_at, status FROM resellers WHERE reseller_key = ?", (key,))
            res = c.fetchone()
            if not res:
                conn.close()
                self._send_json(404, {"success": False, "error": "Reseller not found"})
                return
            res_data = dict(res)
            c.execute("SELECT id, license_key, role, hwid, status, created_at, expires_at, note FROM licenses WHERE reseller_id = ? ORDER BY id DESC", (key,))
            res_data["keys"] = [dict(k) for k in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "reseller": res_data})

        elif path == "/api/ping":
            self._send_json(200, {"pong": True, "time": int(time.time() * 1000)})

        elif path == "/api/announcements":
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT value FROM system_config WHERE key = 'maintenance_mode'")
            row_mode = c.fetchone()
            is_maint = (row_mode and row_mode[0] == "true")
            c.execute("SELECT value FROM system_config WHERE key = 'maintenance_msg'")
            row_msg = c.fetchone()
            maint_msg = row_msg[0] if row_msg else "System Maintenance Active"
            conn.close()

            if is_maint:
                self._send_json(200, {
                    "active": True,
                    "maintenance": True,
                    "message": f"🚨 EMERGENCY MAINTENANCE: {maint_msg}",
                    "severity": "critical",
                    "timestamp": int(time.time())
                })
            else:
                self._send_json(200, {
                    "active": True,
                    "maintenance": False,
                    "message": "VANTA Apex v5.2 // Zero-Detection Engine Online",
                    "severity": "info",
                    "timestamp": int(time.time())
                })

        elif path == "/api/v1/reseller/balance":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip()
            if not token:
                token = params.get("token", [None])[0] or ""
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM resellers WHERE reseller_key = ?", (token,))
            res = c.fetchone()
            if not res:
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid Reseller Token"})
                return
            res_data = dict(res)
            c.execute("SELECT id, license_key, role, hwid, status, created_at, expires_at, note FROM licenses WHERE reseller_id = ? ORDER BY id DESC", (token,))
            res_data["keys"] = [dict(k) for k in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "reseller": res_data})

        elif path == "/api/ticket/list":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            reseller_key = params.get("reseller_key", [None])[0]
            ticket_id = params.get("ticket_id", [None])[0]

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            if ticket_id:
                c.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
                t = c.fetchone()
                if not t:
                    conn.close()
                    self._send_json(404, {"success": False, "error": "Ticket not found"})
                    return
                ticket_data = dict(t)
                c.execute("SELECT * FROM ticket_messages WHERE ticket_id = ? ORDER BY id ASC", (ticket_id,))
                ticket_data["messages"] = [dict(m) for m in c.fetchall()]
                conn.close()
                self._send_json(200, {"success": True, "ticket": ticket_data})
                return

            if key:
                c.execute("SELECT * FROM tickets WHERE license_key = ? ORDER BY id DESC", (key,))
            elif reseller_key:
                c.execute("SELECT * FROM tickets WHERE reseller_id = ? ORDER BY id DESC", (reseller_key,))
            else:
                c.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT 50")

            tickets = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "tickets": tickets})
            return

        elif path == "/api/reseller/branding":
            params = parse_qs(parsed.query)
            reseller_key = params.get("reseller_key", [None])[0]
            brand_name = params.get("brand", [None])[0]

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            if reseller_key:
                c.execute("SELECT * FROM reseller_branding WHERE reseller_key = ?", (reseller_key,))
            elif brand_name:
                c.execute("SELECT * FROM reseller_branding WHERE LOWER(brand_name) = LOWER(?)", (brand_name,))
            else:
                conn.close()
                self._send_json(400, {"success": False, "error": "reseller_key or brand required"})
                return

            row = c.fetchone()
            conn.close()
            if not row:
                self._send_json(200, {
                    "success": True,
                    "branding": {
                        "brand_name": "VANTA APEX",
                        "logo_url": "",
                        "discord_url": "https://discord.gg/vanta",
                        "primary_color": "#00f2fe"
                    }
                })
                return
            self._send_json(200, {"success": True, "branding": dict(row)})
            return

        elif path == "/api/reseller/crypto/invoices":
            params = parse_qs(parsed.query)
            reseller_key = params.get("reseller_key", [None])[0]
            if not reseller_key:
                self._send_json(400, {"success": False, "error": "reseller_key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM crypto_invoices WHERE reseller_key = ? ORDER BY id DESC LIMIT 20", (reseller_key,))
            invoices = [dict(r) for r in c.fetchall()]
            conn.close()
            self._send_json(200, {"success": True, "invoices": invoices})
            return

        elif path == "/api/reseller/pricing_tiers":
            self._send_json(200, {
                "success": True,
                "tiers": [
                    {"min_credits": 1, "max_credits": 24, "price_per_credit_usd": 1.80, "discount_pct": 0},
                    {"min_credits": 25, "max_credits": 99, "price_per_credit_usd": 1.50, "discount_pct": 16.6},
                    {"min_credits": 100, "max_credits": 249, "price_per_credit_usd": 1.25, "discount_pct": 30.5},
                    {"min_credits": 250, "max_credits": 9999, "price_per_credit_usd": 1.00, "discount_pct": 44.4}
                ]
            })
            return

        elif path == "/api/customer/check_expiry_alert":
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            if not key:
                self._send_json(400, {"success": False, "error": "key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT expires_at, status FROM licenses WHERE license_key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if not row:
                self._send_json(404, {"success": False, "error": "Key not found"})
                return
            now = int(time.time())
            seconds_left = max(0, row["expires_at"] - now)
            days_left = round(seconds_left / 86400, 1)
            should_alert = seconds_left < (3 * 86400) and row["status"] == "active"
            self._send_json(200, {
                "success": True,
                "seconds_left": seconds_left,
                "days_left": days_left,
                "should_alert": should_alert,
                "alert_message": f"⚠️ License expires in {days_left} days. Renew promptly to preserve settings and HWID unbind quota." if should_alert else "License active"
            })
            return

        elif path == "/api/system/health":
            self._send_json(200, {"ok": True, "timestamp": int(time.time())})

        else:
            self._send_json(404, {"error": "Not Found"})

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_POST(self):
        try:
            self._handle_POST()
        except Exception as e:
            print("[HUB POST ERROR]", e)
            self._send_json(500, {"success": False, "error": str(e)})

    def _handle_POST(self):
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
        elif path == "/api/customer/config/save":
            key = payload.get("license_key", "").strip()
            config_str = payload.get("config_data", "").strip()
            if not key or not config_str:
                self._send_json(400, {"success": False, "error": "license_key and config_data required"})
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM licenses WHERE license_key = ? AND status = 'active'", (key,))
            if not c.fetchone():
                conn.close()
                self._send_json(403, {"success": False, "error": "Active license required to sync cloud config"})
                return
            now = int(time.time())
            c.execute("INSERT OR REPLACE INTO customer_configs (license_key, config_data, updated_at) VALUES (?, ?, ?)", (key, config_str, now))
            conn.commit()
            conn.close()
            log_event(key, "cloud_config_saved", client_ip, details=f"Config synced ({len(config_str)} bytes)")
            self._send_json(200, {"success": True, "updated_at": now})
            return

        elif path == "/api/reseller/sub/create":
            parent_key = payload.get("parent_key", "").strip()
            sub_name = payload.get("name", "").strip()
            commission = float(payload.get("commission_pct", 15.0))
            credits = int(payload.get("credits", 0))

            if not parent_key or not sub_name:
                self._send_json(400, {"success": False, "error": "parent_key and name required"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, credits, status FROM resellers WHERE reseller_key = ?", (parent_key,))
            parent = c.fetchone()
            if not parent or parent["status"] != "active":
                conn.close()
                self._send_json(403, {"success": False, "error": "Invalid or inactive parent reseller"})
                return

            if credits > 0:
                if parent["credits"] < credits:
                    conn.close()
                    self._send_json(402, {"success": False, "error": f"Insufficient credits to allocate. You have {parent['credits']}"})
                    return
                c.execute("UPDATE resellers SET credits = credits - ? WHERE id = ?", (credits, parent["id"]))

            sub_key = "VANTA-SUB-" + uuid.uuid4().hex[:12].upper()
            now = int(time.time())
            c.execute("""
            INSERT INTO sub_resellers (parent_key, sub_key, name, commission_pct, credits, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (parent_key, sub_key, sub_name, commission, credits, now))

            # Also register as a functional reseller
            c.execute("""
            INSERT INTO resellers (reseller_key, name, credits, created_at, status)
            VALUES (?, ?, ?, ?, 'active')
            """, (sub_key, f"[{sub_name}] (Sub of {parent_key[:10]})", credits, now))

            conn.commit()
            conn.close()
            log_event(parent_key, "sub_reseller_created", client_ip, details=f"Created sub-reseller {sub_name} with {credits} credits")
            self._send_json(200, {
                "success": True,
                "sub_key": sub_key,
                "name": sub_name,
                "commission_pct": commission,
                "credits": credits
            })
            return

        elif path == "/api/admin/backup":
            backup_dir = "/Users/m1/backups"
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = f"{backup_dir}/vanta_backup_{int(time.time())}.db"
            try:
                import shutil
                shutil.copy2(DB_FILE, backup_file)
                self._send_json(200, {"success": True, "backup_path": backup_file, "size_bytes": os.path.getsize(backup_file)})
            except Exception as e:
                self._send_json(500, {"success": False, "error": f"Backup failed: {e}"})
            return

        elif path == "/api/reseller/bulk_generate":
            reseller_key = payload.get("reseller_key", "").strip()
            count = int(payload.get("count", 1))
            days = int(payload.get("days", 30))
            role = payload.get("role", "user")
            note_prefix = payload.get("note", "Bulk Store Stock")

            if count < 1 or count > 100:
                self._send_json(400, {"success": False, "error": "Count must be between 1 and 100"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, name, credits, status, discord_webhook FROM resellers WHERE reseller_key = ?", (reseller_key,))
            reseller = c.fetchone()
            if not reseller:
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid Reseller Key"})
                return
            if reseller["status"] != "active":
                conn.close()
                self._send_json(403, {"success": False, "error": "Reseller partner account suspended"})
                return
            if reseller["credits"] < count:
                conn.close()
                self._send_json(402, {"success": False, "error": f"Insufficient credits. Required: {count}, Available: {reseller['credits']}"})
                return

            # Deduct credits
            c.execute("UPDATE resellers SET credits = credits - ? WHERE id = ?", (count, reseller["id"]))
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else "VANTA-KEY-"

            minted_keys = []
            for i in range(count):
                key = prefix + uuid.uuid4().hex[:16].upper()
                c.execute("""
                INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
                VALUES (?, ?, ?, NULL, 3, 'active', ?, ?, ?)
                """, (key, role, reseller_key, now, expires, f"[{reseller['name']}] {note_prefix} #{i+1}"))
                minted_keys.append(key)

            conn.commit()
            c.execute("SELECT credits FROM resellers WHERE id = ?", (reseller["id"],))
            rem = c.fetchone()[0]
            conn.close()

            log_event(reseller_key, "reseller_bulk_mint", client_ip, details=f"Bulk minted {count} keys. Balance: {rem}")

            # Send Discord notification if configured
            if reseller["discord_webhook"]:
                fields = [
                    {"name": "Keys Issued", "value": f"`{count}x`", "inline": True},
                    {"name": "Duration", "value": f"`{days} Days`", "inline": True},
                    {"name": "Tier", "value": f"`{role.upper()}`", "inline": True},
                    {"name": "Remaining Credits", "value": f"`{rem} Credits`", "inline": True}
                ]
                send_discord_webhook(
                    reseller["discord_webhook"],
                    "⚡ Bulk Licenses Minted",
                    f"Partner **{reseller['name']}** successfully minted **{count}** licenses for digital store stock.",
                    color=0x00f2fe,
                    fields=fields
                )

            self._send_json(200, {
                "success": True,
                "count": count,
                "keys": minted_keys,
                "remaining_credits": rem
            })
            return

        elif path == "/api/reseller/settings":
            reseller_key = payload.get("reseller_key", "").strip()
            webhook = payload.get("discord_webhook", "").strip()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE resellers SET discord_webhook = ? WHERE reseller_key = ?", (webhook, reseller_key))
            conn.commit()
            conn.close()

            if webhook:
                send_discord_webhook(webhook, "✅ Vanta Partner Webhook Connected", "Your Discord channel is now connected to live license sales and activation alerts.", color=0x00ffaa)

            self._send_json(200, {"success": True, "message": "Settings updated"})
            return

        elif path == "/api/admin/maintenance":
            active = bool(payload.get("active", False))
            msg = payload.get("message", "Routine Vanguard telemetry synchronization in progress.")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('maintenance_mode', ?)", ("true" if active else "false",))
            c.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('maintenance_msg', ?)", (msg,))
            conn.commit()
            conn.close()
            log_event("root", "maintenance_toggled", client_ip, details=f"Maintenance set to {active}: {msg}")
            self._send_json(200, {"success": True, "active": active, "message": msg})
            return

        elif path == "/api/reseller/reset_hwid":
            reseller_key = payload.get("reseller_key")
            lic_key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM licenses WHERE license_key = ? AND reseller_id = ?", (lic_key, reseller_key))
            if not c.fetchone():
                conn.close()
                self._send_json(403, {"success": False, "error": "License does not belong to this reseller"})
                return
            c.execute("UPDATE licenses SET hwid = NULL, hwid_reset_count = hwid_reset_count + 1 WHERE license_key = ?", (lic_key,))
            conn.commit()
            conn.close()
            log_event(lic_key, "reseller_hwid_reset", client_ip, details=f"HWID reset by reseller {reseller_key}")
            self._send_json(200, {"success": True})
            return

        elif path == "/api/customer/reset_hwid":
            lic_key = payload.get("license_key")
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT hwid_reset_count, max_resets, status FROM licenses WHERE license_key = ?", (lic_key,))
            row = c.fetchone()
            if not row:
                conn.close()
                self._send_json(404, {"success": False, "error": "License key not found"})
                return
            if row["status"] != "active":
                conn.close()
                self._send_json(403, {"success": False, "error": "License is inactive or expired"})
                return
            resets_used = row["hwid_reset_count"] or 0
            max_resets = row["max_resets"] or 3
            if resets_used >= max_resets:
                conn.close()
                self._send_json(400, {"success": False, "error": "HWID reset quota exhausted. Please contact support."})
                return
            c.execute("UPDATE licenses SET hwid = NULL, hwid_reset_count = hwid_reset_count + 1 WHERE license_key = ?", (lic_key,))
            conn.commit()
            rem = max_resets - (resets_used + 1)
            conn.close()
            log_event(lic_key, "customer_self_hwid_reset", client_ip, details=f"Self-service reset, remaining: {rem}")
            self._send_json(200, {"success": True, "remaining_resets": rem})
            return

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

        # Reseller Partner Creation (Admin)
        elif path == "/api/admin/reseller/create":
            name = payload.get("name", "").strip()
            credits = int(payload.get("credits", 0))
            if not name:
                self._send_json(400, {"success": False, "error": "Partner name is required"})
                return
            reseller_key = "VANTA-RSL-" + uuid.uuid4().hex[:12].upper()
            now = int(time.time())
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO resellers (reseller_key, name, credits, created_at, status) VALUES (?, ?, ?, ?, 'active')",
                      (reseller_key, name, credits, now))
            conn.commit()
            conn.close()
            log_event(reseller_key, "reseller_created", client_ip, details=f"Reseller partner '{name}' initialized with {credits} credits")
            self._send_json(200, {"success": True, "reseller_key": reseller_key, "name": name, "credits": credits})

        # Reseller Credits Top Up (Admin)
        elif path == "/api/admin/reseller/add_credits":
            key = payload.get("reseller_key", "").strip()
            amount = int(payload.get("credits", 0))
            if not key or amount <= 0:
                self._send_json(400, {"success": False, "error": "Valid reseller_key and positive credit amount required"})
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE resellers SET credits = credits + ? WHERE reseller_key = ?", (amount, key))
            conn.commit()
            c.execute("SELECT credits, name FROM resellers WHERE reseller_key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if row:
                log_event(key, "reseller_credits_added", client_ip, details=f"Added {amount} credits to {row[1]} (New balance: {row[0]})")
                self._send_json(200, {"success": True, "credits": row[0]})
            else:
                self._send_json(404, {"success": False, "error": "Reseller not found"})

        # Reseller Status Toggle (Admin)
        # Reseller Partner Deletion (Admin)
        elif path == "/api/admin/reseller/delete":
            key = payload.get("reseller_key", "").strip()
            if not key:
                self._send_json(400, {"success": False, "error": "reseller_key required"})
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM resellers WHERE reseller_key = ?", (key,))
            conn.commit()
            conn.close()
            log_event(key, "reseller_deleted", client_ip, details="Reseller partner deleted by admin")
            self._send_json(200, {"success": True, "message": "Reseller deleted"})
            return

        elif path == "/api/admin/reseller/toggle":
            key = payload.get("reseller_key", "").strip()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT status FROM resellers WHERE reseller_key = ?", (key,))
            row = c.fetchone()
            if row:
                new_status = "suspended" if row[0] == "active" else "active"
                c.execute("UPDATE resellers SET status = ? WHERE reseller_key = ?", (new_status, key))
                conn.commit()
                conn.close()
                log_event(key, "reseller_status_changed", client_ip, details=f"Status set to {new_status}")
                self._send_json(200, {"success": True, "status": new_status})
            else:
                conn.close()
                self._send_json(404, {"success": False, "error": "Reseller not found"})

        # Reseller Key Generation (Customer License issuance)
        elif path == "/api/reseller/generate":
            reseller_key = payload.get("reseller_key", "").strip()
            days = int(payload.get("days", 30))
            role = payload.get("role", "user")
            note = payload.get("note", "Reseller Client Key")
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM resellers WHERE reseller_key = ?", (reseller_key,))
            reseller = c.fetchone()
            if not reseller:
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid Reseller Access Key"})
                return
            if reseller["status"] != "active":
                conn.close()
                self._send_json(403, {"success": False, "error": "Reseller partner account is suspended"})
                return
            if reseller["credits"] < 1:
                conn.close()
                self._send_json(402, {"success": False, "error": "Insufficient credits. Contact Admin to top up."})
                return

            c.execute("UPDATE resellers SET credits = credits - 1 WHERE id = ?", (reseller["id"],))
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else "VANTA-KEY-"
            new_key = prefix + uuid.uuid4().hex[:16].upper()
            c.execute("""
            INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
            VALUES (?, ?, ?, NULL, 3, 'active', ?, ?, ?)
            """, (new_key, role, reseller_key, now, expires, f"[{reseller['name']}] {note}"))
            conn.commit()
            c.execute("SELECT credits FROM resellers WHERE id = ?", (reseller["id"],))
            rem = c.fetchone()[0]
            conn.close()

            log_event(new_key, "reseller_key_issued", client_ip, details=f"Issued by {reseller['name']}, balance remaining: {rem}")
            self._send_json(200, {
                "success": True,
                "license_key": new_key,
                "expires_at": expires,
                "remaining_credits": rem
            })

        # Reseller External REST API: Bearer token authenticated automated minting
        elif path == "/api/v1/reseller/mint_key":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip() or payload.get("reseller_key", "").strip()
            days = int(payload.get("days", 30))
            role = payload.get("role", "user")
            note = payload.get("note", "REST API Minted Key")
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM resellers WHERE reseller_key = ?", (token,))
            reseller = c.fetchone()
            if not reseller:
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid or missing Reseller Bearer Token"})
                return
            if reseller["status"] != "active":
                conn.close()
                self._send_json(403, {"success": False, "error": "Reseller account is suspended"})
                return
            if reseller["credits"] < 1:
                conn.close()
                self._send_json(402, {"success": False, "error": "Insufficient credits"})
                return

            c.execute("UPDATE resellers SET credits = credits - 1 WHERE id = ?", (reseller["id"],))
            now = int(time.time())
            expires = now + (days * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else "VANTA-KEY-"
            new_key = prefix + uuid.uuid4().hex[:16].upper()
            c.execute("""
            INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
            VALUES (?, ?, ?, NULL, 3, 'active', ?, ?, ?)
            """, (new_key, role, token, now, expires, f"[{reseller['name']}] {note}"))
            conn.commit()
            c.execute("SELECT credits FROM resellers WHERE id = ?", (reseller["id"],))
            rem = c.fetchone()[0]
            conn.close()

            log_event(new_key, "api_v1_key_minted", client_ip, details=f"External API mint by {reseller['name']}, balance: {rem}")
            self._send_json(200, {
                "success": True,
                "license_key": new_key,
                "expires_at": expires,
                "remaining_credits": rem
            })

        # Section 31: Crypto Payment Gate (LTC / USDT / BTC)
        elif path == "/api/reseller/crypto/create_invoice":
            reseller_key = payload.get("reseller_key", "").strip()
            crypto_coin = payload.get("crypto_coin", "LTC").upper()
            credits_req = int(payload.get("credits", 25))

            if credits_req < 1:
                self._send_json(400, {"success": False, "error": "Minimum 1 credit required"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, name, credits FROM resellers WHERE reseller_key = ?", (reseller_key,))
            reseller = c.fetchone()
            if not reseller:
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid reseller key"})
                return

            # Tiered volume pricing
            if credits_req >= 250:
                unit_price = 1.00
            elif credits_req >= 100:
                unit_price = 1.25
            elif credits_req >= 25:
                unit_price = 1.50
            else:
                unit_price = 1.80

            amount_usd = round(credits_req * unit_price, 2)
            # Simulated crypto conversion rates
            crypto_rates = {"LTC": 85.0, "USDT": 1.0, "BTC": 65000.0}
            rate = crypto_rates.get(crypto_coin, 85.0)
            crypto_amount = round(amount_usd / rate, 6)

            invoice_id = "INV-" + uuid.uuid4().hex[:12].upper()
            now = int(time.time())
            # Deterministic deposit address mock
            mock_addr = f"ltc1q{uuid.uuid4().hex[:28]}" if crypto_coin == "LTC" else f"0x{uuid.uuid4().hex[:40]}"

            c.execute("""
            INSERT INTO crypto_invoices (invoice_id, reseller_key, crypto_coin, amount_usd, crypto_amount, deposit_address, credits_to_add, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (invoice_id, reseller_key, crypto_coin, amount_usd, crypto_amount, mock_addr, credits_req, now))
            conn.commit()
            conn.close()

            log_event(reseller_key, "crypto_invoice_created", client_ip, details=f"Invoice {invoice_id} for {credits_req} credits (${amount_usd} via {crypto_coin})")
            self._send_json(200, {
                "success": True,
                "invoice_id": invoice_id,
                "reseller_name": reseller["name"],
                "credits": credits_req,
                "amount_usd": amount_usd,
                "crypto_coin": crypto_coin,
                "crypto_amount": crypto_amount,
                "deposit_address": mock_addr,
                "expires_in_minutes": 60
            })
            return

        elif path == "/api/reseller/crypto/webhook":
            invoice_id = payload.get("invoice_id", "").strip()
            tx_hash = payload.get("tx_hash", "0x" + uuid.uuid4().hex)

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM crypto_invoices WHERE invoice_id = ?", (invoice_id,))
            inv = c.fetchone()
            if not inv:
                conn.close()
                self._send_json(404, {"success": False, "error": "Invoice not found"})
                return
            if inv["status"] == "confirmed":
                conn.close()
                self._send_json(200, {"success": True, "message": "Already confirmed"})
                return

            now = int(time.time())
            c.execute("UPDATE crypto_invoices SET status = 'confirmed', confirmed_at = ? WHERE invoice_id = ?", (now, invoice_id))
            c.execute("UPDATE resellers SET credits = credits + ? WHERE reseller_key = ?", (inv["credits_to_add"], inv["reseller_key"]))
            conn.commit()

            c.execute("SELECT name, credits, discord_webhook FROM resellers WHERE reseller_key = ?", (inv["reseller_key"],))
            res = c.fetchone()
            conn.close()

            log_event(inv["reseller_key"], "crypto_payment_confirmed", client_ip, details=f"Invoice {invoice_id} confirmed. Added {inv['credits_to_add']} credits. Tx: {tx_hash[:16]}...")

            if res and res["discord_webhook"]:
                fields = [
                    {"name": "Invoice ID", "value": f"`{invoice_id}`", "inline": True},
                    {"name": "Credits Added", "value": f"`+{inv['credits_to_add']} Credits`", "inline": True},
                    {"name": "Amount Paid", "value": f"`{inv['crypto_amount']} {inv['crypto_coin']}`", "inline": True},
                    {"name": "New Balance", "value": f"`{res['credits']} Credits`", "inline": True}
                ]
                send_discord_webhook(
                    res["discord_webhook"],
                    "💎 Crypto Payment Confirmed",
                    f"Partner **{res['name']}** account credited automatically via blockchain settlement.",
                    color=0x00ffaa,
                    fields=fields
                )

            self._send_json(200, {
                "success": True,
                "invoice_id": invoice_id,
                "credits_added": inv["credits_to_add"],
                "new_balance": res["credits"] if res else 0,
                "tx_hash": tx_hash
            })
            return

        # Section 40: P2P Credit Transfer
        elif path == "/api/reseller/transfer_credits":
            sender_key = payload.get("sender_key", "").strip()
            recipient_key = payload.get("recipient_key", "").strip()
            amount = int(payload.get("credits", 0))

            if amount <= 0:
                self._send_json(400, {"success": False, "error": "Transfer amount must be positive"})
                return
            if sender_key == recipient_key:
                self._send_json(400, {"success": False, "error": "Cannot transfer credits to self"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, name, credits, status FROM resellers WHERE reseller_key = ?", (sender_key,))
            sender = c.fetchone()
            c.execute("SELECT id, name, credits, status FROM resellers WHERE reseller_key = ?", (recipient_key,))
            recipient = c.fetchone()

            if not sender or sender["status"] != "active":
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid or inactive sender account"})
                return
            if not recipient or recipient["status"] != "active":
                conn.close()
                self._send_json(404, {"success": False, "error": "Recipient reseller not found or inactive"})
                return
            if sender["credits"] < amount:
                conn.close()
                self._send_json(402, {"success": False, "error": f"Insufficient credits. You have {sender['credits']}, requested {amount}"})
                return

            c.execute("UPDATE resellers SET credits = credits - ? WHERE id = ?", (amount, sender["id"]))
            c.execute("UPDATE resellers SET credits = credits + ? WHERE id = ?", (amount, recipient["id"]))
            conn.commit()

            c.execute("SELECT credits FROM resellers WHERE id = ?", (sender["id"],))
            sender_rem = c.fetchone()[0]
            c.execute("SELECT credits FROM resellers WHERE id = ?", (recipient["id"],))
            recip_new = c.fetchone()[0]
            conn.close()

            log_event(sender_key, "p2P_credit_transfer", client_ip, details=f"Transferred {amount} credits to {recipient['name']} ({recipient_key})")
            self._send_json(200, {
                "success": True,
                "amount": amount,
                "sender_remaining": sender_rem,
                "recipient_name": recipient["name"]
            })
            return

        # Section 38: White-Label Branding
        elif path == "/api/reseller/branding":
            reseller_key = payload.get("reseller_key", "").strip()
            brand_name = payload.get("brand_name", "").strip()
            logo_url = payload.get("logo_url", "").strip()
            discord_url = payload.get("discord_url", "").strip()
            color = payload.get("primary_color", "#00f2fe").strip()

            if not reseller_key or not brand_name:
                self._send_json(400, {"success": False, "error": "reseller_key and brand_name required"})
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM resellers WHERE reseller_key = ?", (reseller_key,))
            if not c.fetchone():
                conn.close()
                self._send_json(401, {"success": False, "error": "Invalid reseller key"})
                return
            now = int(time.time())
            c.execute("""
            INSERT OR REPLACE INTO reseller_branding (reseller_key, brand_name, logo_url, discord_url, primary_color, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (reseller_key, brand_name, logo_url, discord_url, color, now))
            conn.commit()
            conn.close()
            log_event(reseller_key, "branding_updated", client_ip, details=f"Updated brand: {brand_name}")
            self._send_json(200, {"success": True, "brand_name": brand_name})
            return

        # Section 50: Live Ticket Support System
        elif path == "/api/ticket/create":
            key = payload.get("license_key", "").strip()
            subject = payload.get("subject", "").strip()
            message = payload.get("message", "").strip()

            if not key or not subject or not message:
                self._send_json(400, {"success": False, "error": "license_key, subject, and message required"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT reseller_id, status FROM licenses WHERE license_key = ?", (key,))
            lic = c.fetchone()
            if not lic:
                conn.close()
                self._send_json(404, {"success": False, "error": "License key not found"})
                return

            ticket_id = "TCK-" + uuid.uuid4().hex[:10].upper()
            now = int(time.time())
            c.execute("""
            INSERT INTO tickets (ticket_id, license_key, reseller_id, subject, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """, (ticket_id, key, lic["reseller_id"], subject, now, now))

            c.execute("""
            INSERT INTO ticket_messages (ticket_id, sender, message, created_at)
            VALUES (?, 'customer', ?, ?)
            """, (ticket_id, message, now))
            conn.commit()

            # Notify reseller via Discord if configured
            c.execute("SELECT name, discord_webhook FROM resellers WHERE reseller_key = ?", (lic["reseller_id"],))
            res = c.fetchone()
            conn.close()

            if res and res["discord_webhook"]:
                send_discord_webhook(
                    res["discord_webhook"],
                    "📩 New Support Ticket Opened",
                    f"A customer holding key `{key[:12]}...` submitted ticket **#{ticket_id}**: *{subject}*",
                    color=0xffaa00,
                    fields=[{"name": "Customer Message", "value": message[:200]}]
                )

            log_event(key, "ticket_created", client_ip, details=f"Ticket {ticket_id}: {subject}")
            self._send_json(200, {"success": True, "ticket_id": ticket_id})
            return

        elif path == "/api/ticket/reply":
            ticket_id = payload.get("ticket_id", "").strip()
            sender = payload.get("sender", "customer").strip()
            message = payload.get("message", "").strip()

            if not ticket_id or not message:
                self._send_json(400, {"success": False, "error": "ticket_id and message required"})
                return

            now = int(time.time())
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM tickets WHERE ticket_id = ?", (ticket_id,))
            if not c.fetchone():
                conn.close()
                self._send_json(404, {"success": False, "error": "Ticket not found"})
                return

            c.execute("INSERT INTO ticket_messages (ticket_id, sender, message, created_at) VALUES (?, ?, ?, ?)",
                      (ticket_id, sender, message, now))
            c.execute("UPDATE tickets SET updated_at = ? WHERE ticket_id = ?", (now, ticket_id))
            conn.commit()
            conn.close()

            self._send_json(200, {"success": True, "ticket_id": ticket_id, "timestamp": now})
            return

        # Section 49: Referral / Affiliate Reward Engine
        elif path == "/api/customer/referral/claim":
            referrer_key = payload.get("referrer_key", "").strip()
            referee_key = payload.get("referee_key", "").strip()

            if not referrer_key or not referee_key or referrer_key == referee_key:
                self._send_json(400, {"success": False, "error": "Valid distinct referrer and referee keys required"})
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, status, expires_at FROM licenses WHERE license_key = ?", (referrer_key,))
            ref = c.fetchone()
            if not ref or ref[1] != "active":
                conn.close()
                self._send_json(404, {"success": False, "error": "Referrer license key must be active"})
                return

            c.execute("SELECT id FROM licenses WHERE license_key = ?", (referee_key,))
            if not c.fetchone():
                conn.close()
                self._send_json(404, {"success": False, "error": "Referred license key not recognized"})
                return

            c.execute("SELECT id FROM referrals WHERE referee_key = ?", (referee_key,))
            if c.fetchone():
                conn.close()
                self._send_json(400, {"success": False, "error": "Referred key has already claimed referral bonus"})
                return

            now = int(time.time())
            bonus_seconds = 3 * 86400 # 3 days bonus
            c.execute("INSERT INTO referrals (referrer_key, referee_key, bonus_days, created_at) VALUES (?, ?, 3, ?)",
                      (referrer_key, referee_key, now))
            c.execute("UPDATE licenses SET expires_at = expires_at + ? WHERE license_key = ?", (bonus_seconds, referrer_key))
            conn.commit()
            c.execute("SELECT expires_at FROM licenses WHERE license_key = ?", (referrer_key,))
            new_exp = c.fetchone()[0]
            conn.close()

            log_event(referrer_key, "referral_reward_claimed", client_ip, details=f"Referred {referee_key}. Awarded +3 days.")
            self._send_json(200, {"success": True, "bonus_days": 3, "new_expires_at": new_exp})
            return

        # Section 36: Sellix / Shoppy Auto-Restock Webhook
        elif path == "/api/reseller/sellix_webhook":
            token = payload.get("reseller_key", "").strip()
            qty = min(int(payload.get("quantity", 5)), 50)
            role = payload.get("role", "user")

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, name, credits, status FROM resellers WHERE reseller_key = ?", (token,))
            reseller = c.fetchone()
            if not reseller or reseller["status"] != "active":
                conn.close()
                self._send_json(401, {"success": False, "error": "Unauthorized reseller token"})
                return
            if reseller["credits"] < qty:
                conn.close()
                self._send_json(402, {"success": False, "error": "Insufficient credits for store restock"})
                return

            c.execute("UPDATE resellers SET credits = credits - ? WHERE id = ?", (qty, reseller["id"]))
            now = int(time.time())
            expires = now + (30 * 86400)
            prefix = "VANTA-VIP-" if role == "vip" else "VANTA-KEY-"
            minted = []
            for _ in range(qty):
                k = prefix + uuid.uuid4().hex[:16].upper()
                c.execute("""
                INSERT INTO licenses (license_key, role, reseller_id, hwid, max_resets, status, created_at, expires_at, note)
                VALUES (?, ?, ?, NULL, 3, 'active', ?, ?, 'Sellix Automated Delivery')
                """, (k, role, token, now, expires))
                minted.append(k)
            conn.commit()
            conn.close()

            log_event(token, "sellix_restock_dispatched", client_ip, details=f"Dispatched {qty} keys to digital store")
            self._send_json(200, {"success": True, "count": qty, "keys": minted})
            return

        # Section 55: Slot Reaper & Zombie Cleaner
        elif path == "/api/slots/reap_zombies":
            try:
                # Forward to orchestrator
                req = urllib.request.Request("http://127.0.0.1:9000/api/slots", timeout=2)
                with urllib.request.urlopen(req) as r:
                    sdata = json.loads(r.read().decode())
                reaped = []
                now = time.time()
                for slot_id, sinfo in sdata.get("slots", {}).items():
                    # If slot has been non-idle for > 45 minutes or marked error
                    created = sinfo.get("created_at", now)
                    if sinfo.get("status") in ["error", "zombie"] or (now - created > 2700):
                        kill_body = json.dumps({"slot_id": slot_id}).encode()
                        kreq = urllib.request.Request("http://127.0.0.1:9000/api/slots/kill", data=kill_body, headers={"Content-Type": "application/json"}, method="POST")
                        urllib.request.urlopen(kreq, timeout=3)
                        reaped.append(slot_id)
                self._send_json(200, {"success": True, "reaped_slots": reaped, "count": len(reaped)})
            except Exception as e:
                self._send_json(200, {"success": True, "reaped_slots": [], "error": str(e), "message": "Reaper completed"})
            return

        # Match Concluded Signal (forwarder to Orchestrator port 9000)
        elif path == "/api/match_concluded":
            try:
                body = json.dumps(payload).encode()
                req = urllib.request.Request("http://127.0.0.1:9000/api/match_concluded", data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5) as r:
                    res = json.loads(r.read().decode())
                self._send_json(200, res)
            except urllib.error.HTTPError as he:
                try:
                    err_data = json.loads(he.read().decode())
                    self._send_json(he.code, err_data)
                except Exception:
                    self._send_json(he.code, {"success": False, "error": str(he)})
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})

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
