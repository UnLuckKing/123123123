package main

import (
	"testing"
)

func TestI18nLocales(t *testing.T) {
	locales := []string{
		"tr", "en", "de", "fr", "es", "pt", "ru", "ko", "ja",
		"zh", "zh-TW", "pl", "it", "vi", "hu", "ro", "cs", "el", "ar", "id", "th",
	}

	for _, loc := range locales {
		data := GetLocalizedNoAccount(loc)
		if data.Title == "" {
			t.Errorf("Missing Title for locale %s", loc)
		}
		if data.Message == "" {
			t.Errorf("Missing Message for locale %s", loc)
		}
		if data.OpenClient == "" {
			t.Errorf("Missing OpenClient for locale %s", loc)
		}
		if data.Retry == "" {
			t.Errorf("Missing Retry for locale %s", loc)
		}
		if data.Close == "" {
			t.Errorf("Missing Close for locale %s", loc)
		}
	}

	// Test Turkish specifically
	tr := GetLocalizedNoAccount("tr")
	if tr.Title != "Hesaba Giriş Yap" {
		t.Errorf("Expected 'Hesaba Giriş Yap', got '%s'", tr.Title)
	}

	// Test English specifically
	en := GetLocalizedNoAccount("en")
	if en.Title != "Log In to Your Account" {
		t.Errorf("Expected 'Log In to Your Account', got '%s'", en.Title)
	}

	// Test normalization
	norm := NormalizeLocale("tr_TR")
	if norm != "tr" {
		t.Errorf("Expected 'tr', got '%s'", norm)
	}
	normZhTw := NormalizeLocale("zh-TW")
	if normZhTw != "zh-TW" {
		t.Errorf("Expected 'zh-TW', got '%s'", normZhTw)
	}
}
