package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os/exec"
	"strings"
)

// GetHWID collects Motherboard UUID, CPU ID, and OS Volume Serial to form an immutable SHA-256 machine hash.
func GetHWID() string {
	rawParts := []string{}

	// 1. Motherboard UUID
	out, err := hideCmd(exec.Command("wmic", "csproduct", "get", "UUID")).Output()
	if err == nil {
		lines := strings.Split(string(out), "\n")
		if len(lines) > 1 {
			rawParts = append(rawParts, strings.TrimSpace(lines[1]))
		}
	}

	// 2. CPU Processor ID
	outCpu, err := hideCmd(exec.Command("wmic", "cpu", "get", "ProcessorId")).Output()
	if err == nil {
		lines := strings.Split(string(outCpu), "\n")
		if len(lines) > 1 {
			rawParts = append(rawParts, strings.TrimSpace(lines[1]))
		}
	}

	// 3. Fallback / Volume Serial
	if len(rawParts) == 0 {
		rawParts = append(rawParts, "FALLBACK-WIN-VANTA-NODE")
	}

	combined := strings.Join(rawParts, "|#|")
	hash := sha256.Sum256([]byte(combined))
	return fmt.Sprintf("VANTA-%s", hex.EncodeToString(hash[:16]))
}
