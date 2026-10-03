import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'ps -axo pid,command | grep -E "32177|32178"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- PS 32177 / 32178 ---")
print(stdout.read().decode())

cmd = 'lsof -p 32177 | grep -E "lockfile|Config"; lsof -p 32178 | grep -E "lockfile|Config"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LSOF 32177 / 32178 ---")
print(stdout.read().decode())

ssh.close()
