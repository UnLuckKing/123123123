package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// LoginOKPayload represents client license status for UI.
type LoginOKPayload struct {
	HasLicense bool   `json:"has_license"`
	ExpiresAt  string `json:"expires_at,omitempty"`
}

// App is the main Wails application struct.
type App struct {
	ctx            context.Context
	mu             sync.Mutex
	status         string
	lastError      string
	rcsPath        string
	proxy          *LeagueProxy
	license        *LoginOKPayload
	licenseKey     string
	stopCh         chan struct{}
	activeSlotID   string
	debugLog       []string
	debugMu        sync.Mutex
	sentinel       *EventSentinel
	lastGameArgs   []string
	lastProxyPort    int
	lastLCUPort           int
	lastSlotID            string
	lastGameLaunch        time.Time
	lastConcludedMatchSig string
	lastGameExitTime      time.Time
	autoAcceptActive      bool
	autoAcceptStopCh      chan struct{}
	ticketData            string
	signature             string
}

var globalApp *App

// GetGlobalApp returns the running App instance.
func GetGlobalApp() *App {
	return globalApp
}

// NewApp creates a new App instance.
func NewApp() *App {
	a := &App{
		status: "disconnected",
	}
	globalApp = a
	return a
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	ApplyFullStealthEvasion()
	a.sentinel = NewEventSentinel(a)
	a.sentinel.Start()
	// Do NOT kill Riot or League services on app launch.
}

func (a *App) shutdown(ctx context.Context) {
	if a.sentinel != nil {
		a.sentinel.Stop()
		a.sentinel.PurgeTelemetryAndCrashpads()
	}
	a.cleanup()
}

func (a *App) beforeClose(ctx context.Context) (prevent bool) {
	if a.sentinel != nil {
		a.sentinel.Stop()
		a.sentinel.PurgeTelemetryAndCrashpads()
	}
	a.cleanup()
	return false
}

// --- Wails bindings: common ---

// GetPlatform returns "windows" or "darwin".
func (a *App) GetPlatform() string {
	return runtime.GOOS
}

// GetStatus returns the current app status.
func (a *App) GetStatus() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.status
}

// GetLicenseInfo returns license details after login.
func (a *App) GetLicenseInfo() map[string]interface{} {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.license == nil {
		return nil
	}
	return map[string]interface{}{
		"has_license": a.license.HasLicense,
		"expires_at":  a.license.ExpiresAt,
	}
}

// GetLastError returns the current error code or message.
func (a *App) GetLastError() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.lastError
}

// ClearLastError resets the active error state.
func (a *App) ClearLastError() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.lastError = ""
	return "ok"
}

// GetLocale returns the detected system or League language code.
func (a *App) GetLocale() string {
	return DetectSystemLocale()
}

// GetNoAccountI18n returns localized strings for no-account error screen.
func (a *App) GetNoAccountI18n(locale string) NoAccountI18n {
	return GetLocalizedNoAccount(locale)
}

// LaunchRiotClient opens RiotClientServices on Windows to let the user log in.
func (a *App) LaunchRiotClient() string {
	rcsPath := FindRiotClientServices()
	if rcsPath == "" {
		return "Riot Client executable not found on disk"
	}
	cmd := hideCmd(exec.Command(rcsPath))
	if err := cmd.Start(); err != nil {
		return err.Error()
	}
	return "ok"
}

// Login authorizes access. Instant zero-friction execution.
func (a *App) Login(username, password string) string {
	a.mu.Lock()
	a.licenseKey = username
	a.ticketData = ""
	a.signature = ""
	a.lastError = ""
	a.license = &LoginOKPayload{
		HasLicense: true,
		ExpiresAt:  "Lifetime (Active)",
	}
	a.status = "logged_in"
	a.mu.Unlock()
	return "ok"
}

// Logout disconnects from the server.
func (a *App) Logout() string {
	a.mu.Lock()
	a.lastError = ""
	a.mu.Unlock()
	a.cleanup()
	return "ok"
}

// --- Windows mode: client ---

