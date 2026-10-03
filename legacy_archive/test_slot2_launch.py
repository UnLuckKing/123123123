import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Starting slot2 directly with -H...")
cmd = 'echo PNGGJHc5f7f1 | sudo -S -H -u slot2 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients > /tmp/slot2.log 2>&1 &'
ssh.exec_command(cmd)

time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('ps -axo user,pid,command | grep slot2 | grep -v grep')
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('cat /tmp/slot2.log')
print("--- SLOT2 LOG ---")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S find /Users/slot2 -name "*lockfile*"')
print("--- SLOT2 LOCK ---")
print(stdout.read().decode())

ssh.close()
