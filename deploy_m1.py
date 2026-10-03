import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

sftp = client.open_sftp()
local_path = r"C:\Users\hesap\Desktop\nrx.lol-main\vanta_orchestrator.py"
remote_path = "/Users/m1/vanta_orchestrator.py"

print(f"Uploading {local_path} to {remote_path}...")
sftp.put(local_path, remote_path)
sftp.close()
print("Upload completed.")

# Check py_compile on M1
stdin, stdout, stderr = client.exec_command('python3 -m py_compile /Users/m1/vanta_orchestrator.py')
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("COMPILE ERROR:\n" + err)
else:
    print("PYTHON COMPILE OK!")

# Also copy to vanta-auth server location as backup
client.exec_command('cp /Users/m1/vanta_orchestrator.py /Users/m1/vanta-auth/app/server/vanta_orchestrator.py')

# Restart service cleanly
stdin, stdout, stderr = client.exec_command('''
launchctl kickstart -k gui/501/com.vanta.orchestrator 2>/dev/null || (pkill -9 -f "vanta_orchestrator.py"; nohup python3 /Users/m1/vanta_orchestrator.py >/Users/m1/orchestrator.log 2>&1 &)
''')
print("RESTART OUTPUT:\n" + stdout.read().decode('utf-8', errors='replace'))

client.close()