// PrepareLogin sends the local Riot session YAML to the Mac orchestrator,
// waits for LeagueClient to start there, then launches LeagueClient locally
// with the Mac's RC session tunnel — bypassing Vanguard via macOS platform muafiyeti.
func (a *App) PrepareLogin(rcsPath string) string {
	a.mu.Lock()
	a.lastError = ""
	a.rcsPath = rcsPath
	if a.status != "logged_in" {
		a.mu.Unlock()
		return "must be logged in first"
	}
	if !a.license.HasLicense {
		a.mu.Unlock()
		return "no active license"
	}
	if isLeagueGameRunning() {
		a.mu.Lock()
		a.status = "logged_in"
		a.mu.Unlock()
		return "A League of Legends match is currently active. Finish your game before starting bypass."
	}

	a.status = "login_phase"
	a.mu.Unlock()

	a.logDebug("[bypass] PrepareLogin (Mac session) started")

	// Kill existing Riot/League processes only when clean bypass start requested
	terminateRiotServices()
	if IsVanguardRunning() {
		StopVanguard()
		a.logDebug("[bypass] stopped vanguard")
	}

	// Read local Riot session YAML
	yamlPath := getSettingsPath()
	yamlData, err := os.ReadFile(yamlPath)
	yamlStr := string(yamlData)
	hasValidSession := strings.Contains(yamlStr, "riot-login") ||
		strings.Contains(yamlStr, "rso-authenticator") ||
		strings.Contains(yamlStr, "id_token") ||
		strings.Contains(yamlStr, "refresh_token")

	if err != nil || len(yamlData) < 100 || !hasValidSession {
		a.mu.Lock()
		a.status = "logged_in"
		a.lastError = "ERR_NO_RIOT_ACCOUNT"
		a.mu.Unlock()
		loc := DetectSystemLocale()
		item := GetLocalizedNoAccount(loc)
		return item.Title + ": " + item.Message
	}
	a.logDebug("[bypass] YAML loaded (%d bytes)", len(yamlData))

	a.stopCh = make(chan struct{})

	go func() {
		a.mu.Lock()
		a.status = "submitting"
		a.mu.Unlock()

		// Request a Mac slot — sends YAML to orchestrator
		hub := NewHubClient()
		a.mu.Lock()
		if a.activeSlotID != "" {
			hub.KillSlot(a.activeSlotID)
			a.activeSlotID = ""
		}
		a.mu.Unlock()

		ReportGlobalTelemetry("INFO", "CLIENT_BYPASS", "Requesting M1 isolated slot...", "", nil)
		a.mu.Lock()
		curKey := a.licenseKey
		curTicket := a.ticketData
		curSig := a.signature
		a.mu.Unlock()
		slotID, err := hub.RequestVM(string(yamlData), curKey, curTicket, curSig)
		if err != nil {
			a.mu.Lock()
			a.status = "logged_in"
			a.lastError = "ERR_NO_RIOT_ACCOUNT"
			a.mu.Unlock()
			a.logDebug("[bypass] slot request failed: %v", err)
			ReportGlobalTelemetry("ERROR", "CLIENT_BYPASS", "M1 Slot request failed", err.Error(), nil)
			return
		}
		a.mu.Lock()
		a.activeSlotID = slotID
		a.status = "preparing"
		a.mu.Unlock()

		a.logDebug("[bypass] slot acquired: %s", slotID)
		ReportGlobalTelemetry("INFO", "CLIENT_BYPASS", fmt.Sprintf("M1 Slot acquired: %s", slotID), "", map[string]interface{}{"slot_id": slotID})

		// Poll until game_ready (max 4 min)
		deadline := time.Now().Add(4 * time.Minute)
		for {
			select {
			case <-a.stopCh:
				return
			default:
			}

			if time.Now().After(deadline) {
				a.mu.Lock()
				a.status = "logged_in"
				a.lastError = "ERR_NO_RIOT_ACCOUNT"
				a.mu.Unlock()
				a.logDebug("[bypass] timeout waiting for Mac slot")
				ReportGlobalTelemetry("ERROR", "CLIENT_BYPASS", "Timeout waiting for Mac slot", fmt.Sprintf("slot_id=%s", slotID), nil)
				return
			}

			statusResp, err := hub.PollVM(slotID)
			if err != nil {
				// If orchestrator returned 404 (slot failed or terminated on Mac)
				if strings.Contains(err.Error(), "404") {
					a.mu.Lock()
					a.status = "logged_in"
					a.activeSlotID = ""
					a.lastError = "ERR_NO_RIOT_ACCOUNT"
					a.mu.Unlock()
					a.logDebug("[bypass] slot %s terminated on Mac -> no active account", slotID)
					return
				}
				time.Sleep(2 * time.Second)
				continue
			}

			switch statusResp.Status {
			case "game_ready":
				if len(statusResp.Args) == 0 {
					time.Sleep(1 * time.Second)
					continue
				}
				proxyPort := statusResp.ProxyPort
				if proxyPort == 0 {
					proxyPort = 8090 // fallback
				}
				lcuPort := statusResp.LCUPort
				if lcuPort == 0 {
					lcuPort = proxyPort + 1 // fallback
				}
				a.logDebug("[bypass] game_ready — args=%d proxy_port=%d lcu_port=%d", len(statusResp.Args), proxyPort, lcuPort)
				ReportGlobalTelemetry("INFO", "CLIENT_BYPASS", "Mac slot ready, starting local LeagueClient", fmt.Sprintf("proxy_port=%d, lcu_port=%d", proxyPort, lcuPort), map[string]interface{}{
					"slot_id":    slotID,
					"proxy_port": proxyPort,
					"lcu_port":   lcuPort,
				})
				a.mu.Lock()
				a.status = "running"
				a.lastError = ""
				a.mu.Unlock()
				if err := LaunchLeagueClientLocally(statusResp.Args, proxyPort, lcuPort); err != nil {
					a.logDebug("[bypass] launch error: %v", err)
					ReportGlobalTelemetry("CRITICAL", "CLIENT_BYPASS", "Failed to launch local LeagueClient", err.Error(), map[string]interface{}{"slot_id": slotID})
					a.mu.Lock()
					a.status = "logged_in"
					a.mu.Unlock()
					return
				}
				go a.logCleanLoop()
				go a.gameMatchMonitorLoop(slotID, proxyPort, lcuPort)
				return

			default:
				if strings.Contains(statusResp.Status, "FAILED") || strings.Contains(statusResp.Status, "timeout") || strings.Contains(statusResp.Status, "error") || strings.Contains(statusResp.Status, "NO_ACTIVE") {
					a.mu.Lock()
					a.status = "logged_in"
					a.activeSlotID = ""
					a.lastError = "ERR_NO_RIOT_ACCOUNT"
					a.mu.Unlock()
					a.logDebug("[bypass] slot failed: %s -> no active account", statusResp.Status)
					ReportGlobalTelemetry("ERROR", "CLIENT_BYPASS", "Riot session authentication timeout (no account)", "", map[string]interface{}{"slot_id": slotID, "status": statusResp.Status})
					return
				}
				// still provisioning
			}

			time.Sleep(3 * time.Second)
		}
	}()

	a.flushLogs()
	return "ok"
}

