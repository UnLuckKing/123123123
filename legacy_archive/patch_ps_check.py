import re

with open('vanta_orchestrator_current.py', 'r') as f:
    code = f.read()

# Replace the ps checking block in vm_worker
old_check = '''                for line in ps.splitlines():
                    if (f"--riotclient-app-port={slot.rc_port}" in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "grep" not in line
                            and "--app-port=" in line):'''

new_check = '''                for line in ps.splitlines():
                    if ("grep" not in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "--app-port=" in line
                            and (f"--riotclient-app-port={slot.rc_port}" in line or f"_slot{slot.slot_num}.app" in line or f"RiotClientData_slot{slot.slot_num}" in line)):'''

if old_check in code:
    code = code.replace(old_check, new_check)
    print("Replaced check successfully!")
else:
    print("Old check string not found, let's search regex")

with open('vanta_orchestrator_current.py', 'w') as f:
    f.write(code)
