package main

import (
	"strings"
	"syscall"
	"unsafe"
)

// NoAccountI18n holds localized text elements for the "Log in to account" prompt.
type NoAccountI18n struct {
	Title      string `json:"title"`
	Message    string `json:"message"`
	OpenClient string `json:"open_client"`
	Retry      string `json:"retry"`
	Close      string `json:"close"`
}

var noAccountLocales = map[string]NoAccountI18n{
	"tr": {
		Title:      "Hesaba Giriş Yap",
		Message:    "Riot hesabınıza giriş yapılmamış! Lütfen Riot Client'ı açıp 'Beni Hatırla' seçeneğini işaretleyerek hesabınıza giriş yapın, ardından tekrar başlatın.",
		OpenClient: "Riot Client'ı Aç",
		Retry:      "Tekrar Dene",
		Close:      "Kapat",
	},
	"en": {
		Title:      "Log In to Your Account",
		Message:    "No active Riot account found! Please open Riot Client, log in with 'Remember Me' checked, and try again.",
		OpenClient: "Open Riot Client",
		Retry:      "Try Again",
		Close:      "Close",
	},
	"de": {
		Title:      "Bei Konto anmelden",
		Message:    "Kein aktives Riot-Konto gefunden! Bitte öffne den Riot Client, melde dich mit 'Angemeldet bleiben' an und versuche es erneut.",
		OpenClient: "Riot Client öffnen",
		Retry:      "Erneut versuchen",
		Close:      "Schließen",
	},
	"fr": {
		Title:      "Connectez-vous à votre compte",
		Message:    "Aucun compte Riot actif trouvé ! Veuillez ouvrir le Riot Client, vous connecter en cochant 'Rester connecté' et réessayer.",
		OpenClient: "Ouvrir Riot Client",
		Retry:      "Réessayer",
		Close:      "Fermer",
	},
	"es": {
		Title:      "Inicia sesión en tu cuenta",
		Message:    "¡No se encontró ninguna cuenta de Riot activa! Abre Riot Client, inicia sesión marcando 'Recordarme' e inténtalo de nuevo.",
		OpenClient: "Abrir Riot Client",
		Retry:      "Reintentar",
		Close:      "Cerrar",
	},
	"pt": {
		Title:      "Faça login na sua conta",
		Message:    "Nenhuma conta Riot ativa encontrada! Abra o Riot Client, faça login marcando 'Lembrar de mim' e tente novamente.",
		OpenClient: "Abrir Riot Client",
		Retry:      "Tentar novamente",
		Close:      "Fechar",
	},
	"ru": {
		Title:      "Войдите в свою учетную запись",
		Message:    "Активная учетная запись Riot не найдена! Пожалуйста, откройте Riot Client, войдите с включенной опцией 'Запомнить меня' и повторите попытку.",
		OpenClient: "Открыть Riot Client",
		Retry:      "Повторить",
		Close:      "Закрыть",
	},
	"ko": {
		Title:      "계정에 로그인해 주세요",
		Message:    "활성화된 Riot 계정을 찾을 수 없습니다! Riot Client를 열고 '로그인 상태 유지'를 선택하여 로그인한 후 다시 시도해 주세요.",
		OpenClient: "Riot Client 열기",
		Retry:      "다시 시도",
		Close:      "닫기",
	},
	"ja": {
		Title:      "アカウントにログインしてください",
		Message:    "有効なRiotアカウントが見つかりません。Riot Clientを開き、「ログイン状態を保持」にチェックを入れてログインしてから再度お試しください。",
		OpenClient: "Riot Clientを開く",
		Retry:      "再試行",
		Close:      "閉じる",
	},
	"zh": {
		Title:      "登录您的账户",
		Message:    "未找到有效的Riot账户！请打开Riot客户端，勾选“保持登录状态”并登录，然后重试。",
		OpenClient: "打开 Riot 客户端",
		Retry:      "重试",
		Close:      "关闭",
	},
	"zh-TW": {
		Title:      "登入您的帳戶",
		Message:    "未找到有效的Riot帳戶！請打開Riot客戶端，勾選「保持登入狀態」並登入，然後重試。",
		OpenClient: "開啟 Riot 客戶端",
		Retry:      "重試",
		Close:      "關閉",
	},
	"pl": {
		Title:      "Zaloguj się na swoje konto",
		Message:    "Nie znaleziono aktywnego konta Riot! Otwórz Riot Client, zaloguj się zaznaczając 'Zapamiętaj mnie' i spróbuj ponownie.",
		OpenClient: "Otwórz Riot Client",
		Retry:      "Spróbuj ponownie",
		Close:      "Zamknij",
	},
	"it": {
		Title:      "Accedi al tuo account",
		Message:    "Nessun account Riot attivo trovato! Apri Riot Client, accedi con 'Rimani connesso' e riprova.",
		OpenClient: "Apri Riot Client",
		Retry:      "Riprova",
		Close:      "Chiudi",
	},
	"vi": {
		Title:      "Đăng nhập vào tài khoản",
		Message:    "Không tìm thấy tài khoản Riot đang hoạt động! Vui lòng mở Riot Client, đăng nhập và chọn 'Ghi nhớ đăng nhập', sau đó thử lại.",
		OpenClient: "Mở Riot Client",
		Retry:      "Thử lại",
		Close:      "Đóng",
	},
	"hu": {
		Title:      "Jelentkezz be a fiókodba",
		Message:    "Nem található aktív Riot-fiók! Nyisd meg a Riot Clientet, jelentkezz be a 'Bejelentkezve maradok' lehetőséggel, majd próbáld újra.",
		OpenClient: "Riot Client megnyitása",
		Retry:      "Újrapróbálkozás",
		Close:      "Bezárás",
	},
	"ro": {
		Title:      "Conectați-vă la contul dvs.",
		Message:    "Nu a fost găsit niciun cont Riot activ! Deschideți Riot Client, conectați-vă bifând 'Ține-mă minte' și încercați din nou.",
		OpenClient: "Deschide Riot Client",
		Retry:      "Reîncearcă",
		Close:      "Închide",
	},
	"cs": {
		Title:      "Přihlaste se ke svému účtu",
		Message:    "Nebyl nalezen žádný aktivní účet Riot! Otevřete Riot Client, přihlaste se se zaškrtnutým 'Pamatovat si mě' a zkuste to znovu.",
		OpenClient: "Otevřít Riot Client",
		Retry:      "Zkusit znovu",
		Close:      "Zavřít",
	},
	"el": {
		Title:      "Συνδεθείτε στον λογαριασμό σας",
		Message:    "Δεν βρέθηκε ενεργός λογαριασμός Riot! Ανοίξτε το Riot Client, συνδεθείτε επιλέγοντας 'Να με θυμάσαι' και δοκιμάστε ξανά.",
		OpenClient: "Άνοιγμα Riot Client",
		Retry:      "Δοκιμάστε ξανά",
		Close:      "Κλείσιμο",
	},
	"ar": {
		Title:      "تسجيل الدخول إلى حسابك",
		Message:    "لم يتم العثور على حساب Riot نشط! يُرجى فتح Riot Client وتسجيل الدخول مع تحديد 'تذكرني' ثم المحاولة مرة أخرى.",
		OpenClient: "فتح Riot Client",
		Retry:      "إعادة المحاولة",
		Close:      "إغلاق",
	},
	"id": {
		Title:      "Masuk ke Akun Anda",
		Message:    "Tidak ada akun Riot yang aktif ditemukan! Buka Riot Client, masuk dengan mencentang 'Ingat Saya', lalu coba lagi.",
		OpenClient: "Buka Riot Client",
		Retry:      "Coba Lagi",
		Close:      "Tutup",
	},
	"th": {
		Title:      "เข้าสู่ระบบบัญชีของคุณ",
		Message:    "ไม่พบบัญชี Riot ที่เปิดใช้งานอยู่! โปรดเปิด Riot Client เข้าสู่ระบบโดยเลือก 'จำฉันไว้' แล้วลองใหม่อีกครั้ง",
		OpenClient: "เปิด Riot Client",
		Retry:      "ลองอีกครั้ง",
		Close:      "ปิด",
	},
}

