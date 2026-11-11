"""
backend/communities/routes.py - Rutas REST de la API de Communities para C.C.I. SYSTEM.

Expone endpoints bajo /api/v1/communities e invitaciones protegidos con autenticación JWT Bearer.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import socket
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlparse
from flask import Blueprint, g, jsonify, request, Response, send_file
from backend.auth import require_auth
from backend.communities.service import CommunitiesService, SoundCooldownError, StreamLimitError
from backend.communities.stream_adapter import StreamValidationError
from backend.communities.metrics import CommunityMetricsCollector
from backend.config import config

communities_bp = Blueprint("communities", __name__)

_realtime_emitter: Optional[Callable[..., Any]] = None


def set_realtime_emitter(fn: Callable[..., Any]) -> None:
    """Registra la función Socket.IO para emitir eventos en tiempo real desde rutas REST."""
    global _realtime_emitter
    _realtime_emitter = fn


def _emit_realtime(event: str, payload: Any, room: Optional[str] = None) -> None:
    if _realtime_emitter is None:
        return
    try:
        _realtime_emitter(event, payload, to=room)
    except Exception:
        pass


def _resolve_usernames(user_ids: Iterable[str]) -> Dict[str, str]:
    """Resuelve nombres de cuenta reales desde SQLite (`accounts`) sin simular usuarios."""
    ids = [str(uid) for uid in user_ids if uid]
    mapping: Dict[str, str] = {}
    numeric_ids = []
    for uid in ids:
        if uid.isdigit():
            numeric_ids.append(int(uid))
    if not numeric_ids:
        return mapping
    try:
        import cci_database
        with cci_database.get_db() as conn:
            placeholders = ",".join("?" for _ in numeric_ids)
            rows = conn.execute(
                f"SELECT id, username FROM accounts WHERE id IN ({placeholders})",
                numeric_ids,
            ).fetchall()
            for r in rows:
                mapping[str(r["id"])] = str(r["username"])
    except Exception:
        pass
    return mapping


_ALLOWED_IMAGE_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def _attachments_dir(svc: CommunitiesService) -> Path:
    dbp = str(getattr(svc.repo, "db_path", "") or "")
    if dbp and dbp != ":memory:":
        base = Path(dbp).resolve().parent / "attachments"
    else:
        base = Path(__file__).resolve().parent.parent.parent / ".cci-user-data" / "attachments"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _detect_image_mime(raw: bytes, claimed_mime: str = "", filename: str = "") -> Optional[str]:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    ext = Path(filename).suffix.lower()
    if claimed_mime.lower() in _ALLOWED_IMAGE_MIME and _ALLOWED_IMAGE_MIME[claimed_mime.lower()] == ext:
        return "image/jpeg" if claimed_mime.lower() == "image/jpg" else claimed_mime.lower()
    return None


def _enrich_messages(msgs: List[Dict[str, Any]], fallback_names: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    ids: List[str] = []
    for m in msgs:
        if m.get("author_id"):
            ids.append(str(m["author_id"]))
        rp = m.get("reply_preview")
        if isinstance(rp, dict) and rp.get("author_id"):
            ids.append(str(rp["author_id"]))
    names = _resolve_usernames(ids)
    if fallback_names:
        for k, v in fallback_names.items():
            names.setdefault(str(k), str(v))
    out: List[Dict[str, Any]] = []
    for m in msgs:
        item = dict(m)
        aid = str(item.get("author_id") or "")
        item["author_name"] = item.get("author_name") or names.get(aid) or aid
        rp = item.get("reply_preview")
        if isinstance(rp, dict):
            rp_copy = dict(rp)
            rpid = str(rp_copy.get("author_id") or "")
            rp_copy["author_name"] = rp_copy.get("author_name") or names.get(rpid) or rpid
            item["reply_preview"] = rp_copy
        out.append(item)
    return out


def _broadcast_presence_to_communities(svc: CommunitiesService, user_id: str, raw_presence: Dict[str, Any]) -> None:
    masked = svc._mask_presence_for_viewer(raw_presence, viewer_id=None)
    uname = _resolve_usernames([user_id]).get(str(user_id), str(user_id))
    payload = dict(masked)
    payload["username"] = uname
    payload["game"] = masked.get("activity_title")
    for c in svc.repo.list_communities_for_user(user_id):
        _emit_realtime("presence:updated", payload, room=f"comm_{c['id']}")


def _dispatch_mentions(
    svc: CommunitiesService,
    community_id: str,
    channel_id: str,
    msg: Dict[str, Any],
    sender_id: str,
    sender_name: str,
) -> None:
    content = str(msg.get("content") or "")
    raw_tags = {m.lower() for m in re.findall(r"@([A-Za-z0-9_.-]{2,32})", content)}
    if not raw_tags:
        return
    members = svc.repo.list_members(community_id)
    names = _resolve_usernames(m.get("user_id") for m in members if m.get("user_id"))
    for m in members:
        uid = str(m.get("user_id") or "")
        if not uid or uid == str(sender_id):
            continue
        uname = names.get(uid, uid).lower()
        if uname in raw_tags or uid.lower() in raw_tags:
            notif = svc.repo.create_notification(
                user_id=uid,
                kind="mention",
                actor_id=sender_id,
                community_id=community_id,
                channel_id=channel_id,
                message_id=msg.get("id"),
                title=f"@{sender_name} te mencionó",
                body=content[:140],
            )
            _emit_realtime("notification:created", notif, room=f"user_{uid}")


def _probe_livekit_tcp(timeout: float = 0.25) -> bool:
    """Verifica por TCP si el puerto configurado de LiveKit SFU acepta conexiones reales."""
    raw = config.livekit_ws_url or ""
    try:
        parsed = urlparse(raw)
        host = parsed.hostname
        if not host:
            return False
        port = parsed.port or (443 if parsed.scheme == "wss" else 7880)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


@communities_bp.before_request
def record_community_request_start():
    request._start_time = time.time()
    CommunityMetricsCollector.get_instance().increment("communities_api_requests_total")


@communities_bp.after_request
def record_community_request_latency(response):
    collector = CommunityMetricsCollector.get_instance()
    if hasattr(request, "_start_time"):
        elapsed = time.time() - request._start_time
        collector.record_latency(elapsed)
    if response.status_code >= 400:
        collector.record_error("api")
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
    svc = get_service()
    items = svc.list_communities(user_id, discover_public=discover)
    user_comm_ids = {c["id"] for c in svc.list_communities(user_id, discover_public=False)}
    enriched = []
    for c in items:
        item = dict(c)
        item["member_count"] = len(svc.repo.list_members(c["id"]))
        item["is_member"] = c["id"] in user_comm_ids
        enriched.append(item)
    return jsonify({"communities": enriched}), 200


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


@communities_bp.route("/communities/<community_id>/invitations", methods=["GET"])
@require_auth
def list_invitations_route(community_id: str):
    user_id = g.current_user["user_id"]
    try:
        invs = get_service().list_invitations(community_id, user_id)
        return jsonify({"invitations": invs}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/communities/<community_id>/invitations/<code_str>", methods=["DELETE"])
@require_auth
def revoke_invitation_route(community_id: str, code_str: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().revoke_invitation(community_id, code_str, user_id)
        return jsonify({"status": "revoked", "code": code_str.upper()}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/invitations/<code_str>/accept", methods=["POST"])
@require_auth
def accept_invitation_route(code_str: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
    try:
        res = get_service().join_via_invitation(code_str, user_id)
        comm_id = res["community"]["id"]
        _emit_realtime(
            "community:member_joined",
            {"community_id": comm_id, "user_id": user_id, "username": username, "timestamp": time.time()},
            room=f"comm_{comm_id}",
        )
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
    username = g.current_user.get("username", user_id)
    data = request.get_json() or {}
    code_str = data.get("code", "")
    try:
        res = get_service().join_via_invitation(code_str, user_id)
        comm_id = res["community"]["id"]
        _emit_realtime(
            "community:member_joined",
            {"community_id": comm_id, "user_id": user_id, "username": username, "timestamp": time.time()},
            room=f"comm_{comm_id}",
        )
        return jsonify(res), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/communities/<community_id>/join", methods=["POST"])
@require_auth
def join_public_community_route(community_id: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
    try:
        res = get_service().join_public_community(community_id, user_id)
        if not res.get("already_member"):
            _emit_realtime(
                "community:member_joined",
                {"community_id": community_id, "user_id": user_id, "username": username, "timestamp": time.time()},
                room=f"comm_{community_id}",
            )
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
    names = _resolve_usernames(m.get("user_id") for m in members)
    enriched = []
    for m in members:
        item = dict(m)
        uid = str(item.get("user_id", ""))
        item["username"] = item.get("nickname") or names.get(uid) or uid
        enriched.append(item)
    return jsonify({"members": enriched}), 200


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
        _emit_realtime(
            "community:member_left",
            {"community_id": community_id, "user_id": user_id, "timestamp": time.time()},
            room=f"comm_{community_id}",
        )
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
        _emit_realtime("channel:created", {"community_id": community_id, "channel": ch}, room=f"comm_{community_id}")
        return jsonify({"channel": ch}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@communities_bp.route("/communities/<community_id>/channels/<channel_id>", methods=["PATCH"])
@require_auth
def update_channel_route(community_id: str, channel_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    try:
        ch = get_service().update_channel(
            community_id=community_id,
            channel_id=channel_id,
            requester_id=user_id,
            name=data.get("name"),
            topic=data.get("topic"),
        )
        _emit_realtime("channel:updated", {"community_id": community_id, "channel": ch}, room=f"comm_{community_id}")
        return jsonify({"channel": ch}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/communities/<community_id>/channels/<channel_id>", methods=["DELETE"])
@require_auth
def delete_channel_route(community_id: str, channel_id: str):
    user_id = g.current_user["user_id"]
    try:
        get_service().delete_channel(community_id, channel_id, user_id)
        _emit_realtime("channel:deleted", {"community_id": community_id, "channel_id": channel_id}, room=f"comm_{community_id}")
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
    after_id = request.args.get("after_id")

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
            after_id=after_id,
        )
        return jsonify({"messages": _enrich_messages(msgs)}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/messages", methods=["POST"])
@require_auth
def send_channel_message_route(channel_id: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
    data = request.get_json() or {}
    content = data.get("content", "")
    reply_to_id = data.get("reply_to_id")
    attachment_ids = data.get("attachment_ids")

    svc = get_service()
    ch = svc.repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        msg = svc.send_message(
            community_id=ch["community_id"],
            channel_id=channel_id,
            author_id=user_id,
            content=content,
            reply_to_id=reply_to_id,
            attachment_ids=attachment_ids,
        )
        enriched = _enrich_messages([msg], fallback_names={user_id: username})[0]
        CommunityMetricsCollector.get_instance().increment("communities_messages_total")
        _emit_realtime("message:created", enriched, room=f"comm_chan_{channel_id}")
        _dispatch_mentions(svc, ch["community_id"], channel_id, enriched, str(user_id), str(username))
        return jsonify({"message": enriched}), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except (ValueError, LookupError) as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/channels/<channel_id>/messages/<message_id>", methods=["PATCH"])
@require_auth
def edit_channel_message_route(channel_id: str, message_id: str):
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
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
        enriched = _enrich_messages([updated], fallback_names={user_id: username})[0]
        _emit_realtime("message:updated", enriched, room=f"comm_chan_{channel_id}")
        return jsonify({"message": enriched}), 200
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
        _emit_realtime("message:deleted", {"channel_id": channel_id, "message_id": message_id}, room=f"comm_chan_{channel_id}")
        return jsonify({"status": "deleted", "message_id": message_id}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except LookupError as e:
        return jsonify({"error": str(e)}), 404


@communities_bp.route("/channels/<channel_id>/messages/<message_id>/reactions", methods=["POST"])
@require_auth
def toggle_reaction_route(channel_id: str, message_id: str):
    user_id = g.current_user["user_id"]
    data = request.get_json() or {}
    emoji = data.get("emoji", "")

    svc = get_service()
    ch = svc.repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404

    try:
        res = svc.toggle_message_reaction(
            community_id=ch["community_id"],
            channel_id=channel_id,
            message_id=message_id,
            requester_id=user_id,
            emoji=emoji,
        )
        _emit_realtime("message:reaction_updated", res, room=f"comm_chan_{channel_id}")
        return jsonify(res), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except (ValueError, LookupError) as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/channels/<channel_id>/attachments", methods=["POST"])
@require_auth
def upload_attachment_route(channel_id: str):
    user_id = g.current_user["user_id"]
    svc = get_service()
    ch = svc.repo.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404
    if not svc.has_permission(ch["community_id"], user_id, "messages.attachments", channel_id=channel_id):
        return jsonify({"error": "Acceso denegado: se requiere permiso messages.attachments"}), 403

    raw_bytes: bytes = b""
    filename = "captura.png"
    claimed_mime = ""
    if "file" in request.files:
        fobj = request.files["file"]
        filename = Path(fobj.filename or "captura.png").name
        claimed_mime = str(fobj.mimetype or "")
        raw_bytes = fobj.read(_MAX_ATTACHMENT_BYTES + 1)
    else:
        data = request.get_json(silent=True) or {}
        b64 = data.get("data_b64")
        filename = Path(str(data.get("filename") or "captura.png")).name
        claimed_mime = str(data.get("content_type") or "")
        if b64:
            try:
                raw_bytes = base64.b64decode(b64, validate=True)
            except Exception:
                return jsonify({"error": "Contenido base64 inválido"}), 400

    if not raw_bytes:
        return jsonify({"error": "Archivo adjunto vacío"}), 400
    if len(raw_bytes) > _MAX_ATTACHMENT_BYTES:
        return jsonify({"error": "El adjunto supera el límite de 5 MB"}), 413

    mime = _detect_image_mime(raw_bytes, claimed_mime=claimed_mime, filename=filename)
    if not mime or mime not in _ALLOWED_IMAGE_MIME:
        return jsonify({"error": "Solo se permiten imágenes PNG, JPEG, WEBP o GIF"}), 415

    att_id = str(uuid.uuid4())
    ext = _ALLOWED_IMAGE_MIME[mime]
    storage_key = f"{att_id}{ext}"
    store_dir = _attachments_dir(svc)
    dest = (store_dir / storage_key).resolve()
    if not dest.is_relative_to(store_dir.resolve()):
        return jsonify({"error": "Ruta de almacenamiento inválida"}), 400
    dest.write_bytes(raw_bytes)
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    staged = svc.repo.stage_attachment(
        attachment_id=att_id,
        channel_id=channel_id,
        uploader_id=user_id,
        storage_key=storage_key,
        filename=filename[:120],
        content_type=mime,
        size_bytes=len(raw_bytes),
        checksum_sha256=sha256,
    )
    return jsonify({"attachment": staged}), 201


@communities_bp.route("/attachments/<attachment_id>", methods=["GET"])
@require_auth
def get_attachment_route(attachment_id: str):
    user_id = g.current_user["user_id"]
    svc = get_service()
    att = svc.repo.get_attachment(attachment_id)
    if not att:
        return jsonify({"error": "Adjunto no encontrado"}), 404
    msg = svc.repo.get_message(att["message_id"])
    if not msg:
        return jsonify({"error": "Mensaje asociado no encontrado"}), 404
    ch = svc.repo.get_channel(msg["channel_id"])
    if not ch:
        return jsonify({"error": "Canal no encontrado"}), 404
    if not svc.has_permission(ch["community_id"], user_id, "messages.read", channel_id=ch["id"]):
        return jsonify({"error": "Acceso denegado a este adjunto"}), 403

    store_dir = _attachments_dir(svc).resolve()
    target = (store_dir / Path(att["storage_key"]).name).resolve()
    if not target.is_relative_to(store_dir) or not target.exists():
        return jsonify({"error": "Archivo no disponible en almacenamiento"}), 404
    return send_file(target, mimetype=att["content_type"], download_name=att["filename"])


# =============================================================================
# RUTAS DE PRESENCIA DE USUARIO, HEARTBEAT, ACTIVIDAD Y NOTIFICACIONES
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
    ttl_seconds = data.get("ttl_seconds")
    activity_visibility = data.get("activity_visibility")

    svc = get_service()
    try:
        updated = svc.set_user_presence(
            user_id=user_id,
            status=status,
            custom_status=custom_status,
            ttl_seconds=float(ttl_seconds) if ttl_seconds is not None else None,
            activity_visibility=activity_visibility,
        )
        _broadcast_presence_to_communities(svc, user_id, updated)
        return jsonify({"presence": updated}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/users/presence/heartbeat", methods=["POST"])
@require_auth
def heartbeat_presence_route():
    user_id = g.current_user["user_id"]
    data = request.get_json(silent=True) or {}
    ttl_seconds = data.get("ttl_seconds")
    svc = get_service()
    updated = svc.heartbeat_user_presence(
        user_id=user_id,
        ttl_seconds=float(ttl_seconds) if ttl_seconds is not None else None,
    )
    return jsonify({"presence": updated}), 200


@communities_bp.route("/users/activity/game", methods=["POST"])
@require_auth
def report_game_activity_route():
    user_id = g.current_user["user_id"]
    username = g.current_user.get("username", user_id)
    data = request.get_json() or {}
    action = data.get("action", "")
    game_id = data.get("game_id")
    title = data.get("title")
    visibility = data.get("visibility", "communities")

    svc = get_service()
    try:
        res = svc.report_game_activity(
            user_id=user_id,
            action=action,
            game_id=game_id,
            title=title,
            visibility=visibility,
        )
        ev = dict(res["event"])
        ev["username"] = username
        ev_name = "activity:game_started" if action == "started" else "activity:game_stopped"
        if ev.get("visibility") != "private" and res["presence"].get("status") != "invisible":
            for cid in res["community_ids"]:
                _emit_realtime(ev_name, ev, room=f"comm_{cid}")
        _broadcast_presence_to_communities(svc, user_id, res["presence"])
        return jsonify(res), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@communities_bp.route("/users/activity/feed", methods=["GET"])
@require_auth
def get_activity_feed_route():
    viewer_id = g.current_user["user_id"]
    limit = max(1, min(100, int(request.args.get("limit", 40))))
    friend_ids: List[str] = []
    try:
        import cci_database
        for f in cci_database.get_user_friends(viewer_id):
            if f.get("status") == "accepted":
                fid = f["addressee_id"] if f["requester_id"] == viewer_id else f["requester_id"]
                friend_ids.append(str(fid))
    except Exception:
        pass

    svc = get_service()
    events = svc.get_activity_feed(viewer_id=viewer_id, friend_ids=friend_ids, limit=limit)
    names = _resolve_usernames(e.get("user_id") for e in events)
    enriched = []
    for e in events:
        item = dict(e)
        uid = str(item.get("user_id") or "")
        item["username"] = names.get(uid, uid)
        enriched.append(item)
    return jsonify({"events": enriched}), 200


@communities_bp.route("/users/notifications", methods=["GET"])
@require_auth
def list_notifications_route():
    user_id = g.current_user["user_id"]
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = max(1, min(100, int(request.args.get("limit", 40))))
    items = get_service().list_notifications(user_id, unread_only=unread_only, limit=limit)
    names = _resolve_usernames(i.get("actor_id") for i in items if i.get("actor_id"))
    for i in items:
        aid = str(i.get("actor_id") or "")
        if aid:
            i["actor_name"] = names.get(aid, aid)
    return jsonify({"notifications": items}), 200


@communities_bp.route("/users/notifications/read", methods=["POST"])
@require_auth
def mark_notifications_read_route():
    user_id = g.current_user["user_id"]
    data = request.get_json(silent=True) or {}
    nids = data.get("notification_ids")
    updated = get_service().mark_notifications_read(user_id, notification_ids=nids)
    return jsonify({"marked_read": updated}), 200


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
    collector = CommunityMetricsCollector.get_instance()
    repo_ok = False
    try:
        # Consulta de validación básica contra el repositorio
        repo_ok = get_service().repo.get_community("00000000-0000-0000-0000-000000000000") is None
    except Exception:
        repo_ok = False
        collector.record_error("db")

    metrics = collector.get_snapshot()
    lk_tcp_ok = _probe_livekit_tcp() if repo_ok else False
    status = "healthy" if repo_ok else "degraded"
    return jsonify({
        "status": status,
        "database": "connected" if repo_ok else "disconnected",
        "livekit_sfu": "ready",
        "livekit_token_signing": "ready",
        "livekit_media_plane": "reachable" if lk_tcp_ok else "unreachable",
        "voice_media_transport": "signaling_only",
        "realtime_socketio": "ready",
        "storage": "local_storage_ready",
        "metrics_scope": "process_local",
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


