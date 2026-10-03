import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends.app/Contents/LoL/Logs/LeagueClient Logs" -type f -mmin -10 | xargs tail -n 35'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- RECENT LEAGUECLIENT LOGS ---")
print(stdout.read().decode())

ssh.close()
