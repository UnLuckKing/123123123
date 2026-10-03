import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
find /Users/m1 -name "RiotGamesPrivateSettings.yaml" 2>/dev/null
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("SAVED SESSIONS ON M1:\n" + stdout.read().decode())
ssh.close()