// gameMatchMonitorLoop continuously polls the Mac orchestrator for 3D Game match parameters.
// When a match starts in champion select / gameflow, it launches League of Legends.exe locally.
func (a *App) gameMatchMonitorLoop(slotID string, proxyPort int, lcuPort int) {
	hub := NewHubClient()
	a.logDebug("[match_monitor] Started monitoring for 3D Game Match (slot %s)", slotID)
	gameLaunched := false

	for {
		select {
		case <-a.stopCh:
			a.logDebug("[match_monitor] Stopped")
			return
		default:
		}

		statusResp, err := hub.PollVM(slotID)
		if err == nil {
			a.mu.Lock()
			hasCachedArgs := len(a.lastGameArgs) > 0
			a.mu.Unlock()

			if len(statusResp.GameArgs) > 0 && !gameLaunched && !hasCachedArgs {
				matchSig := strings.Join(statusResp.GameArgs, "|")
				a.mu.Lock()
				concludedSig := a.lastConcludedMatchSig
				timeSinceExit := time.Since(a.lastGameExitTime)
				a.mu.Unlock()

				// Anti-reopen guard: do not re-launch concluded match or launch during post-match cooldown
				if (concludedSig != "" && matchSig == concludedSig) || timeSinceExit < 12*time.Second {
					time.Sleep(2 * time.Second)
					continue
				}

				a.logDebug("[match_monitor] 3D Game Match detected! Args count: %d", len(statusResp.GameArgs))
				ReportGlobalTelemetry("INFO", "GAME_MATCH", "3D Game Match detected on Mac", fmt.Sprintf("slot_id=%s, args=%d", slotID, len(statusResp.GameArgs)), map[string]interface{}{"slot_id": slotID})

				a.mu.Lock()
				a.lastGameArgs = statusResp.GameArgs
				a.lastProxyPort = proxyPort
				a.lastLCUPort = lcuPort
				a.lastSlotID = slotID
				a.lastGameLaunch = time.Now()
				a.mu.Unlock()

				if err := LaunchLeagueGameLocally(statusResp.GameArgs, proxyPort, lcuPort, slotID); err != nil {
					a.logDebug("[match_monitor] Failed to launch local game: %v", err)
					ReportGlobalTelemetry("CRITICAL", "GAME_MATCH", "Failed to launch local 3D League Game", err.Error(), map[string]interface{}{"slot_id": slotID})
					a.mu.Lock()
					a.lastGameArgs = nil
					a.mu.Unlock()
				} else {
					gameLaunched = true
					a.logDebug("[match_monitor] Local League of Legends.exe launched successfully!")
					ReportGlobalTelemetry("INFO", "GAME_MATCH", "Local League of Legends.exe launched successfully", "", map[string]interface{}{"slot_id": slotID})
				}
			} else if len(statusResp.GameArgs) == 0 {
				if gameLaunched {
					gameLaunched = false
					a.logDebug("[match_monitor] Previous game concluded. Ready for next match.")
				}
				a.mu.Lock()
				a.lastConcludedMatchSig = ""
				a.mu.Unlock()
			}
		}

		time.Sleep(2 * time.Second)
	}
}

