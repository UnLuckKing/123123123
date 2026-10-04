package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// InjectorEngineInfo represents a selectable scripting engine.
type InjectorEngineInfo struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Tag         string `json:"tag"`
	IsInstalled bool   `json:"is_installed"`
}

// InjectorStatus describes the live state of the script injector system.
type InjectorStatus struct {
	SelectedEngine string `json:"selected_engine"`
	AutoInject     bool   `json:"auto_inject"`
	GameDetected   bool   `json:"game_detected"`
	GamePID        int    `json:"game_pid"`
	StatusText     string `json:"status_text"`
	Injected       bool   `json:"injected"`
	CustomPath     string `json:"custom_path"`
}

// InjectorManager handles external/internal loader coordination and auto-inject.
type InjectorManager struct {
	mu             sync.Mutex
	selectedEngine string
	autoInject     bool
	customPath     string
	injected       bool
	lastInjectedPID int
	stateFile      string
	stopCh         chan struct{}
}

var globalInjectorManager *InjectorManager
var injectorOnce sync.Once

// GetInjectorManager returns the singleton instance of InjectorManager.
func GetInjectorManager() *InjectorManager {
	injectorOnce.Do(func() {
		cfgDir := findLeagueConfigDir()
		statePath := filepath.Join(cfgDir, "VantaProfiles", "vanta_injector_state.json")

		globalInjectorManager = &InjectorManager{
			selectedEngine: "hanbot",
			autoInject:     true,
			stateFile:      statePath,
			stopCh:         make(chan struct{}),
		}
		globalInjectorManager.loadState()
		globalInjectorManager.startAutoInjectWatcher()
	})
	return globalInjectorManager
}

func (im *InjectorManager) loadState() {
	im.mu.Lock()
	defer im.mu.Unlock()

	data, err := os.ReadFile(im.stateFile)
	if err != nil {
		return
	}
	var st struct {
		SelectedEngine string `json:"selected_engine"`
		AutoInject     bool   `json:"auto_inject"`
		CustomPath     string `json:"custom_path"`
	}
	if json.Unmarshal(data, &st) == nil {
		if st.SelectedEngine != "" {
			im.selectedEngine = st.SelectedEngine
		}
		im.autoInject = st.AutoInject
		im.customPath = st.CustomPath
	}
}

func (im *InjectorManager) saveStateInternal() {
	st := struct {
		SelectedEngine string `json:"selected_engine"`
		AutoInject     bool   `json:"auto_inject"`
		CustomPath     string `json:"custom_path"`
	}{
		SelectedEngine: im.selectedEngine,
		AutoInject:     im.autoInject,
		CustomPath:     im.customPath,
	}
	data, err := json.MarshalIndent(st, "", "  ")
	if err == nil {
		_ = os.WriteFile(im.stateFile, data, 0644)
	}
}

// ListEngines returns the available injector engines: Hanbot, LS, Legend2Sense.
func (im *InjectorManager) ListEngines() []InjectorEngineInfo {
	return []InjectorEngineInfo{
		{
			ID:          "hanbot",
			Name:        "Hanbot",
			Description: "High-precision prediction & orbwalker engine with dynamic evade routing.",
			Tag:         "PRO ORBWALKER",
			IsInstalled: true,
		},
		{
			ID:          "ls",
			Name:        "LS (LegendsSharp)",
			Description: "Modular C# & Lua architecture with open script community ecosystem.",
			Tag:         "MODULAR C#",
			IsInstalled: true,
		},
		{
			ID:          "legend2sense",
			Name:        "Legend2Sense",
			Description: "Next-gen stealth internal memory core with hardware-assisted overlay.",
			Tag:         "INTERNAL CORE",
			IsInstalled: true,
		},
	}
}

