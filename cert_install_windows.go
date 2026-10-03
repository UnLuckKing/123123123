package main

import (
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// installCACert writes the CA DER to a temp file and installs it into the
// Windows Root certificate store via certutil, so Riot Client trusts our
// MITM TLS certificates during HTTPS config interception.
func installCACert(caDER []byte) error {
	tmpDir := os.TempDir()
	certPath := filepath.Join(tmpDir, "VANTA_ca.crt")

	// Write PEM to disk
	pemBlock := &pem.Block{Type: "CERTIFICATE", Bytes: caDER}
	pemData := pem.EncodeToMemory(pemBlock)
	if err := os.WriteFile(certPath, pemData, 0644); err != nil {
		return fmt.Errorf("write CA cert: %w", err)
	}

	// Verify it parses correctly
	if _, err := x509.ParseCertificate(caDER); err != nil {
		return fmt.Errorf("invalid CA cert: %w", err)
	}

	// Install via certutil (silently, no window)
	cmd := exec.Command("certutil", "-addstore", "-f", "-user", "Root", certPath)
	hideCmd(cmd)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("certutil failed: %v — %s", err, string(out))
	}

	return nil
}
