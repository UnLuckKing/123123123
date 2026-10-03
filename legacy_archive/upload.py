import paramiko
from scp import SCPClient

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
scp = SCPClient(ssh.get_transport())
scp.put('vanta_orchestrator_current.py', '/Users/m1/vanta_orchestrator.py')
ssh.exec_command('pkill -9 -f vanta_orchestrator.py; pkill -9 -f RiotClientServices; pkill -9 -f LeagueClient')
ssh.exec_command('nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orchestrator.log 2>&1 &')
ssh.close()
print("Uploaded and restarted orchestrator.")