// NormalizeLocale turns "tr_TR", "tr-TR", "tr", "TR" into normalized key "tr".
func NormalizeLocale(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "en"
	}
	clean := strings.ToLower(strings.ReplaceAll(raw, "-", "_"))
	if strings.HasPrefix(clean, "zh_tw") || strings.HasPrefix(clean, "zh_hk") || strings.HasPrefix(clean, "zh_hant") {
		return "zh-TW"
	}
	if strings.HasPrefix(clean, "zh") {
		return "zh"
	}

	parts := strings.Split(clean, "_")
	prefix := parts[0]
	if _, ok := noAccountLocales[prefix]; ok {
		return prefix
	}
	return "en"
}

// DetectSystemLocale detects Windows preferred UI language or fallback to League asset locale.
func DetectSystemLocale() string {
	var (
		modkernel32                  = syscall.NewLazyDLL("kernel32.dll")
		procGetUserDefaultLocaleName = modkernel32.NewProc("GetUserDefaultLocaleName")
	)
	if procGetUserDefaultLocaleName.Find() == nil {
		buf := make([]uint16, 85)
		r1, _, _ := procGetUserDefaultLocaleName.Call(
			uintptr(unsafe.Pointer(&buf[0])),
			uintptr(len(buf)),
		)
		if r1 > 0 {
			loc := syscall.UTF16ToString(buf)
			if loc != "" {
				return NormalizeLocale(loc)
			}
		}
	}
	return "tr" // Turkish primary fallback for kralım's bench
}

// GetLocalizedNoAccount returns the NoAccountI18n struct for the given or detected locale.
func GetLocalizedNoAccount(locale string) NoAccountI18n {
	norm := NormalizeLocale(locale)
	if norm == "en" && locale == "" {
		norm = DetectSystemLocale()
	}
	if item, ok := noAccountLocales[norm]; ok {
		return item
	}
	return noAccountLocales["en"]
}
