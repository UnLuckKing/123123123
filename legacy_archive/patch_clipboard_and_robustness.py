import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.159.121.126", username="m1", password="PNGGJHc5f7f1")

sftp = ssh.open_sftp()
with sftp.open("/Users/m1/vanta_hub.py", "r") as f:
    hub_code = f.read().decode("utf-8")

# 1. Update copyToClipboard to work over HTTP and insecure origins
old_copy = """        function copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            showToast('Key copied to clipboard');
        }"""

new_copy = """        function copyToClipboard(text) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('Key copied: ' + text);
                }).catch(() => {
                    fallbackCopy(text);
                });
            } else {
                fallbackCopy(text);
            }
        }

        function fallbackCopy(text) {
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            textArea.style.left = "-999999px";
            textArea.style.top = "-999999px";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    showToast('Key copied: ' + text);
                } else {
                    prompt('Copy license key:', text);
                }
            } catch (err) {
                prompt('Copy license key:', text);
            }
            document.body.removeChild(textArea);
        }"""

if old_copy in hub_code:
    hub_code = hub_code.replace(old_copy, new_copy, 1)
    print("Replaced copyToClipboard successfully")
else:
    print("old_copy string not found in hub_code, attempting regex or direct replacement")

# 2. Add automatic DB column migrations in init_db
old_init_db = """    conn.commit()
    conn.close()

def log_event"""

new_init_db = """    # Automatic column migrations
    for col, col_type in [("last_ip", "TEXT"), ("last_seen", "INTEGER")]:
        try:
            c.execute(f"ALTER TABLE licenses ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    conn.commit()
    conn.close()

def log_event"""

if old_init_db in hub_code:
    hub_code = hub_code.replace(old_init_db, new_init_db, 1)
    print("Added DB column migration to init_db")

# 3. Add top-level try/except in do_POST so it never crashes with EOF
old_do_post = """    def do_POST(self):
        parsed = urlparse(self.path)"""

new_do_post = """    def do_POST(self):
        try:
            self._handle_POST()
        except Exception as e:
            print("[HUB POST ERROR]", e)
            self._send_json(500, {"success": False, "error": str(e)})

    def _handle_POST(self):
        parsed = urlparse(self.path)"""

if old_do_post in hub_code:
    hub_code = hub_code.replace(old_do_post, new_do_post, 1)
    print("Wrapped do_POST in exception handler")

# Write back to Mac
with sftp.open("/Users/m1/vanta_hub.py", "w") as f:
    f.write(hub_code)
sftp.close()

# Restart vanta_hub.py
stdin, stdout, stderr = ssh.exec_command("pkill -9 -f vanta_hub.py || true; nohup python3 /Users/m1/vanta_hub.py > /Users/m1/vanta_hub.log 2>&1 &")
stdout.channel.recv_exit_status()

# Verify
stdin, stdout, stderr = ssh.exec_command("sleep 1; ps aux | grep vanta_hub; curl -s http://127.0.0.1:8088/api/system/health")
print("Verification:", stdout.read().decode())
ssh.close()
