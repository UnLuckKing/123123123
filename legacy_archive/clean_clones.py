import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Deleting 74GB cloned apps...")
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S rm -rf "/Applications/League of Legends_slot1.app" "/Applications/League of Legends_slot2.app" "/Applications/Riot Client_slot1.app"')
print(stdout.read().decode())
print(stderr.read().decode())

print("Checking disk space...")
stdin, stdout, stderr = ssh.exec_command('df -h /System/Volumes/Data')
print(stdout.read().decode())

ssh.close()
