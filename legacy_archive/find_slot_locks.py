import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S find /Users/slot1 /Users/slot2 -name "*lockfile*"')
print("--- LOCKFILES ---")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S lsof -p 31834 | grep -E "REG|DIR"')
print("--- OPEN FILES 31834 ---")
print(stdout.read().decode()[:1000])

ssh.close()
