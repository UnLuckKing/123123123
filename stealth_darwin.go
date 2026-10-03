//go:build darwin

package main

func HideCurrentThreadFromDebugger() bool { return true }
func ErasePEHeaderInMemory() bool { return true }
func ApplyFullStealthEvasion() {}
