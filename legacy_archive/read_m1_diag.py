import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = "ps -axo pid,args | grep -i 'riot' | grep -v 'grep'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("=== RUNNING RIOT PROCESSES ===")
print(stdout.read().decode("utf-8", "ignore"))


ssh.close()
