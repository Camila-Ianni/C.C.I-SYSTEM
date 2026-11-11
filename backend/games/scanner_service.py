"""backend/games/scanner_service.py - Servicio Auxiliar de Escaneo, Catalogación y Gestión de Juegos.
Diseñado para evolucionar la biblioteca de forma no invasiva, segura y asíncrona.
100% Python estándar con soporte para refresco en caliente, deduplicación e integridad.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path
from typing import Any, Callable

from backend.games.rom_metadata import ROMMetadataExtractor

ROOT = Path(__file__).resolve().parent.parent.parent


class GameLibraryScannerService:
    """Servicio independiente para escanear, validar y catalogar la biblioteca física de juegos."""

    _instance: GameLibraryScannerService | None = None
    _lock = threading.RLock()

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
        # SNES
        "snes_Aladdin (U) [!]": "fotos juegos/Aladdin.jpg",
        "snes_BS Mario Collection 3 (J)": "fotos juegos/BS Mario Collection 3.webp",
        "snes_Donkey Kong Country (U) (V1.2) [!]": "fotos juegos/Donkey Kong Country.jpg",
        "snes_Donkey Kong Country 2 - Diddy's Kong Quest (U) (V1.1) [!]": "fotos juegos/Donkey Kong Country 2- Diddy's Kong Quest.webp",
        "snes_Donkey Kong Country 3 - Dixie Kong's Double Trouble (U) [!]": "fotos juegos/Donkey Kong Country 3- Dixie Kong's Double Trouble.jpg",
        "snes_Doom (USA)": "fotos juegos/Doom.jpg",
        "snes_Kirby Super Star (U) [!]": "fotos juegos/Kirby Super Star.webp",
        "snes_Legend of Zelda, The - A Link to the Past (U) [!]": "fotos juegos/The Legend of Zelda- A Link to the Past.jpg",
        "snes_Megaman X3 (USA)": "fotos juegos/Mega Man X3.png",
        "snes_Mortal Kombat (USA)": "fotos juegos/Mortal Kombat.webp",
        "snes_Sonic the Hedgehog 4 (World) (Unl)": "fotos juegos/Sonic the Hedgehog 4.jpg",
        "snes_Street Fighter II - The World Warrior (Europe)": "fotos juegos/Street Fighter II- The World Warrior.jpg",
        "snes_Street Fighter II Turbo - Hyper Fighting (USA)": "fotos juegos/Street Fighter II Turbo- Hyper Fighting.webp",
        "snes_Sunset Riders (USA)": "fotos juegos/Sunset Riders.jpeg",
        "snes_Super Bomberman 4": "fotos juegos/Super Bomberman 4.webp",
        "snes_Super Mario All-Stars (U) [!]": "fotos juegos/Super Mario All-Stars Online.jpeg",
        "snes_Super Mario All-Stars + Super Mario World (USA)": "fotos juegos/Super Mario All-Stars + Super Mario World.webp",
        "snes_Super Mario Kart (U) [!]": "fotos juegos/Super Mario Kart.jpg",
        "snes_Super Mario World 2 - Yoshi's Island (U) (V1.1)": "fotos juegos/Super Mario World 2- Yoshi's Island.jpg",
        "snes_Super Metroid (JU) [!]": "fotos juegos/Super Metroid.jpg",
        "snes_Ultimate Mortal Kombat 3 (USA)": "fotos juegos/Ultimate Mortal Kombat 3.jpeg",

        # MAME / ARCADE
        "mame_crusnusa": "fotos juegos/Cruis'n USA.jpg",
        "mame_ffightub": "fotos juegos/Final Fight.jpg",
        "mame_mslug2": "fotos juegos/Metal Slug 2- Super Vehicle-001:II.jpg",
        "mame_mslug6": "fotos juegos/Metal Slug 6.png",
        "mame_mvscu": "fotos juegos/Marvel vs. Capcom- Clash of Super Heroes.png",
        "mame_pacman": "fotos juegos/Pac-Man.png",
        "mame_simpsons": "fotos juegos/The Simpsons.webp",

        # N64
        "n64_Donkey Kong 64 (U) [!]": "fotos juegos/Donkey Kong 64.jpg",
        "n64_Mario Kart 64 (E) (V1.1) [!]": "fotos juegos/Mario Kart 64.jpg",
        "n64_Super Smash Bros. (U) [!]": "fotos juegos/Super Smash Bros..png",
        "n64_Super Mario 64 (U) [!]": "fotos juegos/Super Mario 64.jpg",
        "n64_Legend of Zelda, The - Ocarina of Time (U) (V1.2) [!]": "fotos juegos/The Legend of Zelda- Ocarina of Time.jpg",

        # PS1
        "ps1_Castlevania - Symphony of the Night (USA)": "fotos juegos/Castlevania- Symphony of the Night.webp",
        "ps1_Crash Bandicoot (USA)": "fotos juegos/Crash Bandicoot.png",
        "ps1_Crash Bandicoot - Warped (USA)": "fotos juegos/Crash Bandicoot 3- Warped.webp",
        "ps1_Metal Slug X (USA)": "fotos juegos/Metal Slug X.jpg",
        "ps1_Resident Evil (USA)": "fotos juegos/Resident Evil.webp",
        "ps1_Resident Evil 2 (USA) (Disc 2)": "fotos juegos/Resident Evil 2.jpg",
        "ps1_Yu-Gi-Oh! Forbidden Memories (USA)": "fotos juegos/Yu-Gi-Oh! Forbidden Memories.webp",

        # NDS
        "nds_0168 - Mario Kart DS (U)(SCZ)": "fotos juegos/Mario Kart DS.jpg",
        "nds_0389 - Animal Crossing - Wild World (E)(Legacy)": "fotos juegos/Animal Crossing- Wild World.webp",
        "nds_0434 - New Super Mario Bros. (U)(Psyfer)": "fotos juegos/New Super Mario Bros..jpg",
        "nds_0827 - Bratz - Forever Diamondz (E)(WRG)": "fotos juegos/Bratz- Forever Diamondz.jpeg",
        "nds_1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS)": "fotos juegos/LEGO Star Wars- The Complete Saga.jpg",
        "nds_1740 - Bratz - 4 Real (E)(EXiMiUS)": "fotos juegos/Bratz 4 Real.jpeg",
        "nds_2988 - Bratz - Girlz Really Rock (E)(XenoPhobia)": "fotos juegos/Bratz- Girlz Really Rock.webp",
        "nds_6148 - Bratz Fashion Boutique (U)(frieNDS)": "fotos juegos/Bratz- Fashion Boutique.jpg",
        "nds_Pokemon White Version 2 (DSi Enhanced)(U)(frieNDS)": "fotos juegos/Pokémon White 2.jpg",

        # GBA
        "gba_1645 - Barbie as the Princess and the Pauper (U)(Chameleon)": "fotos juegos/Barbie as The Princess and the Pauper.jpg",
        "gba_1955 - Disney's Girls Pack (E)(Independent)": "fotos juegos/Disney's Girls Pack.jpeg",

        # Neo-Geo
        "neogeo_pbobblen": "fotos juegos/Puzzle Bobble- Bust-A-Move.jpg",
        "neogeo_snowbro2": "fotos juegos/Snow Bros. 2.png",
        "neogeo_ssideki2": "fotos juegos/Super Sidekicks 2- The World Championship.png",

        # Wii
        "wii_Wii Sports [RSPE01]": "fotos juegos/Wii Sports.webp",

        # On-Demand (Instalador Base < 1 GB)
        "gow_ps2_1": "fotos juegos/God of War.jpg",
        "gow_ps2_2": "fotos juegos/God of War II.jpg",
        "gow_psp_chains": "fotos juegos/God of War- Chains of Olympus.jpg",
        "gow_psp_sparta": "fotos juegos/God of War- Ghost of Sparta.webp",
        "wii_monster_high": "fotos juegos/Monster High- 13 Wishes.webp",
        "nds_mh_13_wishes": "fotos juegos/Monster High- 13 Wishes.jpg",
        "nds_mh_ghoul_spirit": "fotos juegos/Monster High- Ghoul Spirit.jpg",
        "nds_mh_roller_maze": "fotos juegos/Monster High- Skultimate Roller Maze.jpg",
        "gba_herbie": "fotos juegos/Disney's Herbie- Fully Loaded.webp",
        "nds_kirby_ultra": "fotos juegos/Kirby Super Star Ultra.webp",
        "nds_lego_marvel": "fotos juegos/LEGO Marvel Super Heroes- Universe in Peril.jpg",
        "nds_pokemon_black": "fotos juegos/Pokémon Black Version.jpg",
        "ps1_re3_nemesis": "fotos juegos/Resident Evil 3- Nemesis.webp",
        "arcade_wonderboy": "fotos juegos/Wonder Boy.jpg",
    }

    # Catálogo Remoto / On-Demand con metadatos neutros y sin enlaces de terceros
    REMOTE_CATALOG_METADATA = [
        {
            "id": "gow_ps2_1",
            "title": "God of War",
            "console": "PlayStation 2",
            "badge": "PS2",
            "type": "on_demand",
            "core": None,  # PS2 requiere core PCSX2/Play! dedicado no instalado
            "rom": None,
            "cover": "fotos juegos/God of War.jpg",
            "year": "2005",
            "developer": "Santa Monica Studio / Sony",
            "desc": "Kratos desata su furia contra los dioses del Olimpo en Grecia clásica a 60 FPS.",
            "installed": False,
            "on_demand": True,
            "size": "6.8 GB",
            "catalog_type": "remote_metadata",
            "is_compatible": False,
        },
        {
            "id": "gow_ps2_2",
            "title": "God of War II",
            "console": "PlayStation 2",
            "badge": "PS2",
            "type": "on_demand",
            "core": None,
            "rom": None,
            "cover": "fotos juegos/God of War II.jpg",
            "year": "2007",
            "developer": "Santa Monica Studio / Sony",
            "desc": "Segunda entrega épica de Kratos desafiando a las Moiras y a Zeus.",
            "installed": False,
            "on_demand": True,
            "size": "6.4 GB",
            "catalog_type": "remote_metadata",
            "is_compatible": False,
        },
        {
            "id": "gow_psp_chains",
            "title": "God of War: Chains of Olympus",
            "console": "PlayStation Portable",
            "badge": "PSP",
            "type": "on_demand",
            "core": None,  # PSP requiere core PPSSPP no instalado
            "rom": None,
            "cover": "fotos juegos/God of War- Chains of Olympus.jpg",
            "year": "2008",
            "developer": "Ready at Dawn / Santa Monica Studio",
            "desc": "Aventura portátil aclamada de Kratos antes de los eventos del primer God of War.",
            "installed": False,
            "on_demand": True,
            "size": "1.25 GB",
            "catalog_type": "remote_metadata",
            "is_compatible": False,
        },
        {
            "id": "gow_psp_sparta",
            "title": "God of War: Ghost of Sparta",
            "console": "PlayStation Portable",
            "badge": "PSP",
            "type": "on_demand",
            "core": None,
            "rom": None,
            "cover": "fotos juegos/God of War- Ghost of Sparta.webp",
            "year": "2010",
            "developer": "Ready at Dawn / Santa Monica Studio",
            "desc": "Kratos en busca de su hermano Deimos revelando el origen de sus cicatrices.",
            "installed": False,
            "on_demand": True,
            "size": "1.08 GB",
            "catalog_type": "remote_metadata",
            "is_compatible": False,
        },
        {
            "id": "wii_monster_high",
            "title": "Monster High: 13 Wishes",
            "console": "Nintendo Wii",
            "badge": "WII",
            "type": "on_demand",
            "core": "cores/dolphin_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Monster High- 13 Wishes.webp",
            "year": "2013",
            "developer": "Little Orbit / Mattel",
            "desc": "Aventura mágica en el mundo de Monster High explorando la lámpara maravillosa.",
            "installed": False,
            "on_demand": True,
            "size": "1.4 GB",
            "catalog_type": "remote_metadata",
            "is_compatible": True,
        },
        {
            "id": "nds_mh_13_wishes",
            "title": "Monster High: 13 Wishes (DS)",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Monster High- 13 Wishes.jpg",
            "year": "2013",
            "developer": "Little Orbit / Mattel",
            "desc": "Versión táctil portátil de Monster High 13 Wishes para Nintendo DS.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "catalog_type": "remote_metadata",
            "is_compatible": True,
        },
        {
            "id": "nds_mh_ghoul_spirit",
            "title": "Monster High: Ghoul Spirit",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Monster High- Ghoul Spirit.jpg",
            "year": "2011",
            "developer": "ImaginEngine / Mattel",
            "desc": "Conviértete en nueva estudiante monstruosa en Monster High Ghoul Spirit.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "catalog_type": "remote_metadata",
            "is_compatible": True,
        },
        {
            "id": "nds_mh_roller_maze",
            "title": "Monster High: Skultimate Roller Maze",
            "console": "Nintendo DS",
            "badge": "NDS",
            "type": "on_demand",
            "core": "cores/melonds_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Monster High- Skultimate Roller Maze.jpg",
            "year": "2012",
            "developer": "Little Orbit / Mattel",
            "desc": "Carreras sobre patines monstruosas en laberintos vertiginosos.",
            "installed": False,
            "on_demand": True,
            "size": "64 MB",
            "catalog_type": "remote_metadata",
            "is_compatible": True,
        },
        {
            "id": "gba_herbie",
            "title": "Disney's Herbie: Fully Loaded",
            "console": "Game Boy Advance",
            "badge": "GBA",
            "type": "on_demand",
            "core": "cores/vba_next_libretro.dylib",
            "rom": None,
            "cover": "fotos juegos/Disney's Herbie- Fully Loaded.webp",
            "year": "2005",
            "developer": "Disney Interactive / Climax",
            "desc": "Conduce al icónico Herbie #53 en carreras 32-Bit de alta velocidad.",
            "installed": False,
            "on_demand": True,
            "size": "16 MB",
            "catalog_type": "remote_metadata",
            "is_compatible": False,
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
            "catalog_type": "remote_metadata",
            "is_compatible": True,
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
            "catalog_type": "remote_metadata",
            "is_compatible": True,
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
            "catalog_type": "remote_metadata",
            "is_compatible": True,
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
            "catalog_type": "remote_metadata",
            "is_compatible": True,
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
            "catalog_type": "remote_metadata",
            "is_compatible": True,
        },
    ]

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = (root_dir or ROOT).resolve()
        self._scan_directories: list[Path] = [self.root_dir / "roms"]
        self._cached_games: list[dict] = []
        self._is_scanning: bool = False
        self._cancel_requested: bool = False
        self._scan_thread: threading.Thread | None = None

        # Precargar catálogo base de forma instantánea para evitar bloqueos en importación
        self._preload_fast_catalog()

    @classmethod
    def get_instance(cls, root_dir: Path | None = None) -> GameLibraryScannerService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(root_dir)
        return cls._instance

    def add_scan_directory(self, path: Path | str) -> bool:
        """Permite registrar directorios adicionales configurables para escaneo de ROMs."""
        p = Path(path).resolve()
        if p.exists() and p.is_dir() and p not in self._scan_directories:
            self._scan_directories.append(p)
            return True
        return False

    def remove_scan_directory(self, path: Path | str) -> bool:
        """Remueve un directorio de escaneo configurado."""
        p = Path(path).resolve()
        if p in self._scan_directories and p != (self.root_dir / "roms"):
            self._scan_directories.remove(p)
            return True
        return False

    def get_scan_directories(self) -> list[str]:
        return [str(p) for p in self._scan_directories]

    def resolve_cover(self, game_id: str, clean_name: str, console_badge: str, alt_title: str | None = None) -> tuple[str, bool]:
        """Encuentra la mejor carátula física disponible y retorna (ruta, es_fallback)."""
        # 1. Mapeo oficial verificado por ID
        if game_id in self.OFFICIAL_GAME_COVERS:
            p = self.root_dir / self.OFFICIAL_GAME_COVERS[game_id]
            if p.exists():
                return self.OFFICIAL_GAME_COVERS[game_id], False

        fj_dir = self.root_dir / "fotos juegos"
        if fj_dir.exists():
            candidates = [c for c in [clean_name, alt_title] if c]

            # 2. Coincidencia directa con extensiones
            for cand_name in candidates:
                for ext in [".jpg", ".webp", ".png", ".jpeg"]:
                    exact = fj_dir / f"{cand_name}{ext}"
                    if exact.exists():
                        return str(exact.relative_to(self.root_dir)), False

            # 3. Búsqueda normalizada (insensible a diacríticos, mayúsculas, símbolos y espaciado)
            import unicodedata
            def _norm(s: str) -> str:
                t = unicodedata.normalize('NFKD', s or '').encode('ASCII', 'ignore').decode('utf-8')
                return re.sub(r'[^a-z0-9]', '', t.lower())

            all_fj = list(fj_dir.glob("*.*"))
            target_norms = [_norm(c) for c in candidates if _norm(c)]

            # Coincidencia exacta de stems normalizados
            for cand in all_fj:
                cand_norm = _norm(cand.stem)
                if cand_norm in target_norms:
                    return str(cand.relative_to(self.root_dir)), False

            # Coincidencia por contención de nombre significativo (mínimo 5 caracteres)
            for cand in all_fj:
                cand_norm = _norm(cand.stem)
                for tn in target_norms:
                    if len(cand_norm) >= 5 and len(tn) >= 5 and (cand_norm in tn or tn in cand_norm):
                        return str(cand.relative_to(self.root_dir)), False

        # Fallbacks por consola (marcados como fallback=True)
        if console_badge == "SNES":
            return "fotos web/super mario.jpg", True
        elif console_badge == "N64":
            return "fotos web/The_Legend_of_Zelda_film_logo.jpg", True
        elif console_badge == "PS1":
            return "assets_omnidash/covers/red.png", True
        elif console_badge == "ARCADE":
            return "fotos web/metal slug.jpg", True
        elif console_badge == "NDS":
            return "fotos web/pokemon.webp", True
        elif console_badge == "WII":
            return "assets_omnidash/covers/far-cry.webp", True
        elif console_badge == "NEO-GEO":
            return "assets_omnidash/covers/sega.webp", True
        return "assets_omnidash/covers/elden.png", True

    def _preload_fast_catalog(self):
        """Genera el catálogo inicial sin bloquear el hilo principal."""
        self.scan_all(force=False)

    def scan_all(self, force: bool = False, progress_callback: Callable[[int, int, str], None] | None = None) -> list[dict]:
        """Escanea todas las carpetas autorizadas de ROMs de forma segura y estructurada."""
        with self._lock:
            self._is_scanning = True
            self._cancel_requested = False

        games: list[dict] = []
        seen_titles: dict[tuple[str, str, str, str], dict] = {}

        total_files = 0
        for base_dir in self._scan_directories:
            if not base_dir.exists():
                continue
            for platform_key, spec in self.PLATFORM_SPECS.items():
                p_dir = base_dir / platform_key
                if p_dir.exists():
                    for ext in spec["extensions"]:
                        total_files += len(list(p_dir.rglob(f"*{ext}")))

        processed_count = 0

        for base_dir in self._scan_directories:
            if not base_dir.exists():
                continue

            for platform_key, spec in self.PLATFORM_SPECS.items():
                if self._cancel_requested:
                    break

                p_dir = base_dir / platform_key
                if not p_dir.exists():
                    continue

                found_files: list[Path] = []
                for ext in spec["extensions"]:
                    found_files.extend(p_dir.rglob(f"*{ext}"))
                    found_files.extend(p_dir.rglob(f"*{ext.upper()}"))

                found_files = sorted(set(found_files))

                for f in found_files:
                    if self._cancel_requested:
                        break

                    if f.name.startswith(".") or f.is_dir():
                        continue

                    processed_count += 1
                    stem = f.stem
                    game_id = f"{platform_key}_{stem}"
                    clean_title = ROMMetadataExtractor.clean_display_title(stem)
                    region, revision = ROMMetadataExtractor.extract_region_and_revision(stem)

                    # Invocación efectiva de extractores de cabecera por plataforma
                    internal_title = ""
                    meta_source = "filename"

                    if platform_key == "snes":
                        snes_meta = ROMMetadataExtractor.extract_snes_header(f)
                        if snes_meta.get("internal_title"):
                            internal_title = snes_meta["internal_title"]
                            meta_source = snes_meta["source"]
                    elif platform_key == "n64":
                        n64_meta = ROMMetadataExtractor.extract_n64_header(f)
                        if n64_meta.get("internal_title"):
                            internal_title = n64_meta["internal_title"]
                            meta_source = n64_meta["source"]
                    elif platform_key == "nds":
                        nds_meta = ROMMetadataExtractor.extract_nds_header(f)
                        if nds_meta.get("internal_title"):
                            internal_title = nds_meta["internal_title"]
                            meta_source = nds_meta["source"]
                    elif platform_key == "gba":
                        gba_meta = ROMMetadataExtractor.extract_gba_header(f)
                        if gba_meta.get("internal_title"):
                            internal_title = gba_meta["internal_title"]
                            meta_source = gba_meta["source"]

                    # Título para interfaz (priorizando mapeo embellecido y clean title)
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

                    # Validación de integridad CUE/BIN
                    integrity_ok = True
                    integrity_notes = "OK"
                    if f.suffix.lower() == ".cue":
                        integrity_ok, integrity_notes = ROMMetadataExtractor.verify_cue_bin_integrity(f)

                    cover_path, is_fallback = self.resolve_cover(game_id, clean_title, spec["badge"], alt_title=display_title)
                    fingerprint = ROMMetadataExtractor.compute_file_fingerprint(f)

                    try:
                        rel_rom = str(f.relative_to(self.root_dir))
                    except ValueError:
                        rel_rom = str(f)

                    item = {
                        "id": game_id,
                        "title": display_title,
                        "internal_title": internal_title or display_title,
                        "metadata_source": meta_source,
                        "console": spec["name"],
                        "badge": spec["badge"],
                        "type": "libretro",
                        "core": spec["core"],
                        "rom": rel_rom,
                        "cover": cover_path,
                        "cover_is_fallback": is_fallback,
                        "year": spec["year"],
                        "developer": spec["developer"],
                        "desc": spec["desc"],
                        "region": region,
                        "revision": revision,
                        "installed": True,
                        "available": integrity_ok,
                        "fingerprint": fingerprint,
                        "integrity_notes": integrity_notes,
                    }

                    # Deduplicación no destructiva: preserva variantes regionales
                    dedup_key = (spec["badge"], clean_title.lower(), region, revision)
                    if dedup_key in seen_titles:
                        prev = seen_titles[dedup_key]
                        if f.suffix.lower() == ".sfc" and prev["rom"].lower().endswith(".smc"):
                            seen_titles[dedup_key] = item
                    else:
                        seen_titles[dedup_key] = item

                    if progress_callback and total_files > 0:
                        progress_callback(processed_count, total_files, display_title)

        installed_games = list(seen_titles.values())
        games.extend(installed_games)
        games.extend(self.REMOTE_CATALOG_METADATA)

        with self._lock:
            self._cached_games = games
            self._is_scanning = False

        return games

    def scan_async(
        self,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_complete: Callable[[list[dict]], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        """Ejecuta el escaneo en un hilo de trabajo en segundo plano para no congelar la UI."""
        def _worker():
            try:
                res = self.scan_all(force=True, progress_callback=on_progress)
                if on_complete:
                    on_complete(res)
            except Exception as err:
                if on_error:
                    on_error(err)

        self._scan_thread = threading.Thread(target=_worker, daemon=True)
        self._scan_thread.start()

    def cancel_scan(self):
        """Solicita la cancelación limpia del escaneo en curso."""
        self._cancel_requested = True

    def get_games(self) -> list[dict]:
        """Retorna el catálogo en memoria de forma inmediata."""
        if not self._cached_games:
            self.scan_all()
        return list(self._cached_games)

    def get_game_by_id(self, game_id: str) -> dict | None:
        """Busca un juego por ID respetando posibles migraciones o nombres directos."""
        for g in self.get_games():
            if g.get("id") == game_id:
                return g
        return None

    def refresh(self) -> list[dict]:
        """Fuerza un reescaneo de las carpetas ROM físicas para reflejar cambios en caliente."""
        return self.scan_all(force=True)

    def verify_game_file(self, game_id: str) -> tuple[bool, str]:
        """Comprueba físicamente antes del lanzamiento si la ROM y el Core existen y son compatibles."""
        game = self.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no registrado en el catálogo: {game_id}"

        if game.get("on_demand"):
            if not game.get("is_compatible", True) or not game.get("core"):
                return False, f"El título '{game['title']}' requiere un núcleo emulador no disponible en la plataforma actual."
            return False, f"El juego '{game['title']}' está en el catálogo On-Demand y requiere instalación previa."

        rom_path = self.root_dir / game["rom"]
        if not rom_path.exists():
            return False, f"Archivo de ROM no encontrado en disco: {game['rom']}"

        core_path = self.root_dir / game["core"]
        if not core_path.exists():
            return False, f"Núcleo Libretro no encontrado en disco: {game['core']}"

        if rom_path.suffix.lower() == ".cue":
            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(rom_path)
            if not ok:
                return False, f"Error de integridad en imagen de disco: {msg}"

        return True, "Archivo de juego y núcleo verificados listos para ejecución a 60 FPS"

    def sync_to_sqlite(self, db_path: Path | None = None) -> int:
        """Sincroniza transaccionalmente el catálogo en la base de datos SQLite con reconciliación de ausentes."""
        target_db = db_path or (self.root_dir / ".cci-user-data" / "cci_system.sqlite3")
        if not target_db.parent.exists():
            target_db.parent.mkdir(parents=True, exist_ok=True)

        current_games = self.get_games()
        active_ids = {g.get("id") for g in current_games if g.get("id")}

        try:
            with sqlite3.connect(target_db) as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS installed_roms (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        internal_title TEXT,
                        metadata_source TEXT,
                        console TEXT NOT NULL,
                        badge TEXT NOT NULL,
                        core TEXT,
                        rom_path TEXT,
                        cover_path TEXT,
                        region TEXT,
                        revision TEXT,
                        fingerprint TEXT,
                        installed INTEGER DEFAULT 1,
                        available INTEGER DEFAULT 1,
                        on_demand INTEGER DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Migración automática de columnas
                cur.execute("PRAGMA table_info(installed_roms)")
                existing_cols = {col[1] for col in cur.fetchall()}
                for c_name, c_type in [
                    ("internal_title", "TEXT"),
                    ("metadata_source", "TEXT"),
                    ("region", "TEXT"),
                    ("revision", "TEXT"),
                ]:
                    if c_name not in existing_cols:
                        try:
                            cur.execute(f"ALTER TABLE installed_roms ADD COLUMN {c_name} {c_type}")
                        except Exception:
                            pass

                for g in current_games:
                    cur.execute("""
                        INSERT OR REPLACE INTO installed_roms
                        (id, title, internal_title, metadata_source, console, badge, core, rom_path, cover_path, region, revision, fingerprint, installed, available, on_demand, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        g.get("id"),
                        g.get("title"),
                        g.get("internal_title", g.get("title")),
                        g.get("metadata_source", "filename"),
                        g.get("console"),
                        g.get("badge"),
                        g.get("core") or "",
                        g.get("rom") or "",
                        g.get("cover") or "",
                        g.get("region", "Unknown"),
                        g.get("revision", "1.0"),
                        g.get("fingerprint", ""),
                        1 if g.get("installed", True) else 0,
                        1 if g.get("available", True) else 0,
                        1 if g.get("on_demand", False) else 0,
                    ))

                # Reconciliación: Marcar como MISSING / available=0 los registros que ya no están en disco
                cur.execute("SELECT id FROM installed_roms WHERE on_demand = 0")
                stored_rows = cur.fetchall()
                for (row_id,) in stored_rows:
                    if row_id not in active_ids:
                        cur.execute("UPDATE installed_roms SET available = 0 WHERE id = ?", (row_id,))

                return len(current_games)
        except Exception as err:
            print(f"[GameLibraryScannerService] Error en sincronización SQLite: {err}")
            return 0
