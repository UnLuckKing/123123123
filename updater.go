package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// CurrentClientVersion tracks the compiled version of this binary.
const CurrentClientVersion = "6.7.0"

type UpdateCheckResponse struct {
	Success         bool   `json:"success"`
	UpdateAvailable bool   `json:"update_available"`
	CurrentVersion  string `json:"current_version"`
	LatestVersion   string `json:"latest_version"`
	Mandatory       bool   `json:"mandatory"`
	DownloadURL     string `json:"download_url"`
	FileSize        int64  `json:"file_size"`
	SHA256          string `json:"sha256"`
	Changelog       string `json:"changelog"`
}

// CleanupPreviousUpdate removes .old binary left from previous auto-update
func CleanupPreviousUpdate() {
	exePath, err := os.Executable()
	if err != nil {
		return
	}
	oldPath := exePath + ".old"
	if _, err := os.Stat(oldPath); err == nil {
		_ = os.Remove(oldPath)
	}
	tmpPath := exePath + ".download"
	if _, err := os.Stat(tmpPath); err == nil {
		_ = os.Remove(tmpPath)
	}
}

// CheckAndRunAutoUpdate checks if a newer version exists on the server and applies in-place update.
// Returns true if an update was installed and process relaunched.
func CheckAndRunAutoUpdate() (bool, error) {
	CleanupPreviousUpdate()

	client := &http.Client{Timeout: 5 * time.Second}
	// Try port 8088 first, fallback to port 9000
	urls := []string{
		fmt.Sprintf("http://51.159.121.126:8088/api/client/update_check?version=%s&hwid=%s", CurrentClientVersion, GetHWID()),
		fmt.Sprintf("http://51.159.121.126:9000/api/client/update_check?version=%s&hwid=%s", CurrentClientVersion, GetHWID()),
	}

	var updateResp UpdateCheckResponse
	var checkSuccess bool

	for _, u := range urls {
		resp, err := client.Get(u)
		if err == nil && resp != nil {
			if resp.StatusCode == http.StatusOK {
				if decErr := json.NewDecoder(resp.Body).Decode(&updateResp); decErr == nil {
					checkSuccess = true
					resp.Body.Close()
					break
				}
			}
			resp.Body.Close()
		}
	}

	if !checkSuccess {
		// Server unreachable or offline — proceed with existing binary
		return false, nil
	}

	if !updateResp.UpdateAvailable {
		fmt.Printf("[VANTA UPDATER] Binary is up to date (v%s)\n", CurrentClientVersion)
		return false, nil
	}

	fmt.Printf("[VANTA UPDATER] Newer version detected: v%s (Current: v%s)\n", updateResp.LatestVersion, CurrentClientVersion)
	fmt.Printf("[VANTA UPDATER] Changelog: %s\n", updateResp.Changelog)
	fmt.Println("[VANTA UPDATER] Autonomous in-place update starting...")

	exePath, err := os.Executable()
	if err != nil {
		return false, fmt.Errorf("failed to locate running executable: %w", err)
	}

	downloadPath := exePath + ".download"
	dlReq, err := http.NewRequest("GET", updateResp.DownloadURL, nil)
	if err != nil {
		return false, err
	}
	dlClient := &http.Client{Timeout: 90 * time.Second}
	dlResp, err := dlClient.Do(dlReq)
	if err != nil {
		return false, fmt.Errorf("failed to download update: %w", err)
	}
	defer dlResp.Body.Close()

	if dlResp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("download HTTP %d", dlResp.StatusCode)
	}

	out, err := os.OpenFile(downloadPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return false, fmt.Errorf("failed to create download file: %w", err)
	}

	hasher := sha256.New()
	multiWriter := io.MultiWriter(out, hasher)
	written, err := io.Copy(multiWriter, dlResp.Body)
	out.Close()
	if err != nil {
		_ = os.Remove(downloadPath)
		return false, fmt.Errorf("failed to save update payload: %w", err)
	}

	if written < 5*1024*1024 { // Minimum sanity check: binary must be >= 5MB
		_ = os.Remove(downloadPath)
		return false, fmt.Errorf("downloaded binary corrupted or too small (%d bytes)", written)
	}

	if updateResp.SHA256 != "" {
		calculatedSHA := hex.EncodeToString(hasher.Sum(nil))
		if !strings.EqualFold(calculatedSHA, updateResp.SHA256) {
			_ = os.Remove(downloadPath)
			return false, fmt.Errorf("SHA256 mismatch (expected: %s, got: %s)", updateResp.SHA256, calculatedSHA)
		}
	}

	fmt.Printf("[VANTA UPDATER] Download completed (%d bytes). Applying in-place rename...\n", written)

	// Step 1: Rename currently running exe to .old (Windows allows renaming running binaries)
	oldPath := exePath + ".old"
	_ = os.Remove(oldPath)
	if err := os.Rename(exePath, oldPath); err != nil {
		_ = os.Remove(downloadPath)
		return false, fmt.Errorf("failed to rename running executable: %w", err)
	}

	// Step 2: Move the downloaded new binary into place
	if err := os.Rename(downloadPath, exePath); err != nil {
		// Rollback if destination rename fails
		_ = os.Rename(oldPath, exePath)
		return false, fmt.Errorf("failed to install new executable: %w", err)
	}

	fmt.Println("[VANTA UPDATER] Update installed successfully! Relaunching latest version...")

	// Step 3: Spawn the newly installed binary detached
	cmd := exec.Command(exePath, os.Args[1:]...)
	cmd.Dir = filepath.Dir(exePath)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x00000008, // DETACHED_PROCESS
	}
	if err := cmd.Start(); err != nil {
		// Fallback without detached flags
		cmd = exec.Command(exePath, os.Args[1:]...)
		cmd.Dir = filepath.Dir(exePath)
		_ = cmd.Start()
	}

	// Exit the old process cleanly so the newly updated binary takes over
	os.Exit(0)
	return true, nil
}
