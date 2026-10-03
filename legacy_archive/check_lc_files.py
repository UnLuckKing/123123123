import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

lc_path = "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS"
stdin, stdout, stderr = ssh.exec_command(f'ls -la "{lc_path}"')
print("--- LC DIR ---")
print(stdout.read().decode())

ssh.close()
