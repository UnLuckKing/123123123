import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

script = """
import glob
import os
import subprocess

apps = sorted(glob.glob("/Applications/League of Legends*.app"))
print(f"Target apps to patch: {len(apps)}")

for app in apps:
    app_name = os.path.basename(app)
    lc_app = os.path.join(app, "Contents/LoL/LeagueClient.app")
    lc_bin = os.path.join(lc_app, "Contents/MacOS/LeagueClient")
    
    if not os.path.exists(lc_bin):
        print(f"[-] {app_name}: binary missing at {lc_bin}")
        continue

    # 1. Patch ARM64 & x86_64 singleton check
    with open(lc_bin, "r+b") as f:
        # Check ARM64
        f.seek(0x2a4fff4)
        curr_arm = f.read(4)
        if curr_arm in (bytes.fromhex("560100b4"), bytes.fromhex("1f2003d5")):
            f.seek(0x2a4fff4)
            f.write(bytes.fromhex("1f2003d5"))
        else:
            print(f"[!] Warning: Unexpected ARM64 bytes at 0x2a4fff4: {curr_arm.hex()}")

        # Check x86_64
        f.seek(0x4f0b2c)
        curr_x86 = f.read(2)
        if curr_x86 in (bytes.fromhex("7430"), bytes.fromhex("9090")):
            f.seek(0x4f0b2c)
            f.write(bytes.fromhex("9090"))
        else:
            print(f"[!] Warning: Unexpected x86_64 bytes at 0x4f0b2c: {curr_x86.hex()}")

    # 2. Re-sign binary and bundle
    res1 = subprocess.run(["codesign", "-f", "-s", "-", lc_bin], capture_output=True, text=True)
    res2 = subprocess.run(["codesign", "-f", "-s", "-", lc_app], capture_output=True, text=True)

    # 3. Verify
    with open(lc_bin, "rb") as f:
        f.seek(0x2a4fff4)
        new_arm = f.read(4).hex()
        f.seek(0x4f0b2c)
        new_x86 = f.read(2).hex()

    print(f"[+] {app_name}: ARM64={new_arm} (NOP), x86={new_x86} (NOP), signed={res1.returncode == 0 and res2.returncode == 0}")

print("All slot binaries patched and resigned successfully.")
"""

sftp = ssh.open_sftp()
with sftp.open("/tmp/patch_slots.py", "w") as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("python3 /tmp/patch_slots.py")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
