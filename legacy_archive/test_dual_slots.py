import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Starting RCS under slot1...")
ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S pkill -9 -f RiotClientServices')
ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S -u slot1 rm -rf "/Users/slot1/Library/Application Support/Riot Games/Riot Client/Config/lockfile"')
ssh.exec_command('echo PNGGJHc5f7f1 | sudo -S -u slot2 rm -rf "/Users/slot2/Library/Application Support/Riot Games/Riot Client/Config/lockfile"')

cmd1 = 'echo PNGGJHc5f7f1 | sudo -S -u slot1 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients > /tmp/rcs_slot1.log 2>&1 &'
ssh.exec_command(cmd1)

time.sleep(3)

print("Starting RCS under slot2...")
cmd2 = 'echo PNGGJHc5f7f1 | sudo -S -u slot2 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients > /tmp/rcs_slot2.log 2>&1 &'
ssh.exec_command(cmd2)

time.sleep(5)

print("Checking processes under slot1 and slot2:")
stdin, stdout, stderr = ssh.exec_command('ps -axo user,pid,command | grep RiotClientServices | grep -v grep')
print(stdout.read().decode())

print("Lockfile slot1:")
stdin, stdout, stderr = ssh.exec_command('cat "/Users/slot1/Library/Application Support/Riot Games/Riot Client/Config/lockfile" 2>/dev/null')
print(stdout.read().decode())

print("Lockfile slot2:")
stdin, stdout, stderr = ssh.exec_command('cat "/Users/slot2/Library/Application Support/Riot Games/Riot Client/Config/lockfile" 2>/dev/null')
print(stdout.read().decode())

ssh.close()
