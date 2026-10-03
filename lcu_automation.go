package main

import (
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

var (
	activeLCUMu    sync.RWMutex
	activeLCUPort  string
	activeLCUToken string
)

// SetActiveLCU stores the running League Client LCU port and token for instant in-process access.
func SetActiveLCU(port string, token string) {
	activeLCUMu.Lock()
	defer activeLCUMu.Unlock()
	activeLCUPort = strings.TrimSpace(port)
	activeLCUToken = strings.Trim(strings.TrimSpace(token), "\"' ")
}

// GetActiveLCU retrieves the cached active LCU credentials.
func GetActiveLCU() (string, string) {
	activeLCUMu.RLock()
	defer activeLCUMu.RUnlock()
	return activeLCUPort, activeLCUToken
}

// ClearActiveLCU wipes the in-memory LCU credentials upon session termination.
func ClearActiveLCU() {
	activeLCUMu.Lock()
	defer activeLCUMu.Unlock()
	activeLCUPort = ""
	activeLCUToken = ""
}

// LCUClient manages communication with the local League Client UX REST API.
type LCUClient struct {
	port       string
	password   string
	httpClient *http.Client
	authHeader string
	active     bool
	mu         sync.Mutex
}

// NewLCUClient discovers the active League Client LCU credentials (in-memory or lockfile) and initializes an authenticated HTTPS client.
func NewLCUClient() (*LCUClient, error) {
	port, pass := GetActiveLCU()
	if port == "" || pass == "" {
		p, ps, err := findLeagueLockfile()
		if err != nil {
			return nil, err
		}
		port = p
		pass = ps
	}

	auth := base64.StdEncoding.EncodeToString([]byte("riot:" + pass))

	client := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
		Timeout: 4 * time.Second,
	}

	return &LCUClient{
		port:       port,
		password:   pass,
		httpClient: client,
		authHeader: "Basic " + auth,
		active:     true,
	}, nil
}

func findLeagueLockfile() (port string, pass string, err error) {
	possibleRoots := []string{
		`C:\Riot Games\League of Legends`,
		`C:\Program Files\Riot Games\League of Legends`,
		`C:\Program Files (x86)\Riot Games\League of Legends`,
		`D:\Riot Games\League of Legends`,
		`E:\Riot Games\League of Legends`,
		`F:\Riot Games\League of Legends`,
		`G:\Riot Games\League of Legends`,
		`/Applications/League of Legends.app/Contents/LoL`,
	}

	for _, root := range possibleRoots {
		lockPath := filepath.Join(root, "lockfile")
		data, err := os.ReadFile(lockPath)
		if err == nil {
			parts := strings.Split(strings.TrimSpace(string(data)), ":")
			if len(parts) >= 4 {
				// Format: LeagueClient:pid:port:password:https
				return parts[2], parts[3], nil
			}
		}
	}

	return "", "", fmt.Errorf("League Client lockfile not found (Game lobby not running)")
}

// GetGameflowPhase returns the current LCU gameflow phase (e.g. "None", "Lobby", "Matchmaking", "ReadyCheck", "ChampSelect", "InProgress", "WaitingForStats", "EndOfGame").
func (l *LCUClient) GetGameflowPhase() (string, error) {
	data, code, err := l.Request("GET", "/lol-gameflow/v1/gameflow-phase", nil)
	if err != nil {
		return "", err
	}
	if code != 200 {
		return "", fmt.Errorf("gameflow-phase status: %d", code)
	}
	var phase string
	if err := json.Unmarshal(data, &phase); err != nil {
		return strings.Trim(string(data), "\"' \r\n"), nil
	}
	return phase, nil
}

// Request executes an authenticated HTTP request to the LCU API.
func (l *LCUClient) Request(method, endpoint string, body io.Reader) ([]byte, int, error) {
	url := fmt.Sprintf("https://127.0.0.1:%s%s", l.port, endpoint)
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, 0, err
	}

	req.Header.Set("Authorization", l.authHeader)
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Content-Type", "application/json")

	resp, err := l.httpClient.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()

	respData, err := io.ReadAll(resp.Body)
	return respData, resp.StatusCode, err
}

// AutoAcceptReadyCheck automatically clicks the Matchmaking Ready Check Accept button.
func (l *LCUClient) AutoAcceptReadyCheck() error {
	_, code, err := l.Request("POST", "/lol-matchmaking/v1/ready-check/accept", nil)
	if err != nil {
		return err
	}
	if code >= 200 && code < 300 {
		return nil
	}
	return fmt.Errorf("accept status: %d", code)
}

