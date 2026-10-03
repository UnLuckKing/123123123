import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
grep -rn "enable_eula" /Applications/ "/Users/Shared/Riot Games" 2>/dev/null
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("EULA OCCURRENCES:\n" + stdout.read().decode())

ssh.close()
