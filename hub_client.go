package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	HubBaseURL         = "http://51.159.121.126:9000"
	OrchestratorBaseURL = "http://51.159.121.126:9000"
)

type AuthResponse struct {
	Success        bool   `json:"success"`
	Role           string `json:"role"`
	ExpiresAt      int64  `json:"expires_at"`
	M1Orchestrator string `json:"m1_orchestrator"`
	TicketData     string `json:"ticket_data"`
	Signature      string `json:"signature"`
	Envelope       string `json:"envelope"`
	Error          string `json:"error"`
}

type SlotResponse struct {
	Success   bool   `json:"success"`
	SlotID    string `json:"slot_id"`
	ProxyPort int    `json:"proxy_port"`
	LCUPort   int    `json:"lcu_port"`
	Error     string `json:"error"`
}

type VMStatusResponse struct {
	Status    string   `json:"status"`
	Args      []string `json:"args"`
	GameArgs  []string `json:"game_args"`
	ProxyPort int      `json:"proxy_port"`
	LCUPort   int      `json:"lcu_port"`
}

// HubClient interacts with the central M1 auth and orchestration nodes.
type HubClient struct {
	client *http.Client
}

func NewHubClient() *HubClient {
	return &HubClient{
		client: &http.Client{Timeout: 8 * time.Second},
	}
}

// AuthenticateLicense verifies the user key, binds/checks HWID, and cryptographically verifies server Ed25519 signature.
func (h *HubClient) AuthenticateLicense(licenseKey string) (*AuthResponse, error) {
	hwid := GetHWID()
	nonce := GenerateNonce()
	clientTs := time.Now().Unix()

	rawReq := map[string]interface{}{
		"license_key": licenseKey,
		"hwid":        hwid,
		"nonce":       nonce,
		"client_ts":   clientTs,
	}
	rawBytes, _ := json.Marshal(rawReq)

	// Encrypt request payload in AES-256-GCM envelope
	encPacket, err := EncryptEnvelope(rawBytes)
	var postBody []byte
	if err == nil {
		postBody, _ = json.Marshal(map[string]string{"envelope": encPacket})
	} else {
		postBody = rawBytes
	}

	resp, err := h.client.Post(HubBaseURL+"/api/client/auth", "application/json", bytes.NewReader(postBody))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to sovereign hub: %w", err)
	}
	defer resp.Body.Close()

	respBytes, _ := io.ReadAll(resp.Body)
	var authResp AuthResponse
	if err := json.Unmarshal(respBytes, &authResp); err != nil {
		return nil, fmt.Errorf("failed to parse auth response: %w", err)
	}

	// Decrypt envelope if server returned encrypted response
	if authResp.Envelope != "" {
		decBytes, err := DecryptEnvelope(authResp.Envelope)
		if err == nil {
			_ = json.Unmarshal(decBytes, &authResp)
		}
	}

	if !authResp.Success {
		return nil, fmt.Errorf("%s", authResp.Error)
	}

	// ── Cryptographic Ed25519 Signature Verification ──────────────────────────
	if authResp.TicketData == "" || authResp.Signature == "" {
		ReportGlobalTelemetry("CRITICAL", "AUTH_TAMPER", "Server omitted cryptographic attestation ticket", "", nil)
		return nil, fmt.Errorf("SECURITY ANOMALY: Server response missing cryptographic attestation")
	}

	ticket, err := VerifyServerTicket(authResp.TicketData, authResp.Signature, nonce)
	if err != nil {
		ReportGlobalTelemetry("CRITICAL", "AUTH_TAMPER", "Cryptographic signature verification failed", err.Error(), nil)
		return nil, fmt.Errorf("FORGERY DETECTED: %w", err)
	}

	if ticket.LicenseKey != licenseKey || ticket.HWID != hwid {
		ReportGlobalTelemetry("CRITICAL", "AUTH_TAMPER", "Ticket HWID/License mismatch", "", nil)
		return nil, fmt.Errorf("CRYPTOGRAPHIC INTEGRITY FAULT: Ticket does not match local device")
	}

	return &authResp, nil
}

// RequestSlot asks M1 Orchestrator for an isolated slot.
func (h *HubClient) RequestSlot(puuid string) (*SlotResponse, error) {
	payload := map[string]string{
		"puuid": puuid,
	}
	body, _ := json.Marshal(payload)

	resp, err := h.client.Post(OrchestratorBaseURL+"/slot/request", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("slot orchestrator unreachable: %w", err)
	}
	defer resp.Body.Close()

	respBytes, _ := io.ReadAll(resp.Body)
	var slotResp SlotResponse
	if err := json.Unmarshal(respBytes, &slotResp); err != nil {
		return nil, fmt.Errorf("failed to parse slot response: %w", err)
	}

	if !slotResp.Success {
		return nil, fmt.Errorf("%s", slotResp.Error)
	}

	return &slotResp, nil
}

// SendHeartbeat keeps the M1 slot alive.
func (h *HubClient) SendHeartbeat(slotID string) error {
	payload := map[string]string{"slot_id": slotID}
	body, _ := json.Marshal(payload)
	_, err := h.client.Post(OrchestratorBaseURL+"/slot/heartbeat", "application/json", bytes.NewReader(body))
	return err
}

// ReleaseSlot frees the M1 slot back into the idle pool.
func (h *HubClient) ReleaseSlot(slotID string) error {
	return h.KillSlot(slotID)
}

