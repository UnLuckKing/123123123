import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_hub.py", "r") as f:
    content = f.read().decode("utf-8")
with open("vanta_hub_backup.py", "w", encoding="utf-8") as f:
    f.write(content)
print(f"Downloaded vanta_hub.py ({len(content)} bytes)")
sftp.close()
ssh.close()
