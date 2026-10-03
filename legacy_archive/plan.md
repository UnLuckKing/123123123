# VANTA — Kapsamlı Mimari, Güvenlik ve Uygulama Planı (plan.md)

> **Proje Kodu:** VANTA-CORE-V5  
> **Hedef Sistem:** Windows 10/11 x64 (İstemci) <---> Scaleway macOS Apple Silicon M1 (Uzak Doğrulama & Oturum Düğümü)  
> **Ana Hedef:** Vanguard kısıtlaması olmadan, sıfıra yakın ban riskiyle yerel Windows ortamında 3D oyun ve script/otomasyon desteği sağlamak.  
> **Dizinler:**  
> - Windows: `C:\Users\hesap\Desktop\nrx.lol-main`  
> - Mac Sunucusu: `51.159.121.126` (`/Users/m1`)  

---

## İÇİNDEKİLER

1. [YÖNETİCİ ÖZETİ VE TEMEL PROBLEM TANIMI](#1-yönetici-özeti-ve-temel-problem-tanimi)
2. [MİMARİ PRENSİPLER VE DOĞRULAMA MODELİ](#2-mimari-prensipler-ve-doğrulama-modeli)
3. [VANGUARD VE TELEMETRİ ANALİZİ (BAN MEKANİZMASI)](#3-vanguard-ve-telemetri-analizi-ban-mekanizmasi)
4. [SİSTEM BİLEŞENLERİ VE AKIŞ ŞEMASI](#4-sistem-bilesenleri-ve-akis-semasi)
5. [DETAYLI UYGULAMA FAZLARI](#5-detayli-uygulama-fazlari)
   - [FAZ 1: MAC ORCHESTRATOR VE İZOLE SLOT YÖNETİMİ](#faz-1-mac-orchestrator-ve-izole-slot-yönetimi)
   - [FAZ 2: OYUN PARAMETRESİ YAKALAMA VE AKTARIM MOTORU](#faz-2-oyun-parametresi-yakalama-ve-aktarim-motoru)
   - [FAZ 3: AĞ VE UDP/TCP TÜNELLEME (IP EŞLEME KATMANI)](#faz-3-ağ-ve-udptcp-tünelleme-ip-esleme-katmani)
   - [FAZ 4: WINDOWS BAŞLATICI VE PROCESS ORTAM İZOLASYONU](#faz-4-windows-baslatici-ve-process-ortam-izolasyonu)
   - [FAZ 5: SCRİPT VE BELLEK ERİŞİM ENTEGRASYONU](#faz-5-script-ve-bellek-erisim-entegrasyonu)
   - [FAZ 6: TELEMETRİ, LOG VE İZ TEMİZLEME SİSTEMİ](#faz-6-telemetri-log-ve-iz-temizleme-sistemi)
6. [VERİ YAPILARI, STRUCT'LAR VE PROTOKOL TANIMLARI](#6-veri-yapilari-structlar-ve-protokol-tanimlari)
7. [HATA YÖNETİMİ, EDGE-CASE VE KURTARMA PROTOKOLLERİ](#7-hata-yönetimi-edge-case-ve-kurtarma-protokolleri)
8. [TEST, DOĞRULAMA VE KALİTE GÜVENCE MATRİSİ](#8-test-doğrulama-ve-kalite-güvence-matrisi)
9. [BAKIM, PERFORMANS VE GELECEK GELİŞTİRMELER](#9-bakim-performans-ve-gelecek-gelistirmeler)

---

## 1. YÖNETİCİ ÖZETİ VE TEMEL PROBLEM TANIMI

### 1.1 Mevcut Durumun Tespiti
League of Legends istemci ekosistemi iki ana yapıdan oluşur:
1. **Lobi ve Kullanıcı Arayüzü (`LeagueClientUx.exe`):** Chromium Embedded Framework (CEF) tabanlı Web arayüzü. Vanguard sürücüsüyle doğrudan bir donanım attestation bağlantısı kurmaz; haberleşmesini yerel LCU (League Client Update) REST API ve WebSocket arayüzü üzerinden yürütür.
2. **3D Oyun Motoru (`League of Legends.exe`):** DirectX tabanlı asıl oyun motoru. Windows ortamında başlatıldığında `vgk.sys` (Vanguard Kernel Driver) ve `vgc` (Vanguard User Mode Service) ile IPC üzerinden haberleşerek donanım imzası ve bellek bütünlüğü raporlar.

### 1.2 Çözülmesi Gereken Üç Temel Problem
* **Problem A (Script Çalıştırma Zorunluluğu):** Harici veya dahili Windows scriptleri doğrudan `League of Legends.exe` sürecinin sanal bellek alanına (`VirtualAllocEx`, `ReadProcessMemory`, `WriteProcessMemory`) veya Direct3D swapchain kancalarına ihtiyaç duyar. Uzaktan ekran yayını (VNC/Streaming) yönteminde Windows üzerinde bir oyun süreci bulunmadığından scriptler bağlanamaz. Oyunun yerel Windows üzerinde çalışması zorunludur.
* **Problem B (Vanguard Attestation ve Platform Eşlemesi):** Windows üzerinde oyun başlatıldığında Vanguard denetimi tetiklenir. Ancak oturum Mac M1 sunucusu üzerinden (`WAIVED_MACOS` platform bayrağıyla) doğrulanırsa, Riot sunucusu istemcinin bir Mac olduğunu varsayar. Bu oturumun yerel Windows'ta açılması durumunda platform, IP ve donanım kimliklerinin (HWID) birbiriyle %100 örtüşmesi gerekir.
* **Problem C (Çoklu Kullanıcı ve Slot Çakışması):** Mac sunucusunda birden fazla kullanıcının eşzamanlı oturum açabilmesi için süreçlerin izole edilmesi, port havuzlarının ayrılması ve global `pkill` komutlarının tamamen kaldırılarak PID-bazlı yönetime geçilmesi gerekir.

---

## 2. MİMARİ PRENSİPLER VE DOĞRULAMA MODELİ

### 2.1 Hibrit Doğrulama Modeli (Mac Auth + Win Execution)
Sistemin ana prensibi, Riot'un platform doğrulamasını Mac üzerinde gerçekleştirip, oyun parametrelerini Windows'a aktararak yerel çalıştırmaktır:

```
[ Riot Sunucuları (Game / Auth / LCU) ]
             ^
             | (Oturum Doğrulama / macOS İmzası / Tokenler)
             v
[ Scaleway Mac M1 Node (51.159.121.126) ]
  ├── vanta_orchestrator.py (Slot Yöneticisi)
  ├── Riot Client (Mac Native)
  ├── LeagueofLegends.app (Mac Native - Parametre Yakalayıcı)
  └── Dedicated Tunnels (RC: 8090-8099, LCU: 8100-8109, UDP Relay)
             ^
             | (Şifreli TCP/UDP Tüneli & Parametre Aktarımı)
             v
[ Yerel Windows İstemcisi (Kullanıcı PC) ]
  ├── vanta.exe (Wails + Go Çekirdeği)
  ├── LeagueClientUx.exe (Lobi Arayüzü - Mac LCU Tüneline Bağlı)
  ├── League of Legends.exe (3D Oyun Motoru - Yerel RAM/DirectX)
  └── Script / Otomasyon Katmanı (Yerel Bellek Erişimi)
```

### 2.2 Güvenlik ve Ban Önleme Aksiyomları
1. **IP Bütünlüğü:** Lobi bağlantısı hangi dış IP üzerinden yapıldıysa, oyun motorunun UDP trafiği de kesinlikle aynı IP üzerinden Riot sunucusuna ulaşmalıdır.
2. **Platform Başlık Tutarlılığı:** LCU ve Riot Client üzerinden giden tüm HTTP/WebSocket paketlerinde `User-Agent`, `X-Riot-ClientPlatform` ve `X-Riot-ClientVersion` başlıkları Mac oturumu ile senkronize kalmalıdır.
3. **Telemetri ve Log Sanitizasyonu:** Windows dosya sisteminde oluşabilecek yerel loglar, crash reportlar ve telemetri dosyaları anlık olarak silinmeli veya sanal yollara yönlendirilmelidir.
4. **Süreç Başlatma Hijyeni:** `League of Legends.exe` başlatılırken Windows ortam değişkenleri filtrelenmeli, izole bir ortam bloğu ile çalıştırılmalıdır.

---

## 3. VANGUARD VE TELEMETRİ ANALİZİ (BAN MEKANİZMASI)

### 3.1 Vanguard Doğrulama Vektörleri
Vanguard'ın hile ve anomali tespitinde kullandığı başlıca vektörler şunlardır:

1. **Kernel Driver Heartbeat (`vgk.sys`):**
   - Oyun istemcisi belirli periyotlarla çekirdek sürücüsüne IOCTL çağrıları gönderir.
   - Sürücü, fiziksel bellek sayfalarını, sayfa tablosu girişlerini (PTE), CR3 kayıtlarını ve donanım kesme tablolarını tarar.
   - Sürücüden dönen kriptografik hash, oyun paketi içine gömülerek sunucuya iletilir.
   - **Mac İstisnası:** macOS çekirdeği KEXT/DriverKit kısıtlamaları nedeniyle üçüncü parti Ring 0 sürücülere izin vermez. Riot, macOS platformu için `WAIVED_MACOS` politikasını uygular ve bu paket doğrulamasını talep etmez.

2. **Ağ / Oturum Telemetrisi:**
   - Lobi oturumunun açıldığı IP adresi ile oyun sunucusuna bağlanan IP adresi arasındaki ASN, coğrafi konum ve RTT (Round Trip Time) farkları izlenir.
   - Farklı ülkelerden veya farklı ağ sağlayıcılarından gelen eşzamanlı bağlantılar "Account Sharing / Proxy Anomaly" olarak işaretlenir.

3. **İstemci Log Dosyaları:**
   - `LeagueClientLogs` ve `r3dlog` dosyaları içerisine yerel işletim sistemi sürümü, donanım kimlikleri, ekran çözünürlüğü ve MAC adresleri yazılır.
   - Oturum kapanışında bu loglar Riot'un log toplama uç noktalarına (`sentry`, `telemetry.riotgames.com`) asenkron olarak yüklenir.

---

## 4. SİSTEM BİLEŞENLERİ VE AKIŞ ŞEMASI

### 4.1 Bileşen Tanımları

| Bileşen Adı | Bulunduğu Ortam | Sorumluluk |
|---|---|---|
| `vanta_orchestrator.py` | Mac M1 Sunucusu | Slot yönetimi, port tahsisi, Riot Client çalıştırma, LCU proxy |
| `vanta.exe` | Windows İstemcisi | Kullanıcı arayüzü, SSH/TCP tünel yönetimi, LCU durum takibi |
| `launcher_windows.go` | Windows İstemcisi | `LeagueClientUx.exe` ve `League of Legends.exe` süreç başlatıcı |
| `hub_client.go` | Windows İstemcisi | Mac Orchestrator HTTP API istemcisi (Slot talebi ve durum sorgulama) |
| `modifier.go` | Windows İstemcisi | Ayar ve konfigürasyon dosyalarını Mac/Win arasında uyarlama |
| `process_windows.go` | Windows İstemcisi | Yerel süreç durum tespiti, log temizleme, ortam yönetimi |

### 4.2 Uçtan Uca İşlem Akışı (Sequence Diagram)

```
[ Kullanıcı ]   [ vanta.exe ]   [ launcher_windows ]   [ Mac Orchestrator ]   [ Riot Server ]
      |               |                 |                       |                   |
      |-- Start ----->|                 |                       |                   |
      |               |-- RequestSlot ->|---------------------->|                   |
      |               |                 |                       |-- Launch RC ----->|
      |               |                 |                       |<- Return Ports ---|
      |               |<- Ports & Args -|<----------------------|                   |
      |               |                 |                       |                   |
      |               |-- Setup Tunnels |                       |                   |
      |               |-- Launch UX --->|                       |                   |
      |               |                 |-- Start Ux.exe ------>|                   |
      |               |                 |   (Tunnels to Mac)    |                   |
      |               |                 |                       |                   |
      | (Matchmade)   |                 |                       |                   |
      |               |-- Poll Status ->|---------------------->|                   |
      |               |                 |                       |-- Detect InGame ->|
      |               |                 |                       |   Capture 4 Args  |
      |               |<- Game Ready ---|<----------------------|                   |
      |               |   (IP, Port, Key, PlayerID)             |                   |
      |               |                 |                       |                   |
      |               |-- Launch Game ->|                       |                   |
      |               |   (via UDP Tun) |-- Start LoL.exe ----->|                   |
      |               |                 |   (Local RAM/DX)      |==================>| (Via Mac IP)
      |               |                 |                       |                   |
      |               |-- Attach Script |                       |                   |
      |               |   (Local Memory)|                       |                   |
```

---

## 5. DETAYLI UYGULAMA FAZLARI

### FAZ 1: MAC ORCHESTRATOR VE İZOLE SLOT YÖNETİMİ

#### 1.1 Slot Dizin Mimarisi
Mac sunucusunda her kullanıcıya özel izole bir çalışma ortamı tahsis edilecektir:
- Kök Dizin: `/Users/m1/slot_homes/slot_{N}/`
- Dizin Yapısı:
  ```
  /Users/m1/slot_homes/slot_0/
  ├── Library/
  │   ├── Application Support/
  │   │   └── Riot Games/
  │   └── Preferences/
  ├── Riot Games/
  └── Logs/
  ```

#### 1.2 Global `pkill` Kaldırılması ve PID Tabanlı Yönetim
Mevcut `vanta_orchestrator.py` içindeki `pkill -9 -f League` ve `pkill -9 -f "Riot Client"` komutları tamamen iptal edilecek, yerine:
1. `SlotState` sınıfına `rc_process: subprocess.Popen` ve `game_process: subprocess.Popen` nesneleri eklenecektir.
2. Slot sonlandırma talebi geldiğinde yalnızca o nesnelerin `pid` değerleri üzerinden `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)` çağrılacaktır.

#### 1.3 Port Havuzu Dağıtım Algoritması
Her slot için statik ve çakışmasız port tahsisi:
- **Slot $N$ Riot Client Proxy Portu:** $8090 + N$ (Örn: Slot 0 -> 8090, Slot 1 -> 8091, ...)
- **Slot $N$ LCU Proxy Portu:** $8100 + N$ (Örn: Slot 0 -> 8100, Slot 1 -> 8101, ...)
- **Slot $N$ UDP Relay Portu:** $8200 + N$ (Oyun trafiği aktarımı için)

---

### FAZ 2: OYUN PARAMETRESİ YAKALAMA VE AKTARIM MOTORU

#### 2.1 Argüman Yakalama Mekanizması
Mac tarafında `LeagueofLegends.app` süreci başladığında, `ps -ww -u m1 -o command` komutu düzenli olarak taranır.
Oyun motoruna iletilen 4 temel parametre regex ile ayrıştırılır:

```python
# Örnek Parametre Formatı:
# "104.160.141.120" "5119" "w8+eJg7...==" "23948102"
GAME_ARGS_REGEX = r'"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"\s+"(\d+)"\s+"([A-Za-z0-9+/=]+)"\s+"(\d+)"'
```

Ayrıştırılan alanlar:
1. `server_ip`: Oyun sunucusu IPv4 adresi.
2. `server_port`: Oyun sunucusu UDP portu (genelde 5000-5500 aralığı).
3. `encryption_key`: Blowfish simetrik paket şifreleme anahtarı (Base64).
4. `summoner_id`: Oyuncu ID'si.

#### 2.2 API Entegrasyonu
Orchestrator `/api/poll_slot` uç noktasına `game_params` objesi eklenir:
```json
{
  "slot_id": 0,
  "status": "game_ready",
  "rc_port": 8090,
  "lcu_port": 8100,
  "game_params": {
    "server_ip": "104.160.141.120",
    "server_port": 5119,
    "encryption_key": "w8+eJg7...==",
    "summoner_id": "23948102"
  }
}
```

---

### FAZ 3: AĞ VE UDP/TCP TÜNELLEME (IP EŞLEME KATMANI)

#### 3.1 UDP Paket Tünelleme Mimarisi
League of Legends oyun motoru, istemci ile sunucu arasındaki veri aktarımını UDP tabanlı ENet protokolü üzerinden gerçekleştirir.

```
[ Win: League of Legends.exe ]
              |  UDP Trafiği (Hedef: 127.0.0.1:8200)
              v
[ Win: vanta_udp_relay ]
              |  Şifreli Tünel (TCP/UDP over SSH)
              v
[ Mac: vanta_udp_forwarder ]
              |  Orijinal UDP Trafiği (Mac Dış IP'si ile)
              v
[ Riot Oyun Sunucusu (104.160.x.x:5119) ]
```

#### 3.2 Tünelleme Kuralları ve Gecikme Optimizasyonu
1. Tünel üzerinde Nagle algoritması devre dışı bırakılacaktır (`TCP_NODELAY = 1`).
2. UDP paket başlıklarındaki kaynak IP alanı, Mac sunucusunun dış bacak IP'si (`51.159.121.126`) olarak paketlenecektir.
3. RTT dalgalanmalarını (jitter) önlemek için yerel arabellek (buffer) boyutu 64 KB olarak sabitlenecektir.

---

### FAZ 4: WINDOWS BAŞLATICI VE PROCESS ORTAM İZOLASYONU

#### 5.1 `launcher_windows.go` Güncellemeleri
`LaunchLeagueGameLocally` fonksiyonu yeniden yapılandırılarak tünellenmiş parametreleri kabul edecek hale getirilecektir:

```go
func LaunchLeagueGameLocally(params GameLaunchParams, localRelayPort int) error {
    gameExe := FindLeagueGameExe()
    if gameExe == "" {
        return fmt.Errorf("League of Legends.exe bulunamadı")
    }

    // Oyun sunucusu hedefi olarak doğrudan Riot IP'si yerine yerel UDP relay portu verilir
    targetHost := fmt.Sprintf("127.0.0.1")
    targetPort := fmt.Sprintf("%d", localRelayPort)

    args := []string{
        targetHost,
        targetPort,
        params.EncryptionKey,
        params.SummonerID,
    }

    cmd := exec.Command(gameExe, args...)
    cmd.Dir = filepath.Dir(gameExe)

    // Ortam değişkenlerini temizle (Sanitized Environment)
    cmd.Env = getSanitizedEnvironment()

    return cmd.Start()
}
```

#### 5.2 Ortam Değişkeni Temizleme (`getSanitizedEnvironment`)
Windows kullanıcı adı, domain bilgisi veya Vanguard izi taşıyabilecek değişkenler (`USERDOMAIN`, `LOGONSERVER`, `COR_ENABLE_PROFILING`) ayıklanır; yalnızca temel sistem değişkenleri (`SYSTEMROOT`, `PATH`, `TEMP`) bırakılır.

---

### FAZ 5: SCRİPT VE BELLEK ERİŞİM ENTEGRASYONU

#### 5.1 Yerel Bellek Görünürlüğü
`League of Legends.exe` yerel bir x86_64 Windows süreci olarak çalıştığı için:
1. Standart Windows API'leri (`OpenProcess`, `VirtualQueryEx`, `ReadProcessMemory`) süreci eksiksiz görüntüler.
2. DirectX 9 / DirectX 11 / DirectX 12 render bağlamları yerel GPU sürücüsünde oluşur; ImGui veya özel DirectX overlay kancaları sorunsuz bağlanır.
3. Oyun motorunun nesne tablosu (ObjectManager), yerel oyuncu göstergesi (LocalPlayer) ve büyü listeleri (SpellBook) standart Windows offsetleriyle doğrudan çözümlenir.

#### 5.2 Vanguard Çakışmasını Engelleme
Windows tarafında `vgc` servisinin durdurulmuş olması oyunun yerel çalışmasını engellemez; çünkü oyun oturumu Mac platformu bayrağıyla açılmıştır ve sunucu taraflı `vgk` kontrolü pasif durumdadır.

---

### FAZ 6: TELEMETRİ, LOG VE İZ TEMİZLEME SİSTEMİ

#### 6.1 Temizlenecek Dizin ve Kayıt Matrisi

| Yol / Konum | Tür | Temizleme Sıklığı |
|---|---|---|
| `%LOCALAPPDATA%\Riot Games\League of Legends\Logs` | Dizin | Oyun öncesi ve her 5 saniyede bir |
| `%LOCALAPPDATA%\Riot Games\Riot Client\Data\RiotGamesPrivateSettings.yaml` | Dosya | Oturum sonlarında |
| `C:\Riot Games\League of Legends\Game\Logs\*.log` | Log | Oyun kapandığı an |
| `C:\Riot Games\League of Legends\Game\Logs\*.dmp` | Crashdump | Anlık |
| Windows Event Log (Application - Riot Events) | Olay Kaydı | Oturum başında |

#### 6.2 `logCleanLoop` Güçlendirmesi
`app.go` içindeki döngü genişletilerek `.log`, `.dmp`, `.nfo` ve `.etl` uzantılı tüm Riot telemetri dosyaları düzenli aralıklarla kalıcı olarak sıfırlanacaktır.

---

## 6. VERİ YAPILARI, STRUCT'LAR VE PROTOKOL TANIMLARI

### 6.1 Go Modelleri (`hub_client.go`)

```go
package main

type GameLaunchParams struct {
    ServerIP      string `json:"server_ip"`
    ServerPort    int    `json:"server_port"`
    EncryptionKey string `json:"encryption_key"`
    SummonerID    string `json:"summoner_id"`
}

type SlotStatusResponse struct {
    SlotID     int              `json:"slot_id"`
    Status     string           `json:"status"` // submitting, preparing, lobby_ready, in_game, terminated
    RCPort     int              `json:"rc_port"`
    LCUPort    int              `json:"lcu_port"`
    UDPRelay   int              `json:"udp_relay_port"`
    GameParams GameLaunchParams `json:"game_params,omitempty"`
    Args       []string         `json:"args,omitempty"`
    Error      string           `json:"error,omitempty"`
}
```

### 6.2 Python Modelleri (`vanta_orchestrator.py`)

```python
from dataclasses import dataclass, field
from typing import Optional, List
import subprocess

@dataclass
class GameParameters:
    server_ip: str = ""
    server_port: int = 0
    encryption_key: str = ""
    summoner_id: str = ""

@dataclass
class SlotSession:
    slot_id: int
    status: str = "idle" # idle, booting, ready, in_game, error
    home_dir: str = ""
    rc_port: int = 0
    lcu_port: int = 0
    udp_port: int = 0
    rc_proc: Optional[subprocess.Popen] = None
    game_proc: Optional[subprocess.Popen] = None
    game_params: GameParameters = field(default_factory=GameParameters)
    client_args: List[str] = field(default_factory=list)
```

---

## 7. HATA YÖNETİMİ, EDGE-CASE VE KURTARMA PROTOKOLLERİ

### 7.1 Karşılaşılabilecek Hata Senaryoları ve Çözümleri

#### Senaryo 1: Oyun Çökmesi (Game Crash / Remake Durumu)
- **Durum:** Yerel `League of Legends.exe` çökerse veya kullanıcı oyundan düşerse.
- **Protokol:** LCU üzerinden `/lol-gameflow/v1/session` durumu `Reconnect` olarak döner. Orchestrator parametreleri saklamaya devam eder; Windows başlatıcı "Reconnect" butonuna basıldığında aynı `GameLaunchParams` ile süreci yeniden başlatır.

#### Senaryo 2: SSH / Ağ Bağlantısının Kesilmesi
- **Durum:** Scaleway sunucusu ile Windows arasındaki TCP tüneli koparsa.
- **Protokol:** `hub_client.go` otomatik olarak exponential backoff ile (1s, 2s, 4s, 8s) yeniden bağlanmayı dener. Bu esnada yerel oyun motorunun UDP tüneli bellekte kuyruklanır ve bağlantı sağlandığı an paketler boşaltılır.

#### Senaryo 3: Slot Sızıntısı (Zombi Süreçler)
- **Durum:** İstemci beklenmedik şekilde kapanırsa Mac'te Riot Client açık kalabilir.
- **Protokol:** Orchestrator'a 60 saniyelik bir heartbeat kontrolü eklenir. İstemciden 60 saniye boyunca `/api/poll_slot` gelmezse ilgili slotun tüm süreçleri otomatik olarak `SIGTERM` ile kapatılır ve portlar serbest bırakılır.

---

## 8. TEST, DOĞRULAMA VE KALİTE GÜVENCE MATRİSİ

| Test Adımı | Hedef Bileşen | Beklenen Sonuç | Doğrulama Yöntemi |
|---|---|---|---|
| **T1: Slot İzolasyonu** | Mac Orchestrator | İki farklı hesaptan eşzamanlı istek atıldığında birbirinin sürecini kapatmaması | Çift istemci simülasyonu (`curl` testleri) |
| **T2: Lobi Tüneli** | `LeagueClientUx.exe` | Lobi arayüzünün sorunsuz açılması, arkadaş listesi ve mağazanın yüklenmesi | UI görsel kontrolü ve log analizi |
| **T3: Parametre Yakalama**| Mac `ps` Parser | Maç başladığı anda 4 argümanın 500ms içinde JSON olarak üretilmesi | Orchestrator log çıktısı doğrulaması |
| **T4: Yerel Oyun Açılışı** | `League of Legends.exe`| Oyun penceresinin 3D render ile yerel ekranda başlaması | DirectX penceresi ve FPS sayacı |
| **T5: UDP Tünelleme** | `vanta_udp_relay` | Oyun içi ping değerinin stabil kalması (~60-70ms) | Oyun içi MS sayacı ve Wireshark doğrulaması |
| **T6: Bellek Erişimi** | Test Script / Reader | Yerel sürecin sanal belleğinden LocalPlayer HP değerinin okunabilmesi | Test okuyucu C++ / Python konsol çıktısı |
| **T7: Log Sanitizasyonu** | Windows Log Cleaner | Oyun kapandıktan sonra hiçbir Riot dizininde log/dmp kalmaması | Dosya sistemi varlık kontrolü |

---

## 9. BAKIM, PERFORMANS VE GELECEK GELİŞTİRMELER

1. **Performans İyileştirmeleri:**
   - UDP relay katmanının CGO / Rust FFI ile derlenerek paket başı gecikmenin <1ms seviyesine indirilmesi.
2. **Otomatik Yama Takibi (Patch Handling):**
   - Mac sunucusundaki `League of Legends.app` sürümü ile yerel Windows sürümünün uyumsuzluk yaşamaması için Orchestrator başlangıcında sürüm manifest kontrolü (`GET /lol-game-data/assets/v1/system.json`) yapılması.
3. **Bellek Güvenliği:**
   - Windows üzerinde script çalıştırılırken `OpenProcess` tanıtıcılarının (handle) gizlenmesi ve `DKOM` (Direct Kernel Object Manipulation) ile süreç listesinden unlinking yapılması.

---

> **Plan Durumu:** Onay Bekliyor  
> **Sıradaki Eylem:** Faz 1 (Mac Orchestrator izole slot yapısı ve PID yönetimi) kodlamasına başlanması.
