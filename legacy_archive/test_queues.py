import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")
stdin, stdout, stderr = ssh.exec_command("""
curl -s -k --user riot:6zMK-re2WRdIzVVl5bZJvw https://127.0.0.1:51293/lol-game-queues/v1/queues | python3 -m json.tool | head -n 40
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
