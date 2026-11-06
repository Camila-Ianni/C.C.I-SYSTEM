"""
backend/communities/routes.py - Rutas REST de la API de Communities para C.C.I. SYSTEM.

Expone endpoints bajo /api/v1/communities e invitaciones protegidos con autenticación JWT Bearer.
"""
from __future__ import annotations

import base64
import time
from flask import Blueprint, g, jsonify, request, Response
from backend.auth import require_auth
from backend.communities.service import CommunitiesService, SoundCooldownError, StreamLimitError
from backend.communities.stream_adapter import StreamValidationError
from backend.communities.metrics import CommunityMetricsCollector

communities_bp = Blueprint("communities", __name__)


@communities_bp.before_request
def record_community_request_start():
    request._start_time = time.time()
    CommunityMetricsCollector.get_instance().increment("communities_api_requests_total")


@communities_bp.after_request
def record_community_request_latency(response):
    if hasattr(request, "_start_time"):
        elapsed = time.time() - request._start_time
        CommunityMetricsCollector.get_instance().record_latency(elapsed)
    return response


def get_service() -> CommunitiesService:
    return CommunitiesService.get_instance()


@communities_bp.route("/communities", methods=["POST"])
@require_auth
def create_community_route():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "El campo 'name' es requerido"}), 400

    desc = data.get("description")
    visibility = data.get("visibility", "private")
    slug = data.get("slug")
    user_id = g.current_user["user_id"]

    try:
        comm = get_service().create_community(
            owner_id=user_id,
            name=name,
            description=desc,
            visibility=visibility,
            slug=slug,
        )
        CommunityMetricsCollector.get_instance().increment("communities_created_total")
        return jsonify({"community": comm}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/communities", methods=["GET"])
@require_auth
def list_communities_route():
    user_id = g.current_user["user_id"]
    discover = request.args.get("visibility") == "public"
    items = get_service().list_communities(user_id, discover_public=discover)
    return jsonify({"communities": items}), 200


@communities_bp.route("/communities/<community_id>", methods=["GET"])
@require_auth
def get_community_route(community_id: str):
    user_id = g.current_user["user_id"]
    comm = get_service().get_community(community_id, user_id)
    if not comm:
        return jsonify({"error": "Comunidad no encontrada o acceso denegado"}), 403
    return jsonify({"community": comm}), 200


@communities_bp.route("/communities/<community_id>", methods=["PATCH"])
@require_auth
def update_community_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    try:
        updated = get_service().update_community(community_id, user_id, data)
        return jsonify({"community": updated}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>", methods=["DELETE"])
@require_auth
def delete_community_route(community_id: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().delete_community(community_id, user_id)
        return jsonify({"status": "deleted"}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/transfer-ownership", methods=["POST"])
@require_auth
def transfer_ownership_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    new_owner_id = data.get("new_owner_id")
    if not new_owner_id:
        return jsonify({"error": "new_owner_id requerido"}), 400

    try:
        get_service().transfer_ownership(community_id, user_id, new_owner_id)
        return jsonify({"status": "transferred", "new_owner_id": new_owner_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except (LookupError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/communities/<community_id>/invitations", methods=["POST"])
@require_auth
def create_invitation_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    max_uses = int(data.get("max_uses", 0))
    expires_in_hours = data.get("expires_in_hours")
    if expires_in_hours is not None:
        expires_in_hours = int(expires_in_hours)

    try:
        inv = get_service().create_invitation(community_id, user_id, max_uses, expires_in_hours)
        return jsonify({"invitation": inv}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/invitations/<code_str>/accept", methods=["POST"])
@require_auth
def accept_invitation_route(code_str: str):
    user_id = g.current_user["user_id"]
    try:
        res = get_service().join_via_invitation(code_str, user_id)
        return jsonify(res), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/invitations/join", methods=["POST"])
@require_auth
def join_invitation_route():
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    code_str = data.get("code", "")
    try:
        res = get_service().join_via_invitation(code_str, user_id)
        return jsonify(res), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/communities/<community_id>/members", methods=["GET"])
@require_auth
def list_members_route(community_id: str):
    user_id = g.current_user["user_id"]
    comm = get_service().get_community(community_id, user_id)
    if not comm:
        return jsonify({"error": "Acceso denegado a la comunidad"}), 403
    members = get_service().repo.list_members(community_id)
    return jsonify({"members": members}), 200


@communities_bp.route("/communities/<community_id>/members/<target_id>/kick", methods=["POST"])
@require_auth
def kick_member_route(community_id: str, target_id: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().kick_member(community_id, user_id, target_id)
        return jsonify({"status": "kicked", "target_id": target_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/leave", methods=["POST"])
@require_auth
def leave_community_route(community_id: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().leave_community(community_id, user_id)
        return jsonify({"status": "left"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/roles", methods=["GET"])
@require_auth
def list_roles_route(community_id: str):
    user_id = g.current_user["user_id"]
    comm = get_service().get_community(community_id, user_id)
    if not comm:
        return jsonify({"error": "Acceso denegado a la comunidad"}), 403
    roles = get_service().repo.list_roles(community_id)
    return jsonify({"roles": roles}), 200


@communities_bp.route("/communities/<community_id>/roles", methods=["POST"])
@require_auth
def create_role_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "El nombre del rol es requerido"}), 400

    color = data.get("color", "#99AAB5")
    position = int(data.get("position", 100))
    is_admin = bool(data.get("is_admin", False))
    permissions = data.get("permissions", [])

    try:
        role = get_service().create_role(
            community_id=community_id,
            requester_id=user_id,
            name=name,
            color=color,
            position=position,
            is_admin=is_admin,
            permissions=permissions,
        )
        return jsonify({"role": role}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@communities_bp.route("/communities/<community_id>/members/<target_id>/roles", methods=["POST"])
@require_auth
def assign_role_route(community_id: str, target_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    role_id = data.get("role_id")
    if not role_id:
        return jsonify({"error": "role_id es requerido"}), 400

    try:
        get_service().assign_role(community_id, user_id, target_id, role_id)
        return jsonify({"status": "role_assigned"}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/channels", methods=["GET"])
@require_auth
def list_channels_route(community_id: str):
    user_id = g.current_user["user_id"]
    comm = get_service().get_community(community_id, user_id)
    if not comm:
        return jsonify({"error": "Acceso denegado a la comunidad"}), 403
    channels = get_service().list_channels(community_id, user_id)
    return jsonify({"channels": channels}), 200


@communities_bp.route("/communities/<community_id>/channels", methods=["POST"])
@require_auth
def create_channel_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "El nombre del canal es requerido"}), 400

    ch_type = data.get("type", "text")
    is_private = bool(data.get("is_private", False))
    topic = data.get("topic")

    try:
        ch = get_service().create_channel(
            community_id=community_id,
            requester_id=user_id,
            name=name,
            channel_type=ch_type,
            topic=topic,
            is_private=is_private,
        )
        return jsonify({"channel": ch}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@communities_bp.route("/communities/<community_id>/channels/<channel_id>", methods=["DELETE"])
@require_auth
def delete_channel_route(community_id: str, channel_id: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().delete_channel(community_id, channel_id, user_id)
        return jsonify({"status": "deleted"}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/channels/<channel_id>/overrides", methods=["POST"])
@require_auth
def set_channel_override_route(community_id: str, channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    permission_id = data.get("permission_id")
    allow = bool(data.get("allow", False))
    deny = bool(data.get("deny", False))

    if not all([target_type, target_id, permission_id]):
        return jsonify({"error": "target_type, target_id y permission_id son requeridos"}), 400

    try:
        get_service().set_channel_override(
            community_id=community_id,
            channel_id=channel_id,
            requester_id=user_id,
            target_type=target_type,
            target_id=target_id,
            permission_id=permission_id,
            allow=allow,
            deny=deny,
        )
        return jsonify({"status": "override_set"}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


# =============================================================================
# RUTAS DE MENSAJERÍA E HISTORIAL
# =============================================================================

@communities_bp.route("/channels/<channel_id>/messages", methods=["GET"])
@require_auth
def get_channel_messages_route(channel_id: str):
    user_id = g.current_user["user_id"]
    limit = int(request.args.get("limit", 50))
    before_id = request.args.get("before_id")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        msgs = get_service().list_channel_messages(
            community_id=ch["community_id"],
            channel_id=channel_id,
            requester_id=user_id,
            limit=limit,
            before_id=before_id,
        )
        return jsonify({"messages": msgs}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/messages", methods=["POST"])
@require_auth
def send_channel_message_route(channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    content = data.get("content", "")
    reply_to_id = data.get("reply_to_id")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        msg = get_service().send_message(
            community_id=ch["community_id"],
            channel_id=channel_id,
            author_id=user_id,
            content=content,
            reply_to_id=reply_to_id,
        )
        CommunityMetricsCollector.get_instance().increment("communities_messages_total")
        return jsonify({"message": msg}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except (ValueError, LookupError) as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/channels/<channel_id>/messages/<message_id>", methods=["PATCH"])
@require_auth
def edit_channel_message_route(channel_id: str, message_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    content = data.get("content", "")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        updated = get_service().edit_message(
            community_id=ch["community_id"],
            channel_id=channel_id,
            message_id=message_id,
            requester_id=user_id,
            new_content=content,
        )
        return jsonify({"message": updated}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except (ValueError, LookupError) as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/channels/<channel_id>/messages/<message_id>", methods=["DELETE"])
@require_auth
def delete_channel_message_route(channel_id: str, message_id: str):
    user_id = g.current_user["user_id"]

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        get_service().delete_message(
            community_id=ch["community_id"],
            channel_id=channel_id,
            message_id=message_id,
            requester_id=user_id,
        )
        return jsonify({"status": "deleted", "message_id": message_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


# =============================================================================
# RUTAS DE PRESENCIA DE USUARIO
# =============================================================================

@communities_bp.route("/users/presence", methods=["GET"])
@require_auth
def get_presence_route():
    viewer_id = g.current_user["user_id"]
    user_ids_arg = request.args.get("user_ids", "")
    if user_ids_arg:
        uids = [u.strip() for u in user_ids_arg.split(",") if u.strip()]
        presences = get_service().list_user_presences(uids, viewer_id=viewer_id)
        return jsonify({"presences": presences}), 200
    else:
        p = get_service().get_user_presence(viewer_id, viewer_id=viewer_id)
        return jsonify({"presence": p}), 200


@communities_bp.route("/users/presence", methods=["POST"])
@require_auth
def set_presence_route():
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    status = data.get("status", "online")
    custom_status = data.get("custom_status")

    try:
        updated = get_service().set_user_presence(
            user_id=user_id,
            status=status,
            custom_status=custom_status,
        )
        return jsonify({"presence": updated}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# RUTAS DE CANALES DE VOZ (LIVEKIT SFU)
# =============================================================================

@communities_bp.route("/channels/<channel_id>/voice-token", methods=["POST"])
@require_auth
def request_voice_token_route(channel_id: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", "User")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        cred = get_service().request_voice_token(
            community_id=ch["community_id"],
            channel_id=channel_id,
            user_id=user_id,
            username=username,
        )
        CommunityMetricsCollector.get_instance().increment("communities_voice_joins_total")
        return jsonify(cred), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/voice-leave", methods=["POST"])
@require_auth
def leave_voice_route(channel_id: str):
    user_id = g.current_user["user_id"]
    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    get_service().leave_voice_channel(ch["community_id"], channel_id, user_id)
    return jsonify({"status": "left", "channel_id": channel_id}), 200


@communities_bp.route("/channels/<channel_id>/voice-participants", methods=["GET"])
@require_auth
def list_voice_participants_route(channel_id: str):
    user_id = g.current_user["user_id"]
    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        participants = get_service().list_voice_participants(ch["community_id"], channel_id, user_id)
        return jsonify({"participants": participants}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/voice-moderate", methods=["POST"])
@require_auth
def moderate_voice_route(channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    action = data.get("action", "mute")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        get_service().moderate_voice_participant(
            community_id=ch["community_id"],
            channel_id=channel_id,
            requester_id=user_id,
            target_user_id=target_user_id,
            action=action,
        )
        return jsonify({"status": "moderated", "action": action, "target_user_id": target_user_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


# =============================================================================
# SOUND DECK (SOUNDBOARD)
# =============================================================================

@communities_bp.route("/sounds/categories", methods=["POST"])
@require_auth
def create_sound_category_route():
    user_id = g.current_user["user_id"]
    is_admin = g.current_user.get("is_admin", False)
    data = request.get_json() or {}

    scope_type = data.get("scope_type", "user")
    name = data.get("name", "").strip()
    scope_id = data.get("scope_id")
    position = int(data.get("position", 0))

    try:
        cat = get_service().create_sound_category(
            actor_id=user_id,
            scope_type=scope_type,
            name=name,
            scope_id=scope_id,
            position=position,
            is_admin=is_admin,
        )
        return jsonify(cat), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/categories", methods=["GET"])
@require_auth
def list_sound_categories_route():
    user_id = g.current_user["user_id"]
    scope_type = request.args.get("scope_type")
    scope_id = request.args.get("scope_id")

    cats = get_service().list_sound_categories(
        actor_id=user_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    return jsonify({"categories": cats}), 200


@communities_bp.route("/sounds", methods=["POST"])
@require_auth
def upload_sound_route():
    user_id = g.current_user["user_id"]
    is_admin = g.current_user.get("is_admin", False)

    file_bytes = None
    title = ""
    owner_type = "user"
    owner_id = None
    category_id = None
    volume_scale = 1.0
    cooldown_seconds = 5
    declared_duration = None

    if request.is_json:
        data = request.get_json() or {}
        title = data.get("title", "")
        owner_type = data.get("owner_type", "user")
        owner_id = data.get("owner_id")
        category_id = data.get("category_id")
        volume_scale = float(data.get("volume_scale", 1.0))
        cooldown_seconds = int(data.get("cooldown_seconds", 5))
        if "duration" in data:
            declared_duration = float(data["duration"])
        b64 = data.get("file_base64", "")
        if b64:
            try:
                file_bytes = base64.b64decode(b64)
            except Exception:
                return jsonify({"error": "Codificación Base64 inválida"}), 400
    else:
        # Multipart form upload
        title = request.form.get("title", "")
        owner_type = request.form.get("owner_type", "user")
        owner_id = request.form.get("owner_id")
        category_id = request.form.get("category_id")
        volume_scale = float(request.form.get("volume_scale", 1.0))
        cooldown_seconds = int(request.form.get("cooldown_seconds", 5))
        if "duration" in request.form:
            declared_duration = float(request.form["duration"])

        if "file" in request.files:
            uploaded_file = request.files["file"]
            file_bytes = uploaded_file.read()

    if not file_bytes:
        return jsonify({"error": "No se proporcionó archivo de audio"}), 400

    if len(file_bytes) > 5 * 1024 * 1024:
        return jsonify({"error": "El archivo excede el tamaño máximo permitido de 5 MB"}), 413

    try:
        sound = get_service().upload_sound(
            actor_id=user_id,
            owner_type=owner_type,
            title=title,
            file_bytes=file_bytes,
            owner_id=owner_id,
            category_id=category_id,
            volume_scale=volume_scale,
            cooldown_seconds=cooldown_seconds,
            declared_duration=declared_duration,
            is_admin=is_admin,
        )
        return jsonify(sound), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        msg = str(e)
        if "5 MB" in msg or "FILE_TOO_LARGE" in msg:
            return jsonify({"error": msg}), 413
        return jsonify({"error": msg}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds", methods=["GET"])
@require_auth
def list_sounds_route():
    user_id = g.current_user["user_id"]
    owner_type = request.args.get("owner_type")
    owner_id = request.args.get("owner_id")
    category_id = request.args.get("category_id")
    search = request.args.get("search")

    sounds = get_service().list_sounds(
        actor_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        category_id=category_id,
        search=search,
    )
    return jsonify({"sounds": sounds}), 200


@communities_bp.route("/communities/<community_id>/sounds", methods=["GET"])
@require_auth
def list_community_sounds_route(community_id: str):
    user_id = g.current_user["user_id"]
    search = request.args.get("search")

    try:
        sounds = get_service().list_sounds(
            actor_id=user_id,
            community_id=community_id,
            search=search,
        )
        return jsonify({"sounds": sounds}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/<sound_id>", methods=["GET"])
@require_auth
def get_sound_route(sound_id: str):
    user_id = g.current_user["user_id"]
    try:
        sound = get_service().get_sound(actor_id=user_id, sound_id=sound_id)
        return jsonify(sound), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/<sound_id>", methods=["PATCH"])
@require_auth
def update_sound_route(sound_id: str):
    user_id = g.current_user["user_id"]
    is_admin = g.current_user.get("is_admin", False)
    data = request.get_json() or {}

    try:
        updated = get_service().update_sound(
            actor_id=user_id,
            sound_id=sound_id,
            title=data.get("title"),
            category_id=data.get("category_id"),
            volume_scale=data.get("volume_scale"),
            cooldown_seconds=data.get("cooldown_seconds"),
            is_admin=is_admin,
        )
        return jsonify(updated), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/<sound_id>", methods=["DELETE"])
@require_auth
def delete_sound_route(sound_id: str):
    user_id = g.current_user["user_id"]
    is_admin = g.current_user.get("is_admin", False)

    try:
        success = get_service().delete_sound(
            actor_id=user_id,
            sound_id=sound_id,
            is_admin=is_admin,
        )
        return jsonify({"deleted": success}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/<sound_id>/favorite", methods=["POST"])
@require_auth
def favorite_sound_route(sound_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    is_favorite = bool(data.get("is_favorite", True))
    hotkey = data.get("hotkey")

    try:
        success = get_service().toggle_favorite_sound(
            actor_id=user_id,
            sound_id=sound_id,
            is_favorite=is_favorite,
            hotkey=hotkey,
        )
        return jsonify({"status": "updated", "is_favorite": is_favorite, "hotkey": hotkey}), 200
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/sounds/favorites", methods=["GET"])
@require_auth
def list_favorites_route():
    user_id = g.current_user["user_id"]
    favorites = get_service().list_favorite_sounds(user_id)
    return jsonify({"favorites": favorites}), 200


@communities_bp.route("/sounds/<sound_id>/play-authorize", methods=["POST"])
@require_auth
def authorize_sound_play_route(sound_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    channel_id = data.get("channel_id")

    if not channel_id:
        return jsonify({"error": "channel_id requerido"}), 400

    try:
        result = get_service().authorize_sound_play(
            actor_id=user_id,
            sound_id=sound_id,
            channel_id=channel_id,
        )
        CommunityMetricsCollector.get_instance().increment("communities_soundboard_plays_total")
        return jsonify(result), 200
    except SoundCooldownError as e:
        resp = jsonify({
            "error": "SOUND_COOLDOWN",
            "message": str(e),
            "retry_after": e.retry_after,
        })
        resp.headers["Retry-After"] = str(int(e.retry_after) + 1)
        return resp, 429
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


# =============================================================================
# STREAMING (COMPARTIR PANTALLA, VENTANA Y JUEGOS)
# =============================================================================

@communities_bp.route("/streams/sources", methods=["GET"])
@require_auth
def get_stream_sources_route():
    user_id = g.current_user["user_id"]
    sources = get_service().get_capture_sources(user_id)
    return jsonify(sources), 200


@communities_bp.route("/channels/<channel_id>/stream-start", methods=["POST"])
@require_auth
def start_stream_route(channel_id: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", "Streamer")
    data = request.get_json() or {}

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    stream_type = data.get("stream_type", "screen")
    title = data.get("title", f"Stream de {username}")
    game_id = data.get("game_id")
    resolution = data.get("resolution", "1080p")
    fps = int(data.get("fps", 60))
    bitrate_kbps = int(data.get("bitrate_kbps", 4500))
    has_audio = bool(data.get("has_audio", True))

    try:
        res = get_service().start_stream(
            actor_id=user_id,
            username=username,
            community_id=ch["community_id"],
            channel_id=channel_id,
            stream_type=stream_type,
            title=title,
            game_id=game_id,
            resolution=resolution,
            fps=fps,
            bitrate_kbps=bitrate_kbps,
            has_audio=has_audio,
        )
        CommunityMetricsCollector.get_instance().increment("communities_streams_started_total")
        return jsonify(res), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except StreamLimitError as e:
        return jsonify({"error": "STREAM_LIMIT_REACHED", "message": str(e)}), 409
    except StreamValidationError as e:
        return jsonify({"error": e.code, "message": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/stream-pause", methods=["POST"])
@require_auth
def pause_stream_route(channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    session_id = data.get("session_id")
    is_paused = bool(data.get("is_paused", True))

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    if not session_id:
        active = get_service().repo.get_active_stream_for_channel(channel_id)
        if not active:
            return jsonify({"error": "No hay transmisión activa en este canal"}), 404
        session_id = active["id"]

    try:
        updated = get_service().pause_stream(
            actor_id=user_id,
            community_id=ch["community_id"],
            channel_id=channel_id,
            session_id=session_id,
            is_paused=is_paused,
        )
        return jsonify(updated), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/stream-resume", methods=["POST"])
@require_auth
def resume_stream_route(channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    session_id = data.get("session_id")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    if not session_id:
        active = get_service().repo.get_active_stream_for_channel(channel_id)
        if not active:
            return jsonify({"error": "No hay transmisión activa en este canal"}), 404
        session_id = active["id"]

    try:
        updated = get_service().pause_stream(
            actor_id=user_id,
            community_id=ch["community_id"],
            channel_id=channel_id,
            session_id=session_id,
            is_paused=False,
        )
        return jsonify(updated), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/stream-stop", methods=["POST"])
@require_auth
def stop_stream_route(channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    session_id = data.get("session_id")

    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    if not session_id:
        active = get_service().repo.get_active_stream_for_channel(channel_id)
        if not active:
            return jsonify({"status": "stopped", "message": "No había stream activo"}), 200
        session_id = active["id"]

    try:
        success = get_service().stop_stream(
            actor_id=user_id,
            community_id=ch["community_id"],
            channel_id=channel_id,
            session_id=session_id,
        )
        return jsonify({"status": "stopped", "session_id": session_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/stream", methods=["GET"])
@require_auth
def get_channel_stream_route(channel_id: str):
    user_id = g.current_user["user_id"]
    ch = get_service().repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        stream = get_service().get_active_channel_stream(
            actor_id=user_id,
            community_id=ch["community_id"],
            channel_id=channel_id,
        )
        return jsonify({"stream": stream}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/streams", methods=["GET"])
@require_auth
def list_active_streams_route():
    user_id = g.current_user["user_id"]
    community_id = request.args.get("community_id")

    try:
        streams = get_service().list_active_streams(
            actor_id=user_id,
            community_id=community_id,
        )
        return jsonify({"streams": streams}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# =============================================================================
# MODERACIÓN, SANCIONES JERÁRQUICAS, REPORTES Y AUDITORÍA
# =============================================================================

@communities_bp.route("/communities/<community_id>/moderation/warn", methods=["POST"])
@require_auth
def warn_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    reason = data.get("reason", "Advertencia de moderación")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        action = get_service().warn_member(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            reason=reason,
        )
        CommunityMetricsCollector.get_instance().increment("communities_moderation_actions_total")
        return jsonify(action), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/mute", methods=["POST"])
@require_auth
def mute_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    duration_minutes = data.get("duration_minutes")
    if duration_minutes is not None:
        duration_minutes = int(duration_minutes)
    reason = data.get("reason")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        action = get_service().mute_member(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            duration_minutes=duration_minutes,
            reason=reason,
        )
        CommunityMetricsCollector.get_instance().increment("communities_moderation_actions_total")
        return jsonify(action), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/unmute", methods=["POST"])
@require_auth
def unmute_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    reason = data.get("reason")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        action = get_service().unmute_member(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            reason=reason,
        )
        CommunityMetricsCollector.get_instance().increment("communities_moderation_actions_total")
        return jsonify(action), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/kick", methods=["POST"])
@require_auth
def moderation_kick_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    reason = data.get("reason")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        success = get_service().kick_member_with_audit(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            reason=reason,
        )
        CommunityMetricsCollector.get_instance().increment("communities_moderation_actions_total")
        return jsonify({"kicked": success, "target_user_id": target_user_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/ban", methods=["POST"])
@require_auth
def ban_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    duration_hours = data.get("duration_hours")
    if duration_hours is not None:
        duration_hours = int(duration_hours)
    reason = data.get("reason")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        action = get_service().ban_member(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            duration_hours=duration_hours,
            reason=reason,
        )
        CommunityMetricsCollector.get_instance().increment("communities_moderation_actions_total")
        return jsonify(action), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/unban", methods=["POST"])
@require_auth
def unban_member_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    reason = data.get("reason")

    if not target_user_id:
        return jsonify({"error": "target_user_id requerido"}), 400

    try:
        action = get_service().unban_member(
            community_id=community_id,
            actor_id=user_id,
            target_user_id=target_user_id,
            reason=reason,
        )
        return jsonify(action), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/moderation/actions", methods=["GET"])
@require_auth
def list_moderation_actions_route(community_id: str):
    user_id = g.current_user["user_id"]
    target_id = request.args.get("target_id")
    action = request.args.get("action")

    try:
        actions = get_service().list_moderation_actions(
            community_id=community_id,
            actor_id=user_id,
            target_id=target_id,
            action=action,
        )
        return jsonify({"actions": actions}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@communities_bp.route("/communities/<community_id>/reports", methods=["POST"])
@require_auth
def create_report_route(community_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    target_type = data.get("target_type", "user")
    target_id = data.get("target_id")
    reason = data.get("reason", "")

    if not target_id:
        return jsonify({"error": "target_id requerido"}), 400

    try:
        report = get_service().create_report(
            community_id=community_id,
            reporter_id=user_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
        )
        return jsonify(report), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/reports", methods=["GET"])
@require_auth
def list_reports_route(community_id: str):
    user_id = g.current_user["user_id"]
    status = request.args.get("status")

    try:
        reports = get_service().list_reports(
            community_id=community_id,
            actor_id=user_id,
            status=status,
        )
        return jsonify({"reports": reports}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@communities_bp.route("/communities/<community_id>/reports/<report_id>", methods=["PATCH"])
@require_auth
def resolve_report_route(community_id: str, report_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    status = data.get("status", "resolved")
    resolution_notes = data.get("resolution_notes")

    try:
        updated = get_service().resolve_report(
            community_id=community_id,
            actor_id=user_id,
            report_id=report_id,
            status=status,
            resolution_notes=resolution_notes,
        )
        return jsonify(updated), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/audit-log", methods=["GET"])
@require_auth
def list_audit_log_route(community_id: str):
    user_id = g.current_user["user_id"]
    action_type = request.args.get("action_type")
    limit = int(request.args.get("limit", 100))

    try:
        entries = get_service().list_audit_log(
            community_id=community_id,
            actor_id=user_id,
            action_type=action_type,
            limit=limit,
        )
        return jsonify({"entries": entries}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# =============================================================================
# OBSERVABILIDAD, MÉTRICAS PROMETHEUS, SALUD Y LÍMITES OPERATIVOS (FASE 7)
# =============================================================================

@communities_bp.route("/health", methods=["GET"])
@communities_bp.route("/communities/health", methods=["GET"])
def health_check_route():
    """Diagnóstico de salud integral de los componentes de Communities."""
    repo_ok = False
    try:
        # Consulta de validación básica contra el repositorio
        repo_ok = get_service().repo.get_community("00000000-0000-0000-0000-000000000000") is None
    except Exception:
        repo_ok = False

    metrics = CommunityMetricsCollector.get_instance().get_snapshot()
    status = "healthy" if repo_ok else "degraded"
    return jsonify({
        "status": status,
        "database": "connected" if repo_ok else "disconnected",
        "livekit_sfu": "ready",
        "storage": "local_storage_ready",
        "uptime_seconds": metrics["uptime_seconds"],
        "version": "2.1.0-communities-v1.0",
    }), 200 if repo_ok else 503


@communities_bp.route("/metrics", methods=["GET"])
@communities_bp.route("/communities/metrics", methods=["GET"])
def metrics_route():
    """Expone métricas en formato estándar Prometheus (RFC 0001) o JSON."""
    collector = CommunityMetricsCollector.get_instance()
    if request.headers.get("Accept") == "application/json":
        return jsonify(collector.get_snapshot()), 200

    return Response(
        collector.format_prometheus(),
        mimetype="text/plain; version=0.0.4; charset=utf-8"
    )


@communities_bp.route("/system/limits", methods=["GET"])
@communities_bp.route("/communities/system/limits", methods=["GET"])
def system_limits_route():
    """Publica formalmente las capacidades y límites de cuota operativos del sistema."""
    return jsonify({
        "limits": {
            "max_members_per_community": 500,
            "max_channels_per_community": 100,
            "max_roles_per_community": 50,
            "max_streams_per_channel": 1,
            "max_voice_participants_per_channel": 100,
            "max_message_length_chars": 2000,
            "max_sound_file_size_bytes": 5242880,
            "max_sound_duration_seconds": 15.0,
            "sound_cooldown_seconds": 5,
            "max_personal_sounds": 50,
            "stream_max_fps": 60,
            "stream_max_resolution": "4k",
        }
    }), 200


