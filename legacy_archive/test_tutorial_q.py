import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
stdin, stdout, stderr = ssh.exec_command("""
curl -s -k --user riot:6zMK-re2WRdIzVVl5bZJvw https://127.0.0.1:51293/lol-game-queues/v1/queues | python3 -c '
import sys, json
queues = json.load(sys.stdin)
for q in queues:
    if "Tutorial" in q.get("description", "") or "Intro" in q.get("description", "") or "Practice" in q.get("description", ""):
        print(q["id"], q["name"], q.get("description"))
'
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
