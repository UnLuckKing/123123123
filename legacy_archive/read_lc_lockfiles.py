import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('cat "/Applications/League of Legends_slot1.app/Contents/LoL/lockfile"')
print("--- SLOT1 LOCKFILE ---")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('cat "/Applications/League of Legends_slot2.app/Contents/LoL/lockfile"')
print("--- SLOT2 LOCKFILE ---")
print(stdout.read().decode())

ssh.close()
