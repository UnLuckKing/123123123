export namespace main {
	
	export class ChampSelectRule {
	    auto_pick_enabled: boolean;
	    pick_champion_id: number;
	    auto_ban_enabled: boolean;
	    ban_champion_id: number;
	    auto_runes: boolean;
	
	    static createFrom(source: any = {}) {
	        return new ChampSelectRule(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.auto_pick_enabled = source["auto_pick_enabled"];
	        this.pick_champion_id = source["pick_champion_id"];
	        this.auto_ban_enabled = source["auto_ban_enabled"];
	        this.ban_champion_id = source["ban_champion_id"];
	        this.auto_runes = source["auto_runes"];
	    }
	}
	export class ConfigProfileInfo {
	    name: string;
	    description: string;
	    is_builtin: boolean;
	    author: string;
	    last_updated: string;
	    files_present: string[];
	    is_active: boolean;
	
	    static createFrom(source: any = {}) {
	        return new ConfigProfileInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.description = source["description"];
	        this.is_builtin = source["is_builtin"];
	        this.author = source["author"];
	        this.last_updated = source["last_updated"];
	        this.files_present = source["files_present"];
	        this.is_active = source["is_active"];
	    }
	}
	export class CriticalPrompt {
	    id: string;
	    type: string;
	    title: string;
	    message: string;
	    action_label: string;
	    cancel_label: string;
	    expires_at: number;
	    duration_sec: number;
	    grief_score?: number;
	    metadata?: Record<string, string>;
	
	    static createFrom(source: any = {}) {
	        return new CriticalPrompt(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.type = source["type"];
	        this.title = source["title"];
	        this.message = source["message"];
	        this.action_label = source["action_label"];
	        this.cancel_label = source["cancel_label"];
	        this.expires_at = source["expires_at"];
	        this.duration_sec = source["duration_sec"];
	        this.grief_score = source["grief_score"];
	        this.metadata = source["metadata"];
	    }
	}
	export class InjectorEngineInfo {
	    id: string;
	    name: string;
	    description: string;
	    tag: string;
	    is_installed: boolean;
	
	    static createFrom(source: any = {}) {
	        return new InjectorEngineInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.description = source["description"];
	        this.tag = source["tag"];
	        this.is_installed = source["is_installed"];
	    }
	}
	export class InjectorStatus {
	    selected_engine: string;
	    auto_inject: boolean;
	    game_detected: boolean;
	    game_pid: number;
	    status_text: string;
	    injected: boolean;
	    custom_path: string;
	
	    static createFrom(source: any = {}) {
	        return new InjectorStatus(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.selected_engine = source["selected_engine"];
	        this.auto_inject = source["auto_inject"];
	        this.game_detected = source["game_detected"];
	        this.game_pid = source["game_pid"];
	        this.status_text = source["status_text"];
	        this.injected = source["injected"];
	        this.custom_path = source["custom_path"];
	    }
	}
	export class LobbyTeammate {
	    puuid: string;
	    summoner_name: string;
	    tag_line: string;
	    assigned_role: string;
	    champion_id: number;
	    champion_name: string;
	    recent_winrate: number;
	    recent_games: number;
	    recent_wins: number;
	    streak: number;
	    grief_risk_level: string;
	
	    static createFrom(source: any = {}) {
	        return new LobbyTeammate(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.puuid = source["puuid"];
	        this.summoner_name = source["summoner_name"];
	        this.tag_line = source["tag_line"];
	        this.assigned_role = source["assigned_role"];
	        this.champion_id = source["champion_id"];
	        this.champion_name = source["champion_name"];
	        this.recent_winrate = source["recent_winrate"];
	        this.recent_games = source["recent_games"];
	        this.recent_wins = source["recent_wins"];
	        this.streak = source["streak"];
	        this.grief_risk_level = source["grief_risk_level"];
	    }
	}
	export class LobbyScoutReport {
	    in_champ_select: boolean;
	    phase: string;
	    grief_score: number;
	    dodge_recommended: boolean;
	    teammates: LobbyTeammate[];
	    last_updated: string;
	
	    static createFrom(source: any = {}) {
	        return new LobbyScoutReport(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.in_champ_select = source["in_champ_select"];
	        this.phase = source["phase"];
	        this.grief_score = source["grief_score"];
	        this.dodge_recommended = source["dodge_recommended"];
	        this.teammates = this.convertValues(source["teammates"], LobbyTeammate);
	        this.last_updated = source["last_updated"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	
	export class NoAccountI18n {
	    title: string;
	    message: string;
	    open_client: string;
	    retry: string;
	    close: string;
	
	    static createFrom(source: any = {}) {
	        return new NoAccountI18n(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.title = source["title"];
	        this.message = source["message"];
	        this.open_client = source["open_client"];
	        this.retry = source["retry"];
	        this.close = source["close"];
	    }
	}

}

