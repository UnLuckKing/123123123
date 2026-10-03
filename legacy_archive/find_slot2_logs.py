import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, glob

dirs = [
    "/Users/m1/VantaSlots/slot2",
    "/Applications/League of Legends_slot2.app/Contents/LoL/Logs",
    "/Users/m1/Library/Logs/Riot Games"
]

for d in dirs:
    print("=== Checking:", d)
    if os.path.exists(d):
        logs = glob.glob(d + "/**/*.log", recursive=True)
        for log in sorted(logs, key=os.path.getmtime, reverse=True)[:5]:
            print(f"{log} (mtime: {os.path.getmtime(log)}, size: {os.path.getsize(log)})")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
