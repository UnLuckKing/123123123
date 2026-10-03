import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S lsof -p 31958')
print("--- LSOF 31958 ALL ---")
lines = stdout.read().decode().splitlines()
print(f"Total files: {len(lines)}")
for l in lines[:25]:
    print(l)

ssh.close()
