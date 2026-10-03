import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -in "LeagueClientUx Helper" /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_LeagueClient.log | head -n 30'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- UX HELPER IN LOG ---")
print(stdout.read().decode())

cmd = 'head -n 100 /Applications/League\\ of\\ Legends_slot2.app/Contents/LoL/Logs/LeagueClient\\ Logs/2026-09-29T21-49-56_30352_30365_LeagueClientUx.log | grep -iE "port|listen|auth"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- UX LOG HEAD ---")
print(stdout.read().decode())

ssh.close()
