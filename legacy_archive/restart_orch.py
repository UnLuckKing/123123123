import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
# Kill old vanta_orchestrator.py and restart it clean
stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_orchestrator.py
pkill -9 -f League
pkill -9 -f "Riot Client"
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &
sleep 2
ps aux | grep vanta_orchestrator
curl -s http://127.0.0.1:9000/api/health
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
