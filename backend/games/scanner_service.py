"""backend/games/scanner_service.py - Servicio Auxiliar de Escaneo, Catalogación y Gestión de Juegos.
Diseñado para evolucionar la lectura de la biblioteca sin modificar emuladores, núcleos ni Libretro.
100% Python estándar con soporte para refresco en caliente, deduplicación e integridad.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from backend.games.rom_metadata import ROMMetadataExtractor

ROOT = Path(__file__).resolve().parent.parent.parent


class GameLibraryScannerService:
    """Servicio independiente para escanear, validar y catalogar la biblioteca física de juegos."""

    _instance: GameLibraryScannerService | None = None

    PLATFORM_SPECS = {
        "snes": {
            "name": "Super Nintendo",
            "badge": "SNES",
            "extensions": [".sfc", ".smc"],
            "core": "cores/snes9x_libretro.dylib",
            "year": "1992",
            "developer": "Nintendo EAD",
            "desc": "Clásico legendario de 16-Bit Super Nintendo preservado a 60 FPS estables.",
        },
        "mame": {
            "name": "Arcade",
            "badge": "ARCADE",
            "extensions": [".zip"],
            "core": "cores/mame2003_plus_libretro.dylib",
            "year": "1991",
            "developer": "Konami / Capcom / Sega",
            "desc": "Cabina recreativa arcade clásica preservada a 60 FPS estables.",
        },
        "n64": {
            "name": "Nintendo 64",
            "badge": "N64",
            "extensions": [".z64", ".v64", ".n64"],
            "core": "cores/mupen64plus_next_libretro.dylib",
            "year": "1996",
            "developer": "Nintendo",
            "desc": "Hito de la revolución poligonal en 3D de 64-Bit a 60 FPS.",
        },
        "ps1": {
            "name": "PlayStation 1",
            "badge": "PS1",
            "extensions": [".cue"],
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "year": "1997",
            "developer": "Sony / Konami / Capcom",
            "desc": "Aventura cinematográfica en formato CD-ROM PlayStation.",
        },
        "nds": {
            "name": "Nintendo DS",
            "badge": "NDS",
            "extensions": [".nds"],
            "core": "cores/melonds_libretro.dylib",
            "year": "2005",
            "developer": "Nintendo",
            "desc": "Doble pantalla interactiva de Nintendo DS preservada a 60 FPS.",
        },
        "gba": {
            "name": "Game Boy Advance",
            "badge": "GBA",
            "extensions": [".gba"],
            "core": "cores/vba_next_libretro.dylib",
            "year": "2004",
            "developer": "Nintendo / Various",
            "desc": "Clásico de 32-Bit Game Boy Advance con gráficos portátiles de alta definición.",
        },
        "neogeo": {
            "name": "Neo-Geo",
            "badge": "NEO-GEO",
            "extensions": [".zip"],
            "core": "cores/fbneo_libretro.dylib",
            "year": "1995",
            "developer": "SNK Neo-Geo",
            "desc": "Arcade 24-Bit SNK Neo-Geo de máxima fidelidad.",
        },
        "wii": {
            "name": "Nintendo Wii",
            "badge": "WII",
            "extensions": [".wbfs"],
            "core": "cores/dolphin_libretro.dylib",
            "year": "2006",
            "developer": "Nintendo",
            "desc": "Innovación por control de movimiento de Nintendo Wii a 60 FPS.",
        },
    }

    # Títulos embellecidos para ROMs Arcade y retro donde el filename es críptico
    ARCADE_TITLE_BEAUTIFY = {
        "mame_crusnusa": "Cruis'n USA",
        "mame_ffightub": "Final Fight",
        "mame_mslug2": "Metal Slug 2",
        "mame_mslug6": "Metal Slug 6",
        "mame_mvscu": "Marvel vs. Capcom: Clash of Super Heroes",
        "mame_pacman": "Pac-Man",
        "mame_simpsons": "The Simpsons Arcade",
        "neogeo_pbobblen": "Puzzle Bobble / Bust-A-Move",
        "neogeo_snowbro2": "Snow Bros. 2",
        "neogeo_ssideki2": "Super Sidekicks 2: The World Championship",
        "snes_Legend of Zelda, The - A Link to the Past (U) [!]": "The Legend of Zelda: A Link to the Past",
        "n64_Legend of Zelda, The - Ocarina of Time (U) (V1.2) [!]": "The Legend of Zelda: Ocarina of Time",
    }

    OFFICIAL_GAME_COVERS = {
        "mame_mslug2": "fotos juegos/Metal Slug 2- Super Vehicle-001:II.jpg",
        "mame_mslug6": "fotos juegos/Metal Slug 6.png",
        "ps1_Castlevania - Symphony of the Night (USA)": "fotos juegos/Castlevania- Symphony of the Night.webp",
        "ps1_Metal Slug X (USA)": "fotos juegos/Metal Slug X.jpg",
        "nds_0168 - Mario Kart DS (U)(SCZ)": "fotos juegos/Mario Kart DS.jpg",
        "snes_Super Mario World 2 - Yoshi's Island (U) (V1.1)": "fotos juegos/Super Mario World 2- Yoshi's Island.jpg",
        "snes_Donkey Kong Country (U) (V1.2) [!]": "fotos juegos/Donkey Kong Country.jpg",
        "snes_Donkey Kong Country 2 - Diddy's Kong Quest (U) (V1.1)": "fotos juegos/Donkey Kong Country 2- Diddy's Kong Quest.jpg",
        "snes_Donkey Kong Country 3 - Dixie Kong's Double Trouble (U) [!]": "fotos juegos/Donkey Kong Country 3- Dixie Kong's Double Trouble!.jpg",
        "n64_Donkey Kong 64 (U) [!]": "fotos juegos/Donkey Kong 64.jpg",
        "snes_Super Mario Kart (U) [!]": "fotos juegos/Super Mario Kart.jpg",
        "n64_Mario Kart 64 (E) (V1.1) [!]": "fotos juegos/Mario Kart 64.jpg",
        "snes_Doom (USA)": "fotos juegos/Doom.jpg",
        "snes_Super Metroid (JU) [!]": "fotos juegos/Super Metroid.jpg",
        "snes_Street Fighter II - The World Warrior (Europe)": "fotos juegos/Street Fighter II- The World Warrior.jpg",
        "snes_Street Fighter II Turbo - Hyper Fighting (USA)": "fotos juegos/Street Fighter II Turbo- Hyper Fighting.jpg",
        "snes_Super Mario All-Stars (U) [!]": "fotos juegos/Super Mario All-Stars.jpg",
        "snes_Super Mario All-Stars + Super Mario World (USA)": "fotos juegos/Super Mario All-Stars + Super Mario World.jpg",
        "snes_Kirby Super Star (U) [!]": "fotos juegos/Kirby Super Star.jpg",
        "snes_Aladdin (U) [!]": "fotos juegos/Aladdin.jpg",
        "snes_Megaman X3 (USA)": "fotos juegos/Mega Man X3.jpg",
        "snes_Mortal Kombat (USA)": "fotos juegos/Mortal Kombat.jpg",
        "snes_Ultimate Mortal Kombat 3 (USA)": "fotos juegos/Ultimate Mortal Kombat 3.jpg",
        "snes_Sunset Riders (USA)": "fotos juegos/Sunset Riders.jpg",
        "snes_Sonic the Hedgehog 4 (World) (Unl)": "fotos juegos/Sonic The Hedgehog 4- Episode 1.jpg",
        "snes_Super Bomberman 4": "fotos juegos/Super Bomberman 4.jpg",
        "snes_Legend of Zelda, The - A Link to the Past (U) [!]": "fotos juegos/The Legend of Zelda- A Link to the Past.jpg",
        "n64_Legend of Zelda, The - Ocarina of Time (U) (V1.2) [!]": "fotos juegos/The Legend of Zelda- Ocarina of Time.jpg",
        "n64_Super Mario 64 (U) [!]": "fotos juegos/Super Mario 64.jpg",
        "n64_Super Smash Bros. (U) [!]": "fotos juegos/Super Smash Bros..jpg",
        "ps1_Crash Bandicoot (USA)": "fotos juegos/Crash Bandicoot.webp",
        "ps1_Crash Bandicoot - Warped (USA)": "fotos juegos/Crash Bandicoot 3- Warped.webp",
        "ps1_Resident Evil (USA)": "fotos juegos/Resident Evil.webp",
        "ps1_Resident Evil 2 (USA) (Disc 2)": "fotos juegos/Resident Evil 2.webp",
        "ps1_Yu-Gi-Oh! Forbidden Memories (USA)": "fotos juegos/Yu-Gi-Oh! Forbidden Memories.webp",
        "nds_0434 - New Super Mario Bros. (U)(Psyfer)": "fotos juegos/New Super Mario Bros..jpg",
        "nds_0389 - Animal Crossing - Wild World (E)(Legacy)": "fotos juegos/Animal Crossing- Wild World.jpg",
        "nds_1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS)": "fotos juegos/LEGO Star Wars- The Complete Saga.jpg",
        "nds_0827 - Bratz - Forever Diamondz (E)(WRG)": "fotos juegos/Bratz- Forever Diamondz.jpg",
        "nds_1740 - Bratz - 4 Real (E)(EXiMiUS)": "fotos juegos/Bratz- 4 Real.jpg",
        "nds_2988 - Bratz - Girlz Really Rock (E)(XenoPhobia)": "fotos juegos/Bratz- Girlz Really Rock.jpg",
        "nds_6148 - Bratz Fashion Boutique (U)(frieNDS)": "fotos juegos/Bratz Fashion Boutique.jpg",
        "gba_1645 - Barbie as the Princess and the Pauper (U)(Chameleon)": "fotos juegos/Barbie as The Princess and the Pauper.jpg",
        "gba_1955 - Disney's Girls Pack (E)(Independent)": "fotos juegos/Disney Princess.jpg",
        "wii_Wii Sports [RSPE01]": "fotos juegos/Wii Sports.jpg",
    }

    # Catálogo On-Demand Legítimo (Sin URLs externas ilegales ni dependencias inseguras)
    AUTHORIZED_ON_DEMAND_CATALOG = [
        {
            "id": "gow_ps2_1",
            "title": "God of War",
            "console": "PlayStation 2",
            "badge": "PS2",
            "type": "on_demand",
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/gow_ps2.png",
            "year": "2005",
            "developer": "Santa Monica Studio / Sony",
            "desc": "Kratos desata su furia contra los dioses del Olimpo en Grecia clásica a 60 FPS.",
            "installed": False,
            "on_demand": True,
            "size": "6.8 GB",
            "vault_package_id": "cci-pkg-gow-ps2",
            "vault_status": "authorized",
        },
        {
            "id": "gow_ps2_2",
            "title": "God of War II",
            "console": "PlayStation 2",
            "badge": "PS2",
            "type": "on_demand",
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/gow_2.png",
            "year": "2007",
            "developer": "Santa Monica Studio / Sony",
            "desc": "Segunda entrega épica de Kratos desafiando a las Moiras y a Zeus.",
            "installed": False,
            "on_demand": True,
            "size": "6.4 GB",
            "vault_package_id": "cci-pkg-gow2-ps2",
            "vault_status": "authorized",
        },
        {
            "id": "gow_psp_chains",
            "title": "God of War: Chains of Olympus",
            "console": "PlayStation Portable",
            "badge": "PSP",
            "type": "on_demand",
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/gow_chains.png",
            "year": "2008",
            "developer": "Ready at Dawn / Santa Monica Studio",
            "desc": "Aventura portátil aclamada de Kratos antes de los eventos del primer God of War.",
            "installed": False,
            "on_demand": True,
            "size": "1.25 GB",
            "vault_package_id": "cci-pkg-gow-chains-psp",
            "vault_status": "authorized",
        },
        {
            "id": "gow_psp_sparta",
            "title": "God of War: Ghost of Sparta",
            "console": "PlayStation Portable",
            "badge": "PSP",
            "type": "on_demand",
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/gow_sparta.png",
            "year": "2010",
            "developer": "Ready at Dawn / Santa Monica Studio",
            "desc": "Kratos en busca de su hermano Deimos revelando el origen de sus cicatrices.",
            "installed": False,
            "on_demand": True,
            "size": "1.08 GB",
            "vault_package_id": "cci-pkg-gow-sparta-psp",
            "vault_status": "authorized",
        },
        {
            "id": "wii_monster_high",
            "title": "Monster High: 13 Wishes",
            "console": "Nintendo Wii",
            "badge": "WII",
            "type": "on_demand",
            "core": "cores/dolphin_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/mh_13_wishes.png",
            "year": "2013",
            "developer": "Little Orbit / Mattel",
            "desc": "Aventura mágica en el mundo de Monster High explorando la lámpara maravillosa.",
            "installed": False,
            "on_demand": True,
            "size": "1.4 GB",
            "vault_package_id": "cci-pkg-mh-13wishes-wii",
            "vault_status": "authorized",
        },
        {
            "id": "nds_mh_13_wishes",
            "title": "Monster High: 13 Wishes (DS)",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/mh_13_wishes.png",
            "year": "2013",
            "developer": "Little Orbit / Mattel",
            "desc": "Versión táctil portátil de Monster High 13 Wishes para Nintendo DS.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "vault_package_id": "cci-pkg-mh-13wishes-nds",
            "vault_status": "authorized",
        },
        {
            "id": "nds_mh_ghoul_spirit",
            "title": "Monster High: Ghoul Spirit",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/mh_ghoul_spirit.png",
            "year": "2011",
            "developer": "ImaginEngine / Mattel",
            "desc": "Conviértete en nueva estudiante monstruosa en Monster High Ghoul Spirit.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "vault_package_id": "cci-pkg-mh-ghoulspirit-nds",
            "vault_status": "authorized",
        },
        {
            "id": "nds_mh_roller_maze",
            "title": "Monster High: Skultimate Roller Maze",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/mh_roller.png",
            "year": "2012",
            "developer": "Little Orbit / Mattel",
            "desc": "Carreras sobre patines monstruosas en laberintos vertiginosos.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "vault_package_id": "cci-pkg-mh-roller-nds",
            "vault_status": "authorized",
        },
        {
            "id": "gba_herbie",
            "title": "Disney's Herbie: Fully Loaded",
            "console": "Game Boy Advance",
            "badge": "GBA",
            "type": "on_demand",
            "core": "cores/vba_next_libretro.dylib",
            "rom": None,
            "cover": "assets_omnidash/covers/herbie.png",
            "year": "2005",
            "developer": "Disney Interactive / Climax",
            "desc": "Conduce al icónico Herbie #53 en carreras 32-Bit de alta velocidad.",
            "installed": False,
            "on_demand": True,
            "size": "16 MB",
            "vault_package_id": "cci-pkg-herbie-gba",
            "vault_status": "authorized",
        },
        {
            "id": "nds_kirby_ultra",
            "title": "Kirby Super Star Ultra",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Kirby Super Star Ultra.webp",
            "year": "2008",
            "developer": "HAL Laboratory / Nintendo",
            "desc": "Remake ampliado para Nintendo DS del legendario juego de SNES con minijuegos táctiles.",
            "installed": False,
            "on_demand": True,
            "size": "128 MB",
            "vault_package_id": "cci-pkg-kirby-ultra-nds",
            "vault_status": "authorized",
        },
        {
            "id": "nds_pokemon_black",
            "title": "Pokémon Black Version",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Pokémon Black Version.jpg",
            "year": "2010",
            "developer": "Game Freak / Nintendo",
            "desc": "Quinta generación de Pokémon en la región de Teselia con Reshiram y el Equipo Plasma.",
            "installed": False,
            "on_demand": True,
            "size": "256 MB",
            "vault_package_id": "cci-pkg-pokemon-black-nds",
            "vault_status": "authorized",
        },
        {
            "id": "nds_lego_marvel",
            "title": "LEGO Marvel Super Heroes: Universe in Peril",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": "roms/nds/6325 - LEGO Marvel Super Heroes Universe in Peril (U)(ABSTRAKT).7z",
            "cover": "fotos juegos/LEGO Marvel Super Heroes- Universe in Peril.jpg",
            "year": "2013",
            "developer": "TT Games / Warner Bros.",
            "desc": "Únete a Iron Man, Spider-Man, Hulk y más héroes de Marvel para detener a Loki.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "vault_package_id": "cci-pkg-lego-marvel-nds",
            "vault_status": "authorized",
        },
        {
            "id": "ps1_re3_nemesis",
            "title": "Resident Evil 3: Nemesis",
            "console": "PlayStation 1",
            "badge": "PS1",
            "type": "on_demand",
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "rom": "roms/ps1/Resident Evil 3 - Nemesis (E) [SLES-02529].bin.ecm",
            "cover": "fotos juegos/Resident Evil 3- Nemesis.webp",
            "year": "1999",
            "developer": "Capcom",
            "desc": "Jill Valentine intenta escapar de Raccoon City mientras el implacable Nemesis la persigue.",
            "installed": False,
            "on_demand": True,
            "size": "450 MB",
            "vault_package_id": "cci-pkg-re3-ps1",
            "vault_status": "authorized",
        },
        {
            "id": "arcade_wonderboy",
            "title": "Wonder Boy",
            "console": "Arcade",
            "badge": "ARCADE",
            "type": "on_demand",
            "core": "cores/mame2003_plus_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Wonder Boy.jpg",
            "year": "1986",
            "developer": "Escape / Sega",
            "desc": "Clásico arcade de plataformas y acción de desplazamiento lateral rescatando a Tina.",
            "installed": False,
            "on_demand": True,
            "size": "12 MB",
            "vault_package_id": "cci-pkg-wonderboy-arcade",
            "vault_status": "authorized",
        },
    ]

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = (root_dir or ROOT).resolve()
        self.roms_dir = self.root_dir / "roms"
        self._cached_games: list[dict] = []
        self._last_scan_time: float = 0.0

    @classmethod
    def get_instance(cls, root_dir: Path | None = None) -> GameLibraryScannerService:
        if cls._instance is None:
            cls._instance = cls(root_dir)
        return cls._instance

    def resolve_cover(self, game_id: str, clean_name: str, console_badge: str) -> str:
        """Encuentra la mejor carátula física disponible en fotos juegos/ o assets."""
        # 1. Carátula oficial asignada por ID
        if game_id in self.OFFICIAL_GAME_COVERS:
            p = self.root_dir / self.OFFICIAL_GAME_COVERS[game_id]
            if p.exists():
                return self.OFFICIAL_GAME_COVERS[game_id]

        # 2. Búsqueda directa por nombre en fotos juegos/
        fj_dir = self.root_dir / "fotos juegos"
        if fj_dir.exists():
            for ext in [".jpg", ".webp", ".png", ".jpeg"]:
                exact = fj_dir / f"{clean_name}{ext}"
                if exact.exists():
                    return str(exact.relative_to(self.root_dir))

            # Búsqueda insensible a mayúsculas
            n_low = clean_name.lower()
            for cand in fj_dir.glob("*.*"):
                if cand.stem.lower() == n_low:
                    return str(cand.relative_to(self.root_dir))

            # Substring match
            for cand in fj_dir.glob("*.*"):
                if n_low in cand.stem.lower() or cand.stem.lower() in n_low:
                    return str(cand.relative_to(self.root_dir))

        # 3. Fallbacks por consola
        if console_badge == "SNES":
            return "fotos web/super mario.jpg"
        elif console_badge == "N64":
            return "fotos web/The_Legend_of_Zelda_film_logo.jpg"
        elif console_badge == "PS1":
            return "assets_omnidash/covers/red.png"
        elif console_badge == "ARCADE":
            return "fotos web/metal slug.jpg"
        elif console_badge == "NDS":
            return "fotos web/pokemon.webp"
        elif console_badge == "WII":
            return "assets_omnidash/covers/far-cry.webp"
        elif console_badge == "NEO-GEO":
            return "assets_omnidash/covers/sega.webp"
        return "assets_omnidash/covers/elden.png"

    def scan_all(self, force: bool = False) -> list[dict]:
        """Escanea todas las carpetas autorizadas de ROMs y genera el catálogo estructurado."""
        games: list[dict] = []
        if not self.roms_dir.exists():
            return games

        # Diccionario para deduplicación por (plataforma, título limpio)
        # Permite priorizar dumps limpios (.sfc sobre .smc, etc.)
        seen_titles: dict[tuple[str, str], dict] = {}

        for platform_key, spec in self.PLATFORM_SPECS.items():
            p_dir = self.roms_dir / platform_key
            if not p_dir.exists():
                continue

            # Buscar archivos compatibles recursivamente
            found_files: list[Path] = []
            for ext in spec["extensions"]:
                found_files.extend(p_dir.rglob(f"*{ext}"))
                found_files.extend(p_dir.rglob(f"*{ext.upper()}"))

            # Ordenar para determinismo
            found_files = sorted(set(found_files))

            for f in found_files:
                if f.name.startswith(".") or f.is_dir():
                    continue

                stem = f.stem
                game_id = f"{platform_key}_{stem}"
                clean_title = ROMMetadataExtractor.clean_display_title(stem)

                # Especiales para MAME y Arcade
                if game_id in self.ARCADE_TITLE_BEAUTIFY:
                    display_title = self.ARCADE_TITLE_BEAUTIFY[game_id]
                elif platform_key == "mame":
                    display_title = stem.upper()
                    if stem.lower() == "simpsons":
                        display_title = "The Simpsons Arcade"
                    elif stem.lower() == "pacman":
                        display_title = "Pac-Man"
                    elif not display_title.startswith("The ") and display_title != "Pac-Man":
                        display_title = f"Arcade: {display_title}"
                elif platform_key == "neogeo":
                    display_title = f"NeoGeo: {stem.upper()}"
                else:
                    display_title = clean_title

                # Verificar integridad específica de CUE/BIN para PS1
                integrity_ok = True
                integrity_notes = "OK"
                if f.suffix.lower() == ".cue":
                    integrity_ok, integrity_notes = ROMMetadataExtractor.verify_cue_bin_integrity(f)

                cover = self.resolve_cover(game_id, clean_title, spec["badge"])
                fingerprint = ROMMetadataExtractor.compute_file_fingerprint(f)

                item = {
                    "id": game_id,
                    "title": display_title,
                    "console": spec["name"],
                    "badge": spec["badge"],
                    "type": "libretro",
                    "core": spec["core"],
                    "rom": str(f.relative_to(self.root_dir)),
                    "cover": cover,
                    "year": spec["year"],
                    "developer": spec["developer"],
                    "desc": spec["desc"],
                    "installed": True,
                    "available": integrity_ok,
                    "fingerprint": fingerprint,
                    "integrity_notes": integrity_notes,
                }

                # Deduplicación inteligente: si ya existe para la misma consola y título,
                # preferir .sfc sobre .smc
                dedup_key = (spec["badge"], clean_title.lower())
                if dedup_key in seen_titles:
                    prev = seen_titles[dedup_key]
                    if f.suffix.lower() == ".sfc" and prev["rom"].lower().endswith(".smc"):
                        seen_titles[dedup_key] = item
                else:
                    seen_titles[dedup_key] = item

        # Consolidar juegos instalados
        installed_games = list(seen_titles.values())
        games.extend(installed_games)

        # Agregar catálogo On-Demand autorizado (sin URLs ilegales)
        games.extend(self.AUTHORIZED_ON_DEMAND_CATALOG)

        self._cached_games = games
        return games

    def get_games(self) -> list[dict]:
        """Retorna el catálogo en memoria o lo escanea si aún no ha sido cargado."""
        if not self._cached_games:
            self.scan_all()
        return self._cached_games

    def get_game_by_id(self, game_id: str) -> dict | None:
        """Busca un juego por su identificador único."""
        for g in self.get_games():
            if g.get("id") == game_id:
                return g
        return None

    def refresh(self) -> list[dict]:
        """Fuerza un reescaneo de las carpetas ROM físicas para reflejar cambios en caliente."""
        return self.scan_all(force=True)

    def verify_game_file(self, game_id: str) -> tuple[bool, str]:
        """Comprueba físicamente antes del lanzamiento si la ROM y el Core existen y son legibles."""
        game = self.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no registrado en catálogo: {game_id}"

        # Si es on-demand, no tiene ROM local aún
        if game.get("on_demand"):
            return False, f"El juego '{game['title']}' está en el catálogo On-Demand y requiere instalación."

        rom_path = self.root_dir / game["rom"]
        if not rom_path.exists():
            return False, f"Archivo de ROM no encontrado en disco: {game['rom']}"

        core_path = self.root_dir / game["core"]
        if not core_path.exists():
            return False, f"Núcleo Libretro no encontrado en disco: {game['core']}"

        # Comprobar CUE/BIN si corresponde
        if rom_path.suffix.lower() == ".cue":
            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(rom_path)
            if not ok:
                return False, f"Error de integridad en imagen de disco: {msg}"

        return True, "Archivo de juego y núcleo verificados listos para ejecución a 60 FPS"

    def sync_to_sqlite(self, db_path: Path | None = None) -> int:
        """Sincroniza el catálogo escaneado en la base de datos SQLite (.cci-user-data/cci_system.sqlite3)."""
        target_db = db_path or (self.root_dir / ".cci-user-data" / "cci_system.sqlite3")
        if not target_db.exists():
            return 0

        conn = sqlite3.connect(target_db)
        cur = conn.cursor()

        # Crear tabla auxiliar para biblioteca de ROMs instaladas sin alterar la tabla 'games' original
        cur.execute("""
            CREATE TABLE IF NOT EXISTS installed_roms (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                console TEXT NOT NULL,
                badge TEXT NOT NULL,
                core TEXT NOT NULL,
                rom_path TEXT,
                cover_path TEXT,
                fingerprint TEXT,
                installed INTEGER DEFAULT 1,
                available INTEGER DEFAULT 1,
                on_demand INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        count = 0
        for g in self.get_games():
            cur.execute("""
                INSERT OR REPLACE INTO installed_roms
                (id, title, console, badge, core, rom_path, cover_path, fingerprint, installed, available, on_demand, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                g.get("id"),
                g.get("title"),
                g.get("console"),
                g.get("badge"),
                g.get("core"),
                g.get("rom"),
                g.get("cover"),
                g.get("fingerprint", ""),
                1 if g.get("installed", True) else 0,
                1 if g.get("available", True) else 0,
                1 if g.get("on_demand", False) else 0,
            ))
            count += 1

        conn.commit()
        conn.close()
        return count
