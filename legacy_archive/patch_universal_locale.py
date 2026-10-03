with open("launcher_windows.go", "r", encoding="utf-8") as f:
    code = f.read()

target = """	// Detect local installed language/wad file
	detectedLocale := "tr_TR"
	locDir := filepath.Join(filepath.Dir(gameExe), "DATA", "FINAL", "Localized")
	if entries, err := os.ReadDir(locDir); err == nil {
		for _, e := range entries {
			if strings.HasPrefix(e.Name(), "Global.") && strings.HasSuffix(e.Name(), ".wad.client") {
				parts := strings.Split(e.Name(), ".")
				if len(parts) >= 3 {
					detectedLocale = parts[1]
					break
				}
			}
		}
	}"""

replacement = """	// Universal Multi-Language Fallback Engine
	// Autodetects user's installed League language across all global regions:
	// en_US, en_GB, tr_TR, de_DE, fr_FR, es_ES, es_MX, pt_BR, it_IT, ru_RU, pl_PL,
	// ja_JP, ko_KR, zh_CN, zh_TW, vi_VN, th_TH, ar_AE, etc.
	detectedLocale := "en_US"
	locDir := filepath.Join(filepath.Dir(gameExe), "DATA", "FINAL", "Localized")
	var primaryWadPath string

	if entries, err := os.ReadDir(locDir); err == nil {
		for _, e := range entries {
			if strings.HasPrefix(e.Name(), "Global.") && strings.HasSuffix(e.Name(), ".wad.client") {
				parts := strings.Split(e.Name(), ".")
				if len(parts) >= 3 {
					detectedLocale = parts[1]
					primaryWadPath = filepath.Join(locDir, e.Name())
					break
				}
			}
		}

		// Safeguard: If user's PC is missing any requested locale wad,
		// automatically clone/link the primary wad so the game NEVER crashes for any customer
		if primaryWadPath != "" {
			commonLocales := []string{
				"en_US", "en_GB", "tr_TR", "de_DE", "fr_FR", "es_ES", "es_MX", 
				"pt_BR", "it_IT", "ru_RU", "pl_PL", "ja_JP", "ko_KR", "zh_CN", 
				"zh_TW", "vi_VN", "th_TH", "ar_AE",
			}
			for _, loc := range commonLocales {
				targetWad := filepath.Join(locDir, fmt.Sprintf("Global.%s.wad.client", loc))
				if _, statErr := os.Stat(targetWad); os.IsNotExist(statErr) {
					_ = os.Link(primaryWadPath, targetWad)
				}
			}
		}
	}"""

if target in code:
    code = code.replace(target, replacement)
    with open("launcher_windows.go", "w", encoding="utf-8") as f:
        f.write(code)
    print("EMBEDDED UNIVERSAL MULTI-LANGUAGE ENGINE IN LAUNCHER")
else:
    print("TARGET NOT FOUND")
