"""
backend/chat_service.py - Servicio de Chat en Tiempo Real y Control de Abuso/Spam.
Implementa las especificaciones funcionales de la Fase 3 (Módulo B.2) para C.C.I. SYSTEM.
"""
from __future__ import annotations

import collections
import secrets
import time
from typing import Any, Callable, Dict, List, Optional
import cci_database
from backend.contracts import ChatMessagePayload, SocketEvents


class ChatService:
    """Servicio desacoplado de mensajería grupal con control de spam y moderación."""

    _instance: Optional[ChatService] = None

    @classmethod
    def get_instance(cls) -> ChatService:
        if cls._instance is None:
            cls._instance = ChatService()
        return cls._instance

    def __init__(self, broadcast_fn: Optional[Callable[[str, Dict[str, Any], str], None]] = None):
        """
        broadcast_fn: Función para emitir eventos a la sala Socket.IO del grupo: (event, data, room).
        """
        self._broadcast = broadcast_fn
        # Registro de timestamps de mensajes para anti-spam: user_id -> deque([t1, t2, ...], maxlen=10)
        self._user_msg_times: Dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=10))

        # Parámetros de moderación
        self.MAX_MSG_LENGTH = 500
        self.SPAM_BURST_LIMIT = 5  # máx 5 mensajes
        self.SPAM_WINDOW_SECONDS = 3.0  # en ventana de 3 segundos

    def set_broadcast_fn(self, broadcast_fn: Callable[[str, Dict[str, Any], str], None]) -> None:
        self._broadcast = broadcast_fn

    # ==============================================================================
    # 1. ENVÍO DE MENSAJES Y FILTROS ANTI-ABUSO
    # ==============================================================================

    def send_message(
        self,
        group_id: str,
        sender_id: str,
        sender_name: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Envía un mensaje de texto validando:
        1. Longitud (1 a 500 caracteres).
        2. Frecuencia (Rate-limiting anti-spam).
        3. Membresía y estado silenciado (muted/banned).
        """
        # Validación de longitud y contenido
        clean_body = body.strip() if body else ""
        if not clean_body:
            return {"success": False, "error": "El mensaje no puede estar vacío."}
        if len(clean_body) > self.MAX_MSG_LENGTH:
            return {"success": False, "error": f"El mensaje supera el límite máximo de {self.MAX_MSG_LENGTH} caracteres."}

        # Control Anti-Spam (Rate limiting con ventana deslizante)
        now = time.monotonic()
        times = self._user_msg_times[sender_id]
        # Limpiar marcas de tiempo antiguas fuera de la ventana
        while times and (now - times[0]) > self.SPAM_WINDOW_SECONDS:
            times.popleft()

        if len(times) >= self.SPAM_BURST_LIMIT:
            return {
                "success": False,
                "error": "Estás enviando mensajes demasiado rápido. Espera unos segundos (Protección Anti-Spam)."
            }

        # Validación de Membresía y Permisos en el Grupo
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "El grupo no existe."}

        member = next((m for m in grp["members"] if m["user_id"] == sender_id), None)
        if not member:
            return {"success": False, "error": "No eres miembro de este grupo para enviar mensajes."}

        if member.get("status") in ("muted", "banned"):
            return {"success": False, "error": "Tu cuenta está silenciada en este grupo por moderación."}

        # Registrar timestamp exitoso
        times.append(now)

        # Persistir en SQLite
        msg_id = f"msg_{secrets.token_hex(6)}"
        entry = cci_database.save_chat_message_entry(
            message_id=msg_id,
            group_id=group_id,
            sender_id=sender_id,
            body=clean_body
        )

        payload = ChatMessagePayload(
            message_id=msg_id,
            group_id=group_id,
            sender_id=sender_id,
            sender_name=sender_name,
            body=clean_body,
            timestamp_iso=entry["created_at"],
        )

        # Emitir en tiempo real a los participantes conectados en la sala del grupo
        if self._broadcast:
            self._broadcast(SocketEvents.CHAT_MESSAGE, payload.to_dict(), group_id)

        return {"success": True, "message": payload.to_dict()}

    # ==============================================================================
    # 2. HISTORIAL PAGINADO Y RECUPERACIÓN
    # ==============================================================================

    def get_history(
        self,
        group_id: str,
        limit: int = 30,
        before_created_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene el historial paginado de mensajes de un grupo."""
        safe_limit = max(1, min(limit, 100))
        messages = cci_database.get_paged_messages_entry(
            group_id=group_id,
            limit=safe_limit,
            before_created_at=before_created_at
        )
        return {
            "group_id": group_id,
            "count": len(messages),
            "messages": messages,
        }

    # ==============================================================================
    # 3. MODERACIÓN: BORRADO LÓGICO Y REPORTES
    # ==============================================================================

    def delete_message(self, message_id: str, actor_id: str) -> Dict[str, Any]:
        """
        Elimina un mensaje lógicamente.
        Permitido para: autor del mensaje, admin del grupo o dueño del grupo.
        """
        msg = cci_database.get_chat_message_by_id(message_id)
        if not msg:
            return {"success": False, "error": "El mensaje no existe."}
        if msg.get("deleted_at"):
            return {"success": False, "error": "El mensaje ya fue eliminado."}

        group_id = msg["group_id"]
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "Grupo asociado no encontrado."}

        actor_member = next((m for m in grp["members"] if m["user_id"] == actor_id), None)
        if not actor_member:
            return {"success": False, "error": "No eres miembro de este grupo."}

        is_author = (msg["sender_id"] == actor_id)
        is_staff = actor_member.get("role") in ("owner", "admin")

        if not (is_author or is_staff):
            return {"success": False, "error": "No tienes permisos para eliminar este mensaje."}

        ok = cci_database.soft_delete_chat_message_entry(message_id)
        return {"success": ok, "message": "Mensaje eliminado correctamente."}

    def report_message(self, message_id: str, reporter_id: str, reason: str) -> Dict[str, Any]:
        """Registra un reporte de abuso/spam sobre un mensaje."""
        msg = cci_database.get_chat_message_by_id(message_id)
        if not msg:
            return {"success": False, "error": "El mensaje no existe."}

        clean_reason = reason.strip() if reason else "Contenido inapropiado"
        report_id = f"rep_{secrets.token_hex(4)}"
        ok = cci_database.record_message_report_entry(report_id, message_id, reporter_id, clean_reason)
        return {"success": ok, "message": "Reporte registrado para moderación."}
