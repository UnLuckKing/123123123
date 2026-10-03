import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
ls -la "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs"
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("SLOT 2 LC LOGS DIR:\n" + stdout.read().decode())

cmd2 = """
tail -n 60 "/Applications/League of Legends_slot2.app/Contents/LoL/Logs/LeagueClient Logs/2026-09-29T23-22-33_37040_LeagueClient.log"
"""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print("LAST LC LOG:\n" + stdout.read().decode())

ssh.close()
