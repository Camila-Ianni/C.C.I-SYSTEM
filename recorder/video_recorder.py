"""
recorder/video_recorder.py - Grabador de video de gameplay asíncrono para C.C.I. SYSTEM.
Implementa las especificaciones de la Fase 6 (Módulo C).
100% Python con OpenCV Headless, codificación MP4 en Worker Thread dedicado a 30 FPS
sin penalización en el bucle principal de 60 FPS de la consola.
"""
from __future__ import annotations

import os
import queue
import secrets
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Silenciar warnings de símbolos Objective-C SDL2 duplicados entre pygame y opencv-python en macOS
_old_stderr_fd = None
try:
    sys.stderr.flush()
    _old_stderr_fd = os.dup(2)
    _devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull_fd, 2)
    os.close(_devnull_fd)
except Exception:
    _old_stderr_fd = None

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore

if _old_stderr_fd is not None:
    try:
        os.dup2(_old_stderr_fd, 2)
        os.close(_old_stderr_fd)
    except Exception:
        pass

import cci_database
from backend.config import config

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECORDINGS_DIR = ROOT / "grabaciones"


class GameplayVideoRecorder:
    """Grabador de sesiones de juego desacoplado en segundo plano."""

    _instance: Optional[GameplayVideoRecorder] = None

    @classmethod
    def get_instance(cls) -> GameplayVideoRecorder:
        if cls._instance is None:
            cls._instance = GameplayVideoRecorder()
        return cls._instance

    def __init__(self, output_dir: Optional[Path] = None, max_quota_mb: Optional[int] = None):
        self.output_dir = output_dir or Path(config.recordings_path)
        self.max_quota_mb = max_quota_mb if max_quota_mb is not None else config.max_recordings_mb

        self.is_recording: bool = False
        self.current_recording_id: Optional[str] = None
        self.current_game_id: str = "general"
        self.current_owner_id: str = "pilot"

        self._start_time: float = 0.0
        self._target_w: int = 960
        self._target_h: int = 540
        self._fps: float = 30.0

        self._frame_queue: queue.Queue = queue.Queue(maxsize=90)
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._active_filepath: Optional[Path] = None
        self._active_thumbpath: Optional[Path] = None
        self._frames_written: int = 0

    def start_recording(
        self,
        game_id: str = "general",
        owner_id: str = "pilot",
        target_w: int = 960,
        target_h: int = 540,
        fps: float = 30.0
    ) -> Dict[str, Any]:
        """Inicia una nueva sesión de grabación en segundo plano."""
        if self.is_recording:
            return {"success": False, "error": "Ya hay una grabación en curso."}

        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Aplicar política de depuración FIFO si el disco supera la cuota
        self._enforce_storage_quota()

        self.current_recording_id = f"rec_{secrets.token_hex(4)}"
        self.current_game_id = game_id
        self.current_owner_id = owner_id
        self._target_w = target_w
        self._target_h = target_h
        self._fps = fps

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"clip_{timestamp}_{game_id}.mp4"
        thumb_name = f"thumb_{timestamp}_{game_id}.png"

        self._active_filepath = self.output_dir / filename
        self._active_thumbpath = self.output_dir / thumb_name

        self._frame_queue = queue.Queue(maxsize=90)
        self._stop_event.clear()
        self._frames_written = 0
        self._start_time = time.monotonic()
        self.is_recording = True

        self._worker_thread = threading.Thread(target=self._encoding_worker, daemon=True)
        self._worker_thread.start()

        return {
            "success": True,
            "recording_id": self.current_recording_id,
            "game_id": self.current_game_id,
            "output_file": str(self._active_filepath),
        }

    def capture_surface(self, surface: pygame.Surface) -> bool:
        """
        Captura la superficie actual de Pygame y la encola sin bloquear.
        Si la cola está llena (saturación transitoria de CPU), descarta el frame
        para garantizar que el bucle de juego nunca caiga de 60 FPS.
        """
        if not self.is_recording or surface is None:
            return False

        try:
            # Capturar buffer (w, h, 3) y transponer a (h, w, 3)
            arr = pygame.surfarray.array3d(surface)
            frame_rgb = np.transpose(arr, (1, 0, 2))
            self._frame_queue.put_nowait(frame_rgb)
            return True
        except queue.Full:
            # Descartar frame silenciosamente sin penalizar FPS
            return False
        except Exception:
            return False

    def stop_recording(self) -> Dict[str, Any]:
        """
        Detiene la grabación, vacía la cola de frames, asegura el cierre de OpenCV VideoWriter,
        valida la integridad física del contenedor MP4 y persiste metadatos garantizados en SQLite.
        """
        if not self.is_recording:
            return {"success": False, "error": "No hay grabación activa."}

        self.is_recording = False
        self._stop_event.set()

        # Esperar finalización del worker asegurando que todos los frames en cola se escriban
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10.0)
            if self._worker_thread.is_alive():
                return {
                    "success": False,
                    "error": "Timeout esperando cierre del hilo codificador de video.",
                }

        duration = max(0.1, time.monotonic() - self._start_time)
        filepath = self._active_filepath
        thumbpath = self._active_thumbpath

        # Validación de integridad del archivo MP4
        if not filepath or not filepath.exists():
            return {
                "success": False,
                "error": "El archivo de video MP4 no fue generado en disco.",
            }

        file_size = filepath.stat().st_size
        if file_size < 32 or self._frames_written == 0:
            try:
                filepath.unlink(missing_ok=True)
                if thumbpath and thumbpath.exists():
                    thumbpath.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "success": False,
                "error": "Archivo de video corrupto o sin frames capturados.",
            }

        # Verificar cabecera MP4 (ISO Base Media File Format: ftyp/mdat/moov)
        try:
            with open(filepath, "rb") as f:
                header = f.read(64)
                if b"ftyp" not in header and b"mdat" not in header and b"moov" not in header:
                    return {
                        "success": False,
                        "error": "Cabecera de contenedor MP4 inválida.",
                    }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Error leyendo contenedor de video: {exc}",
            }

        # Validación y decodificación real del archivo MP4 mediante OpenCV VideoCapture con muestreo distribuido
        cap = cv2.VideoCapture(str(filepath))
        is_opened = cap.isOpened()
        decoded_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if is_opened else 0
        decoded_fps = cap.get(cv2.CAP_PROP_FPS) if is_opened else 0.0

        valid_sampling = False
        if is_opened and decoded_frames > 0:
            sample_points = [0.0, 0.25, 0.50, 0.75, 1.0]
            sampled_success = 0
            for pt in sample_points:
                target_frame_idx = min(int(round(pt * (decoded_frames - 1))), max(0, decoded_frames - 1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
                ret_sample, sample_frame = cap.read()
                if ret_sample and sample_frame is not None and sample_frame.size > 0:
                    sampled_success += 1
            valid_sampling = (sampled_success == len(sample_points))
        cap.release()

        if not is_opened or not valid_sampling:
            try:
                filepath.unlink(missing_ok=True)
                if thumbpath and thumbpath.exists():
                    thumbpath.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "success": False,
                "error": "El archivo MP4 no es reproducible o falló la decodificación en muestreo distribuido.",
            }

        effective_fps = round(self._frames_written / duration, 2)

        # Persistir en SQLite únicamente con integridad certificada
        rec_id = self.current_recording_id or f"rec_{secrets.token_hex(4)}"
        try:
            cci_database.save_gameplay_recording_entry(
                recording_id=rec_id,
                owner_id=self.current_owner_id,
                game_id=self.current_game_id,
                local_path=str(filepath),
                duration_seconds=round(duration, 1),
                size_bytes=file_size,
                thumbnail_path=str(thumbpath) if (thumbpath and thumbpath.exists()) else None,
            )
        except Exception as exc:
            print(f"[VideoRecorder] Error guardando metadatos en SQLite: {exc}")

        result = {
            "success": True,
            "recording_id": rec_id,
            "game_id": self.current_game_id,
            "duration_seconds": round(duration, 1),
            "size_bytes": file_size,
            "frames_written": self._frames_written,
            "effective_fps": effective_fps,
            "file_path": str(filepath),
            "thumbnail_path": str(thumbpath) if (thumbpath and thumbpath.exists()) else None,
        }

        self.current_recording_id = None
        self._active_filepath = None
        self._active_thumbpath = None
        return result

    def get_status(self) -> Dict[str, Any]:
        """Estado actual del grabador."""
        duration = (time.monotonic() - self._start_time) if self.is_recording else 0.0
        return {
            "is_recording": self.is_recording,
            "recording_id": self.current_recording_id,
            "game_id": self.current_game_id,
            "elapsed_seconds": round(duration, 1),
            "frames_written": self._frames_written,
        }

    # ==============================================================================
    # HILO TRABAJADOR Y POLÍTICA DE CUOTA FIFO
    # ==============================================================================

    def _encoding_worker(self):
        """Worker thread dedicado a la codificación MP4 asíncrona."""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(self._active_filepath),
            fourcc,
            self._fps,
            (self._target_w, self._target_h)
        )

        thumb_saved = False
        while not self._stop_event.is_set() or not self._frame_queue.empty():
            try:
                frame_rgb = self._frame_queue.get(timeout=0.05)
                # Reescalar si difiere de la resolución objetivo (ej. 1280x720 a 960x540)
                h, w = frame_rgb.shape[:2]
                if (w, h) != (self._target_w, self._target_h):
                    resized = cv2.resize(frame_rgb, (self._target_w, self._target_h), interpolation=cv2.INTER_LINEAR)
                else:
                    resized = frame_rgb

                bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR)
                writer.write(bgr)
                self._frames_written += 1

                # Generar miniatura PNG desde el primer frame válido
                if not thumb_saved and self._active_thumbpath:
                    try:
                        thumb_w, thumb_h = 320, 180
                        thumb_img = cv2.resize(bgr, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
                        cv2.imwrite(str(self._active_thumbpath), thumb_img)
                        thumb_saved = True
                    except Exception:
                        pass

                self._frame_queue.task_done()
            except queue.Empty:
                pass
            except Exception as exc:
                print(f"[VideoRecorder] Error en hilo de codificación: {exc}")

        writer.release()

    def _enforce_storage_quota(self):
        """Aplica la política de depuración FIFO si el almacenamiento supera el límite fijado."""
        try:
            max_bytes = self.max_quota_mb * 1024 * 1024
            current_bytes = cci_database.get_total_recordings_disk_usage()

            while current_bytes > max_bytes:
                oldest = cci_database.get_oldest_gameplay_recording()
                if not oldest:
                    break

                # Borrar archivo físico de video y miniatura
                if oldest.get("local_path") and os.path.exists(oldest["local_path"]):
                    try:
                        os.remove(oldest["local_path"])
                    except Exception:
                        pass
                if oldest.get("thumbnail_path") and os.path.exists(oldest["thumbnail_path"]):
                    try:
                        os.remove(oldest["thumbnail_path"])
                    except Exception:
                        pass

                cci_database.delete_gameplay_recording_entry(oldest["id"])
                current_bytes = cci_database.get_total_recordings_disk_usage()
        except Exception as exc:
            print(f"[VideoRecorder] Error aplicando cuota de almacenamiento: {exc}")
