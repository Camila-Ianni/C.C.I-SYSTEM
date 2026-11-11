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
        "external:rpcs3": ("RPCS3", ["rpcs3"], ["/Applications/RPCS3.app"]),
        "external:ryujinx": ("Ryujinx", ["ryujinx", "Ryujinx"], ["/Applications/Ryujinx.app"]),
        "external:shadps4": ("shadPS4", ["shadps4", "shadPS4"], ["/Applications/shadPS4.app"]),
        "external:pcsx2": ("PCSX2", ["pcsx2", "pcsx2-qt"], ["/Applications/PCSX2.app", "/Applications/PCSX2-Qt.app"]),
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
                                    and not f.name.startswith(".")
                                    and not f.name.endswith(".part")
                                ):
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
            if expected_rom:
                exp_abs = (self.root_dir / expected_rom).resolve()
                exp_name = Path(expected_rom).name.lower()
                for f in candidates:
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
                matched_disk_paths.add(matched_file)
                processed += 1
                try:
                    rel_rom = str(matched_file.relative_to(self.root_dir))
                except ValueError:
                    rel_rom = str(matched_file)

                size_bytes = matched_file.stat().st_size
                integrity_ok = size_bytes > 0
                notes = "OK"
                if matched_file.suffix.lower() == ".cue":
                    integrity_ok, notes = ROMMetadataExtractor.verify_cue_bin_integrity(matched_file)

                region, revision = ROMMetadataExtractor.extract_region_and_revision(matched_file.stem)
                entry.update({
                    "type": "libretro" if str(entry.get("core") or "").endswith(".dylib") else "modern",
                    "rom": rel_rom,
                    "installed": True,
                    "on_demand": False,
                    "available": integrity_ok,
                    "catalog_type": "local_installed",
                    "metadata_source": "catalog_disk",
                    "region": region,
                    "revision": revision,
                    "fingerprint": ROMMetadataExtractor.compute_file_fingerprint(matched_file),
                    "integrity_notes": notes,
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

        with self._lock:
            self._cached_games = catalog_games
            self._is_scanning = False

        return catalog_games

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

        core = game.get("core")
        if not core:
            return False, f"No hay emulador compatible configurado para {game.get('console')}."

        if str(core).startswith("external:"):
            emu = self.resolve_external_emulator(str(core))
            if not emu:
                label = self.EXTERNAL_EMULATORS.get(str(core), (str(core),))[0]
                return (
                    False,
                    f"ROM instalada localmente en '{rom_val}', pero falta instalar {label} en /Applications o PATH para lanzarlo.",
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
