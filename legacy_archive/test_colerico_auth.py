import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, subprocess, time, urllib.request, ssl, base64

# Setup test dir
test_dir = "/tmp/test_colerico"
os.makedirs(f"{test_dir}/Data", exist_ok=True)
os.makedirs(f"{test_dir}/Config", exist_ok=True)

with open("/Users/m1/RiotGamesPrivateSettings.yaml") as f:
    c = f.read()
with open(f"{test_dir}/Data/RiotGamesPrivateSettings.yaml", "w") as f:
    f.write(c)

cmd = [
    "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices",
    "--allow-multiple-clients",
    f"--user-data-root={test_dir}"
]

p = subprocess.Popen(cmd)
time.sleep(4)

lockfile = f"{test_dir}/Config/lockfile"
if os.path.exists(lockfile):
    with open(lockfile) as f:
        parts = f.read().strip().split(":")
    port, token = parts[2], parts[3]
    print(f"RC online at port {port}")
    
    auth_hdr = base64.b64encode(f"riot:{token}".encode()).decode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for i in range(10):
        try:
            req = urllib.request.Request(f"https://127.0.0.1:{port}/rso-auth/v1/session", headers={"Authorization": f"Basic {auth_hdr}"})
            with urllib.request.urlopen(req, context=ctx, timeout=2) as r:
                body = r.read().decode()
                print("Session status:", body[:120])
                if "authenticated" in body:
                    print("SUCCESS! Refresh token restored session successfully!")
                    break
        except Exception as e:
            print("Poll err:", e)
        time.sleep(1)

p.kill()
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)
ssh.close()
