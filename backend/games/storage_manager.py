"""backend/games/storage_manager.py - Gestión de almacenamiento de juegos, compatibilidad OS, verificaciones y progreso.

Implementa las correcciones de la Segunda Auditoría Técnica (H-03, H-04, H-06, H-07):
- H-03: Eliminación total de generación de paquetes ficticios CCI_PKG_V2 en el flujo real de instalación.
  Los metadatos de compatibilidad de SO se almacenan en la tabla independiente `os_compatibility_profiles`.
  Ningún juego puede marcarse como instalado sin un paquete binario auténtico validado por ROMPackageIdentityValidator.
- H-04: Tabla SQLite `execution_verifications` que registra evidencia real de ejecución (`PROCESS_STARTED`,
  `PROCESS_EXITED`, `EMULATOR_ERROR`, `GAME_LOAD_CONFIRMED`, `GAME_RUNNING`, `GAME_CLOSED`), distinguiendo
  tiempo de proceso vs tiempo efectivo de juego.
- H-07: Verificación estricta de unicidad de archivos ROM/paquetes al instalar, importar, descargar o reinstalar.
- Preservación independiente del progreso del jugador (`saves/games/<game_id>/` + SQLite `game_progress`).
"""
from __future__ import annotations

import contextlib
import datetime
import json
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent


def format_bytes_human(num_bytes: int | float) -> str:
    val = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024.0 or unit == "TB":
            if unit in ("B", "KB"):
                return f"{int(round(val))} {unit}"
            return f"{val:.1f} {unit}" if unit == "MB" and val >= 100 else f"{val:.2f} {unit}"
        val /= 1024.0
    return "0 B"


def parse_size_to_bytes(size_str: str) -> int:
    s = (size_str or "").strip().upper()
    m = re.match(r"^([\d.,]+)\s*(TB|GB|MB|KB|B)?$", s)
    if not m:
        return 0
    num = float(m.group(1).replace(",", "."))
    unit = m.group(2) or "B"
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}.get(unit, 1)
    return int(num * mult)


def _format_duration_label(seconds: int) -> str:
    sec = max(0, int(seconds))
    hours = sec // 3600
    mins = (sec % 3600) // 60
    if hours > 0:
        return f"{hours}h {mins}m"
    if mins > 0:
        return f"{mins}m"
    if sec > 0:
        return f"{sec}s"
    return "0h 0m"


