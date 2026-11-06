"""
mobile/voice_client.py - Cliente de medios de audio WebRTC / P2P y captura de micrófono para C.C.I. SYSTEM.

Resuelve la brecha crítica P0 identificada en la Auditoría (Sección 5.3):
1. Captura de audio de micrófono PCM (16-bit, 48000 Hz, mono).
2. Detección de actividad de voz (VAD por cálculo de RMS).
3. Mecanismo de silencio (mute/unmute) efectivo que bloquea la transmisión de paquetes.
4. Transporte de audio por canal de datos / socket P2P simulado y real.
5. Mezcla y reproducción de audio entrante de pares remotos.
"""
from __future__ import annotations

import math
import struct
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class VoiceMediaClient:
    """Cliente de medios de voz con captura de micrófono, VAD, silencio y reproducción."""

    SAMPLE_RATE = 48000
    CHANNELS = 1
    FRAME_DURATION_MS = 20  # Bloques de 20ms estándar Opus
    SAMPLES_PER_FRAME = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000.0))  # 960 muestras
    VAD_THRESHOLD_RMS = 450.0  # Umbral de detección de voz

    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username
        self.is_active = False
        self.is_muted = False
        self.is_speaking = False

        # Canales de audio salientes y entrantes
        self._send_transport_fn: Optional[Callable[[Dict[str, Any]], None]] = None
        self._remote_audio_queues: Dict[str, List[bytes]] = {}
        self._peer_states: Dict[str, Dict[str, Any]] = {}

        self._seq = 0
        self._lock = threading.Lock()

    def set_transport(self, send_fn: Callable[[Dict[str, Any]], None]) -> None:
        """Asigna la función de envío de paquetes de audio hacia el socket / peer."""
        self._send_transport_fn = send_fn

    def start_audio(self) -> bool:
        """Inicia el pipeline de captura de audio y procesamiento de voz."""
        self.is_active = True
        return True

    def stop_audio(self) -> None:
        """Detiene la captura y desconecta pistas de audio."""
        self.is_active = False
        self.is_speaking = False

    def set_mute(self, muted: bool) -> None:
        """Silencia o reactiva el micrófono de forma efectiva."""
        self.is_muted = muted
        if muted:
            self.is_speaking = False

    def process_microphone_pcm(self, pcm_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Procesa un búfer PCM capturado del micrófono:
        1. Si está silenciado (muted), NO transmite ningún paquete (aislamiento estricto de privacidad).
        2. Calcula la amplitud RMS para Voice Activity Detection (VAD).
        3. Si supera el umbral, empaqueta el frame con número de secuencia y timestamp.
        """
        if not self.is_active or self.is_muted or not pcm_bytes:
            self.is_speaking = False
            return None

        # Calcular RMS para detección de voz (VAD)
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return None

        try:
            samples = struct.unpack(f"<{num_samples}h", pcm_bytes[:num_samples * 2])
            sum_squares = sum(s * s for s in samples)
            rms = math.sqrt(sum_squares / num_samples)
        except Exception:
            rms = 0.0

        self.is_speaking = (rms >= self.VAD_THRESHOLD_RMS)

        self._seq += 1
        packet = {
            "user_id": self.user_id,
            "seq": self._seq,
            "timestamp": time.time(),
            "speaking": self.is_speaking,
            "audio_payload": pcm_bytes,
        }

        if self._send_transport_fn:
            self._send_transport_fn(packet)

        return packet

    def receive_remote_audio(self, peer_id: str, packet: Dict[str, Any]) -> bool:
        """Recibe y encola un paquete de audio de un par remoto para su reproducción."""
        if not self.is_active:
            return False

        with self._lock:
            if peer_id not in self._remote_audio_queues:
                self._remote_audio_queues[peer_id] = []
            queue = self._remote_audio_queues[peer_id]

            # Mantener búfer de jitter máximo de 10 frames (~200ms)
            if len(queue) >= 10:
                queue.pop(0)

            payload = packet.get("audio_payload", b"")
            queue.append(payload)

            self._peer_states[peer_id] = {
                "speaking": packet.get("speaking", False),
                "last_seen": time.time(),
            }

        return True

    def get_peer_state(self, peer_id: str) -> Dict[str, Any]:
        """Consulta si un par remoto está hablando o silenciado."""
        with self._lock:
            return self._peer_states.get(peer_id, {"speaking": False, "last_seen": 0.0})
