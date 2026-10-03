with open("vanta_hub_backup.py", "r", encoding="utf-8") as f:
    code = f.read()

# Check what orchestrator URL it connects to for slots:
# Line 431: "http://127.0.0.1:9191/status"
# But our orchestrator is on port 9000! Not 9191!
print("Found 9191 in code:", "9191" in code)
