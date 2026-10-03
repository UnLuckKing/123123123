import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os, glob

base_apps = sorted(glob.glob("/Applications/League of Legends*.app"))
print("Found apps:", base_apps)

for app in base_apps:
    lc_bin = os.path.join(app, "Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient")
    if not os.path.exists(lc_bin):
        print(app + ": LeagueClient binary not found!")
        continue
    with open(lc_bin, "rb") as f:
        f.seek(0x2a4fff4)
        arm_bytes = f.read(4).hex()
        f.seek(0x4f0b2c)
        x86_bytes = f.read(2).hex()
    print(os.path.basename(app) + f": ARM64(0x2a4fff4)={arm_bytes}, x86(0x4f0b2c)={x86_bytes}")
'
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)
ssh.close()
