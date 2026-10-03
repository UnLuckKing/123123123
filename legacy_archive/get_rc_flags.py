import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
cmd = """
strings '/Applications/Riot Client.app/Contents/MacOS/RiotClientServices' | grep -E '^--' | sort -u
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("RiotClientServices flags:\n" + stdout.read().decode())
ssh.close()