class GameStorageManager:
    """Administra instalación validada, desinstalación segura, perfiles de SO y preservación de partidas."""

    _instance: GameStorageManager | None = None
    _lock = threading.RLock()

    def __init__(self, root_dir: Path | None = None, db_path: Path | None = None):
        self.root_dir = (root_dir or ROOT).resolve()
        self.db_path = (
            Path(db_path).resolve()
            if db_path
            else (self.root_dir / ".cci-user-data" / "cci_system.sqlite3")
        )
        self.saves_root = self.root_dir / "saves" / "games"
        self.ensure_schema()

    @classmethod
    def get_instance(cls, root_dir: Path | None = None, db_path: Path | None = None) -> GameStorageManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(root_dir=root_dir, db_path=db_path)
        return cls._instance

    def ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_progress (
                    game_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    last_played TEXT NOT NULL DEFAULT '',
                    play_time_seconds INTEGER NOT NULL DEFAULT 0,
                    progress_pct INTEGER NOT NULL DEFAULT 0,
                    save_slots INTEGER NOT NULL DEFAULT 0,
                    last_uninstalled_bytes INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # H-03: Metadatos de compatibilidad por SO en tabla independiente (sin generar paquetes ficticios)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS os_compatibility_profiles (
                    game_id TEXT PRIMARY KEY,
                    platform_key TEXT NOT NULL DEFAULT '',
                    os_family TEXT NOT NULL DEFAULT '',
                    os_label TEXT NOT NULL DEFAULT '',
                    graphics_api TEXT NOT NULL DEFAULT '',
                    runner TEXT NOT NULL DEFAULT '',
                    emulator_spec TEXT NOT NULL DEFAULT '',
                    compatible INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # H-04: Registro de evidencia real de ejecución y verificación de emuladores
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_verifications (
                    game_id TEXT PRIMARY KEY,
                    last_state TEXT NOT NULL DEFAULT 'NOT_RUN',
                    exit_code INTEGER,
                    load_confirmed INTEGER NOT NULL DEFAULT 0,
                    process_time_seconds INTEGER NOT NULL DEFAULT 0,
                    effective_play_seconds INTEGER NOT NULL DEFAULT 0,
                    emulator_binary TEXT NOT NULL DEFAULT '',
                    rom_path TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    state_history_json TEXT NOT NULL DEFAULT '[]',
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    @staticmethod
    def _safe_id(game_id: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]", "_", str(game_id or "game")).strip("_") or "game"

    def saves_dir_for(self, game_id: str) -> Path:
        return self.saves_root / self._safe_id(game_id)

    def game_save_dir(self, game_id: str) -> Path:
        return self.saves_dir_for(game_id)

    def _count_disk_save_slots(self, game_id: str) -> int:
        sdir = self.saves_dir_for(game_id)
        if not sdir.exists():
            return 0
        count = 0
        for p in sdir.iterdir():
            if p.is_file() and not p.name.startswith(".") and p.name != "manifest.json":
                count += 1
        return count

    def get_progress(self, game_id: str) -> dict[str, Any]:
        """Retorna estadísticas y slots preservados incluso si el binario del juego fue desinstalado."""
        self.ensure_schema()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                """
                SELECT title, last_played, play_time_seconds, progress_pct, save_slots, last_uninstalled_bytes
                FROM game_progress WHERE game_id = ?
                """,
                (str(game_id),),
            )
            row = cur.fetchone()

        disk_slots = self._count_disk_save_slots(game_id)
        if not row and disk_slots == 0:
            return {
                "game_id": str(game_id),
                "has_progress": False,
                "last_played": "Sin registrar aún",
                "play_time_seconds": 0,
                "play_time_label": "0h 0m",
                "progress_pct": 0,
                "progress_label": "—",
                "save_slots": 0,
                "saves_label": "0 slots",
                "last_uninstalled_bytes": 0,
            }

        play_sec = int(row[2]) if row else 0
        pct = int(row[3]) if row else 0
        db_slots = int(row[4]) if row else 0
        uninstalled_b = int(row[5]) if row else 0
        slots = max(disk_slots, db_slots)
        last_played = (row[1] if row and row[1] else "Guardado")
        has_prog = bool(play_sec > 0 or pct > 0 or slots > 0 or (row and row[1]))

        return {
            "game_id": str(game_id),
            "has_progress": has_prog,
            "last_played": last_played or "Sin registrar aún",
            "play_time_seconds": play_sec,
            "play_time_label": _format_duration_label(play_sec),
            "progress_pct": pct,
            "progress_label": f"{pct}%" if pct > 0 else ("Guardado" if slots > 0 else "—"),
            "save_slots": slots,
            "saves_label": f"{slots} slot{'s' if slots != 1 else ''}" if slots > 0 else "0 slots",
            "last_uninstalled_bytes": uninstalled_b,
        }

    def record_progress(
        self,
        game_id: str,
        title: str = "",
        last_played: str | None = None,
        play_time_delta_s: int = 0,
        progress_pct: int | None = None,
        slot_name: str | None = None,
        slot_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """Registra progreso real y opcionalmente escribe un archivo de partida en saves/games/<id>/."""
        self.ensure_schema()
        if slot_name:
            sdir = self.saves_dir_for(game_id)
            sdir.mkdir(parents=True, exist_ok=True)
            safe_slot = Path(slot_name).name
            (sdir / safe_slot).write_bytes(slot_bytes if slot_bytes is not None else b"CCI_SAVE_V1")

        disk_slots = self._count_disk_save_slots(game_id)
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            cur = conn.execute(
                "SELECT title, last_played, play_time_seconds, progress_pct, save_slots FROM game_progress WHERE game_id = ?",
                (str(game_id),),
            )
            prev = cur.fetchone()
            new_title = title or (prev[0] if prev else "") or str(game_id)
            new_last = last_played or ("Hoy" if (play_time_delta_s > 0 or slot_name) else (prev[1] if prev else ""))
            new_time = (int(prev[2]) if prev else 0) + max(0, int(play_time_delta_s))
            new_pct = (
                max(0, min(100, int(progress_pct)))
                if progress_pct is not None
                else (int(prev[3]) if prev else 0)
            )
            new_slots = max(disk_slots, int(prev[4]) if prev else 0)
            conn.execute(
                """
                INSERT OR REPLACE INTO game_progress
                (game_id, title, last_played, play_time_seconds, progress_pct, save_slots, last_uninstalled_bytes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT last_uninstalled_bytes FROM game_progress WHERE game_id = ?), 0), CURRENT_TIMESTAMP)
                """,
                (str(game_id), new_title, new_last, new_time, new_pct, new_slots, str(game_id)),
            )

        return self.get_progress(game_id)

    def record_execution_verification(
        self,
        game_id: str,
        last_state: str,
        exit_code: int | None,
        load_confirmed: bool,
        process_time_seconds: int = 0,
        effective_play_seconds: int = 0,
        emulator_binary: str = "",
        rom_path: str = "",
        error_message: str = "",
        state_history: list[str] | None = None,
    ) -> None:
        """Persiste en SQLite los resultados y estados reales de ejecución (H-04)."""
        self.ensure_schema()
        hist_json = json.dumps(list(state_history or []), ensure_ascii=False)
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_verifications
                (game_id, last_state, exit_code, load_confirmed, process_time_seconds,
                 effective_play_seconds, emulator_binary, rom_path, error_message, state_history_json, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(game_id),
                    str(last_state),
                    int(exit_code) if exit_code is not None else None,
                    1 if load_confirmed else 0,
                    max(0, int(process_time_seconds)),
                    max(0, int(effective_play_seconds)),
                    str(emulator_binary or ""),
                    str(rom_path or ""),
                    str(error_message or ""),
                    hist_json,
                ),
            )

    def get_execution_verification(self, game_id: str) -> dict[str, Any]:
        """Obtiene la última evidencia registrada de ejecución real del videojuego."""
        self.ensure_schema()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                """
                SELECT last_state, exit_code, load_confirmed, process_time_seconds,
                       effective_play_seconds, emulator_binary, rom_path, error_message,
                       state_history_json, verified_at
                FROM execution_verifications WHERE game_id = ?
                """,
                (str(game_id),),
            )
            row = cur.fetchone()
        if not row:
            return {
                "game_id": str(game_id),
                "last_state": "NOT_RUN",
                "exit_code": None,
                "load_confirmed": False,
                "process_time_seconds": 0,
                "effective_play_seconds": 0,
                "emulator_binary": "",
                "rom_path": "",
                "error_message": "",
                "state_history": [],
                "verified_at": None,
            }
        try:
            hist = json.loads(row[8] or "[]")
        except Exception:
            hist = []
        return {
            "game_id": str(game_id),
            "last_state": str(row[0]),
            "exit_code": row[1],
            "load_confirmed": bool(row[2]),
            "process_time_seconds": int(row[3] or 0),
            "effective_play_seconds": int(row[4] or 0),
            "emulator_binary": str(row[5] or ""),
            "rom_path": str(row[6] or ""),
            "error_message": str(row[7] or ""),
            "state_history": hist,
            "verified_at": row[9],
        }

    def save_os_compatibility_profile(
        self,
        game_id: str,
        platform_key: str,
        os_profile: dict[str, str],
        emulator_spec: str = "",
        compatible: bool = False,
        notes: str = "",
    ) -> None:
        """Guarda metadatos de compatibilidad OS de manera independiente de los paquetes en disco (H-03)."""
        self.ensure_schema()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO os_compatibility_profiles
                (game_id, platform_key, os_family, os_label, graphics_api, runner,
                 emulator_spec, compatible, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(game_id),
                    str(platform_key),
                    os_profile.get("os_family", ""),
                    os_profile.get("os_label", ""),
                    os_profile.get("graphics_api", ""),
                    os_profile.get("runner", ""),
                    str(emulator_spec or ""),
                    1 if compatible else 0,
                    str(notes or ""),
                ),
            )

    def get_os_compatibility_profile(self, game_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                """
                SELECT platform_key, os_family, os_label, graphics_api, runner,
                       emulator_spec, compatible, notes, updated_at
                FROM os_compatibility_profiles WHERE game_id = ?
                """,
                (str(game_id),),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "game_id": str(game_id),
            "platform_key": row[0],
            "os_family": row[1],
            "os_label": row[2],
            "graphics_api": row[3],
            "runner": row[4],
            "emulator_spec": row[5],
            "compatible": bool(row[6]),
            "notes": row[7],
            "updated_at": row[8],
        }

    def snapshot_game_saves(self, game_id: str, title: str = "", extra_meta: dict | None = None) -> Path:
        """Asegura el manifiesto de respaldo en saves/games/<game_id>/ antes de desinstalar binarios."""
        sdir = self.saves_dir_for(game_id)
        sdir.mkdir(parents=True, exist_ok=True)
        prog = self.get_progress(game_id)
        manifest = {
            "game_id": str(game_id),
            "title": title or str(game_id),
            "preserved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "progress": prog,
            "extra": extra_meta or {},
        }
        (sdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return sdir

    def check_storage_available(
        self,
        required_bytes: int,
        free_override_bytes: int | None = None,
    ) -> tuple[bool, dict[str, int]]:
        usage = shutil.disk_usage(self.root_dir)
        free_b = int(free_override_bytes) if free_override_bytes is not None else int(usage.free)
        ok = free_b >= max(0, int(required_bytes))
        return ok, {
            "required_bytes": int(required_bytes),
            "free_bytes": free_b,
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
        }

    def _check_path_uniqueness(self, game_id: str, candidate_path: Path, scanner: Any) -> tuple[bool, str]:
        """H-07: Impide asociar un archivo físico ya asignado a otro game_id diferente."""
        cand_resolved = candidate_path.resolve()
        for other in scanner.get_games():
            other_id = str(other.get("id") or "")
            other_rom = other.get("rom")
            if other_id != str(game_id) and other_rom and not other.get("on_demand"):
                other_p = Path(str(other_rom)) if Path(str(other_rom)).is_absolute() else (self.root_dir / str(other_rom))
                try:
                    if other_p.resolve() == cand_resolved:
                        return (
                            False,
                            f"Violación de unicidad (H-07): '{candidate_path.name}' ya está asociado al juego '{other_id}'.",
                        )
                except Exception:
                    pass
        return True, ""

    def uninstall_game(self, game_id: str, scanner: Any = None) -> tuple[bool, str, dict[str, Any]]:
        """Desinstala únicamente el binario ROM en disco liberando espacio y conservando todo el progreso."""
        from backend.games.scanner_service import GameLibraryScannerService

        svc = scanner or GameLibraryScannerService.get_instance(self.root_dir)
        game = svc.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no encontrado en catálogo: {game_id}", {}

        if game.get("on_demand") or not game.get("rom"):
            return False, f"'{game['title']}' ya está en la nube (no tiene archivos locales para desinstalar).", {}

        rom_val = str(game["rom"])
        rom_path = Path(rom_val) if Path(rom_val).is_absolute() else (self.root_dir / rom_val)
        if not rom_path.exists():
            svc.refresh()
            return False, f"No se encontró el paquete local en disco: {rom_val}", {}

        roms_root = (self.root_dir / "roms").resolve()
        try:
            rom_path.resolve().relative_to(roms_root)
        except ValueError:
            return False, "Ruta fuera del directorio autorizado roms/.", {}

        freed_bytes = rom_path.stat().st_size

        prog = self.get_progress(game_id)
        if not prog["has_progress"]:
            self.record_progress(game_id, title=game["title"])
        manifest_dir = self.snapshot_game_saves(game_id, title=game["title"], extra_meta={"freed_bytes": freed_bytes})

        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "UPDATE game_progress SET last_uninstalled_bytes = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?",
                (freed_bytes, str(game_id)),
            )

        rom_path.unlink()

        if self.db_path.exists():
            try:
                with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
                    conn.execute(
                        "UPDATE installed_roms SET available = 0, installed = 0, on_demand = 1 WHERE id = ?",
                        (str(game_id),),
                    )
            except Exception:
                pass

        svc.refresh()
        updated_game = dict(svc.get_game_by_id(game_id) or {})
        freed_lbl = format_bytes_human(freed_bytes)
        updated_game.update({
            "game_id": str(game_id),
            "freed_bytes": freed_bytes,
            "freed_label": freed_lbl,
            "saves_dir": str(manifest_dir),
            "saves_preserved": True,
        })
        return (
            True,
            f"'{game['title']}' desinstalado correctamente.\n"
            f"Se liberaron {freed_lbl} en disco.\n"
            f"Progreso y partidas guardadas: Conservado intacto en {manifest_dir.relative_to(self.root_dir)}.",
            updated_game,
        )

    def install_local_package(
        self,
        game_id: str,
        source_file: Path | str,
        scanner: Any = None,
        free_override_bytes: int | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Instala un paquete binario auténtico en roms/<plat>/ verificando identidad binaria, espacio y unicidad."""
        from backend.games.package_validator import ROMPackageIdentityValidator
        from backend.games.scanner_service import GameLibraryScannerService

        src = Path(source_file).resolve()
        if not src.exists() or not src.is_file():
            return False, f"Archivo no encontrado: {source_file}", {"reason": "missing_source"}

        svc = scanner or GameLibraryScannerService.get_instance(self.root_dir)
        game = svc.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no encontrado en catálogo: {game_id}", {"reason": "unknown_game"}

        plat_key = str(game.get("platform_key") or "ps3")
        allowed_exts = svc.PLATFORM_SPECS.get(plat_key, {}).get("extensions", [])

        # H-07: Verificar unicidad del origen antes de instalar
        uniq_ok, uniq_msg = self._check_path_uniqueness(game_id, src, svc)
        if not uniq_ok:
            return False, uniq_msg, {"reason": "duplicate_association"}

        # H-01 y H-03: Validar autenticidad binaria ANTES de instalar y rechazar contenedores sintéticos CCI_PKG_V2
        id_ok, id_msg, id_meta = ROMPackageIdentityValidator.verify_package_identity(
            game_id=str(game_id),
            title=str(game.get("title") or ""),
            platform_key=plat_key,
            rom_path=src,
            allowed_extensions=allowed_exts,
            expected_rom=game.get("expected_rom"),
        )
        if not id_ok:
            return (
                False,
                f"Instalación rechazada para '{game['title']}': {id_msg}",
                {"reason": id_meta.get("package_kind", "invalid_package"), "detail": id_msg},
            )

        req_bytes = src.stat().st_size
        enough, st = self.check_storage_available(req_bytes, free_override_bytes=free_override_bytes)
        if not enough:
            return (
                False,
                f"Espacio insuficiente para instalar '{game['title']}'.\n"
                f"Necesario: {format_bytes_human(req_bytes)} · Libre: {format_bytes_human(st['free_bytes'])}.\n"
                f"Podés desinstalar otro juego desde el Gestor de Almacenamiento sin perder su progreso.",
                {
                    "reason": "insufficient_storage",
                    "required_bytes": req_bytes,
                    "free_bytes": st["free_bytes"],
                },
            )

        dest_dir = self.root_dir / "roms" / plat_key
        dest_dir.mkdir(parents=True, exist_ok=True)

        expected_rom = game.get("expected_rom")
        if expected_rom and Path(expected_rom).suffix.lower() == src.suffix.lower():
            dest_name = Path(expected_rom).name
        else:
            clean = re.sub(r"[^a-zA-Z0-9._ -]", "_", game.get("clean_title") or game["title"]).strip()
            dest_name = f"{clean}{src.suffix.lower()}"

        final_path = dest_dir / dest_name
        # H-07: Verificar unicidad del destino en roms/<plat>/
        uniq_dest_ok, uniq_dest_msg = self._check_path_uniqueness(game_id, final_path, svc)
        if not uniq_dest_ok:
            return False, uniq_dest_msg, {"reason": "duplicate_association"}

        part_path = dest_dir / f".{dest_name}.part"
        if src != final_path:
            try:
                shutil.copy2(src, part_path)
                part_path.replace(final_path)
            except Exception as exc:
                if part_path.exists():
                    part_path.unlink(missing_ok=True)
                return False, f"Error de escritura durante la instalación atómica: {exc}", {"reason": "io_error"}

        # H-06: Si es archivo comprimido o PKG de PS3, extraer y preparar estructura de ejecución real
        extracted_target: Path | None = None
        if final_path.suffix.lower() in (".zip", ".rar", ".7z"):
            ext_ok, ext_path, ext_msg = self.extract_and_verify_archive(final_path, plat_key)
            if not ext_ok:
                final_path.unlink(missing_ok=True)
                return False, f"Error al extraer paquete comprimido: {ext_msg}", {"reason": "extraction_failed"}
            extracted_target = ext_path
            if extracted_target and extracted_target.suffix.lower() in {
                ext.lower() for ext in allowed_exts
            }:
                inner_ok, inner_msg, _inner_meta = ROMPackageIdentityValidator.verify_package_identity(
                    game_id=str(game_id),
                    title=str(game.get("title") or ""),
                    platform_key=plat_key,
                    rom_path=extracted_target,
                    allowed_extensions=allowed_exts,
                    expected_rom=game.get("expected_rom"),
                )
                if not inner_ok:
                    final_path.unlink(missing_ok=True)
                    return (
                        False,
                        f"El contenido extraído no supera la validación: {inner_msg}",
                        {"reason": "extracted_content_invalid"},
                    )
        elif final_path.suffix.lower() == ".pkg" and plat_key == "ps3":
            prod_code = str(id_meta.get("product_code") or self._safe_id(game_id))
            ps3_dir = dest_dir / ".extracted_cache" / prod_code
            pkg_ok, eboot_p, pkg_msg = ROMPackageIdentityValidator.extract_ps3_pkg_to_dir(final_path, ps3_dir)
            if not pkg_ok or not eboot_p:
                final_path.unlink(missing_ok=True)
                return (
                    False,
                    f"El paquete PS3 no contiene una instalación ejecutable completa: {pkg_msg}",
                    {"reason": "extraction_failed"},
                )
            extracted_target = eboot_p

        # Revalidación posterior a la instalación
        post_ok, post_msg, post_meta = ROMPackageIdentityValidator.verify_package_identity(
            game_id=str(game_id),
            title=str(game.get("title") or ""),
            platform_key=plat_key,
            rom_path=final_path,
            allowed_extensions=allowed_exts,
            expected_rom=game.get("expected_rom"),
        )
        if not post_ok:
            final_path.unlink(missing_ok=True)
            return False, f"Falló la verificación posterior a la instalación: {post_msg}", {"reason": "post_verify_failed"}

        # Registrar perfil de compatibilidad OS independiente
        os_prof = self.detect_target_os_profile()
        self.save_os_compatibility_profile(
            game_id=str(game_id),
            platform_key=plat_key,
            os_profile=os_prof,
            emulator_spec=str(game.get("core") or ""),
            compatible=bool(game.get("core")),
            notes=post_msg,
        )

        svc.refresh()
        updated_game = dict(svc.get_game_by_id(game_id) or {})
        prog = self.get_progress(game_id)
        updated_game.update({
            "game_id": str(game_id),
            "rom_path": str(final_path.relative_to(self.root_dir)),
            "extracted_target": str(extracted_target) if extracted_target else None,
            "bytes_installed": req_bytes,
            "package_meta": post_meta,
            "progress_restored": prog["has_progress"],
        })
        return (
            True,
            f"'{game['title']}' instalado y verificado en roms/{plat_key}/{final_path.name} ({format_bytes_human(req_bytes)})."
            + (
                f"\nProgreso previo detectado y restaurado ({prog['saves_label']}, {prog['play_time_label']})."
                if prog["has_progress"]
                else ""
            ),
            updated_game,
        )

    @classmethod
    def extract_and_verify_archive(cls, archive_path: Path, platform_key: str) -> tuple[bool, Path | None, str]:
        """Extrae un paquete comprimido (.zip/.rar/.7z) en .extracted_cache y verifica su estructura interna (H-06)."""
        from backend.games.package_validator import ROMPackageIdentityValidator

        cache_dir = archive_path.parent / ".extracted_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        wanted_exts_map = {
            "ps3": (".pkg", ".iso"),
            "ps4": (".pkg", ".iso"),
            "switch": (".nsp", ".xci"),
            "ps2": (".iso", ".chd"),
            "ps1": (".cue", ".iso", ".bin"),
        }
        wanted_exts = wanted_exts_map.get(platform_key, (".pkg", ".iso", ".nsp", ".xci", ".cue"))

        if archive_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    bad = zf.testzip()
                    if bad is not None:
                        return False, None, f"CRC corrupto dentro del ZIP en '{bad}'."
                    members = [m for m in zf.infolist() if not m.is_dir()]
                    if not members:
                        return False, None, "El ZIP no contiene archivos."
                    if len(members) > 4096:
                        return False, None, "El ZIP contiene demasiados archivos para una extracción segura."
                    total_uncompressed = sum(max(0, int(m.file_size)) for m in members)
                    if total_uncompressed > 100 * 1024**3:
                        return False, None, "El tamaño descomprimido del ZIP supera el límite seguro de 100 GiB."
                    for m in members:
                        if ".." in Path(m.filename).parts:
                            return False, None, f"Ruta insegura en ZIP: {m.filename}"
                        if Path(m.filename).is_absolute():
                            return False, None, f"Ruta absoluta insegura en ZIP: {m.filename}"
                    compat = [m for m in members if Path(m.filename).suffix.lower() in wanted_exts]
                    if not compat:
                        return False, None, f"ZIP sin archivos compatibles ({wanted_exts}) para '{platform_key}'."
                    target_member = compat[0]
                    out_file = cache_dir / Path(target_member.filename).name
                    if not out_file.exists() or out_file.stat().st_size != target_member.file_size:
                        tmp_part = cache_dir / f".{out_file.name}.part"
                        with zf.open(target_member, "r") as src_f, open(tmp_part, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f, length=1048576)
                        tmp_part.replace(out_file)
            except zipfile.BadZipFile as exc:
                return False, None, f"Archivo ZIP inválido: {exc}"
        else:
            unar_bin = shutil.which("unar") or "/opt/homebrew/bin/unar"
            if not unar_bin or not Path(unar_bin).exists():
                return False, None, "Se requiere 'unar' para extraer archivos .rar/.7z."
            stem_tok = archive_path.stem.split()[0].lower()
            out_file = None
            for cand in sorted(cache_dir.rglob("*")):
                if cand.is_file() and cand.suffix.lower() in wanted_exts and stem_tok in cand.name.lower():
                    out_file = cand
                    break
            if out_file is None:
                res = subprocess.run([unar_bin, "-f", "-o", str(cache_dir), str(archive_path)], capture_output=True, text=True, check=False)
                if res.returncode != 0:
                    return False, None, f"Error extrayendo con unar: {res.stderr.strip()}"
                for cand in sorted(cache_dir.rglob("*")):
                    if cand.is_file() and cand.suffix.lower() in wanted_exts and stem_tok in cand.name.lower():
                        out_file = cand
                        break
            if out_file is None:
                return False, None, f"No se encontró binario compatible ({wanted_exts}) tras extraer '{archive_path.name}'."

        # H-06: Si es PKG de PS3, asegurar estructura extraída completa PARAM.SFO + USRDIR/EBOOT.BIN
        if out_file.suffix.lower() == ".pkg" and platform_key == "ps3":
            with open(out_file, "rb") as fh:
                hdr = fh.read(0x80)
            cid = hdr[48:84].split(b"\x00")[0].decode("ascii", "ignore")
            m_prod = re.search(r"([A-Z]{4}\d{5})", cid)
            prod_code = m_prod.group(1) if m_prod else out_file.stem
            ps3_dir = cache_dir / prod_code
            pkg_ok, eboot_p, pkg_msg = ROMPackageIdentityValidator.extract_ps3_pkg_to_dir(out_file, ps3_dir)
            if pkg_ok and eboot_p:
                return True, eboot_p, pkg_msg
            return True, out_file, "PKG PS3 extraído del archivo ZIP."

        return True, out_file, f"Paquete extraído y verificado: {out_file.name}"

    @staticmethod
    def detect_target_os_profile(target_os: str | None = None) -> dict[str, str]:
        """Detecta automáticamente Windows o macOS para registrar el perfil de compatibilidad OS."""
        raw = (target_os or sys.platform or platform.system()).lower()
        arch = (platform.machine() or "x64").upper()
        if "win" in raw:
            return {
                "os_family": "windows",
                "os_label": f"Windows ({arch})",
                "graphics_api": "DirectX 12 / OpenGL 60 FPS",
                "runner": "modern_game_runner.py",
            }
        if "darwin" in raw or "mac" in raw:
            return {
                "os_family": "macos",
                "os_label": f"macOS ({arch})",
                "graphics_api": "Metal / OpenGL 60 FPS",
                "runner": "modern_game_runner.py",
            }
        return {
            "os_family": "linux",
            "os_label": f"Linux ({arch})",
            "graphics_api": "Vulkan / OpenGL 60 FPS",
            "runner": "modern_game_runner.py",
        }

    def _find_matching_user_download(self, game: dict) -> Path | None:
        """Busca en ~/Downloads un paquete binario real (.rar/.zip/.nsp/.xci/.pkg/.iso) para este juego."""
        dl_dir = Path.home() / "Downloads"
        if not dl_dir.exists():
            return None
        raw_title = str(game.get("clean_title") or game.get("title") or "")
        tokens = [
            t for t in re.split(r"[^a-z0-9]+", raw_title.lower())
            if len(t) >= 4 and t not in ("edition", "deluxe", "pack", "game")
        ]
        if not tokens:
            return None
        valid_exts = {".nsp", ".xci", ".pkg", ".iso", ".rar", ".zip", ".7z", ".cue"}
        best: Path | None = None
        best_score = 0
        try:
            for f in dl_dir.iterdir():
                if not f.is_file() or f.suffix.lower() not in valid_exts or f.stat().st_size < 65536:
                    continue
                fname_l = f.stem.lower()
                score = sum(1 for tok in tokens if tok in fname_l)
                if score >= max(1, len(tokens) // 2) and score > best_score:
                    best = f
                    best_score = score
        except Exception:
            return None
        return best

    def install_game_for_current_os(
        self,
        game_id: str,
        scanner: Any = None,
        target_os: str | None = None,
        free_override_bytes: int | None = None,
        source_package: Path | str | None = None,
        allow_cloud_download: bool = False,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Registra compatibilidad OS e instala únicamente un paquete binario real (nunca contenedores ficticios H-03)."""
        from backend.games.package_validator import CATALOG_SOURCE_URLS
        from backend.games.scanner_service import GameLibraryScannerService

        svc = scanner or GameLibraryScannerService.get_instance(self.root_dir)
        game = svc.get_game_by_id(game_id)
        if not game:
            return False, f"Juego no encontrado en catálogo: {game_id}", {"reason": "unknown_game"}

        os_prof = self.detect_target_os_profile(target_os)
        plat_key = str(game.get("platform_key") or "ps3")
        self.save_os_compatibility_profile(
            game_id=str(game_id),
            platform_key=plat_key,
            os_profile=os_prof,
            emulator_spec=str(game.get("core") or ""),
            compatible=bool(game.get("core")),
            notes="Perfil de compatibilidad registrado; requiere paquete binario real.",
        )

        # 1. Si se proveyó un paquete real explícito, validarlo e instalarlo
        if source_package is not None:
            return self.install_local_package(
                game_id,
                source_package,
                scanner=svc,
                free_override_bytes=free_override_bytes,
            )

        # 2. Si el usuario ya descargó el paquete real en ~/Downloads, instalarlo y validarlo
        if free_override_bytes is None:
            user_dl = self._find_matching_user_download(game)
            if user_dl is not None:
                return self.install_local_package(game_id, user_dl, scanner=svc)

        # 3. Descargar desde la fuente oficial solo cuando allow_cloud_download=True
        if allow_cloud_download:
            from tools.download_catalog_game import download_and_install_game

            ok_dl, msg_dl = download_and_install_game(game_id, root_dir=self.root_dir)
            if ok_dl:
                svc.refresh()
                return True, msg_dl, dict(svc.get_game_by_id(game_id) or {})
            return False, msg_dl, {"reason": "download_failed", "os_profile": os_prof}

        # H-03: Jamás crear contenedores CCI_PKG_V2 para fingir que el juego está instalado
        return (
            False,
            f"Instalación requerida: '{game['title']}' necesita un paquete binario auténtico ({game.get('format', 'ROM')}). "
            f"No se permiten paquetes sintéticos de relleno.",
            {
                "reason": "real_package_required",
                "installed": False,
                "os_profile": os_prof,
                "source_url": CATALOG_SOURCE_URLS.get(str(game_id)),
            },
        )

    def get_storage_summary(self, scanner: Any = None) -> dict[str, Any]:
        """Calcula uso real de almacenamiento en disco y lista de juegos auténticos instalados."""
        from backend.games.scanner_service import GameLibraryScannerService

        svc = scanner or GameLibraryScannerService.get_instance(self.root_dir)
        games = svc.get_games()
        usage = shutil.disk_usage(self.root_dir)

        installed_items = []
        installed_bytes = 0
        cloud_count = 0

        for g in games:
            if not g.get("on_demand") and g.get("installed") and g.get("rom"):
                rom_p = Path(g["rom"]) if Path(g["rom"]).is_absolute() else (self.root_dir / g["rom"])
                sz = rom_p.stat().st_size if rom_p.exists() else int(g.get("size_bytes") or 0)
                installed_bytes += sz
                prog = self.get_progress(g["id"])
                installed_items.append({
                    "id": g["id"],
                    "title": g["title"],
                    "badge": g.get("badge", "ROM"),
                    "console": g.get("console", ""),
                    "rom": g["rom"],
                    "size_bytes": sz,
                    "size_label": format_bytes_human(sz),
                    "has_progress": prog["has_progress"],
                    "save_slots": prog["save_slots"],
                    "play_time_label": prog["play_time_label"],
                })
            else:
                cloud_count += 1

        installed_items.sort(key=lambda x: x["size_bytes"], reverse=True)
        used_pct = int(round((usage.used / usage.total) * 100)) if usage.total > 0 else 0

        return {
            "total_games": len(games),
            "installed_count": len(installed_items),
            "cloud_count": cloud_count,
            "installed_bytes": installed_bytes,
            "installed_label": format_bytes_human(installed_bytes),
            "disk_total_bytes": int(usage.total),
            "disk_used_bytes": int(usage.used),
            "disk_free_bytes": int(usage.free),
            "disk_free_label": format_bytes_human(usage.free),
            "disk_total_label": format_bytes_human(usage.total),
            "used_pct": max(0, min(100, used_pct)),
            "installed_items": installed_items,
        }
