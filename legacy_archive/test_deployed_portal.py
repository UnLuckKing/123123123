import urllib.request

base = "http://51.159.121.126:8088"

# Test 1: Fetch reseller portal page with query param
req = urllib.request.urlopen(base + "/reseller?key=VANTA-RSL-3D4908C39DE6")
html = req.read().decode("utf-8")
print("Reseller Portal HTML length:", len(html), "Status:", req.status)
print("Has URL Query auto-auth:", "urlParams.get('key')" in html)
print("Has Sub-Resellers tab:", "pane-subs" in html)
print("Has Discord Webhook integration:", "discordWebhookInput" in html)
print("Has Customer Handout Copy:", "copyCustomerHandout" in html)

# Test 2: Fetch Admin dashboard
req2 = urllib.request.urlopen(base + "/admin")
dash = req2.read().decode("utf-8")
print("Admin Dashboard HTML length:", len(dash), "Status:", req2.status)
print("Has Open Portal button:", "Open Portal" in dash)
print("Has Delete reseller handler:", "deleteReseller" in dash)
