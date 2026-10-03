import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    d = f.read()

idx = d.find(b"Setting SDK configuration setting {} from command-line argument {}")
if idx != -1:
    print(d[idx-100:idx+300])
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
