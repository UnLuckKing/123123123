import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Test running a command as slot1 and slot2
cmd = 'echo PNGGJHc5f7f1 | sudo -S -u slot1 whoami; echo PNGGJHc5f7f1 | sudo -S -u slot2 whoami'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- TEST SUDO USERS ---")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
