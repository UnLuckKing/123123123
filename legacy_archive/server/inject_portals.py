# inject_portals.py - Generates HTML_RESELLER_PORTAL & HTML_CUSTOMER_PORTAL and wires routes in vanta_hub.py
import re
import os

hub_path = r"C:\Users\hesap\Desktop\nrx.lol-main\server\vanta_hub.py"

with open(hub_path, "r", encoding="utf-8") as f:
    content = f.read()

HTML_RESELLER_PORTAL = '''<!DOCTYPE html>
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
            max-width: 1200px;
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
            padding: 8px 16px;
            border-radius: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .credits-pill b { color: var(--warning); font-size: 15px; }

        /* Auth Screen */
        #authSection {
            max-width: 440px;
            margin: 80px auto;
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            padding: 36px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6);
        }
        #authSection h2 { font-size: 20px; margin-bottom: 8px; }
        #authSection p { color: var(--text-dim); font-size: 14px; margin-bottom: 24px; }
        
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
        .kpi-value { font-size: 26px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }

        .panels-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        @media (max-width: 900px) { .panels-grid { grid-template-columns: 1fr; } }

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
        td { padding: 12px 14px; border-bottom: 1px solid var(--surface-border); font-family: 'JetBrains Mono', monospace; }
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
            <p>Enter your Vanta Reseller Partner Access Key to manage client licenses and balance.</p>
            <input type="text" class="form-control" id="resellerKeyInput" placeholder="VANTA-RES-XXXXXXXXXXXXXXXX" onkeydown="if(event.key==='Enter') loginReseller()">
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

            <div class="panels-grid">
                <!-- Mint Key Panel -->
                <div class="card">
                    <div class="card-header">
                        <h3>⚡ Mint Customer License</h3>
                        <span class="badge badge-partner">1 Credit / Key</span>
                    </div>
                    <div class="form-group">
                        <label>License Duration</label>
                        <select class="form-control" id="mintDays">
                            <option value="1">1 Day Access (1 Credit)</option>
                            <option value="7">7 Days Weekly (1 Credit)</option>
                            <option value="30" selected>30 Days Monthly (1 Credit)</option>
                            <option value="365">1 Year / Lifetime (1 Credit)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Customer Tier / Role</label>
                        <select class="form-control" id="mintRole">
                            <option value="user">Standard User (Match Bypass)</option>
                            <option value="vip">VIP Member (Priority VM Queue)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Buyer Reference / Discord Tag</label>
                        <input type="text" class="form-control" id="mintNote" placeholder="e.g. Discord: user#1234 / Order #509">
                    </div>
                    <button class="btn btn-primary" style="width:100%;" onclick="generateKey()">Generate License Key</button>
                </div>

                <!-- API Integration Panel -->
                <div class="card">
                    <div class="card-header">
                        <h3>🤖 Automated Store Integration</h3>
                        <span class="badge badge-vip">REST API v1</span>
                    </div>
                    <p style="font-size:13px; color:var(--text-dim); margin-bottom:10px;">
                        Connect your Sellix, Shoppy, Tebex, or custom Discord bot for 100% automated key delivery upon payment:
                    </p>
                    <div class="form-group">
                        <label>Your Bearer Token</label>
                        <input type="text" class="form-control" id="apiTokenDisplay" readonly onclick="copyText(this.value)">
                    </div>
                    <div class="form-group">
                        <label>Webhook / API Command Snippet</label>
                        <div class="api-snippet" id="apiCurlSnippet">Loading API configuration...</div>
                    </div>
                </div>
            </div>

            <!-- Client Keys Table -->
            <div class="card" style="margin-bottom: 24px;">
                <div class="card-header">
                    <h3>📋 My Issued Customer Keys</h3>
                    <div style="display:flex; gap:10px;">
                        <input type="text" class="form-control" style="margin-bottom:0; width:260px; padding:6px 12px; font-size:13px;" id="keySearchInput" placeholder="Search key or note..." onkeyup="renderTable()">
                        <button class="btn btn-action btn-sm" onclick="loadResellerData()">🔄 Refresh</button>
                    </div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>LICENSE KEY</th>
                                <th>PLAN</th>
                                <th>CUSTOMER REF</th>
                                <th>BOUND HWID</th>
                                <th>STATUS</th>
                                <th>EXPIRES AT</th>
                                <th>ACTIONS</th>
                            </tr>
                        </thead>
                        <tbody id="keysTableBody">
                            <tr><td colspan="7" style="text-align:center; color:var(--text-dim);">Loading client keys...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let currentResellerKey = localStorage.getItem('vanta_reseller_key') || '';
        let resellerData = null;

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        function copyText(str) {
            navigator.clipboard.writeText(str);
            showToast('Copied to clipboard: ' + str);
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

            document.getElementById('resellerCredits').innerText = resellerData.credits;
            document.getElementById('kpiCredits').innerText = resellerData.credits;
            document.getElementById('kpiKeysCount').innerText = resellerData.keys ? resellerData.keys.length : 0;
            
            const activeCount = (resellerData.keys || []).filter(k => k.status === 'active').length;
            document.getElementById('kpiActiveCount').innerText = activeCount;
            document.getElementById('kpiStatus').innerText = resellerData.status.toUpperCase();

            document.getElementById('apiTokenDisplay').value = currentResellerKey;
            document.getElementById('apiCurlSnippet').innerText = 
`curl -X POST http://51.159.121.126:8088/api/v1/reseller/mint_key \\
  -H "Authorization: Bearer ${currentResellerKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"days": 30, "role": "user", "note": "Order #1042"}'`;

            renderTable();
        }

        function renderTable() {
            const tbody = document.getElementById('keysTableBody');
            const q = (document.getElementById('keySearchInput').value || '').toLowerCase();
            const keys = (resellerData.keys || []).filter(k => 
                k.license_key.toLowerCase().includes(q) || (k.note && k.note.toLowerCase().includes(q))
            );

            if (keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-dim); padding:20px;">No issued keys found.</td></tr>';
                return;
            }

            tbody.innerHTML = keys.map(k => `
                <tr>
                    <td style="color:var(--accent); font-weight:700; cursor:pointer;" onclick="copyText('${k.license_key}')" title="Click to copy">
                        ${k.license_key} 📋
                    </td>
                    <td><span class="badge ${k.role === 'vip' ? 'badge-vip' : 'badge-partner'}">${k.role.toUpperCase()}</span></td>
                    <td style="color:#fff;">${k.note || '—'}</td>
                    <td>${k.hwid ? `<span style="color:#aaa;">${k.hwid.substring(0,10)}...</span>` : '<span style="color:var(--success);">Unbound</span>'}</td>
                    <td><span class="status-pill status-${k.status}"></span>${k.status.toUpperCase()}</td>
                    <td>${new Date(k.expires_at * 1000).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-action btn-sm" onclick="resetCustomerHWID('${k.license_key}')">Reset HWID</button>
                    </td>
                </tr>
            `).join('');
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
                prompt('Customer License Key Generated! Copy below and send to buyer:', data.license_key);
                loadResellerData();
            } else {
                alert('Generation failed: ' + data.error);
            }
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

        if (currentResellerKey) {
            loadResellerData();
        }
    </script>
</body>
</html>'''

