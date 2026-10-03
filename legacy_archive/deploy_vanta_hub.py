import paramiko
import time

print("Connecting to M1 Mac Server 51.159.121.126...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
print("Uploading vanta_hub_upgraded_final.py to /Users/m1/vanta_hub.py...")
sftp.put("vanta_hub_upgraded_final.py", "/Users/m1/vanta_hub.py")
sftp.close()

print("Restarting vanta_hub process on Mac...")
cmd = """
pkill -9 -f vanta_hub.py
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &
sleep 2
ps aux | grep vanta_hub
curl -s http://127.0.0.1:8088/api/ping
echo ""
curl -s http://127.0.0.1:8088/api/admin/resellers | head -c 120
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("DEPLOY OUTPUT:\n", stdout.read().decode("utf-8", "ignore"))
print("STDERR:\n", stderr.read().decode("utf-8", "ignore"))
ssh.close()
print("SERVER DEPLOYMENT COMPLETED!")
