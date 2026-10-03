import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import urllib.request, ssl, json, os

# Check if there is an active RC lockfile in slot1
lock = "/Users/m1/VantaSlots/slot1/Config/lockfile"
if not os.path.exists(lock):
    print("No lockfile in slot1")
    exit(0)

with open(lock) as f:
    parts = f.read().strip().split(":")
port, token = parts[2], parts[3]
print(f"Testing RC on port {port} with token {token}")

import base64
auth = base64.b64encode(f"riot:{token}".encode()).decode()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    f"https://127.0.0.1:{port}/data-store/v1/product-settings/products/league_of_legends/patchlines/live",
    headers={"Authorization": f"Basic {auth}"}
)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
        print("GET product-settings:", resp.status, resp.read().decode())
except Exception as e:
    print("GET error:", e)

req2 = urllib.request.Request(
    f"https://127.0.0.1:{port}/data-store/v1/product-settings/products/league_of_legends/patchlines/live/product_install_full_path",
    headers={"Authorization": f"Basic {auth}"}
)
try:
    with urllib.request.urlopen(req2, context=ctx, timeout=3) as resp:
        print("GET product_install_full_path:", resp.status, resp.read().decode())
except Exception as e:
    print("GET path error:", e)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
