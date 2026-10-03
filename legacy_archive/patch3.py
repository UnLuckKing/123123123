import os

with open('app.go', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'go a.gameMatchMonitorLoop(slotID)',
    'go a.gameMatchMonitorLoop(slotID, proxyPort)'
)
code = code.replace(
    'func (a *App) gameMatchMonitorLoop(slotID string) {',
    'func (a *App) gameMatchMonitorLoop(slotID string, proxyPort int) {'
)
code = code.replace(
    'if err := LaunchLeagueGameLocally(statusResp.GameArgs); err != nil {',
    'if err := LaunchLeagueGameLocally(statusResp.GameArgs, proxyPort); err != nil {'
)
with open('app.go', 'w', encoding='utf-8') as f:
    f.write(code)


with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_func = False
for i, line in enumerate(lines):
    if 'func LaunchLeagueGameLocally(args []string' in line:
        lines[i] = line.replace('args []string', 'args []string, proxyPort int')
        in_func = True
    elif in_func and 'func ' in line:
        in_func = False
    
    if in_func:
        if 'undefined: proxyPort' in line:
            pass # ignore
        elif 'cleanArgs = append(cleanArgs, arg)' in line and 'else {' not in line:
            lines[i] = '\t\t} else if strings.HasPrefix(arg, "-RiotClientPort=") {\n\t\t\tcleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))\n\t\t} else {\n\t\t\tcleanArgs = append(cleanArgs, arg)\n'

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.writelines(lines)
