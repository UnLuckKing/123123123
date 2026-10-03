package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

// ConfigProfileInfo describes a saved or built-in configuration profile.
type ConfigProfileInfo struct {
	Name         string   `json:"name"`
	Description  string   `json:"description"`
	IsBuiltIn    bool     `json:"is_builtin"`
	Author       string   `json:"author"`
	LastUpdated  string   `json:"last_updated"`
	FilesPresent []string `json:"files_present"`
	IsActive     bool     `json:"is_active"`
}

// ConfigManager handles backing up, restoring, swapping, and auto-syncing League configs across accounts.
type ConfigManager struct {
	mu              sync.Mutex
	configDir       string
	profilesDir     string
	activeProfile   string
	autoSyncEnabled bool
	autoSyncStopCh  chan struct{}
	lastHash        string
}

var globalConfigManager *ConfigManager
var configOnce sync.Once

// GetConfigManager returns the singleton instance of ConfigManager.
func GetConfigManager() *ConfigManager {
	configOnce.Do(func() {
		cfgDir := findLeagueConfigDir()
		profDir := filepath.Join(cfgDir, "VantaProfiles")
		_ = os.MkdirAll(profDir, 0755)

		globalConfigManager = &ConfigManager{
			configDir:     cfgDir,
			profilesDir:   profDir,
			activeProfile: "MasterProfile",
		}

		// Automatically preserve authentic player configuration backup if not already saved
		origBackup := filepath.Join(profDir, "Original_Backup")
		if _, statErr := os.Stat(origBackup); os.IsNotExist(statErr) {
			_ = globalConfigManager.SaveCurrentProfile("Original_Backup", "Original League Settings Backup (Auto-Preserved)")
		}
	})
	return globalConfigManager
}

func findLeagueConfigDir() string {
	possible := []string{
		`C:\Riot Games\League of Legends\Config`,
		`D:\Riot Games\League of Legends\Config`,
		`E:\Riot Games\League of Legends\Config`,
		`F:\Riot Games\League of Legends\Config`,
	}

	for _, p := range possible {
		if fi, err := os.Stat(p); err == nil && fi.IsDir() {
			return p
		}
	}

	// Try detecting via ProgramData RiotClientInstalls.json
	programData := os.Getenv("ProgramData")
	if programData != "" {
		installsFile := filepath.Join(programData, "Riot Games", "RiotClientInstalls.json")
		if data, err := os.ReadFile(installsFile); err == nil {
			var m map[string]interface{}
			if json.Unmarshal(data, &m) == nil {
				for _, v := range m {
					if pathStr, ok := v.(string); ok && strings.Contains(strings.ToLower(pathStr), "league of legends") {
						dir := filepath.Dir(pathStr)
						cfg := filepath.Join(dir, "Config")
						if fi, err := os.Stat(cfg); err == nil && fi.IsDir() {
							return cfg
						}
					}
				}
			}
		}
	}

	// Default fallback
	return `C:\Riot Games\League of Legends\Config`
}

