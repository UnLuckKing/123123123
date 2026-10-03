import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S cat "/Users/slot2/Library/Logs/Riot Games/Riot Client/Launcher/2026-09-29T22-12-12_31958_Launcher.log"')
print("--- LAUNCHER LOG ---")
print(stdout.read().decode())

ssh.close()
