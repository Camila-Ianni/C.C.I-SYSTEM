"""backend/communities/game_watcher.py - Watcher real de juegos por launcher y procesos del SO.

Detecta apertura y cierre de juegos tanto lanzados desde OmniDash (`QProcess` /
`retro_core_runner.py` / ejecutables nativos) como procesos independientes del sistema
operativo (`psutil`), evitando duplicados y emitiendo eventos únicos `started` / `stopped`.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import psutil
except Exception:  # pragma: no cover - fallback defensivo en entornos server sin psutil
    psutil = None  # type: ignore

logger = logging.getLogger(__name__)

ROM_EXTENSIONS = {
    ".sfc",
    ".smc",
    ".zip",
    ".z64",
    ".v64",
    ".n64",
    ".cue",
    ".nds",
    ".gba",
    ".wbfs",
    ".iso",
    ".chd",
    ".bin",
    ".nes",
    ".gb",
    ".gbc",
    ".gen",
    ".md",
    ".rvz",
    ".cso",
}

DEFAULT_EMULATORS: Tuple[Tuple[str, str], ...] = (
    ("retroarch", "RetroArch"),
    ("snes9x", "Snes9x"),
    ("snes9x-gtk", "Snes9x"),
    ("dolphin", "Dolphin Emulator"),
    ("dolphin-emu", "Dolphin Emulator"),
    ("pcsx2", "PCSX2"),
    ("pcsx2-qt", "PCSX2"),
    ("duckstation", "DuckStation"),
    ("duckstation-qt", "DuckStation"),
    ("melonds", "melonDS"),
    ("mgba", "mGBA"),
    ("mgba-qt", "mGBA"),
    ("mame", "MAME"),
    ("fbneo", "FinalBurn Neo"),
    ("mupen64plus", "Mupen64Plus"),
    ("ppsspp", "PPSSPP"),
    ("ppssppdl", "PPSSPP"),
    ("rpcs3", "RPCS3"),
    ("ryujinx", "Ryujinx"),
)


def _normalize_exe_name(raw: str) -> str:
    """Normaliza nombre o ruta de ejecutable eliminando extensiones .exe/.app."""
    val = str(raw or "").strip().replace("\\", "/")
    if not val:
        return ""
    # En macOS, un bundle .app suele terminar en .../Game.app/Contents/MacOS/Game
    if "/Contents/MacOS/" in val:
        val = val.split("/")[-1]
    else:
        val = val.rsplit("/", 1)[-1]
    low = val.lower()
    for suffix in (".exe", ".app"):
        if low.endswith(suffix):
            low = low[: -len(suffix)]
    return low


def _normalize_path_key(raw: str) -> str:
    """Normaliza una ruta o token para comparación case-insensitive cross-platform."""
    text = str(raw or "").strip().strip("\"'")
    if not text:
        return ""
    return text.replace("\\", "/").lower()


def _clean_title_from_stem(raw_name: str) -> str:
    """Limpia un nombre de archivo de ROM para usarlo como título legible."""
    stem = Path(raw_name).stem
    stem = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", stem)
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem or Path(raw_name).stem or "Juego"


def _extract_flag_value(cmdline: Sequence[str], flag: str) -> Optional[str]:
    """Extrae el valor de `--flag val` o `--flag=val` de un argv."""
    for idx, tok in enumerate(cmdline):
        if tok == flag and idx + 1 < len(cmdline):
            return str(cmdline[idx + 1])
        if tok.startswith(f"{flag}="):
            return str(tok.split("=", 1)[1])
    return None


def _extract_runner_title(cmdline: Sequence[str]) -> Optional[str]:
    """Extrae el título limpio pasado a retro_core_runner.py vía `--title`."""
    raw = _extract_flag_value(cmdline, "--title")
    if not raw:
        return None
    title = raw.strip()
    prefix = "C.C.I. SYSTEM — "
    if title.startswith(prefix):
        title = title[len(prefix):]
    if title.endswith(" (60 FPS)"):
        title = title[: -len(" (60 FPS)")]
    return title.strip() or None


def _extract_rom_candidate(cmdline: Sequence[str]) -> Optional[str]:
    """Obtiene la ruta/nombre de ROM desde `--rom` o argumentos posicionales."""
    explicit = _extract_flag_value(cmdline, "--rom")
    if explicit:
        return explicit
    for tok in cmdline[1:]:
        cleaned = str(tok or "").strip().strip("\"'")
        if not cleaned or cleaned.startswith("-"):
            continue
        if Path(cleaned).suffix.lower() in ROM_EXTENSIONS:
            return cleaned
    return None


@dataclass(frozen=True)
class WatchedGameRule:
    """Regla de detección de un juego o ejecutable monitoreado en el SO."""

    game_id: str
    title: str
    executable_names: Tuple[str, ...] = ()
    cmdline_tokens: Tuple[str, ...] = ()
    rom_paths: Tuple[str, ...] = ()
    rom_filenames: Tuple[str, ...] = ()


@dataclass
class TrackedGameSession:
    """Estado de la sesión de juego actualmente detectada/lanzada."""

    game_id: str
    title: str
    pid: Optional[int]
    source: str
    started_at: float
    process_create_time: Optional[float] = None
    child_pids: Set[int] = field(default_factory=set)
    reported_start: bool = False
    reported_stop: bool = False

    def to_payload(self, action: str) -> Dict[str, Any]:
        return {
            "action": action,
            "game_id": self.game_id,
            "title": self.title,
            "source": self.source,
            "pid": self.pid,
            "started_at": self.started_at,
        }


class GameProcessWatcher:
    """Monitorea procesos del sistema operativo y lanzamientos de OmniDash para reportar juegos activos."""

    def __init__(
        self,
        on_game_started: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_game_stopped: Optional[Callable[[Dict[str, Any]], None]] = None,
        poll_interval_sec: float = 1.0,
        include_default_emulators: bool = True,
    ):
        self.on_game_started = on_game_started
        self.on_game_stopped = on_game_stopped
        self.poll_interval_sec = max(0.05, float(poll_interval_sec))
        self.include_default_emulators = bool(include_default_emulators)

        self._lock = threading.RLock()
        self._rules: Dict[str, WatchedGameRule] = {}
        self._rom_path_index: Dict[str, Tuple[str, str]] = {}
        self._rom_name_index: Dict[str, Tuple[str, str]] = {}
        self._emulator_map: Dict[str, str] = {
            _normalize_exe_name(name): display for name, display in DEFAULT_EMULATORS
        }

        self._active: Optional[TrackedGameSession] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Configuración del catálogo y reglas monitoreadas
    # ------------------------------------------------------------------

    @staticmethod
    def psutil_available() -> bool:
        return psutil is not None

    def clear_rules(self) -> None:
        with self._lock:
            self._rules.clear()
            self._rom_path_index.clear()
            self._rom_name_index.clear()

    def register_game_rule(
        self,
        game_id: str,
        title: str,
        executable_names: Sequence[str] = (),
        cmdline_tokens: Sequence[str] = (),
        rom_paths: Sequence[str] = (),
    ) -> None:
        """Registra o actualiza una regla de detección por ejecutable, cmdline o ROM."""
        gid = str(game_id or "").strip()
        clean_title = str(title or gid).strip()
        if not gid or not clean_title:
            return
        exe_norms = tuple(dict.fromkeys(_normalize_exe_name(x) for x in executable_names if _normalize_exe_name(x)))
        tok_norms = tuple(dict.fromkeys(_normalize_path_key(t) for t in cmdline_tokens if _normalize_path_key(t)))
        rom_norms = tuple(dict.fromkeys(_normalize_path_key(r) for r in rom_paths if _normalize_path_key(r)))
        rom_names = tuple(dict.fromkeys(Path(r).name.lower() for r in rom_paths if r))
        rule = WatchedGameRule(
            game_id=gid,
            title=clean_title,
            executable_names=exe_norms,
            cmdline_tokens=tok_norms,
            rom_paths=rom_norms,
            rom_filenames=rom_names,
        )
        with self._lock:
            self._rules[gid] = rule
            for rp in rom_norms:
                self._rom_path_index[rp] = (gid, clean_title)
            for rn in rom_names:
                self._rom_name_index.setdefault(rn, (gid, clean_title))

    def unregister_game_rule(self, game_id: str) -> None:
        gid = str(game_id or "").strip()
        with self._lock:
            old = self._rules.pop(gid, None)
            if old:
                for rp in old.rom_paths:
                    self._rom_path_index.pop(rp, None)
                self._rebuild_rom_name_index_locked()

    def _rebuild_rom_name_index_locked(self) -> None:
        self._rom_name_index.clear()
        for rule in self._rules.values():
            for rn in rule.rom_filenames:
                self._rom_name_index.setdefault(rn, (rule.game_id, rule.title))

    def set_catalog_games(self, games: Iterable[Dict[str, Any]]) -> int:
        """Sincroniza reglas e índice de ROMs a partir del catálogo escaneado."""
        new_rules: Dict[str, WatchedGameRule] = {}
        new_rom_paths: Dict[str, Tuple[str, str]] = {}
        new_rom_names: Dict[str, Tuple[str, str]] = {}

        count = 0
        for g in games:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id") or g.get("game_id") or "").strip()
            title = str(g.get("title") or gid).strip()
            if not gid or not title:
                continue
            rom_raw = str(g.get("rom") or g.get("rom_path") or "").strip()
            exe_raw = g.get("executable") or g.get("exe") or g.get("process_name") or g.get("command")
            exes: List[str] = []
            if isinstance(exe_raw, (list, tuple)) and exe_raw:
                exes.append(str(exe_raw[0]))
            elif isinstance(exe_raw, str) and exe_raw.strip():
                exes.append(exe_raw.strip())

            exe_norms = tuple(dict.fromkeys(_normalize_exe_name(x) for x in exes if _normalize_exe_name(x)))
            rom_paths = (_normalize_path_key(rom_raw),) if rom_raw else ()
            rom_names = (Path(rom_raw).name.lower(),) if rom_raw else ()
            toks = tuple(str(t).lower() for t in (g.get("cmdline_tokens") or ()) if str(t).strip())

            rule = WatchedGameRule(
                game_id=gid,
                title=title,
                executable_names=exe_norms,
                cmdline_tokens=toks,
                rom_paths=rom_paths,
                rom_filenames=rom_names,
            )
            new_rules[gid] = rule
            for rp in rom_paths:
                new_rom_paths[rp] = (gid, title)
            for rn in rom_names:
                new_rom_names.setdefault(rn, (gid, title))
            count += 1

        with self._lock:
            self._rules = new_rules
            self._rom_path_index = new_rom_paths
            self._rom_name_index = new_rom_names
        return count

    # ------------------------------------------------------------------
    # Notificaciones directas desde el Launcher de OmniDash (QProcess)
    # ------------------------------------------------------------------

    def notify_launcher_started(
        self,
        game_id: str,
        title: str,
        pid: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Registra un juego lanzado desde OmniDash evitando duplicar `started`."""
        gid = str(game_id or title or "").strip()
        clean_title = str(title or gid).strip()
        if not clean_title:
            return None

        create_time = self._read_create_time(pid)
        stopped_prev: Optional[Dict[str, Any]] = None
        started_payload: Optional[Dict[str, Any]] = None

        with self._lock:
            cur = self._active
            if cur is not None:
                same_pid = pid is not None and cur.pid == pid
                same_game = cur.game_id == gid and cur.title == clean_title
                if same_pid or (same_game and self._is_session_alive_locked(cur)):
                    if pid is not None and cur.pid is None:
                        cur.pid = pid
                        cur.process_create_time = create_time
                    return None
                if not cur.reported_stop:
                    cur.reported_stop = True
                    stopped_prev = cur.to_payload("stopped")
                self._active = None

            sess = TrackedGameSession(
                game_id=gid,
                title=clean_title,
                pid=pid,
                source="launcher",
                started_at=time.time(),
                process_create_time=create_time,
                child_pids=self._collect_children(pid) if pid else set(),
                reported_start=True,
            )
            self._active = sess
            started_payload = sess.to_payload("started")

        if stopped_prev is not None:
            self._dispatch_stopped(stopped_prev)
        if started_payload is not None:
            self._dispatch_started(started_payload)
        return started_payload

    def notify_launcher_stopped(
        self,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Marca cierre desde `QProcess`. Si el launcher dejó procesos hijos vivos, continúa rastreando."""
        stopped_payload: Optional[Dict[str, Any]] = None
        with self._lock:
            cur = self._active
            if cur is None or cur.reported_stop:
                return None
            if pid is not None and cur.pid is not None and cur.pid != pid and cur.pid not in cur.child_pids:
                if game_id and cur.game_id != game_id:
                    return None
            elif game_id and cur.game_id != game_id and (pid is None or cur.pid != pid):
                return None

            if not force and self._promote_live_child_locked(cur):
                return None

            cur.reported_stop = True
            stopped_payload = cur.to_payload("stopped")
            self._active = None

        if stopped_payload is not None:
            self._dispatch_stopped(stopped_payload)
        return stopped_payload

    def active_game(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._active is None:
                return None
            return self._active.to_payload("started")

    # ------------------------------------------------------------------
    # Ciclo de vida de polling con psutil
    # ------------------------------------------------------------------

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(
                target=self._poll_loop,
                name="cci-game-process-watcher",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self, timeout: float = 1.5) -> None:
        with self._lock:
            self._running = False
            self._stop_event.set()
            th = self._thread
            self._thread = None
        if th is not None and th.is_alive() and th is not threading.current_thread():
            th.join(timeout=timeout)

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # pragma: no cover - resiliencia en loop daemon
                logger.debug("GameProcessWatcher poll error: %s", exc)
            if self._stop_event.wait(self.poll_interval_sec):
                break

    def poll_once(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Ejecuta un ciclo de inspección del árbol de procesos del SO y retorna transiciones."""
        transitions: List[Tuple[str, Dict[str, Any]]] = []
        to_dispatch: List[Tuple[str, Dict[str, Any]]] = []

        if psutil is None:
            return transitions

        with self._lock:
            cur = self._active
            if cur is not None:
                if self._is_session_alive_locked(cur):
                    return transitions
                # El juego activo ya no existe en el SO -> emitir stopped
                if not cur.reported_stop:
                    cur.reported_stop = True
                    payload = cur.to_payload("stopped")
                    transitions.append(("stopped", payload))
                    to_dispatch.append(("stopped", payload))
                self._active = None

            detected = self._scan_processes_locked()
            if detected is not None:
                detected.reported_start = True
                self._active = detected
                payload = detected.to_payload("started")
                transitions.append(("started", payload))
                to_dispatch.append(("started", payload))

        for action, payload in to_dispatch:
            if action == "started":
                self._dispatch_started(payload)
            else:
                self._dispatch_stopped(payload)
        return transitions

    # ------------------------------------------------------------------
    # Inspección interna de procesos (bajo self._lock)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_create_time(pid: Optional[int]) -> Optional[float]:
        if psutil is None or pid is None or pid <= 0:
            return None
        try:
            return float(psutil.Process(int(pid)).create_time())
        except Exception:
            return None

    @staticmethod
    def _is_pid_valid(pid: Optional[int], expected_create_time: Optional[float]) -> bool:
        if psutil is None or pid is None or pid <= 0:
            return False
        try:
            proc = psutil.Process(int(pid))
            if not proc.is_running():
                return False
            status = proc.status()
            if status == psutil.STATUS_ZOMBIE:
                return False
            if expected_create_time is not None:
                if abs(float(proc.create_time()) - expected_create_time) > 1.0:
                    return False
            return True
        except Exception:
            return False

    def _collect_children(self, pid: int) -> Set[int]:
        if psutil is None:
            return set()
        try:
            proc = psutil.Process(int(pid))
            return {c.pid for c in proc.children(recursive=True) if c.is_running()}
        except Exception:
            return set()

    def _promote_live_child_locked(self, sess: TrackedGameSession) -> bool:
        """Si el PID principal terminó pero dejó hijos vivos (o proceso coincidente), promueve su PID."""
        if sess.pid is not None:
            sess.child_pids.update(self._collect_children(sess.pid))
        for cpid in list(sess.child_pids):
            if self._is_pid_valid(cpid, None):
                sess.pid = cpid
                sess.process_create_time = self._read_create_time(cpid)
                sess.child_pids.discard(cpid)
                return True
        if sess.game_id in self._rules:
            found = self._scan_processes_locked(target_game_id=sess.game_id)
            if found is not None and found.pid is not None:
                sess.pid = found.pid
                sess.process_create_time = found.process_create_time
                return True
        return False

    def _is_session_alive_locked(self, sess: TrackedGameSession) -> bool:
        if sess.pid is None:
            return True
        if self._is_pid_valid(sess.pid, sess.process_create_time):
            sess.child_pids.update(self._collect_children(sess.pid))
            return True
        return self._promote_live_child_locked(sess)

    def _scan_processes_locked(self, target_game_id: Optional[str] = None) -> Optional[TrackedGameSession]:
        if psutil is None:
            return None
        self_pid = os.getpid()
        attrs = ["pid", "name", "exe", "cmdline", "create_time", "status"]
        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                pid = int(info.get("pid") or 0)
                if pid <= 0 or pid == self_pid:
                    continue
                if info.get("status") == getattr(psutil, "STATUS_ZOMBIE", "zombie"):
                    continue
                name = str(info.get("name") or "")
                exe = str(info.get("exe") or "")
                cmdline = [str(x) for x in (info.get("cmdline") or ()) if x is not None]
                matched = self._match_process_locked(name=name, exe=exe, cmdline=cmdline)
                if matched is not None:
                    gid, title = matched
                    if target_game_id is not None and gid != target_game_id:
                        continue
                    ctime = float(info["create_time"]) if info.get("create_time") else None
                    return TrackedGameSession(
                        game_id=gid,
                        title=title,
                        pid=pid,
                        source="process",
                        started_at=time.time(),
                        process_create_time=ctime,
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue
        return None

    def _match_process_locked(
        self,
        name: str,
        exe: str,
        cmdline: Sequence[str],
    ) -> Optional[Tuple[str, str]]:
        # Evitar falsos positivos con procesos de test (pytest/unittest) que puedan mencionar nombres
        joined_low = " ".join(_normalize_path_key(tok) for tok in cmdline)
        first_norm = _normalize_exe_name(cmdline[0]) if cmdline else ""
        if "pytest" in joined_low or first_norm in ("pytest", "py.test"):
            return None

        exe_candidates = {
            c
            for c in (
                _normalize_exe_name(name),
                _normalize_exe_name(exe),
                first_norm,
            )
            if c
        }

        # 1. Reglas explícitas (juegos nativos o reglas custom con ejecutable/tokens)
        for rule in self._rules.values():
            if not rule.executable_names and not rule.cmdline_tokens:
                continue
            exe_ok = (not rule.executable_names) or any(e in exe_candidates for e in rule.executable_names)
            tok_ok = (not rule.cmdline_tokens) or all(tok in joined_low for tok in rule.cmdline_tokens)
            if exe_ok and tok_ok:
                return rule.game_id, rule.title

        # 2. Subproceso retro_core_runner.py lanzado fuera de QProcess o directamente en SO
        if any("retro_core_runner.py" in _normalize_path_key(tok) for tok in cmdline):
            rom_cand = _extract_rom_candidate(cmdline)
            if rom_cand:
                found = self._resolve_rom_to_catalog_locked(rom_cand)
                if found is not None:
                    return found
            title = _extract_runner_title(cmdline)
            if title:
                gid = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "retro_game"
                return gid, title
            if rom_cand:
                stem = _clean_title_from_stem(rom_cand)
                gid = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_") or "retro_game"
                return gid, stem

        # 3. Emuladores standalone conocidos (p. ej. RetroArch, Dolphin, Snes9x, PCSX2...)
        if self.include_default_emulators:
            for cand in exe_candidates:
                if cand in self._emulator_map:
                    rom_cand = _extract_rom_candidate(cmdline)
                    if rom_cand:
                        found = self._resolve_rom_to_catalog_locked(rom_cand)
                        if found is not None:
                            return found
                        stem = _clean_title_from_stem(rom_cand)
                        gid = f"rom_{re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_') or 'game'}"
                        return gid, stem
                    return f"emu_{cand}", self._emulator_map[cand]
        return None

    def _resolve_rom_to_catalog_locked(self, rom_candidate: str) -> Optional[Tuple[str, str]]:
        norm = _normalize_path_key(rom_candidate)
        if norm in self._rom_path_index:
            return self._rom_path_index[norm]
        # Comparar rutas resueltas si el token era relativo
        for known_path, pair in self._rom_path_index.items():
            if norm.endswith(known_path) or known_path.endswith(norm):
                return pair
        fname = Path(norm).name.lower()
        if fname in self._rom_name_index:
            return self._rom_name_index[fname]
        return None

    # ------------------------------------------------------------------
    # Despacho fuera del lock
    # ------------------------------------------------------------------

    def _dispatch_started(self, payload: Dict[str, Any]) -> None:
        cb = self.on_game_started
        if cb is not None:
            try:
                cb(payload)
            except Exception as exc:
                logger.warning("Error in on_game_started callback: %s", exc)

    def _dispatch_stopped(self, payload: Dict[str, Any]) -> None:
        cb = self.on_game_stopped
        if cb is not None:
            try:
                cb(payload)
            except Exception as exc:
                logger.warning("Error in on_game_stopped callback: %s", exc)
