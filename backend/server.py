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
from backend.chat_service import ChatService
from backend.voice_service import VoiceService
from backend.room_manager import RoomManager
from backend.sync_engine import AuthoritativeSyncEngine
from backend.webrtc_signaling import WebRTCSignalingRouter
from recorder.video_recorder import GameplayVideoRecorder
from recorder.gallery_service import GalleryService

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
chat_svc = ChatService.get_instance()
voice_svc = VoiceService.get_instance()
video_recorder = GameplayVideoRecorder.get_instance()
gallery_svc = GalleryService.get_instance()
sync_engines: Dict[str, AuthoritativeSyncEngine] = {}

def _emit_to(event: str, data: Any, to: Any = None):
    if to:
        socketio.emit(event, data, to=to)
    else:
        socketio.emit(event, data)

chat_svc.set_broadcast_fn(_emit_to)
voice_svc.set_broadcast_fn(_emit_to)
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
# ENDPOINTS REST: CHAT Y MODERACIÓN (FASE 3)
# ==============================================================================

@app.route("/api/v1/chat/send", methods=["POST"])
def send_chat_message():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    sender_id = data.get("sender_id")
    sender_name = data.get("sender_name", sender_id)
    body = data.get("body")
    if not group_id or not sender_id or not body:
        return jsonify({"success": False, "error": "group_id, sender_id y body requeridos"}), 400

    res = chat_svc.send_message(group_id, sender_id, sender_name, body)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/chat/<group_id>/history", methods=["GET"])
def get_chat_history(group_id):
    limit = int(request.args.get("limit", 30))
    before = request.args.get("before")
    history = chat_svc.get_history(group_id, limit=limit, before_created_at=before)
    return jsonify({"success": True, "data": history})


