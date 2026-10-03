import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'which brew; which tart; which utmctl; sw_vers; uname -m'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- TOOLS ---")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
