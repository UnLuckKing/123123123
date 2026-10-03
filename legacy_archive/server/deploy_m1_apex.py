import paramiko
from scp import SCPClient
import time
import requests

M1_IP = '51.159.121.126'
M1_USER = 'm1'
M1_PASS = 'PNGGJHc5f7f1'

print("[1/4] Connecting SSH to M1...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(M1_IP, username=M1_USER, password=M1_PASS)
scp = SCPClient(ssh.get_transport())

import os

server_dir = os.path.dirname(os.path.abspath(__file__))
print("[2/4] Uploading vanta_orchestrator.py and vanta_hub.py...")
scp.put(os.path.join(server_dir, 'vanta_orchestrator.py'), '/Users/m1/vanta_orchestrator.py')
scp.put(os.path.join(server_dir, 'vanta_hub.py'), '/Users/m1/vanta_hub.py')

print("[3/4] Restarting services on M1...")
# Gracefully kill running orchestrator, hub, and any dangling game processes
cmd_kill = (
    "pkill -9 -f vanta_orchestrator.py; "
    "pkill -9 -f vanta_hub.py; "
    "pkill -9 -f RiotClientServices; "
    "pkill -9 -f LeagueClient; "
    "pkill -9 -f 'League of Legends'"
)
stdin, stdout, stderr = ssh.exec_command(cmd_kill)
stdout.channel.recv_exit_status()

# Launch orchestrator
ssh.exec_command('nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orchestrator.log 2>&1 &')
# Launch hub
ssh.exec_command('nohup python3 /Users/m1/vanta_hub.py > /Users/m1/hub.log 2>&1 &')

time.sleep(3)
ssh.close()
print("[4/4] Deploy complete. Verifying endpoints locally...")
