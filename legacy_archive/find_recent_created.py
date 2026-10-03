import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot1.app" -mmin -2 -type f; find "/Applications/League of Legends_slot2.app" -mmin -2 -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- NEWLY CREATED FILES IN SLOT APPS ---")
print(stdout.read().decode())

ssh.close()
