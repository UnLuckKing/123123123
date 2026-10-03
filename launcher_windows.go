//go:build windows

package main

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/binary"
	"encoding/pem"
	"fmt"
	"io"
	"math/big"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

var (
	suspendedLeagueClientCmd *exec.Cmd
	blitzProxyMu             sync.Mutex
	blitzProxyListener       net.Listener
	blitzProxyPort           int
	summonerIdRegex          = regexp.MustCompile(`"summonerId"\s*:\s*null`)
)

// TerminateLeagueClientShim cleanly closes the suspended LeagueClient.exe companion, stops the Blitz proxy, and removes stale lockfiles.
func TerminateLeagueClientShim() {
	blitzProxyMu.Lock()
	if blitzProxyListener != nil {
		_ = blitzProxyListener.Close()
		blitzProxyListener = nil
		blitzProxyPort = 0
		fmt.Println("[BLITZ PROXY] Sanitizing proxy closed")
	}
	blitzProxyMu.Unlock()

	if suspendedLeagueClientCmd != nil && suspendedLeagueClientCmd.Process != nil {
		_ = suspendedLeagueClientCmd.Process.Kill()
		suspendedLeagueClientCmd = nil
		fmt.Println("[BLITZ COMPAT] Suspended LeagueClient.exe terminated cleanly")
	}
	// Terminate any orphan suspended LeagueClient processes
	cmd := hideCmd(exec.Command("taskkill", "/F", "/IM", "LeagueClient.exe"))
	_ = cmd.Run()

	// Clean up stale lockfile across all drives so Blitz never reads a dead port
	for _, drive := range []string{"C", "D", "E", "F"} {
		lockPath := filepath.Join(drive+`:\Riot Games\League of Legends`, "lockfile")
		_ = os.Remove(lockPath)
	}
}

// EnsureConfigUnlocked guarantees game config files are writable so user settings never reset.
func EnsureConfigUnlocked() {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return
	}
	configDir := filepath.Join(filepath.Dir(filepath.Dir(gameExe)), "Config")
	entries, err := os.ReadDir(configDir)
	if err != nil {
		return
	}
	for _, e := range entries {
		if !e.IsDir() {
			p := filepath.Join(configDir, e.Name())
			_ = os.Chmod(p, 0666)
			if ptr, err := syscall.UTF16PtrFromString(p); err == nil {
				attrs, err := syscall.GetFileAttributes(ptr)
				if err == nil && (attrs&syscall.FILE_ATTRIBUTE_READONLY) != 0 {
					_ = syscall.SetFileAttributes(ptr, attrs&^syscall.FILE_ATTRIBUTE_READONLY)
				}
			}
		}
	}
}

func startLocalTCPProxy(localPort int, remoteIP string, remotePort int) {
	ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", localPort))
	if err != nil {
		// Port already in use — existing proxy is fine
		return
	}
	go func() {
		dialer := &net.Dialer{
			Timeout:   5 * time.Second,
			KeepAlive: 15 * time.Second,
		}
		for {
			conn, err := ln.Accept()
			if err != nil {
				continue
			}
			go func(c net.Conn) {
				defer c.Close()
				if tc, ok := c.(*net.TCPConn); ok {
					_ = tc.SetKeepAlive(true)
					_ = tc.SetKeepAlivePeriod(15 * time.Second)
					_ = tc.SetNoDelay(true)
					_ = tc.SetReadBuffer(4 * 1024 * 1024)
					_ = tc.SetWriteBuffer(4 * 1024 * 1024)
				}

				// Retry connecting to Mac proxy
				var rc net.Conn
				var dialErr error
				for i := 0; i < 30; i++ {
					rc, dialErr = dialer.Dial("tcp", fmt.Sprintf("%s:%d", remoteIP, remotePort))
					if dialErr == nil {
						break
					}
					time.Sleep(500 * time.Millisecond)
				}
				if dialErr != nil {
					return
				}
				defer rc.Close()
				if rtc, ok := rc.(*net.TCPConn); ok {
					_ = rtc.SetKeepAlive(true)
					_ = rtc.SetKeepAlivePeriod(15 * time.Second)
					_ = rtc.SetNoDelay(true)
					_ = rtc.SetReadBuffer(4 * 1024 * 1024)
					_ = rtc.SetWriteBuffer(4 * 1024 * 1024)
				}

				done := make(chan struct{}, 2)
				go func() {
					buf := make([]byte, 128*1024)
					_, _ = io.CopyBuffer(rc, c, buf)
					if tc, ok := rc.(*net.TCPConn); ok {
						_ = tc.CloseWrite()
					}
					done <- struct{}{}
				}()
				go func() {
					buf := make([]byte, 128*1024)
					_, _ = io.CopyBuffer(c, rc, buf)
					if tc, ok := c.(*net.TCPConn); ok {
						_ = tc.CloseWrite()
					}
					done <- struct{}{}
				}()
				<-done
				<-done
			}(conn)
		}
	}()
}

