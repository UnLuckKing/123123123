import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, glob

def check_dir(base):
    print("=== Checking:", base)
    for root, dirs, files in os.walk(base):
        for f in files:
            p = os.path.join(root, f)
            if any(k in f.lower() for k in ["eula", "settings", "agreement", "private", "client"]):
                print(" ", p)
                try:
                    with open(p, "r", errors="ignore") as fp:
                        content = fp.read()
                        if "eula" in content.lower():
                            for line in content.splitlines():
                                if "eula" in line.lower():
                                    print("    MATCH:", line.strip())
                except: pass

check_dir("/Users/m1/Library/Application Support/RiotClientData_slot1")
check_dir("/Users/m1/VantaSlots/slot1")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
