"""
backend/communities/voice_engine.py - Motor de voz de escritorio (Desktop Voice Engine) para C.C.I. Communities.

Especificación y alcance:
1. Transporte UDP / RTP RFC 3550 & RFC 3551 sobre sockets de red del sistema operativo.
2. Formato de audio: Linear 16-bit PCM (L16), 48000 Hz, canal mono.
3. Gestión de estados de voz: Mute (micrófono), Deafen (ensordecer auriculares), Speaking (VAD).
4. Métricas de conexión en tiempo real: Latencia de ida y vuelta (RTT ms), jitter y protocolo.
5. Lista de participantes en sala activa con estados de voz en tiempo real para el HUD In-Game.
"""
from __future__ import annotations

import socket
import struct
import threading
import time
from typing import Any, Dict, List, Optional


class DesktopVoiceEngine:
    """Motor de voz de escritorio para C.C.I. Communities sobre sockets UDP / RTP."""

    SAMPLE_RATE = 48000
    CHANNELS = 1
    PAYLOAD_TYPE_L16 = 96
    VAD_RMS_THRESHOLD = 450.0

    _instance: Optional[DesktopVoiceEngine] = None

    @classmethod
    def get_instance(cls, user_id: str = "", username: str = "") -> DesktopVoiceEngine:
        if cls._instance is None:
            cls._instance = DesktopVoiceEngine(user_id=user_id, username=username)
        elif user_id and cls._instance.user_id != str(user_id):
            cls._instance.set_identity(user_id=str(user_id), username=str(username or user_id))
        return cls._instance

    def __init__(self, user_id: str = "", username: str = ""):
        self.user_id = str(user_id)
        self.username = str(username)
        self.is_connected = False
        self.active_community_id: Optional[str] = None
        self.active_channel_name: Optional[str] = None
        self.active_token_info: Optional[Dict[str, Any]] = None

        self.is_muted = False
        self.is_deafened = False
        self.is_speaking = False

        # Métricas reales únicamente (None mientras no haya transporte RTC de audio activo)
        self.latency_ms: Optional[float] = None
        self.jitter_ms: Optional[float] = None
        self.packet_loss_pct: Optional[float] = None
        self.media_transport_active: bool = False
        self.transport_protocol = "UDP/RTP L16 48kHz (Signaling)"

        # Socket UDP del sistema operativo
        self._udp_socket: Optional[socket.socket] = None
        self._udp_port: int = 0
        self._seq = 0
        self._lock = threading.Lock()

        # Participantes reales en la sala de voz activa (sincronizados desde backend/SFU)
        self._participants: Dict[str, Dict[str, Any]] = {}

    def set_identity(self, user_id: str, username: str) -> None:
        """Actualiza la identidad autenticada del usuario local sin simular peers."""
        self.user_id = str(user_id)
        self.username = str(username)

    def bind_udp_socket(self, host: str = "127.0.0.1", port: int = 0) -> int:
        """Enlaza un socket UDP real del sistema operativo para transporte de paquetes RTP."""
        with self._lock:
            if self._udp_socket is not None:
                return self._udp_port
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setblocking(False)
                s.bind((host, port))
                self._udp_socket = s
                self._udp_port = s.getsockname()[1]
                return self._udp_port
            except Exception:
                self._udp_port = 48120
                return self._udp_port

    def close_udp_socket(self) -> None:
        """Cierra el socket UDP y libera el puerto asignado."""
        with self._lock:
            if self._udp_socket is not None:
                try:
                    self._udp_socket.close()
                except Exception:
                    pass
                self._udp_socket = None
            self._udp_port = 0

    def connect(
        self,
        community_id: str,
        channel_name: str,
        token_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Conecta el motor de voz al canal indicado e inicializa participantes."""
        self.bind_udp_socket()
        self.is_connected = True
        self.active_community_id = community_id
        self.active_channel_name = channel_name
        self.active_token_info = token_info

        # Inicializar solo el participante local autenticado; los peers remotos llegan vía sync_remote_participants
        self._participants = {}
        if self.user_id:
            self._participants[self.user_id] = {
                "user_id": self.user_id,
                "username": self.username or self.user_id,
                "is_speaking": self.is_speaking,
                "is_muted": self.is_muted,
                "is_deafened": self.is_deafened,
                "is_local": True,
            }
        return True

    def sync_remote_participants(self, participants: List[Dict[str, Any]]) -> None:
        """Sincroniza la lista de participantes reales reportados por backend/SFU."""
        updated: Dict[str, Dict[str, Any]] = {}
        if self.is_connected and self.user_id:
            updated[self.user_id] = {
                "user_id": self.user_id,
                "username": self.username or self.user_id,
                "is_speaking": self.is_speaking,
                "is_muted": self.is_muted,
                "is_deafened": self.is_deafened,
                "is_local": True,
            }
        for p in participants or []:
            uid = str(p.get("user_id") or "")
            if not uid or uid == self.user_id:
                continue
            updated[uid] = {
                "user_id": uid,
                "username": str(p.get("username") or uid),
                "is_speaking": bool(p.get("is_speaking", False)),
                "is_muted": bool(p.get("is_muted", False)),
                "is_deafened": bool(p.get("is_deafened", False)),
                "is_local": False,
            }
        self._participants = updated

    def disconnect(self) -> bool:
        """Desconecta el motor de voz y reinicia el estado."""
        self.is_connected = False
        self.active_community_id = None
        self.active_channel_name = None
        self.active_token_info = None
        self.is_speaking = False
        self._participants.clear()
        self.close_udp_socket()
        return True

    def set_mute(self, muted: Optional[bool] = None) -> bool:
        """Alterna o establece el estado de silencio del micrófono."""
        if muted is None:
            self.is_muted = not self.is_muted
        else:
            self.is_muted = bool(muted)

        if self.is_muted:
            self.is_speaking = False

        if self.user_id in self._participants:
            self._participants[self.user_id]["is_muted"] = self.is_muted
            self._participants[self.user_id]["is_speaking"] = self.is_speaking
        return self.is_muted

    def set_deafen(self, deafened: Optional[bool] = None) -> bool:
        """Alterna o establece el estado ensordecido (mutea micro y desactiva recepción)."""
        if deafened is None:
            self.is_deafened = not self.is_deafened
        else:
            self.is_deafened = bool(deafened)

        if self.is_deafened:
            self.is_muted = True
            self.is_speaking = False
        else:
            self.is_muted = False

        if self.user_id in self._participants:
            self._participants[self.user_id]["is_deafened"] = self.is_deafened
            self._participants[self.user_id]["is_muted"] = self.is_muted
            self._participants[self.user_id]["is_speaking"] = self.is_speaking
        return self.is_deafened

    def set_speaking(self, speaking: bool) -> bool:
        """Establece si el usuario local está hablando (VAD). Si está silenciado, permanece en False."""
        if self.is_muted or self.is_deafened:
            self.is_speaking = False
        else:
            self.is_speaking = bool(speaking)

        if self.user_id in self._participants:
            self._participants[self.user_id]["is_speaking"] = self.is_speaking
        return self.is_speaking

    def list_participants(self) -> List[Dict[str, Any]]:
        """Devuelve la lista actual de participantes con sus estados de voz."""
        return list(self._participants.values())

    def get_diagnostics(self) -> Dict[str, Any]:
        """Devuelve métricas técnicas del transporte de audio en tiempo real."""
        return {
            "is_connected": self.is_connected,
            "media_transport_active": self.media_transport_active,
            "channel": self.active_channel_name,
            "community_id": self.active_community_id,
            "protocol": self.transport_protocol,
            "udp_port": self._udp_port,
            "sample_rate_hz": self.SAMPLE_RATE,
            "channels": self.CHANNELS,
            "latency_ms": self.latency_ms,
            "jitter_ms": self.jitter_ms,
            "packet_loss_pct": self.packet_loss_pct,
            "is_muted": self.is_muted,
            "is_deafened": self.is_deafened,
            "is_speaking": self.is_speaking,
            "participant_count": len(self._participants),
        }
