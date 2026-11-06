"""
backend/webrtc_signaling.py - Enrutador de señalización WebRTC en Python.
Intercambia ofertas SDP, respuestas SDP y candidatos ICE para llamadas de voz grupales P2P Mesh.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from backend.auth import get_sockets_by_user, check_call_participation
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
            room_id = payload_dict.get("room_id", "")
            sender_id = payload_dict.get("sender_id", "")
            target_id = payload_dict.get("target_id")
            sig_type = payload_dict.get("type", "")

            # Si hay session_id de llamada de voz, validar pertenencia
            if room_id and not check_call_participation(sender_id, room_id):
                # Si no está en la llamada, rechazar señal
                return False

            payload = WebRTCSignalingPayload(
                room_id=room_id,
                sender_id=sender_id,
                target_id=target_id,
                type=sig_type,
                payload=payload_dict.get("payload", {}),
            )

            data = payload.to_dict()
            target_destination = target_id

            # Si target_id es un user_id, buscar sus sockets activos
            if target_id:
                user_sids = get_sockets_by_user(target_id)
                if user_sids:
                    # Enviar a todos los sockets del usuario objetivo
                    for sid in user_sids:
                        self._dispatch_event(sig_type, data, sid)
                    return True

            # Si target_id es un room o sid directo
            self._dispatch_event(sig_type, data, target_destination)
            return True
        except Exception as exc:
            print(f"[WebRTCSignaling] Error procesando señalización: {exc}")
            return False

    def _dispatch_event(self, sig_type: str, data: Dict[str, Any], destination: Optional[str]) -> None:
        if sig_type == "offer":
            self._emit(SocketEvents.WEBRTC_OFFER, data, destination)
        elif sig_type == "answer":
            self._emit(SocketEvents.WEBRTC_ANSWER, data, destination)
        elif sig_type == "ice-candidate":
            self._emit(SocketEvents.WEBRTC_ICE_CANDIDATE, data, destination)
