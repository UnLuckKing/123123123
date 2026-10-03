import requests
import json
import time

HUB_URL = "http://51.159.121.126:8088"
ORCH_URL = "http://51.159.121.126:9000"

print("--- VANTA APEX VERIFICATION SUITE ---")

# 1. Orchestrator Health
try:
    r = requests.get(f"{ORCH_URL}/api/slots", timeout=5)
    print(f"[+] Orchestrator /api/slots: HTTP {r.status_code}")
    slots = r.json()
    print(f"    Available slots: {list(slots.keys())}")
except Exception as e:
    print(f"[-] Orchestrator health check failed: {e}")

# 2. Orchestrator /api/match_concluded test
try:
    r = requests.post(f"{ORCH_URL}/api/match_concluded", json={"slot_id": "nonexistent_test"}, timeout=5)
    print(f"[+] Orchestrator /api/match_concluded handled: HTTP {r.status_code} (Expected 404 for dummy slot)")
except Exception as e:
    print(f"[-] Orchestrator match_concluded test failed: {e}")

# 3. Hub Health
try:
    r = requests.get(f"{HUB_URL}/api/admin/slots", timeout=5)
    print(f"[+] Hub /api/admin/slots: HTTP {r.status_code}")
except Exception as e:
    print(f"[-] Hub health check failed: {e}")

# 4. Reseller Creation & Credits
reseller_key = None
try:
    # Get initial resellers
    r = requests.get(f"{HUB_URL}/api/admin/resellers", timeout=5)
    print(f"[+] Hub /api/admin/resellers: HTTP {r.status_code} -> count: {len(r.json())}")

    # Create a reseller
    create_payload = {
        "name": "Test Partner Alpha",
        "credits": 10
    }
    r = requests.post(f"{HUB_URL}/api/admin/reseller/create", json=create_payload, timeout=5)
    res_data = r.json()
    print(f"[+] Create Reseller: {res_data}")
    reseller_key = res_data.get("reseller_key")

    # Add credits
    add_payload = {
        "reseller_key": reseller_key,
        "credits": 5
    }
    r = requests.post(f"{HUB_URL}/api/admin/reseller/add_credits", json=add_payload, timeout=5)
    print(f"[+] Add Credits (+5): {r.json()}")

    # Reseller info
    r = requests.get(f"{HUB_URL}/api/reseller/info?key={reseller_key}", timeout=5)
    print(f"[+] Reseller Info: {r.json()}")
except Exception as e:
    print(f"[-] Reseller workflow failed: {e}")

# 5. Reseller Key Generation & Consumption
customer_key = None
try:
    gen_payload = {
        "reseller_key": reseller_key,
        "note": "Customer Order #1001",
        "days": 30
    }
    r = requests.post(f"{HUB_URL}/api/reseller/generate", json=gen_payload, timeout=5)
    gen_data = r.json()
    print(f"[+] Reseller Generated Key: {gen_data}")
    customer_key = gen_data.get("license_key")

    # Check remaining credits
    r = requests.get(f"{HUB_URL}/api/reseller/info?key={reseller_key}", timeout=5)
    print(f"[+] Reseller Balance after Generation: {r.json().get('credits')} credits remaining")
except Exception as e:
    print(f"[-] Key generation failed: {e}")

# 6. Customer License Authentication with HWID binding
try:
    auth_payload = {
        "license_key": customer_key,
        "hwid": "TEST-HWID-APEX-001"
    }
    r = requests.post(f"{HUB_URL}/api/client/auth", json=auth_payload, timeout=5)
    print(f"[+] Client Auth (First Device): {r.json()}")

    # Try auth with same HWID (re-login)
    r = requests.post(f"{HUB_URL}/api/client/auth", json=auth_payload, timeout=5)
    print(f"[+] Client Auth (Re-login same HWID): {r.json().get('success')}")

    # Try auth with second device (dual device support)
    auth_payload_2 = {
        "license_key": customer_key,
        "hwid": "TEST-HWID-APEX-002"
    }
    r = requests.post(f"{HUB_URL}/api/client/auth", json=auth_payload_2, timeout=5)
    print(f"[+] Client Auth (Second Device): {r.json().get('success')}")

    # Try auth with third device (should fail - exceeds max devices)
    auth_payload_3 = {
        "license_key": customer_key,
        "hwid": "TEST-HWID-APEX-003"
    }
    r = requests.post(f"{HUB_URL}/api/client/auth", json=auth_payload_3, timeout=5)
    print(f"[+] Client Auth (Third Device - Should Fail): {r.json()}")
except Exception as e:
    print(f"[-] Client Auth testing failed: {e}")

# 7. Hub Match Concluded Forwarder
try:
    r = requests.post(f"{HUB_URL}/api/match_concluded", json={"slot_id": "nonexistent_test"}, timeout=5)
    print(f"[+] Hub forwarder /api/match_concluded handled: HTTP {r.status_code}")
except Exception as e:
    print(f"[-] Hub match_concluded test failed: {e}")

print("--- SUITE COMPLETE ---")
