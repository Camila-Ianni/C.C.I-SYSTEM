"""backend/games/scanner_service.py - Servicio de Escaneo, Catalogación y Gestión de Biblioteca Moderna.
100% Python estándar con soporte para refresco en caliente, deduplicación e integridad.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import threading
import unicodedata
from pathlib import Path
from typing import Any, Callable

from backend.games.modern_catalog import MODERN_GAMES_CATALOG
from backend.games.rom_metadata import ROMMetadataExtractor

ROOT = Path(__file__).resolve().parent.parent.parent


def _build_modern_remote_metadata() -> list[dict]:
    """Construye entradas de catálogo remoto/nube neutrales desde MODERN_GAMES_CATALOG."""
    out: list[dict] = []
    for entry in MODERN_GAMES_CATALOG:
        item = {
            "id": entry["id"],
            "title": entry["title"],
            "clean_title": entry.get("clean_title", entry["title"]),
            "console": entry["console"],
            "badge": entry["badge"],
            "platform_key": entry["platform_key"],
            "format": entry.get("format", "PKG"),
            "genre": entry.get("genre", "Acción / Aventura"),
            "players": entry.get("players", "1-2 Jugadores"),
            "type": "on_demand",
            "core": entry.get("core"),
            "rom": None,
            "expected_rom": entry.get("rom"),
            "cover": entry.get("cover", ""),
            "cover_is_fallback": not bool(entry.get("cover")),
            "year": str(entry.get("year", "2024")),
            "developer": entry.get("developer", "Publicación Oficial"),
            "desc": entry.get("desc", ""),
            "installed": False,
            "on_demand": True,
            "available": False,
            "size": entry.get("size", "Cloud"),
            "size_gb": float(entry.get("size_gb", 4.0)),
            "catalog_type": "remote_metadata",
            "is_compatible": bool(entry.get("is_compatible", False)),
        }
        out.append(item)
    return out


class GameLibraryScannerService:
    """Servicio independiente para escanear, validar y catalogar la biblioteca moderna de juegos."""

    _instance: GameLibraryScannerService | None = None
    _lock = threading.RLock()

    PLATFORM_SPECS = {
        "nes": {
            "name": "Nintendo Entertainment System",
            "badge": "NES",
            "extensions": [".nes", ".zip"],
            "core": "cores/fceumm_libretro.dylib",
            "emulator_app": None,
            "year": "1985",
            "developer": "Nintendo",
            "desc": "Juego local de Nintendo Entertainment System.",
        },
        "gba": {
            "name": "Game Boy Advance",
            "badge": "GBA",
            "extensions": [".gba", ".gbc", ".gb"],
            "core": "cores/mgba_libretro.dylib",
            "emulator_app": None,
            "year": "2001",
            "developer": "Nintendo",
            "desc": "Juego local de Game Boy Advance.",
        },
        "snes": {
            "name": "Super Nintendo",
            "badge": "SNES",
            "extensions": [".smc", ".sfc", ".fig"],
            "core": "cores/snes9x_libretro.dylib",
            "emulator_app": None,
            "year": "1992",
            "developer": "Nintendo",
            "desc": "Juego local de Super Nintendo.",
        },
        "mame": {
            "name": "Arcade Classics",
            "badge": "ARCADE",
            "extensions": [".zip"],
            "core": "cores/mame2003_plus_libretro.dylib",
            "emulator_app": None,
            "year": "1990",
            "developer": "Varios",
            "desc": "Juego local arcade.",
        },
        "model2": {
            "name": "Sega Model 2",
            "badge": "MODEL 2",
            "extensions": [".zip"],
            "core": "cores/mame_libretro.dylib",
            "emulator_app": None,
            "year": "1996",
            "developer": "Sega AM1",
            "desc": "Arcade de Sega Model 2 ejecutado con MAME.",
        },
        "neogeo": {
            "name": "SNK Neo-Geo",
            "badge": "NEO-GEO",
            "extensions": [".zip"],
            "core": "cores/fbneo_libretro.dylib",
            "emulator_app": None,
            "year": "1990",
            "developer": "SNK",
            "desc": "Juego local de Neo-Geo.",
        },
        "n64": {
            "name": "Nintendo 64",
            "badge": "N64",
            "extensions": [".z64", ".n64", ".v64"],
            "core": "cores/mupen64plus_next_libretro.dylib",
            "emulator_app": None,
            "year": "1996",
            "developer": "Nintendo",
            "desc": "Juego local de Nintendo 64.",
        },
        "nds": {
            "name": "Nintendo DS",
            "badge": "NDS",
            "extensions": [".nds"],
            "core": "cores/melonds_libretro.dylib",
            "emulator_app": None,
            "year": "2004",
            "developer": "Nintendo",
            "desc": "Juego local de Nintendo DS.",
        },
        "megadrive": {
            "name": "Sega Mega Drive",
            "badge": "MEGA DRIVE",
            "extensions": [".gen", ".md"],
            "core": "cores/genesis_plus_gx_libretro.dylib",
            "emulator_app": None,
            "year": "1988",
            "developer": "Sega",
            "desc": "Juego local de Sega Mega Drive.",
        },
        "wii": {
            "name": "Nintendo Wii",
            "badge": "WII",
            "extensions": [".iso", ".wbfs", ".rvz"],
            "core": "cores/dolphin_libretro.dylib",
            "emulator_app": None,
            "year": "2006",
            "developer": "Nintendo",
            "desc": "Juego local de Nintendo Wii.",
        },
        "ps5": {
            "name": "PlayStation 5",
            "badge": "PS5",
            "extensions": [".pkg", ".iso", ".rar", ".zip"],
            "core": None,
            "emulator_app": None,
            "year": "2024",
            "developer": "Sony Interactive Entertainment",
            "desc": "Título de nueva generación PlayStation 5 gestionado en biblioteca C.C.I.",
        },
        "ps4": {
            "name": "PlayStation 4",
            "badge": "PS4",
            "extensions": [".pkg", ".iso", ".rar", ".zip"],
            "core": "external:shadps4",
            "emulator_app": "shadPS4",
            "year": "2018",
            "developer": "Sony Interactive Entertainment",
            "desc": "Edición PlayStation 4 compatible con emulador shadPS4.",
        },
        "ps3": {
            "name": "PlayStation 3",
            "badge": "PS3",
            "extensions": [".zip", ".iso", ".pkg", ".7z", ".rar"],
            "core": "external:rpcs3",
            "emulator_app": "RPCS3",
            "year": "2014",
            "developer": "Sony Interactive Entertainment",
            "desc": "Título HD de PlayStation 3 preparado para RPCS3.",
        },
        "switch": {
            "name": "Nintendo Switch",
            "badge": "SWITCH",
            "extensions": [".nsp", ".xci", ".rar", ".zip"],
            "core": "external:ryujinx",
            "emulator_app": "Ryujinx",
            "year": "2022",
            "developer": "Nintendo",
            "desc": "Juego de Nintendo Switch compatible con Ryujinx.",
        },
        "switch2": {
            "name": "Nintendo Switch 2",
            "badge": "SWITCH 2",
            "extensions": [".nsp", ".xci", ".rar", ".zip"],
            "core": None,
            "emulator_app": None,
            "year": "2025",
            "developer": "Nintendo",
            "desc": "Título de nueva generación para Nintendo Switch 2.",
        },
        "ps2": {
            "name": "PlayStation 2",
            "badge": "PS2",
            "extensions": [".iso", ".chd", ".zip"],
            "core": "external:pcsx2",
            "emulator_app": "PCSX2",
            "year": "2005",
            "developer": "Sony Computer Entertainment",
            "desc": "Clásico moderno PlayStation 2 compatible con PCSX2.",
        },
        "ps1": {
            "name": "PlayStation 1",
            "badge": "PS1",
            "extensions": [".cue", ".iso", ".bin", ".zip"],
            "core": "cores/pcsx_rearmed_libretro.dylib",
            "emulator_app": None,
            "year": "1999",
            "developer": "Sony Computer Entertainment",
            "desc": "Clásico PlayStation compatible con motor Libretro nativo.",
        },
    }

    EXTERNAL_EMULATORS: dict[str, tuple[str, list[str], list[str]]] = {
        "external:rpcs3": (
            "RPCS3",
            ["rpcs3", "rpcs3.exe"],
            [
                str(ROOT / "cores/emulators/RPCS3.app"),
                "/Applications/RPCS3.app",
                "C:/Program Files/RPCS3/rpcs3.exe",
                str(Path.home() / "AppData/Local/Programs/RPCS3/rpcs3.exe"),
            ],
        ),
        "external:ryujinx": (
            "Ryujinx",
            ["ryujinx", "Ryujinx", "Astris", "Ryujinx.exe"],
            [
                str(ROOT / "cores/emulators/Ryujinx.app"),
                "/Applications/Ryujinx.app",
                "C:/Program Files/Ryujinx/Ryujinx.exe",
                str(Path.home() / "AppData/Local/Programs/Ryujinx/Ryujinx.exe"),
            ],
        ),
        "external:shadps4": (
            "shadPS4",
            ["shadps4", "shadPS4", "shadPS4.exe"],
            [
                str(ROOT / "cores/emulators/shadPS4.app"),
                "/Applications/shadPS4.app",
                "C:/Program Files/shadPS4/shadPS4.exe",
                str(Path.home() / "AppData/Local/Programs/shadPS4/shadPS4.exe"),
            ],
        ),
        "external:pcsx2": (
            "PCSX2",
            ["pcsx2", "pcsx2-qt", "pcsx2-qt.exe", "pcsx2.exe"],
            [
                str(ROOT / "cores/emulators/PCSX2-v2.8.2.app"),
                "/Applications/PCSX2.app",
                "/Applications/PCSX2-Qt.app",
                "C:/Program Files/PCSX2/pcsx2-qt.exe",
                str(Path.home() / "AppData/Local/Programs/PCSX2/pcsx2-qt.exe"),
            ],
        ),
        "external:ppsspp": (
            "PPSSPP 3D",
            ["PPSSPPSDL", "ppsspp", "PPSSPPWindows64.exe"],
            [
                str(ROOT / "cores/emulators/PPSSPPSDL.app"),
                "/Applications/PPSSPPSDL.app",
                "/Applications/PPSSPP.app",
                "C:/Program Files/PPSSPP/PPSSPPWindows64.exe",
            ],
        ),
    }

    OFFICIAL_GAME_COVERS: dict[str, str] = {
        e["id"]: e["cover"] for e in MODERN_GAMES_CATALOG if e.get("cover")
    }

    REMOTE_CATALOG_METADATA: list[dict] = _build_modern_remote_metadata()

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = (root_dir or ROOT).resolve()
        self._scan_directories: list[Path] = [self.root_dir / "roms"]
        self._cached_games: list[dict] = []
        self._is_scanning: bool = False
        self._cancel_requested: bool = False
        self._scan_thread: threading.Thread | None = None

        # Precarga inmediata para UI sin bloqueos
        self._preload_fast_catalog()

    @classmethod
    def get_instance(cls, root_dir: Path | None = None) -> GameLibraryScannerService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(root_dir)
        return cls._instance

    @classmethod
    def is_rpcs3_firmware_installed(cls) -> bool:
        """Verifica si RPCS3 tiene instalado el firmware oficial de PS3 (dev_flash/vsh/etc/version.txt)."""
        candidates = [
            Path.home() / "Library/Application Support/rpcs3/dev_flash/vsh/etc/version.txt",
            Path.home() / ".config/rpcs3/dev_flash/vsh/etc/version.txt",
            Path.home() / "AppData/Roaming/rpcs3/dev_flash/vsh/etc/version.txt",
            ROOT / "cores/emulators/dev_flash/vsh/etc/version.txt",
        ]
        return any(p.exists() and p.is_file() and p.stat().st_size > 0 for p in candidates)

    @classmethod
    def resolve_external_emulator(cls, core_spec: str | None) -> tuple[str, str] | None:
        """Busca un emulador externo instalado en PATH o /Applications."""
        if not core_spec or not str(core_spec).startswith("external:"):
            return None
        info = cls.EXTERNAL_EMULATORS.get(str(core_spec))
        if not info:
            return None
        label, bins, app_paths = info
        for app_p in app_paths:
            p = Path(app_p)
            if p.exists():
                macos_bin = p / "Contents" / "MacOS"
                if macos_bin.exists():
                    for child in macos_bin.iterdir():
                        if child.is_file() and os.access(child, os.X_OK):
                            return label, str(child)
                return label, str(p)
        for b in bins:
            found = shutil.which(b)
            if found:
                return label, found
        return None

    def add_scan_directory(self, path: Path | str) -> bool:
        """Registra un directorio adicional de escaneo de ROMs."""
        p = Path(path).resolve()
        if p.exists() and p.is_dir() and p not in self._scan_directories:
            self._scan_directories.append(p)
            return True
        return False

    def remove_scan_directory(self, path: Path | str) -> bool:
        """Remueve un directorio adicional de escaneo configurado."""
        p = Path(path).resolve()
        if p in self._scan_directories and p != (self.root_dir / "roms"):
            self._scan_directories.remove(p)
            return True
        return False

    def get_scan_directories(self) -> list[str]:
        return [str(p) for p in self._scan_directories]

    def resolve_cover(
        self,
        game_id: str,
        clean_name: str,
        console_badge: str,
        alt_title: str | None = None,
    ) -> tuple[str, bool]:
        """Resuelve la carátula moderna del juego desde fotos juegos/ o fallback."""
        def _norm(s: str) -> str:
            t = unicodedata.normalize("NFKD", s or "").encode("ASCII", "ignore").decode("utf-8")
            return re.sub(r"[^a-z0-9]", "", t.lower())

        if game_id in self.OFFICIAL_GAME_COVERS:
            cov_p = self.OFFICIAL_GAME_COVERS[game_id]
            if (self.root_dir / cov_p).exists():
                return cov_p, False

        fj_dir = self.root_dir / "fotos juegos"
        if fj_dir.exists():
            candidates = [clean_name, alt_title or "", game_id]
            target_norms = [_norm(c) for c in candidates if _norm(c)]
            all_fj = sorted(fj_dir.glob("*.*"))

            for cand in all_fj:
                c_norm = _norm(cand.stem)
                if c_norm in target_norms:
                    return str(cand.relative_to(self.root_dir)), False

            for cand in all_fj:
                c_norm = _norm(cand.stem)
                for tn in target_norms:
                    if len(c_norm) >= 5 and len(tn) >= 5 and (c_norm in tn or tn in c_norm):
                        return str(cand.relative_to(self.root_dir)), False

        fallback = "assets_omnidash/covers/elden.png"
        if console_badge in ("PS5", "PS4", "PS3"):
            p = self.root_dir / "assets_omnidash" / "covers" / "red.png"
            if p.exists():
                fallback = "assets_omnidash/covers/red.png"
        return fallback, True

    def _preload_fast_catalog(self):
        self.scan_all(force=False)

    @staticmethod
    def _norm_key(text: str) -> str:
        t = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")
        return re.sub(r"[^a-z0-9]", "", t.lower())

    def scan_all(
        self,
        force: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """Escanea carpetas roms/ modernas y combina con la metadata del catálogo moderno."""
        with self._lock:
            self._is_scanning = True
            self._cancel_requested = False

        # Mapa de archivos físicos por plataforma encontrados en disk
        disk_files_by_platform: dict[str, list[Path]] = {k: [] for k in self.PLATFORM_SPECS}
        total_files = 0
        for base_dir in self._scan_directories:
            if not base_dir.exists():
                continue
            for platform_key, spec in self.PLATFORM_SPECS.items():
                p_dir = base_dir / platform_key
                if p_dir.exists():
                    for ext in spec["extensions"]:
                        for ext_variant in (ext, ext.upper()):
                            for f in p_dir.rglob(f"*{ext_variant}"):
                                if (
                                    f.is_file()
                                    and not any(part.startswith(".") for part in f.relative_to(p_dir).parts)
                                    and not f.name.endswith(".part")
                                    and not (platform_key == "neogeo" and f.name.lower() == "neogeo.zip")
                                    and not (platform_key == "model2" and f.name.lower() in {"hd44780.zip", "model1io.zip", "model1io2.zip", "segabill.zip"})
                                ):
                                    if f.suffix.lower() == ".bin" and any(p.suffix.lower() == ".cue" for p in f.parent.glob("*.[cC][uU][eE]")):
                                        continue
                                    disk_files_by_platform[platform_key].append(f)

        for pk in disk_files_by_platform:
            disk_files_by_platform[pk] = sorted(set(disk_files_by_platform[pk]))
            total_files += len(disk_files_by_platform[pk])

        matched_disk_paths: set[Path] = set()
        catalog_games: list[dict] = []
        processed = 0

        for meta in self.REMOTE_CATALOG_METADATA:
            entry = dict(meta)
            pk = entry.get("platform_key", "ps3")
            candidates = disk_files_by_platform.get(pk, [])
            expected_rom = entry.get("expected_rom")

            matched_file: Path | None = None
            from backend.games.package_validator import ROMPackageIdentityValidator

            if expected_rom:
                exp_abs = (self.root_dir / expected_rom).resolve()
                exp_name = Path(expected_rom).name.lower()
                for f in candidates:
                    if f in matched_disk_paths:
                        continue
                    if f.resolve() == exp_abs or f.name.lower() == exp_name:
                        matched_file = f
                        break

            if not matched_file and candidates:
                title_norm = self._norm_key(entry.get("clean_title") or entry.get("title", ""))
                for f in candidates:
                    if f in matched_disk_paths:
                        continue
                    stem_norm = self._norm_key(ROMMetadataExtractor.clean_display_title(f.stem))
                    if title_norm and len(title_norm) >= 5 and (
                        stem_norm == title_norm or title_norm in stem_norm or stem_norm in title_norm
                    ):
                        matched_file = f
                        break

            if matched_file:
                id_ok, id_msg, id_meta = ROMPackageIdentityValidator.verify_package_identity(
                    game_id=str(entry.get("id") or ""),
                    title=str(entry.get("title") or ""),
                    platform_key=pk,
                    rom_path=matched_file,
                    allowed_extensions=self.PLATFORM_SPECS.get(pk, {}).get("extensions", []),
                    expected_rom=expected_rom,
                )
                processed += 1
                try:
                    rel_rom = str(matched_file.relative_to(self.root_dir))
                except ValueError:
                    rel_rom = str(matched_file)

                size_bytes = matched_file.stat().st_size
                integrity_ok = bool(id_ok and size_bytes > 0)
                notes = "OK" if id_ok else id_msg
                if integrity_ok and matched_file.suffix.lower() == ".cue":
                    integrity_ok, notes = ROMMetadataExtractor.verify_cue_bin_integrity(matched_file)

                is_container = id_meta.get("package_kind") == "cci_container"
                # If catalog metadata does not recognize a user's regional or
                # custom dump, leave the file for the local filename catalog below.
                # Valid catalog matches and synthetic containers are consumed here.
                if id_ok or is_container:
                    matched_disk_paths.add(matched_file)
                region, revision = ROMMetadataExtractor.extract_region_and_revision(matched_file.stem)
                entry.update({
                    "type": "libretro" if str(entry.get("core") or "").endswith(".dylib") else "modern",
                    "rom": rel_rom,
                    "installed": bool(integrity_ok and not is_container),
                    "on_demand": bool(is_container or not integrity_ok),
                    "available": integrity_ok,
                    "catalog_type": "local_installed" if (integrity_ok and not is_container) else "invalid_or_container",
                    "metadata_source": "catalog_disk",
                    "region": region,
                    "revision": revision,
                    "fingerprint": ROMMetadataExtractor.compute_file_fingerprint(matched_file),
                    "integrity_notes": notes,
                    "package_kind": id_meta.get("package_kind", "native_rom"),
                    "product_code": id_meta.get("product_code"),
                    "size_bytes": size_bytes,
                })
                if progress_callback and total_files > 0:
                    progress_callback(processed, total_files, entry["title"])

            catalog_games.append(entry)

        # Incluir cualquier ROM adicional no listada que el usuario agregue manualmente a roms/<plat>/
        for pk, files in disk_files_by_platform.items():
            if self._cancel_requested:
                break
            spec = self.PLATFORM_SPECS[pk]
            for f in files:
                if f in matched_disk_paths:
                    continue
                processed += 1
                stem = f.stem
                game_id = f"{pk}_{stem}"
                clean_title = ROMMetadataExtractor.clean_display_title(stem)
                if pk == "nds" and f.name.lower() == "mario kart ds (e).nds":
                    clean_title = "Mario Kart DS - Europe"
                if pk == "model2" and f.name.lower() == "hotd.zip":
                    game_id = "model2_house_of_the_dead"
                    clean_title = "House of the Dead (Model 2)"
                region, revision = ROMMetadataExtractor.extract_region_and_revision(stem)
                cover_path, is_fb = self.resolve_cover(game_id, clean_title, spec["badge"], alt_title=clean_title)
                try:
                    rel_rom = str(f.relative_to(self.root_dir))
                except ValueError:
                    rel_rom = str(f)
                size_mb = round(f.stat().st_size / (1024 * 1024), 1)
                size_str = f"{round(size_mb / 1024, 2)} GB" if size_mb >= 1024 else f"{size_mb} MB"

                catalog_games.append({
                    "id": game_id,
                    "title": clean_title,
                    "clean_title": clean_title,
                    "internal_title": clean_title,
                    "metadata_source": "filename",
                    "console": spec["name"],
                    "badge": spec["badge"],
                    "platform_key": pk,
                    "format": f.suffix.lstrip(".").upper() or "ROM",
                    "type": "libretro" if str(spec["core"] or "").endswith(".dylib") else "modern",
                    "core": spec["core"],
                    "rom": rel_rom,
                    "cover": cover_path,
                    "cover_is_fallback": is_fb,
                    "year": spec["year"],
                    "developer": spec["developer"],
                    "desc": spec["desc"],
                    "region": region,
                    "revision": revision,
                    "size": size_str,
                    "installed": True,
                    "on_demand": False,
                    "available": True,
                    "fingerprint": ROMMetadataExtractor.compute_file_fingerprint(f),
                    "integrity_notes": "OK",
                    "is_compatible": spec["core"] is not None,
                })
                if progress_callback and total_files > 0:
                    progress_callback(processed, total_files, clean_title)

        try:
            from backend.games.storage_manager import GameStorageManager, parse_size_to_bytes

            storage_mgr = GameStorageManager.get_instance(self.root_dir)
            for item in catalog_games:
                prog = storage_mgr.get_progress(str(item.get("id") or ""))
                item["has_saved_data"] = prog["has_progress"]
                item["save_slots"] = prog["save_slots"]
                item["saves_label"] = prog["saves_label"]
                item["play_time_seconds"] = prog["play_time_seconds"]
                item["play_time_label"] = prog["play_time_label"]
                item["progress_pct"] = prog["progress_pct"]
                item["progress_label"] = prog["progress_label"]
                item["last_played"] = prog["last_played"]
                if not item.get("size_bytes"):
                    item["size_bytes"] = parse_size_to_bytes(str(item.get("size") or ""))
        except Exception:
            pass

        # La biblioteca visible contiene solo paquetes locales instalados en roms/.
        # La metadata remota sigue disponible por ID para el flujo de instalación,
        # pero no se mezcla con los juegos que aparecen como parte de la colección.
        library_games = []
        roms_root = (self.root_dir / "roms").resolve()
        for item in catalog_games:
            if not item.get("installed") or item.get("on_demand") or not item.get("rom"):
                continue
            rom_path = Path(str(item["rom"]))
            if not rom_path.is_absolute():
                rom_path = self.root_dir / rom_path
            try:
                rom_path = rom_path.resolve()
                rom_path.relative_to(roms_root)
            except (OSError, ValueError):
                continue
            if rom_path.is_file():
                library_games.append(item)

        with self._lock:
            self._cached_games = library_games
            self._is_scanning = False

        return list(library_games)

    def scan_async(
        self,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_complete: Callable[[list[dict]], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        """Ejecuta el escaneo en segundo plano sin bloquear el hilo principal de Qt."""
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
        self._cancel_requested = True

    def get_games(self) -> list[dict]:
        if not self._cached_games:
            self.scan_all()
        return list(self._cached_games)

    def get_game_by_id(self, game_id: str) -> dict | None:
        for g in self.get_games():
            if g.get("id") == game_id:
                return g
        # Mantener resolución interna por ID para descargas iniciadas desde
        # flujos explícitos; estos registros no se publican en la biblioteca.
        for game in self.REMOTE_CATALOG_METADATA:
            if str(game.get("id") or "") == str(game_id):
                return dict(game)
        return None

    def refresh(self) -> list[dict]:
        return self.scan_all(force=True)

    def verify_game_file(self, game_id: str) -> tuple[bool, str]:
        """Comprueba físicamente antes del lanzamiento si la ROM y el emulador están listos."""
        game = self.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no registrado en el catálogo: {game_id}"

        if game.get("on_demand"):
            badge = game.get("badge", "ROM")
            size = game.get("size", "")
            if badge == "PS5" or badge == "SWITCH 2":
                return (
                    False,
                    f"'{game['title']}' ({badge} · {size}) está en la nube On-Demand. "
                    f"Aún no existe emulador comercial estable para {game.get('console')}.",
                )
            if not game.get("is_compatible", True) or not game.get("core"):
                return (
                    False,
                    f"El título '{game['title']}' ({size}) está disponible en la nube para {game.get('console')}.",
                )
            return (
                False,
                f"El juego '{game['title']}' ({size}) está en la nube On-Demand y requiere descarga previa en roms/{game.get('platform_key', 'ps3')}/.",
            )

        rom_val = str(game.get("rom") or "")
        rom_path = Path(rom_val) if Path(rom_val).is_absolute() else (self.root_dir / rom_val)
        if not rom_val or not rom_path.exists():
            return False, f"Archivo de ROM no encontrado en disco: {rom_val}"

        from backend.games.package_validator import ROMPackageIdentityValidator

        plat_key = str(game.get("platform_key") or "ps3")
        try:
            rom_rel = rom_path.resolve().relative_to((self.root_dir / "roms").resolve())
            is_local_library_rom = bool(rom_rel.parts and rom_rel.parts[0].lower() == plat_key.lower())
        except (OSError, ValueError):
            is_local_library_rom = False
        id_ok, id_msg, id_meta = ROMPackageIdentityValidator.verify_package_identity(
            game_id=str(game.get("id") or game_id),
            title=str(game.get("title") or ""),
            platform_key=plat_key,
            rom_path=rom_path,
            allowed_extensions=self.PLATFORM_SPECS.get(plat_key, {}).get("extensions", []),
            expected_rom=game.get("expected_rom"),
            allow_local_filename_identity=is_local_library_rom,
        )
        if not id_ok:
            return False, f"Error de identidad o asociación de paquete: {id_msg}"

        if id_meta.get("package_kind") == "cci_container":
            return False, f"El archivo '{rom_path.name}' es únicamente un contenedor de prueba CCI_PKG_V2 y no un juego real."

        # H-07: Verificar unicidad antes de autorizar ejecución
        for other in self.get_games():
            other_id = str(other.get("id") or "")
            other_rom = other.get("rom")
            if other_id != str(game_id) and other_rom and not other.get("on_demand"):
                other_p = Path(str(other_rom)) if Path(str(other_rom)).is_absolute() else (self.root_dir / str(other_rom))
                try:
                    if other_p.resolve() == rom_path.resolve():
                        return False, f"Asociación inválida: el archivo '{rom_path.name}' está compartido con '{other_id}'."
                except Exception:
                    pass

        core = game.get("core")
        if not core or plat_key in ("ps5", "switch2"):
            return (
                False,
                f"Juego no jugable: no existe emulador comercial compatible configurado para {game.get('console')}.",
            )

        if str(core).startswith("external:"):
            emu = self.resolve_external_emulator(str(core))
            if not emu:
                label = self.EXTERNAL_EMULATORS.get(str(core), (str(core),))[0]
                return (
                    False,
                    f"Juego no jugable: ROM instalada localmente en '{rom_val}', pero falta instalar {label} en /Applications o PATH.",
                )
            if str(core) == "external:rpcs3" and not self.is_rpcs3_firmware_installed():
                return (
                    False,
                    "RPCS3 está instalado, pero falta instalar el firmware oficial de PS3 (PS3UPDAT.PUP).",
                )
            return True, f"ROM y emulador externo {emu[0]} verificados."

        core_path = self.root_dir / str(core)
        if not core_path.exists():
            return False, f"Núcleo Libretro no encontrado en disco: {core}"

        if rom_path.suffix.lower() == ".cue":
            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(rom_path)
            if not ok:
                return False, f"Error de integridad en imagen de disco: {msg}"

        return True, "Archivo de juego y núcleo verificados listos para ejecución a 60 FPS"

    def sync_to_sqlite(self, db_path: Path | None = None) -> int:
        """Sincroniza transaccionalmente el catálogo moderno en SQLite con reconciliación."""
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
                    is_inst = 1 if g.get("installed", False) else 0
                    is_avail = 1 if g.get("available", False) else 0
                    cur.execute("""
                        INSERT OR REPLACE INTO installed_roms
                        (id, title, internal_title, metadata_source, console, badge, core, rom_path, cover_path, region, revision, fingerprint, installed, available, on_demand, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        g.get("id"),
                        g.get("title"),
                        g.get("internal_title", g.get("title")),
                        g.get("metadata_source", "catalog"),
                        g.get("console"),
                        g.get("badge"),
                        g.get("core") or "",
                        g.get("rom") or "",
                        g.get("cover") or "",
                        g.get("region", "Global"),
                        g.get("revision", "1.0"),
                        g.get("fingerprint", ""),
                        is_inst,
                        is_avail,
                        1 if g.get("on_demand", False) else 0,
                    ))

                cur.execute("SELECT id FROM installed_roms")
                stored_rows = cur.fetchall()
                for (row_id,) in stored_rows:
                    if row_id not in active_ids:
                        cur.execute("UPDATE installed_roms SET available = 0 WHERE id = ?", (row_id,))

                return len(current_games)
        except Exception as err:
            print(f"[GameLibraryScannerService] Error en sincronización SQLite: {err}")
            return 0
