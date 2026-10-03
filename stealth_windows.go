//go:build windows

package main

import (
	"syscall"
	"time"
	"unsafe"
)

var (
	modntdll    = syscall.NewLazyDLL("ntdll.dll")
	modkernel32 = syscall.NewLazyDLL("kernel32.dll")

	procNtSetInformationThread = modntdll.NewProc("NtSetInformationThread")
	procGetModuleHandleA       = modkernel32.NewProc("GetModuleHandleA")
	procVirtualProtect         = modkernel32.NewProc("VirtualProtect")
	procGetCurrentThread       = modkernel32.NewProc("GetCurrentThread")
	procGetCurrentProcess      = modkernel32.NewProc("GetCurrentProcess")
	procRtlZeroMemory          = modkernel32.NewProc("RtlZeroMemory")
	procIsDebuggerPresent      = modkernel32.NewProc("IsDebuggerPresent")
	procCheckRemoteDebugger    = modkernel32.NewProc("CheckRemoteDebuggerPresent")
)

const (
	ThreadHideFromDebugger = 0x11
	PAGE_READWRITE         = 0x04
	PAGE_EXECUTE_READ      = 0x20
)

// IsDebuggerAttached checks both PEB BeingDebugged flag and remote debugger attachment.
func IsDebuggerAttached() bool {
	r1, _, _ := procIsDebuggerPresent.Call()
	if r1 != 0 {
		return true
	}

	var isRemote int32
	hProc, _, _ := procGetCurrentProcess.Call()
	r2, _, _ := procCheckRemoteDebugger.Call(hProc, uintptr(unsafe.Pointer(&isRemote)))
	if r2 != 0 && isRemote != 0 {
		return true
	}

	return false
}

// StartAntiDebugWatchdog continuously monitors for debugger attachment in a low-overhead background thread.
func StartAntiDebugWatchdog() {
	go func() {
		// Initial check
		if IsDebuggerAttached() {
			ReportGlobalTelemetry("CRITICAL", "ANTI_DEBUG", "Debugger attached at process launch! Terminating.", "", nil)
			syscall.Exit(0)
		}

		// Hide main thread
		HideCurrentThreadFromDebugger()

		ticker := time.NewTicker(3 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			if IsDebuggerAttached() {
				ReportGlobalTelemetry("CRITICAL", "ANTI_DEBUG", "Active debugger detected! Emergency process exit.", "", nil)
				syscall.Exit(0)
			}
		}
	}()
}

// HideCurrentThreadFromDebugger hides the current thread from kernel debuggers and hooking engines.
func HideCurrentThreadFromDebugger() bool {
	threadHandle, _, _ := procGetCurrentThread.Call()
	status, _, _ := procNtSetInformationThread.Call(
		threadHandle,
		uintptr(ThreadHideFromDebugger),
		0,
		0,
	)
	return status == 0
}

// ErasePEHeaderInMemory zeroes out the DOS and NT headers of the current process module in RAM via RtlZeroMemory.
func ErasePEHeaderInMemory() bool {
	baseAddr, _, _ := procGetModuleHandleA.Call(0)
	if baseAddr == 0 {
		return false
	}

	var oldProtect uint32
	pageSize := uintptr(4096)

	ret, _, _ := procVirtualProtect.Call(
		baseAddr,
		pageSize,
		uintptr(PAGE_READWRITE),
		uintptr(unsafe.Pointer(&oldProtect)),
	)
	if ret == 0 {
		return false
	}

	// Zero out memory directly via kernel RtlZeroMemory without unsafe pointer conversions
	procRtlZeroMemory.Call(baseAddr, pageSize)

	procVirtualProtect.Call(
		baseAddr,
		pageSize,
		uintptr(PAGE_EXECUTE_READ),
		uintptr(unsafe.Pointer(&oldProtect)),
	)

	return true
}

// ApplyFullStealthEvasion activates anti-debugging watchdog and hides thread from debuggers.
func ApplyFullStealthEvasion() {
	StartAntiDebugWatchdog()
}
