"""modern_game_runner.py - Ejecutor estricto y verificador real de ejecución para C.C.I. SYSTEM.

Implementa las correcciones P0 y P1 de la Segunda Auditoría Técnica (Versión 2.0):
- H-01 / H-03: Valida autenticidad binaria del paquete antes de lanzar; bloquea contenedores sintéticos CCI_PKG_V2
  como juegos comerciales reales y prohíbe sustituciones o fallbacks silenciosos.
- H-04: Implementa los 6 estados independientes de ejecución:
    PROCESS_STARTED -> PROCESS_EXITED | EMULATOR_ERROR -> GAME_LOAD_CONFIRMED -> GAME_RUNNING -> GAME_CLOSED
  Jamás asigna exit_code=0 si el emulador falla, termina prematuramente o reporta error fatal en sus logs/stderr.
  Persiste la evidencia de carga y errores en SQLite (`execution_verifications`).
- H-06: Extrae y verifica paquetes comprimidos (.zip/.rar/.7z) y PS3 .pkg (PARAM.SFO + USRDIR/EBOOT.BIN) antes
  de pasar el objetivo real al emulador (ej. RPCS3 con Minecraft: PlayStation 3 Edition [NPUB31419]).
"""
from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pygame

from backend.games.package_validator import ROMPackageIdentityValidator
from retro_core_runner import LibretroRunner

ROOT = Path(__file__).resolve().parent
CORES_DIR = ROOT / "cores"
EMULATORS_DIR = CORES_DIR / "emulators"

# Garantía explícita de auditoría: mapas de sustitución cruzada deshabilitados permanentemente
_EXACT_GAME_MAP: dict[str, list[tuple[str, str]]] = {}
_PLAYSTATION_3D_ISO_MAP: dict[str, list[str]] = {}
_NATIVE_MACOS_APP_MAP: dict[str, str] = {}

EXECUTION_STATES = (
    "PROCESS_STARTED",
    "PROCESS_EXITED",
    "EMULATOR_ERROR",
    "GAME_LOAD_CONFIRMED",
    "GAME_RUNNING",
    "GAME_CLOSED",
)


def detect_os_runtime_label() -> str:
    sys_name = platform.system().lower()
    machine = platform.machine().upper()
    if sys_name == "darwin":
        return f"macOS ({machine or 'ARM64'}) · Verificación Estricta C.C.I."
    if sys_name == "windows":
        return f"Windows ({machine or 'x64'}) · Verificación Estricta C.C.I."
    return f"{platform.system()} ({machine}) · Verificación Estricta C.C.I."


def _core_ext() -> str:
    sys_name = platform.system().lower()
    if "win" in sys_name:
        return ".dll"
    if "darwin" in sys_name or "mac" in sys_name:
        return ".dylib"
    return ".so"


def _resolve_core_path(core_stem_or_rel: str) -> Path:
    p = ROOT / core_stem_or_rel
    if p.exists():
        return p
    stem = Path(core_stem_or_rel).stem
    ext = _core_ext()
    cand = CORES_DIR / f"{stem}{ext}"
    if cand.exists():
        return cand
    for fallback_ext in (".dylib", ".dll", ".so"):
        alt = CORES_DIR / f"{stem}{fallback_ext}"
        if alt.exists():
            return alt
    return cand


