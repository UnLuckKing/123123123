import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, glob
libs = glob.glob("/Applications/Riot Client.app/Contents/Frameworks/*.dylib")
print("Libs:", libs)
for lib in libs:
    with open(lib, "rb") as f:
        d = f.read()
    if b"terminated with exit code" in d or b"product-session" in d:
        print(f"Found in {lib}")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
