import re

with open('vanta_orchestrator_current.py', 'r') as f:
    content = f.read()

new_worker = """
def vm_worker(slot: SlotState, yaml_data: str):
    try:
        log(f"[worker:slot{slot.slot_num}] Initializing isolated slot environment...")

        clean_slot_processes_isolated(slot)

        cfg_dir = os.path.join(slot.data_dir, "Config")
        data_dir = os.path.join(slot.data_dir, "Data")
        shared_dir = os.path.join(slot.data_dir, "SharedMetadata")
        os.makedirs(cfg_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(shared_dir, "league_of_legends.live"), exist_ok=True)

        app_path = f"/Applications/League of Legends_slot{slot.slot_num}.app"
        subprocess.run(f"rm -rf '{app_path}'", shell=True)
        subprocess.run(f"cp -c -R '/Applications/League of Legends.app' '{app_path}'", shell=True)
        
        meta_yaml = f\"\"\"auto_patching_enabled_by_player: false
dependencies: {{}}
patching_policy: "manual"
patchline_patching_ask_policy: "ask"
product_dependency: "teamfighttactics.live"
product_install_full_path: "{app_path}"
product_install_root: "/Applications"
settings:
    create_shortcut: false
    create_uninstall_key: false
    locale: "en_GB"
should_repair: false
\"\"\"
        with open(os.path.join(shared_dir, "league_of_legends.live", "league_of_legends.live.product_settings.yaml"), "w") as f:
            f.write(meta_yaml)

        lockfile_path = os.path.join(cfg_dir, "lockfile")
        if os.path.exists(lockfile_path):
            try: os.remove(lockfile_path)
            except: pass

        settings_yaml = os.path.join(cfg_dir, "RiotClientSettings.yaml")
        if os.path.exists(TEMPLATE_CONFIG) and not os.path.exists(settings_yaml):
            try:
                import shutil
                shutil.copyfile(TEMPLATE_CONFIG, settings_yaml)
            except: pass

        private_yaml = os.path.join(data_dir, "RiotGamesPrivateSettings.yaml")
        with open(private_yaml, "w") as f:
            f.write(yaml_data)

        cmd = [
            "/Applications/Riot Client.app/Contents/MacOS/RiotClientServices",
            "--allow-multiple-clients",
            f"--user-data-root={slot.data_dir}",
            f"--data-root={shared_dir}"
        ]
        
        env = os.environ.copy()
        env["VANTA_SLOT_NUM"] = str(slot.slot_num)
        proc = subprocess.Popen(cmd, env=env)
        slot.rc_proc = proc
        slot.rc_pid = proc.pid
        log(f"[worker:slot{slot.slot_num}] RiotClientServices spawned (PID {proc.pid}) with root {slot.data_dir}")

        rc_port, rc_token = None, None
        for _ in range(45):
            rc_port, rc_token = read_lockfile(lockfile_path)
            if rc_port and rc_token: break
            time.sleep(1)

        if not rc_port:
            _fail(slot, f"RC lockfile timeout in {slot.data_dir}")
            return

        slot.rc_port  = rc_port
        slot.rc_token = rc_token
        log(f"[worker:slot{slot.slot_num}] RC online at port {rc_port}")

        srv = start_tcp_proxy(slot.proxy_port, rc_port)
        slot._proxy_srv = srv

        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        auth_hdr = base64.b64encode(f"riot:{rc_token}".encode()).decode()

        session_ready = False
        for i in range(25):
            try:
                session_req = urllib.request.Request(
                    f"https://127.0.0.1:{rc_port}/rso-auth/v1/session",
                    headers={"Authorization": f"Basic {auth_hdr}"}
                )
                with urllib.request.urlopen(session_req, context=ctx, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("type") == "authenticated":
                        session_ready = True
                        break
            except: pass
            time.sleep(1)

        launch_url = f"https://127.0.0.1:{rc_port}/product-launcher/v1/products/league_of_legends/patchlines/live"
        req = urllib.request.Request(
            launch_url, data=b"{}",
            headers={"Authorization": f"Basic {auth_hdr}", "Content-Type": "application/json"}
        )

        launch_ok = False
        for attempt in range(20):
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                    launch_ok = True
                    break
            except: time.sleep(2)

        if not launch_ok:
            _fail(slot, "Failed to trigger game launch via RC API")
            return

        for _ in range(60):
            try:
                ps = subprocess.check_output(["ps", "-axo", "pid,args"], timeout=5).decode(errors="replace")
                for line in ps.splitlines():
                    if (f"--riotclient-app-port={slot.rc_port}" in line
                            and ("LeagueClientUx" in line or "LeagueClient" in line)
                            and "grep" not in line
                            and "--app-port=" in line):
                        raw_parts = line.strip().split()
                        pid = int(raw_parts[0])
                        import shlex
                        args = shlex.split(line)[1:]
                        if args and ("LeagueClient" in args[0] or "LeagueClientUx" in args[0]):
                            args = args[1:]
                        app_port = None
                        for a in args:
                            if a.startswith("--app-port="):
                                try: app_port = int(a.split("=")[1])
                                except: pass
                                break
                        if app_port:
                            slot.app_port = app_port
                            slot.lc_pid = pid
                            slot._lcu_srv = start_tcp_proxy(slot.lcu_port, app_port)
                        with slots_lock:
                            slot.status = "game_ready"
                            slot.args   = args
                        threading.Thread(target=capture_game_engine_loop, args=(slot,), daemon=True).start()
                        return
            except: pass
            time.sleep(1.5)

        _fail(slot, "Timeout waiting for LeagueClient")
    except Exception as e:
        _fail(slot, f"exception: {e}")
"""

content = re.sub(r'def vm_worker\(slot: SlotState, yaml_data: str\):.*?(?=\ndef _fail)', new_worker, content, flags=re.DOTALL)

with open('vanta_orchestrator_current.py', 'w') as f:
    f.write(content)
