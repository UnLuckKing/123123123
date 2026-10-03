import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
sftp.put("vanta_orchestrator.py", "/Users/m1/vanta_orchestrator.py")
sftp.close()
print("UPLOADED vanta_orchestrator.py")

# Kill old orchestrator
stdin, stdout, stderr = ssh.exec_command("pkill -9 -f 'vanta_orchestrator.py' || true")
stdout.channel.recv_exit_status()
time.sleep(1)

# Start new orchestrator in background with nohup
cmd = "nohup python3 /Users/m1/vanta_orchestrator.py > /Users/m1/orchestrator.log 2>&1 &"
ssh.exec_command(cmd)
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command("ps aux | grep vanta_orchestrator | grep -v grep; tail -n 25 /Users/m1/orchestrator.log")
print(stdout.read().decode("utf-8", "ignore"))

ssh.close()