// ClaimTutorialRewards crafts/claims tutorial and level up capsules automatically.
func (l *LCUClient) ClaimTutorialRewards() ([]string, error) {
	data, code, err := l.Request("GET", "/lol-loot/v1/player-loot", nil)
	if err != nil || code != 200 {
		return nil, fmt.Errorf("failed to fetch loot: %v", err)
	}

	var items []map[string]interface{}
	if err := json.Unmarshal(data, &items); err != nil {
		return nil, err
	}

	var claimed []string
	for _, item := range items {
		lootName, _ := item["lootName"].(string)
		if strings.Contains(strings.ToLower(lootName), "capsule") || strings.Contains(strings.ToLower(lootName), "chest") || strings.Contains(strings.ToLower(lootName), "tutorial") {
			repeat := 1
			craftBody := fmt.Sprintf(`{"repeat": %d}`, repeat)
			_, craftCode, _ := l.Request("POST", fmt.Sprintf("/lol-loot/v1/recipes/%s_OPEN/craft?repeat=%d", lootName, repeat), strings.NewReader(craftBody))
			if craftCode >= 200 && craftCode < 300 {
				claimed = append(claimed, lootName)
			}
		}
	}

	return claimed, nil
}

// StartAutoAcceptDaemon runs in a background goroutine polling for queue pop.
func StartAutoAcceptDaemon(stopCh chan struct{}, logger func(string, ...interface{})) {
	go func() {
		ticker := time.NewTicker(800 * time.Millisecond)
		defer ticker.Stop()

		var client *LCUClient
		if logger != nil {
			logger("[LCU-AUTO] Auto-Accept daemon running")
		}

		for {
			select {
			case <-stopCh:
				if logger != nil {
					logger("[LCU-AUTO] Auto-Accept daemon stopped")
				}
				return
			case <-ticker.C:
				if client == nil {
					c, err := NewLCUClient()
					if err == nil {
						client = c
						if logger != nil {
							logger("[LCU-AUTO] Connected to League Client LCU (port %s)", client.port)
						}
					}
					continue
				}

				// Check ready check status
				resp, code, err := client.Request("GET", "/lol-matchmaking/v1/ready-check", nil)
				if err != nil || code == 401 || code == 403 {
					// Network disconnect or credential rotated
					client = nil
					continue
				}

				// HTTP 404 is normal idle state when not in matchmaking/ready-check.
				// Process if status is 200 OK.
				accepted := false
				if code == 200 && len(resp) > 0 {
					var status map[string]interface{}
					if json.Unmarshal(resp, &status) == nil {
						state, _ := status["state"].(string)
						playerResponse, _ := status["playerResponse"].(string)
						if (state == "InProgress" || state == "ReadyCheck") && playerResponse != "Accepted" {
							for attempt := 1; attempt <= 3; attempt++ {
								if err := client.AutoAcceptReadyCheck(); err == nil {
									accepted = true
									if logger != nil {
										logger("[LCU-AUTO] Match found! Auto-accepted ready check (attempt %d).", attempt)
									}
									ReportGlobalTelemetry("INFO", "AUTO_ACCEPT", "Match found! Auto-accepted ready check", "", nil)
									break
								}
								time.Sleep(150 * time.Millisecond)
							}
						}
					}
				}

				if !accepted {
					// Secondary fallback check: LCU Gameflow phase
					phase, pErr := client.GetGameflowPhase()
					if pErr == nil && (phase == "ReadyCheck" || strings.EqualFold(phase, "readycheck")) {
						for attempt := 1; attempt <= 3; attempt++ {
							if err := client.AutoAcceptReadyCheck(); err == nil {
								if logger != nil {
									logger("[LCU-AUTO] Match found (via gameflow)! Auto-accepted ready check (attempt %d).", attempt)
								}
								ReportGlobalTelemetry("INFO", "AUTO_ACCEPT", "Match found via gameflow! Auto-accepted ready check", "", nil)
								break
							}
							time.Sleep(150 * time.Millisecond)
						}
					}
				}

				// 2. Check Champion Select Automation (Auto-Pick, Auto-Ban & Instant Runes)
				rule := GetActiveChampSelectRule()
				if rule.AutoPickEnabled || rule.AutoBanEnabled {
					_ = client.HandleChampSelectAutomation(rule, logger)
				}
			}
		}
	}()
}

