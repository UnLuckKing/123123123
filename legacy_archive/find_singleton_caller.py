import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    d = f.read()

# ARM64 slice starts at 39305216 (0x257c000)
# String offset in file: 0x4877073
# In slice: 0x4877073 - 0x257c000 = 0x22fb073
# String virtual address: 0x100000000 + 0x22fb073 = 0x1022fb073

print("Searching references to 0x1022fb073 (Did not acquire process singleton)...")
arm_slice = d[0x257c000:]

# In ARM64: adrp to page (0x1022fb000), add offset (0x073)
# Page offset from PC: (0x1022fb000 - (pc & ~0xfff)) >> 12
import struct

# Let us disassemble all adrp instructions or scan for this string reference
import subprocess
cmd = ["otool", "-tvV", "-arch", "arm64", "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

capture = False
lines_after = 0
for line in p.stdout:
    if "Did not acquire process singleton" in line or "0x1022fb073" in line or "7719 ; 0x1022fb000" in line:
        print("MATCH:", line.strip())
        capture = True
        lines_after = 30
    elif capture and lines_after > 0:
        print(" ", line.strip())
        lines_after -= 1
        if lines_after == 0:
            capture = False
p.kill()
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
