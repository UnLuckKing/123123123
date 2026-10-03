import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'vanta_orchestrator|vanta_hub' | grep -v grep")
print("=== PROCESSES & CPU ===")
print(stdout.read().decode("utf-8", "ignore"))

stdin, stdout, stderr = ssh.exec_command("tail -n 15 /Users/m1/orchestrator.log")
print("=== ORCHESTRATOR LOG ===")
print(stdout.read().decode("utf-8", "ignore"))

ssh.close()
