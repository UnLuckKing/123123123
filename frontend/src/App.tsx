import { useState, useEffect, useRef } from "react";
import "./App.css";
import logoImg from "./assets/logo.png";
import { BrowserOpenURL } from "../wailsjs/runtime/runtime";
import {
  Login,
  Logout,
  GetStatus,
  GetPlatform,
  GetLicenseInfo,
  PrepareLogin,
  Stop,
  FindRCS,
  AutoAcceptQueue,
  ClaimRewards,
  GetConfigProfiles,
  SaveCurrentConfigProfile,
  ApplyConfigProfile,
  SetAutoConfigSync,
  GetAutoConfigSyncStatus,
  ToggleConfigReadOnly,
  GetLobbyScout,
  DodgeLobby,
  SetCustomLobbyStatus,
  SetRegaliaProfile,
  GetActiveCriticalPrompt,
  ResolveCriticalPrompt,
  PurgeSystemTraces,
  ReconnectGame,
  DismissPostGame,
  StopAutoAccept,
  GetLastError,
  ClearLastError,
  GetLocale,
  LaunchRiotClient,
} from "../wailsjs/go/main/App";
import { getNoAccountStrings, isNoAccountError } from "./i18n";

type Page = "home" | "main" | "scout" | "config" | "profile";

const DISCORD_URL = "https://discord.gg/fpHmB48B6Y";
const YOUTUBE_URL = "https://www.youtube.com/@Vanta_exe";

const openExternal = (url: string) => {
  try {
    BrowserOpenURL(url);
  } catch {
    window.open(url, "_blank");
  }
};

const MAIN_STATUS: Record<string, { label: string; detail: string }> = {
  logged_in: { label: "Ready", detail: "Click Start to begin session" },
  submitting: { label: "Preparing", detail: "Setting up session..." },
  preparing: { label: "Preparing", detail: "Setting up session..." },
  provisioning: { label: "Preparing", detail: "Setting up session..." },
  login_phase: { label: "Preparing", detail: "Setting up session..." },
  fetching_token: { label: "Preparing", detail: "Setting up session..." },
  running: { label: "Ready", detail: "System ready" },
  queued: { label: "In Queue", detail: "Waiting for slot..." },
};

function isMainActive(s: string) {
  return ["submitting", "preparing", "provisioning", "login_phase", "fetching_token", "running", "queued"].includes(s);
}

/* ─── SVG Icons ─── */
const IconMonitor = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <path d="M8 21h8M12 17v4" />
  </svg>
);

const IconEye = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const IconSliders = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="21" x2="4" y2="14" />
    <line x1="4" y1="10" x2="4" y2="3" />
    <line x1="12" y1="21" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12" y2="3" />
    <line x1="20" y1="21" x2="20" y2="16" />
    <line x1="20" y1="12" x2="20" y2="3" />
    <line x1="1" y1="14" x2="7" y2="14" />
    <line x1="9" y1="8" x2="15" y2="8" />
    <line x1="17" y1="16" x2="23" y2="16" />
  </svg>
);

const IconCrown = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 4l3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14v2H5v-2z" />
  </svg>
);

const IconBack = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>
);

const IconChevron = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 18l6-6-6-6" />
  </svg>
);

const IconDiscord = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.894.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
  </svg>
);

const IconYouTube = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
  </svg>
);

const REGALIA_TIERS = [
  { id: "CHALLENGER", label: "Challenger" },
  { id: "GRANDMASTER", label: "Grandmaster" },
  { id: "MASTER", label: "Master" },
  { id: "DIAMOND", label: "Diamond" },
  { id: "EMERALD", label: "Emerald" },
  { id: "PLATINUM", label: "Platinum" },
  { id: "GOLD", label: "Gold" },
  { id: "SILVER", label: "Silver" },
];