@app.route("/api/v1/chat/message/<message_id>", methods=["DELETE"])
def delete_chat_message(message_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    if not actor_id:
        return jsonify({"success": False, "error": "actor_id requerido"}), 400
    res = chat_svc.delete_message(message_id, actor_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/chat/message/<message_id>/report", methods=["POST"])
def report_chat_message(message_id):
    data = request.get_json() or {}
    reporter_id = data.get("reporter_id")
    reason = data.get("reason", "Contenido inapropiado")
    if not reporter_id:
        return jsonify({"success": False, "error": "reporter_id requerido"}), 400
    res = chat_svc.report_message(message_id, reporter_id, reason)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


# ==============================================================================
# ENDPOINTS REST: MULTIJUGADOR ONLINE Y PARTIDAS (FASE 4)
# ==============================================================================

@app.route("/api/v1/multiplayer/rooms/create", methods=["POST"])
def create_multiplayer_room():
    data = request.get_json() or {}
    game_id = data.get("game_id", "davinci")
    host_id = data.get("host_id")
    username = data.get("username", host_id)
    visibility = data.get("visibility", "public")
    if not host_id:
        return jsonify({"success": False, "error": "host_id requerido"}), 400

    room = room_mgr.create_room(
        game_id=game_id,
        host_id=host_id,
        host_name=username,
        visibility=visibility
    )
    return jsonify({"success": True, "room": room.to_dict()})


@app.route("/api/v1/multiplayer/rooms/join", methods=["POST"])
def join_multiplayer_room():
    data = request.get_json() or {}
    room_id = data.get("room_id", "")
    invite_code = data.get("invite_code")
    user_id = data.get("user_id")
    username = data.get("username", user_id)
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400

    room = room_mgr.join_room(
        room_id=room_id,
        user_id=user_id,
        username=username,
        invite_code=invite_code
    )
    if not room:
        return jsonify({"success": False, "error": "No fue posible unirse a la sala o código inválido"}), 400

    return jsonify({"success": True, "room": room.to_dict()})


@app.route("/api/v1/multiplayer/rooms/<room_id>", methods=["GET"])
def get_multiplayer_room(room_id):
    room = room_mgr.get_room(room_id)
    if not room:
        # Fallback a SQLite
        db_room = cci_database.get_game_room(room_id)
        if not db_room:
            return jsonify({"success": False, "error": "Sala no encontrada"}), 404
        return jsonify({"success": True, "room": db_room})
    return jsonify({"success": True, "room": room.to_dict()})


@app.route("/api/v1/multiplayer/matches/history", methods=["GET"])
def get_matches_history():
    game_id = request.args.get("game_id")
    limit = int(request.args.get("limit", 20))
    matches = cci_database.get_match_history_entries(game_id=game_id, limit=limit)
    return jsonify({"success": True, "matches": matches})


# ==============================================================================
# ENDPOINTS REST: LLAMADAS DE VOZ WEBRTC (FASE 5)
# ==============================================================================

@app.route("/api/v1/voice/calls/start", methods=["POST"])
def start_voice_call():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    user_id = data.get("user_id")
    username = data.get("username", user_id)
    if not group_id or not user_id:
        return jsonify({"success": False, "error": "group_id y user_id requeridos"}), 400

    res = voice_svc.start_call(group_id, user_id, username)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/join", methods=["POST"])
def join_voice_call(session_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    username = data.get("username", user_id)
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400

    res = voice_svc.join_call(session_id, user_id, username)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/leave", methods=["POST"])
def leave_voice_call(session_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400

    res = voice_svc.leave_call(session_id, user_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/mute", methods=["POST"])
def mute_voice_call(session_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    muted = bool(data.get("muted", True))
    if not user_id:
        return jsonify({"success": False, "error": "user_id requerido"}), 400

    res = voice_svc.toggle_mute(session_id, user_id, muted)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/end", methods=["POST"])
def end_voice_call(session_id):
    data = request.get_json() or {}
    actor_id = data.get("actor_id")
    if not actor_id:
        return jsonify({"success": False, "error": "actor_id requerido"}), 400

    res = voice_svc.end_call(session_id, actor_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/active/<group_id>", methods=["GET"])
def get_active_call_for_group_endpoint(group_id):
    call = voice_svc.get_active_call_for_group(group_id)
    if not call:
        # Fallback a SQLite
        db_call = cci_database.get_active_call_for_group(group_id)
        if not db_call:
            return jsonify({"success": True, "active": False, "call": None})
        return jsonify({"success": True, "active": True, "call": db_call})
    return jsonify({"success": True, "active": True, "call": call.to_dict()})


@app.route("/api/v1/voice/ice-servers", methods=["GET"])
def get_ice_servers_endpoint():
    servers = voice_svc.get_ice_servers()
    return jsonify({"success": True, "ice_servers": servers})


# ==============================================================================
# ENDPOINTS REST: GRABACIONES DE GAMEPLAY Y GALERÍA (FASE 6)
# ==============================================================================

@app.route("/api/v1/recordings/start", methods=["POST"])
def start_gameplay_recording():
    data = request.get_json() or {}
    game_id = data.get("game_id", "general")
    owner_id = data.get("owner_id", "pilot")
    res = video_recorder.start_recording(game_id=game_id, owner_id=owner_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/stop", methods=["POST"])
def stop_gameplay_recording():
    res = video_recorder.stop_recording()
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/status", methods=["GET"])
def get_recording_status():
    return jsonify({"success": True, "status": video_recorder.get_status()})


@app.route("/api/v1/recordings/<owner_id>", methods=["GET"])
def get_user_recordings_gallery(owner_id):
    game_id = request.args.get("game_id")
    clips = gallery_svc.get_gallery_clips(owner_id, game_id=game_id)
    return jsonify({"success": True, "owner_id": owner_id, "clips": clips})


@app.route("/api/v1/recordings/<recording_id>", methods=["DELETE"])
def delete_gameplay_recording(recording_id):
    res = gallery_svc.delete_clip(recording_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/<recording_id>/visibility", methods=["PATCH"])
def patch_recording_visibility(recording_id):
    data = request.get_json() or {}
    visibility = data.get("visibility", "private")
    res = gallery_svc.update_visibility(recording_id, visibility)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/storage/stats", methods=["GET"])
def get_recordings_storage_stats():
    stats = gallery_svc.get_storage_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/v1/recordings/<recording_id>/play", methods=["POST"])
def play_recording_in_system(recording_id):
    res = gallery_svc.open_in_system_player(recording_id)
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
# EVENTOS WEBSOCKET: CHAT EN TIEMPO REAL (FASE 3)
# ==============================================================================

@socketio.on("chat:join")
def on_chat_join(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    if group_id:
        join_room(group_id)
        emit("chat:joined", {"group_id": group_id, "user_id": data.get("user_id")}, to=group_id)


@socketio.on("chat:leave")
def on_chat_leave(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    if group_id:
        leave_room(group_id)


@socketio.on(SocketEvents.CHAT_SEND)
def on_chat_send(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    sender_id = data.get("sender_id", "")
    sender_name = data.get("sender_name", sender_id)
    body = data.get("body", "")

    res = chat_svc.send_message(group_id, sender_id, sender_name, body)
    if not res.get("success"):
        emit("chat:error", res)


@socketio.on("chat:typing")
def on_chat_typing(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    user_id = data.get("user_id", "")
    if group_id and user_id:
        emit("chat:typing", {"user_id": user_id, "typing": data.get("typing", True)}, to=group_id, include_self=False)



# ==============================================================================
# EVENTOS WEBSOCKET: MULTIJUGADOR ONLINE (FASE 4)
# ==============================================================================

@socketio.on("game:start")
def on_game_start(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    room = room_mgr.get_room(room_id)
    if not room or not room.both_ready:
        emit("game:error", {"message": "Ambos jugadores deben estar listos para iniciar"})
        return

    room.status = RoomStatus.PLAYING
    sync_engine = AuthoritativeSyncEngine(room_id)
    sync_engines[room_id] = sync_engine

    initial_snap = sync_engine.get_snapshot().to_dict()
    emit("game:start", {"room_id": room_id, "snapshot": initial_snap}, to=room_id)


@socketio.on(SocketEvents.GAME_INPUT)
def on_game_input(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    engine = sync_engines.get(room_id)
    if not engine:
        return

    from backend.contracts import PlayerInputPacket
    packet = PlayerInputPacket(
        room_id=room_id,
        player_id=int(data.get("player_id", 1)),
        tick=int(data.get("tick", 0)),
        seq=int(data.get("seq", 0)),
        dpad=data.get("dpad", "idle"),
        buttons=data.get("buttons", []),
        timestamp_ms=float(data.get("timestamp_ms", 0.0)),
    )
    engine.push_input(packet)
    snapshot = engine.step(1.0 / 60.0)

    # Si la partida terminó, persistir en matches
    if snapshot.status == "match_over":
        winner = engine.get_winner_slot()
        import secrets, datetime
        match_id = f"mat_{secrets.token_hex(4)}"
        now_iso = datetime.datetime.now().isoformat(timespec="seconds")
        cci_database.record_match_result_entry(
            match_id=match_id,
            room_id=room_id,
            game_id="davinci",
            started_at=now_iso,
            ended_at=now_iso,
            result_metadata={
                "winner_slot": winner,
                "p1_wins": engine.p1_wins,
                "p2_wins": engine.p2_wins,
                "final_round": engine.current_round,
            }
        )

    emit(SocketEvents.GAME_SNAPSHOT, snapshot.to_dict(), to=room_id)


@socketio.on(SocketEvents.GAME_PAUSE)
def on_game_pause(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    room = room_mgr.get_room(room_id)
    if room:
        room.status = RoomStatus.PAUSED
        emit(SocketEvents.GAME_PAUSE, {"room_id": room_id, "paused_by": data.get("user_id")}, to=room_id)


@socketio.on(SocketEvents.GAME_RESUME)
def on_game_resume(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    room = room_mgr.get_room(room_id)
    engine = sync_engines.get(room_id)
    if room and engine:
        room.status = RoomStatus.PLAYING
        full_sync = engine.get_full_world_sync()
        emit(SocketEvents.GAME_RESUME, {"room_id": room_id, "snapshot": full_sync}, to=room_id)


# ==============================================================================
# EVENTOS WEBSOCKET: CONTROL DE LLAMADAS DE VOZ (FASE 5)
# ==============================================================================

@socketio.on("call:start")
def on_call_start(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    user_id = data.get("user_id", "")
    username = data.get("username", user_id)
    if group_id and user_id:
        res = voice_svc.start_call(group_id, user_id, username, socket_id=request.sid)
        if res.get("success"):
            join_room(res["call"]["session_id"])
            emit("call:started", res["call"], to=group_id)


@socketio.on("call:join")
def on_call_join(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id", "")
    username = data.get("username", user_id)
    if session_id and user_id:
        res = voice_svc.join_call(session_id, user_id, username, socket_id=request.sid)
        if res.get("success"):
            join_room(session_id)
            emit("call:joined", res["call"], to=session_id)


@socketio.on("call:leave")
def on_call_leave(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id", "")
    if session_id and user_id:
        leave_room(session_id)
        voice_svc.leave_call(session_id, user_id)


@socketio.on("call:mute")
def on_call_mute(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id", "")
    muted = bool(data.get("muted", True))
    if session_id and user_id:
        voice_svc.toggle_mute(session_id, user_id, muted)


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
