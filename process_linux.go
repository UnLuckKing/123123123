//go:build linux

package main

import "os/exec"

func terminateRiotServices() {}

func isLeagueClientRunning() bool { return false }

func isLeagueGameRunning() bool { return false }

func killLeagueGame() {}

func waitRiotThenClose(proxy *LeagueProxy) {
	proxy.Stop()
}

func clearRiotLogs() {}

func hideCmd(cmd *exec.Cmd) *exec.Cmd {
	return cmd
}
