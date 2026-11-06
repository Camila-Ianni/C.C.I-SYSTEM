"""
backend/server.py - Servidor principal de tiempo real y backend API para C.C.I. SYSTEM.
Combina Flask + Flask-SocketIO con soporte de WebSockets bidireccionales y fallback polling.
"""
from __future__ import annotations

import os
from typing import Any, Dict
from flask import Flask, jsonify, request, g
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
from backend.auth import (
    create_access_token,
    verify_access_token,
    require_auth,
    require_socket_auth,
    authenticate_socket_connection,
    check_group_membership,
    check_recording_ownership,
    check_room_participation,
    check_call_participation,
    unregister_socket,
    authenticate_user_credentials,
)

# Crear aplicación Flask para el backend de red
app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key

# Socket.IO con soporte multi-origen y autorización centralizada
socketio = SocketIO(
    app,
    cors_allowed_origins=config.cors_origins,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

@socketio.on("connect")
def on_socket_connect(auth=None):
    """Valida el token de autenticación en el handshake de WebSocket. Rechaza estrictamente si falta o es inválido."""
    payload = authenticate_socket_connection(auth)
    if not payload:
        # En Flask-SocketIO, retornar False rechaza el handshake inmediatamente
        return False
    return True


@socketio.on("disconnect")
def on_socket_disconnect():
    """Limpia el registro autoritativo de socket al desconectarse."""
    if hasattr(request, "sid"):
        unregister_socket(request.sid)

room_mgr = RoomManager.get_instance()
friends_svc = FriendsService.get_instance()
chat_svc = ChatService.get_instance()
voice_svc = VoiceService.get_instance()
video_recorder = GameplayVideoRecorder.get_instance()
gallery_svc = GalleryService.get_instance()
sync_engines: Dict[str, AuthoritativeSyncEngine] = {}

import threading
import time

_ticker_lock = threading.Lock()

class RoomSimulationTicker:
    """Bucle autoritativo independiente de simulación a 60 Hz por sala."""
    def __init__(self, room_id: str, engine: AuthoritativeSyncEngine, emit_fn):
        self.room_id = room_id
        self.engine = engine
        self.emit_fn = emit_fn
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"RoomTicker-{self.room_id}")
        self._thread.start()

    def stop(self, timeout: float = 1.0):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    def _run(self):
        dt = 1.0 / 60.0
        next_tick = time.monotonic()
        while self.running:
            now = time.monotonic()
            if now >= next_tick:
                snapshot = self.engine.step(dt)
                self.emit_fn(SocketEvents.GAME_SNAPSHOT, snapshot.to_dict(), self.room_id)
                if snapshot.status == "match_over":
                    self.running = False
                    winner = self.engine.get_winner_slot()
                    import secrets, datetime
                    match_id = f"mat_{secrets.token_hex(4)}"
                    now_iso = datetime.datetime.now().isoformat(timespec="seconds")
                    try:
                        cci_database.record_match_result_entry(
                            match_id=match_id,
                            room_id=self.room_id,
                            game_id="davinci",
                            started_at=now_iso,
                            ended_at=now_iso,
                            result_metadata={
                                "winner_slot": winner,
                                "p1_wins": self.engine.p1_wins,
                                "p2_wins": self.engine.p2_wins,
                                "final_round": self.engine.current_round,
                            }
                        )
                    except Exception:
                        pass
                    break
                next_tick += dt
            else:
                sleep_sec = max(0.001, min(0.01, next_tick - now))
                time.sleep(sleep_sec)

room_tickers: Dict[str, RoomSimulationTicker] = {}

def _start_room_ticker(room_id: str, engine: AuthoritativeSyncEngine):
    """Garantiza la existencia de exactamente un ticker activo por sala."""
    with _ticker_lock:
        existing = room_tickers.pop(room_id, None)
        if existing:
            existing.stop(timeout=1.0)
        ticker = RoomSimulationTicker(room_id, engine, _emit_to)
        room_tickers[room_id] = ticker
        ticker.start()

def _stop_room_ticker(room_id: str):
    """Detiene y remueve el ticker de la sala de forma coordinada."""
    with _ticker_lock:
        existing = room_tickers.pop(room_id, None)
        if existing:
            existing.stop(timeout=1.0)

