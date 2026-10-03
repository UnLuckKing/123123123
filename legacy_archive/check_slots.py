import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep -iE 'Riot|League'")
print("PROCESSES:")
print(stdout.read().decode("utf-8", "ignore"))

stdin, stdout, stderr = ssh.exec_command("grep -n -C 10 'def do_GET' /Users/m1/vanta_orchestrator.py")
print("GET HANDLERS:")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
