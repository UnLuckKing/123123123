import os

with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if '", gameExe, cleanArgs)' in line and 'fmt.Printf' not in line:
        continue
    new_lines.append(line)

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
