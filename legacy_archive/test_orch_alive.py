import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i vanta; curl -s -m 3 http://127.0.0.1:9000/api/health || echo 'LOCAL CURL FAILED'")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
