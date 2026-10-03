import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

# Test launching product-launcher directly for slot2 with curl to see exact response
# First get slot2 RC port and token
stdin, stdout, stderr = ssh.exec_command('cat "/Users/m1/Library/Application Support/RiotClientData_slot2/Config/lockfile"')
lock = stdout.read().decode().strip()
print("Slot2 lock:", lock)

cmd = 'grep -A 10 "worker:slot2" /Users/m1/orchestrator.log | tail -n 25'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- DETAILED SLOT2 LOG ---")
print(stdout.read().decode())

ssh.close()