def resolve_playable_engine(
    game_id: str,
    title: str = "",
    genre: str = "",
    rom_arg: str = "",
    root_dir: Path | None = None,
) -> tuple[Path | None, Path | None, str]:
    """Resuelve estrictamente (emulator_or_core_path, validated_rom_path, status_message)."""
    from backend.games.scanner_service import GameLibraryScannerService

    base_root = (root_dir or ROOT).resolve()
    svc = GameLibraryScannerService.get_instance(base_root)
    gid = str(game_id or "").strip()
    if not gid:
        return None, None, "Juego no instalado o no compatible: game_id vacío."

    game = svc.get_game_by_id(gid)
    if not game:
        return None, None, f"Juego no instalado o no compatible: '{gid}' no existe en el catálogo."

    catalog_title = str(game.get("title") or title or gid)
    plat_key = str(game.get("platform_key") or "").lower()
    spec = svc.PLATFORM_SPECS.get(plat_key)
    if not spec:
        return None, None, f"Plataforma '{plat_key}' no reconocida para '{catalog_title}'."
    if plat_key in ("ps5", "switch2") or not spec.get("core"):
        return (
            None,
            None,
            f"Juego no compatible: la plataforma {game.get('console', plat_key.upper())} "
            "aún no dispone de emulador comercial estable.",
        )

    rom_val = game.get("rom") or rom_arg
    if not rom_val or game.get("on_demand", False):
        if rom_val:
            cand_p = Path(str(rom_val)) if Path(str(rom_val)).is_absolute() else (base_root / str(rom_val))
            if cand_p.exists() and ROMPackageIdentityValidator.inspect_cci_container(cand_p) is not None:
                return (
                    None,
                    None,
                    f"Contenedor sintético de prueba detectado para '{catalog_title}': no contiene el paquete binario comercial real.",
                )
        return (
            None,
            None,
            f"Juego no instalado: '{catalog_title}' [{game.get('badge', plat_key.upper())}] no tiene un paquete local instalado en roms/{plat_key}/.",
        )

    rom_path = Path(str(rom_val)) if Path(str(rom_val)).is_absolute() else (base_root / str(rom_val))
    try:
        rom_rel = rom_path.resolve().relative_to((base_root / "roms").resolve())
        is_local_library_rom = bool(rom_rel.parts and rom_rel.parts[0].lower() == plat_key)
    except (OSError, ValueError):
        is_local_library_rom = False

    id_ok, id_msg, id_meta = ROMPackageIdentityValidator.verify_package_identity(
        game_id=gid,
        title=catalog_title,
        platform_key=plat_key,
        rom_path=rom_path,
        allowed_extensions=spec.get("extensions", []),
        expected_rom=game.get("expected_rom"),
        allow_local_filename_identity=is_local_library_rom,
    )
    if not id_ok:
        return None, None, f"Juego no instalado o identidad inválida: {id_msg}"

    # H-07: Verificar unicidad de archivo entre todos los game_id del catálogo
    for other in svc.get_games():
        other_id = str(other.get("id") or "")
        other_rom = other.get("rom")
        if other_id != gid and other_rom and not other.get("on_demand"):
            other_path = Path(str(other_rom)) if Path(str(other_rom)).is_absolute() else (base_root / str(other_rom))
            try:
                if other_path.resolve() == rom_path.resolve():
                    return (
                        None,
                        None,
                        f"Asociación inválida: el archivo '{rom_path.name}' está compartido con '{other_id}'.",
                    )
            except Exception:
                pass

    core_spec = game.get("core") or spec.get("core")
    if not core_spec or plat_key in ("ps5", "switch2"):
        return (
            None,
            None,
            f"Juego no compatible: la plataforma {game.get('console', plat_key.upper())} aún no dispone de emulador comercial estable.",
        )

    if str(core_spec).startswith("external:"):
        emu_info = svc.resolve_external_emulator(str(core_spec))
        if not emu_info:
            emu_label = svc.EXTERNAL_EMULATORS.get(str(core_spec), (str(core_spec),))[0]
            return (
                None,
                rom_path,
                f"Emulador no disponible: se requiere {emu_label} instalado para ejecutar '{catalog_title}'.",
            )
        if str(core_spec) == "external:rpcs3" and not svc.is_rpcs3_firmware_installed():
            return (
                None,
                rom_path,
                f"Firmware PS3 faltante en RPCS3: instala PS3UPDAT.PUP para ejecutar '{catalog_title}'.",
            )
        return Path(emu_info[1]), rom_path, f"Verificado con emulador externo {emu_info[0]} ({id_meta.get('package_kind')})."

    core_path = _resolve_core_path(str(core_spec))
    if not core_path.exists():
        return None, rom_path, f"Núcleo Libretro requerido no encontrado en disco: {core_spec}"

    return core_path, rom_path, f"Verificado con núcleo Libretro {core_path.name} ({id_meta.get('package_kind')})."


