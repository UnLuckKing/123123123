import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'cat /Applications/League\\ of\\ Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SCRIPT CONTENT ---")
print(stdout.read().decode())

ssh.close()