// OnGameProcessExited is triggered as soon as the League of Legends.exe process terminates.
// OnGameProcessExited is triggered as soon as the League of Legends.exe process terminates.
func (a *App) OnGameProcessExited(waitErr error, duration float64, slotID string) {
	if slotID == "" {
		a.mu.Lock()
		slotID = a.lastSlotID
		if slotID == "" {
			slotID = a.activeSlotID
		}
		a.mu.Unlock()
	}

	// Autonomous crash detection: check if gameflow is still InProgress or Reconnect
	isMatchActive := false
	if client, err := NewLCUClient(); err == nil {
		if phase, pErr := client.GetGameflowPhase(); pErr == nil {
			if phase == "InProgress" || phase == "Reconnect" {
				isMatchActive = true
			}
		}
	}

	// If game exited with an error / crash and the match is STILL ongoing on Riot servers:
	// Retain cached args and DO NOT conclude the match on Mac orchestrator!
	// This enables instant autonomous reconnection.
	if waitErr != nil && isMatchActive {
		a.logDebug("[match] Game crashed after %.1fs (err=%v) during active match. Retaining slot %s for reconnect.", duration, waitErr, slotID)
		ReportGlobalTelemetry("WARNING", "GAME_MATCH", fmt.Sprintf("Game crashed after %.1fs during active match. Triggering autonomous reconnect.", duration), waitErr.Error(), map[string]interface{}{
			"slot_id":  slotID,
			"duration": duration,
		})
		go func() {
			time.Sleep(1500 * time.Millisecond)
			reconnRes := a.ReconnectGame()
			a.logDebug("[match] Autonomous reconnect result: %s", reconnRes)
		}()
		return
	}

	a.mu.Lock()
	if len(a.lastGameArgs) > 0 {
		a.lastConcludedMatchSig = strings.Join(a.lastGameArgs, "|")
	}
	a.lastGameExitTime = time.Now()
	a.lastGameArgs = nil // Immediately clear cached match arguments so no auto-reconnect loops occur
	a.status = "running"
	a.mu.Unlock()

	a.logDebug("[match] Game process exited after %.1fs (err=%v). Concluding slot %s", duration, waitErr, slotID)
	ReportGlobalTelemetry("INFO", "GAME_MATCH", fmt.Sprintf("Game process ended after %.1fs", duration), "", map[string]interface{}{
		"slot_id":  slotID,
		"duration": duration,
	})

	// Conclude match on orchestrator and hub immediately
	if slotID != "" {
		hub := NewHubClient()
		_ = hub.ConcludeMatch(slotID)
	}

	// Dismiss end of game stats in LCU so LeagueClientUx returns cleanly to lobby
	go func() {
		time.Sleep(1 * time.Second)
		if lcu, err := NewLCUClient(); err == nil {
			_ = lcu.DismissEndOfGame()
		}
	}()
}

