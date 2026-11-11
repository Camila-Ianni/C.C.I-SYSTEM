"""test_communities_fase1_3.py - Suite E2E real para Fase 1, Fase 2 y Fase 3 de C.C.I. Communities.

Verifica:
- Fase 1 (Unificar): edición/eliminación de canales + sync realtime, listado/revocación de invitaciones,
  moderación (mute/unmute/kick), unificación de presencia en FriendsService + SQLite WAL + solicitudes por @username.
- Fase 2 (Chat completo): reply_preview, edición inline, borrado, reacciones emoji realtime,
  adjuntos PNG validados (subida + descarga autorizada + 403 a no-miembro), paginación before_id,
  indicador de escritura (typing:updated), y recuperación tras reconexión (after_id) sin duplicados.
- Fase 3 (Presencia/Actividad): estados online/idle/dnd/invisible (enmascaramiento real),
  expiración automática por TTL en SQLite, ciclo started/stopped de actividad de juego con privacidad,
  feed deduplicado y notificaciones reales por @mención marcables como leídas.
"""
from __future__ import annotations

import os
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"

import requests
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _pump_events(seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.025)
    return bool(predicate())


def _make_tiny_png() -> bytes:
    """Genera un PNG válido 1x1 RGB mínimo sin depender de librerías externas."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw_scanline = b"\x00\x35\xc8\xf1"
    idat = zlib.compress(raw_scanline)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


class TestCommunitiesFase1To3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_f13_")
        tmp_path = Path(cls._tmp_dir.name)
        cls._old_envs = {
            k: os.environ.get(k)
            for k in ("CCI_DATABASE_PATH", "CCI_COMMUNITIES_DB_PATH", "CCI_PRESENCE_TTL_SECONDS")
        }
        os.environ["CCI_DATABASE_PATH"] = str(tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(tmp_path / "communities.sqlite3")
        os.environ["CCI_PRESENCE_TTL_SECONDS"] = "60"

        import cci_database
        from backend.communities.repository import CommunitiesRepository
        from backend.friends_service import FriendsService

        cci_database.init_db()
        CommunitiesRepository.reset_instance()
        FriendsService._instance = None

        import backend.server as server_mod
        cls.server_mod = server_mod
        cls.port = _free_port()
        cls.api_url = f"http://127.0.0.1:{cls.port}"

        def _serve():
            server_mod.socketio.run(
                server_mod.app,
                host="127.0.0.1",
                port=cls.port,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        cls._srv_thread = threading.Thread(target=_serve, daemon=True)
        cls._srv_thread.start()

        deadline = time.time() + 10.0
        while time.time() < deadline:
            try:
                if requests.get(f"{cls.api_url}/api/v1/health", timeout=0.5).status_code == 200:
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("No se pudo iniciar servidor backend local para suite Fase 1-3.")

        cls.app = QApplication.instance() or QApplication(sys.argv)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._old_envs.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        cls._tmp_dir.cleanup()

    def _new_controller(self, tag: str):
        from backend.communities.desktop_client import CommunityController

        sess_path = Path(self._tmp_dir.name) / f"session_{tag}_{time.time_ns()}.json"
        ctrl = CommunityController(
            api_url=self.api_url,
            session_path=sess_path,
            heartbeat_interval_ms=0,
        )
        self.addCleanup(ctrl.shutdown)
        return ctrl

    def test_fase1_channels_invites_moderation_and_friends_unification(self):
        from backend.communities.desktop_client import CommunityApiError
        from backend.friends_service import FriendsService, PresenceStatus

        ctrl_a = self._new_controller("f1_a")
        ctrl_b = self._new_controller("f1_b")
        ctrl_c = self._new_controller("f1_c")

        u_suffix = str(time.time_ns())[-6:]
        ctrl_a.register(f"f1a_{u_suffix}@cci.local", f"f1alice_{u_suffix}", "SecretPass123!")
        ctrl_b.register(f"f1b_{u_suffix}@cci.local", f"f1bob_{u_suffix}", "SecretPass123!")
        ctrl_c.register(f"f1c_{u_suffix}@cci.local", f"f1carol_{u_suffix}", "SecretPass123!")

        _wait_until(lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(), timeout=5.0)

        comm_payload = ctrl_a.create_community("Fase 1 Guild", "Mod & channels", visibility="private")
        cid = comm_payload["community"]["id"]

        # Crear invitación y revocar una segunda invitación antes de usarla
        inv_valid = ctrl_a.create_invitation(cid)
        inv_revoked = ctrl_a.create_invitation(cid)
        all_invs = ctrl_a.list_invitations(cid)
        codes = {i["code"] for i in all_invs}
        self.assertIn(inv_valid["code"], codes)
        self.assertIn(inv_revoked["code"], codes)

        self.assertTrue(ctrl_a.revoke_invitation(cid, inv_revoked["code"]))
        codes_after = {i["code"] for i in ctrl_a.list_invitations(cid)}
        self.assertNotIn(inv_revoked["code"], codes_after)

        # Unirse con invitación revocada falla 404
        with self.assertRaises(CommunityApiError) as err_rev:
            ctrl_b.join_by_invitation(inv_revoked["code"])
        self.assertEqual(err_rev.exception.status_code, 404)

        # Unirse con invitación válida sí funciona
        ctrl_b.join_by_invitation(inv_valid["code"])
        _pump_events(0.25)

        # Edición/eliminación de canal por no-admin falla 403; por owner actualiza realtime en B
        ch = ctrl_a.create_channel("torneos-old", "text", "Reglas v1")
        _wait_until(lambda: any(c["id"] == ch["id"] for c in ctrl_b.active_channels), timeout=4.0)

        with self.assertRaises(CommunityApiError) as err_perm:
            ctrl_b.update_channel(ch["id"], name="hacked")
        self.assertEqual(err_perm.exception.status_code, 403)

        updated_ch = ctrl_a.update_channel(ch["id"], name="torneos-live", topic="Reglas v2")
        self.assertEqual(updated_ch["name"], "torneos-live")
        self.assertTrue(
            _wait_until(
                lambda: any(c["id"] == ch["id"] and c["name"] == "torneos-live" for c in ctrl_b.active_channels),
                timeout=4.0,
            )
        )

        # Eliminar canal creado
        self.assertTrue(ctrl_a.delete_channel(ch["id"]))
        self.assertTrue(
            _wait_until(lambda: not any(c["id"] == ch["id"] for c in ctrl_b.active_channels), timeout=4.0)
        )

        # Moderación: mutear a Bob impide enviar mensajes, unmute restaura, kick expulsa
        ctrl_b.select_channel(ctrl_b.active_channels[0]["id"])
        ctrl_a.moderate_member(cid, ctrl_b.session.user_id, "mute", duration_seconds=120, reason="spam")
        with self.assertRaises(CommunityApiError) as err_mute:
            ctrl_b.send_message("No debería salir muteado")
        self.assertEqual(err_mute.exception.status_code, 403)

        ctrl_a.moderate_member(cid, ctrl_b.session.user_id, "unmute")
        ok_msg = ctrl_b.send_message("Ahora sí tras unmute")
        self.assertEqual(ok_msg["content"], "Ahora sí tras unmute")

        ctrl_a.moderate_member(cid, ctrl_b.session.user_id, "kick")
        with self.assertRaises(CommunityApiError):
            ctrl_b.send_message("Tras kick tampoco")

        # Unificación FriendsService -> CommunitiesRepository SQLite WAL persiste tras reset_instance
        fsvc = FriendsService.get_instance()
        fsvc.update_presence(ctrl_a.session.user_id, PresenceStatus.ONLINE, "Castlevania: SOTN")
        FriendsService._instance = None
        fsvc2 = FriendsService.get_instance()
        persisted = fsvc2.get_presence(ctrl_a.session.user_id)
        self.assertEqual(persisted["status"], "online")
        self.assertEqual(persisted["current_game"], "Castlevania: SOTN")

        # Solicitudes de amistad por @username y respuesta aceptada vía REST client
        ctrl_a.send_friend_request(ctrl_c.session.username)
        friends_c, incoming_c = ctrl_c.refresh_friends()
        self.assertTrue(
            any(str(r.get("requester_id") or r.get("from_user_id")) == ctrl_a.session.user_id for r in incoming_c)
        )
        ctrl_c.respond_friend_request(ctrl_a.session.user_id, accept=True)
        friends_a, _ = ctrl_a.refresh_friends()
        self.assertTrue(
            any(str(f.get("friend_id") or f.get("user_id")) == ctrl_c.session.user_id for f in friends_a)
        )

    def test_fase2_rich_chat_reactions_attachments_typing_pagination_and_reconnect_sync(self):
        from omnidash_qt import CommunitiesView

        ctrl_a = self._new_controller("f2_a")
        ctrl_b = self._new_controller("f2_b")
        view_a = CommunitiesView(controller=ctrl_a, auto_connect=False)
        view_b = CommunitiesView(controller=ctrl_b, auto_connect=False)
        self.addCleanup(view_a.deleteLater)
        self.addCleanup(view_b.deleteLater)

        u_suffix = str(time.time_ns())[-6:]
        ctrl_a.register(f"f2a_{u_suffix}@cci.local", f"f2alice_{u_suffix}", "SecretPass123!")
        ctrl_b.register(f"f2b_{u_suffix}@cci.local", f"f2bob_{u_suffix}", "SecretPass123!")
        _wait_until(lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(), timeout=5.0)

        comm = ctrl_a.create_community("Fase 2 Chat Hub", "Multimedia chat", visibility="private")
        cid = comm["community"]["id"]
        inv = ctrl_a.create_invitation(cid)
        ctrl_b.join_by_invitation(inv["code"])
        _wait_until(lambda: ctrl_b.active_channel is not None, timeout=5.0)
        ch_id = ctrl_a.active_channel["id"]

        # Sembrar 25 mensajes para verificar paginación before_id
        for idx in range(25):
            ctrl_a.send_message(f"hist_{idx:02d}")
        page_latest = ctrl_a.api.list_messages(ch_id, limit=10)
        self.assertEqual(len(page_latest), 10)
        older = ctrl_a.load_older_messages(before_id=page_latest[0]["id"], limit=10)
        self.assertEqual(len(older), 10)
        self.assertTrue({m["id"] for m in older}.isdisjoint({m["id"] for m in page_latest}))

        # Subir adjunto PNG real, enviarlo en mensaje y verificar descarga autorizada vs 403 no-miembro
        png_path = Path(self._tmp_dir.name) / "shot.png"
        png_bytes = _make_tiny_png()
        png_path.write_bytes(png_bytes)
        att = ctrl_a.upload_attachment(str(png_path))
        self.assertEqual(att["content_type"], "image/png")

        # Enviar mensaje con adjunto y luego responder (reply_to_id) + editar + reaccionar
        m_img = ctrl_a.send_message("Captura real del core", attachment_ids=[att["id"]])
        self.assertEqual(len(m_img.get("attachments") or []), 1)

        # Non-member 403 check
        ctrl_outsider = self._new_controller("f2_out")
        ctrl_outsider.register(f"f2out_{u_suffix}@cci.local", f"f2out_{u_suffix}", "SecretPass123!")
        r_forbid = requests.get(
            f"{self.api_url}/api/v1/attachments/{att['id']}",
            headers={"Authorization": f"Bearer {ctrl_outsider.session.token}"},
            timeout=3,
        )
        self.assertEqual(r_forbid.status_code, 403)
        self.assertEqual(ctrl_b.api.download_attachment_bytes(att["id"]), png_bytes)
        m_reply = ctrl_b.send_message("Buen frame!", reply_to_id=m_img["id"])
        self.assertEqual(m_reply["reply_preview"]["id"], m_img["id"])

        self.assertTrue(
            _wait_until(lambda: m_reply["id"] in view_a.interior_view.chat_area._msg_widgets, timeout=4.0)
        )

        # Reacción en tiempo real A -> B UI
        ctrl_a.toggle_reaction(m_img["id"], "🔥")
        self.assertTrue(
            _wait_until(
                lambda: not view_b.interior_view.chat_area._msg_widgets[m_img["id"]].reactions_wrap.isHidden(),
                timeout=4.0,
            )
        )

        # Typing indicator A -> B UI
        ctrl_a.emit_typing(True)
        self.assertTrue(
            _wait_until(
                lambda: (not view_b.interior_view.chat_area.typing_lbl.isHidden())
                and ctrl_a.session.username in view_b.interior_view.chat_area.typing_lbl.text(),
                timeout=4.0,
            )
        )

        # Edición inline A -> B UI
        ctrl_a.edit_message(m_img["id"], "Captura editada del core")
        self.assertTrue(
            _wait_until(
                lambda: "Captura editada del core" in view_b.interior_view.chat_area._msg_widgets[m_img["id"]].txt_lbl.text(),
                timeout=4.0,
            )
        )

        # ACC-04: Desconexión de B, mensajes enviados mientras tanto, reconexión y sync sin duplicados
        view_b.interior_view.chat_area.set_messages([m_img, m_reply], current_user_id=ctrl_b.session.user_id)
        before_count = len(view_b.interior_view.chat_area._msg_widgets)
        ctrl_b.realtime.disconnect_sync()
        _pump_events(0.2)

        m_missed_1 = ctrl_a.send_message("Mientras B estaba offline 1")
        m_missed_2 = ctrl_a.send_message("Mientras B estaba offline 2")

        ctrl_b.realtime.connect_with_token(self.api_url, ctrl_b.session.token)
        self.assertTrue(
            _wait_until(
                lambda: m_missed_1["id"] in view_b.interior_view.chat_area._msg_widgets
                and m_missed_2["id"] in view_b.interior_view.chat_area._msg_widgets,
                timeout=5.0,
            )
        )
        after_count = len(view_b.interior_view.chat_area._msg_widgets)
        self.assertEqual(after_count, before_count + 2)

    def test_fase3_presence_ttl_masking_game_activity_feed_and_mentions(self):
        from backend.communities.repository import CommunitiesRepository
        from backend.communities.service import CommunitiesService

        ctrl_a = self._new_controller("f3_a")
        ctrl_b = self._new_controller("f3_b")

        u_suffix = str(time.time_ns())[-6:]
        ctrl_a.register(f"f3a_{u_suffix}@cci.local", f"f3alice_{u_suffix}", "SecretPass123!")
        ctrl_b.register(f"f3b_{u_suffix}@cci.local", f"f3bob_{u_suffix}", "SecretPass123!")
        _wait_until(lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(), timeout=5.0)

        comm = ctrl_a.create_community("Fase 3 Presence Hub", "Live game state", visibility="private")
        cid = comm["community"]["id"]
        inv = ctrl_a.create_invitation(cid)
        ctrl_b.join_by_invitation(inv["code"])
        _wait_until(lambda: ctrl_b.active_channel is not None, timeout=4.0)

        # Estado invisible oculta presencia y juego a otros miembros
        ctrl_a.set_status("invisible", activity_visibility="communities")
        ctrl_a.report_game_activity("started", game_id="mslug2", title="Metal Slug 2")
        pres_for_b = ctrl_b.api.get_presences([ctrl_a.session.user_id])
        self.assertEqual(pres_for_b[ctrl_a.session.user_id]["status"], "offline")
        self.assertIsNone(pres_for_b[ctrl_a.session.user_id].get("activity_title"))

        # Volver online + privacidad visible muestra juego a B y genera feed deduplicado
        ctrl_a.set_status("online", activity_visibility="communities")
        ctrl_a.report_game_activity("started", game_id="mslug2", title="Metal Slug 2")
        # Evento duplicado consecutivo no debe crear doble fila en feed
        ctrl_a.report_game_activity("started", game_id="mslug2", title="Metal Slug 2")

        pres_visible = ctrl_b.api.get_presences([ctrl_a.session.user_id])[ctrl_a.session.user_id]
        self.assertEqual(pres_visible["status"], "online")
        self.assertEqual(pres_visible["activity_title"], "Metal Slug 2")

        feed = ctrl_b.api.get_activity_feed(limit=20)
        mslug_starts = [
            e for e in feed
            if e["user_id"] == ctrl_a.session.user_id and e["event_type"] == "activity.game.started"
        ]
        self.assertEqual(len(mslug_starts), 1)

        # Detener juego limpia actividad
        ctrl_a.report_game_activity("stopped", game_id="mslug2", title="Metal Slug 2")
        pres_stopped = ctrl_b.api.get_presences([ctrl_a.session.user_id])[ctrl_a.session.user_id]
        self.assertIsNone(pres_stopped.get("activity_title"))

        # Privacidad "private" oculta actividad de juego incluso estando "dnd"
        ctrl_a.set_status("dnd", activity_visibility="private")
        ctrl_a.report_game_activity("started", game_id="mario64", title="Super Mario 64")
        pres_priv = ctrl_b.api.get_presences([ctrl_a.session.user_id])[ctrl_a.session.user_id]
        self.assertEqual(pres_priv["status"], "dnd")
        self.assertIsNone(pres_priv.get("activity_title"))

        # Expiración por TTL convierte presencia vencida en offline automáticamente en SQLite
        prev_ttl = os.environ.get("CCI_PRESENCE_TTL_SECONDS")
        try:
            os.environ["CCI_PRESENCE_TTL_SECONDS"] = "0.15"
            svc = CommunitiesService(CommunitiesRepository.get_instance())
            svc.set_user_presence(ctrl_a.session.user_id, status="online", activity_visibility="communities")
            svc.report_game_activity(
                ctrl_a.session.user_id,
                action="started",
                game_id="mslugx",
                title="Metal Slug X",
                visibility="communities",
            )
            time.sleep(0.25)
            expired = svc.list_user_presences([ctrl_a.session.user_id], viewer_id=ctrl_b.session.user_id)[
                ctrl_a.session.user_id
            ]
            self.assertEqual(expired["status"], "offline")
            self.assertIsNone(expired.get("activity_title"))
        finally:
            if prev_ttl is None:
                os.environ.pop("CCI_PRESENCE_TTL_SECONDS", None)
            else:
                os.environ["CCI_PRESENCE_TTL_SECONDS"] = prev_ttl

        # @mención real crea notificación persistida no leída y luego se marca leída
        ctrl_a.send_message(f"Hey @{ctrl_b.session.username} sale partida!")
        self.assertTrue(
            _wait_until(
                lambda: any(
                    n.get("kind") == "mention" and not n.get("is_read")
                    for n in ctrl_b.api.list_notifications()
                ),
                timeout=4.0,
            )
        )
        ctrl_b.mark_all_notifications_read()
        notifs_after = ctrl_b.api.list_notifications()
        self.assertEqual(sum(1 for n in notifs_after if not n.get("is_read")), 0)
        self.assertTrue(len(notifs_after) >= 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
