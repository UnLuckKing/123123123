import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    text = f.read().decode("utf-8")

lines = text.splitlines()
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if "while " in line or "Thread" in line:
        print(f"{i+1}: {line}")