func generateSelfSignedCert() (tls.Certificate, error) {
	priv, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return tls.Certificate{}, err
	}

	template := x509.Certificate{
		SerialNumber: big.NewInt(time.Now().UnixNano()),
		Subject: pkix.Name{
			Organization: []string{"Riot Games"},
			CommonName:   "127.0.0.1",
		},
		NotBefore: time.Now().Add(-24 * time.Hour),
		NotAfter:  time.Now().Add(365 * 24 * time.Hour),

		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1")},
		DNSNames:              []string{"localhost"},
	}

	derBytes, err := x509.CreateCertificate(rand.Reader, &template, &template, &priv.PublicKey, priv)
	if err != nil {
		return tls.Certificate{}, err
	}

	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: derBytes})
	privBytes, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		return tls.Certificate{}, err
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privBytes})

	return tls.X509KeyPair(certPEM, keyPEM)
}

func sanitizeLCUJson(data []byte) []byte {
	if !bytes.Contains(data, []byte("summonerId")) {
		return data
	}
	return summonerIdRegex.ReplaceAll(data, []byte(`"summonerId":0`))
}

func isWebSocketRequest(req *http.Request) bool {
	return strings.EqualFold(req.Header.Get("Upgrade"), "websocket") ||
		strings.Contains(strings.ToLower(req.Header.Get("Connection")), "upgrade")
}

func handleBlitzWebSocket(w http.ResponseWriter, req *http.Request, remoteIP string, remotePort int) {
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "Hijacking not supported", http.StatusInternalServerError)
		return
	}
	clientConn, clientBuf, err := hijacker.Hijack()
	if err != nil {
		return
	}
	defer clientConn.Close()

	backendConn, err := tls.Dial("tcp", fmt.Sprintf("%s:%d", remoteIP, remotePort), &tls.Config{
		InsecureSkipVerify: true,
	})
	if err != nil {
		return
	}
	defer backendConn.Close()

	// Forward client's handshake request to Mac LCU
	req.Host = fmt.Sprintf("%s:%d", remoteIP, remotePort)
	req.Header.Del("Accept-Encoding")
	if err := req.Write(backendConn); err != nil {
		return
	}

	// Read backend's 101 Switching Protocols response
	backendBuf := bufio.NewReader(backendConn)
	resp, err := http.ReadResponse(backendBuf, req)
	if err != nil {
		return
	}

	// Forward the 101 response to client
	if err := resp.Write(clientConn); err != nil {
		return
	}

	// Flush any pending data from client buffer
	if clientBuf.Reader.Buffered() > 0 {
		buffered := make([]byte, clientBuf.Reader.Buffered())
		_, _ = io.ReadFull(clientBuf.Reader, buffered)
		_, _ = backendConn.Write(buffered)
	}

	done := make(chan struct{}, 2)

	// Client -> Backend: raw copy
	go func() {
		_, _ = io.Copy(backendConn, clientConn)
		done <- struct{}{}
	}()

	// Backend -> Client: WebSocket frame inspector & sanitizer
	go func() {
		_ = proxyWebSocketServerToClient(backendBuf, clientConn)
		done <- struct{}{}
	}()

	<-done
}

func proxyWebSocketServerToClient(src io.Reader, dst io.Writer) error {
	for {
		header := make([]byte, 2)
		if _, err := io.ReadFull(src, header); err != nil {
			return err
		}

		opcode := header[0] & 0x0F
		hasMask := (header[1] & 0x80) != 0
		payloadLen := uint64(header[1] & 0x7F)

		if payloadLen == 126 {
			ext := make([]byte, 2)
			if _, err := io.ReadFull(src, ext); err != nil {
				return err
			}
			payloadLen = uint64(binary.BigEndian.Uint16(ext))
		} else if payloadLen == 127 {
			ext := make([]byte, 8)
			if _, err := io.ReadFull(src, ext); err != nil {
				return err
			}
			payloadLen = binary.BigEndian.Uint64(ext)
		}

		var maskKey []byte
		if hasMask {
			maskKey = make([]byte, 4)
			if _, err := io.ReadFull(src, maskKey); err != nil {
				return err
			}
		}

		payload := make([]byte, payloadLen)
		if _, err := io.ReadFull(src, payload); err != nil {
			return err
		}

		if hasMask {
			for i := range payload {
				payload[i] ^= maskKey[i%4]
			}
		}

		// Text frame (or continuation) from LCU: sanitize summonerId
		if opcode == 0x1 || opcode == 0x0 {
			if bytes.Contains(payload, []byte("summonerId")) {
				payload = sanitizeLCUJson(payload)
			}
		}

		// Rebuild frame header with updated payload length
		newLen := len(payload)
		var frameHeader []byte
		frameHeader = append(frameHeader, header[0]) // Preserves FIN, RSV, opcode

		if newLen <= 125 {
			frameHeader = append(frameHeader, byte(newLen))
		} else if newLen <= 65535 {
			frameHeader = append(frameHeader, 126)
			ext := make([]byte, 2)
			binary.BigEndian.PutUint16(ext, uint16(newLen))
			frameHeader = append(frameHeader, ext...)
		} else {
			frameHeader = append(frameHeader, 127)
			ext := make([]byte, 8)
			binary.BigEndian.PutUint64(ext, uint64(newLen))
			frameHeader = append(frameHeader, ext...)
		}

		if _, err := dst.Write(frameHeader); err != nil {
			return err
		}
		if _, err := dst.Write(payload); err != nil {
			return err
		}
	}
}