// ChampSelectRule specifies champion preferences for pick/ban automation.
type ChampSelectRule struct {
	AutoPickEnabled bool `json:"auto_pick_enabled"`
	PickChampionID  int  `json:"pick_champion_id"`
	AutoBanEnabled  bool `json:"auto_ban_enabled"`
	BanChampionID   int  `json:"ban_champion_id"`
	AutoRunes       bool `json:"auto_runes"`
}

var (
	champSelectRuleMu     sync.RWMutex
	activeChampSelectRule ChampSelectRule
)

// SetActiveChampSelectRule updates the active pick/ban automation rule.
func SetActiveChampSelectRule(r ChampSelectRule) {
	champSelectRuleMu.Lock()
	defer champSelectRuleMu.Unlock()
	activeChampSelectRule = r
}

// GetActiveChampSelectRule retrieves the active pick/ban automation rule.
func GetActiveChampSelectRule() ChampSelectRule {
	champSelectRuleMu.RLock()
	defer champSelectRuleMu.RUnlock()
	return activeChampSelectRule
}

// HandleChampSelectAutomation checks active pick/ban actions and executes them instantly.
func (l *LCUClient) HandleChampSelectAutomation(rule ChampSelectRule, logger func(string, ...interface{})) error {
	sessionData, code, err := l.Request("GET", "/lol-champ-select/v1/session", nil)
	if err != nil || code != 200 {
		return nil
	}

	var session map[string]interface{}
	if err := json.Unmarshal(sessionData, &session); err != nil {
		return err
	}

	localCellId, ok := session["localPlayerCellId"].(float64)
	if !ok {
		return nil
	}
	myCell := int(localCellId)

	actionsRaw, ok := session["actions"].([]interface{})
	if !ok {
		return nil
	}

	for _, blockRaw := range actionsRaw {
		blockList, ok := blockRaw.([]interface{})
		if !ok {
			continue
		}
		for _, actionRaw := range blockList {
			action, ok := actionRaw.(map[string]interface{})
			if !ok {
				continue
			}

			actorCellId, ok := action["actorCellId"].(float64)
			if !ok || int(actorCellId) != myCell {
				continue
			}

			completed, _ := action["completed"].(bool)
			isInProgress, _ := action["isInProgress"].(bool)
			if completed || !isInProgress {
				continue
			}

			actionId := int(action["id"].(float64))
			actionType, _ := action["type"].(string) // "pick" or "ban"

			if actionType == "ban" && rule.AutoBanEnabled && rule.BanChampionID > 0 {
				body := fmt.Sprintf(`{"championId": %d, "completed": true}`, rule.BanChampionID)
				_, pCode, pErr := l.Request("PATCH", fmt.Sprintf("/lol-champ-select/v1/session/actions/%d", actionId), strings.NewReader(body))
				if pErr == nil && pCode >= 200 && pCode < 300 {
					if logger != nil {
						logger("[CHAMP-SELECT] Auto-banned %s (ID %d)", getChampionNameByID(rule.BanChampionID), rule.BanChampionID)
					}
					ReportGlobalTelemetry("INFO", "CHAMP_SELECT", "Auto-banned champion", fmt.Sprintf("champ_id=%d", rule.BanChampionID), nil)
				}
			} else if actionType == "pick" && rule.AutoPickEnabled && rule.PickChampionID > 0 {
				body := fmt.Sprintf(`{"championId": %d, "completed": true}`, rule.PickChampionID)
				_, pCode, pErr := l.Request("PATCH", fmt.Sprintf("/lol-champ-select/v1/session/actions/%d", actionId), strings.NewReader(body))
				if pErr == nil && pCode >= 200 && pCode < 300 {
					if logger != nil {
						logger("[CHAMP-SELECT] Auto-picked & locked %s (ID %d)", getChampionNameByID(rule.PickChampionID), rule.PickChampionID)
					}
					ReportGlobalTelemetry("INFO", "CHAMP_SELECT", "Auto-picked champion", fmt.Sprintf("champ_id=%d", rule.PickChampionID), nil)

					if rule.AutoRunes {
						_ = l.ApplyMetaRunes(rule.PickChampionID)
						if logger != nil {
							logger("[CHAMP-SELECT] Injected ProBuild meta runes for %s", getChampionNameByID(rule.PickChampionID))
						}
					}
				}
			}
		}
	}

	return nil
}

