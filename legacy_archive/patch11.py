import os

with open('app.go', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'os.WriteFile("C:\\\\Users\\\\hesap\\\\Desktop\\\\vanta_debug.txt", []byte(line+"\\n"), 0644)\n\tf, _ := os.OpenFile("C:\\\\Users\\\\hesap\\\\Desktop\\\\vanta_debug.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)',
    '\tf, _ := os.OpenFile("C:\\\\Users\\\\hesap\\\\Desktop\\\\vanta_debug.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)'
)

with open('app.go', 'w', encoding='utf-8') as f:
    f.write(code)
