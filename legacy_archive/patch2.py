import os
import re

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
    code = f.read()

code = code.replace(
    'func LaunchLeagueGameLocally(args []string) error {',
    'func LaunchLeagueGameLocally(args []string, proxyPort int) error {'
)
code = code.replace(
    'cleanArgs = append(cleanArgs, arg)',
    'if strings.HasPrefix(arg, "-RiotClientPort=") {\n\t\t\tcleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))\n\t\t} else {\n\t\t\tcleanArgs = append(cleanArgs, arg)\n\t\t}'
)

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.write(code)
