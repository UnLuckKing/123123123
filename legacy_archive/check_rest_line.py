import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -in "Started REST server on port" /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_LeagueClient.log'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- REST SERVER LOG ---")
print(stdout.read().decode())

cmd = 'grep -i "port" /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_LeagueClient.log | head -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- PORT LINES IN LC LOG ---")
print(stdout.read().decode())

ssh.close()
