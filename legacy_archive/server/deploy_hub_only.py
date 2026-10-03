import paramiko
from scp import SCPClient
import time
import os
import urllib.request
import json

M1_IP = '51.159.121.126'
M1_USER = 'm1'
M1_PASS = 'PNGGJHc5f7f1'

print("[1/3] Connecting SSH to M1...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(M1_IP, username=M1_USER, password=M1_PASS)
scp = SCPClient(ssh.get_transport())

server_dir = os.path.dirname(os.path.abspath(__file__))
hub_file = os.path.join(server_dir, 'vanta_hub.py')

print(f"[2/3] Uploading {hub_file} to /Users/m1/vanta_hub.py...")
scp.put(hub_file, '/Users/m1/vanta_hub.py')

print("[3/3] Gracefully restarting vanta_hub on M1...")
# Only restart vanta_hub.py, do NOT touch orchestrator or game slots!
ssh.exec_command('pkill -f vanta_hub.py')
time.sleep(1)
ssh.exec_command('nohup python3 /Users/m1/vanta_hub.py > /Users/m1/hub.log 2>&1 &')
time.sleep(2)

ssh.close()
print("[DEPLOY] Hub successfully deployed and restarted!")