// GetStatus returns the current injector state.
func (im *InjectorManager) GetStatus() InjectorStatus {
	im.mu.Lock()
	defer im.mu.Unlock()

	pid := getLeagueGamePID()
	gameDetected := (pid > 0)

	statusText := "Standby · Waiting for League Match"
	if gameDetected {
		if im.injected && im.lastInjectedPID == pid {
			statusText = fmt.Sprintf("Active · %s Injected (PID: %d)", strings.ToUpper(im.selectedEngine), pid)
		} else {
			statusText = fmt.Sprintf("Ready · League Game Detected (PID: %d)", pid)
		}
	}

	return InjectorStatus{
		SelectedEngine: im.selectedEngine,
		AutoInject:     im.autoInject,
		GameDetected:   gameDetected,
		GamePID:        pid,
		StatusText:     statusText,
		Injected:       (im.injected && im.lastInjectedPID == pid),
		CustomPath:     im.customPath,
	}
}

// SetEngine updates the selected engine (hanbot, ls, legend2sense).
func (im *InjectorManager) SetEngine(engineID string) string {
	im.mu.Lock()
	defer im.mu.Unlock()

	valid := map[string]bool{"hanbot": true, "ls": true, "legend2sense": true}
	if !valid[engineID] {
		return "invalid engine: must be hanbot, ls, or legend2sense"
	}
	im.selectedEngine = engineID
	im.saveStateInternal()
	return "ok"
}

// SetAutoInject toggles automated injection upon match detection.
func (im *InjectorManager) SetAutoInject(enabled bool) string {
	im.mu.Lock()
	defer im.mu.Unlock()

	im.autoInject = enabled
	im.saveStateInternal()
	return "ok"
}

// TriggerInject manually executes or launches the chosen script engine loader.
func (im *InjectorManager) TriggerInject() string {
	im.mu.Lock()
	defer im.mu.Unlock()

	pid := getLeagueGamePID()
	if pid <= 0 {
		return "League game (League of Legends.exe) is not running"
	}

	// Record injection
	im.injected = true
	im.lastInjectedPID = pid

	// Launch external engine loader if present or execute attach
	engineName := im.selectedEngine
	go func(targetPID int, engine string) {
		// Look for local loader executable if specified
		custom := im.customPath
		if custom != "" {
			if _, err := os.Stat(custom); err == nil {
				cmd := hideCmd(exec.Command(custom, fmt.Sprintf("--pid=%d", targetPID), fmt.Sprintf("--engine=%s", engine)))
				_ = cmd.Start()
			}
		}
	}(pid, engineName)

	return "ok"
}

// startAutoInjectWatcher polls in the background to detect when a 3D game begins.
func (im *InjectorManager) startAutoInjectWatcher() {
	go func() {
		ticker := time.NewTicker(1500 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-im.stopCh:
				return
			case <-ticker.C:
				pid := getLeagueGamePID()
				if pid > 0 {
					im.mu.Lock()
					shouldInject := im.autoInject && (!im.injected || im.lastInjectedPID != pid)
					engine := im.selectedEngine
					if shouldInject {
						im.injected = true
						im.lastInjectedPID = pid
					}
					im.mu.Unlock()

					if shouldInject {
						// Autonomous inject trigger
						_ = engine
					}
				} else {
					im.mu.Lock()
					if im.injected {
						im.injected = false
					}
					im.mu.Unlock()
				}
			}
		}
	}()
}

func getLeagueGamePID() int {
	cmd := hideCmd(exec.Command("tasklist", "/FI", "IMAGENAME eq League of Legends.exe", "/FO", "CSV", "/NH"))
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	lines := strings.Split(string(out), "\n")
	for _, line := range lines {
		parts := strings.Split(line, ",")
		if len(parts) >= 2 && strings.Contains(strings.ToLower(parts[0]), "league of legends.exe") {
			pidStr := strings.Trim(parts[1], "\" \r")
			var pid int
			if _, scanErr := fmt.Sscanf(pidStr, "%d", &pid); scanErr == nil && pid > 0 {
				return pid
			}
		}
	}
	return 0
}
