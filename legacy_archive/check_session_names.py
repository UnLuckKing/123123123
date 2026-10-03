import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
files = [
    "/Users/m1/RiotGamesPrivateSettings.yaml",
    "/Users/m1/Library/Application Support/RiotClientData_slot2/Data/RiotGamesPrivateSettings.yaml",
    "/Users/m1/Library/Application Support/RiotClientData/Data/RiotGamesPrivateSettings.yaml",
    "/Users/m1/Library/Application Support/RiotClientData_slot1/Data/RiotGamesPrivateSettings.yaml",
    "/Users/m1/VantaSlots/slot3/Data/RiotGamesPrivateSettings.yaml",
    "/Users/m1/vanta_data/Data/RiotGamesPrivateSettings.yaml"
]

import base64, json

for f in files:
    try:
        with open(f, "r") as fp:
            c = fp.read()
        tokens = [line for line in c.splitlines() if "id_token:" in line]
        if tokens:
            jwt = tokens[0].split(":", 1)[1].strip().strip("\\\"")
            payload = jwt.split(".")[1]
            padded = payload + "=" * ((4 - len(payload) % 4) % 4)
            data = json.loads(base64.b64decode(padded.encode()).decode())
            sub = data.get("sub")
            acct = data.get("acct")
            print(f + " : sub=" + str(sub) + " acct=" + str(acct))
        else:
            print(f + " : no id_token")
    except Exception as e:
        print(f + " : error=" + str(e))
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)
ssh.close()
