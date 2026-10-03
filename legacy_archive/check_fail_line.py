import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'grep -n "Failed to trigger game launch" /Users/m1/orchestrator.log; grep -n "Timeout waiting for LeagueClient" /Users/m1/orchestrator.log'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- FAILURE REASONS ---")
print(stdout.read().decode())

cmd = 'tail -n 60 /Users/m1/orchestrator.log | grep -E "worker|error|fail|Timeout|rcp|HTTP"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- RECENT RELEVANT ---")
print(stdout.read().decode())

ssh.close()