// --- VANTA APEX V6: LOBBY REVEALER, AUTO-DODGER & REGALIA ENGINE ---

// LobbyTeammate holds revealed player info during Champion Select.
type LobbyTeammate struct {
	PUUID          string  `json:"puuid"`
	SummonerName   string  `json:"summoner_name"`
	TagLine        string  `json:"tag_line"`
	AssignedRole   string  `json:"assigned_role"`
	ChampionID     int     `json:"champion_id"`
	ChampionName   string  `json:"champion_name"`
	RecentWinrate  float64 `json:"recent_winrate"`
	RecentGames    int     `json:"recent_games"`
	RecentWins     int     `json:"recent_wins"`
	Streak         int     `json:"streak"` // positive for win streak, negative for loss streak
	GriefRiskLevel string  `json:"grief_risk_level"` // "LOW", "MEDIUM", "HIGH", "CRITICAL"
}

// LobbyScoutReport aggregates all teammate analyses.
type LobbyScoutReport struct {
	InChampSelect    bool            `json:"in_champ_select"`
	Phase            string          `json:"phase"`
	GriefScore       int             `json:"grief_score"` // 0-100%
	DodgeRecommended bool            `json:"dodge_recommended"`
	Teammates        []LobbyTeammate `json:"teammates"`
	LastUpdated      string          `json:"last_updated"`
}

// GetLobbyScoutReport analyzes the active Champion Select lobby.
func (l *LCUClient) GetLobbyScoutReport() (*LobbyScoutReport, error) {
	// 1. Check if in Champion Select
	sessionData, code, err := l.Request("GET", "/lol-champ-select/v1/session", nil)
	if err != nil || code != 200 {
		return &LobbyScoutReport{
			InChampSelect: false,
			Phase:         "NOT_IN_CHAMP_SELECT",
			LastUpdated:   time.Now().Format("15:04:05"),
		}, nil
	}

	var session map[string]interface{}
	if err := json.Unmarshal(sessionData, &session); err != nil {
		return nil, err
	}

	// 2. Unmask names via LCU Chat participants
	chatData, chatCode, _ := l.Request("GET", "/chat/v5/participants", nil)
	puuidMap := make(map[string]map[string]string)
	if chatCode == 200 {
		var chatResp map[string]interface{}
		if json.Unmarshal(chatData, &chatResp) == nil {
			if participants, ok := chatResp["participants"].([]interface{}); ok {
				for _, p := range participants {
					if pm, ok := p.(map[string]interface{}); ok {
						cid, _ := pm["cid"].(string)
						if strings.Contains(cid, "champ-select") || strings.Contains(cid, "rcp-fe-lol") {
							puuid, _ := pm["puuid"].(string)
							gName, _ := pm["game_name"].(string)
							gTag, _ := pm["game_tag"].(string)
							if puuid != "" {
								puuidMap[puuid] = map[string]string{
									"name": gName,
									"tag":  gTag,
								}
							}
						}
					}
				}
			}
		}
	}

	// 3. Parse teammates from myTeam
	var teammates []LobbyTeammate
	griefPoints := 0

	if myTeam, ok := session["myTeam"].([]interface{}); ok {
		for _, member := range myTeam {
			if mm, ok := member.(map[string]interface{}); ok {
				puuid, _ := mm["puuid"].(string)
				cellId := int(mm["cellId"].(float64))
				champId := 0
				if cid, ok := mm["championId"].(float64); ok {
					champId = int(cid)
				}
				role, _ := mm["assignedPosition"].(string)
				if role == "" {
					role = "FILL"
				}

				name := fmt.Sprintf("Ally %d", cellId)
				tag := "RIOT"
				if info, found := puuidMap[puuid]; found && info["name"] != "" {
					name = info["name"]
					tag = info["tag"]
				}

				// Query recent match history if PUUID available
				winrate := 50.0
				games := 0
				wins := 0
				streak := 0
				risk := "LOW"

				if puuid != "" {
					histData, histCode, err := l.Request("GET", fmt.Sprintf("/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=5", puuid), nil)
					if err == nil && histCode == 200 {
						var hist map[string]interface{}
						if json.Unmarshal(histData, &hist) == nil {
							if gamesObj, ok := hist["games"].(map[string]interface{}); ok {
								if gameList, ok := gamesObj["games"].([]interface{}); ok {
									games = len(gameList)
									streakCalculated := false
									for _, g := range gameList {
										if gm, ok := g.(map[string]interface{}); ok {
											// Check participant win status
											if parts, ok := gm["participants"].([]interface{}); ok {
												for _, p := range parts {
													if pm, ok := p.(map[string]interface{}); ok {
														if stats, ok := pm["stats"].(map[string]interface{}); ok {
															if isWin, ok := stats["win"].(bool); ok {
																if isWin {
																	wins++
																	if !streakCalculated {
																		if streak >= 0 {
																			streak++
																		} else {
																			streakCalculated = true
																		}
																	}
																} else {
																	if !streakCalculated {
																		if streak <= 0 {
																			streak--
																		} else {
																			streakCalculated = true
																		}
																	}
																}
															}
														}
													}
												}
											}
										}
									}
									if games > 0 {
										winrate = (float64(wins) / float64(games)) * 100.0
									}
								}
							}
						}
					}
				}

				// Evaluate risk
				if streak <= -3 || winrate < 30.0 {
					risk = "CRITICAL"
					griefPoints += 35
				} else if streak <= -2 || winrate < 45.0 {
					risk = "HIGH"
					griefPoints += 20
				} else if winrate < 50.0 {
					risk = "MEDIUM"
					griefPoints += 10
				}

				teammates = append(teammates, LobbyTeammate{
					PUUID:          puuid,
					SummonerName:   name,
					TagLine:        tag,
					AssignedRole:   strings.ToUpper(role),
					ChampionID:     champId,
					ChampionName:   getChampionNameByID(champId),
					RecentWinrate:  winrate,
					RecentGames:    games,
					RecentWins:     wins,
					Streak:         streak,
					GriefRiskLevel: risk,
				})
			}
		}
	}

	if griefPoints > 100 {
		griefPoints = 100
	}

	return &LobbyScoutReport{
		InChampSelect:    true,
		Phase:            "CHAMP_SELECT_SCOUTED",
		GriefScore:       griefPoints,
		DodgeRecommended: griefPoints >= 50,
		Teammates:        teammates,
		LastUpdated:      time.Now().Format("15:04:05"),
	}, nil
}

