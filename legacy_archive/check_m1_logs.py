import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find /Users/m1/Library/Logs/LeagueClient* -type f -mmin -15 | xargs tail -n 25'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- USER M1 LOGS ---")
print(stdout.read().decode())

cmd = 'ls -la /Users/m1/Library/Logs/'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- M1 LOGS DIR ---")
print(stdout.read().decode())

ssh.close()