// ConcludeMatch manually concludes the match and returns to lobby state.
func (a *App) ConcludeMatch() string {
	a.mu.Lock()
	slotID := a.activeSlotID
	if slotID == "" {
		slotID = a.lastSlotID
	}
	a.lastGameArgs = nil
	a.status = "running"
	a.mu.Unlock()

	if slotID != "" {
		hub := NewHubClient()
		_ = hub.ConcludeMatch(slotID)
	}

	go func() {
		time.Sleep(500 * time.Millisecond)
		if lcu, err := NewLCUClient(); err == nil {
			_ = lcu.DismissEndOfGame()
		}
	}()
	return "ok"
}

// ReconnectGame re-launches League of Legends.exe locally with the cached match arguments.
func (a *App) ReconnectGame() string {
	a.mu.Lock()
	args := a.lastGameArgs
	proxyPort := a.lastProxyPort
	lcuPort := a.lastLCUPort
	slotID := a.lastSlotID
	if slotID == "" {
		slotID = a.activeSlotID
	}
	a.mu.Unlock()

	if len(args) == 0 {
		if slotID != "" {
			hub := NewHubClient()
			if statusResp, err := hub.PollVM(slotID); err == nil && len(statusResp.GameArgs) > 0 {
				args = statusResp.GameArgs
				if statusResp.ProxyPort > 0 {
					proxyPort = statusResp.ProxyPort
				}
				if statusResp.LCUPort > 0 {
					lcuPort = statusResp.LCUPort
				}
				a.mu.Lock()
				a.lastGameArgs = args
				a.lastProxyPort = proxyPort
				a.lastLCUPort = lcuPort
				a.mu.Unlock()
			}
		}
		if len(args) == 0 {
			return "No active match arguments cached to reconnect"
		}
	}

	a.logDebug("[reconnect] Reconnecting to 3D game (slot %s, args %d)", slotID, len(args))
	ReportGlobalTelemetry("INFO", "RECONNECT", "User triggered ReconnectGame", fmt.Sprintf("slot_id=%s", slotID), map[string]interface{}{
		"slot_id": slotID,
	})

	// Make sure any stale League of Legends.exe is terminated first
	killLeagueGame()
	time.Sleep(500 * time.Millisecond)

	if err := LaunchLeagueGameLocally(args, proxyPort, lcuPort, slotID); err != nil {
		a.logDebug("[reconnect] Launch error: %v", err)
		ReportGlobalTelemetry("CRITICAL", "RECONNECT", "Failed to relaunch 3D game", err.Error(), nil)
		return "Failed to reconnect: " + err.Error()
	}

	a.logDebug("[reconnect] 3D Game relaunched successfully!")
	return "ok"
}

// DismissPostGame clears any stuck "Game is still in progress..." or end-of-game stats screen.
func (a *App) DismissPostGame() string {
	a.mu.Lock()
	slotID := a.activeSlotID
	a.mu.Unlock()

	if slotID != "" {
		hub := NewHubClient()
		_ = hub.ConcludeMatch(slotID)
	}

	client, err := NewLCUClient()
	if err != nil {
		return "lcu_unavailable: " + err.Error()
	}
	if err := client.DismissEndOfGame(); err != nil {
		return "failed: " + err.Error()
	}
	a.logDebug("[lcu] Post-game / stuck flow successfully dismissed")
	return "ok"
}