// ListProfiles returns all available custom and e-sports pro presets.
func (cm *ConfigManager) ListProfiles() []ConfigProfileInfo {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	var list []ConfigProfileInfo

	// 1. Built-in E-Sports Pro Presets
	proPresets := []struct {
		Name        string
		Author      string
		Description string
	}{
		{
			Name:        "Faker (T1)",
			Author:      "T1 Faker - GOAT Midlaner",
			Description: "Quick Cast all abilities, Attack Move on A & Shift+MB2, Target Champions Only on [~], HUD 33, Minimap 100, 1080p Borderless, Colorblind mode.",
		},
		{
			Name:        "Chovy (Gen.G)",
			Author:      "Gen.G Chovy - CS God",
			Description: "High camera speed (65), Target Champions Only Toggle on Mouse Button 5, HUD 20, Smartcast with indicator for precision skillshots.",
		},
		{
			Name:        "Zeus (T1)",
			Author:      "T1 Zeus - Toplane Duelist",
			Description: "Max performance high-FPS graphics, Auto-Attack disabled, Target Champions Only on Mouse Button 4, Quick Cast all.",
		},
		{
			Name:        "Caps (G2)",
			Author:      "G2 Caps - European Midlaner",
			Description: "Quick Cast all, Quick Danger Ping on V, Emote wheel on T, Chat Font Scale 100, Custom minimap HUD scale.",
		},
		{
			Name:        "Keria (T1)",
			Author:      "T1 Keria - Support Playmaker",
			Description: "Self-Cast binds (Alt+Q/W/E/R), Ward quick cast on 4, Scoreboard size 75, Camera lock toggle on Space.",
		},
	}

	for _, p := range proPresets {
		list = append(list, ConfigProfileInfo{
			Name:         p.Name,
			Description:  p.Description,
			IsBuiltIn:    true,
			Author:       p.Author,
			LastUpdated:  "Vanta Cloud Preset",
			FilesPresent: []string{"game.cfg", "input.ini", "PersistedSettings.json"},
			IsActive:     (cm.activeProfile == p.Name),
		})
	}

	// 2. Custom Saved Profiles in VantaProfiles
	entries, err := os.ReadDir(cm.profilesDir)
	if err == nil {
		for _, e := range entries {
			if e.IsDir() {
				pName := e.Name()
				pDir := filepath.Join(cm.profilesDir, pName)
				var files []string
				for _, fName := range []string{"game.cfg", "input.ini", "PersistedSettings.json"} {
					if _, err := os.Stat(filepath.Join(pDir, fName)); err == nil {
						files = append(files, fName)
					}
				}

				metaPath := filepath.Join(pDir, "profile_meta.json")
				desc := "User custom account backup"
				author := "Local User"
				updated := "Recently"
				if metaData, err := os.ReadFile(metaPath); err == nil {
					var meta map[string]string
					if json.Unmarshal(metaData, &meta) == nil {
						if d, ok := meta["description"]; ok && d != "" {
							desc = d
						}
						if a, ok := meta["author"]; ok && a != "" {
							author = a
						}
						if u, ok := meta["updated_at"]; ok && u != "" {
							updated = u
						}
					}
				}

				list = append(list, ConfigProfileInfo{
					Name:         pName,
					Description:  desc,
					IsBuiltIn:    false,
					Author:       author,
					LastUpdated:  updated,
					FilesPresent: files,
					IsActive:     (cm.activeProfile == pName),
				})
			}
		}
	}

	return list
}

// SaveCurrentProfile backs up the active League of Legends configuration into a named profile.
func (cm *ConfigManager) SaveCurrentProfile(profileName, description string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	if profileName == "" {
		return fmt.Errorf("profile name cannot be empty")
	}

	targetDir := filepath.Join(cm.profilesDir, profileName)
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return err
	}

	// Copy config files
	filesToCopy := []string{"game.cfg", "input.ini", "PersistedSettings.json"}
	copiedCount := 0
	for _, f := range filesToCopy {
		src := filepath.Join(cm.configDir, f)
		dst := filepath.Join(targetDir, f)
		if err := copyFile(src, dst); err == nil {
			copiedCount++
		}
	}

	if copiedCount == 0 {
		return fmt.Errorf("no config files found in League Config dir (%s)", cm.configDir)
	}

	// Write metadata
	meta := map[string]string{
		"description": description,
		"author":      "Local Player",
		"updated_at":  time.Now().Format("2006-01-02 15:04:05"),
	}
	metaBytes, _ := json.MarshalIndent(meta, "", "  ")
	_ = os.WriteFile(filepath.Join(targetDir, "profile_meta.json"), metaBytes, 0644)

	cm.activeProfile = profileName
	return nil
}

