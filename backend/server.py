"""
backend/server.py - Servidor principal de tiempo real y backend API para C.C.I. SYSTEM.
Combina Flask + Flask-SocketIO con soporte de WebSockets bidireccionales y fallback polling.
"""
from __future__ import annotations

import os
from typing import Any, Dict
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from backend.config import config
from backend.contracts import SocketEvents
from backend.room_manager import RoomManager
from backend.sync_engine import AuthoritativeSyncEngine
from backend.webrtc_signaling import WebRTCSignalingRouter

# Crear aplicación Flask para el backend de red
app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key

# Socket.IO con soporte multi-origen
socketio = SocketIO(
    app,
    cors_allowed_origins=config.cors_origins,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

room_mgr = RoomManager.get_instance()
sync_engines: Dict[str, AuthoritativeSyncEngine] = {}

def _emit_to(event: str, data: Any, to: Any = None):
    if to:
        emit(event, data, to=to)
    else:
        emit(event, data)

signaling_router = WebRTCSignalingRouter(emit_fn=_emit_to)


# ==============================================================================
# ENDPOINTS REST: SALAS Y ESTADO DE RED
# ==============================================================================

@app.route("/api/v1/network/status", methods=["GET"])
def network_status():
    """Estado y configuración de red del servidor."""
    return jsonify({
        "status": "online",
        "service": "C.C.I. SYSTEM Realtime Backend",
        "version": "2.1.0",
        "stun_server": config.stun_server,
        "active_rooms": len(room_mgr._rooms),
    })


@app.route("/api/v1/network/rooms", methods=["GET"])
def list_rooms():
    """Lista las salas de juego activas disponibles."""
    rooms = [r.to_dict() for r in room_mgr._rooms.values() if r.visibility == "public"]
    return jsonify({"rooms": rooms})


# ==============================================================================
# EVENTOS WEBSOCKET: GESTIÓN DE SALAS
# ==============================================================================

@socketio.on(SocketEvents.ROOM_CREATE)
def on_room_create(data: Dict[str, Any]):
    game_id = data.get("game_id", "davinci")
    user_id = data.get("user_id", "guest")
    username = data.get("username", "Pilot")
    visibility = data.get("visibility", "public")

    room = room_mgr.create_room(
        game_id=game_id,
        host_id=user_id,
        host_name=username,
        socket_id=request.sid,
        visibility=visibility,
    )
    join_room(room.room_id)
    emit(SocketEvents.ROOM_STATE, room.to_dict())


@socketio.on(SocketEvents.ROOM_JOIN)
def on_room_join(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id", "guest")
    username = data.get("username", "Pilot2")

    room = room_mgr.join_room(
        room_id=room_id,
        user_id=user_id,
        username=username,
        socket_id=request.sid,
    )
    if not room:
        emit(SocketEvents.ROOM_ERROR, {"message": "No fue posible unirse a la sala"})
        return

    join_room(room_id)
    emit(SocketEvents.ROOM_STATE, room.to_dict(), to=room_id)


@socketio.on(SocketEvents.ROOM_READY)
def on_room_ready(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id", "")
    ready = bool(data.get("ready", True))

    room = room_mgr.set_ready(room_id, user_id, ready)
    if room:
        emit(SocketEvents.ROOM_STATE, room.to_dict(), to=room_id)


@socketio.on(SocketEvents.ROOM_LEAVE)
def on_room_leave(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id", "")

    room = room_mgr.leave_room(room_id, user_id)
    leave_room(room_id)
    if room:
        emit(SocketEvents.ROOM_STATE, room.to_dict(), to=room_id)


# ==============================================================================
# EVENTOS WEBSOCKET: SEÑALIZACIÓN WEBRTC (VOZ)
# ==============================================================================

@socketio.on(SocketEvents.WEBRTC_OFFER)
def on_webrtc_offer(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


@socketio.on(SocketEvents.WEBRTC_ANSWER)
def on_webrtc_answer(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


@socketio.on(SocketEvents.WEBRTC_ICE_CANDIDATE)
def on_webrtc_ice(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


def create_app():
    return app
