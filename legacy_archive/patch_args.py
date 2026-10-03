import os
import re

with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace writeLog with file append logic
replacement = """	f, _ := os.OpenFile("C:\\\\Users\\\\hesap\\\\Desktop\\\\vanta_debug.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(fmt.Sprintf("[VANTA] Launching Game: %s %v\\n", gameExe, cleanArgs))
		f.Close()
	}"""

code = code.replace('writeLog("[VANTA] Launching Game: %s %v", gameExe, cleanArgs)', replacement)

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.write(code)
