package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdh"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"time"
)

// Hardcoded Master Server Ed25519 Public Key (Private key strictly resides on M1 Silicon Server)
const ServerEd25519PublicKeyB64 = "UAvCUdWyYOZZLOP95Kq53o94w6dyFv0i3FL3qcSuoCU="

// Master Transport Key for AES-256-GCM Envelope Encryption
var MasterTransportKey = sha256.Sum256([]byte("VANTA_APEX_KERNEL_TRANSPORT_SECRET_2026_SOVEREIGN_KEY_!#"))

// VantaTicket represents the canonical server-attested license ticket.
type VantaTicket struct {
	LicenseKey string `json:"license_key"`
	HWID       string `json:"hwid"`
	Role       string `json:"role"`
	ExpiresAt  int64  `json:"expires_at"`
	Nonce      string `json:"nonce"`
	IssuedAt   int64  `json:"issued_at"`
}

// GenerateNonce creates a secure 32-byte cryptographic nonce.
func GenerateNonce() string {
	b := make([]byte, 32)
	if _, err := io.ReadFull(rand.Reader, b); err != nil {
		// Fallback to timestamp hash if entropy read fails
		h := sha256.Sum256([]byte(fmt.Sprintf("%d_%d", time.Now().UnixNano(), rand.Reader)))
		return hex.EncodeToString(h[:])
	}
	return hex.EncodeToString(b)
}

// EncryptEnvelope encrypts arbitrary plaintext using AES-256-GCM with a 12-byte random nonce.
func EncryptEnvelope(plaintext []byte) (string, error) {
	block, err := aes.NewCipher(MasterTransportKey[:])
	if err != nil {
		return "", fmt.Errorf("aes init failed: %w", err)
	}
	aesgcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("gcm init failed: %w", err)
	}

	nonce := make([]byte, 12)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("nonce generation failed: %w", err)
	}

	ciphertext := aesgcm.Seal(nil, nonce, plaintext, nil)
	packet := append(nonce, ciphertext...)
	return base64.StdEncoding.EncodeToString(packet), nil
}

// DecryptEnvelope decrypts a base64 encoded AES-256-GCM packet.
func DecryptEnvelope(b64Packet string) ([]byte, error) {
	raw, err := base64.StdEncoding.DecodeString(b64Packet)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 envelope: %w", err)
	}
	if len(raw) < 28 { // 12-byte nonce + 16-byte auth tag
		return nil, fmt.Errorf("ciphertext packet too short")
	}

	nonce := raw[:12]
	ciphertext := raw[12:]

	block, err := aes.NewCipher(MasterTransportKey[:])
	if err != nil {
		return nil, fmt.Errorf("aes init failed: %w", err)
	}
	aesgcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("gcm init failed: %w", err)
	}

	return aesgcm.Open(nil, nonce, ciphertext, nil)
}

// VerifyServerTicket cryptographically verifies the Ed25519 signature from the sovereign M1 server.
// If the signature does NOT match the server's private key, verification fails mathematically.
func VerifyServerTicket(b64Ticket, b64Sig, expectedNonce string) (*VantaTicket, error) {
	pubBytes, err := base64.StdEncoding.DecodeString(ServerEd25519PublicKeyB64)
	if err != nil {
		return nil, fmt.Errorf("corrupted public key definition: %w", err)
	}

	ticketBytes, err := base64.StdEncoding.DecodeString(b64Ticket)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 ticket: %w", err)
	}

	sigBytes, err := base64.StdEncoding.DecodeString(b64Sig)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 signature: %w", err)
	}

	// 1. Ed25519 Asymmetric Verification
	if !ed25519.Verify(pubBytes, ticketBytes, sigBytes) {
		return nil, fmt.Errorf("CRITICAL SECURITY VIOLATION: Forged or tampered license attestation signature")
	}

	// 2. Parse Canonical Ticket Data
	var ticket VantaTicket
	if err := json.Unmarshal(ticketBytes, &ticket); err != nil {
		return nil, fmt.Errorf("failed to parse verified ticket payload: %w", err)
	}

	// 3. Anti-Replay Nonce Check
	if expectedNonce != "" && ticket.Nonce != expectedNonce {
		return nil, fmt.Errorf("ANTI-REPLAY VIOLATION: Ticket nonce mismatch (stale or intercepted ticket)")
	}

	// 4. Expiration Timestamp Check
	now := time.Now().Unix()
	if ticket.ExpiresAt < now {
		return nil, fmt.Errorf("LICENSE EXPIRED: Attestation validity period ended")
	}

	return &ticket, nil
}

// deriveAESKey performs ECDH key exchange and returns SHA-256 derived AES key.
func deriveAESKey(privKey *ecdh.PrivateKey, peerPubBytes []byte) ([]byte, error) {
	peerPub, err := ecdh.P256().NewPublicKey(peerPubBytes)
	if err != nil {
		return nil, fmt.Errorf("invalid peer public key: %w", err)
	}
	sharedSecret, err := privKey.ECDH(peerPub)
	if err != nil {
		return nil, fmt.Errorf("ecdh failed: %w", err)
	}
	key := sha256.Sum256(sharedSecret)
	result := make([]byte, 32)
	copy(result, key[:])
	return result, nil
}

// encrypt encrypts data with AES-256-GCM using the provided key and random 12-byte nonce.
func encrypt(key []byte, plaintext []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	aesgcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, 12)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}
	ciphertext := aesgcm.Seal(nil, nonce, plaintext, nil)
	return append(nonce, ciphertext...), nil
}

// decrypt decrypts AES-256-GCM data using the provided key.
func decrypt(key []byte, raw []byte) ([]byte, error) {
	if len(raw) < 28 {
		return nil, fmt.Errorf("ciphertext too short")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	aesgcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := raw[:12]
	ciphertext := raw[12:]
	return aesgcm.Open(nil, nonce, ciphertext, nil)
}

