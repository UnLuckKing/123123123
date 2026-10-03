import os, shutil

# Create backup / copy for en_GB wad file
wad_dir = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Localized"
tr_wad = os.path.join(wad_dir, "Global.tr_TR.wad.client")
en_wad = os.path.join(wad_dir, "Global.en_GB.wad.client")

if os.path.exists(tr_wad) and not os.path.exists(en_wad):
    shutil.copyfile(tr_wad, en_wad)
    print("COPIED Global.tr_TR.wad.client to Global.en_GB.wad.client")

# Patch launcher_windows.go with dynamic locale detection
with open("launcher_windows.go", "r", encoding="utf-8") as f:
    code = f.read()

target = """	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Ensure local tunnel to Mac LCU API on lcuPort is active"""

replacement = """	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Detect local installed language/wad file
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
	}

	// Ensure local tunnel to Mac LCU API on lcuPort is active"""

code = code.replace(target, replacement)
code = code.replace(
    '} else if strings.HasPrefix(arg, "-Locale=") {\n\t\t\tcontinue',
    '} else if strings.HasPrefix(arg, "-Locale=") {\n\t\t\tcleanArgs = append(cleanArgs, "-Locale="+detectedLocale)'
)
# If -Locale= wasn't explicit, replace in generic arg loop:
locale_override = """		} else if strings.HasPrefix(arg, "-Locale=") {
			cleanArgs = append(cleanArgs, "-Locale="+detectedLocale)"""
if "cleanArgs = append(cleanArgs, \"-Locale=\"+detectedLocale)" not in code:
    code = code.replace(
        "} else if strings.HasPrefix(arg, \"-RiotClientPort=\") {",
        locale_override + "\n\t\t} else if strings.HasPrefix(arg, \"-RiotClientPort=\") {"
    )

with open("launcher_windows.go", "w", encoding="utf-8") as f:
    f.write(code)

print("PATCHED launcher_windows.go LOCALE OVERRIDE")
