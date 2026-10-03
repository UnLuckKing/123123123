import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
stdin, stdout, stderr = ssh.exec_command('sed -n "111,170p" "/Applications/League of Legends.app/Contents/LoL/Logs/LeagueClient Logs/2026-09-29T23-03-26_35665_LeagueClient.log"')
print(stdout.read().decode())
ssh.close()
