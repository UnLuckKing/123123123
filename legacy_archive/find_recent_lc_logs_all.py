import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, glob

# Check all logs in /Users/m1 and /Applications/League*
paths = glob.glob("/Applications/League*/**/LeagueClient*.log", recursive=True)
paths += glob.glob("/Users/m1/**/LeagueClient*.log", recursive=True)
paths += glob.glob("/Users/m1/VantaSlots/**/LeagueClient*.log", recursive=True)

print("Found LeagueClient logs:", len(paths))
for p in sorted(paths, key=os.path.getmtime, reverse=True)[:10]:
    print(f"{p} -> mtime: {os.path.getmtime(p)}, size: {os.path.getsize(p)}")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
