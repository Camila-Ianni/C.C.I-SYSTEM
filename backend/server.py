"""
backend/server.py - Servidor principal de tiempo real y backend API para C.C.I. SYSTEM.
Combina Flask + Flask-SocketIO con soporte de WebSockets bidireccionales y fallback polling.
"""
from __future__ import annotations

import os
from typing import Any, Dict
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import cci_database
from backend.config import config
from backend.contracts import SocketEvents
from backend.friends_service import FriendsService
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
friends_svc = FriendsService.get_instance()
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
# ENDPOINTS REST: AMIGOS, PRESENCIA Y GRUPOS (FASE 2)
# ==============================================================================

@app.route("/api/v1/friends/request", methods=["POST"])
def send_friend_request():
    data = request.get_json() or {}
    requester = data.get("requester_id")
    addressee = data.get("addressee_id")
    if not requester or not addressee:
        return jsonify({"success": False, "error": "Faltan requester_id o addressee_id"}), 400
    res = friends_svc.send_friend_request(requester, addressee)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/friends/respond", methods=["POST"])
def respond_friend_request():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    requester_id = data.get("requester_id")
    action = data.get("action", "accept")
    if not user_id or not requester_id:
        return jsonify({"success": False, "error": "Faltan user_id o requester_id"}), 400

    if action == "accept":
        res = friends_svc.accept_friend_request(user_id, requester_id)
    else:
        res = friends_svc.reject_friend_request(user_id, requester_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/friends/<user_id>", methods=["GET"])
def get_user_friends(user_id):
    friends = friends_svc.get_friends_list(user_id)
    pending = cci_database.get_pending_friend_requests(user_id)
    return jsonify({
        "user_id": user_id,
        "friends": friends,
        "pending": pending,
    })


@app.route("/api/v1/presence", methods=["POST"])
def update_presence():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    status = data.get("status", "online")
    current_game = data.get("current_game")
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400
    presence = friends_svc.update_presence(user_id, status, current_game)
    return jsonify({"success": True, "presence": presence})


@app.route("/api/v1/groups/create", methods=["POST"])
def create_group():
    data = request.get_json() or {}
    name = data.get("name")
    owner_id = data.get("owner_id")
    avatar = data.get("avatar")
    visibility = data.get("visibility", "private")
    if not name or not owner_id:
        return jsonify({"success": False, "error": "name y owner_id requeridos"}), 400
    res = friends_svc.create_group(name, owner_id, avatar, visibility)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>", methods=["GET"])
def get_group(group_id):
    grp = friends_svc.get_group_info(group_id)
    if not grp:
        return jsonify({"success": False, "error": "Grupo no encontrado"}), 404
    return jsonify({"success": True, "group": grp})


@app.route("/api/v1/groups/<group_id>/invite", methods=["POST"])
def invite_to_group(group_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    target_id = data.get("target_id")
    if not actor_id or not target_id:
        return jsonify({"success": False, "error": "actor_id y target_id requeridos"}), 400
    res = friends_svc.invite_member(group_id, actor_id, target_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/kick", methods=["POST"])
def kick_from_group(group_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    target_id = data.get("target_id")
    if not actor_id or not target_id:
        return jsonify({"success": False, "error": "actor_id y target_id requeridos"}), 400
    res = friends_svc.kick_member(group_id, actor_id, target_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/leave", methods=["POST"])
def leave_group(group_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400
    res = friends_svc.leave_group(group_id, user_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/transfer", methods=["POST"])
def transfer_group(group_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    new_owner_id = data.get("new_owner_id")
    if not actor_id or not new_owner_id:
        return jsonify({"success": False, "error": "actor_id y new_owner_id requeridos"}), 400
    res = friends_svc.transfer_ownership(group_id, actor_id, new_owner_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/role", methods=["POST"])
def update_group_role(group_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    target_id = data.get("target_id")
    role = data.get("role")
    if not actor_id or not target_id or not role:
        return jsonify({"success": False, "error": "actor_id, target_id y role requeridos"}), 400
    res = friends_svc.update_role(group_id, actor_id, target_id, role)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code



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
