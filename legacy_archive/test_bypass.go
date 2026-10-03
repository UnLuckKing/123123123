package main

import (
	"context"
	"fmt"
	"time"
)

func runTest() {
	fmt.Println("Starting App test...")
	app := NewApp()
	app.startup(context.Background())
	
	fmt.Println("Bypassing login check...")
	app.mu.Lock()
	app.license = &LoginOKPayload{
		HasLicense: true,
		ExpiresAt:  "2030-01-01",
	}
	app.status = "logged_in"
	app.mu.Unlock()
	
	fmt.Println("Preparing Login (Starting Bypass)...")
	res2 := app.PrepareLogin("C:\\Riot Games\\Riot Client\\RiotClientServices.exe")
	fmt.Println("PrepareLogin result:", res2)
	
	for i := 0; i < 60; i++ {
		status := app.GetStatus()
		fmt.Println("Status:", status)
		if status == "running" || status == "logged_in" {
			break
		}
		time.Sleep(2 * time.Second)
	}
}
