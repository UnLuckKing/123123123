import paramiko
import time
import base64
import json
import urllib.request
import ssl
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Starting test1 with HOME override...")
ssh.exec_command('rm -rf /tmp/vanta_test1 /tmp/vanta_rc && mkdir -p /tmp/vanta_test1 /tmp/vanta_rc')

# Also write dummy RiotGamesPrivateSettings.yaml
ssh.exec_command('mkdir -p /tmp/vanta_rc/Data && touch /tmp/vanta_rc/Data/RiotGamesPrivateSettings.yaml')
ssh.exec_command('HOME=/tmp/vanta_test1 /Applications/"Riot Client.app"/Contents/MacOS/RiotClientServices --allow-multiple-clients --user-data-root=/tmp/vanta_rc > /dev/null 2>&1 &')

time.sleep(5)

# Get lockfile
stdin, stdout, stderr = ssh.exec_command('cat /tmp/vanta_rc/Config/lockfile')
lock_data = stdout.read().decode().strip()
print(f"Lockfile: {lock_data}")

if lock_data:
    parts = lock_data.split(":")
    if len(parts) >= 4:
        rc_port = parts[2]
        rc_token = parts[3]
        
        # Trigger launch via SSH curl
        curl_cmd = f"curl -k -u riot:{rc_token} -X POST https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live -d '{{}}' -H 'Content-Type: application/json'"
        ssh.exec_command(curl_cmd)
        
        print("Waiting 15 seconds for LeagueClient to spawn and write files...")
        time.sleep(15)

print("Listing /tmp/vanta_test1")
stdin, stdout, stderr = ssh.exec_command('find /tmp/vanta_test1')
print(stdout.read().decode())

print("Killing test1")
ssh.exec_command('pkill -9 -f "LeagueClient"')
ssh.exec_command('pkill -9 -f "RiotClientServices"')
ssh.close()