// DodgeLobby sends the LCDS quit command or gracefully terminates champ select queue.
func (l *LCUClient) DodgeLobby() error {
	// Attempt LCU LCDS quitV2 invocation
	body := strings.NewReader(`["","teambuilder-draft","quitV2",""]`)
	_, code, err := l.Request("POST", "/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&args=[\"\",\"teambuilder-draft\",\"quitV2\",\"\"]", body)
	if err == nil && code >= 200 && code < 300 {
		return nil
	}

	// Fallback: Drop match queue via gameflow
	_, fCode, fErr := l.Request("POST", "/lol-lobby/v1/lobby/matchmaking/stop", nil)
	if fErr == nil && fCode >= 200 && fCode < 300 {
		return nil
	}

	return fmt.Errorf("queue dodge requested (handled via LCU dispatch)")
}

// SetCustomLobbyStatus updates the player's status message in League chat.
func (l *LCUClient) SetCustomLobbyStatus(msg string) error {
	body := fmt.Sprintf(`{"statusMessage": "%s"}`, msg)
	_, code, err := l.Request("PUT", "/lol-chat/v1/me", strings.NewReader(body))
	if err != nil || code < 200 || code >= 300 {
		return fmt.Errorf("failed to update status message: code %d", code)
	}
	return nil
}

// SetRegaliaProfile updates client-side rank badge and title.
func (l *LCUClient) SetRegaliaProfile(bannerType, crestType string) error {
	body := fmt.Sprintf(`{"preferredBannerType": "%s", "preferredCrestType": "%s"}`, bannerType, crestType)
	_, code, err := l.Request("PUT", "/lol-regalia/v2/current-summoner/regalia", strings.NewReader(body))
	if err != nil || code < 200 || code >= 300 {
		return fmt.Errorf("failed to set regalia: code %d", code)
	}
	return nil
}

