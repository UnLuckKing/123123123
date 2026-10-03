import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Checking RCS files open (lsof)")
stdin, stdout, stderr = ssh.exec_command('lsof -c RiotClientServices | grep Shared')
print(stdout.read().decode())

ssh.close()
