package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// CriticalPrompt represents an urgent decision that requires explicit user consent.
type CriticalPrompt struct {
	ID          string            `json:"id"`
	Type        string            `json:"type"` // "DODGE_SUGGESTION", "CRASH_RECONNECT", "CONFIG_SYNC"
	Title       string            `json:"title"`
	Message     string            `json:"message"`
	ActionLabel string            `json:"action_label"`
	CancelLabel string            `json:"cancel_label"`
	ExpiresAt   int64             `json:"expires_at"` // Unix timestamp in seconds
	DurationSec int               `json:"duration_sec"`
	GriefScore  int               `json:"grief_score,omitempty"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

// EventSentinel manages background state tracking and gates critical decisions behind user prompts.
type EventSentinel struct {
	app              *App
	mu               sync.Mutex
	activePrompt     *CriticalPrompt
	dismissedPhases  map[string]bool
	stopCh           chan struct{}
	isRunning        bool
	lastGameRunning  bool
	lastGameCrashAt  time.Time
}

// NewEventSentinel instantiates the autonomous monitor.
func NewEventSentinel(app *App) *EventSentinel {
	return &EventSentinel{
		app:             app,
		dismissedPhases: make(map[string]bool),
		stopCh:          make(chan struct{}),
	}
}

// Start launches the sentinel daemon loop in a background goroutine.
func (s *EventSentinel) Start() {
	s.mu.Lock()
	if s.isRunning {
		s.mu.Unlock()
		return
	}
	s.isRunning = true
	s.stopCh = make(chan struct{})
	s.mu.Unlock()

	go s.daemonLoop()
}

// Stop cleanly terminates the daemon.
func (s *EventSentinel) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.isRunning {
		return
	}
	s.isRunning = false
	close(s.stopCh)
}

// GetActivePrompt returns the current pending critical prompt, if not expired.
func (s *EventSentinel) GetActivePrompt() *CriticalPrompt {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.activePrompt == nil {
		return nil
	}

	if time.Now().Unix() > s.activePrompt.ExpiresAt {
		s.activePrompt = nil
		return nil
	}

	return s.activePrompt
}

// ResolvePrompt handles user approval or dismissal of an active prompt.
func (s *EventSentinel) ResolvePrompt(promptID string, approve bool) string {
	s.mu.Lock()
	prompt := s.activePrompt
	if prompt == nil || prompt.ID != promptID {
		s.mu.Unlock()
		return "prompt_expired_or_not_found"
	}
	s.activePrompt = nil
	s.mu.Unlock()

	if !approve {
		// User chose to stay / dismiss risk
		if prompt.Type == "DODGE_SUGGESTION" {
			s.mu.Lock()
			s.dismissedPhases["current_champ_select"] = true
			s.mu.Unlock()
		} else if prompt.Type == "CRASH_RECONNECT" {
			s.app.logDebug("[SENTINEL] User chose to return to lobby - concluding match")
			s.app.ConcludeMatch()
		}
		return "dismissed"
	}

	// Action Approved by user
	switch prompt.Type {
	case "DODGE_SUGGESTION":
		client, err := NewLCUClient()
		if err != nil {
			return "lcu_unavailable"
		}
		if err := client.DodgeLobby(); err != nil {
			return "dodge_failed: " + err.Error()
		}
		s.app.logDebug("[SENTINEL] User approved dodge - lobby successfully dropped")
		return "dodge_executed"

	case "CRASH_RECONNECT":
		s.app.logDebug("[SENTINEL] User approved crash reconnect - relaunching 3D engine")
		res := s.app.ReconnectGame()
		s.app.logDebug("[SENTINEL] Reconnect result: %s", res)
		if res == "ok" {
			return "reconnect_executed"
		}
		return res

	case "CONFIG_SYNC":
		targetProfile := prompt.Metadata["profile"]
		if targetProfile != "" {
			_ = s.app.ApplyConfigProfile(targetProfile)
			s.app.logDebug("[SENTINEL] User approved config sync to %s", targetProfile)
			return "config_synced"
		}
	}

	return "ok"
}

// daemonLoop runs periodic checks every 1.5 seconds.
func (s *EventSentinel) daemonLoop() {
	ticker := time.NewTicker(1500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.stopCh:
			return
		case <-ticker.C:
			s.tick()
		}
	}
}

func (s *EventSentinel) tick() {
	// 1. Clear expired prompt
	s.mu.Lock()
	if s.activePrompt != nil && time.Now().Unix() > s.activePrompt.ExpiresAt {
		s.activePrompt = nil
	}
	s.mu.Unlock()

	// 2. Monitor Game Process Lifecycle (Silent Purge & Crash Detection)
	gameRunning := isLeagueGameRunning()

	// Transition: Game was running -> now stopped
	if s.lastGameRunning && !gameRunning {
		// Run silent telemetry purge immediately without user prompt
		go s.PurgeTelemetryAndCrashpads()

		// Check if this was an unexpected crash during an active match
		s.app.mu.Lock()
		activeSlot := s.app.activeSlotID
		hasGameArgs := len(s.app.lastGameArgs) > 0
		s.app.mu.Unlock()

		if activeSlot != "" && hasGameArgs {
			shouldPrompt := false
			if client, err := NewLCUClient(); err == nil {
				phase, pErr := client.GetGameflowPhase()
				if pErr == nil && (phase == "InProgress" || phase == "Reconnect") {
					shouldPrompt = true
				}
			}

			if shouldPrompt {
				if time.Since(s.lastGameCrashAt) > 10*time.Second {
					s.lastGameCrashAt = time.Now()
					s.app.logDebug("[SENTINEL] Game exited while gameflow is InProgress - prompting user to reconnect")
					s.triggerPrompt(&CriticalPrompt{
						ID:          fmt.Sprintf("reconnect_%d", time.Now().Unix()),
						Type:        "CRASH_RECONNECT",
						Title:       "Match Still In Progress",
						Message:     "League of Legends exited while your match is still ongoing. Would you like to reconnect?",
						ActionLabel: "Reconnect Now",
						CancelLabel: "Back to Lobby",
						ExpiresAt:   time.Now().Add(25 * time.Second).Unix(),
						DurationSec: 25,
					})
				}
			} else {
				// Normal match conclusion: conclude slot and reset state cleanly
				s.app.ConcludeMatch()
			}
		}
	}
	s.lastGameRunning = gameRunning

	// If 3D Game is running, pause LCU polling to keep WAN tunnel 100% clean for game and companion
	if gameRunning {
		return
	}

	// 3. Monitor LCU Champion Select for Grief Risk (Prompt only, never auto-dodge without consent)
	client, err := NewLCUClient()
	if err == nil {
		report, err := client.GetLobbyScoutReport()
		if err == nil && report.InChampSelect {
			if report.DodgeRecommended || report.GriefScore >= 50 {
				s.mu.Lock()
				alreadyDismissed := s.dismissedPhases["current_champ_select"]
				hasPrompt := s.activePrompt != nil
				s.mu.Unlock()

				if !alreadyDismissed && !hasPrompt {
					worstReason := "High loss / grief probability"
					for _, tm := range report.Teammates {
						if tm.GriefRiskLevel == "HIGH" || tm.GriefRiskLevel == "CRITICAL" {
							worstReason = fmt.Sprintf("%s (%s - %.0f%% WR)", tm.AssignedRole, tm.SummonerName, tm.RecentWinrate)
							break
						}
					}

					s.triggerPrompt(&CriticalPrompt{
						ID:          fmt.Sprintf("dodge_%d", time.Now().Unix()),
						Type:        "DODGE_SUGGESTION",
						Title:       "High Grief Risk Detected",
						Message:     fmt.Sprintf("High risk teammate detected in lobby (%s, Risk Score: %d%%). Dodge match to protect LP?", worstReason, report.GriefScore),
						ActionLabel: "Dodge Lobby (Avoid Loss)",
						CancelLabel: "Stay in Lobby",
						ExpiresAt:   time.Now().Add(12 * time.Second).Unix(),
						DurationSec: 12,
						GriefScore:  report.GriefScore,
					})
				}
			}
		} else if err == nil && !report.InChampSelect {
			// Reset dismissal when out of champ select
			s.mu.Lock()
			delete(s.dismissedPhases, "current_champ_select")
			s.mu.Unlock()
		}
	}
}

func (s *EventSentinel) triggerPrompt(p *CriticalPrompt) {
	s.mu.Lock()
	defer s.mu.Unlock()
	// Only set if no higher priority prompt is active
	if s.activePrompt == nil || s.activePrompt.Type != "CRASH_RECONNECT" {
		s.activePrompt = p
		s.app.logDebug("[SENTINEL] Triggered critical prompt: %s (%s)", p.Title, p.Type)
	}
}

// PurgeTelemetryAndCrashpads silently removes Riot crashpad dumps, telemetry caches and logs.
func (s *EventSentinel) PurgeTelemetryAndCrashpads() {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		return
	}

	targets := []string{
		filepath.Join(localAppData, "Riot Games", "League of Legends", "Logs"),
		filepath.Join(localAppData, "Riot Games", "Crashpad", "reports"),
		filepath.Join(localAppData, "Riot Games", "Riot Client", "Logs"),
		filepath.Join(localAppData, "CrashDumps"),
	}

	for _, dir := range targets {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, entry := range entries {
			fullPath := filepath.Join(dir, entry.Name())
			_ = os.RemoveAll(fullPath)
		}
	}
	s.app.logDebug("[SENTINEL] Silent exit telemetry and crashpad purge completed.")
}