// Stop cancels any in-progress operation (Windows only).
func (a *App) Stop() string {
	a.mu.Lock()
	s := a.status
	a.mu.Unlock()

	if s == "disconnected" || s == "logged_in" {
		return "nothing to stop"
	}

	if a.stopCh != nil {
		select {
		case <-a.stopCh:
		default:
			close(a.stopCh)
		}
	}

	// Don't kill Riot/League processes on stop — user may want to keep playing
	if a.proxy != nil {
		a.proxy.Stop()
		a.proxy = nil
	}
	TerminateLeagueClientShim()

	a.mu.Lock()
	if a.activeSlotID != "" {
		hub := NewHubClient()
		hub.KillSlot(a.activeSlotID)
		a.activeSlotID = ""
	}
	a.status = "logged_in"
	a.lastError = ""
	a.mu.Unlock()

	return "ok"
}

// --- Secondary PC mode: guardian ---

// StartWorker begins monitoring for League game on the secondary PC and kills it if it starts.
func (a *App) StartWorker() string {
	a.mu.Lock()
	if a.status != "logged_in" {
		a.mu.Unlock()
		return "must be logged in first"
	}
	if !a.license.HasLicense {
		a.mu.Unlock()
		return "no active license"
	}
	a.status = "monitoring"
	a.stopCh = make(chan struct{})
	a.mu.Unlock()

	a.logDebug("[2nd-pc] StartWorker, platform=%s", runtime.GOOS)
	go a.workerLoop()
	return "ok"
}

// workerLoop runs on the secondary PC:
//   - kills League game (League of Legends.exe) if it starts
//   - keeps League client alive — restarts it if it crashes
func (a *App) workerLoop() {
	a.logDebug("[2nd-pc] workerLoop started")

	// Initial launch if League client is not already running
	if !isLeagueClientRunning() {
		a.logDebug("[2nd-pc] League client not running, launching")
		launchLeague()
		sleepOrStop(a.stopCh, 5000)
	}

	failCount := 0
	for {
		select {
		case <-a.stopCh:
			a.logDebug("[2nd-pc] workerLoop stopped")
			a.flushLogs()
			return
		default:
		}

		// Kill the game process if it tries to start
		if isLeagueGameRunning() {
			a.logDebug("[2nd-pc] League game detected, terminating")
			killLeagueGame()
		}

		// Keep League client alive — restart if it crashed
		if !isLeagueClientRunning() {
			a.logDebug("[2nd-pc] League client not running, restarting")
			if err := launchLeague(); err != nil {
				failCount++
				a.logDebug("[2nd-pc] client launch failed (attempt %d): %v", failCount, err)
				backoff := 5000
				if failCount > 5 {
					backoff = 30000
				}
				sleepOrStop(a.stopCh, backoff)
				continue
			}
			failCount = 0
			sleepOrStop(a.stopCh, 5000)
			continue
		}

		failCount = 0
		sleepOrStop(a.stopCh, 1000)
	}
}

// StopWorker stops the worker monitoring loop.
func (a *App) StopWorker() string {
	a.mu.Lock()
	if a.status != "monitoring" {
		a.mu.Unlock()
		return "worker not running"
	}
	a.mu.Unlock()

	close(a.stopCh)

	a.mu.Lock()
	a.status = "logged_in"
	a.mu.Unlock()

	return "ok"
}

// --- internal helpers ---

func (a *App) cleanup() {
	if a.stopCh != nil {
		select {
		case <-a.stopCh:
		default:
			close(a.stopCh)
		}
	}

	if a.proxy != nil {
		a.proxy.Stop()
		a.proxy = nil
	}

	a.mu.Lock()
	slotID := a.activeSlotID
	a.activeSlotID = ""
	a.license = nil
	a.status = "disconnected"
	a.mu.Unlock()

	if slotID != "" {
		a.logDebug("[cleanup] Freeing active slot on exit: %s", slotID)
		hub := NewHubClient()
		_ = hub.KillSlot(slotID)
	}
}

// logCleanLoop removes Riot log directories periodically while idle, but never while a game is running.
func (a *App) logCleanLoop() {
	for {
		sleepOrStop(a.stopCh, 5000)
		select {
		case <-a.stopCh:
			return
		default:
			if !isLeagueGameRunning() {
				clearRiotLogs()
			}
		}
	}
}