func startBlitzSanitizingProxy(preferredPort int, remoteIP string, remotePort int) int {
	blitzProxyMu.Lock()
	defer blitzProxyMu.Unlock()

	if blitzProxyListener != nil && blitzProxyPort > 0 {
		return blitzProxyPort
	}

	cert, err := generateSelfSignedCert()
	if err != nil {
		fmt.Printf("[BLITZ PROXY] Failed to generate TLS cert: %v\n", err)
		return 0
	}

	var ln net.Listener
	var listenPort int

	if preferredPort > 0 {
		ln, err = net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", preferredPort))
		if err == nil {
			listenPort = preferredPort
		}
	}

	if ln == nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			fmt.Printf("[BLITZ PROXY] Failed to listen: %v\n", err)
			return 0
		}
		listenPort = ln.Addr().(*net.TCPAddr).Port
	}

	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{cert},
	}
	tlsLn := tls.NewListener(ln, tlsConfig)
	blitzProxyListener = tlsLn
	blitzProxyPort = listenPort

	targetURL, _ := url.Parse(fmt.Sprintf("https://%s:%d", remoteIP, remotePort))
	reverseProxy := httputil.NewSingleHostReverseProxy(targetURL)
	reverseProxy.Transport = &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}

	originalDirector := reverseProxy.Director
	reverseProxy.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = fmt.Sprintf("127.0.0.1:%d", remotePort)
		req.Header.Del("Accept-Encoding")
	}

	reverseProxy.ModifyResponse = func(resp *http.Response) error {
		if resp.Body == nil {
			return nil
		}

		var reader io.Reader = resp.Body
		isGzip := strings.EqualFold(resp.Header.Get("Content-Encoding"), "gzip")
		if isGzip {
			gzReader, err := gzip.NewReader(resp.Body)
			if err == nil {
				defer gzReader.Close()
				reader = gzReader
			} else {
				isGzip = false
			}
		}

		bodyBytes, err := io.ReadAll(reader)
		if err != nil {
			return nil
		}
		_ = resp.Body.Close()

		if bytes.Contains(bodyBytes, []byte("summonerId")) {
			bodyBytes = sanitizeLCUJson(bodyBytes)
		}

		if isGzip {
			var buf bytes.Buffer
			gzWriter := gzip.NewWriter(&buf)
			_, _ = gzWriter.Write(bodyBytes)
			_ = gzWriter.Close()
			bodyBytes = buf.Bytes()
		}

		resp.Body = io.NopCloser(bytes.NewReader(bodyBytes))
		resp.Header.Del("Transfer-Encoding")
		resp.ContentLength = int64(len(bodyBytes))
		resp.Header.Set("Content-Length", strconv.Itoa(len(bodyBytes)))
		return nil
	}

	reverseProxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		http.Error(w, err.Error(), http.StatusBadGateway)
	}

	server := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			if isWebSocketRequest(req) {
				handleBlitzWebSocket(w, req, remoteIP, remotePort)
				return
			}
			reverseProxy.ServeHTTP(w, req)
		}),
	}

	go func() {
		_ = server.Serve(tlsLn)
	}()

	fmt.Printf("[BLITZ PROXY] Sanitizing TLS reverse proxy active on 127.0.0.1:%d -> %s:%d\n", listenPort, remoteIP, remotePort)
	return listenPort
}

