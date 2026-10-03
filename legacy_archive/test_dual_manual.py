import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("1. Preparing slot1 and slot2 app clones...")
ssh.exec_command('rm -rf "/Applications/League of Legends_slot1.app" "/Applications/League of Legends_slot2.app"')
ssh.exec_command('cp -c -R "/Applications/League of Legends.app" "/Applications/League of Legends_slot1.app"')
ssh.exec_command('cp -c -R "/Applications/League of Legends.app" "/Applications/League of Legends_slot2.app"')
time.sleep(3)

print("2. Starting LeagueClient slot1 manually...")
cmd1 = '/Applications/"League of Legends_slot1.app"/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient --no-rads --disable-self-update --region=NA --locale=en_GB > /tmp/lc_man_slot1.log 2>&1 &'
ssh.exec_command(cmd1)
time.sleep(4)

print("3. Starting LeagueClient slot2 manually...")
cmd2 = '/Applications/"League of Legends_slot2.app"/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient --no-rads --disable-self-update --region=NA --locale=en_GB > /tmp/lc_man_slot2.log 2>&1 &'
ssh.exec_command(cmd2)
time.sleep(6)

print("4. Checking if BOTH LeagueClient processes are running:")
stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep LeagueClient | grep -v grep')
print(stdout.read().decode())

print("5. Checking lockfiles in both slots:")
stdin, stdout, stderr = ssh.exec_command('ls -l "/Applications/League of Legends_slot1.app/Contents/LoL/lockfile" "/Applications/League of Legends_slot2.app/Contents/LoL/lockfile"')
print(stdout.read().decode())

print("Cleaning up...")
ssh.exec_command('pkill -9 -f LeagueClient')
ssh.close()
