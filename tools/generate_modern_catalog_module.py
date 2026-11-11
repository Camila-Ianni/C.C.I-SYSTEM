"""Generate backend/games/modern_catalog.py from scraped metadata without third-party URLs."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED_PATH = ROOT / "tools" / "modern_catalog_parsed.json"
OUT_MODULE = ROOT / "backend" / "games" / "modern_catalog.py"

CONSOLE_NORMALIZE = {
    "PS5": ("PlayStation 5", "PS5", "ps5", "PKG/ISO", None, False),
    "PS4": ("PlayStation 4", "PS4", "ps4", "PKG", "external:shadps4", False),
    "PS3": ("PlayStation 3", "PS3", "ps3", "ISO/PKG", "external:rpcs3", True),
    "Switch": ("Nintendo Switch", "SWITCH", "switch", "NSP/XCI", "external:ryujinx", True),
    "Switch 2": ("Nintendo Switch 2", "SWITCH 2", "switch2", "NSP", None, False),
    "PS2": ("PlayStation 2", "PS2", "ps2", "ISO", "external:pcsx2", True),
    "PlayStation (PS1)": ("PlayStation 1", "PS1", "ps1", "ISO/ZIP", "cores/pcsx_rearmed_libretro.dylib", True),
}

# Expected filenames for locally downloadable (<4 GB direct CDN) PS3 titles
LOCAL_ROM_HINTS = {
    1: "roms/ps3/Grand Theft Auto San Andreas PS3 - DUPLEX.zip",
    3: "roms/ps3/Minecraft PlayStation 3 Edition.zip",
    6: "roms/ps3/Plants.vs.Zombies.Garden.Warfare.PS3-iMARS.zip",
}

YEAR_OVERRIDES = {
    1: "2015",  # GTA San Andreas PS3 Remaster
    2: "2018",  # FIFA 19 PS3
    3: "2014",  # Minecraft PS3
    4: "2016",  # PES 2017 PS3
    5: "2014",  # Amazing Spider-Man 2 PS3
    6: "2014",  # PvZ Garden Warfare PS3
    7: "2014",  # AC Rogue PS3
    8: "2008",  # Sonic Unleashed PS3
    9: "2013",  # NFS Rivals PS3
    10: "2015", # WRC 5 PS3
    11: "2015", # Lego Jurassic World PS3
    12: "2017", # Gran Turismo Sport
    13: "2015", # FIFA 16
    14: "2015", # COD Black Ops III
    15: "2018", # God of War (2018)
    16: "2016", # Lego Marvel's Avengers
    17: "2013", # NFS Rivals PS4
}


def _slug(s: str) -> str:
    t = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def _infer_dev_genre_players(title: str, console_code: str, raw_genre: str) -> tuple[str, str, str]:
    t = title.lower()
    if "god of war" in t:
        return "Santa Monica Studio", "Acción / Aventura", "1 Jugador"
    if "astro bot" in t:
        return "Team ASOBI / Sony", "Plataformas 3D", "1 Jugador"
    if "sackboy" in t:
        return "Sumo Digital / Sony", "Plataformas 3D", "1-4 Jugadores"
    if "gran turismo" in t:
        return "Polyphony Digital / Sony", "Simulación / Carreras", "1-2 Jugadores"
    if "grand theft auto" in t or "gta" in t:
        return "Rockstar Games", "Acción / Mundo Abierto", "1 Jugador"
    if "marvel rivals" in t:
        return "NetEase Games / Marvel", "Hero Shooter / PvP", "Multijugador"
    if "spider-man" in t:
        return "Beenox / Activision", "Acción / Superhéroes", "1 Jugador"
    if "ea sports" in t or "fifa" in t:
        return "EA Sports", "Deportes / Fútbol" if ("fc" in t or "fifa" in t) else "Rally / Carreras", "1-4 Jugadores"
    if "pro evolution" in t:
        return "Konami", "Deportes / Fútbol", "1-4 Jugadores"
    if "f1 25" in t or "wrc" in t:
        return "Codemasters / EA Sports" if "f1" in t else "Kylotonn", "Carreras / Motorsport", "1-2 Jugadores"
    if "need for speed" in t:
        return "Ghost Games / EA", "Carreras / Arcade", "1 Jugador"
    if "hot wheels" in t:
        return "Milestone / Mattel", "Carreras / Arcade", "1-4 Jugadores"
    if "project drift" in t:
        return "Gaming Factory", "Drift / Carreras", "1 Jugador"
    if "plants vs. zombies" in t:
        return "PopCap / Electronic Arts", "Shooter / Estrategia" if "warfare" in t else "Estrategia / Tower Defense", "1-4 Jugadores"
    if "assassin" in t:
        return "Ubisoft Sofia", "Acción / Sigilo", "1 Jugador"
    if "sonic" in t:
        return "Sonic Team / SEGA", "Plataformas / Velocidad", "1 Jugador"
    if "call of duty" in t:
        return "Treyarch / Activision", "FPS / Acción", "1-4 Jugadores"
    if "lego" in t:
        return "TT Games / Warner Bros.", "Aventura / Familiar", "1-2 Jugadores"
    if "mario kart" in t:
        return "Nintendo EPD", "Carreras / Kart", "1-4 Jugadores"
    if "mario party" in t:
        return "NDcube / Nintendo", "Party / Familiar", "1-4 Jugadores"
    if "luigi's mansion" in t:
        return "Next Level Games / Nintendo", "Aventura / Puzles", "1-2 Jugadores"
    if "donkey kong" in t:
        return "Nintendo EPD", "Plataformas 3D", "1-2 Jugadores"
    if "animal crossing" in t:
        return "Nintendo EPD", "Simulación / Vida", "1-4 Jugadores"
    if "tomodachi" in t:
        return "Nintendo", "Simulación / Social", "1 Jugador"
    if "pokémon" in t or "pokemon" in t or "pokkén" in t:
        return "ILCA / The Pokémon Company" if "diamond" in t else "Bandai Namco / Nintendo", "RPG / Aventura" if "diamond" in t else "Lucha / Arena", "1-2 Jugadores"
    if "kirby" in t:
        return "HAL Laboratory / Nintendo", "Plataformas / Acción", "1-4 Jugadores"
    if "just dance" in t:
        return "Ubisoft", "Música / Baile", "1-6 Jugadores"
    if "mortal kombat" in t:
        return "NetherRealm Studios", "Lucha / Arcade", "1-2 Jugadores"
    if "dragon ball" in t:
        return "Bandai Namco", "Lucha / Arena", "1-2 Jugadores"
    if "jojo" in t:
        return "CyberConnect2 / Bandai Namco", "Lucha / Anime", "1-2 Jugadores"
    if "my hero" in t:
        return "Byking / Bandai Namco", "Acción / Lucha Anime", "1-4 Jugadores"
    if "one piece" in t:
        return "Omega Force / Bandai Namco", "Musou / Acción", "1-2 Jugadores"
    if "silent hill" in t:
        return "Bloober Team / Konami", "Survival Horror", "1 Jugador"
    if "resident evil" in t:
        return "Capcom", "Survival Horror / Acción", "1-2 Jugadores" if "5" in t or "6" in t or "revelations" in t else "1 Jugador"
    if "minecraft" in t:
        return "Mojang Studios", "Sandbox / Supervivencia", "1-4 Jugadores"
    if "cuphead" in t:
        return "Studio MDHR", "Run & Gun / Indie", "1-2 Jugadores"
    if "hollow knight" in t:
        return "Team Cherry", "Metroidvania / Indie", "1 Jugador"
    if "nightmare: the lunatic" in t:
        return "Maetdol Games", "Roguelite / Acción", "1 Jugador"
    if "crash bandicoot" in t:
        return "Vicarious Visions / Activision", "Plataformas 3D", "1 Jugador"
    if "bratz" in t:
        return "Petoons Studio / Outright Games", "Moda / Ritmo / Aventura", "1-2 Jugadores"
    if "star wars" in t:
        return "Ubisoft Massive" if "outlaws" in t else "Aspyr / Lucasfilm Games", "Acción / Ciencia Ficción", "1-2 Jugadores"
    return "Publicación Oficial", raw_genre or "Acción / Aventura", "1-2 Jugadores"


def _build_desc(title: str, console_name: str, genre: str, fmt: str, size_str: str) -> str:
    return (
        f"{title} para {console_name} ({genre}). "
        f"Edición moderna preservada en formato {fmt} ({size_str}) integrada al catálogo OmniDash."
    )


def main():
    parsed = json.load(PARSED_PATH.open(encoding="utf-8"))
    entries = []
    seen_ids = set()

    for p in parsed:
        idx = p["idx"]
        title = p["title"].strip()
        raw_console = p["console"]
        console_name, badge, plat_key, fmt, core_hint, compat = CONSOLE_NORMALIZE[raw_console]

        base_id = f"{plat_key}_{_slug(title)}"
        if idx == 75:
            base_id += "_xci"
            title = f"{title} (XCI)"
        elif idx == 76:
            base_id += "_nsp"
        while base_id in seen_ids:
            base_id = f"{base_id}_{idx}"
        seen_ids.add(base_id)

        dev, genre, players = _infer_dev_genre_players(title, plat_key, p.get("genre", ""))
        year = YEAR_OVERRIDES.get(idx) or p.get("year") or "2024"
        if year == "—":
            year = "2024"

        size_gb = p.get("size_gb")
        size_str = p.get("size_str") or "Cloud"
        cover_rel = p.get("cover_rel") or ""
        local_rom = LOCAL_ROM_HINTS.get(idx)
        is_local_target = bool(local_rom)
        fmt_actual = p.get("format") or fmt

        entries.append({
            "id": base_id,
            "title": title,
            "clean_title": p["title"].strip(),
            "console": console_name,
            "badge": badge,
            "platform_key": plat_key,
            "format": fmt_actual,
            "genre": genre,
            "players": players,
            "core": core_hint,
            "rom": local_rom,
            "cover": cover_rel,
            "year": str(year),
            "developer": dev,
            "desc": _build_desc(title, console_name, genre, fmt_actual, size_str),
            "size": size_str,
            "size_gb": size_gb if size_gb is not None else 4.0,
            "is_compatible": compat,
            "local_candidate": is_local_target,
        })

    header = (
        '"""Catálogo moderno oficial de C.C.I. SYSTEM (90 títulos PS5 / PS4 / PS3 / Switch)."""\n'
        "from __future__ import annotations\n\n"
        f"MODERN_GAMES_CATALOG: list[dict] = {json.dumps(entries, indent=4, ensure_ascii=False)}\n"
    )
    # Replace JSON booleans/nulls with Python True/False/None cleanly
    header = (
        header.replace(": true", ": True")
        .replace(": false", ": False")
        .replace(": null", ": None")
    )
    OUT_MODULE.write_text(header, encoding="utf-8")
    print(f"Generated {OUT_MODULE} with {len(entries)} entries.")


if __name__ == "__main__":
    main()
