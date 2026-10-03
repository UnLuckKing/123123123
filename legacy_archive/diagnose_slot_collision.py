import paramiko
import time
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

print("1. Cleaning up any running processes...")
ssh.exec_command('pkill -9 -f "LeagueClient"; pkill -9 -f "RiotClientServices"; pkill -9 -f "vanta_orchestrator"')
time.sleep(2)

print("2. Starting orchestrator in background...")
ssh.exec_command('nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /tmp/diag_orch.log 2>&1 &')
time.sleep(2)

print("3. Requesting Slot 1...")
yaml_file = '/Users/m1/Library/Application Support/RiotClientData_slot1/Data/RiotGamesPrivateSettings.yaml'
cmd_req1 = f"curl -s -X POST http://127.0.0.1:9000/api/request_slot -H 'Content-Type: text/plain' --data-binary @'{yaml_file}'"
stdin, stdout, stderr = ssh.exec_command(cmd_req1)
res1_str = stdout.read().decode().strip()
print("Slot 1 Response:", res1_str)
try:
    res1 = json.loads(res1_str)
    sid1 = res1.get('slot_id')
except Exception as e:
    sid1 = None
    print("Error parsing res1:", e)

if sid1:
    print("Polling Slot 1 until game_ready...")
    for i in range(30):
        time.sleep(2)
        _, o, _ = ssh.exec_command(f"curl -s http://127.0.0.1:9000/api/poll_slot?slot_id={sid1}")
        status = o.read().decode().strip()
        print(f"[{i*2}s] Slot 1:", status[:100])
        if "game_ready" in status:
            print(">>> SLOT 1 IS GAME_READY! <<<")
            break

print("\n4. Checking current running processes for Slot 1:")
stdin, stdout, stderr = ssh.exec_command('ps -axo pid,command | grep -E "RiotClient|LeagueClient" | grep -v grep')
print(stdout.read().decode())

print("\n5. Checking lockfiles on system:")
stdin, stdout, stderr = ssh.exec_command('find /Users/m1 -name "*lockfile*" 2>/dev/null; find /Applications/League* -name "*lockfile*" 2>/dev/null')
print(stdout.read().decode())

print("\n6. Requesting Slot 2 while Slot 1 is ACTIVE...")
stdin, stdout, stderr = ssh.exec_command(cmd_req1)
res2_str = stdout.read().decode().strip()
print("Slot 2 Response:", res2_str)
try:
    res2 = json.loads(res2_str)
    sid2 = res2.get('slot_id')
except Exception as e:
    sid2 = None
    print("Error parsing res2:", e)

if sid2:
    print("Polling Slot 2 and checking processes...")
    for i in range(15):
        time.sleep(2)
        _, o, _ = ssh.exec_command(f"curl -s http://127.0.0.1:9000/api/poll_slot?slot_id={sid2}")
        status = o.read().decode().strip()
        print(f"[{i*2}s] Slot 2:", status[:100])
        if "FAILED" in status or "game_ready" in status:
            break
        # Print ps output to see what processes exist for slot 2
        _, o_ps, _ = ssh.exec_command('ps -axo pid,command | grep -E "slot2|RiotClient|LeagueClient" | grep -v grep')
        print(f"--- PS at {i*2}s ---:\n", o_ps.read().decode())

print("\n7. Diagnostic Orchestrator Log:")
stdin, stdout, stderr = ssh.exec_command('tail -n 40 /tmp/diag_orch.log')
print(stdout.read().decode())

ssh.close()
