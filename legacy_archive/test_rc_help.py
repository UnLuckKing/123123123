import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Test running RCS with --product-install-path
cmd = """
/Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --help 2>&1 | head -n 30
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
