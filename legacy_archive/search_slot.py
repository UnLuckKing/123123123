import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = 'grep -rn "a72f7f16" /tmp /Users/m1/ 2>/dev/null | head -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode("utf-8", "ignore"))

ssh.close()