// FindRCS auto-detects RCS path (exposed to frontend).
func (a *App) FindRCS() string {
	return FindRiotClientServices()
}

// AutoAcceptQueue starts the background LCU auto-accept loop.
func (a *App) AutoAcceptQueue() string {
	a.mu.Lock()
	if a.autoAcceptActive {
		a.mu.Unlock()
		return "already_running"
	}
	a.autoAcceptActive = true
	a.autoAcceptStopCh = make(chan struct{})
	stopCh := a.autoAcceptStopCh
	a.mu.Unlock()

	StartAutoAcceptDaemon(stopCh, a.logDebug)
	a.logDebug("[bypass] AutoAcceptQueue daemon initiated")
	return "ok"
}

// StopAutoAccept stops the background LCU auto-accept loop.
func (a *App) StopAutoAccept() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.autoAcceptActive && a.autoAcceptStopCh != nil {
		close(a.autoAcceptStopCh)
		a.autoAcceptActive = false
		a.autoAcceptStopCh = nil
		a.logDebug("[bypass] AutoAcceptQueue daemon terminated")
	}
	return "ok"
}

// SetChampSelectRule configures autonomous champion select pick/ban preferences.
func (a *App) SetChampSelectRule(rule ChampSelectRule) string {
	SetActiveChampSelectRule(rule)
	a.logDebug("[bypass] ChampSelectRule updated: pick=%d (active=%v), ban=%d (active=%v), runes=%v",
		rule.PickChampionID, rule.AutoPickEnabled, rule.BanChampionID, rule.AutoBanEnabled, rule.AutoRunes)
	return "ok"
}

// GetChampSelectRule returns the current autonomous champion select pick/ban preferences.
func (a *App) GetChampSelectRule() ChampSelectRule {
	return GetActiveChampSelectRule()
}

// ClaimRewards claims any pending tutorial capsules or level up loot via LCU.
func (a *App) ClaimRewards() []string {
	client, err := NewLCUClient()
	if err != nil {
		a.logDebug("[LCU-LOOT] Failed to connect to LCU: %v", err)
		return nil
	}
	claimed, err := client.ClaimTutorialRewards()
	if err != nil {
		a.logDebug("[LCU-LOOT] Error claiming rewards: %v", err)
		return nil
	}
	a.logDebug("[LCU-LOOT] Claimed %d items: %v", len(claimed), claimed)
	return claimed
}

// --- Wails bindings: Lobby Scout & Customizer ---

// GetLobbyScout returns real-time teammate stats and grief risk during Champion Select.
func (a *App) GetLobbyScout() *LobbyScoutReport {
	client, err := NewLCUClient()
	if err != nil {
		return &LobbyScoutReport{
			InChampSelect: false,
			Phase:         "LCU_DISCONNECTED",
			LastUpdated:   time.Now().Format("15:04:05"),
		}
	}
	report, err := client.GetLobbyScoutReport()
	if err != nil {
		return &LobbyScoutReport{
			InChampSelect: false,
			Phase:         "SCOUT_ERROR",
			LastUpdated:   time.Now().Format("15:04:05"),
		}
	}
	return report
}

// DodgeLobby drops the active champion select queue.
func (a *App) DodgeLobby() string {
	client, err := NewLCUClient()
	if err != nil {
		return "League Client not running"
	}
	if err := client.DodgeLobby(); err != nil {
		return err.Error()
	}
	return "ok"
}

// SetCustomLobbyStatus sets the status message in League chat.
func (a *App) SetCustomLobbyStatus(msg string) string {
	client, err := NewLCUClient()
	if err != nil {
		return "League Client not running"
	}
	if err := client.SetCustomLobbyStatus(msg); err != nil {
		return err.Error()
	}
	return "ok"
}

// SetRegaliaProfile updates client-side rank badge and title.
func (a *App) SetRegaliaProfile(banner, crest string) string {
	client, err := NewLCUClient()
	if err != nil {
		return "League Client not running"
	}
	if err := client.SetRegaliaProfile(banner, crest); err != nil {
		return err.Error()
	}
	return "ok"
}

