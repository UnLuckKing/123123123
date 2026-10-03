import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    data = f.read()

idx = data.find(b"hing is disabled or multiple clients are allowed")
if idx != -1:
    print(data[idx-100:idx+200])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