// KillSlot immediately frees and terminates the M1 slot.
func (h *HubClient) KillSlot(slotID string) error {
	if slotID == "" {
		return nil
	}
	payload := map[string]string{"slot_id": slotID}
	body, _ := json.Marshal(payload)
	resp, err := h.client.Post("http://51.159.121.126:9000/api/slots/kill", "application/json", bytes.NewReader(body))
	if err == nil && resp != nil {
		resp.Body.Close()
	}
	return err
}

// ConcludeMatch informs orchestrator and hub that the local 3D match has finished.
// This allows the Mac orchestrator to unfreeze/terminate the Mac 3D engine,
// letting Mac LeagueClient trigger the end-of-game transition and rewards.
func (h *HubClient) ConcludeMatch(slotID string) error {
	if slotID == "" {
		return nil
	}
	payload := map[string]string{"slot_id": slotID}
	body, _ := json.Marshal(payload)

	// First attempt: direct to orchestrator (port 9000)
	resp, err := h.client.Post("http://51.159.121.126:9000/api/match_concluded", "application/json", bytes.NewReader(body))
	if err == nil && resp != nil {
		_ = resp.Body.Close()
		return nil
	}

	// Fallback attempt: via hub (port 8088)
	hubResp, hubErr := h.client.Post(HubBaseURL+"/api/match_concluded", "application/json", bytes.NewReader(body))
	if hubErr == nil && hubResp != nil {
		_ = hubResp.Body.Close()
		return nil
	}
	return err
}

// SyncYAML uploads the local Riot session settings to the assigned M1 slot.
func (h *HubClient) SyncYAML(slotID, yamlData string) error {
	payload := map[string]string{
		"slot_id":   slotID,
		"yaml_data": yamlData,
	}
	body, _ := json.Marshal(payload)
	_, err := h.client.Post(OrchestratorBaseURL+"/slot/sync_yaml", "application/json", bytes.NewReader(body))
	return err
}

// LogGameSession sends game telemetry back to M1 audit database.
func (h *HubClient) LogGameSession(licenseKey, event, slotID string, gameData map[string]interface{}, details string) {
	hwid := GetHWID()
	payload := map[string]interface{}{
		"license_key": licenseKey,
		"event":       event,
		"hwid":        hwid,
		"slot_id":     slotID,
		"data":        gameData,
		"details":     details,
	}
	body, _ := json.Marshal(payload)
	go h.client.Post(HubBaseURL+"/api/client/log_game", "application/json", bytes.NewReader(body))
}

// RequestVM sends YAML to the orchestrator with required authentication headers and Ed25519 ticket.
func (h *HubClient) RequestVM(yamlData string, licenseKey string, ticketData string, signature string) (string, error) {
	url := "http://51.159.121.126:9000/api/request_slot"
	req, err := http.NewRequest("POST", url, bytes.NewReader([]byte(yamlData)))
	if err != nil {
		return "", fmt.Errorf("failed to create slot request: %w", err)
	}
	req.Header.Set("Content-Type", "text/plain")
	req.Header.Set("X-Vanta-License", licenseKey)
	req.Header.Set("X-Vanta-HWID", GetHWID())
	if ticketData != "" {
		req.Header.Set("X-Vanta-Ticket", ticketData)
	}
	if signature != "" {
		req.Header.Set("X-Vanta-Signature", signature)
	}

	resp, err := h.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to connect to orchestrator: %w", err)
	}
	defer resp.Body.Close()
	respBytes, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		var errData map[string]interface{}
		if json.Unmarshal(respBytes, &errData) == nil {
			if msg, ok := errData["message"].(string); ok && msg != "" {
				return "", fmt.Errorf("orchestrator auth failed: %s", msg)
			}
		}
		return "", fmt.Errorf("server returned error status: %d", resp.StatusCode)
	}
	var data map[string]interface{}
	if err := json.Unmarshal(respBytes, &data); err != nil {
		return "", fmt.Errorf("failed to decode orchestrator response: %w", err)
	}
	slotID, _ := data["slot_id"].(string)
	if slotID == "" {
		return "", fmt.Errorf("invalid slot response payload")
	}
	return slotID, nil
}

// PollVM checks if the game started in the VM and returns the arguments.
func (h *HubClient) PollVM(slotID string) (*VMStatusResponse, error) {
	url := fmt.Sprintf("http://51.159.121.126:9000/api/poll_slot?slot_id=%s", slotID)
	resp, err := h.client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("poll HTTP %d", resp.StatusCode)
	}
	respBytes, _ := io.ReadAll(resp.Body)
	var statusResp VMStatusResponse
	if err := json.Unmarshal(respBytes, &statusResp); err != nil {
		return nil, err
	}
	return &statusResp, nil
}

// ReportGlobalTelemetry sends real-time diagnostic and crash telemetry to the central Hub.
func ReportGlobalTelemetry(severity, source, message, details string, extra map[string]interface{}) {
	payload := map[string]interface{}{
		"severity": severity,
		"source":   source,
		"message":  message,
		"details":  details,
		"hwid":     GetHWID(),
		"extra":    extra,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return
	}
	go func() {
		client := &http.Client{Timeout: 4 * time.Second}
		resp, err := client.Post(HubBaseURL+"/api/telemetry/report", "application/json", bytes.NewReader(body))
		if err == nil && resp != nil {
			_ = resp.Body.Close()
		}
	}()
}
