import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S find /Users/slot2 -name "*lockfile*"')
print("--- SLOT2 LOCKFILES ---")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S lsof -p 31839 | grep -E "lockfile|Config"')
print("--- OPEN FILES 31839 ---")
print(stdout.read().decode())

ssh.close()