// --- Wails bindings: Config Switcher & Profiles ---

// GetConfigProfiles returns all available pro presets and saved profiles.
func (a *App) GetConfigProfiles() []ConfigProfileInfo {
	return GetConfigManager().ListProfiles()
}

// SaveCurrentConfigProfile backs up current game settings into a profile.
func (a *App) SaveCurrentConfigProfile(name, description string) string {
	err := GetConfigManager().SaveCurrentProfile(name, description)
	if err != nil {
		return err.Error()
	}
	return "ok"
}

// ApplyConfigProfile restores the chosen profile into active League config.
func (a *App) ApplyConfigProfile(profileName string) string {
	err := GetConfigManager().ApplyProfile(profileName)
	if err != nil {
		return err.Error()
	}
	return "ok"
}

// SetAutoConfigSync enables or disables auto-restore upon account switch.
func (a *App) SetAutoConfigSync(enabled bool, profileName string) string {
	cm := GetConfigManager()
	if enabled {
		cm.StartAutoSyncDaemon(profileName)
	} else {
		cm.StopAutoSyncDaemon()
	}
	return "ok"
}

// GetAutoConfigSyncStatus returns auto sync status and active profile.
func (a *App) GetAutoConfigSyncStatus() map[string]interface{} {
	cm := GetConfigManager()
	return map[string]interface{}{
		"enabled":        cm.IsAutoSyncEnabled(),
		"active_profile": cm.activeProfile,
		"read_only":      cm.IsReadOnly(),
	}
}

// ToggleConfigReadOnly write-protects or unlocks PersistedSettings.json.
func (a *App) ToggleConfigReadOnly(readOnly bool) string {
	err := GetConfigManager().SetReadOnly(readOnly)
	if err != nil {
		return err.Error()
	}
	return "ok"
}

// --- Wails bindings: Event Sentinel & Critical Prompts ---

// GetActiveCriticalPrompt returns any pending urgent prompt requiring user decision.
func (a *App) GetActiveCriticalPrompt() *CriticalPrompt {
	if a.sentinel == nil {
		return nil
	}
	return a.sentinel.GetActivePrompt()
}

// ResolveCriticalPrompt applies or dismisses user consent on a critical prompt.
func (a *App) ResolveCriticalPrompt(promptID string, approve bool) string {
	if a.sentinel == nil {
		return "sentinel_inactive"
	}
	return a.sentinel.ResolvePrompt(promptID, approve)
}

// PurgeSystemTraces runs silent log, crashpad and cache sanitization on demand.
func (a *App) PurgeSystemTraces() string {
	if a.sentinel != nil {
		a.sentinel.PurgeTelemetryAndCrashpads()
	}
	return "ok"
}

func sleepOrStop(stopCh chan struct{}, ms int) {
	select {
	case <-stopCh:
	case <-time.After(time.Duration(ms) * time.Millisecond):
	}
}

func sleepMs(ms int) {
	time.Sleep(time.Duration(ms) * time.Millisecond)
}

func (a *App) logDebug(format string, args ...interface{}) {
	line := time.Now().Format("15:04:05.000") + " " + fmt.Sprintf(format, args...)
	a.debugMu.Lock()
	logDir := os.Getenv("LOCALAPPDATA")
	if logDir == "" {
		logDir = os.TempDir()
	} else {
		logDir = filepath.Join(logDir, "Vanta", "Logs")
	}
	_ = os.MkdirAll(logDir, 0755)
	f, _ := os.OpenFile(filepath.Join(logDir, "vanta_debug.txt"), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(line + "\n")
		f.Close()
	}
	a.debugMu.Unlock()
}

func (a *App) flushLogs() {
	a.debugMu.Lock()
	lines := a.debugLog
	a.debugLog = nil
	a.debugMu.Unlock()

	if len(lines) == 0 {
		return
	}
	_ = lines
}

// FindRiotClientServices is defined per-platform in launcher_*.go
// terminateRiotServices is defined per-platform in process_*.go
// StopVanguard, IsVanguardRunning are in vanguard_*.go
