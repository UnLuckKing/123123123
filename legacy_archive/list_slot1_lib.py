import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find /Users/slot1/Library/ -type f'
stdin, stdout, stderr = ssh.exec_command(f'echo PNGGJHc5f7f1 | sudo -S {cmd}')
print("--- ALL FILES IN SLOT1 LIBRARY ---")
files = stdout.read().decode().splitlines()
for f in files:
    print(f)

ssh.close()
