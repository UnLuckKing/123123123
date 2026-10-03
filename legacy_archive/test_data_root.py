import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Preparing isolated shared dir...")
ssh.exec_command('rm -rf /tmp/Shared_slot1 && mkdir -p /tmp/Shared_slot1/Metadata')
# Copy league_of_legends.live to isolated shared dir
ssh.exec_command('cp -R "/Users/Shared/Riot Games/Metadata/league_of_legends.live" "/tmp/Shared_slot1/Metadata/"')
# Modify the product_install_full_path inside the copied yaml
sed_cmd = "sed -i '' 's|/Applications/League of Legends.app|/Applications/League of Legends_slot1.app|g' /tmp/Shared_slot1/Metadata/league_of_legends.live/league_of_legends.live.product_settings.yaml"
ssh.exec_command(sed_cmd)

print("Check yaml after modify:")
stdin, stdout, stderr = ssh.exec_command('grep product_install_full_path "/tmp/Shared_slot1/Metadata/league_of_legends.live/league_of_legends.live.product_settings.yaml"')
print(stdout.read().decode())

# Test RCS with --data-root
print("Running RCS with --data-root")
ssh.exec_command('pkill -9 -f "RiotClientServices"')
ssh.exec_command('HOME=/tmp/User_slot1 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients --user-data-root=/tmp/User_slot1 --data-root=/tmp/Shared_slot1 > /tmp/rcs.log 2>&1 &')

ssh.close()
print("Done")
