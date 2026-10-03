import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'dscl . -list /Users | grep -E "m[0-9]|slot[0-9]"; id m1; id slot1 2>/dev/null; id m2 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- USERS ---")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
