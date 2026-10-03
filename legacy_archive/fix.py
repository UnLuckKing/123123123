import os

with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'strings.ReplaceAll(installDir,' in line:
        lines[i] = '\tinstallDirFwd := strings.ReplaceAll(installDir, "\\\\", "/")\n'
    if 'fmt.Printf("[VANTA] Launching Game:' in line:
        lines[i] = '\tfmt.Printf("[VANTA] Launching Game: %s %v\\n", gameExe, cleanArgs)\n'

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.writelines(lines)
