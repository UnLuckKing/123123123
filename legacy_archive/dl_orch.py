import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    content = f.read().decode("utf-8", "ignore")
with open("vanta_orchestrator_remote.py", "w", encoding="utf-8") as f:
    f.write(content)
print(f"Downloaded vanta_orchestrator.py ({len(content)} chars, {len(content.splitlines())} lines)")
sftp.close()
ssh.close()
