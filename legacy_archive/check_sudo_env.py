import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """echo PNGGJHc5f7f1 | sudo -S -u slot1 bash -c 'HOME=/Users/slot1 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients'"""
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S pkill -9 -f RiotClientServices')

# Test running with HOME set explicitly
stdin, stdout, stderr = ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S -H -u slot2 bash -c "env"')
print("--- ENV SLOT2 ---")
lines = stdout.read().decode().splitlines()
for l in lines:
    if any(k in l for k in ['HOME', 'USER', 'LOGNAME']):
        print(l)

ssh.close()
