import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Cloning app...")
ssh.exec_command('rm -rf "/Applications/League of Legends_slot1.app"')
ssh.exec_command('cp -c -R "/Applications/League of Legends.app" "/Applications/League of Legends_slot1.app"')
time.sleep(2)
print("Listing Applications...")
stdin, stdout, stderr = ssh.exec_command('ls -d /Applications/League*')
print(stdout.read().decode())
ssh.close()
