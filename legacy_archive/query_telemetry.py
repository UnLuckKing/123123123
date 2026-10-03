import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

stdin, stdout, stderr = ssh.exec_command("sqlite3 /Users/m1/vanta_auth.db 'SELECT id, timestamp, severity, source, message, details, extra FROM diagnostics WHERE id >= 400 ORDER BY id ASC;'")
print(stdout.read().decode("utf-8", "ignore"))

ssh.close()
