import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

print("Connected to M1. Checking and creating slots 1 to 25...")

script = """
for i in $(seq 1 25); do
    mkdir -p "/Users/m1/VantaSlots/slot$i"
    APP="/Applications/League of Legends_slot$i.app"
    if [ ! -d "$APP" ]; then
        echo "Cloning slot $i with APFS CoW..."
        cp -c -R "/Applications/League of Legends.app" "$APP"
    else
        echo "Slot $i app exists."
    fi
done
df -h /
"""

stdin, stdout, stderr = ssh.exec_command(script)
for line in stdout:
    print(line.strip())

err = stderr.read().decode("utf-8", "ignore")
if err:
    print("ERR:", err)

ssh.close()
print("Slot provisioning completed.")
