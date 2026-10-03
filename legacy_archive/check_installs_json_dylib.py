import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
cmd = """
python3 -c '
with open("/Applications/Riot Client.app/Contents/Frameworks/libRiotClientFoundation.dylib", "rb") as f:
    d = f.read()

idx = d.find(b"RiotClientInstalls.json")
while idx != -1:
    print("Match at", idx, ":", d[max(0, idx-100):min(len(d), idx+150)])
    idx = d.find(b"RiotClientInstalls.json", idx+1)
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
