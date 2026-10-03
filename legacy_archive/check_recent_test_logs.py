import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find "/Applications/League of Legends_slot1.app/Contents/LoL/Logs/LeagueClient Logs" -type f -name "*LeagueClient.log" | xargs tail -n 40'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SLOT1 LC LOG ---")
print(stdout.read().decode())

cmd = 'find "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs" -type f -name "*LeagueClient.log" | xargs tail -n 40'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- SLOT2 LC LOG ---")
print(stdout.read().decode())

ssh.close()
