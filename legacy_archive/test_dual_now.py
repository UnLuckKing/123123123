import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

ssh.exec_command('pkill -9 -f LeagueClient; rm -f /tmp/lc_man_slot*.log')
time.sleep(1)

print("1. Starting LeagueClient slot1 manually...")
cmd1 = 'nohup "/Applications/League of Legends_slot1.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient" --no-rads --disable-self-update --region=NA --locale=en_GB > /tmp/lc_man_slot1.log 2>&1 &'
ssh.exec_command(cmd1)
time.sleep(4)

print("2. Starting LeagueClient slot2 manually...")
cmd2 = 'nohup "/Applications/League of Legends_slot2.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient" --no-rads --disable-self-update --region=NA --locale=en_GB > /tmp/lc_man_slot2.log 2>&1 &'
ssh.exec_command(cmd2)
time.sleep(6)

print("3. Checking processes:")
stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep LeagueClient | grep -v grep')
print(stdout.read().decode())

print("4. Log slot 1:")
stdin, stdout, stderr = ssh.exec_command('tail -n 15 /tmp/lc_man_slot1.log')
print(stdout.read().decode())

print("5. Log slot 2:")
stdin, stdout, stderr = ssh.exec_command('tail -n 15 /tmp/lc_man_slot2.log')
print(stdout.read().decode())

ssh.exec_command('pkill -9 -f LeagueClient')
ssh.close()
