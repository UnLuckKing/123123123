import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
tail -n 80 '/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-38-06_38858_Riot Client.log'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("RIOT CLIENT LOG (38858):\n" + stdout.read().decode())

cmd2 = """
tail -n 80 '/Users/m1/Library/Logs/Riot Games/Riot Client/Launcher/2026-09-29T23-38-05_38858_Launcher.log'
"""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("LAUNCHER LOG (38858):\n" + stdout.read().decode())

ssh.close()
