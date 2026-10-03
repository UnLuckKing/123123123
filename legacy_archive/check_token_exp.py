import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Test reading Colerico token expiration
cmd = """
python3 -c '
import base64, json, time
with open("/Users/m1/RiotGamesPrivateSettings.yaml") as f:
    c = f.read()

tokens = [line for line in c.splitlines() if "id_token:" in line]
jwt = tokens[0].split(":", 1)[1].strip().strip("\\\"")
payload = jwt.split(".")[1]
padded = payload + "=" * ((4 - len(payload) % 4) % 4)
data = json.loads(base64.b64decode(padded.encode()).decode())
exp = data.get("exp")
print("Exp timestamp:", exp, "Current time:", time.time(), "Valid:", exp > time.time())
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
