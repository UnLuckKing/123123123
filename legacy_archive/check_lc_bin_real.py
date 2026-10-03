import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'ls -la "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LC DIR REAL ---")
print(stdout.read().decode())

ssh.close()
