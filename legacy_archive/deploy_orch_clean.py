import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
sftp.put(r"C:\Users\hesap\Desktop\nrx.lol-main\vanta_orchestrator.py", "/Users/m1/vanta_orchestrator.py")
sftp.close()
print("Uploaded vanta_orchestrator.py to M1 successfully")

# Restart orchestrator
cmd = """
echo PNGGJHc5f7f1 | sudo -S pkill -9 -f vanta_orchestrator.py
sleep 1
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/orch_apex.log 2>&1 &
sleep 2
ps aux | grep vanta_orchestrator
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode("utf-8", "ignore"))
print("STDERR:")
print(stderr.read().decode("utf-8", "ignore"))

ssh.close()
