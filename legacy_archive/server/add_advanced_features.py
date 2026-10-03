# add_advanced_features.py
import re
import os

hub_path = r"C:\Users\hesap\Desktop\nrx.lol-main\server\vanta_hub.py"

with open(hub_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update init_db() to add discord_webhook to resellers and maintenance table
db_migration = '''    # Automatic column migrations
    for col, col_type in [("last_ip", "TEXT"), ("last_seen", "INTEGER"), ("reseller_id", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE licenses ADD COLUMN {col} {col_type}")
        except Exception:
            pass'''

new_db_migration = '''    # Automatic column migrations
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
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('maintenance_mode', 'false')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('maintenance_msg', 'Routine Vanguard telemetry synchronization in progress.')")'''

if db_migration in content:
    content = content.replace(db_migration, new_db_migration)
    print("[SUCCESS] Injected DB migrations for discord_webhook and system_config!")

# 2. Add discord notification helper function
webhook_func = '''def send_discord_webhook(webhook_url, title, description, color=0x00f2fe, fields=None):
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

'''

if "def send_discord_webhook" not in content:
    # Place right before log_event
    content = content.replace("def log_event(", webhook_func + "def log_event(")
    print("[SUCCESS] Injected send_discord_webhook helper!")

# 3. Add API routes in do_POST for bulk_generate, reseller settings, and admin maintenance
post_hook_anchor = 'elif path == "/api/reseller/reset_hwid":'
advanced_post_routes = '''elif path == "/api/reseller/bulk_generate":
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

        elif path == "/api/reseller/reset_hwid":'''

if post_hook_anchor in content and "elif path == \"/api/reseller/bulk_generate\":" not in content:
    content = content.replace(post_hook_anchor, advanced_post_routes)
    print("[SUCCESS] Injected POST routes for bulk_generate, settings, and maintenance!")

# 4. Update /api/announcements in do_GET to read maintenance mode
ann_anchor = '''        elif path == "/api/announcements":
            self._send_json(200, {
                "active": True,
                "message": "VANTA Apex v5.2 // Zero-Detection Engine Online",
                "severity": "info",
                "timestamp": int(time.time())
            })'''

new_ann = '''        elif path == "/api/announcements":
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
                })'''

if ann_anchor in content:
    content = content.replace(ann_anchor, new_ann)
    print("[SUCCESS] Updated /api/announcements with dynamic maintenance mode!")

# 5. In HTML_RESELLER_PORTAL: add Bulk Minting section and Webhook settings
old_reseller_panel = '''                    <button class="btn btn-primary" style="width:100%;" onclick="generateKey()">Generate License Key</button>
                </div>

                <!-- API Integration Panel -->'''

new_reseller_panel = '''                    <button class="btn btn-primary" style="width:100%;" onclick="generateKey()">Generate Single Key</button>
                    <button class="btn btn-action" style="width:100%; margin-top:8px; border-color:var(--warning); color:var(--warning);" onclick="openBulkMintModal()">📦 Bulk Mint for Store Stock</button>
                </div>

                <!-- API Integration & Webhook Panel -->'''

if old_reseller_panel in content:
    content = content.replace(old_reseller_panel, new_reseller_panel)
    print("[SUCCESS] Injected Bulk Mint button in Reseller Portal HTML!")

# Add Bulk Mint Modal & Webhook settings in HTML_RESELLER_PORTAL right before </body>
modal_and_webhook_html = '''    <!-- Bulk Mint Modal -->
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
'''

# Insert bulk modal JS and functions
bulk_js = '''
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
'''

if "function openBulkMintModal" not in content:
    # Insert modal HTML before closing </body> of reseller portal
    content = content.replace("    <div class=\"toast\" id=\"toast\"></div>\n\n    <script>", modal_and_webhook_html + "    <div class=\"toast\" id=\"toast\"></div>\n\n    <script>")
    content = content.replace("if (currentResellerKey) {\n            loadResellerData();\n        }", bulk_js + "\n        if (currentResellerKey) {\n            loadResellerData();\n        }")
    print("[SUCCESS] Injected Bulk Mint UI & JS into HTML_RESELLER_PORTAL!")

with open(hub_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] vanta_hub.py updated with advanced features!")
