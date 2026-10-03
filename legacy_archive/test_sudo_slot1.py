import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Test running a command as slot1 with full debugging
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S -u slot1 id')
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

ssh.close()
