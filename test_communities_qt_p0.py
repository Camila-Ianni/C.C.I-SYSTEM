"""test_communities_qt_p0.py - Pruebas de verificación real P0 para C.C.I. Communities Desktop (Qt).

Cubre:
- Fase 0 / CCI-08: Propagación honesta de errores en groups_ui.py (sin falsos éxitos).
- P0.1: Conexión real PySide6 <-> Backend Flask + Socket.IO + SQLite con auth JWT, aislamiento entre usuarios,
  creación de comunidad privada, invitaciones por código, creación de canal, envío y recepción Socket.IO
  en tiempo real, persistencia tras reconexión y estado explícito cuando el backend está offline.
- P0.2: Estado honesto de voz/LiveKit sin peers ficticios, sin simulación automática ni toggle LIVE falso.
- Smoke check offscreen de OmniDashMainWindow sin identidad hardcodeada u_alex / ALEX.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Asegurar modo offscreen ANTES de importar PySide6 / widgets
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"

from PySide6.QtWidgets import QApplication


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestCommunitiesQtP0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_qt_p0_")
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
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        cls._srv_thread = threading.Thread(target=_serve, daemon=True)
        cls._srv_thread.start()

        import requests
        deadline = time.time() + 10.0
        ready = False
        while time.time() < deadline:
            try:
                resp = requests.get(f"{cls.api_url}/api/v1/health", timeout=0.5)
                if resp.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.1)
        if not ready:
            raise RuntimeError("No se pudo iniciar backend local Flask+SocketIO para test P0.")

        cls.app = QApplication.instance() or QApplication(sys.argv)

    @classmethod
    def tearDownClass(cls):
        from backend.communities.repository import CommunitiesRepository
        CommunitiesRepository.reset_instance()
        if cls._old_db_env is None:
            os.environ.pop("CCI_DATABASE_PATH", None)
        else:
            os.environ["CCI_DATABASE_PATH"] = cls._old_db_env
        if cls._old_comm_db_env is None:
            os.environ.pop("CCI_COMMUNITIES_DB_PATH", None)
        else:
            os.environ["CCI_COMMUNITIES_DB_PATH"] = cls._old_comm_db_env
        cls._tmp_dir.cleanup()

    def tearDown(self):
        import gc
        self.app.processEvents()
        gc.collect()

    def _pump_events_until(self, predicate, timeout_s: float = 4.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.03)
        self.app.processEvents()
        return bool(predicate())

    def test_01_backend_offline_error_and_no_demo_fallback(self):
        from backend.communities.desktop_client import CommunityApiError, CommunityController
        from omnidash_qt import CommunitiesView

        closed_port = _free_port()
        sess_file = Path(self._tmp_dir.name) / "offline_sess.json"
        ctrl = CommunityController(api_url=f"http://127.0.0.1:{closed_port}", session_path=sess_file)
        view = CommunitiesView(controller=ctrl, auto_connect=False)
        try:
            ok, msg = ctrl.check_backend(auto_start=False)
            self.assertFalse(ok)
            self.assertTrue(bool(msg))
            self.app.processEvents()
            self.assertIn("sin conexión", view.auth_view.backend_lbl.text().lower())
            self.assertEqual(view.internal_stack.currentWidget(), view.auth_view)

            view.auth_view.login_identifier.setText("nadie@test.local")
            view.auth_view.login_password.setText("Password123")
            view.auth_view.login_btn.click()
            self.assertTrue(
                self._pump_events_until(lambda: not view.auth_view.error_lbl.isHidden(), timeout_s=4.0)
            )

            self.assertFalse(view.auth_view.error_lbl.isHidden())
            self.assertIn("disponible", view.auth_view.error_lbl.text().lower())
            self.assertIsNone(ctrl.session)
            self.assertEqual(view.internal_stack.currentWidget(), view.auth_view)
            with self.assertRaises(CommunityApiError):
                ctrl.refresh_communities()
        finally:
            ctrl.shutdown()
            view.close()
            view.deleteLater()
            self.app.processEvents()

    def test_02_two_users_e2e_auth_invite_realtime_chat_and_persistence(self):
        from backend.communities.desktop_client import CommunityController
        from omnidash_qt import CommunitiesView

        sess_a = Path(self._tmp_dir.name) / "sess_alice.json"
        sess_b = Path(self._tmp_dir.name) / "sess_bob.json"

        ctrl_a = CommunityController(api_url=self.api_url, session_path=sess_a)
        ctrl_b = CommunityController(api_url=self.api_url, session_path=sess_b)
        view_a = CommunitiesView(controller=ctrl_a, auto_connect=False)
        view_b = CommunitiesView(controller=ctrl_b, auto_connect=False)

        try:
            # 1) Registro de Alice vía widgets Qt reales
            view_a.auth_view.set_mode("register")
            view_a.auth_view.reg_email.setText("alice@cci.local")
            view_a.auth_view.reg_username.setText("Alice")
            view_a.auth_view.reg_password.setText("AlicePass123!")
            view_a.auth_view.reg_btn.click()
            self.assertTrue(
                self._pump_events_until(
                    lambda: ctrl_a.session is not None
                    and view_a.internal_stack.currentWidget() == view_a.explore_view
                    and view_a.auth_view.reg_btn.isEnabled(),
                    timeout_s=4.0,
                )
            )

            self.assertIsNotNone(ctrl_a.session)
            self.assertTrue(sess_a.exists())
            self.assertEqual(view_a.internal_stack.currentWidget(), view_a.explore_view)
            self.assertEqual(ctrl_a.my_communities, [])

            # 2) Alice crea comunidad privada e invitación real
            opened = ctrl_a.create_community("Liga Retro", "Comunidad privada real", "private")
            comm_id = str(opened["community"]["id"])
            self.assertEqual(view_a.internal_stack.currentWidget(), view_a.interior_view)
            self.assertIn(comm_id, view_a.interior_view.rail.items)

            inv = ctrl_a.create_invitation(comm_id)
            code = str(inv["code"])
            self.assertTrue(bool(code))

            # 3) Persistencia de sesión tras reiniciar controller
            ctrl_a_restored = CommunityController(api_url=self.api_url, session_path=sess_a)
            try:
                restored_sess = ctrl_a_restored.restore_session()
                self.assertIsNotNone(restored_sess)
                self.assertEqual(restored_sess.user_id, ctrl_a.session.user_id)
                mine_restored, _ = ctrl_a_restored.refresh_communities()
                self.assertTrue(any(c["id"] == comm_id for c in mine_restored))
            finally:
                ctrl_a_restored.realtime.disconnect_sync()

            # 4) Registro de Bob: NO debe ver la comunidad privada de Alice
            view_b.auth_view.set_mode("register")
            view_b.auth_view.reg_email.setText("bob@cci.local")
            view_b.auth_view.reg_username.setText("Bob")
            view_b.auth_view.reg_password.setText("BobPass123!")
            view_b.auth_view.reg_btn.click()
            self.assertTrue(
                self._pump_events_until(
                    lambda: ctrl_b.session is not None and view_b.auth_view.reg_btn.isEnabled(),
                    timeout_s=4.0,
                )
            )

            self.assertIsNotNone(ctrl_b.session)
            bob_mine, bob_pub = ctrl_b.refresh_communities()
            self.assertFalse(any(c["id"] == comm_id for c in bob_mine))
            self.assertFalse(any(c["id"] == comm_id for c in bob_pub))

            # 5) Bob se une mediante el código de invitación real
            ctrl_b.join_by_invitation(f"cci://invite/{code}")
            self.app.processEvents()
            self.assertEqual(view_b.internal_stack.currentWidget(), view_b.interior_view)

            # 6) Canal de texto compartido + Socket.IO en tiempo real sin refrescar
            torneos_ch = ctrl_a.create_channel("torneos", "text", "Sala E2E")
            torneos_id = str(torneos_ch["id"])
            ctrl_b.open_community(comm_id)
            ctrl_b.select_channel(torneos_id)

            rt_ready = self._pump_events_until(
                lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(),
                timeout_s=5.0,
            )
            self.assertTrue(rt_ready, "Ambos clientes Socket.IO debieron conectarse al servidor")

            view_a.interior_view.chat_area.msg_input.setText("Hola Bob en tiempo real!")
            view_a.interior_view.chat_area.send_btn.click()

            received = self._pump_events_until(
                lambda: any(
                    "Hola Bob en tiempo real!" in w.txt_lbl.text()
                    for w in view_b.interior_view.chat_area._msg_widgets.values()
                ),
                timeout_s=5.0,
            )
            self.assertTrue(received, "Bob debió recibir el mensaje por Socket.IO en tiempo real")

            # 7) Verificación de persistencia tras cerrar/reabrir canal
            msgs_after = ctrl_b.api.list_messages(torneos_id)
            self.assertTrue(any(m.get("content") == "Hola Bob en tiempo real!" for m in msgs_after))
        finally:
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            view_a.close()
            view_b.close()
            view_a.deleteLater()
            view_b.deleteLater()
            self.app.processEvents()

    def test_03_voice_honest_state_no_fake_peers_or_live_toggle(self):
        import requests
        from backend.communities.desktop_client import CommunityController
        from backend.communities.voice_engine import DesktopVoiceEngine
        from omnidash_qt import CommunitiesView

        # VoiceEngine ya no fabrica peers ni métricas estáticas simuladas
        engine = DesktopVoiceEngine()
        self.assertEqual(engine.list_participants(), [])
        diag = engine.get_diagnostics()
        self.assertIsNone(diag["latency_ms"])
        self.assertIsNone(diag["jitter_ms"])
        self.assertFalse(diag["media_transport_active"])

        # Health honesto de media plane
        health = requests.get(f"{self.api_url}/api/v1/health", timeout=2.0).json()
        self.assertEqual(health.get("livekit_sfu"), "ready")
        self.assertEqual(health.get("voice_media_transport"), "signaling_only")
        self.assertIn(health.get("livekit_media_plane"), ("reachable", "unreachable"))

        sess = Path(self._tmp_dir.name) / "sess_voice.json"
        ctrl = CommunityController(api_url=self.api_url, session_path=sess)
        view = CommunitiesView(controller=ctrl, auto_connect=False)
        try:
            ctrl.register("voice@cci.local", "VoiceTester", "VoicePass123!")
            opened = ctrl.create_community("Sala Voz", "Prueba P0.2", "public")
            voice_ch = next((c for c in opened["channels"] if c.get("type") == "voice"), None)
            if not voice_ch:
                voice_ch = ctrl.create_channel("voz-general", "voice", "Canal de voz")

            state = ctrl.join_voice_channel(str(voice_ch["id"]))
            self.app.processEvents()
            self.assertTrue(state["connected"])
            self.assertTrue(state["token_issued"])
            self.assertFalse(state["media_ready"])

            rp = view.interior_view.right_panel
            self.assertFalse(rp.voice_panel.isHidden())
            rp.screen_btn.click()
            self.app.processEvents()
            self.assertFalse(rp.screen_active)
        finally:
            ctrl.shutdown()
            view.close()
            view.deleteLater()
            self.app.processEvents()

    def test_04_groups_ui_no_false_success_on_errors(self):
        import groups_ui

        fake_service = MagicMock()
        fake_service.has_permission.return_value = False
        fake_service.authorize_sound_play.side_effect = LookupError("soundboard missing")
        fake_service.start_stream.side_effect = RuntimeError("SFU offline")
        fake_service.stop_stream.side_effect = RuntimeError("SFU offline")

        fake_repo = MagicMock()
        fake_repo.list_channels.return_value = [{"id": "ch_v", "name": "Voz", "type": "voice"}]

        bridge = object.__new__(groups_ui.CommunitiesUIBridge)
        bridge.user_id = "usr_test"
        bridge.service = fake_service
        bridge.repo = fake_repo
        bridge._resolve_community = lambda _slug: {"id": "comm_1", "name": "Test"}

        snd_res = bridge.trigger_soundboard("comm_1", "airhorn")
        self.assertEqual(snd_res.get("status"), "error")

        stream_res = bridge.start_live_stream("comm_1", "Voz", "Mi Stream")
        self.assertEqual(stream_res.get("status"), "error")
        self.assertIn("SFU offline", stream_res.get("message", ""))

        stopped = bridge.stop_live_stream("comm_1", channel_id="ch_v")
        self.assertFalse(stopped)

    def test_05_main_window_offscreen_smoke_no_hardcoded_alex(self):
        from omnidash_qt import OmniDashMainWindow

        win = OmniDashMainWindow(auto_connect=False)
        try:
            self.app.processEvents()
            self.assertNotIn("Alex", win.home_view.title_lbl.text())
            self.assertNotIn("Alex", win.home_view.pill_name_lbl.text())
            self.assertNotIn("Alex", win.nav_bar.nav_player_lbl.text())
            self.assertFalse(win.home_view._home_live_badge.isVisible())

            win.switch_view("COMMUNITY")
            self.app.processEvents()
            self.assertEqual(win.stack.currentIndex(), 4)
            self.assertEqual(
                win.communities_view.internal_stack.currentWidget(),
                win.communities_view.auth_view,
            )
            win.nav_bar.set_session_user("mimi")
            self.assertIn("@mimi", win.nav_bar.nav_player_lbl.text())
            self.assertNotIn("Alex", win.nav_bar.nav_player_lbl.text())
        finally:
            win.close()
            win.deleteLater()
            self.app.processEvents()

    def test_06_foreign_server_on_port_does_not_cause_404_on_register(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from backend.communities.desktop_client import CommunityController

        class _ForeignHealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/v1/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok","engine":"foreign-web"}')
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):
                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):
                return

        foreign_port = _free_port()
        foreign_srv = HTTPServer(("127.0.0.1", foreign_port), _ForeignHealthHandler)
        t = threading.Thread(target=foreign_srv.serve_forever, daemon=True)
        t.start()

        old_auto = os.environ.get("CCI_AUTO_START_BACKEND")
        sess_path = Path(self._tmp_dir.name) / "sess_foreign.json"
        ctrl = CommunityController(
            api_url=f"http://127.0.0.1:{foreign_port}",
            session_path=sess_path,
            heartbeat_interval_ms=0,
        )
        try:
            # Con auto_start=False NO debe dar falso positivo usando /api/v1/health ajeno
            ok_strict, msg_strict = ctrl.check_backend(auto_start=False)
            self.assertFalse(ok_strict)
            self.assertIn("communities/health", msg_strict)

            # Con auto_start=True debe detectar el puerto ocupado ajeno, levantar Communities en puerto libre y registrar real
            os.environ["CCI_AUTO_START_BACKEND"] = "1"
            ok_auto, _ = ctrl.check_backend(auto_start=True)
            self.assertTrue(ok_auto)
            self.assertNotEqual(ctrl.api_url, f"http://127.0.0.1:{foreign_port}")

            sess = ctrl.register("mimi_fallback@cci.local", "mimi_fb", "MimiPass123!")
            self.assertEqual(sess.username.upper(), "MIMI_FB")
            self.assertEqual(sess.api_url, ctrl.api_url)
        finally:
            ctrl.realtime.disconnect_sync()
            foreign_srv.shutdown()
            foreign_srv.server_close()
            if old_auto is None:
                os.environ.pop("CCI_AUTO_START_BACKEND", None)
            else:
                os.environ["CCI_AUTO_START_BACKEND"] = old_auto


if __name__ == "__main__":
    unittest.main()
