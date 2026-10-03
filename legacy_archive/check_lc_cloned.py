import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/LeagueClient.app/Contents/MacOS" -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SLOT2 LEAGUECLIENT DIR ---")
print(stdout.read().decode())

cmd = 'find "/Applications/League of Legends_slot1.app/Contents/LoL/LeagueClient.app/Contents/MacOS" -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SLOT1 LEAGUECLIENT DIR ---")
print(stdout.read().decode())

ssh.close()
