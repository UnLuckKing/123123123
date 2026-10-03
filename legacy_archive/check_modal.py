with open("current_server_vanta_hub.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
print("Delete endpoints:", re.findall(r'elif path == ["\'][^"\']*delete[^"\']*["\']:', text))
