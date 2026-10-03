import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'cat "/Applications/League of Legends_slot2.app/Contents/LoL/League of Legends.app/Contents/MacOS/LeagueClientUx" | head -n 5'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- UX FILE TYPE ---")
stdin2, stdout2, stderr2 = ssh.exec_command('file "/Applications/League of Legends_slot2.app/Contents/LoL/League of Legends.app/Contents/MacOS/LeagueClientUx"')
print(stdout2.read().decode())

cmd = 'find "/Applications/League of Legends.app" -name "*wrapper*"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- WRAPPERS FOUND ---")
print(stdout.read().decode())

cmd = 'find "/Users/m1" -name "*wrapper*"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- USER WRAPPERS ---")
print(stdout.read().decode())

ssh.close()
