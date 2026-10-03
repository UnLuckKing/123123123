import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    code = f.read().decode("utf-8")

old_code = """                    with slots_lock:
                        slot.game_args = game_args
                    log(f"[game_monitor] Captured 3D Game Engine (PID {pid}): Redirecting {target_ip}:{target_port} via relay on port {slot.udp_proxy_port}")
                    return"""

new_code = """                    with slots_lock:
                        slot.game_args = game_args
                    log(f"[game_monitor] Captured 3D Game Engine (PID {pid}): Redirecting {target_ip}:{target_port} via relay on port {slot.udp_proxy_port}")
                    try:
                        os.kill(pid, 9)
                        subprocess.run(["pkill", "-9", "-f", "LeagueofLegends"], capture_output=True)
                        log(f"[game_monitor] Terminated Mac 3D engine PID {pid} so local Windows client has exclusive session")
                    except Exception as err:
                        log(f"[game_monitor] Error terminating Mac game: {err}")
                    return"""

if old_code in code:
    code = code.replace(old_code, new_code)
    with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
        f.write(code)
    print("PATCHED capture_game_engine_loop TO KILL MAC 3D ENGINE")
else:
    print("OLD CODE NOT FOUND")
sftp.close()

# Restart orchestrator
stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_orchestrator.py
pkill -9 -f LeagueofLegends
pkill -9 -f LeagueCrashHandler
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:9000/api/health
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
