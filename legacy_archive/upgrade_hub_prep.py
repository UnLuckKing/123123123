import re
import json

with open("current_server_vanta_hub.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add /api/admin/reseller/delete endpoint if not present
reseller_delete_endpoint = """
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
"""

if 'elif path == "/api/admin/reseller/delete":' not in code:
    target = 'elif path == "/api/admin/reseller/toggle":'
    pos = code.find(target)
    if pos != -1:
        code = code[:pos] + reseller_delete_endpoint.strip() + "\n\n        " + code[pos:]
        print("Added /api/admin/reseller/delete endpoint")

# 2. Check /api/reseller/info to make sure keys query handles null safe
# Look at c.execute("SELECT id, license_key, role, hwid, status, created_at, expires_at, note FROM licenses WHERE reseller_id = ? ORDER BY id DESC", (key,))
# Everything is already clean there.

with open("vanta_hub_modified.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved preliminary vanta_hub_modified.py, size:", len(code))
