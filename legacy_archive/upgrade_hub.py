import sys

# Read the base vanta_hub_modified.py
with open("vanta_hub_modified.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update HTML_RESELLER_PORTAL
new_reseller_portal = '''HTML_RESELLER_PORTAL = """<!DOCTYPE html>
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
`curl -X POST http://51.159.121.126:8088/api/v1/reseller/mint_key \\
  -H "Authorization: Bearer ${currentResellerKey}" \\
  -H "Content-Type: application/json" \\
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
                alert(`Sub-Reseller created!\\nKey: ${data.sub_key}\\nCredits: ${data.credits}`);
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
                document.getElementById('bulkOutputArea').value = data.keys.join('\\n');
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
</html>"""'''

# Replace HTML_RESELLER_PORTAL in content
start_idx = content.find("HTML_RESELLER_PORTAL =")
end_idx = content.find("HTML_CUSTOMER_PORTAL =")
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_reseller_portal + "\n\n" + content[end_idx:]
    print("Successfully replaced HTML_RESELLER_PORTAL")
else:
    print("Could not find HTML_RESELLER_PORTAL bounds")

# 2. Update renderResellers in HTML_DASHBOARD to add Open Portal link, Copy Portal URL, and Delete
old_actions = """                        <button class="btn btn-primary btn-sm" onclick="openAddCreditsModal('${r.reseller_key}', '${r.name}')">+ Credits</button>
                        <button class="btn btn-warning btn-sm" onclick="toggleReseller('${r.reseller_key}')">${r.status === 'active' ? 'Suspend' : 'Activate'}</button>
                        <button class="btn btn-action btn-sm" onclick="openResellerPortal('${r.reseller_key}')">Portal</button>"""

new_actions = """                        <button class="btn btn-primary btn-sm" onclick="openAddCreditsModal('${r.reseller_key}', '${r.name}')">+ Credits</button>
                        <button class="btn btn-action btn-sm" onclick="window.open('/reseller?key=' + encodeURIComponent('${r.reseller_key}'), '_blank')">Open Portal ↗</button>
                        <button class="btn btn-action btn-sm" onclick="copyToClipboard(window.location.origin + '/reseller?key=' + encodeURIComponent('${r.reseller_key}'))" title="Copy Partner Access Link">Copy Link</button>
                        <button class="btn btn-warning btn-sm" onclick="toggleReseller('${r.reseller_key}')">${r.status === 'active' ? 'Suspend' : 'Activate'}</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteReseller('${r.reseller_key}', '${r.name}')">Delete</button>"""

if old_actions in content:
    content = content.replace(old_actions, new_actions)
    print("Replaced old_actions in renderResellers")
else:
    print("old_actions pattern not found in content, checking alternative")

# 3. Add deleteReseller JS function in HTML_DASHBOARD
delete_reseller_js = """
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
"""

if "async function deleteReseller" not in content and "async function toggleReseller" in content:
    content = content.replace("async function toggleReseller", delete_reseller_js.strip() + "\n\n        async function toggleReseller")
    print("Added deleteReseller JS function to dashboard")

with open("vanta_hub_upgraded_final.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Saved vanta_hub_upgraded_final.py, size:", len(content))
