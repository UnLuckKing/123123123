import paramiko
import time
import os
import json
import hashlib

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

print("Connected to M1. Starting deployment...")
sftp = ssh.open_sftp()

# 1. Upload orchestrator
sftp.put("vanta_orchestrator.py", "/Users/m1/vanta_orchestrator.py")
print("[+] Uploaded vanta_orchestrator.py")

# 2. Upload hub
sftp.put("server/vanta_hub.py", "/Users/m1/vanta_hub.py")
print("[+] Uploaded vanta_hub.py")

# 3. Ensure releases directory exists
stdin, stdout, stderr = ssh.exec_command("mkdir -p /Users/m1/releases")
stdout.channel.recv_exit_status()

# 4. Upload latest client executable to releases
exe_local = "C:/Users/hesap/Desktop/VANTA_CUSTOMER/vanta.exe"
if os.path.exists(exe_local):
    with open(exe_local, "rb") as f:
        data = f.read()
        sha = hashlib.sha256(data).hexdigest()
        size = len(data)
    
    sftp.put(exe_local, "/Users/m1/releases/vanta.exe")
    print(f"[+] Uploaded release vanta.exe ({size} bytes, sha256: {sha[:16]}...)")
    
    version_info = {
        "version": "6.5.0",
        "mandatory": True,
        "changelog": "Apex v6.5: Direct Ultra-Low Latency UDP Routing (15-25ms) + 25 Isolated Slots + Autonomous In-Place Self-Updater",
        "download_url": "http://51.159.121.126:8088/api/client/download_latest",
        "file_size": size,
        "sha256": sha
    }
    with sftp.open("/Users/m1/releases/version.json", "w") as f:
        f.write(json.dumps(version_info, indent=2))
    print("[+] Created /Users/m1/releases/version.json")

sftp.close()

# 5. Restart services cleanly
print("[*] Restarting orchestrator and hub on M1...")
ssh.exec_command("pkill -9 -f 'vanta_orchestrator.py' || true")
ssh.exec_command("pkill -9 -f 'vanta_hub.py' || true")
time.sleep(1)

ssh.exec_command("nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orchestrator.log 2>&1 &")
ssh.exec_command("nohup python3 /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &")
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'vanta_orchestrator|vanta_hub' | grep -v grep")
print("=== PROCESSES ===")
print(stdout.read().decode("utf-8", "ignore"))

ssh.close()
print("Deployment completed successfully.")
