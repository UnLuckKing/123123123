import os, shutil

riot_locales = [
    "en_US", "en_GB", "en_AU", "tr_TR", "de_DE", "fr_FR", 
    "es_ES", "es_MX", "pt_BR", "it_IT", "ru_RU", "pl_PL", 
    "el_GR", "ro_RO", "hu_HU", "cs_CZ", "ja_JP", "ko_KR", 
    "zh_CN", "zh_TW", "vi_VN", "th_TH", "id_ID", "ms_MY", "ar_AE"
]

wad_dir = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Localized"
tr_wad = os.path.join(wad_dir, "Global.tr_TR.wad.client")

if os.path.exists(tr_wad):
    created = 0
    for loc in riot_locales:
        target_wad = os.path.join(wad_dir, f"Global.{loc}.wad.client")
        if not os.path.exists(target_wad):
            try:
                # Use hardlink or copy so it takes zero extra disk space if hardlinked
                os.link(tr_wad, target_wad)
                created += 1
            except Exception:
                shutil.copyfile(tr_wad, target_wad)
                created += 1
    print(f"Ensured all {len(riot_locales)} Riot locales exist ({created} created)")
else:
    print("tr_TR wad not found")
