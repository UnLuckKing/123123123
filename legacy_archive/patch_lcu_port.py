with open("app.go", "r", encoding="utf-8") as f:
    code = f.read()

# Update call in app.go to pass lcuPort as well
code = code.replace(
    "go a.gameMatchMonitorLoop(slotID, proxyPort)",
    "go a.gameMatchMonitorLoop(slotID, proxyPort, lcuPort)"
)
code = code.replace(
    "func (a *App) gameMatchMonitorLoop(slotID string, proxyPort int) {",
    "func (a *App) gameMatchMonitorLoop(slotID string, proxyPort int, lcuPort int) {"
)
code = code.replace(
    "if err := LaunchLeagueGameLocally(statusResp.GameArgs, proxyPort); err != nil {",
    "if err := LaunchLeagueGameLocally(statusResp.GameArgs, lcuPort); err != nil {"
)

with open("app.go", "w", encoding="utf-8") as f:
    f.write(code)

with open("launcher_windows.go", "r", encoding="utf-8") as f:
    code = f.read()

old_func_hdr = """func LaunchLeagueGameLocally(args []string, proxyPort int) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("Oyun dosyasi (League of Legends.exe) bulunamadi")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Ensure local tunnel to Mac RC API on proxyPort is active
	if proxyPort != 0 {
		startLocalTCPProxy(proxyPort, "51.159.121.126", proxyPort)
	}"""

new_func_hdr = """func LaunchLeagueGameLocally(args []string, lcuPort int) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("Oyun dosyasi (League of Legends.exe) bulunamadi")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Ensure local tunnel to Mac LCU API on lcuPort is active
	if lcuPort != 0 {
		startLocalTCPProxy(lcuPort, "51.159.121.126", lcuPort)
	}"""

code = code.replace(old_func_hdr, new_func_hdr)
code = code.replace(
    'cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))',
    'cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", lcuPort))'
)

with open("launcher_windows.go", "w", encoding="utf-8") as f:
    f.write(code)

print("PATCHED LCU PORT TO 8100 FOR 3D GAME ENGINE")
