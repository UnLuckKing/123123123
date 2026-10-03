import os
with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = """func LaunchLeagueGameLocally(args []string, proxyPort int) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("Oyun dosyasi (League of Legends.exe) bulunamadi")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))
	installDirFwd := strings.ReplaceAll(installDir, "\\\\", "/")

	var cleanArgs []string
	for i, arg := range args {
		if strings.HasPrefix(arg, "-GameBaseDir=") {
			cleanArgs = append(cleanArgs, "-GameBaseDir="+installDirFwd)
		} else if strings.HasPrefix(arg, "-RiotClientPort=") {
			cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))
		} else if strings.HasPrefix(arg, "-UseMetal=") {
			continue
		} else if strings.HasPrefix(arg, "-AppLogFilePath=") {
			continue
		} else if strings.HasPrefix(arg, "-OutputBaseDir=") {
			continue
		} else if strings.HasPrefix(arg, "-InstallDirectory=") {
			continue
		} else if i >= 4 && !strings.HasPrefix(arg, "-") && !strings.Contains(arg, "=") {
			continue
		} else {
			cleanArgs = append(cleanArgs, arg)
		}
	}

	cmd := exec.Command(gameExe, cleanArgs...)
	cmd.Dir = filepath.Dir(gameExe)

	var filteredEnv []string
	for _, env := range os.Environ() {
		upper := strings.ToUpper(env)
		if strings.HasPrefix(upper, "USERDOMAIN=") ||
			strings.HasPrefix(upper, "LOGONSERVER=") ||
			strings.HasPrefix(upper, "COR_ENABLE_PROFILING=") {
			continue
		}
		filteredEnv = append(filteredEnv, env)
	}
	cmd.Env = filteredEnv

	f, _ := os.OpenFile("C:\\\\Users\\\\hesap\\\\Desktop\\\\vanta_debug.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(fmt.Sprintf("[VANTA] Launching Game: %s %v\\n", gameExe, cleanArgs))
		f.Close()
	}

	return cmd.Start()
}

func launchLeague() error {
"""

start_idx = -1
for i, line in enumerate(lines):
    if line.startswith('func LaunchLeagueGameLocally'):
        start_idx = i
        break

end_idx = -1
for i in range(start_idx + 1, len(lines)):
    if lines[i].startswith('func launchLeague() error {'):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    final = "".join(lines[:start_idx]) + new_func + "".join(lines[end_idx+1:])
    with open('launcher_windows.go', 'w', encoding='utf-8') as f:
        f.write(final)
