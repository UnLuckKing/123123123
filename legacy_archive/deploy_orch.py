import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("1. Uploading updated vanta_orchestrator.py to M1...")
sftp = ssh.open_sftp()
sftp.put(r'C:\Users\hesap\Desktop\nrx.lol-main\vanta_orchestrator.py', '/Users/m1/vanta_orchestrator.py')
sftp.close()
print("Upload complete!")

print("2. Killing any lingering processes on M1...")
ssh.exec_command('pkill -9 -f "vanta_orchestrator"; pkill -9 -f "LeagueClient"; pkill -9 -f "RiotClientServices"')
ssh.exec_command('lsof -ti :9000 | xargs kill -9')
time.sleep(2)

print("3. Starting updated vanta_orchestrator.py...")
cmd = 'nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/orchestrator.log 2>&1 &'
ssh.exec_command(cmd)
time.sleep(2)

print("4. Verifying process status...")
stdin, stdout, stderr = ssh.exec_command('ps -ef | grep vanta_orchestrator | grep -v grep')
print(stdout.read().decode())

print("5. Verifying server banner...")
stdin, stdout, stderr = ssh.exec_command('tail -n 10 /Users/m1/orchestrator.log')
print(stdout.read().decode())

ssh.close()
print("Done!")
