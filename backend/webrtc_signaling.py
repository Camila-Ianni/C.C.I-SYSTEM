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
        """Enruta la señal al destinatario específico de forma autoritativa y fail-closed."""
        try:
            room_id = str(payload_dict.get("room_id", "")).strip()
            sender_id = str(payload_dict.get("sender_id", "")).strip()
            target_id = payload_dict.get("target_id")
            sig_type = str(payload_dict.get("type", "")).strip()

            # Validación de presencia obligatoria de sesión y tipo
            if not room_id or not sender_id or sig_type not in ("offer", "answer", "ice-candidate"):
                return False

            # Comprobar pertenencia del emisor a la llamada activa (Fail-Closed estricto)
            if not check_call_participation(sender_id, room_id):
                return False

            # Si target_id está definido, validar que el destinatario PERTENEZCA a la misma llamada
            if target_id:
                target_str = str(target_id).strip()
                if not check_call_participation(target_str, room_id):
                    return False

            payload = WebRTCSignalingPayload(
                room_id=room_id,
                sender_id=sender_id,
                target_id=target_id,
                type=sig_type,
                payload=payload_dict.get("payload", {}),
            )

            data = payload.to_dict()

            # Si target_id es un user_id, buscar sus sockets activos
            if target_id:
                user_sids = get_sockets_by_user(str(target_id))
                if user_sids:
                    for sid in user_sids:
                        self._dispatch_event(sig_type, data, sid)
                    return True
                # Si target_id no tiene socket registrado, emitir directamente al canal de target
                self._dispatch_event(sig_type, data, str(target_id))
                return True

            # Si target_id es la sala completa
            self._dispatch_event(sig_type, data, room_id)
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
