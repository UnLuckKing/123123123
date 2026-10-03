import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/LeagueClient.app/Contents/MacOS" -type f'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- FILES IN SLOT2 APP ---")
print(stdout.read().decode())

cmd = 'cat "/Applications/League of Legends_slot2.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"'
stdin, stdout, stderr = ssh.exec_command('file "/Applications/League of Legends_slot2.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"')
print(stdout.read().decode())

ssh.close()
