import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = 'find /Users/m1 -name "*.ipsw" -o -name "*.utm" -o -name "*.tart" 2>/dev/null; ls -la ~/.tart /Users/m1/.tart /Users/m1/Virtual* /Users/m1/VM* 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("--- EXISTING IMAGES ---")
print(stdout.read().decode())
print(stderr.read().decode())

# Check curl download speed with a test file
cmd_speed = 'curl -s -w "%{speed_download}\n" -o /dev/null http://speedtest.tele2.net/100MB.zip'
stdin, stdout, stderr = ssh.exec_command(cmd_speed)
print("--- SPEED (bytes/sec) ---")
print(stdout.read().decode())

ssh.close()
