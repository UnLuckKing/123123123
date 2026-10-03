import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
# Check if LeagueClientUx is listening on any port on Mac
stdin, stdout, stderr = ssh.exec_command("ps -eo pid,command | grep -i LeagueClientUx | grep -v grep")
print("LeagueClientUx process:\n", stdout.read().decode("utf-8", "ignore"))
ssh.close()