def _emit_to(event: str, data: Any, to: Any = None):
    if to:
        socketio.emit(event, data, to=to)
    else:
        socketio.emit(event, data)

chat_svc.set_broadcast_fn(_emit_to)
voice_svc.set_broadcast_fn(_emit_to)
signaling_router = WebRTCSignalingRouter(emit_fn=_emit_to)


# ==============================================================================
# ENDPOINT DE AUTENTICACIÓN CENTRALIZADA Y REGISTRO (P0)
# ==============================================================================

@app.route("/api/v1/auth/register", methods=["POST"])
def register_account():
    """[PÚBLICO] Registra una nueva cuenta de usuario en el sistema."""
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip()
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()

    if not email or not username or not password:
        return jsonify({"success": False, "error": "email, username y password son requeridos."}), 400

    try:
        acc = cci_database.create_account(email, username, password)
        return jsonify({"success": True, "account": acc}), 201
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/v1/auth/token", methods=["POST"])
def issue_auth_token():
    """
    [PÚBLICO] Emite un token de sesión firmado para clientes autenticados.
    Valida credenciales reales (usuario/email y contraseña o token de cuenta registrado).
    Rechaza solicitudes sin credenciales o con credenciales erróneas (401 Unauthorized).
    """
    body = request.get_json(silent=True) or {}
    identifier = str(body.get("identifier") or body.get("email") or body.get("user_id") or body.get("username") or "").strip()
    password = str(body.get("password", "")).strip()
    account_token = str(body.get("account_token", "")).strip()

    account = None
    if account_token:
        account = cci_database.get_account_by_token(account_token)
    elif identifier and password:
        account = authenticate_user_credentials(identifier, password)

    if not account:
        return jsonify({
            "success": False,
            "error": "Credenciales inválidas o cuenta inexistente. Se requiere usuario/email y contraseña válidos.",
            "code": "UNAUTHORIZED"
        }), 401

    user_id = str(account.get("id", identifier))
    username = str(account.get("username", identifier))

    token = create_access_token(user_id=user_id, username=username)
    return jsonify({
        "success": True,
        "token": token,
        "user_id": user_id,
        "username": username,
        "expires_in": 86400,
    })


# ==============================================================================
# ENDPOINTS REST: SALAS Y ESTADO DE RED
# ==============================================================================

@app.route("/api/v1/network/status", methods=["GET"])
def network_status():
    """[PÚBLICO] Estado y configuración de red del servidor."""
    return jsonify({
        "status": "online",
        "service": "C.C.I. SYSTEM Realtime Backend",
        "version": "2.1.0",
        "stun_server": config.stun_server,
        "active_rooms": len(room_mgr._rooms),
    })


@app.route("/api/v1/network/rooms", methods=["GET"])
def list_rooms():
    """[PÚBLICO] Lista las salas de juego públicas activas disponibles."""
    rooms = [r.to_dict() for r in room_mgr._rooms.values() if r.visibility == "public"]
    return jsonify({"rooms": rooms})


# ==============================================================================
# ENDPOINTS REST: AMIGOS, PRESENCIA Y GRUPOS (FASE 2)
# ==============================================================================

@app.route("/api/v1/friends/request", methods=["POST"])
@require_auth
def send_friend_request():
    data = request.get_json() or {}
    requester = g.current_user["user_id"]
    addressee = data.get("addressee_id")
    if not addressee:
        return jsonify({"success": False, "error": "addressee_id es requerido."}), 400
    res = friends_svc.send_friend_request(requester, addressee)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/friends/respond", methods=["POST"])
