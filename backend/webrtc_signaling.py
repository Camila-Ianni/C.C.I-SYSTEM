"""
backend/webrtc_signaling.py - Enrutador de señalización WebRTC en Python.
Intercambia ofertas SDP, respuestas SDP y candidatos ICE para llamadas de voz grupales P2P Mesh.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from backend.contracts import SocketEvents, WebRTCSignalingPayload


class WebRTCSignalingRouter:
    """Enrutador de paquetes de señalización SDP e ICE sobre WebSocket."""

    def __init__(self, emit_fn: Callable[[str, Dict[str, Any], Optional[str]], None]):
        """
        emit_fn: Función para emitir eventos a clientes socket (event, data, room o target_sid).
        """
        self._emit = emit_fn

    def handle_signal(self, payload_dict: Dict[str, Any], sender_sid: str) -> bool:
        """Enruta la señal al destinatario específico o difunde en la sala."""
        try:
            payload = WebRTCSignalingPayload(
                room_id=payload_dict.get("room_id", ""),
                sender_id=payload_dict.get("sender_id", ""),
                target_id=payload_dict.get("target_id"),
                type=payload_dict.get("type", ""),
                payload=payload_dict.get("payload", {}),
            )

            # Reenviar al peer objetivo si está especificado, o a la sala
            data = payload.to_dict()
            if payload.type == "offer":
                self._emit(SocketEvents.WEBRTC_OFFER, data, payload.target_id)
            elif payload.type == "answer":
                self._emit(SocketEvents.WEBRTC_ANSWER, data, payload.target_id)
            elif payload.type == "ice-candidate":
                self._emit(SocketEvents.WEBRTC_ICE_CANDIDATE, data, payload.target_id)
            return True
        except Exception as exc:
            print(f"[WebRTCSignaling] Error procesando señalización: {exc}")
            return False
