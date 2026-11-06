"""
backend/communities/routes.py - Rutas REST de la API de Communities para C.C.I. SYSTEM.

Expone endpoints bajo /api/v1/communities e invitaciones protegidos con autenticación JWT Bearer.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from backend.auth import require_auth
from backend.communities.service import CommunitiesService

communities_bp = Blueprint("communities", __name__)


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


