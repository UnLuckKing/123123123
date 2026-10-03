import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
sftp = ssh.open_sftp()

print("Uploading updated vanta_orchestrator.py...")
sftp.put('vanta_orchestrator_current.py', '/Users/m1/vanta_orchestrator.py')
sftp.close()

print("Restarting orchestrator...")
ssh.exec_command("pkill -9 -f 'python3 /Users/m1/vanta_orchestrator.py'")
time.sleep(1)
ssh.exec_command("nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orch.log 2>&1 &")

ssh.close()
print("Done")
