import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1', timeout=5)

log_path = "/Applications/League of Legends_slot1.app/Contents/LoL/Logs/LeagueClient Logs/2026-09-29T23-45-06_39640_LeagueClient.log"
cmd = f"tail -n 60 '{log_path}'"
_, out, _ = s.exec_command(cmd)
print("=== LEAGUECLIENT.LOG TAIL ===")
print(out.read().decode())

cmd2 = f"grep -i -E 'gameflow|endofgame|rewards|phase|terminated|quit' '{log_path}' | tail -n 30"
_, out2, _ = s.exec_command(cmd2)
print("=== GAMEFLOW & PHASE EVENTS ===")
print(out2.read().decode())

s.close()
