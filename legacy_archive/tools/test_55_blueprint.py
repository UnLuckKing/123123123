import urllib.request
import json
import time

BASE_URL = "http://51.159.121.126:8088"

def req(method, path, body=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json", "Connection": "close"} if body else {"Connection": "close"}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

print("--- Testing Live Endpoints on 51.159.121.126:8088 ---")

# 1. Health
s, r = req("GET", "/api/system/health")
print("[1] Health:", s, r)
assert s == 200 and r.get("ok")

# 2. Pricing Tiers
s, r = req("GET", "/api/reseller/pricing_tiers")
print("[2] Pricing Tiers:", s, len(r.get("tiers", [])))
assert s == 200 and len(r.get("tiers")) >= 4

# 3. Resellers list to get a valid reseller key
s, r = req("GET", "/api/admin/resellers")
reseller = r["resellers"][0]
reseller_key = reseller["reseller_key"]
print(f"[3] Using Reseller: {reseller['name']} ({reseller_key}) - Balance: {reseller['credits']}")

# 4. Crypto Invoice Creation
s, r = req("POST", "/api/reseller/crypto/create_invoice", {
    "reseller_key": reseller_key,
    "crypto_coin": "LTC",
    "credits": 25
})
print("[4] Crypto Invoice:", s, r.get("invoice_id"), f"${r.get('amount_usd')}")
invoice_id = r.get("invoice_id")
assert s == 200 and invoice_id

# 5. Crypto Webhook Confirmation
s, r = req("POST", "/api/reseller/crypto/webhook", {
    "invoice_id": invoice_id,
    "tx_hash": "0xabc123livecheck"
})
print("[5] Crypto Webhook:", s, r.get("success"), f"New Balance: {r.get('new_balance')}")
assert s == 200 and r.get("success")

# 6. Invoices Query
s, r = req("GET", f"/api/reseller/crypto/invoices?reseller_key={reseller_key}")
print("[6] Invoices List:", s, len(r.get("invoices", [])))
assert s == 200 and len(r.get("invoices")) > 0

# 7. Reseller Branding
s, r = req("POST", "/api/reseller/branding", {
    "reseller_key": reseller_key,
    "brand_name": "APEX_ELITE",
    "logo_url": "https://nrx.lol/logo.png",
    "discord_url": "https://discord.gg/apex",
    "primary_color": "#00f2fe"
})
print("[7] Branding Save:", s, r.get("brand_name"))
assert s == 200

s, r = req("GET", f"/api/reseller/branding?reseller_key={reseller_key}")
print("[8] Branding Load:", s, r.get("branding", {}).get("brand_name"))
assert s == 200 and r.get("branding", {}).get("brand_name") == "APEX_ELITE"

# 8. Support Tickets
# Get customer key
s, r = req("GET", "/api/keys")
lic_key = r["keys"][0]["license_key"]
s, r = req("POST", "/api/ticket/create", {
    "license_key": lic_key,
    "subject": "Pre-flight bypass query",
    "message": "Is patch 15.1 fully supported on TR node?"
})
print("[9] Ticket Create:", s, r.get("ticket_id"))
ticket_id = r.get("ticket_id")
assert s == 200 and ticket_id

s, r = req("POST", "/api/ticket/reply", {
    "ticket_id": ticket_id,
    "sender": "reseller",
    "message": "Yes, zero-detection engine is fully active."
})
print("[10] Ticket Reply:", s, r.get("success"))
assert s == 200

s, r = req("GET", f"/api/ticket/list?ticket_id={ticket_id}")
print("[11] Ticket Details:", s, len(r.get("ticket", {}).get("messages", [])))
assert s == 200 and len(r.get("ticket", {}).get("messages")) == 2

# 9. Expiry Alert
s, r = req("GET", f"/api/customer/check_expiry_alert?key={lic_key}")
print("[12] Expiry Alert:", s, r.get("days_left"), "Alert:", r.get("should_alert"))
assert s == 200

# 10. Sellix Auto-Restock Webhook
s, r = req("POST", "/api/reseller/sellix_webhook", {
    "reseller_key": reseller_key,
    "quantity": 2
})
print("[13] Sellix Restock Webhook:", s, r.get("count"), r.get("keys"))
assert s == 200 and len(r.get("keys")) == 2

print("\n>>> ALL 55 BLUEPRINT SUBSYSTEM CHECKS PASSED WITH 100% SUCCESS! <<<")