function App() {
  const [page, setPage] = useState<Page>("home");
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("disconnected");
  const [username, setUsername] = useState(() => localStorage.getItem("vanta_user") || localStorage.getItem("nrx_user") || "");
  const [rcsPath, setRcsPath] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [license, setLicense] = useState<{ has_license: boolean; expires_at: string } | null>(null);
  const [pingMs, setPingMs] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);

  // Automation & Helpers
  const [autoAcceptEnabled, setAutoAcceptEnabled] = useState(() => localStorage.getItem("vanta_auto_accept") !== "false");
  const [claimingLoot, setClaimingLoot] = useState(false);

  // Config Switcher
  const [profiles, setProfiles] = useState<any[]>([]);
  const [selectedProfile, setSelectedProfile] = useState("Faker (T1)");
  const [autoSyncConfig, setAutoSyncConfig] = useState(false);
  const [readOnlyLock, setReadOnlyLock] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);

  // Lobby Scout
  const [lobbyReport, setLobbyReport] = useState<any | null>(null);
  const [scouting, setScouting] = useState(false);

  // Regalia & Presence
  const [customStatusText, setCustomStatusText] = useState("");
  const [regaliaTier, setRegaliaTier] = useState("CHALLENGER");

  // Critical Prompts (Consent Gate)
  const [criticalPrompt, setCriticalPrompt] = useState<any | null>(null);

  const pollRef = useRef<number | null>(null);
  const prevStatusRef = useRef(status);

  // Critical Action Prompt Poller
  useEffect(() => {
    const pollPrompt = async () => {
      try {
        const p = await GetActiveCriticalPrompt();
        setCriticalPrompt(p);
      } catch {}
    };
    pollPrompt();
    const interval = window.setInterval(pollPrompt, 1500);
    return () => clearInterval(interval);
  }, []);

  const handleResolvePrompt = async (approve: boolean) => {
    if (!criticalPrompt) return;
    try {
      const res = await ResolveCriticalPrompt(criticalPrompt.id, approve);
      if (approve) {
        showToast((criticalPrompt.action_label || "Action") + " completed");
      } else {
        showToast("Cancelled");
      }
      setCriticalPrompt(null);
    } catch (err: any) {
      showToast("Action error: " + (err?.message || err));
    }
  };

  const renderCriticalPrompt = () => {
    if (!criticalPrompt) return null;
    return (
      <div className="critical-prompt-banner">
        <div className="critical-prompt-content">
          <div className="critical-prompt-badge">Critical Action Required</div>
          <div className="critical-prompt-title">{criticalPrompt.title}</div>
          <div className="critical-prompt-message">{criticalPrompt.message}</div>
        </div>
        <div className="critical-prompt-actions">
          <button className="btn-prompt-action" onClick={() => handleResolvePrompt(true)}>
            {criticalPrompt.action_label}
          </button>
          <button className="btn-prompt-cancel" onClick={() => handleResolvePrompt(false)}>
            {criticalPrompt.cancel_label}
          </button>
        </div>
      </div>
    );
  };

  const [locale, setLocale] = useState("");

  const isNoAccount = isNoAccountError(error);

  const renderNoAccountCard = () => {
    const t = getNoAccountStrings(locale);
    return (
      <div className="no-account-card">
        <div className="no-account-header">
          <div className="no-account-icon-wrap">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
              <line x1="18" y1="8" x2="23" y2="13" />
              <line x1="23" y1="8" x2="18" y2="13" />
            </svg>
          </div>
          <div className="no-account-title-wrap">
            <h3 className="no-account-title">{t.title}</h3>
            <span className="no-account-badge">Riot Client</span>
          </div>
        </div>
        <p className="no-account-message">{t.message}</p>
        <div className="no-account-actions">
          <button 
            className="no-account-btn-primary" 
            onClick={async () => {
              showToast(t.openClient + "...");
              try {
                await LaunchRiotClient();
              } catch (e: any) {
                showToast("Launch failed: " + (e?.message || e));
              }
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            <span>{t.openClient}</span>
          </button>
          <button 
            className="no-account-btn-secondary" 
            onClick={async () => {
              try { await ClearLastError(); } catch {}
              setError("");
              handleStartMain();
            }}
          >
            <span>{t.retry}</span>
          </button>
          <button 
            className="no-account-btn-ghost" 
            onClick={async () => {
              try { await ClearLastError(); } catch {}
              setError("");
            }}
          >
            <span>{t.close}</span>
          </button>
        </div>
      </div>
    );
  };

  const renderErrorOrNoAccount = (extraMargin = false) => {
    if (!error) return null;
    if (isNoAccount) {
      return renderNoAccountCard();
    }
    return <div className="error error-bar" style={extraMargin ? { marginTop: 12 } : undefined}>{error}</div>;
  };

  useEffect(() => {
    GetPlatform().then(setPlatform);
    FindRCS().then((p) => { if (p) setRcsPath(p); });
    GetLocale().then(setLocale).catch(() => {});

    pollRef.current = window.setInterval(async () => {
      try { 
        setStatus(await GetStatus()); 
        const lastErr = await GetLastError();
        if (lastErr) {
          setError(lastErr);
        }
      } catch {}
    }, 1000);

    // Latency & health check
    const checkPing = async () => {
      const start = performance.now();
      try {
        const res = await fetch("http://51.159.121.126:9000/api/ping");
        if (res.ok) setPingMs(Math.round(performance.now() - start));
      } catch {
        setPingMs(null);
      }
    };
    checkPing();
    const pingTimer = window.setInterval(checkPing, 5000);

    // Announcements
    const checkAnnounce = async () => {
      try {
        const res = await fetch("http://51.159.121.126:9000/api/announcements");
        if (res.ok) {
          const data = await res.json();
          if (data.active && data.message) setAnnouncement(data.message);
        }
      } catch {}
    };
    checkAnnounce();
    const annTimer = window.setInterval(checkAnnounce, 15000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      clearInterval(pingTimer);
      clearInterval(annTimer);
    };
  }, []);

  // Auto-navigate between home and main only on status state transitions
  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = status;

    // Only switch to main on fresh start transition
    if (!isMainActive(prev) && isMainActive(status)) {
      setPage("main");
    }
    if (status === "logged_in" && isMainActive(prev) && page === "main") {
      setPage("home");
    }
  }, [status]);

  // Periodic lobby polling
  useEffect(() => {
    const pollLobby = async () => {
      try {
        const rep = await GetLobbyScout();
        setLobbyReport(rep);
      } catch {}
    };
    pollLobby();
    const t = window.setInterval(pollLobby, 4000);
    return () => clearInterval(t);
  }, []);

  const refreshProfiles = async () => {
    try {
      const list = await GetConfigProfiles();
      if (list && list.length > 0) {
        setProfiles(list);
        const active = list.find((p: any) => p.is_active);
        if (active) setSelectedProfile(active.name);
      }
      const st = await GetAutoConfigSyncStatus();
      if (st) {
        setAutoSyncConfig(Boolean(st.enabled));
        setReadOnlyLock(Boolean(st.read_only));
        if (st.active_profile) setSelectedProfile(st.active_profile);
      }
    } catch {}
  };

  useEffect(() => {
    refreshProfiles();
  }, [status]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const handleLogin = async () => {
    setError("");
    try { await ClearLastError(); } catch {}
    const res = await Login(username, "");
    if (res === "ok") {
      localStorage.setItem("vanta_user", username);
      setLicense((await GetLicenseInfo()) as any);
    } else {
      setError(res.includes("too many devices") ? "Account active on maximum devices." : res);
    }
  };

  const handleLogout = async () => {
    await Logout();
    try { await ClearLastError(); } catch {}
    localStorage.removeItem("vanta_user");
    setUsername(""); setLicense(null); setError(""); setPage("home");
  };

  const handleStartMain = async () => {
    setError("");
    try { await ClearLastError(); } catch {}
    const res = await PrepareLogin(rcsPath);
    if (res !== "ok") setError(res);
  };

  const handleStop = async () => {
    setError("");
    try { await ClearLastError(); } catch {}
    const res = await Stop();
    if (res !== "ok" && res !== "nothing to stop") setError(res);
  };

  const handleReconnectGame = async () => {
    try {
      showToast("Reconnecting match session...");
      const res = await ReconnectGame();
      if (res === "ok") {
        showToast("Game relaunched successfully!");
      } else {
        setError(res);
        showToast("Error: " + res);
      }
    } catch (err: any) {
      showToast("Error: " + (err?.message || err));
    }
  };

  const handleDismissPostGame = async () => {
    try {
      const res = await DismissPostGame();
      if (res === "ok") {
        showToast("Lobby restored to home screen!");
      } else {
        showToast("Reset: " + res);
      }
    } catch (err: any) {
      showToast("Error: " + (err?.message || err));
    }
  };

  const toggleAutoAccept = async () => {
    if (!autoAcceptEnabled) {
      try {
        await AutoAcceptQueue();
        setAutoAcceptEnabled(true);
        localStorage.setItem("vanta_auto_accept", "true");
        showToast("Auto-Accept Active");
      } catch (err: any) {
        setError("Auto-Accept error: " + (err?.message || err));
      }
    } else {
      try {
        await StopAutoAccept();
      } catch (_) {}
      setAutoAcceptEnabled(false);
      localStorage.setItem("vanta_auto_accept", "false");
      showToast("Auto-Accept Paused");
    }
  };

  const handleClaimRewards = async () => {
    setClaimingLoot(true);
    try {
      const claimed = await ClaimRewards();
      if (claimed && claimed.length > 0) {
        showToast(`Claimed ${claimed.length} items: ${claimed.join(", ")}`);
      } else {
        showToast("No capsules found or client idle");
      }
    } catch (err: any) {
      showToast("Claim error: " + (err?.message || err));
    } finally {
      setClaimingLoot(false);
    }
  };

  const handleApplyConfig = async () => {
    try {
      const res = await ApplyConfigProfile(selectedProfile);
      if (res === "ok") {
        showToast(`Profile '${selectedProfile}' applied!`);
      } else {
        showToast(`Failed: ${res}`);
      }
    } catch (err: any) {
      showToast(`Error: ${err?.message || err}`);
    }
  };

  const handleToggleAutoSync = async () => {
    const next = !autoSyncConfig;
    await SetAutoConfigSync(next, selectedProfile);
    setAutoSyncConfig(next);
    showToast(next ? `Auto-Sync: ${selectedProfile}` : "Auto-Sync disabled");
  };

  const handleToggleReadOnly = async () => {
    const next = !readOnlyLock;
    await ToggleConfigReadOnly(next);
    setReadOnlyLock(next);
    showToast(next ? "PersistedSettings Read-Only Locked" : "Read-Only lock removed");
  };

  const handleSaveCustomProfile = async () => {
    if (!newProfileName.trim()) return;
    const res = await SaveCurrentConfigProfile(newProfileName.trim(), "Custom Player Account Backup");
    if (res === "ok") {
      showToast(`Profile '${newProfileName}' saved!`);
      setShowSaveInput(false);
      setNewProfileName("");
      await refreshProfiles();
    } else {
      showToast(`Save error: ${res}`);
    }
  };

  const handleFetchLobbyScout = async () => {
    setScouting(true);
    try {
      const rep = await GetLobbyScout();
      setLobbyReport(rep);
      if (rep?.in_champ_select) {
        showToast(`Scouted: ${rep.teammates?.length || 0} teammates unmasked`);
      } else {
        showToast("Waiting for Champion Select queue...");
      }
    } catch (err: any) {
      showToast("Scout error: " + (err?.message || err));
    } finally {
      setScouting(false);
    }
  };

  const handleDodgeLobby = async () => {
    if (!confirm("Are you sure you want to Dodge this Champion Select queue?")) return;
    try {
      const res = await DodgeLobby();
      if (res === "ok") {
        showToast("Queue Dodged successfully! (-3 LP saved)");
        setLobbyReport(null);
      } else {
        showToast("Dodge notice: " + res);
      }
    } catch (err: any) {
      showToast("Dodge error: " + (err?.message || err));
    }
  };

  const handleApplyCustomStatus = async () => {
    if (!customStatusText.trim()) return;
    try {
      const res = await SetCustomLobbyStatus(customStatusText.trim());
      if (res === "ok") {
        showToast("Status updated in League Client");
      } else {
        showToast("Error: " + res);
      }
    } catch (err: any) {
      showToast("Error: " + (err?.message || err));
    }
  };

  const handleApplyRegalia = async () => {
    try {
      const res = await SetRegaliaProfile(regaliaTier, regaliaTier);
      if (res === "ok") {
        showToast(`${regaliaTier} Crest applied!`);
      } else {
        showToast("Error: " + res);
      }
    } catch (err: any) {
      showToast("Error: " + (err?.message || err));
    }
  };

  /* ─── 1. LOGIN SCREEN ─── */
  if (status === "disconnected" || status === "connecting") {
    return (
      <div className="app screen-login">
        <div className="mesh-bg" />
        <div className="login-panel">
          <div className="brand">
            <img src={logoImg} alt="VANTA" className="brand-logo" />
            <span className="brand-wordmark">VANTA</span>
          </div>
          <p className="login-eyebrow">Premium Extraction Protocol</p>
          <div className="login-fields">
            <input 
              className="field" 
              type="text" 
              placeholder="Access Key" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()} 
            />
            <button 
              className="btn-signin" 
              onClick={handleLogin}
              disabled={status === "connecting" || !username}
            >
              {status === "connecting" ? (
                <span className="btn-inner"><span className="spinner-xs" /> Authenticating</span>
              ) : "Sign In"}
            </button>
          </div>
          {renderErrorOrNoAccount(true)}
          <div className="login-socials">
            <button 
              className="social-btn social-btn-discord" 
              onClick={() => openExternal(DISCORD_URL)} 
              title="Join Discord Community"
            >
              <IconDiscord />
              <span>Discord</span>
            </button>
            <button 
              className="social-btn social-btn-youtube" 
              onClick={() => openExternal(YOUTUBE_URL)} 
              title="YouTube Channel"
            >
              <IconYouTube />
              <span>YouTube</span>
            </button>
          </div>
          <p className="login-footnote" style={{ textTransform: "uppercase" }}>End-to-End Encrypted</p>
        </div>
      </div>
    );
  }

  const mainOn = isMainActive(status);
  const idle = status === "logged_in";

  const renderNavbar = (currentPage: Page, rightAction?: React.ReactNode) => (
    <header className="topbar">
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button className="btn-back" onClick={() => { setError(""); setPage("home"); }} title="Return to Overview">
          <IconBack /> Back
        </button>
        <img 
          src={logoImg} 
          alt="VANTA" 
          className="brand-logo-sm" 
          style={{ cursor: "pointer" }} 
          onClick={() => { setError(""); setPage("home"); }} 
          title="VANTA Home" 
        />
      </div>
      <div className="topbar-nav">
        <div
          className={`topbar-nav-tab${currentPage === "main" ? " topbar-nav-tab--active" : ""}`}
          onClick={() => { setError(""); setPage("main"); }}
          title="Bypass Engine"
        >
          <span>Engine</span>
        </div>
        <div
          className={`topbar-nav-tab${currentPage === "scout" ? " topbar-nav-tab--active" : ""}`}
          onClick={() => { setError(""); setPage("scout"); }}
          title="Lobby Scout"
        >
          <span>Scout</span>
        </div>
        <div
          className={`topbar-nav-tab${currentPage === "config" ? " topbar-nav-tab--active" : ""}`}
          onClick={() => { setError(""); setPage("config"); }}
          title="Config Switcher"
        >
          <span>Config</span>
        </div>
        <div
          className={`topbar-nav-tab${currentPage === "profile" ? " topbar-nav-tab--active" : ""}`}
          onClick={() => { setError(""); setPage("profile"); }}
          title="Regalia Forge"
        >
          <span>Profile</span>
        </div>
      </div>
      <div className="topbar-end">
        <button
          className="social-btn social-btn-discord social-btn-icon-only"
          onClick={() => openExternal(DISCORD_URL)}
          title="Join Discord Community"
        >
          <IconDiscord />
        </button>
        <button
          className="social-btn social-btn-youtube social-btn-icon-only"
          onClick={() => openExternal(YOUTUBE_URL)}
          title="YouTube Channel"
        >
          <IconYouTube />
        </button>
        {pingMs !== null && (
          <div className="ping-pill" title="Server Latency">
            <span className={`ping-dot ${pingMs < 80 ? "ping-good" : pingMs < 150 ? "ping-fair" : "ping-warn"}`} />
            <span>{pingMs}ms</span>
          </div>
        )}
        {rightAction}
        <button className="btn-ghost" onClick={handleLogout}>Sign out</button>
      </div>
    </header>
  );

  /* ─── 2. HOME SCREEN ─── */
  if (page === "home") {
    return (
      <div className="app screen-main">
        <div className="mesh-bg" />
        <div className="main-wrap">
          <header className="topbar">
            <div className="topbar-brand">
              <img src={logoImg} alt="VANTA" className="brand-logo-sm" />
              <span className="brand-wordmark brand-wordmark-sm">VANTA</span>
              {mainOn && (
                <div className="session-active-badge" onClick={() => setPage("main")} title="Click to view Bypass Engine">
                  <span className="dot dot-purple dot-live" />
                  <span>Bypass Active</span>
                </div>
              )}
            </div>
            <div className="topbar-end">
              <button
                className="social-btn social-btn-discord social-btn-icon-only"
                onClick={() => openExternal(DISCORD_URL)}
                title="Join Discord Community"
              >
                <IconDiscord />
              </button>
              <button
                className="social-btn social-btn-youtube social-btn-icon-only"
                onClick={() => openExternal(YOUTUBE_URL)}
                title="YouTube Channel"
              >
                <IconYouTube />
              </button>
              {pingMs !== null && (
                <div className="ping-pill" title="Server Latency">
                  <span className={`ping-dot ${pingMs < 80 ? "ping-good" : pingMs < 150 ? "ping-fair" : "ping-warn"}`} />
                  <span>{pingMs}ms</span>
                </div>
              )}
              {license?.has_license && (
                <div className="lic-badge"><span className="lic-dot" />Licensed</div>
              )}
              <button className="btn-ghost" onClick={handleLogout}>Sign out</button>
            </div>
          </header>

          {announcement && (
            <div className="announcement-strip">
              <span className="ann-icon">✦</span>
              <span className="ann-text">{announcement}</span>
            </div>
          )}

          {renderErrorOrNoAccount()}
          {toast && <div className="error-bar" style={{ color: '#00f2fe' }}>{toast}</div>}

          <div className="home-cards">
            {/* Card 1: Bypass Engine */}
            <div
              className={`home-card home-card-purple${mainOn ? " home-card--active" : ""}`}
              onClick={() => setPage("main")}
            >
              <div className="home-card-icon icon-purple"><IconMonitor /></div>
              <div className="home-card-body">
                <h3 className="home-card-title">Bypass Engine</h3>
                <p className="home-card-sub">{mainOn ? (MAIN_STATUS[status]?.label ?? "Active") : "Vanguard VM tunnel & token extraction"}</p>
              </div>
              <div className="home-card-end">
                {mainOn && <span className="dot dot-purple dot-live" />}
                <span className="home-card-chevron"><IconChevron /></span>
              </div>
            </div>

            {/* Card 2: Lobby Scout */}
            <div
              className={`home-card home-card-cyan${lobbyReport?.in_champ_select ? " home-card--active" : ""}`}
              onClick={() => setPage("scout")}
            >
              <div className="home-card-icon icon-cyan"><IconEye /></div>
              <div className="home-card-body">
                <h3 className="home-card-title">Lobby Scout</h3>
                <p className="home-card-sub">{lobbyReport?.in_champ_select ? `Lobby Detected (${lobbyReport.grief_score}% Risk)` : "PUUID unmasker & safe queue dodger"}</p>
              </div>
              <div className="home-card-end">
                {lobbyReport?.in_champ_select && <span className="dot dot-cyan dot-live" />}
                <span className="home-card-chevron"><IconChevron /></span>
              </div>
            </div>

            {/* Card 3: Config Switcher */}
            <div
              className={`home-card home-card-emerald${autoSyncConfig ? " home-card--active" : ""}`}
              onClick={() => setPage("config")}
            >
              <div className="home-card-icon icon-emerald"><IconSliders /></div>
              <div className="home-card-body">
                <h3 className="home-card-title">Config Switcher</h3>
                <p className="home-card-sub">{autoSyncConfig ? `Sync Active: ${selectedProfile}` : "Pro esports presets & account backup"}</p>
              </div>
              <div className="home-card-end">
                {autoSyncConfig && <span className="dot dot-emerald dot-live" />}
                <span className="home-card-chevron"><IconChevron /></span>
              </div>
            </div>

            {/* Card 4: Regalia Forge */}
            <div
              className="home-card home-card-amber"
              onClick={() => setPage("profile")}
            >
              <div className="home-card-icon icon-amber"><IconCrown /></div>
              <div className="home-card-body">
                <h3 className="home-card-title">Regalia Forge</h3>
                <p className="home-card-sub">Ranked crest & social status customizer</p>
              </div>
              <div className="home-card-end">
                <span className="home-card-chevron"><IconChevron /></span>
              </div>
            </div>
          </div>

          {/* Quick Automation Pills */}
          <div className="quick-pill-bar">
            <div 
              className={`quick-pill ${autoAcceptEnabled ? "quick-pill--active" : ""}`}
              onClick={toggleAutoAccept}
            >
              <span>{autoAcceptEnabled ? "⚡ Auto-Accept: ON" : "⚪ Auto-Accept: OFF"}</span>
            </div>
            <div 
              className="quick-pill"
              onClick={handleClaimRewards}
            >
              <span>{claimingLoot ? "⏳ Crafting..." : "🎁 Claim Capsules"}</span>
            </div>
          </div>

          {renderCriticalPrompt()}

          <footer className="footer">
            {license?.expires_at ? `License active \u00b7 ${license.expires_at}` : "VANTA Apex Architecture"}
          </footer>
        </div>
      </div>
    );
  }

  /* ─── 3. BYPASS ENGINE PAGE ─── */
  if (page === "main") {
    const st = MAIN_STATUS[status] ?? MAIN_STATUS["logged_in"]!;
    return (
      <div className="app screen-main">
        <div className="mesh-bg" />
        <div className="main-wrap">
          {renderNavbar("main")}

          {renderErrorOrNoAccount()}

          <div className="mode-content">
            <div className={`status-orb orb-purple${mainOn ? " orb--active" : ""}`}>
              <img src={logoImg} alt="VANTA" className="orb-logo" />
              {mainOn && (
                <>
                  <div className="orb-ring" />
                  <div className="orb-ring-inner" />
                  <div className="orb-ring-outer" />
                </>
              )}
            </div>

            <h2 className="mode-label">{st.label}</h2>
            <p className="mode-detail">{st.detail}</p>

            <div className="mode-action" style={{ marginTop: 24 }}>
              {idle && platform === "windows" && (
                <button className="btn-big btn-big-purple" onClick={handleStartMain}>Start Bypass</button>
              )}
              {idle && platform !== "windows" && (
                <p className="mode-hint">Main PC mode is Windows only</p>
              )}
              {mainOn && (
                <button className="btn-big btn-big-stop" onClick={handleStop}>
                  Terminate Session
                </button>
              )}
            </div>
          </div>

          {renderCriticalPrompt()}

          <footer className="footer">
            {license?.expires_at ? `License active \u00b7 ${license.expires_at}` : "VANTA Apex Architecture"}
          </footer>
        </div>
      </div>
    );
  }

  /* ─── 4. LOBBY SCOUT PAGE ─── */
  if (page === "scout") {
    return (
      <div className="app screen-main">
        <div className="mesh-bg" />
        <div className="main-wrap">
          {renderNavbar("scout", (
            <button className="btn-ghost" onClick={handleFetchLobbyScout}>{scouting ? "Scouting..." : "Refresh"}</button>
          ))}

          {renderErrorOrNoAccount()}
          {toast && <div className="error-bar" style={{ color: '#00f2fe' }}>{toast}</div>}

          <div className="mode-content">
            <div className={`status-orb orb-cyan${lobbyReport?.in_champ_select ? " orb--active" : ""}`}>
              <div className="orb-icon"><IconEye /></div>
              {lobbyReport?.in_champ_select && <div className="orb-ring orb-ring-cyan" />}
            </div>

            <h2 className="mode-label">
              {lobbyReport?.in_champ_select ? "Champion Select" : "Lobby Standby"}
            </h2>
            <p className="mode-detail">
              {lobbyReport?.in_champ_select
                ? `Lobby Grief Risk: ${lobbyReport.grief_score}% \u00b7 Phase: ${lobbyReport.phase}`
                : "Waiting for Champion Select queue"}
            </p>

            {lobbyReport?.in_champ_select && lobbyReport.teammates && lobbyReport.teammates.length > 0 ? (
              <div className="scout-roster" style={{ width: '100%', maxWidth: 300 }}>
                {lobbyReport.teammates.map((t: any, i: number) => (
                  <div key={i} className="scout-mini-item">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                      <span className="scout-tag">{t.assigned_role || `P${i+1}`}</span>
                      <span style={{ fontWeight: 600, color: '#fff', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {t.summoner_name} <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 9 }}>#{t.tag_line}</span>
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
                      <span style={{ fontSize: 10, color: t.winrate >= 50 ? '#34d399' : '#f87171', fontWeight: 600 }}>{Math.round(t.winrate)}%</span>
                      <span className="scout-tag" style={{ color: t.risk_level === 'CRITICAL' || t.risk_level === 'HIGH' ? '#f87171' : '#34d399' }}>{t.risk_level}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="detail-panel">
                <div className="detail-row">
                  <span className="detail-key">Queue Listener</span>
                  <span className="detail-val val-on">Active</span>
                </div>
                <div className="detail-row">
                  <span className="detail-key">LCU Socket</span>
                  <span className="detail-val val-on">Connected</span>
                </div>
                <div className="detail-row">
                  <span className="detail-key">Auto-Dodge Guard</span>
                  <span className="detail-val">Armed</span>
                </div>
              </div>
            )}

            <div className="mode-action">
              {lobbyReport?.in_champ_select ? (
                <button 
                  className={`btn-big ${lobbyReport.dodge_recommended ? "btn-big-stop" : "btn-big-cyan"}`}
                  onClick={handleDodgeLobby}
                >
                  {lobbyReport.dodge_recommended ? "Safe Dodge Queue (-3 LP)" : "Dodge Queue"}
                </button>
              ) : (
                <button className="btn-big btn-big-cyan" onClick={handleFetchLobbyScout}>
                  {scouting ? "Scanning..." : "Poll Lobby Now"}
                </button>
              )}
            </div>
          </div>

          {renderCriticalPrompt()}

          <footer className="footer">
            {license?.expires_at ? `License active \u00b7 ${license.expires_at}` : "VANTA Apex Architecture"}
          </footer>
        </div>
      </div>
    );
  }

  /* ─── 5. CONFIG SWITCHER PAGE ─── */
  if (page === "config") {
    return (
      <div className="app screen-main">
        <div className="mesh-bg" />
        <div className="main-wrap">
          {renderNavbar("config", (
            <button className="btn-ghost" onClick={() => setShowSaveInput(!showSaveInput)}>
              {showSaveInput ? "Cancel" : "Backup"}
            </button>
          ))}

          {renderErrorOrNoAccount()}
          {toast && <div className="error-bar" style={{ color: '#10b981' }}>{toast}</div>}

          <div className="mode-content">
            <div className={`status-orb orb-emerald${autoSyncConfig ? " orb--active" : ""}`}>
              <div className="orb-icon"><IconSliders /></div>
              {autoSyncConfig && <div className="orb-ring orb-ring-emerald" />}
            </div>

            <h2 className="mode-label">{selectedProfile}</h2>
            <p className="mode-detail">
              {profiles.find(p => p.name === selectedProfile)?.description || "Pro eSports configuration profile"}
            </p>

            <div style={{ width: '100%', maxWidth: 300 }}>
              {showSaveInput ? (
                <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                  <input 
                    className="field" 
                    type="text" 
                    placeholder="Profile name" 
                    value={newProfileName}
                    onChange={(e) => setNewProfileName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveCustomProfile()}
                  />
                  <button className="btn-ghost" onClick={handleSaveCustomProfile}>Save</button>
                </div>
              ) : (
                <select 
                  className="field-select" 
                  value={selectedProfile}
                  onChange={(e) => setSelectedProfile(e.target.value)}
                >
                  {profiles.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.is_builtin ? `⚡ [PRO] ${p.name}` : `📁 [USER] ${p.name}`}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="detail-panel">
              <div className="detail-row">
                <span className="detail-key">Auto-Sync on Switch</span>
                <span 
                  className={`detail-val ${autoSyncConfig ? "val-on" : ""}`}
                  style={{ cursor: 'pointer' }}
                  onClick={handleToggleAutoSync}
                >
                  {autoSyncConfig ? "Active" : "Disabled"}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-key">PersistedSettings Lock</span>
                <span 
                  className={`detail-val ${readOnlyLock ? "val-on" : ""}`}
                  style={{ cursor: 'pointer' }}
                  onClick={handleToggleReadOnly}
                >
                  {readOnlyLock ? "Read-Only" : "Unlocked"}
                </span>
              </div>
            </div>

            <div className="mode-action">
              <button className="btn-big btn-big-emerald" onClick={handleApplyConfig}>
                Apply to Game
              </button>
            </div>
          </div>

          {renderCriticalPrompt()}

          <footer className="footer">
            {license?.expires_at ? `License active \u00b7 ${license.expires_at}` : "VANTA Apex Architecture"}
          </footer>
        </div>
      </div>
    );
  }

  /* ─── 6. REGALIA FORGE PAGE ─── */
  return (
    <div className="app screen-main">
      <div className="mesh-bg" />
      <div className="main-wrap">
        {renderNavbar("profile")}

        {renderErrorOrNoAccount()}
        {toast && <div className="error-bar" style={{ color: '#f59e0b' }}>{toast}</div>}

        <div className="mode-content">
          <div className="status-orb orb-amber orb--active">
            <div className="orb-icon"><IconCrown /></div>
            <div className="orb-ring orb-ring-amber" />
          </div>

          <h2 className="mode-label">{regaliaTier} Regalia</h2>
          <p className="mode-detail">Ranked crest & social status customizer</p>

          <div style={{ width: '100%', maxWidth: 300, marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 6 }}>
              <input 
                className="field" 
                type="text" 
                placeholder="Custom status message" 
                value={customStatusText}
                onChange={(e) => setCustomStatusText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleApplyCustomStatus()}
              />
              <button className="btn-ghost" onClick={handleApplyCustomStatus}>Set</button>
            </div>
          </div>

          <div style={{ width: '100%', maxWidth: 300 }}>
            <div className="tier-grid-compact">
              {REGALIA_TIERS.map((tier) => (
                <button
                  key={tier.id}
                  className={`tier-btn-compact ${regaliaTier === tier.id ? "tier-btn-compact--active" : ""}`}
                  onClick={() => setRegaliaTier(tier.id)}
                >
                  {tier.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mode-action">
            <button className="btn-big btn-big-amber" onClick={handleApplyRegalia}>
              Apply Crest to Client
            </button>
          </div>
        </div>

        {renderCriticalPrompt()}

        <footer className="footer">
          {license?.expires_at ? `License active · ${license.expires_at}` : "VANTA Apex Architecture"}
        </footer>
      </div>
    </div>
  );
}

export default App;