def _prepare_launch_target(rom_path: Path, platform_key: str) -> tuple[bool, Path | None, str]:
    """H-06: Extrae y verifica paquetes comprimidos o .pkg PS3 antes de invocar al emulador."""
    from backend.games.storage_manager import GameStorageManager

    ext = rom_path.suffix.lower()
    if ext in (".zip", ".rar", ".7z"):
        return GameStorageManager.extract_and_verify_archive(rom_path, platform_key)
    if ext == ".pkg" and platform_key == "ps3":
        ps3_dir = rom_path.parent / ".extracted_cache" / rom_path.stem
        ok, eboot_p, msg = ROMPackageIdentityValidator.extract_ps3_pkg_to_dir(rom_path, ps3_dir)
        if ok and eboot_p:
            return True, eboot_p, msg
        return False, None, msg
    return True, rom_path, "Objetivo nativo listo."


def _read_new_rpcs3_log_lines(log_path: Path, start_offset: int) -> list[str]:
    if not log_path.exists():
        return []
    try:
        data = log_path.read_bytes()
        if len(data) < start_offset:
            return data.decode("utf-8", errors="ignore").splitlines()
        return data[start_offset:].decode("utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _inspect_rpcs3_log_status(lines: list[str]) -> tuple[bool, bool, str]:
    """Analiza el log real de RPCS3 -> (fatal_error, load_confirmed, diagnostic_message)."""
    fatal_markers = (
        "Reason: Firmware is missing",
        "with cli argument failed",
        "Failed to load",
        "Thread terminated due to fatal error",
        "SYS: Stopping emulator",
        "·F ",
    )
    for ln in lines:
        for fm in fatal_markers:
            if fm in ln:
                return True, False, ln.strip()

    has_boot = any("SYS: Booting application" in ln or "SYS: Serial:" in ln for ln in lines)
    has_graphics = any("RSX: Swapchain:" in ln or "RSX: Found Vulkan" in ln or "cellAudio: Opened audio backend" in ln for ln in lines)
    if has_boot and has_graphics:
        return False, True, "RPCS3 confirmó arranque de aplicación PS3 y backend RSX/Audio activo."
    return False, False, "Esperando confirmación de carga en RPCS3."


def _run_external_emulator(
    game_id: str,
    title: str,
    badge: str,
    core_spec: str,
    engine_path: Path,
    launch_target: Path,
    max_frames: int,
    storage: Any,
) -> int:
    state_history: list[str] = []
    start_ts = time.monotonic()

    env = dict(os.environ)
    # Emuladores Qt externos (RPCS3/PCSX2) requieren el plugin nativo cocoa en macOS, no offscreen
    if env.get("QT_QPA_PLATFORM") == "offscreen":
        env.pop("QT_QPA_PLATFORM", None)

    is_rpcs3 = "rpcs3" in core_spec.lower() or "rpcs3" in engine_path.name.lower()
    rpcs3_log = Path.home() / "Library/Caches/rpcs3/RPCS3.log"
    rpcs3_log_offset = rpcs3_log.stat().st_size if (is_rpcs3 and rpcs3_log.exists()) else 0

    cmd = [str(engine_path)]
    # La ruta interactiva de OmniDash necesita la ventana de RPCS3. El modo
    # sin GUI sólo se usa en pruebas temporizadas para no ocultar el juego.
    if is_rpcs3 and max_frames > 0 and "--no-gui" not in cmd:
        cmd.append("--no-gui")
    cmd.append(str(launch_target.resolve()))

    print(f"[C.C.I. Runner] Ejecutando '{title}' [{badge}] con {engine_path.name} -> {launch_target.name}")

    try:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        state_history.append("EMULATOR_ERROR")
        storage.record_execution_verification(
            game_id=game_id,
            last_state="EMULATOR_ERROR",
            exit_code=127,
            load_confirmed=False,
            emulator_binary=str(engine_path),
            rom_path=str(launch_target),
            error_message=f"No se pudo iniciar el proceso del emulador: {exc}",
            state_history=state_history,
        )
        print(f"[C.C.I. Runner] Error al iniciar emulador: {exc}", file=sys.stderr)
        return 127

    state_history.append("PROCESS_STARTED")

    if max_frames > 0:
        load_confirmed = False
        fatal_error = False
        err_detail = ""
        deadline = time.monotonic() + (8.0 if is_rpcs3 else 2.5)
        min_wait = time.monotonic() + (1.2 if not is_rpcs3 else 2.5)

        while time.monotonic() < deadline:
            rc_now = proc.poll()
            if rc_now is not None:
                out_txt, err_txt = proc.communicate()
                state_history.append("PROCESS_EXITED")
                combined_err = (err_txt or out_txt or "").strip()
                if is_rpcs3:
                    new_lines = _read_new_rpcs3_log_lines(rpcs3_log, rpcs3_log_offset)
                    f_err, _l_ok, f_msg = _inspect_rpcs3_log_status(new_lines)
                    if f_err and not combined_err:
                        combined_err = f_msg

                if rc_now != 0 or any(tok in combined_err.lower() for tok in ("error", "failed", "missing", "fatal", "corrupt")):
                    state_history.append("EMULATOR_ERROR")
                    msg = combined_err or f"El emulador terminó prematuramente con código {rc_now}."
                    storage.record_execution_verification(
                        game_id=game_id,
                        last_state="EMULATOR_ERROR",
                        exit_code=int(rc_now if rc_now != 0 else 1),
                        load_confirmed=False,
                        process_time_seconds=max(1, int(time.monotonic() - start_ts)),
                        effective_play_seconds=0,
                        emulator_binary=str(engine_path),
                        rom_path=str(launch_target),
                        error_message=msg[:500],
                        state_history=state_history,
                    )
                    print(f"[C.C.I. Runner] EMULATOR_ERROR: {msg[:300]}", file=sys.stderr)
                    return int(rc_now if rc_now != 0 else 1)

                # Un código 0 sólo indica que el proceso terminó limpiamente.
                # Sin evidencia de carga no se puede certificar el videojuego.
                if not load_confirmed:
                    state_history.append("EXECUTION_INDETERMINATE")
                    msg = "El emulador terminó sin evidenciar carga real del juego."
                    storage.record_execution_verification(
                        game_id=game_id,
                        last_state="INDETERMINATE",
                        exit_code=1,
                        load_confirmed=False,
                        process_time_seconds=0,
                        effective_play_seconds=0,
                        emulator_binary=str(engine_path),
                        rom_path=str(launch_target),
                        error_message=msg,
                        state_history=state_history,
                    )
                    print(f"[C.C.I. Runner] EMULATOR_ERROR: {msg}", file=sys.stderr)
                    return 1

                # Si terminó limpiamente tras el mínimo de ejecución con código 0 y sin errores
                state_history.extend(["GAME_LOAD_CONFIRMED", "GAME_RUNNING", "GAME_CLOSED"])
                proc_s = max(1, int(time.monotonic() - start_ts))
                storage.record_execution_verification(
                    game_id=game_id,
                    last_state="GAME_CLOSED",
                    exit_code=0,
                    load_confirmed=True,
                    process_time_seconds=proc_s,
                    effective_play_seconds=proc_s,
                    emulator_binary=str(engine_path),
                    rom_path=str(launch_target),
                    error_message="",
                    state_history=state_history,
                )
                storage.record_progress(game_id=game_id, title=title, last_played="Hoy", play_time_delta_s=proc_s, progress_pct=None)
                return 0

            if is_rpcs3:
                new_lines = _read_new_rpcs3_log_lines(rpcs3_log, rpcs3_log_offset)
                f_err, l_ok, l_msg = _inspect_rpcs3_log_status(new_lines)
                if f_err:
                    fatal_error = True
                    err_detail = l_msg
                    break
                if l_ok:
                    load_confirmed = True
                    break
            elif time.monotonic() >= min_wait:
                # Mantener el proceso abierto no prueba que el juego haya
                # cargado. Sólo los logs/API específicos del emulador pueden
                # confirmar esta transición.
                break

            time.sleep(0.25)

        if proc.poll() is None:
            proc.terminate()
            try:
                out_txt, err_txt = proc.communicate(timeout=3)
            except Exception:
                proc.kill()
                out_txt, err_txt = proc.communicate()
        else:
            out_txt, err_txt = proc.communicate()

        if is_rpcs3 and not fatal_error:
            new_lines = _read_new_rpcs3_log_lines(rpcs3_log, rpcs3_log_offset)
            f_err, l_ok, l_msg = _inspect_rpcs3_log_status(new_lines)
            if f_err:
                fatal_error = True
                err_detail = l_msg
            elif l_ok:
                load_confirmed = True

        proc_s = max(1, int(time.monotonic() - start_ts))
        if fatal_error or not load_confirmed:
            state_history.append("EMULATOR_ERROR" if fatal_error else "EXECUTION_INDETERMINATE")
            err_msg = err_detail or (err_txt or "").strip() or "No se pudo confirmar la carga real del juego en el emulador."
            storage.record_execution_verification(
                game_id=game_id,
                last_state="EMULATOR_ERROR" if fatal_error else "INDETERMINATE",
                exit_code=1,
                load_confirmed=False,
                process_time_seconds=proc_s,
                effective_play_seconds=0,
                emulator_binary=str(engine_path),
                rom_path=str(launch_target),
                error_message=err_msg[:500],
                state_history=state_history,
            )
            print(f"[C.C.I. Runner] EMULATOR_ERROR: {err_msg[:300]}", file=sys.stderr)
            return 1

        state_history.extend(["GAME_LOAD_CONFIRMED", "GAME_RUNNING", "GAME_CLOSED"])
        storage.record_execution_verification(
            game_id=game_id,
            last_state="GAME_CLOSED",
            exit_code=0,
            load_confirmed=True,
            process_time_seconds=proc_s,
            effective_play_seconds=proc_s,
            emulator_binary=str(engine_path),
            rom_path=str(launch_target),
            error_message="",
            state_history=state_history,
        )
        storage.record_progress(game_id=game_id, title=title, last_played="Hoy", play_time_delta_s=proc_s, progress_pct=None)
        return 0

    # Ejecución interactiva completa hasta que el usuario cierre el emulador
    out_txt, err_txt = proc.communicate()
    rc = int(proc.returncode or 0)
    proc_s = max(1, int(time.monotonic() - start_ts))
    state_history.append("PROCESS_EXITED")

    if rc != 0:
        state_history.append("EMULATOR_ERROR")
        storage.record_execution_verification(
            game_id=game_id,
            last_state="EMULATOR_ERROR",
            exit_code=rc,
            load_confirmed=False,
            process_time_seconds=proc_s,
            effective_play_seconds=0,
            emulator_binary=str(engine_path),
            rom_path=str(launch_target),
            error_message=(err_txt or out_txt or f"Código de salida {rc}")[:500],
            state_history=state_history,
        )
        return rc

    load_ok = False
    err_detail = ""
    if is_rpcs3:
        new_lines = _read_new_rpcs3_log_lines(rpcs3_log, rpcs3_log_offset)
        f_err, l_ok, l_msg = _inspect_rpcs3_log_status(new_lines)
        if f_err or not l_ok:
            err_detail = l_msg
        else:
            load_ok = True

    if not load_ok:
        state_history.append("EXECUTION_INDETERMINATE" if not is_rpcs3 else "EMULATOR_ERROR")
        storage.record_execution_verification(
            game_id=game_id,
            last_state="INDETERMINATE" if not is_rpcs3 else "EMULATOR_ERROR",
            exit_code=1,
            load_confirmed=False,
            process_time_seconds=proc_s,
            effective_play_seconds=0,
            emulator_binary=str(engine_path),
            rom_path=str(launch_target),
            error_message=(err_detail or "El emulador no proporcionó evidencia confiable de carga del juego.")[:500],
            state_history=state_history,
        )
        return 1

    state_history.extend(["GAME_LOAD_CONFIRMED", "GAME_RUNNING", "GAME_CLOSED"])
    storage.record_execution_verification(
        game_id=game_id,
        last_state="GAME_CLOSED",
        exit_code=0,
        load_confirmed=True,
        process_time_seconds=proc_s,
        effective_play_seconds=proc_s,
        emulator_binary=str(engine_path),
        rom_path=str(launch_target),
        error_message="",
        state_history=state_history,
    )
    storage.record_progress(game_id=game_id, title=title, last_played="Hoy", play_time_delta_s=proc_s, progress_pct=None)
    return 0


def run_modern_game(
    game_id: str,
    title: str,
    console_name: str,
    badge: str,
    genre: str,
    cover_rel: str,
    rom_path: str,
    width: int = 1280,
    height: int = 720,
    max_frames: int = 0,
    root_dir: Path | None = None,
) -> int:
    from backend.games.scanner_service import GameLibraryScannerService
    from backend.games.storage_manager import GameStorageManager

    base_root = (root_dir or ROOT).resolve()
    storage = GameStorageManager.get_instance(base_root)
    scanner = GameLibraryScannerService.get_instance(base_root)

    engine_path, validated_rom, status_msg = resolve_playable_engine(
        game_id=game_id,
        title=title,
        genre=genre,
        rom_arg=rom_path,
        root_dir=base_root,
    )

    if engine_path is None or validated_rom is None:
        print(f"[C.C.I. Runner] {status_msg}", file=sys.stderr)
        return 2

    game_meta = scanner.get_game_by_id(game_id) or {}
    plat_key = str(game_meta.get("platform_key") or "").lower()
    prep_ok, launch_target, prep_msg = _prepare_launch_target(validated_rom, plat_key)
    if not prep_ok or launch_target is None:
        storage.record_execution_verification(
            game_id=game_id,
            last_state="EMULATOR_ERROR",
            exit_code=3,
            load_confirmed=False,
            emulator_binary=str(engine_path),
            rom_path=str(validated_rom),
            error_message=prep_msg,
            state_history=["PROCESS_STARTED", "EMULATOR_ERROR"],
        )
        print(f"[C.C.I. Runner] Error preparando paquete: {prep_msg}", file=sys.stderr)
        return 3

    core_spec = str(game_meta.get("core") or "")
    if core_spec.startswith("external:"):
        return _run_external_emulator(
            game_id=game_id,
            title=title,
            badge=badge,
            core_spec=core_spec,
            engine_path=engine_path,
            launch_target=launch_target,
            max_frames=max_frames,
            storage=storage,
        )

    # Ejecución con núcleo Libretro nativo (ej. PS1 con pcsx_rearmed_libretro)
    state_history = ["PROCESS_STARTED"]
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.joystick.get_init():
        try:
            pygame.joystick.init()
        except Exception:
            pass

    os_label = detect_os_runtime_label()
    window_caption = f"C.C.I. SYSTEM — {title} [{badge}] ({os_label})"

    runner = LibretroRunner(
        core_path=engine_path,
        rom_path=launch_target,
        screen_w=width,
        screen_h=height,
    )
    if not runner.load_rom(launch_target):
        state_history.append("EMULATOR_ERROR")
        storage.record_execution_verification(
            game_id=game_id,
            last_state="EMULATOR_ERROR",
            exit_code=1,
            load_confirmed=False,
            emulator_binary=str(engine_path),
            rom_path=str(launch_target),
            error_message=f"Libretro retro_load_game falló para {launch_target.name}.",
            state_history=state_history,
        )
        print(f"[C.C.I. Runner] Error al cargar ROM verificada: {launch_target}", file=sys.stderr)
        return 1

    state_history.append("GAME_LOAD_CONFIRMED")

    save_dir = storage.game_save_dir(game_id)
    state_file = save_dir / "libretro_state.sav"
    restored_state = False
    if state_file.exists():
        try:
            state_bytes = state_file.read_bytes()
            if len(state_bytes) > 64:
                restored_state = runner.unserialize_state(state_bytes)
        except Exception:
            restored_state = False

    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(window_caption)
    clock = pygame.time.Clock()
    target_fps = max(30, min(60, int(round(runner.fps)))) if runner.fps else 60

    font_bar = pygame.font.SysFont("Avenir Next,Segoe UI,Arial", 14, bold=True)
    font_toast = pygame.font.SysFont("Avenir Next,Segoe UI,Arial", 16, bold=True)

    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        if not j.get_init():
            try:
                j.init()
            except Exception:
                pass

    start_time = time.monotonic()
    frame_count = 0
    toast_timer = 3.0 if restored_state else 0.0
    toast_msg = "✓ Estado de partida restaurado desde memoria de consola" if restored_state else ""
    last_view_rect = (0, 0, width, height - 34)
    running = True
    confirmed_running_marked = False

    def _save_game_state(manual: bool = False):
        nonlocal toast_timer, toast_msg
        elapsed = max(1, int(time.monotonic() - start_time))
        raw_state = runner.serialize_state()
        res = storage.record_progress(
            game_id=game_id,
            title=title,
            last_played="Hoy",
            play_time_delta_s=elapsed if not manual else 0,
            progress_pct=None,
            slot_name="libretro_state.sav" if raw_state else None,
            slot_bytes=raw_state if raw_state else None,
        )
        slots = int(res.get("save_slots", 0))
        toast_timer = 2.6
        toast_msg = f"✓ Estado guardado ({slots} slot(s))"

    while running:
        dt = clock.tick(target_fps) / 1000.0
        frame_count += 1
        if max_frames > 0 and frame_count >= max_frames:
            running = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F5:
                    _save_game_state(manual=True)
                elif event.key == pygame.K_F8 and state_file.exists():
                    try:
                        if runner.unserialize_state(state_file.read_bytes()):
                            toast_timer = 2.4
                            toast_msg = "✓ Estado cargado (F8)"
                    except Exception:
                        pass
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 8):
                    running = False

        keys = pygame.key.get_pressed()
        joy = joysticks[0] if joysticks else None
        runner.update_input(keys, joy)

        mx, my = pygame.mouse.get_pos()
        m_pressed = bool(pygame.mouse.get_pressed()[0])
        runner.update_pointer_from_mouse(mx, my, m_pressed, last_view_rect)

        runner.step_frame()
        if not confirmed_running_marked:
            state_history.append("GAME_RUNNING")
            confirmed_running_marked = True

        if not runner.is_hw_render and screen is not None:
            last_view_rect = runner.render_to(
                screen,
                screen_w=width,
                screen_h=height,
                top_offset=0,
                bottom_margin=34,
            )

        bar_rect = pygame.Rect(0, height - 34, width, 34)
        pygame.draw.rect(screen, (8, 18, 28), bar_rect)
        pygame.draw.line(screen, (39, 189, 231), (0, height - 34), (width, height - 34), 1)

        ctrl_text = (
            f"{title} [{badge}]   •   [Flechas] Mover   •   [X / Espacio] A   •   [Z] B   •   "
            f"[Enter] Start   •   [Shift] Select   •   [F5] Guardar Estado   •   [ESC] Salir"
        )
        ctrl_surf = font_bar.render(ctrl_text, True, (195, 228, 248))
        screen.blit(ctrl_surf, (max(12, (width - ctrl_surf.get_width()) // 2), height - 25))

        if toast_timer > 0 and toast_msg:
            toast_timer = max(0.0, toast_timer - dt)
            t_surf = font_toast.render(toast_msg, True, (255, 255, 255))
            tw = t_surf.get_width() + 36
            t_rect = pygame.Rect((width - tw) // 2, 16, tw, 36)
            pygame.draw.rect(screen, (14, 68, 58), t_rect, border_radius=10)
            pygame.draw.rect(screen, (86, 240, 200), t_rect, 2, border_radius=10)
            screen.blit(t_surf, (t_rect.x + 18, t_rect.y + 8))

        pygame.display.flip()

    _save_game_state(manual=False)
    elapsed_total = max(1, int(time.monotonic() - start_time))
    runner.unload()
    state_history.append("GAME_CLOSED")
    storage.record_execution_verification(
        game_id=game_id,
        last_state="GAME_CLOSED",
        exit_code=0,
        load_confirmed=confirmed_running_marked,
        process_time_seconds=elapsed_total,
        effective_play_seconds=elapsed_total if confirmed_running_marked else 0,
        emulator_binary=str(engine_path),
        rom_path=str(launch_target),
        error_message="",
        state_history=state_history,
    )
    try:
        pygame.display.quit()
    except Exception:
        pass
    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C.C.I. SYSTEM Strict Validated Game Runner")
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--console", default="Consola Moderna")
    parser.add_argument("--badge", default="PS5")
    parser.add_argument("--genre", default="Acción / Aventura")
    parser.add_argument("--cover", default="")
    parser.add_argument("--rom", default="")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args(argv)

    return run_modern_game(
        game_id=args.game_id,
        title=args.title,
        console_name=args.console,
        badge=args.badge,
        genre=args.genre,
        cover_rel=args.cover,
        rom_path=args.rom,
        width=args.width,
        height=args.height,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    raise SystemExit(main())
