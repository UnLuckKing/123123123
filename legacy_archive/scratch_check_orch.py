import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    lines = f.read().decode("utf-8").splitlines()

print(f"Total lines in orchestrator: {len(lines)}")
found = False
for i, line in enumerate(lines):
    l = line.lower()
    if any(k in l for k in ["role", "vip", "tier", "priority", "standard", "queue"]):
        print(f"{i+1}: {line}")
        found = True

if not found:
    print("No direct role/vip references found in orchestrator lines.")