@require_auth
def respond_friend_request():
    data = request.get_json() or {}
    user_id = g.current_user["user_id"]
    requester_id = data.get("requester_id")
    action = data.get("action", "accept")
    if not requester_id:
        return jsonify({"success": False, "error": "requester_id es requerido."}), 400

    if action == "accept":
        res = friends_svc.accept_friend_request(user_id, requester_id)
    else:
        res = friends_svc.reject_friend_request(user_id, requester_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/friends/<user_id>", methods=["GET"])
@require_auth
def get_user_friends(user_id):
    current = g.current_user["user_id"]
    if user_id != current:
        friends = friends_svc.get_friends_list(current)
        if not any(f.get("friend_id") == user_id for f in friends):
            return jsonify({"success": False, "error": "No tienes permiso para consultar amigos de este usuario."}), 403

    friends = friends_svc.get_friends_list(user_id)
    pending = cci_database.get_pending_friend_requests(user_id)
    return jsonify({
        "user_id": user_id,
        "friends": friends,
        "pending": pending,
    })


@app.route("/api/v1/presence", methods=["POST"])
@require_auth
def update_presence():
    data = request.get_json() or {}
    user_id = g.current_user["user_id"]
    status = data.get("status", "online")
    current_game = data.get("current_game")
    presence = friends_svc.update_presence(user_id, status, current_game)
    return jsonify({"success": True, "presence": presence})


@app.route("/api/v1/groups/create", methods=["POST"])
@require_auth
def create_group():
    data = request.get_json() or {}
    name = data.get("name")
    owner_id = g.current_user["user_id"]
    avatar = data.get("avatar")
    visibility = data.get("visibility", "private")
    if not name:
        return jsonify({"success": False, "error": "name es requerido."}), 400
    res = friends_svc.create_group(name, owner_id, avatar, visibility)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>", methods=["GET"])
@require_auth
def get_group(group_id):
    if not check_group_membership(g.current_user["user_id"], group_id):
        grp_db = cci_database.get_group_detail(group_id)
        if not grp_db or grp_db.get("visibility") != "public":
            return jsonify({"success": False, "error": "Acceso denegado: no perteneces a este grupo privado."}), 403

    grp = friends_svc.get_group_info(group_id)
    if not grp:
        return jsonify({"success": False, "error": "Grupo no encontrado"}), 404
    return jsonify({"success": True, "group": grp})


@app.route("/api/v1/groups/<group_id>/invite", methods=["POST"])
@require_auth
def invite_to_group(group_id):
    data = request.get_json() or {}
    actor_id = g.current_user["user_id"]
    target_id = data.get("target_id")
    if not target_id:
        return jsonify({"success": False, "error": "target_id es requerido."}), 400
    res = friends_svc.invite_member(group_id, actor_id, target_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/kick", methods=["POST"])
@require_auth
def kick_from_group(group_id):
    data = request.get_json() or {}
    actor_id = g.current_user["user_id"]
    target_id = data.get("target_id")
    if not target_id:
        return jsonify({"success": False, "error": "target_id es requerido."}), 400
    res = friends_svc.kick_member(group_id, actor_id, target_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/leave", methods=["POST"])
@require_auth
def leave_group(group_id):
    user_id = g.current_user["user_id"]
    res = friends_svc.leave_group(group_id, user_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/transfer", methods=["POST"])
@require_auth
def transfer_group(group_id):
    data = request.get_json() or {}
    actor_id = g.current_user["user_id"]
    new_owner_id = data.get("new_owner_id")
    if not new_owner_id:
        return jsonify({"success": False, "error": "new_owner_id es requerido."}), 400
    res = friends_svc.transfer_ownership(group_id, actor_id, new_owner_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/groups/<group_id>/role", methods=["POST"])
@require_auth
def update_group_role(group_id):
    data = request.get_json() or {}
    actor_id = g.current_user["user_id"]
    target_id = data.get("target_id")
    role = data.get("role")
    if not target_id or not role:
        return jsonify({"success": False, "error": "target_id y role son requeridos."}), 400
    res = friends_svc.update_role(group_id, actor_id, target_id, role)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


# ==============================================================================
# ENDPOINTS REST: CHAT Y MODERACIÓN (FASE 3)
# ==============================================================================

@app.route("/api/v1/chat/send", methods=["POST"])
@require_auth
def send_chat_message():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    sender_id = g.current_user["user_id"]
    sender_name = g.current_user.get("username", sender_id)
    body = data.get("body")
    if not group_id or not body:
        return jsonify({"success": False, "error": "group_id y body requeridos"}), 400

    if not check_group_membership(sender_id, group_id):
        return jsonify({"success": False, "error": "Acceso denegado: no eres miembro de este grupo."}), 403

    res = chat_svc.send_message(group_id, sender_id, sender_name, body)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/chat/<group_id>/history", methods=["GET"])
@require_auth
def get_chat_history(group_id):
    if not check_group_membership(g.current_user["user_id"], group_id):
        return jsonify({"success": False, "error": "Acceso denegado: no eres miembro de este grupo."}), 403

    limit = int(request.args.get("limit", 30))
    before = request.args.get("before")
    history = chat_svc.get_history(group_id, limit=limit, before_created_at=before)
    return jsonify({"success": True, "data": history})


@app.route("/api/v1/chat/message/<message_id>", methods=["DELETE"])
@require_auth
def delete_chat_message(message_id):
    actor_id = g.current_user["user_id"]
    res = chat_svc.delete_message(message_id, actor_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/chat/message/<message_id>/report", methods=["POST"])
@require_auth
def report_chat_message(message_id):
    data = request.get_json() or {}
    reporter_id = g.current_user["user_id"]
    reason = data.get("reason", "Contenido inapropiado")
    res = chat_svc.report_message(message_id, reporter_id, reason)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


# ==============================================================================
# ENDPOINTS REST: MULTIJUGADOR ONLINE Y PARTIDAS (FASE 4)
# ==============================================================================

@app.route("/api/v1/multiplayer/rooms/create", methods=["POST"])
@require_auth
def create_multiplayer_room():
    data = request.get_json() or {}
    game_id = data.get("game_id", "davinci")
    host_id = g.current_user["user_id"]
    username = g.current_user.get("username", host_id)
    visibility = data.get("visibility", "public")

    room = room_mgr.create_room(
        game_id=game_id,
        host_id=host_id,
        host_name=username,
        visibility=visibility
    )
    return jsonify({"success": True, "room": room.to_dict()})


@app.route("/api/v1/multiplayer/rooms/join", methods=["POST"])
@require_auth
def join_multiplayer_room():
    data = request.get_json() or {}
    room_id = data.get("room_id", "")
    invite_code = data.get("invite_code")
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)

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
@require_auth
def get_multiplayer_room(room_id):
    room = room_mgr.get_room(room_id)
    if not room:
        db_room = cci_database.get_game_room(room_id)
        if not db_room:
            return jsonify({"success": False, "error": "Sala no encontrada"}), 404
        return jsonify({"success": True, "room": db_room})
    return jsonify({"success": True, "room": room.to_dict()})


@app.route("/api/v1/multiplayer/matches/history", methods=["GET"])
@require_auth
def get_matches_history():
    game_id = request.args.get("game_id")
    limit = int(request.args.get("limit", 20))
    matches = cci_database.get_match_history_entries(game_id=game_id, limit=limit)
    return jsonify({"success": True, "matches": matches})


# ==============================================================================
# ENDPOINTS REST: LLAMADAS DE VOZ WEBRTC (FASE 5)
# ==============================================================================

@app.route("/api/v1/voice/calls/start", methods=["POST"])
@require_auth
def start_voice_call():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
    if not group_id:
        return jsonify({"success": False, "error": "group_id requerido"}), 400

    if not check_group_membership(user_id, group_id):
        return jsonify({"success": False, "error": "Acceso denegado: no perteneces a este grupo."}), 403

    res = voice_svc.start_call(group_id, user_id, username)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/join", methods=["POST"])
@require_auth
def join_voice_call(session_id):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)

    res = voice_svc.join_call(session_id, user_id, username)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/leave", methods=["POST"])
@require_auth
def leave_voice_call(session_id):
    user_id = g.current_user["user_id"]
    res = voice_svc.leave_call(session_id, user_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/mute", methods=["POST"])
@require_auth
def mute_voice_call(session_id):
    data = request.get_json() or {}
    user_id = g.current_user["user_id"]
    muted = bool(data.get("muted", True))

    res = voice_svc.toggle_mute(session_id, user_id, muted)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/<session_id>/end", methods=["POST"])
@require_auth
def end_voice_call(session_id):
    actor_id = g.current_user["user_id"]
    res = voice_svc.end_call(session_id, actor_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/voice/calls/active/<group_id>", methods=["GET"])
@require_auth
def get_active_call_for_group_endpoint(group_id):
    if not check_group_membership(g.current_user["user_id"], group_id):
        return jsonify({"success": False, "error": "Acceso denegado: no perteneces a este grupo."}), 403

    call = voice_svc.get_active_call_for_group(group_id)
    if not call:
        db_call = cci_database.get_active_call_for_group(group_id)
        if not db_call:
            return jsonify({"success": True, "active": False, "call": None})
        return jsonify({"success": True, "active": True, "call": db_call})
    return jsonify({"success": True, "active": True, "call": call.to_dict()})


@app.route("/api/v1/voice/ice-servers", methods=["GET"])
def get_ice_servers_endpoint():
    """[PÚBLICO] Obtiene configuración de servidores STUN/TURN."""
    servers = voice_svc.get_ice_servers()
    return jsonify({"success": True, "ice_servers": servers})


# ==============================================================================
# ENDPOINTS REST: GRABACIONES DE GAMEPLAY Y GALERÍA (FASE 6)
# ==============================================================================

@app.route("/api/v1/recordings/start", methods=["POST"])
@require_auth
def start_gameplay_recording():
    data = request.get_json() or {}
    game_id = data.get("game_id", "general")
    owner_id = g.current_user["user_id"]
    res = video_recorder.start_recording(game_id=game_id, owner_id=owner_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/stop", methods=["POST"])
@require_auth
def stop_gameplay_recording():
    res = video_recorder.stop_recording()
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/status", methods=["GET"])
@require_auth
def get_recording_status():
    return jsonify({"success": True, "status": video_recorder.get_status()})


@app.route("/api/v1/recordings/<owner_id>", methods=["GET"])
@require_auth
def get_user_recordings_gallery(owner_id):
    if owner_id != g.current_user["user_id"]:
        return jsonify({"success": False, "error": "No tienes permiso para ver grabaciones privadas de otro usuario."}), 403

    game_id = request.args.get("game_id")
    clips = gallery_svc.get_gallery_clips(owner_id, game_id=game_id)
    return jsonify({"success": True, "owner_id": owner_id, "clips": clips})


@app.route("/api/v1/recordings/<recording_id>", methods=["DELETE"])
@require_auth
def delete_gameplay_recording(recording_id):
    if not check_recording_ownership(g.current_user["user_id"], recording_id):
        return jsonify({"success": False, "error": "No tienes permiso para eliminar esta grabación ajena."}), 403

    res = gallery_svc.delete_clip(recording_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/<recording_id>/visibility", methods=["PATCH"])
@require_auth
def patch_recording_visibility(recording_id):
    if not check_recording_ownership(g.current_user["user_id"], recording_id):
        return jsonify({"success": False, "error": "No tienes permiso para modificar esta grabación ajena."}), 403

    data = request.get_json() or {}
    visibility = data.get("visibility", "private")
    res = gallery_svc.update_visibility(recording_id, visibility)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/v1/recordings/storage/stats", methods=["GET"])
def get_recordings_storage_stats():
    """[PÚBLICO] Estadísticas globales de cuota de almacenamiento."""
    stats = gallery_svc.get_storage_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/v1/recordings/<recording_id>/play", methods=["POST"])
@require_auth
def play_recording_in_system(recording_id):
    if not check_recording_ownership(g.current_user["user_id"], recording_id):
        return jsonify({"success": False, "error": "No tienes permiso para reproducir esta grabación ajena."}), 403

    res = gallery_svc.open_in_system_player(recording_id)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code







# ==============================================================================
# EVENTOS WEBSOCKET: GESTIÓN DE SALAS (CON AUTORIZACIÓN CENTRALIZADA)
# ==============================================================================

@socketio.on(SocketEvents.ROOM_CREATE)
@require_socket_auth
def on_room_create(data: Dict[str, Any]):
    game_id = data.get("game_id", "davinci")
    user_id = data.get("user_id")
    username = data.get("username") or data.get("sender_name") or "Pilot"
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
@require_socket_auth
def on_room_join(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    username = data.get("username") or data.get("sender_name") or "Pilot2"

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
@require_socket_auth
def on_room_ready(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    ready = bool(data.get("ready", True))

    room = room_mgr.set_ready(room_id, user_id, ready)
    if room:
        emit(SocketEvents.ROOM_STATE, room.to_dict(), to=room_id)


@socketio.on(SocketEvents.ROOM_LEAVE)
@require_socket_auth
def on_room_leave(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")

    room = room_mgr.leave_room(room_id, user_id)
    leave_room(room_id)
    if room:
        emit(SocketEvents.ROOM_STATE, room.to_dict(), to=room_id)


# ==============================================================================
# EVENTOS WEBSOCKET: CHAT EN TIEMPO REAL (CON AUTORIZACIÓN CENTRALIZADA)
# ==============================================================================

@socketio.on("chat:join")
@require_socket_auth
def on_chat_join(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    user_id = data.get("user_id")
    if not group_id or not check_group_membership(user_id, group_id):
        emit("chat:error", {"success": False, "error": "No tienes acceso a este grupo o no eres miembro."})
        return
    join_room(group_id)
    emit("chat:joined", {"group_id": group_id, "user_id": user_id}, to=group_id)


@socketio.on("chat:leave")
@require_socket_auth
def on_chat_leave(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    if group_id:
        leave_room(group_id)


@socketio.on(SocketEvents.CHAT_SEND)
@require_socket_auth
def on_chat_send(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    sender_id = data.get("user_id")
    sender_name = data.get("sender_name", sender_id)
    body = data.get("body", "")

    # Verificación obligatoria de pertenencia al grupo
    if not check_group_membership(sender_id, group_id):
        emit("chat:error", {"success": False, "error": "Acceso denegado: no eres miembro de este grupo."})
        return

    res = chat_svc.send_message(group_id, sender_id, sender_name, body)
    if not res.get("success"):
        emit("chat:error", res)


@socketio.on("chat:typing")
@require_socket_auth
def on_chat_typing(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    user_id = data.get("user_id")
    if group_id and user_id:
        emit("chat:typing", {"user_id": user_id, "typing": data.get("typing", True)}, to=group_id, include_self=False)



# ==============================================================================
# EVENTOS WEBSOCKET: MULTIJUGADOR ONLINE (CON AUTORIZACIÓN CENTRALIZADA)
# ==============================================================================

@socketio.on("game:start")
@require_socket_auth
def on_game_start(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    room = room_mgr.get_room(room_id)
    if not room or not room.both_ready:
        emit("game:error", {"message": "Ambos jugadores deben estar listos para iniciar"})
        return

    # Solo el anfitrión puede ordenar el inicio de la partida
    if room.host_id != user_id:
        emit("game:error", {"message": "Solo el anfitrión de la sala puede iniciar la partida."})
        return

    room.status = RoomStatus.PLAYING
    sync_engine = AuthoritativeSyncEngine(room_id)
    sync_engines[room_id] = sync_engine

    # Iniciar bucle independiente coordinado de simulación a 60 Hz por sala
    _start_room_ticker(room_id, sync_engine)

    initial_snap = sync_engine.get_snapshot().to_dict()
    emit("game:start", {"room_id": room_id, "snapshot": initial_snap}, to=room_id)


@socketio.on(SocketEvents.GAME_INPUT)
@require_socket_auth
def on_game_input(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    engine = sync_engines.get(room_id)
    room = room_mgr.get_room(room_id)
    if not engine or not room:
        return

    # Validar que el usuario sea miembro activo de la sala
    member = room.members.get(user_id)
    if not member:
        emit("game:error", {"message": "Acceso denegado: no perteneces a esta sala."})
        return

    # El slot de jugador (P1 o P2) es asignado por el servidor, nunca por el cliente
    player_id = member.slot.value

    # Validar tick y secuencia (rechazar entradas obsoletas o fuera de orden)
    seq = int(data.get("seq", 0))
    tick = int(data.get("tick", 0))
    last_seq = getattr(engine, f"_last_seq_p{player_id}", 0)
    if seq <= last_seq and last_seq > 0:
        return  # Descartar entrada fuera de orden
    setattr(engine, f"_last_seq_p{player_id}", seq)

    from backend.contracts import PlayerInputPacket
    packet = PlayerInputPacket(
        room_id=room_id,
        player_id=player_id,
        tick=tick,
        seq=seq,
        dpad=data.get("dpad", "idle"),
        buttons=data.get("buttons", []),
        timestamp_ms=float(data.get("timestamp_ms", 0.0)),
    )
    engine.push_input(packet)

    # Si el ticker independiente no está activo (entorno síncrono de tests), avanzar paso
    ticker = room_tickers.get(room_id)
    if not ticker or not ticker.running:
        snapshot = engine.step(1.0 / 60.0)
        if snapshot.status == "match_over":
            winner = engine.get_winner_slot()
            import secrets, datetime
            match_id = f"mat_{secrets.token_hex(4)}"
            now_iso = datetime.datetime.now().isoformat(timespec="seconds")
            try:
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
            except Exception:
                pass
        emit(SocketEvents.GAME_SNAPSHOT, snapshot.to_dict(), to=room_id)


@socketio.on(SocketEvents.GAME_PAUSE)
@require_socket_auth
def on_game_pause(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    room = room_mgr.get_room(room_id)
    if room and user_id in room.members:
        room.status = RoomStatus.PAUSED
        _stop_room_ticker(room_id)
        emit(SocketEvents.GAME_PAUSE, {"room_id": room_id, "paused_by": user_id}, to=room_id)


@socketio.on(SocketEvents.GAME_RESUME)
@require_socket_auth
def on_game_resume(data: Dict[str, Any]):
    room_id = data.get("room_id", "")
    user_id = data.get("user_id")
    room = room_mgr.get_room(room_id)
    engine = sync_engines.get(room_id)
    if room and engine and user_id in room.members:
        room.status = RoomStatus.PLAYING
        _start_room_ticker(room_id, engine)
        full_sync = engine.get_full_world_sync()
        emit(SocketEvents.GAME_RESUME, {"room_id": room_id, "snapshot": full_sync}, to=room_id)


# ==============================================================================
# EVENTOS WEBSOCKET: CONTROL DE LLAMADAS DE VOZ (CON AUTORIZACIÓN CENTRALIZADA)
# ==============================================================================

@socketio.on("call:start")
@require_socket_auth
def on_call_start(data: Dict[str, Any]):
    group_id = data.get("group_id", "")
    user_id = data.get("user_id")
    username = data.get("sender_name") or data.get("username") or user_id

    if not group_id or not check_group_membership(user_id, group_id):
        emit("call:error", {"success": False, "error": "No eres miembro de este grupo para iniciar una llamada."})
        return

    res = voice_svc.start_call(group_id, user_id, username, socket_id=request.sid)
    if res.get("success"):
        join_room(res["call"]["session_id"])
        emit("call:started", res["call"], to=group_id)


@socketio.on("call:join")
@require_socket_auth
def on_call_join(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id")
    username = data.get("sender_name") or data.get("username") or user_id

    call = voice_svc._active_calls.get(session_id)
    if not call or not check_group_membership(user_id, call.group_id):
        emit("call:error", {"success": False, "error": "Acceso denegado a la llamada del grupo."})
        return

    res = voice_svc.join_call(session_id, user_id, username, socket_id=request.sid)
    if res.get("success"):
        join_room(session_id)
        emit("call:joined", res["call"], to=session_id)


@socketio.on("call:leave")
@require_socket_auth
def on_call_leave(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id")
    if session_id and user_id:
        leave_room(session_id)
        voice_svc.leave_call(session_id, user_id)


@socketio.on("call:mute")
@require_socket_auth
def on_call_mute(data: Dict[str, Any]):
    session_id = data.get("session_id", "")
    user_id = data.get("user_id")
    muted = bool(data.get("muted", True))
    if session_id and user_id:
        voice_svc.toggle_mute(session_id, user_id, muted)


# ==============================================================================
# EVENTOS WEBSOCKET: SEÑALIZACIÓN WEBRTC (VOZ - AUTORIZADA)
# ==============================================================================

@socketio.on(SocketEvents.WEBRTC_OFFER)
@require_socket_auth
def on_webrtc_offer(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


@socketio.on(SocketEvents.WEBRTC_ANSWER)
@require_socket_auth
def on_webrtc_answer(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


@socketio.on(SocketEvents.WEBRTC_ICE_CANDIDATE)
@require_socket_auth
def on_webrtc_ice(data: Dict[str, Any]):
    signaling_router.handle_signal(data, request.sid)


def create_app():
    return app
