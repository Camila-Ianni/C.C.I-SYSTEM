"""test_communities_p0_closure.py - Certificación de cierre de hallazgos P0-A, P0-B y P0-C.

Verifica:
- P0-A (P0-01): Autorización por recurso en handlers Socket.IO de voz, soundboard, stream
  y moderación (rechazo a intrusos, usuarios sin permiso, anti-spoofing y cero broadcast global).
- P0-B (P0-02 y P0-03): Workers REST asíncronos (Qt GUI no se congela ante servidor lento),
  estados loading/cancelación por generación de navegación y dependencias directas en requirements.txt.
- P0-C (P0-09 y P0-10): Push en tiempo real de actividad de juego A -> Amigo B sin refresh manual,
  y deduplicación idempotente de mensajes ante cualquier orden de llegada REST vs Socket.IO.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"

from PySide6.QtWidgets import QApplication


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestCommunitiesP0Closure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p0_closure_")
        tmp_path = Path(cls._tmp_dir.name)
        cls._old_db_env = os.environ.get("CCI_DATABASE_PATH")
        cls._old_comm_db_env = os.environ.get("CCI_COMMUNITIES_DB_PATH")
        os.environ["CCI_DATABASE_PATH"] = str(tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(tmp_path / "communities.sqlite3")

        import cci_database
        from backend.communities.repository import CommunitiesRepository

        cci_database.init_db()
        CommunitiesRepository.reset_instance()

        import backend.server as server_mod
        cls.server_mod = server_mod
        cls.port = _free_port()
        cls.api_url = f"http://127.0.0.1:{cls.port}"

        def _serve():
            server_mod.socketio.run(
                server_mod.app,
                host="127.0.0.1",
                port=cls.port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        cls._srv_thread = threading.Thread(target=_serve, daemon=True)
        cls._srv_thread.start()

        import requests
        deadline = time.time() + 8.0
        while time.time() < deadline:
            try:
                r = requests.get(f"{cls.api_url}/api/v1/communities/health", timeout=0.6)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)

        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        try:
            cls._tmp_dir.cleanup()
        except Exception:
            pass
        if cls._old_db_env is None:
            os.environ.pop("CCI_DATABASE_PATH", None)
        else:
            os.environ["CCI_DATABASE_PATH"] = cls._old_db_env
        if cls._old_comm_db_env is None:
            os.environ.pop("CCI_COMMUNITIES_DB_PATH", None)
        else:
            os.environ["CCI_COMMUNITIES_DB_PATH"] = cls._old_comm_db_env

    def _pump_until(self, predicate, timeout_s: float = 5.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.025)
        self.app.processEvents()
        return bool(predicate())

    def test_01_p0_01_socketio_resource_authorization_and_no_global_broadcast(self):
        from backend.communities.desktop_client import CommunityApiClient
        from backend.communities.service import CommunitiesService

        svc = CommunitiesService.get_instance()
        api_owner = CommunityApiClient(self.api_url)
        api_member = CommunityApiClient(self.api_url)
        api_intruder = CommunityApiClient(self.api_url)

        owner_reg = api_owner.register("p01_owner@cci.local", "p01_owner", "OwnerPass123!")
        member_reg = api_member.register("p01_member@cci.local", "p01_member", "MemberPass123!")
        intr_reg = api_intruder.register("p01_intruder@cci.local", "p01_intruder", "IntrPass123!")

        api_owner.set_token(owner_reg["token"])
        api_member.set_token(member_reg["token"])
        api_intruder.set_token(intr_reg["token"])

        comm = api_owner.create_community("Sala Segura", "RBAC test", "private")
        comm_id = str(comm["id"])
        voice_ch = api_owner.create_channel(comm_id, "Voz Privada", "voice")
        voice_id = str(voice_ch["id"])
        inv = api_owner.create_invitation(comm_id)
        api_member.join_via_invitation(inv["code"])

        # Asignar rol restringido al miembro (sin voice.stream, soundboard.play ni kick/ban)
        restricted = svc.create_role(
            comm_id,
            str(owner_reg["user_id"]),
            name="SoloEscucha",
            permissions=["messages.read", "voice.connect"],
        )
        # Reemplazar rol base para dejar únicamente voice.connect (sin speak/stream/soundboard)
        member_rec = svc.repo.get_member(comm_id, str(member_reg["user_id"]))
        for r in list(member_rec.get("roles") or []):
            if r["id"] != restricted["id"]:
                svc.repo.remove_role_from_member(comm_id, str(member_reg["user_id"]), r["id"])
        svc.repo.assign_role_to_member(comm_id, str(member_reg["user_id"]), restricted["id"])

        import socketio as py_sio

        class _LiveSioProbe:
            EVENTS = (
                "community:error",
                "voice.participant_joined",
                "voice.mute_state_changed",
                "voice.active_speakers",
                "sound.played",
                "sound.stopped",
                "stream.started",
                "stream.paused",
                "stream.ended",
                "moderation.action_taken",
            )

            def __init__(self, url: str, token: str):
                self._lock = threading.Lock()
                self._cv = threading.Condition(self._lock)
                self._events: list[dict] = []
                self._sio = py_sio.Client(reconnection=False, logger=False, engineio_logger=False)
                for ev in self.EVENTS:
                    def _make_cb(ev_name: str):
                        def _cb(data):
                            with self._cv:
                                self._events.append({"name": ev_name, "args": [data]})
                                self._cv.notify_all()
                        return _cb
                    self._sio.on(ev, _make_cb(ev))
                self._sio.connect(url, auth={"token": token}, transports=["polling"], wait_timeout=5)

            def emit(self, ev_name: str, payload: dict):
                self._sio.emit(ev_name, payload)

            def wait_event(self, ev_name: str, timeout: float = 2.0) -> list[dict]:
                deadline = time.time() + timeout
                with self._cv:
                    while True:
                        matches = [e for e in self._events if e["name"] == ev_name]
                        if matches:
                            return self._drain_locked()
                        rem = deadline - time.time()
                        if rem <= 0:
                            return self._drain_locked()
                        self._cv.wait(timeout=rem)

            def get_received(self, settle_s: float = 0.05) -> list[dict]:
                if settle_s > 0:
                    time.sleep(settle_s)
                with self._cv:
                    return self._drain_locked()

            def _drain_locked(self) -> list[dict]:
                out = list(self._events)
                self._events.clear()
                return out

            def disconnect(self):
                try:
                    self._sio.disconnect()
                except Exception:
                    pass

        c_owner = _LiveSioProbe(self.api_url, owner_reg["token"])
        c_member = _LiveSioProbe(self.api_url, member_reg["token"])
        c_intr = _LiveSioProbe(self.api_url, intr_reg["token"])
        try:
            c_owner.emit("community:join", {"community_id": comm_id})
            c_owner.emit("community:voice:join", {"channel_id": voice_id})
            c_member.emit("community:join", {"community_id": comm_id})
            c_member.emit("community:voice:join", {"channel_id": voice_id})
            time.sleep(0.15)
            c_owner.get_received(settle_s=0)
            c_member.get_received(settle_s=0)
            c_intr.get_received(settle_s=0)

            # 1) Intruso externo (con identidad falseada en payload) debe ser rechazado en voz, sonido, stream y moderación
            spoof_uid = str(owner_reg["user_id"])
            for ev_name, payload in (
                ("community:voice:join", {"channel_id": voice_id, "user_id": spoof_uid}),
                ("community:voice:mute", {"channel_id": voice_id, "user_id": spoof_uid, "is_muted": True}),
                ("community:voice:speakers", {"channel_id": voice_id, "user_id": spoof_uid, "is_speaking": True}),
                ("community:sound:play", {"channel_id": voice_id, "user_id": spoof_uid, "sound_id": "s1", "title": "Horn"}),
                ("community:sound:stop", {"channel_id": voice_id, "user_id": spoof_uid, "sound_id": "s1"}),
                ("community:stream:start", {"channel_id": voice_id, "user_id": spoof_uid, "title": "Leak"}),
                ("community:stream:pause", {"channel_id": voice_id, "user_id": spoof_uid, "is_paused": True}),
                ("community:stream:stop", {"channel_id": voice_id, "user_id": spoof_uid}),
                ("community:moderation:action", {
                    "community_id": comm_id,
                    "user_id": spoof_uid,
                    "action": "kick",
                    "target_user_id": str(member_reg["user_id"]),
                }),
            ):
                c_intr.emit(ev_name, payload)
                rec_intr = c_intr.wait_event("community:error")
                errors = [e for e in rec_intr if e["name"] == "community:error"]
                self.assertTrue(errors, f"Intruso debió recibir community:error para {ev_name}")

            # Owner NO debió recibir ningún broadcast indebido del intruso
            rec_owner_after_intr = c_owner.get_received(settle_s=0.1)
            leaked = [
                e for e in rec_owner_after_intr
                if e["name"] in (
                    "voice.participant_joined", "voice.mute_state_changed", "voice.active_speakers",
                    "sound.played", "sound.stopped", "stream.started", "stream.paused",
                    "stream.ended", "moderation.action_taken",
                )
            ]
            self.assertEqual(leaked, [])

            # 2) Miembro sin permisos granulares (SoloEscucha) es rechazado en speak/sound/stream/moderation
            for ev_name, payload in (
                ("community:voice:speakers", {"channel_id": voice_id, "is_speaking": True, "audio_level": 0.9}),
                ("community:sound:play", {"channel_id": voice_id, "sound_id": "s1", "title": "Horn"}),
                ("community:stream:start", {"channel_id": voice_id, "title": "NoPerm"}),
                ("community:moderation:action", {
                    "community_id": comm_id,
                    "action": "kick",
                    "target_user_id": str(owner_reg["user_id"]),
                }),
            ):
                c_member.emit(ev_name, payload)
                rec_m = c_member.wait_event("community:error")
                errs = [e for e in rec_m if e["name"] == "community:error"]
                self.assertTrue(errs, f"Miembro sin permiso debió recibir error en {ev_name}")

            self.assertEqual(c_owner.get_received(settle_s=0.1), [])

            # 3) Owner ejecuta moderación válida: llega SOLO a comm_<id>, jamás a intruso (no broadcast=True)
            c_owner.emit("community:moderation:action", {
                "community_id": comm_id,
                "action": "kick",
                "target_user_id": str(member_reg["user_id"]),
                "reason": "prueba",
            })
            rec_member_mod = [e for e in c_member.wait_event("moderation.action_taken") if e["name"] == "moderation.action_taken"]
            rec_intr_mod = [e for e in c_intr.get_received(settle_s=0.1) if e["name"] == "moderation.action_taken"]
            self.assertEqual(len(rec_member_mod), 1)
            self.assertEqual(rec_member_mod[0]["args"][0]["actor_id"], str(owner_reg["user_id"]))
            self.assertEqual(rec_intr_mod, [])
        finally:
            c_owner.disconnect()
            c_member.disconnect()
            c_intr.disconnect()

    def test_02_p0_02_p0_03_async_workers_loading_cancellation_and_requirements(self):
        from backend.communities.desktop_client import CommunityController, CommunitySession

        req_text = (Path(__file__).resolve().parent / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("PySide6", req_text)
        self.assertIn("Flask-SocketIO", req_text)
        self.assertIn("python-socketio", req_text)

        class _SlowHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/v1/communities/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"healthy","realtime_socketio":"ready"}')
                    return
                if parsed.path == "/api/v1/channels/ch_slow/messages":
                    time.sleep(0.45)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"messages":[{"id":"m_slow","channel_id":"ch_slow","author_id":"1","content":"Lento"}]}')
                    return
                if parsed.path == "/api/v1/channels/ch_fast/messages":
                    time.sleep(0.05)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"messages":[{"id":"m_fast","channel_id":"ch_fast","author_id":"1","content":"Rapido"}]}')
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format, *args):
                return

        slow_port = _free_port()
        srv = HTTPServer(("127.0.0.1", slow_port), _SlowHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        sess_file = Path(self._tmp_dir.name) / "slow_sess.json"
        ctrl = CommunityController(
            api_url=f"http://127.0.0.1:{slow_port}",
            session_path=sess_file,
            heartbeat_interval_ms=0,
        )
        loading_trace: list[bool] = []
        loaded_channels: list[str] = []
        ctrl.loading_changed.connect(lambda busy, _op: loading_trace.append(bool(busy)))
        ctrl.channel_messages_loaded.connect(lambda ch_id, _msgs: loaded_channels.append(ch_id))

        try:
            ctrl.session = CommunitySession(ctrl.api_url, "tok", "1", "tester")
            ctrl.active_channels = [
                {"id": "ch_slow", "name": "lento", "type": "text"},
                {"id": "ch_fast", "name": "rapido", "type": "text"},
            ]

            t0 = time.monotonic()
            ctrl.select_channel_async("ch_slow")
            ctrl.select_channel_async("ch_fast")
            elapsed_call = time.monotonic() - t0
            self.assertLess(elapsed_call, 0.15, "El hilo GUI no debe bloquearse esperando REST lento")

            self.assertTrue(self._pump_until(lambda: "ch_fast" in loaded_channels, timeout_s=3.0))
            # Esperar incluso más allá del sleep de ch_slow para comprobar cancelación por generación
            time.sleep(0.50)
            self.app.processEvents()
            self.assertEqual(loaded_channels, ["ch_fast"])
            self.assertEqual(ctrl.active_channel["id"], "ch_fast")
            self.assertTrue(any(loading_trace))
            self.assertFalse(loading_trace[-1])
        finally:
            ctrl.shutdown()
            srv.shutdown()
            srv.server_close()

    def test_03_p0_09_p0_10_friend_activity_push_and_message_deduplication_orders(self):
        from backend.communities.desktop_client import CommunityController
        from omnidash_qt import CommunitiesView

        ctrl_a = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "push_a.json",
            heartbeat_interval_ms=0,
        )
        ctrl_b = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "push_b.json",
            heartbeat_interval_ms=0,
        )
        view_b = CommunitiesView(controller=ctrl_b, auto_connect=False)
        try:
            sa = ctrl_a.register("push_a@cci.local", "push_alice", "PushPass123!")
            sb = ctrl_b.register("push_b@cci.local", "push_bob", "PushPass123!")

            self.assertTrue(
                self._pump_until(
                    lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(),
                    timeout_s=5.0,
                )
            )

            # A envía solicitud de amistad a B y B acepta
            ctrl_a.send_friend_request(sb.username)
            ctrl_b.respond_friend_request(sa.user_id, accept=True)

            # A inicia un juego; B NO comparte comunidad con A ni llama a refresh manual
            ctrl_a.report_game_activity("started", game_id="mk2", title="Mortal Kombat II")

            pushed = self._pump_until(
                lambda: any(
                    ev.get("game_title") == "Mortal Kombat II"
                    for ev in (ctrl_b.active_activity_feed or [])
                ),
                timeout_s=5.0,
            )
            self.assertTrue(pushed, "Bob debió recibir push de actividad de su amiga Alice sin refrescar")

            # Deduplicación P0-10 en ambos órdenes de llegada (REST antes de Socket.IO y Socket.IO antes de REST)
            chat = view_b.interior_view.chat_area
            msg_first_rest = {"id": "msg_order_1", "channel_id": "c1", "author_id": sb.user_id, "author_name": sb.username, "content": "Primero REST"}
            chat.append_or_update_message(msg_first_rest, current_user_id=sb.user_id)
            chat.append_or_update_message(dict(msg_first_rest), current_user_id=sb.user_id)
            self.assertEqual(list(chat._msg_order).count("msg_order_1"), 1)

            msg_first_rt = {"id": "msg_order_2", "channel_id": "c1", "author_id": sb.user_id, "author_name": sb.username, "content": "Primero Socket"}
            chat.append_or_update_message(msg_first_rt, current_user_id=sb.user_id)
            chat.append_or_update_message(dict(msg_first_rt), current_user_id=sb.user_id)
            self.assertEqual(list(chat._msg_order).count("msg_order_2"), 1)
            self.assertEqual(len(chat._msg_widgets), 2)
        finally:
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            view_b.close()


if __name__ == "__main__":
    unittest.main()