// ApplyProfile restores a profile into the active League of Legends Config directory.
func (cm *ConfigManager) ApplyProfile(profileName string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// Ensure files are not write-protected during restore
	cm.setReadOnlyInternal(false)

	// Check if this is a custom saved profile
	customPath := filepath.Join(cm.profilesDir, profileName)
	if fi, err := os.Stat(customPath); err == nil && fi.IsDir() {
		for _, f := range []string{"game.cfg", "input.ini", "PersistedSettings.json"} {
			src := filepath.Join(customPath, f)
			dst := filepath.Join(cm.configDir, f)
			if _, err := os.Stat(src); err == nil {
				_ = copyFile(src, dst)
			}
		}
	} else {
		// Built-in Pro Player Preset generator
		if err := cm.generateProPreset(profileName); err != nil {
			return err
		}
	}

	cm.activeProfile = profileName

	// If League client is running, notify LCU to reload post-game settings
	go func() {
		client, err := NewLCUClient()
		if err == nil {
			_, _, _ = client.Request("POST", "/lol-game-settings/v1/reload-post-game", nil)
		}
	}()

	return nil
}

// generateProPreset constructs pro player configurations dynamically if not saved locally.
func (cm *ConfigManager) generateProPreset(name string) error {
	persistedPath := filepath.Join(cm.configDir, "PersistedSettings.json")
	gameCfgPath := filepath.Join(cm.configDir, "game.cfg")
	inputIniPath := filepath.Join(cm.configDir, "input.ini")

	// Read existing game.cfg or template
	gameCfgData, _ := os.ReadFile(gameCfgPath)
	gameCfgStr := string(gameCfgData)

	inputData, _ := os.ReadFile(inputIniPath)
	inputStr := string(inputData)

	switch {
	case strings.Contains(name, "Faker"):
		gameCfgStr = setConfigValue(gameCfgStr, "General", "TargetChampionsOnlyAsToggle", "1")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtPlayerAttackMoveClick", "[a],[Shift][Button 2]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtTargetChampionsOnly", "[grave]")

	case strings.Contains(name, "Chovy"):
		gameCfgStr = setConfigValue(gameCfgStr, "General", "TargetChampionsOnlyAsToggle", "1")
		gameCfgStr = setConfigValue(gameCfgStr, "General", "GameMouseSpeed", "12")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtTargetChampionsOnly", "[Button 5]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtPlayerAttackMoveClick", "[a]")

	case strings.Contains(name, "Zeus"):
		gameCfgStr = setConfigValue(gameCfgStr, "General", "AutoAcquireTargets", "0")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtTargetChampionsOnly", "[Button 4]")

	case strings.Contains(name, "Caps"):
		inputStr = setConfigValue(inputStr, "GameEvents", "evtEmoteWheel", "[t]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtDangerPing", "[v]")

	case strings.Contains(name, "Keria"):
		inputStr = setConfigValue(inputStr, "GameEvents", "evtSmartPlusSelfCastSpell1", "[Alt][q]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtSmartPlusSelfCastSpell2", "[Alt][w]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtSmartPlusSelfCastSpell3", "[Alt][e]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtSmartPlusSelfCastSpell4", "[Alt][r]")
		inputStr = setConfigValue(inputStr, "GameEvents", "evtUseVisionItem", "[4]")
	}

	_ = os.WriteFile(gameCfgPath, []byte(gameCfgStr), 0644)
	_ = os.WriteFile(inputIniPath, []byte(inputStr), 0644)

	// If PersistedSettings.json exists, update its timestamp
	now := time.Now()
	_ = os.Chtimes(persistedPath, now, now)

	return nil
}

// SetReadOnly toggles Windows read-only file attribute on PersistedSettings.json and game.cfg.
func (cm *ConfigManager) SetReadOnly(readOnly bool) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	return cm.setReadOnlyInternal(readOnly)
}

func (cm *ConfigManager) setReadOnlyInternal(readOnly bool) error {
	targets := []string{
		filepath.Join(cm.configDir, "PersistedSettings.json"),
		filepath.Join(cm.configDir, "game.cfg"),
		filepath.Join(cm.configDir, "input.ini"),
	}

	for _, t := range targets {
		if _, err := os.Stat(t); err == nil {
			setWindowsFileReadOnly(t, readOnly)
		}
	}
	return nil
}

