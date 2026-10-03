import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

stdin, stdout, stderr = client.exec_command('''grep -n -C 20 "0b7efd03" /Users/m1/orchestrator.log''')
print("GREP SLOT 0b7efd03:\n" + stdout.read().decode('utf-8', errors='replace'))

client.close()
