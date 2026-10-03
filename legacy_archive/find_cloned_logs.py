import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot1.app/Contents/LoL/Logs" -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- ALL LOGS IN SLOT1 APP ---")
files = stdout.read().decode().splitlines()
for f in files:
    print(f)

cmd = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/Logs" -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- ALL LOGS IN SLOT2 APP ---")
files = stdout.read().decode().splitlines()
for f in files:
    print(f)

ssh.close()