// IsReadOnly checks if PersistedSettings.json is currently write-protected.
func (cm *ConfigManager) IsReadOnly() bool {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	p := filepath.Join(cm.configDir, "PersistedSettings.json")
	return isWindowsFileReadOnly(p)
}

// StartAutoSyncDaemon activates the background account-switch watcher.
func (cm *ConfigManager) StartAutoSyncDaemon(targetProfile string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	if cm.autoSyncEnabled {
		if cm.autoSyncStopCh != nil {
			close(cm.autoSyncStopCh)
		}
	}

	cm.autoSyncEnabled = true
	cm.autoSyncStopCh = make(chan struct{})
	cm.activeProfile = targetProfile

	persistedPath := filepath.Join(cm.configDir, "PersistedSettings.json")
	cm.lastHash = getFileMD5(persistedPath)

	stopCh := cm.autoSyncStopCh

	go func() {
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-stopCh:
				return
			case <-ticker.C:
				currentHash := getFileMD5(persistedPath)
				if currentHash != "" && cm.lastHash != "" && currentHash != cm.lastHash {
					// PersistedSettings was modified.
					// If the 3D game match is active (League of Legends.exe is running), DO NOT overwrite
					// because the user is currently playing and adjusting their real in-game preferences!
					if !isLeagueGameRunning() {
						_ = cm.ApplyProfile(targetProfile)
					}
					cm.lastHash = getFileMD5(persistedPath)
				}
			}
		}
	}()
}

// StopAutoSyncDaemon disables background auto sync.
func (cm *ConfigManager) StopAutoSyncDaemon() {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	if cm.autoSyncEnabled && cm.autoSyncStopCh != nil {
		close(cm.autoSyncStopCh)
		cm.autoSyncStopCh = nil
	}
	cm.autoSyncEnabled = false
}

// IsAutoSyncEnabled returns the current status of background auto-sync.
func (cm *ConfigManager) IsAutoSyncEnabled() bool {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	return cm.autoSyncEnabled
}

// --- Windows File Attribute Helpers ---

func setWindowsFileReadOnly(path string, readOnly bool) {
	ptr, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return
	}
	attrs, err := syscall.GetFileAttributes(ptr)
	if err != nil {
		return
	}
	if readOnly {
		attrs |= syscall.FILE_ATTRIBUTE_READONLY
	} else {
		attrs &^= syscall.FILE_ATTRIBUTE_READONLY
	}
	_ = syscall.SetFileAttributes(ptr, attrs)
}

func isWindowsFileReadOnly(path string) bool {
	ptr, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return false
	}
	attrs, err := syscall.GetFileAttributes(ptr)
	if err != nil {
		return false
	}
	return (attrs & syscall.FILE_ATTRIBUTE_READONLY) != 0
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

func getFileMD5(path string) string {
	f, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer f.Close()

	h := md5.New()
	if _, err := io.Copy(h, f); err != nil {
		return ""
	}
	return hex.EncodeToString(h.Sum(nil))
}

func setConfigValue(content, section, key, val string) string {
	lines := strings.Split(content, "\n")
	inSection := false
	keyFound := false
	targetSec := "[" + section + "]"

	var newLines []string
	for _, l := range lines {
		trimmed := strings.TrimSpace(l)
		if strings.HasPrefix(trimmed, "[") && strings.HasSuffix(trimmed, "]") {
			if inSection && !keyFound {
				newLines = append(newLines, key+"="+val)
				keyFound = true
			}
			inSection = (trimmed == targetSec)
		} else if inSection && strings.HasPrefix(trimmed, key+"=") {
			l = key + "=" + val
			keyFound = true
		}
		newLines = append(newLines, l)
	}

	if inSection && !keyFound {
		newLines = append(newLines, key+"="+val)
	} else if !keyFound {
		newLines = append(newLines, "", targetSec, key+"="+val)
	}

	return strings.Join(newLines, "\n")
}
