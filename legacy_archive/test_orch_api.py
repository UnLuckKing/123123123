import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:9000/api/slots; echo ''; curl -s http://127.0.0.1:9000/api/health")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
