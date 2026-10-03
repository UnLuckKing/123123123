import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_orchestrator.py", "r") as f:
    code = f.read().decode("utf-8")

old_proxy = """def start_udp_proxy(listen_port: int, target_ip: str, target_port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", listen_port))
    client_addr = None
    target_addr = (target_ip, target_port)
    log(f"[proxy] UDP 0.0.0.0:{listen_port} -> {target_ip}:{target_port}")

    def loop():
        nonlocal client_addr
        while True:
            try:
                data, addr = sock.recvfrom(65536)
                if addr == target_addr:
                    if client_addr:
                        sock.sendto(data, client_addr)
                else:
                    client_addr = addr
                    sock.sendto(data, target_addr)
            except Exception as e:
                log(f"[udp_proxy] error: {e}")
                break

    threading.Thread(target=loop, daemon=True).start()
    return sock"""

new_proxy = """def start_udp_proxy(listen_port: int, target_ip: str, target_port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", listen_port))
    client_addr = None
    target_addr = (target_ip, target_port)
    log(f"[proxy] UDP 0.0.0.0:{listen_port} -> {target_ip}:{target_port}")

    def loop():
        nonlocal client_addr
        pkt_in = 0
        pkt_out = 0
        while True:
            try:
                data, addr = sock.recvfrom(65536)
                # If packet comes from Riot server (by IP, regardless of dynamic port)
                if addr[0] == target_ip:
                    if client_addr:
                        sock.sendto(data, client_addr)
                        pkt_out += 1
                        if pkt_out % 100 == 1:
                            log(f"[udp_proxy] Server -> Client ({len(data)}B, total {pkt_out})")
                else:
                    # Packet comes from Windows client
                    client_addr = addr
                    sock.sendto(data, target_addr)
                    pkt_in += 1
                    if pkt_in % 100 == 1:
                        log(f"[udp_proxy] Client -> Server ({len(data)}B from {addr}, total {pkt_in})")
            except Exception as e:
                log(f"[udp_proxy] error: {e}")
                break

    threading.Thread(target=loop, daemon=True).start()
    return sock"""

if old_proxy in code:
    code = code.replace(old_proxy, new_proxy)
    with sftp.open("/Users/m1/vanta_orchestrator.py", "w") as f:
        f.write(code)
    print("UPGRADED UDP PROXY TO ROBUST BIDIRECTIONAL ROUTING")
else:
    print("OLD PROXY BLOCK NOT FOUND")
sftp.close()

stdin, stdout, stderr = ssh.exec_command("""
pkill -9 -f vanta_orchestrator.py
nohup /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /Users/m1/vanta_orchestrator.py > /Users/m1/vanta_orchestrator.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:9000/api/health
""")
print(stdout.read().decode("utf-8", "ignore"))
ssh.close()
