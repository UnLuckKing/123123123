import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

cmd = """python3 - << 'EOF'
with open('/Users/m1/vanta_hub.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace total_slots: 5 with 25
content = content.replace('"total_slots": 5,', '"total_slots": 25,')
content = content.replace('/ 5 Slots In-Flight', '/ 25 Slots In-Flight')
content = content.replace('MAX 5 SLOTS', 'MAX 25 SLOTS')

with open('/Users/m1/vanta_hub.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("vanta_hub.py patched on M1 with 25 slots")
EOF
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode("utf-8", "ignore"))
print(stderr.read().decode("utf-8", "ignore"))

# Restart vanta_hub cleanly
stdin, stdout, stderr = ssh.exec_command("pkill -9 -f 'vanta_hub.py' || true")
stdout.channel.recv_exit_status()
ssh.exec_command("nohup python3 /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &")

ssh.close()
print("vanta_hub restarted.")
