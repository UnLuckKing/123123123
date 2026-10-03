package main

import (
	"context"
	"embed"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	// Autonomous In-Place Auto-Update: checks server for latest release, updates and relaunches silently
	_, _ = CheckAndRunAutoUpdate()

	app := NewApp()

	err := wails.Run(&options.App{
		Title:  "VANTA",
		Width:  420,
		Height: 640,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 10, G: 10, B: 10, A: 1},
		Windows: &windows.Options{
			WindowClassName: "VANTA",
		},
		OnStartup: func(ctx context.Context) {
			app.startup(ctx)
		},
		OnBeforeClose: func(ctx context.Context) bool {
			return app.beforeClose(ctx)
		},
		OnShutdown: func(ctx context.Context) {
			app.shutdown(ctx)
		},
		Bind: []interface{}{
			app,
		},
	})

	if err != nil {
		println("Error:", err.Error())
	}
}