// DismissEndOfGame clears stuck end-of-game screens and returns LeagueClient to lobby.
func (l *LCUClient) DismissEndOfGame() error {
	_, _, _ = l.Request("POST", "/lol-end-of-game/v1/state/dismiss-stats", strings.NewReader("{}"))
	_, _, _ = l.Request("POST", "/lol-end-of-game/v1/dismiss-stats", strings.NewReader("{}"))
	_, _, _ = l.Request("POST", "/lol-gameflow/v1/pre-end-of-game", strings.NewReader("{}"))
	_, _, _ = l.Request("POST", "/lol-gameflow/v1/ack", strings.NewReader("{}"))
	_, _, _ = l.Request("POST", "/lol-gameflow/v1/session/request-lobby", strings.NewReader("{}"))
	return nil
}

func getChampionNameByID(id int) string {
	known := map[int]string{
		1: "Annie", 22: "Ashe", 11: "Master Yi", 86: "Garen", 222: "Jinx",
		157: "Yasuo", 238: "Zed", 67: "Vayne", 64: "Lee Sin", 103: "Ahri",
		89: "Leona", 412: "Thresh", 134: "Syndra", 81: "Ezreal", 51: "Caitlyn",
	}
	if name, ok := known[id]; ok {
		return name
	}
	if id > 0 {
		return fmt.Sprintf("Champion #%d", id)
	}
	return "Selecting..."
}

// RunePagePayload represents an LCU perk page.
type RunePagePayload struct {
	Name            string `json:"name"`
	PrimaryStyleId  int    `json:"primaryStyleId"`
	SubStyleId      int    `json:"subStyleId"`
	SelectedPerkIds []int  `json:"selectedPerkIds"`
	Current         bool   `json:"current"`
	IsValid         bool   `json:"isValid"`
}

// ApplyMetaRunes sets optimal pro runes for the given champion directly via LCU in 5ms.
func (l *LCUClient) ApplyMetaRunes(champId int) error {
	primaryStyle, subStyle, perks := getMetaRunesForChamp(champId)

	// 1. Get existing pages to delete old custom pages
	data, code, err := l.Request("GET", "/lol-perks/v1/pages", nil)
	if err == nil && code == 200 {
		var pages []map[string]interface{}
		if json.Unmarshal(data, &pages) == nil {
			for _, p := range pages {
				isDeletable, _ := p["isDeletable"].(bool)
				pageId, _ := p["id"].(float64)
				if isDeletable && pageId > 0 {
					_, _, _ = l.Request("DELETE", fmt.Sprintf("/lol-perks/v1/pages/%.0f", pageId), nil)
				}
			}
		}
	}

	// 2. Create new optimized perk page
	newPage := RunePagePayload{
		Name:            fmt.Sprintf("VANTA Pro: %s", getChampionNameByID(champId)),
		PrimaryStyleId:  primaryStyle,
		SubStyleId:      subStyle,
		SelectedPerkIds: perks,
		Current:         true,
		IsValid:         true,
	}

	body, err := json.Marshal(newPage)
	if err != nil {
		return err
	}
	_, postCode, postErr := l.Request("POST", "/lol-perks/v1/pages", strings.NewReader(string(body)))
	if postErr != nil || postCode >= 300 {
		return fmt.Errorf("failed to create rune page: status %d", postCode)
	}
	return nil
}

func getMetaRunesForChamp(champId int) (int, int, []int) {
	// 8000: Precision, 8100: Domination, 8200: Sorcery, 8300: Inspiration, 8400: Resolve
	switch champId {
	case 222, 67, 81, 22, 51: // ADC Archetype (Jinx, Vayne, Ezreal, Ashe, Caitlyn)
		return 8000, 8100, []int{8008, 9111, 9104, 8014, 8139, 8135, 5005, 5008, 5003}
	case 157, 11, 86: // Yasuo, Master Yi, Garen: Conqueror
		return 8000, 8400, []int{8010, 9111, 9104, 8299, 8444, 8451, 5005, 5008, 5002}
	case 238, 64: // Assassin / Skirmisher (Zed, Lee Sin)
		return 8100, 8000, []int{8112, 8143, 8138, 8106, 8009, 8014, 5008, 5008, 5002}
	case 103, 134, 1: // Mage (Ahri, Syndra, Annie)
		return 8100, 8200, []int{8112, 8143, 8138, 8106, 8226, 8236, 5008, 5008, 5003}
	case 89, 412: // Support Tank (Leona, Thresh)
		return 8400, 8300, []int{8439, 8401, 8444, 8242, 8306, 8345, 5007, 5002, 5002}
	default: // Universal Balanced
		return 8000, 8100, []int{8010, 9111, 9104, 8014, 8139, 8135, 5008, 5008, 5002}
	}
}

