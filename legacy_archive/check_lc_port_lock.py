import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -in "lockfile" /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_LeagueClient.log'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- LOCKFILE IN LC LOG ---")
print(stdout.read().decode())

cmd = 'grep -in "port" /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_LeagueClient.log | grep -E "app-port|listening" | head -n 25'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- APP PORT IN LC LOG ---")
print(stdout.read().decode())

ssh.close()