func FindRiotClientServices() string {
	searchPaths := []string{
		`E:\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
		`F:\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
		`C:\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
		`C:\Program Files\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
		`C:\Program Files (x86)\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
		`D:\Riot Games\Riot Client\` + decodeStr(rcsExeObf),
	}

	for _, p := range searchPaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	programData := os.Getenv("ProgramData")
	if programData != "" {
		if data, err := os.ReadFile(filepath.Join(programData, "Riot Games", decodeStr(rcsInstallsJsonObf))); err == nil {
			content := string(data)
			if idx := strings.Index(content, `"`+decodeStr(rcLiveKeyObf)+`"`); idx != -1 {
				rest := content[idx+len(`"`+decodeStr(rcLiveKeyObf)+`"`):]
				if colonIdx := strings.Index(rest, `"`); colonIdx != -1 {
					rest = rest[colonIdx+1:]
					if endIdx := strings.Index(rest, `"`); endIdx != -1 {
						path := rest[:endIdx]
						path = strings.ReplaceAll(path, `\\`, `\`)
						path = strings.ReplaceAll(path, `/`, `\`)
						if _, err := os.Stat(path); err == nil {
							return path
						}
					}
				}
			}
		}
	}

	return ""
}

func LaunchRCSLogin(rcsPath string, proxyPort int, patchline string) error {
	clientConfigURL := fmt.Sprintf("http://127.0.0.1:%d", proxyPort)
	args := []string{
		"--launch-patchline=" + patchline,
		"--client-config-url=" + clientConfigURL,
		"--disable-features=" + decodeStr(disableFeatObf),
	}
	return launchRCSWithArgs(rcsPath, proxyPort, args)
}

func LaunchRCSGame(rcsPath string, proxyPort int, product, patchline string) error {
	clientConfigURL := fmt.Sprintf("http://127.0.0.1:%d", proxyPort)
	args := []string{
		"--launch-patchline=" + patchline,
		"--launch-product=" + product,
		"--client-config-url=" + clientConfigURL,
		"--disable-features=" + decodeStr(disableFeatObf),
	}
	return launchRCSWithArgs(rcsPath, proxyPort, args)
}

func launchRCSWithArgs(rcsPath string, proxyPort int, args []string) error {
	cmd := exec.Command(rcsPath, args...)

	proxyAddr := fmt.Sprintf("http://127.0.0.1:%d", proxyPort)
	env := os.Environ()

	filteredEnv := make([]string, 0, len(env))
	for _, e := range env {
		upper := strings.ToUpper(e)
		if strings.HasPrefix(upper, "HTTP_PROXY=") ||
			strings.HasPrefix(upper, "HTTPS_PROXY=") ||
			strings.HasPrefix(upper, "NO_PROXY=") {
			continue
		}
		filteredEnv = append(filteredEnv, e)
	}

	filteredEnv = append(filteredEnv,
		"HTTP_PROXY="+proxyAddr,
		"HTTPS_PROXY="+proxyAddr,
	)

	hasSystemRoot := false
	for _, e := range filteredEnv {
		if strings.HasPrefix(strings.ToUpper(e), "SYSTEMROOT=") {
			hasSystemRoot = true
			break
		}
	}
	if !hasSystemRoot {
		systemRoot := os.Getenv("SYSTEMROOT")
		if systemRoot == "" {
			systemRoot = `C:\Windows`
		}
		filteredEnv = append(filteredEnv, "SYSTEMROOT="+systemRoot)
	}

	cmd.Env = filteredEnv
	return cmd.Start()
}

func clearSavedLogin() {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		return
	}
	os.Remove(filepath.Join(localAppData, "Riot Games", "Riot Client", "Data", decodeStr(riotSettingsFileObf)))
}

func getSettingsPath() string {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		return ""
	}
	return filepath.Join(localAppData, "Riot Games", "Riot Client", "Data", decodeStr(riotSettingsFileObf))
}

func saveYamlSettings(yamlData string) error {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		return fmt.Errorf("LOCALAPPDATA not set")
	}
	settingsDir := filepath.Join(localAppData, "Riot Games", "Riot Client", "Data")
	if err := os.MkdirAll(settingsDir, 0755); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(settingsDir, decodeStr(riotSettingsFileObf)), []byte(yamlData), 0644)
}

func FindLeagueClientExe() string {
	searchPaths := []string{
		`E:\Riot Games\League of Legends\LeagueClient.exe`,
		`F:\Riot Games\League of Legends\LeagueClient.exe`,
		`C:\Riot Games\League of Legends\LeagueClient.exe`,
		`C:\Program Files\Riot Games\League of Legends\LeagueClient.exe`,
		`C:\Program Files (x86)\Riot Games\League of Legends\LeagueClient.exe`,
		`D:\Riot Games\League of Legends\LeagueClient.exe`,
	}
	for _, p := range searchPaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

func FindLeagueClientUxExe() string {
	searchPaths := []string{
		`E:\Riot Games\League of Legends\LeagueClientUx.exe`,
		`F:\Riot Games\League of Legends\LeagueClientUx.exe`,
		`C:\Riot Games\League of Legends\LeagueClientUx.exe`,
		`C:\Program Files\Riot Games\League of Legends\LeagueClientUx.exe`,
		`C:\Program Files (x86)\Riot Games\League of Legends\LeagueClientUx.exe`,
		`D:\Riot Games\League of Legends\LeagueClientUx.exe`,
	}
	for _, p := range searchPaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

func LaunchLeagueClientLocally(args []string, macProxyPort int, macLCUPort int) error {
	clientExe := FindLeagueClientUxExe()
	if clientExe == "" {
		clientExe = FindLeagueClientExe()
		if clientExe == "" {
			return fmt.Errorf("game client executables (LeagueClientUx.exe / LeagueClient.exe) not found")
		}
	}

	EnsureConfigUnlocked()
	installDir := filepath.Dir(clientExe)
	installDirFwd := strings.ReplaceAll(installDir, "\\", "/")
	localAppData := strings.ReplaceAll(os.Getenv("LOCALAPPDATA"), "\\", "/")
	programData := strings.ReplaceAll(os.Getenv("PROGRAMDATA"), "\\", "/")

	var rcPort int
	var appPort int
	var authToken string
	for _, arg := range args {
		if strings.HasPrefix(arg, "--riotclient-app-port=") {
			fmt.Sscanf(arg, "--riotclient-app-port=%d", &rcPort)
		} else if strings.HasPrefix(arg, "--app-port=") {
			fmt.Sscanf(arg, "--app-port=%d", &appPort)
		} else if strings.HasPrefix(arg, "--remoting-auth-token=") {
			authToken = strings.Trim(strings.TrimPrefix(arg, "--remoting-auth-token="), "\"' ")
		}
	}

	if rcPort != 0 {
		// Tunnel Windows -> Mac RC API on the slot's dedicated proxy port
		startLocalTCPProxy(rcPort, "51.159.121.126", macProxyPort)
	}
	if appPort != 0 {
		// Tunnel Windows -> Mac LCU API
		startLocalTCPProxy(appPort, "51.159.121.126", macLCUPort)
		if authToken != "" {
			SetActiveLCU(fmt.Sprintf("%d", appPort), authToken)
			fmt.Printf("[VANTA] Active LCU registered on port %d with auth token\n", appPort)
		}
	}

	var cleanArgs []string
	for _, arg := range args {
		if !strings.HasPrefix(arg, "--") {
			continue
		}
		if strings.HasPrefix(arg, "--install-directory=") {
			cleanArgs = append(cleanArgs, "--install-directory="+installDir)
		} else if strings.HasPrefix(arg, "--output-base-dir=") {
			cleanArgs = append(cleanArgs, "--output-base-dir="+installDir)
		} else if strings.HasPrefix(arg, "--app-log-file-path=") {
			logDir := filepath.Join(installDir, "Logs", "LeagueClient Logs")
			os.MkdirAll(logDir, 0755)
			cleanArgs = append(cleanArgs, "--app-log-file-path="+filepath.Join(logDir, "bypass_LeagueClient.log"))
		} else if strings.HasPrefix(arg, "--primary-ux-log-file-path=") {
			logDir := filepath.Join(installDir, "Logs", "LeagueClient Logs")
			os.MkdirAll(logDir, 0755)
			cleanArgs = append(cleanArgs, "--primary-ux-log-file-path="+filepath.Join(logDir, "bypass_LeagueClientUx.log"))
		} else if strings.HasPrefix(arg, "--riotgamesapi-settings=") {
			rawB64 := strings.TrimPrefix(arg, "--riotgamesapi-settings=")
			if decoded, err := base64.StdEncoding.DecodeString(rawB64); err == nil {
				jsonStr := string(decoded)
				jsonStr = strings.ReplaceAll(jsonStr, "/Users/m1/Library/Application Support", localAppData)
				jsonStr = strings.ReplaceAll(jsonStr, "/Users/Shared/Riot Games", programData+"/Riot Games")
				for s := 1; s <= 25; s++ {
					jsonStr = strings.ReplaceAll(jsonStr, fmt.Sprintf("/Applications/League of Legends_slot%d.app/Contents/LoL", s), installDirFwd)
					jsonStr = strings.ReplaceAll(jsonStr, fmt.Sprintf("/Users/m1/VantaSlots/slot%d/SharedMetadata", s), programData+"/Riot Games/Metadata")
					jsonStr = strings.ReplaceAll(jsonStr, fmt.Sprintf("/Users/m1/VantaSlots/slot%d/Data", s), localAppData+"/Riot Games/Riot Client/Data")
				}
				jsonStr = strings.ReplaceAll(jsonStr, "/Users/m1/VantaSlots/League of Legends", localAppData+"/Riot Games/League of Legends")
				jsonStr = strings.ReplaceAll(jsonStr, "/Applications/League of Legends.app/Contents/LoL", installDirFwd)
				newB64 := base64.StdEncoding.EncodeToString([]byte(jsonStr))
				cleanArgs = append(cleanArgs, "--riotgamesapi-settings="+newB64)
			} else {
				cleanArgs = append(cleanArgs, arg)
			}
		} else if strings.HasPrefix(arg, "--app-pid=") {
			cleanArgs = append(cleanArgs, fmt.Sprintf("--app-pid=%d", os.Getpid()))
		} else {
			cleanArgs = append(cleanArgs, arg)
		}
	}

	cmd := exec.Command(clientExe, cleanArgs...)
	cmd.Dir = installDir
	fmt.Printf("Executing: %s %v\n", clientExe, cleanArgs)
	err := cmd.Start()
	if err == nil && appPort != 0 && authToken != "" && cmd.Process != nil {
		// Blitz & Third-Party Companion Integration:
		// Blitz's getLeagueClientProcess() specifically scans psList() for a process ending in 'LeagueClient.exe'.
		// We launch the genuine LeagueClient.exe in CREATE_SUSPENDED (0x00000004) state in installDir.
		// It executes 0 instructions, uses 0 CPU, bypasses Vanguard checks, and satisfies Blitz's process scanner.
		leagueClientExe := filepath.Join(installDir, "LeagueClient.exe")
		var targetPid = cmd.Process.Pid
		if _, statErr := os.Stat(leagueClientExe); statErr == nil {
			TerminateLeagueClientShim()
			shimCmd := exec.Command(leagueClientExe)
			shimCmd.Dir = installDir
			shimCmd.SysProcAttr = &syscall.SysProcAttr{
				CreationFlags: 0x00000004, // CREATE_SUSPENDED
			}
			if shimErr := shimCmd.Start(); shimErr == nil && shimCmd.Process != nil {
				suspendedLeagueClientCmd = shimCmd
				targetPid = shimCmd.Process.Pid
				fmt.Printf("[BLITZ COMPAT] Suspended LeagueClient.exe spawned (PID %d)\n", targetPid)
			}
		}

		// Dedicated Blitz Sanitizing Proxy:
		// Eliminates Dart CheckedFromJsonException where summonerId is null in Arena mode (Map 30).
		// Routes Blitz through an in-memory TLS proxy that replaces "summonerId": null with 0.
		blitzPort := startBlitzSanitizingProxy(appPort+200, "51.159.121.126", macLCUPort)
		if blitzPort == 0 {
			blitzPort = appPort // Fallback to raw TCP proxy if TLS setup fails
		}

		lockContent := fmt.Sprintf("LeagueClient:%d:%d:%s:https", targetPid, blitzPort, authToken)
		lockPath := filepath.Join(installDir, "lockfile")
		_ = os.WriteFile(lockPath, []byte(lockContent), 0644)
		if !strings.EqualFold(installDir, `C:\Riot Games\League of Legends`) {
			_ = os.WriteFile(`C:\Riot Games\League of Legends\lockfile`, []byte(lockContent), 0644)
		}
		SetActiveLCU(fmt.Sprintf("%d", blitzPort), authToken)
		fmt.Printf("[BLITZ COMPAT] Written lockfile with port %d (PID %d)\n", blitzPort, targetPid)
	}
	return err
}

func FindLeagueGameExe() string {
	searchPaths := []string{
		`E:\Riot Games\League of Legends\Game\League of Legends.exe`,
		`F:\Riot Games\League of Legends\Game\League of Legends.exe`,
		`C:\Riot Games\League of Legends\Game\League of Legends.exe`,
		`C:\Program Files\Riot Games\League of Legends\Game\League of Legends.exe`,
		`C:\Program Files (x86)\Riot Games\League of Legends\Game\League of Legends.exe`,
		`D:\Riot Games\League of Legends\Game\League of Legends.exe`,
	}
	for _, p := range searchPaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

// EnsureAllMapsLocalized dynamically scans all installed map assets (Map11, Map12, Map22, Map453, etc.)
// and guarantees that localized WADs for the detected locale are linked.
func EnsureAllMapsLocalized(mapsDir string, detectedLocale string) {
	entries, err := os.ReadDir(mapsDir)
	if err != nil {
		return
	}
	existingMapLocales := make(map[string]string)
	hasTargetLocale := make(map[string]bool)

	for _, e := range entries {
		name := e.Name()
		if strings.HasSuffix(name, ".wad.client") {
			parts := strings.Split(name, ".")
			if len(parts) >= 3 {
				mapPrefix := parts[0]
				existingMapLocales[mapPrefix] = name
				if parts[1] == detectedLocale {
					hasTargetLocale[mapPrefix] = true
				}
			}
		}
	}

	for mapPrefix, existingFile := range existingMapLocales {
		if !hasTargetLocale[mapPrefix] {
			targetName := fmt.Sprintf("%s.%s.wad.client", mapPrefix, detectedLocale)
			targetPath := filepath.Join(mapsDir, targetName)
			_ = os.Link(filepath.Join(mapsDir, existingFile), targetPath)
		}
	}
}

func LaunchLeagueGameLocally(args []string, proxyPort int, lcuPort int, slotID string) error {
	gameExe := FindLeagueGameExe()
	if gameExe == "" {
		return fmt.Errorf("game executable (League of Legends.exe) not found")
	}

	installDir := filepath.Dir(filepath.Dir(gameExe))

	// Universal Multi-Language Engine:
	// Detect user's REAL installed asset locale from core map assets (Map11 - Summoner's Rift)
	detectedLocale := "tr_TR"
	mapsDir := filepath.Join(filepath.Dir(gameExe), "DATA", "FINAL", "Maps", "Shipping")
	if entries, err := os.ReadDir(mapsDir); err == nil {
		for _, e := range entries {
			name := e.Name()
			if strings.HasPrefix(name, "Map11.") && strings.HasSuffix(name, ".wad.client") && name != "Map11.wad.client" {
				parts := strings.Split(name, ".")
				if len(parts) == 4 {
					detectedLocale = parts[1]
					break
				}
			}
		}
	}

	// Ensure Localized directory has Global.<detectedLocale>.wad.client
	locDir := filepath.Join(filepath.Dir(gameExe), "DATA", "FINAL", "Localized")
	targetGlobalWad := filepath.Join(locDir, fmt.Sprintf("Global.%s.wad.client", detectedLocale))
	if _, statErr := os.Stat(targetGlobalWad); os.IsNotExist(statErr) {
		// Find any existing Global.*.wad.client and link it
		if entries, err := os.ReadDir(locDir); err == nil {
			for _, e := range entries {
				if strings.HasPrefix(e.Name(), "Global.") && strings.HasSuffix(e.Name(), ".wad.client") {
					_ = os.Link(filepath.Join(locDir, e.Name()), targetGlobalWad)
					break
				}
			}
		}
	}

	// Also ensure Global.en_US.wad.client exists as engine fallback
	targetEnUsWad := filepath.Join(locDir, "Global.en_US.wad.client")
	if _, statErr := os.Stat(targetEnUsWad); os.IsNotExist(statErr) {
		if _, statTr := os.Stat(targetGlobalWad); statTr == nil {
			_ = os.Link(targetGlobalWad, targetEnUsWad)
		}
	}

	// Ensure Tutorial and all other game maps (Map11, Map12, Map22, Map453) have localized WADs
	EnsureAllMapsLocalized(mapsDir, detectedLocale)
	EnsureConfigUnlocked()

	// Ensure local tunnels to Mac API ports are active
	if proxyPort != 0 {
		startLocalTCPProxy(proxyPort, "51.159.121.126", proxyPort)
	}
	if lcuPort != 0 {
		startLocalTCPProxy(lcuPort, "51.159.121.126", lcuPort)
	}

	var cleanArgs []string
	
	if len(args) >= 4 {
		firstArg := fmt.Sprintf("%s %s %s %s", args[0], args[1], args[2], args[3])
		cleanArgs = append(cleanArgs, firstArg)
	}
	
	for i := 4; i < len(args); i++ {
		arg := args[i]
		if strings.HasPrefix(arg, "-GameBaseDir=") {
			cleanArgs = append(cleanArgs, "-GameBaseDir="+installDir)
		} else if strings.HasPrefix(arg, "-Locale=") {
			cleanArgs = append(cleanArgs, "-Locale="+detectedLocale)
		} else if strings.HasPrefix(arg, "-RiotClientPort=") {
			origPortStr := strings.TrimPrefix(arg, "-RiotClientPort=")
			origPort, _ := strconv.Atoi(origPortStr)
			// CRITICAL FIX: -RiotClientPort= must route to proxyPort (RCS - Riot Client Services on Mac),
			// NOT lcuPort (which is LCU / LeagueClientUx).
			// Forwarding to LCU causes RCS session validation to fail with 401/404, triggering the
			// internal 180s Riot Client heartbeat timeout and 0xc0000409 (STATUS_STACK_BUFFER_OVERRUN) crash.
			targetRcPort := proxyPort
			if targetRcPort == 0 {
				targetRcPort = 8090
			}
			if origPort > 0 {
				startLocalTCPProxy(origPort, "51.159.121.126", targetRcPort)
				cleanArgs = append(cleanArgs, arg)
			} else {
				cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", targetRcPort))
			}
		} else if strings.HasPrefix(arg, "-UseMetal=") {
		} else if strings.HasPrefix(arg, "-EnableCrashpad=") {
			cleanArgs = append(cleanArgs, "-EnableCrashpad=false", "-DisableCrashUploading")
		} else if strings.HasPrefix(arg, "-OutputBaseDir=") {
			cleanArgs = append(cleanArgs, "-OutputBaseDir="+installDir)
		} else if strings.HasPrefix(arg, "-InstallDirectory=") {
			cleanArgs = append(cleanArgs, "-InstallDirectory="+installDir)
		} else if !strings.HasPrefix(arg, "-") && !strings.Contains(arg, "=") {
			continue
		} else {
			cleanArgs = append(cleanArgs, arg)
		}
	}

	cmd := exec.Command(gameExe, cleanArgs...)
	cmd.Dir = filepath.Dir(gameExe)

	logDir := getVantaLogDir()
	stdoutFile, _ := os.OpenFile(filepath.Join(logDir, "league_stdout.log"), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if stdoutFile != nil {
		cmd.Stdout = stdoutFile
		cmd.Stderr = stdoutFile
	}

	var filteredEnv []string
	for _, env := range os.Environ() {
		upper := strings.ToUpper(env)
		if strings.HasPrefix(upper, "USERDOMAIN=") ||
			strings.HasPrefix(upper, "LOGONSERVER=") ||
			strings.HasPrefix(upper, "COR_ENABLE_PROFILING=") {
			continue
		}
		filteredEnv = append(filteredEnv, env)
	}
	cmd.Env = filteredEnv

	f, _ := os.OpenFile(filepath.Join(logDir, "vanta_debug.txt"), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(fmt.Sprintf("[VANTA] Launching Game: %s %v\n", gameExe, cleanArgs))
		f.Close()
	}

	ReportGlobalTelemetry("INFO", "GAME_LAUNCHER", "Launching 3D League Game locally", fmt.Sprintf("Locale: %s, Args count: %d", detectedLocale, len(cleanArgs)), map[string]interface{}{
		"locale":   detectedLocale,
		"lcu_port": lcuPort,
		"game_exe": gameExe,
	})

	err := cmd.Start()
	if err != nil {
		if stdoutFile != nil {
			_ = stdoutFile.Close()
		}
		ReportGlobalTelemetry("CRITICAL", "GAME_LAUNCHER", "Failed to start League of Legends.exe", err.Error(), nil)
		return err
	}

	// Live background process monitor for immediate crash & exit detection
	startTime := time.Now()
	go func() {
		waitErr := cmd.Wait()
		if stdoutFile != nil {
			_ = stdoutFile.Close()
		}
		duration := time.Since(startTime).Seconds()
		if waitErr != nil {
			ReportGlobalTelemetry("CRITICAL", "GAME_LAUNCHER", fmt.Sprintf("Game exited / crashed after %.1fs", duration), waitErr.Error(), map[string]interface{}{
				"duration_seconds": duration,
				"locale":           detectedLocale,
			})
		} else {
			ReportGlobalTelemetry("INFO", "GAME_LAUNCHER", fmt.Sprintf("Game process ended cleanly after %.1fs", duration), "", map[string]interface{}{
				"duration_seconds": duration,
			})
		}

		// Automatically notify App of process exit to conclude match on Mac and clear cached args
		if app := GetGlobalApp(); app != nil {
			app.OnGameProcessExited(waitErr, duration, slotID)
		} else if slotID != "" {
			hub := NewHubClient()
			_ = hub.ConcludeMatch(slotID)
			time.Sleep(1 * time.Second)
			if lcu, err := NewLCUClient(); err == nil {
				_ = lcu.DismissEndOfGame()
			}
		}
	}()

	return nil
}

func launchLeague() error {
	rcsPath := FindRiotClientServices()
	if rcsPath == "" {
		return fmt.Errorf("RCS not found")
	}
	cmd := exec.Command(rcsPath,
		"--launch-patchline="+decodeStr(patchlineLiveObf),
		"--launch-product="+decodeStr(productLoLObf),
	)
	return cmd.Start()
}

func clearRiotLogs() {
	if isLeagueGameRunning() {
		return
	}
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData != "" {
		os.RemoveAll(filepath.Join(localAppData, "Riot Games", "Riot Client", "Logs"))
		os.RemoveAll(filepath.Join(localAppData, "Riot Games", "Riot Client", "Crashes"))
	}
	for _, drive := range []string{"C", "D", "E", "F"} {
		root := drive + `:\`
		if _, err := os.Stat(root); err != nil {
			continue
		}
		os.RemoveAll(filepath.Join(root, "Riot Games", "Riot Client", "Logs"))
	}
}

func getVantaLogDir() string {
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		localAppData = os.TempDir()
	}
	logDir := filepath.Join(localAppData, "Vanta", "Logs")
	_ = os.MkdirAll(logDir, 0755)
	return logDir
}

