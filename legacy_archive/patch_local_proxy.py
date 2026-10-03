with open("launcher_windows.go", "r", encoding="utf-8") as f:
    code = f.read()

target = """func LaunchLeagueGameLocally(args []string, proxyPort int) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("Oyun dosyasi (League of Legends.exe) bulunamadi")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))"""

replacement = """func LaunchLeagueGameLocally(args []string, proxyPort int) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("Oyun dosyasi (League of Legends.exe) bulunamadi")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Ensure local tunnel to Mac RC API on proxyPort is active
	if proxyPort != 0 {
		startLocalTCPProxy(proxyPort, "51.159.121.126", proxyPort)
	}"""

if target in code:
    code = code.replace(target, replacement)
    with open("launcher_windows.go", "w", encoding="utf-8") as f:
        f.write(code)
    print("PATCHED LaunchLeagueGameLocally WITH startLocalTCPProxy")
else:
    print("TARGET NOT FOUND")
