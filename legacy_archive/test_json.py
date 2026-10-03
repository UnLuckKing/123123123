import paramiko
import time
import json
import urllib.request
import ssl
import base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("Reading lockfile")
stdin, stdout, stderr = ssh.exec_command('cat /tmp/User_slot1/Config/lockfile')
lock = stdout.read().decode().strip()
if lock:
    parts = lock.split(":")
    if len(parts) >= 4:
        rc_port = parts[2]
        rc_token = parts[3]
        print(f"Triggering product-launcher API on port {rc_port}")
        curl_cmd = f"curl -k -u riot:{rc_token} -X POST https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live -d '{{}}' -H 'Content-Type: application/json'"
        ssh.exec_command(curl_cmd)
        time.sleep(15)
        
        print("Checking LC args:")
        stdin, stdout, stderr = ssh.exec_command("ps -axo pid,args | grep -i 'LeagueClient ' | grep -v grep")
        out = stdout.read().decode().strip()
        print("PS output:", out)
        for line in out.splitlines():
            if '--riotgamesapi-settings=' in line:
                for arg in line.split():
                    if arg.startswith('--riotgamesapi-settings='):
                        b64 = arg.split('=', 1)[1]
                        try:
                            js = json.loads(base64.b64decode(b64).decode())
                            print(json.dumps(js, indent=2))
                        except: pass

ssh.close()
