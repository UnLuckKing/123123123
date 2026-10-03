import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
grep -C 5 "productSessionEnd" '/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-38-06_38858_Riot Client.log'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("PRODUCT SESSION END LOG:\n" + stdout.read().decode())

cmd2 = """
grep -E -C 3 "productLaunch|launching|LeagueClient" '/Users/m1/Library/Logs/Riot Games/Riot Client/Riot Client Logs/2026-09-29T23-38-06_38858_Riot Client.log'
"""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("PRODUCT LAUNCH LOG:\n" + stdout.read().decode())

ssh.close()
