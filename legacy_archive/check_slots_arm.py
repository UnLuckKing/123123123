import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import os

for i in range(1, 6):
    app = f"/Applications/League of Legends_slot{i}.app"
    lc_bin = os.path.join(app, "Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient")
    if not os.path.exists(lc_bin):
        print(f"{app}: MISSING BINARY!")
        continue
    with open(lc_bin, "rb") as f:
        f.seek(0x2a4fff4)
        arm = f.read(4).hex()
        f.seek(0x4f0b2c)
        x86 = f.read(2).hex()
    print(f"slot{i}: ARM64(0x2a4fff4)={arm} (NOP=1f2003d5) x86(0x4f0b2c)={x86} (NOP=9090)")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
