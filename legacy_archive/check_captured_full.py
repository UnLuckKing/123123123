import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
# Let's inspect the last captured game_args in vanta_orchestrator.log
stdin, stdout, stderr = ssh.exec_command("grep 'Captured 3D Game Engine' /Users/m1/vanta_orchestrator.log | tail -n 2")
print("Captured lines:\n", stdout.read().decode("utf-8", "ignore"))
ssh.close()
