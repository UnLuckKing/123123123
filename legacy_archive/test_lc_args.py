import paramiko
import base64
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

stdin, stdout, stderr = ssh.exec_command("ps -axo args | grep 'LeagueClient ' | grep riotgamesapi-settings")
ps_out = stdout.read().decode().strip()
for line in ps_out.splitlines():
    if '--riotgamesapi-settings=' in line:
        for arg in line.split():
            if arg.startswith('--riotgamesapi-settings='):
                b64 = arg.split('=', 1)[1]
                print(f"Original B64: {b64[:30]}...")
                try:
                    js = json.loads(base64.b64decode(b64).decode())
                    print(json.dumps(js, indent=2))
                except Exception as e:
                    print("Err", e)
ssh.close()
