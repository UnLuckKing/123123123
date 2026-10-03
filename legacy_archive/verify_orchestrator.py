import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

stdin, stdout, stderr = ssh.exec_command("ps aux | grep vanta_orchestrator | grep -v grep")
print("RUNNING PID:\n", stdout.read().decode("utf-8", "ignore"))

stdin, stdout, stderr = ssh.exec_command('grep -n -C 5 "Active 3D Game Match" /Users/m1/vanta_orchestrator.py')
print("REAPER MATCH CHECK IN SERVER CODE:\n", stdout.read().decode("utf-8", "ignore"))

stdin, stdout, stderr = ssh.exec_command('grep -n -C 5 "TCP_NODELAY" /Users/m1/vanta_orchestrator.py')
print("TCP_NODELAY CHECK:\n", stdout.read().decode("utf-8", "ignore"))

ssh.close()