HTML_CUSTOMER_PORTAL = '''<!DOCTYPE html>
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
</html>'''

# Check if templates already injected
if "HTML_RESELLER_PORTAL" not in content:
    # Insert right before class VantaHubHandler
    anchor = "class VantaHubHandler(BaseHTTPRequestHandler):"
    portal_defs = f'HTML_RESELLER_PORTAL = """{HTML_RESELLER_PORTAL}"""\n\nHTML_CUSTOMER_PORTAL = """{HTML_CUSTOMER_PORTAL}"""\n\n'
    content = content.replace(anchor, portal_defs + anchor)
    print("[SUCCESS] Injected HTML_RESELLER_PORTAL and HTML_CUSTOMER_PORTAL definitions!")
else:
    print("[INFO] HTML_RESELLER_PORTAL already present.")

# Route updates in do_GET
get_anchor = 'if path in ["/", "/admin", "/reseller", "/dashboard"]:'
new_get_routing = '''if path in ["/", "/admin", "/dashboard"]:
            self._send_html(HTML_DASHBOARD)
            return

        elif path == "/reseller":
            self._send_html(HTML_RESELLER_PORTAL)
            return

        elif path in ["/customer", "/portal"]:
            self._send_html(HTML_CUSTOMER_PORTAL)
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
            return'''

if get_anchor in content:
    content = content.replace(get_anchor, new_get_routing)
    print("[SUCCESS] Injected GET routing for /reseller and /customer!")

# Route updates in do_POST
post_anchor = 'elif path == "/api/keys/reset_hwid":'
new_post_routing = '''elif path == "/api/reseller/reset_hwid":
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

        elif path == "/api/keys/reset_hwid":'''

if post_anchor in content and "elif path == \"/api/reseller/reset_hwid\":" not in content:
    content = content.replace(post_anchor, new_post_routing)
    print("[SUCCESS] Injected POST routing for reseller and customer reset_hwid!")

with open(hub_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] vanta_hub.py completely updated!")
