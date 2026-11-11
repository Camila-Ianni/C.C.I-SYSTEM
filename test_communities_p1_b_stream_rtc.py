"""test_communities_p1_b_stream_rtc.py - Certificación E2E P1-B: Streaming real de pantalla / juego sobre LiveKit SFU.

Verifica con dos clientes independientes (`CommunityController` + `CommunityInteriorView`) y un servidor
LiveKit SFU real (`livekit-server`):
1. Confirmación real de TrackPublishOptions (`SOURCE_SCREENSHARE` + `SOURCE_SCREENSHARE_AUDIO`) antes de activar estado LIVE.
2. Transmisión real de video RGBA (patrón de colores + captura Qt `QWidget.grab()`) vía WebRTC VideoStream y
   audio de pantalla/juego (`770 Hz` PCM) recibidos en el visor remoto `StreamStageWidget`.
3. Detención limpia con `unpublish_track`, cierre de sesión en backend y limpieza de estado LIVE vía `stream.ended`.
4. Reglas fail-closed: prohibido activar LIVE si SFU no está disponible o falla publicación (incluye rollback en backend),
   y bloqueo RBAC 403 sin permiso `voice.stream`.
"""
from __future__ import annotations

import math
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"
os.environ["CCI_DISABLE_AUDIO_IO"] = "1"

from PySide6.QtWidgets import QApplication, QWidget


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _sine_frame(freq_hz: float, frame_idx: int, amp: float = 14000.0, samples: int = 960, sr: int = 48000) -> np.ndarray:
    t = (np.arange(samples, dtype=np.float64) + frame_idx * samples) / float(sr)
    return (amp * np.sin(2.0 * math.pi * freq_hz * t)).astype(np.int16)


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def _dominant_freq(samples: np.ndarray, sr: int = 48000) -> float:
    if samples.size < 64:
        return 0.0
    spec = np.abs(np.fft.rfft(samples.astype(np.float64)))
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / sr)
    spec[0] = 0.0
    return float(freqs[int(np.argmax(spec))])


def _make_split_test_frame(width: int = 320, height: int = 180) -> bytes:
    """Genera frame RGBA verificable: mitad superior cian (0, 210, 255) y mitad inferior magenta (255, 40, 180)."""
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    half = height // 2
    arr[:half, :, :] = [0, 210, 255, 255]
    arr[half:, :, :] = [255, 40, 180, 255]
    return arr.tobytes()


class TestCommunitiesP1BStreamRTC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p1b_stream_")
        tmp_path = Path(cls._tmp_dir.name)

        cls._old_env = {
            k: os.environ.get(k)
            for k in (
                "CCI_DATABASE_PATH",
                "CCI_COMMUNITIES_DB_PATH",
                "LIVEKIT_WS_URL",
                "LIVEKIT_API_KEY",
                "LIVEKIT_API_SECRET",
            )
        }
        os.environ["CCI_DATABASE_PATH"] = str(tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(tmp_path / "communities.sqlite3")
        os.environ["LIVEKIT_API_KEY"] = "devkey"
        os.environ["LIVEKIT_API_SECRET"] = "secretkey1234567890abcdef"

        lk_bin = shutil.which("livekit-server")
        assert lk_bin, "Se requiere livekit-server instalado para certificar P1-B WebRTC real"
        cls.lk_http_port = _free_port()
        cls.lk_tcp_port = _free_port()
        ice_base = 54000 + (os.getpid() % 50) * 30
        cfg_body = (
            f"port: {cls.lk_http_port}\n"
            f"rtc:\n"
            f"  tcp_port: {cls.lk_tcp_port}\n"
            f"  port_range_start: {ice_base}\n"
            f"  port_range_end: {ice_base + 20}\n"
            f"  use_external_ip: false\n"
            f"keys:\n"
            f"  devkey: secretkey1234567890abcdef\n"
        )
        cls.lk_proc = subprocess.Popen(
            [
                lk_bin,
                "--dev",
                "--bind", "127.0.0.1",
                "--node-ip", "127.0.0.1",
                "--config-body", cfg_body,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 6.0
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", cls.lk_http_port), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.1)

        cls.lk_ws_url = f"ws://127.0.0.1:{cls.lk_http_port}"
        os.environ["LIVEKIT_WS_URL"] = cls.lk_ws_url

        import cci_database
        from backend.communities.repository import CommunitiesRepository
        cci_database.init_db()
        CommunitiesRepository.reset_instance()

        import backend.server as server_mod
        cls.server_port = _free_port()
        cls.api_url = f"http://127.0.0.1:{cls.server_port}"

        def _serve():
            server_mod.socketio.run(
                server_mod.app,
                host="127.0.0.1",
                port=cls.server_port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        threading.Thread(target=_serve, daemon=True).start()
        import requests
        deadline = time.time() + 8.0
        while time.time() < deadline:
            try:
                r = requests.get(f"{cls.api_url}/api/v1/health", timeout=0.5)
                if r.status_code == 200 and r.json().get("livekit_media_plane") == "reachable":
                    break
            except Exception:
                pass
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.lk_proc.terminate()
            cls.lk_proc.wait(timeout=3)
        except Exception:
            try:
                cls.lk_proc.kill()
            except Exception:
                pass
        from backend.communities.repository import CommunitiesRepository
        CommunitiesRepository.reset_instance()
        for k, prev in cls._old_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev
        cls._tmp_dir.cleanup()

    def _pump(self, seconds: float = 0.05) -> None:
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def _new_controller(self, suffix: str):
        from backend.communities.desktop_client import CommunityController
        sess_path = Path(self._tmp_dir.name) / f"sess_{suffix}.json"
        ctrl = CommunityController(
            api_url=self.api_url,
            session_path=sess_path,
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )
        return ctrl

    def _register_and_connect_pair(self, tag: str):
        ctrl_a = self._new_controller(f"{tag}_a")
        ctrl_b = self._new_controller(f"{tag}_b")

        ctrl_a.register(f"str_{tag}@cci.test", f"str_{tag}", "StrPass123!")
        ctrl_b.register(f"vwr_{tag}@cci.test", f"vwr_{tag}", "StrPass123!")

        opened = ctrl_a.create_community(f"Arena {tag}", "Streaming P1-B", "public")
        comm = opened["community"]
        comm_id = str(comm["id"])
        voice_ch = next((c for c in opened["channels"] if c.get("type") == "voice"), None)
        if not voice_ch:
            voice_ch = ctrl_a.create_channel(f"stage-{tag}", "voice", "Streaming LiveKit")
        inv = ctrl_a.create_invitation(comm_id)
        ctrl_b.join_by_invitation(inv["code"])

        ctrl_a.open_community(comm_id)
        ctrl_b.open_community(comm_id)

        ctrl_a.join_voice_channel(voice_ch["id"], enable_audio_io=False)
        ctrl_b.join_voice_channel(voice_ch["id"], enable_audio_io=False)

        deadline = time.time() + 6.0
        while time.time() < deadline:
            self._pump(0.03)
            if (
                ctrl_a.voice_engine.media_transport_active
                and ctrl_b.voice_engine.media_transport_active
                and len(ctrl_a.voice_engine.list_participants()) >= 2
                and len(ctrl_b.voice_engine.list_participants()) >= 2
            ):
                break
        return ctrl_a, ctrl_b, comm, voice_ch

    def test_01_real_screen_video_and_audio_e2e_qt(self):
        from omnidash_qt import CommunityInteriorView

        ctrl_a, ctrl_b, _comm, voice_ch = self._register_and_connect_pair("s1")
        view_a = CommunityInteriorView(ctrl_a)
        view_b = CommunityInteriorView(ctrl_b)

        try:
            view_a.show()
            view_b.show()
            ctrl_a._on_voice_engine_state_changed(ctrl_a.voice_engine.get_diagnostics())
            ctrl_b._on_voice_engine_state_changed(ctrl_b.voice_engine.get_diagnostics())
            self._pump(0.08)

            # Estado inicial: sin LIVE simulado y visor oculto
            self.assertFalse(view_a.right_panel.screen_active)
            self.assertFalse(view_a.right_panel.v_live_badge.isVisible())
            self.assertFalse(view_a.chat_area.stream_stage.isVisible())
            self.assertFalse(view_b.chat_area.stream_stage.isVisible())

            rx_screen_audio: list[np.ndarray] = []
            ctrl_b.voice_engine.on_remote_screen_audio_frame = (
                lambda _pid, pcm, _sr, _ch: rx_screen_audio.append(pcm.copy())
            )

            pattern_rgba = _make_split_test_frame(1280, 720)
            frame_counter = {"n": 0}

            def _provider():
                frame_counter["n"] += 1
                return (1280, 720, pattern_rgba)

            # Publicar pantalla real (720p @ 30fps + audio 770Hz) con track confirmado en LiveKit SFU
            st = ctrl_a.start_screen_share(
                channel_id=voice_ch["id"],
                source_id="screen:0",
                resolution="720p",
                fps=30,
                bitrate_kbps=2500,
                with_audio=True,
                title="Gameplay Test 770Hz",
                frame_provider=_provider,
            )
            self.assertTrue(st["live"])
            self.assertTrue(ctrl_a.voice_engine.is_screen_sharing)
            self.assertIsNotNone(getattr(ctrl_a.voice_engine._video_pub, "sid", None))
            self.assertIsNotNone(getattr(ctrl_a.voice_engine._screen_audio_pub, "sid", None))

            # Evitar que el QTimer sobreescriba con widget capture durante este test controlado
            view_a._screen_capture_timer.stop()
            self._pump(0.1)

            self.assertTrue(view_a.right_panel.screen_active)
            self.assertTrue(view_a.right_panel.v_live_badge.isVisible())
            self.assertTrue(view_a.chat_area.stream_stage.isVisible())
            self.assertTrue(view_a.chat_area.stream_stage.live_badge.isVisible())

            # Enviar frames de video y audio 770 Hz hasta que view_b renderice frames decodificados por WebRTC
            idx = 0
            deadline = time.time() + 10.0
            while time.time() < deadline:
                ctrl_a.push_screen_video_frame(1280, 720, pattern_rgba)
                ctrl_a.push_screen_audio_frame(_sine_frame(770.0, idx))
                idx += 1
                self._pump(0.04)
                if (
                    view_b.chat_area.stream_stage.frames_rendered >= 3
                    and len(rx_screen_audio) >= 5
                ):
                    break

            self.assertGreaterEqual(ctrl_a.voice_engine.screen_tx_frames, 2)
            self.assertGreaterEqual(ctrl_b.voice_engine.screen_rx_frames, 2)
            self.assertGreaterEqual(view_b.chat_area.stream_stage.frames_rendered, 2)
            self.assertTrue(view_b.chat_area.stream_stage.isVisible())
            self.assertIsNotNone(view_b.chat_area.stream_stage.last_frame_rgba)

            # Verificar contenido real de píxeles tras encode VP8 + decode RGBA en LiveKit SFU
            rw, rh = view_b.chat_area.stream_stage.last_frame_size
            rgba_rx = np.frombuffer(
                view_b.chat_area.stream_stage.last_frame_rgba, dtype=np.uint8
            ).reshape((rh, rw, 4))
            top_rgb = rgba_rx[: rh // 3, :, :3].mean(axis=(0, 1))
            bot_rgb = rgba_rx[(2 * rh) // 3 :, :, :3].mean(axis=(0, 1))
            # Mitad superior debe ser cian (B > 170, G > 140, R < 90)
            self.assertGreater(top_rgb[2], 170.0)
            self.assertGreater(top_rgb[1], 140.0)
            self.assertLess(top_rgb[0], 90.0)
            # Mitad inferior debe ser magenta (R > 170, B > 120, G < 100)
            self.assertGreater(bot_rgb[0], 170.0)
            self.assertGreater(bot_rgb[2], 120.0)
            self.assertLess(bot_rgb[1], 100.0)

            # Verificar audio de pantalla real (770 Hz)
            combined_audio = np.concatenate(rx_screen_audio[-5:])
            self.assertGreater(_rms(combined_audio), 1500.0)
            self.assertAlmostEqual(_dominant_freq(combined_audio), 770.0, delta=35.0)

            # Verificar stream listado en backend
            active_streams = ctrl_b.api.list_active_streams()
            self.assertTrue(any(s.get("channel_id") == voice_ch["id"] for s in active_streams))

            # Detener stream -> limpia LIVE en emisor, backend y espectador
            ctrl_a.stop_screen_share()
            deadline = time.time() + 4.0
            while time.time() < deadline:
                self._pump(0.03)
                if (
                    not view_a.right_panel.screen_active
                    and not view_a.right_panel.v_live_badge.isVisible()
                    and not view_b.chat_area.stream_stage.isVisible()
                ):
                    break

            self.assertFalse(ctrl_a.voice_engine.is_screen_sharing)
            self.assertFalse(view_a.right_panel.screen_active)
            self.assertFalse(view_a.right_panel.v_live_badge.isVisible())
            self.assertFalse(view_b.chat_area.stream_stage.isVisible())
            self.assertEqual(ctrl_a.api.list_active_streams(), [])
        finally:
            view_a._screen_capture_timer.stop()
            view_b._screen_capture_timer.stop()
            view_a.close()
            view_b.close()
            ctrl_a.shutdown()
            ctrl_b.shutdown()

    def test_02_qt_widget_grab_capture_transmits_real_frames(self):
        from backend.communities.stream_adapter import capture_source_rgba

        ctrl_a, ctrl_b, _comm, voice_ch = self._register_and_connect_pair("s2")
        demo_win = QWidget()
        demo_win.resize(320, 180)
        demo_win.setStyleSheet("background-color: rgb(30, 180, 90);")
        demo_win.show()
        self._pump(0.05)

        try:
            captured = capture_source_rgba(
                "window:omnidash",
                target_width=1280,
                target_height=720,
                window_widget=demo_win,
            )
            self.assertIsNotNone(captured)
            cw, ch, _ = captured
            self.assertEqual((cw, ch), (1280, 720))

            st = ctrl_a.start_screen_share(
                channel_id=voice_ch["id"],
                source_id="window:omnidash",
                resolution="720p",
                fps=30,
                with_audio=False,
                window_widget=demo_win,
            )
            self.assertTrue(st["live"])

            deadline = time.time() + 8.0
            while time.time() < deadline:
                fr = capture_source_rgba("window:omnidash", 1280, 720, window_widget=demo_win)
                if fr is not None:
                    ctrl_a.push_screen_video_frame(*fr)
                self._pump(0.05)
                latest = ctrl_b.voice_engine.get_latest_remote_video_frame()
                if latest is not None and ctrl_b.voice_engine.screen_rx_frames >= 2:
                    break

            latest = ctrl_b.voice_engine.get_latest_remote_video_frame()
            self.assertIsNotNone(latest)
            _pid, rw, rh, rgba_bytes = latest
            arr = np.frombuffer(rgba_bytes, dtype=np.uint8).reshape((rh, rw, 4))
            mean_rgb = arr[:, :, :3].mean(axis=(0, 1))
            # Verde dominante (30, 180, 90) preservado tras transporte WebRTC
            self.assertGreater(mean_rgb[1], 130.0)
            self.assertLess(mean_rgb[0], 80.0)
        finally:
            demo_win.close()
            ctrl_a.shutdown()
            ctrl_b.shutdown()

    def test_03_fail_closed_when_sfu_unreachable_and_rollback_slot(self):
        from backend.communities.desktop_client import CommunityApiError
        from omnidash_qt import CommunityInteriorView

        ctrl = self._new_controller("s3_off")
        ctrl.register("off_s3@cci.test", "off_s3", "StrPass123!")
        opened = ctrl.create_community("Offline SFU Room", "Fail closed", "public")
        comm = opened["community"]
        voice_ch = next((c for c in opened["channels"] if c.get("type") == "voice"), None)
        if not voice_ch:
            voice_ch = ctrl.create_channel("voz-off", "voice", "Offline test")
        ctrl.open_community(comm["id"])

        # Conectar solo señalización simulando ausencia de transporte LiveKit SFU
        cred = ctrl.api.request_voice_token(voice_ch["id"])
        ctrl.active_voice_channel = voice_ch
        ctrl._active_voice_cred = cred
        ctrl._active_voice_reachable = False
        ctrl.voice_engine.connect(comm["id"], voice_ch["name"], token_info=None, enable_audio_io=False)

        view = CommunityInteriorView(ctrl)
        view._on_voice_state_changed(ctrl._build_voice_state(voice_ch, cred, False))
        try:
            self.assertFalse(ctrl.voice_engine.media_transport_active)
            # 1) Clic en screen_btn en modo sin SFU nunca activa LIVE
            view.right_panel.screen_btn.click()
            self._pump(0.05)
            self.assertFalse(view.right_panel.screen_active)
            self.assertFalse(view.right_panel.v_live_badge.isVisible())
            self.assertFalse(ctrl.voice_engine.is_screen_sharing)

            # 2) Llamada directa con fallo RTC tampoco deja LIVE y no abre sesión persistida
            with self.assertRaises(CommunityApiError):
                ctrl.start_screen_share(channel_id=voice_ch["id"])
            self.assertFalse(ctrl.voice_engine.is_screen_sharing)
            self.assertEqual(ctrl.api.list_active_streams(comm["id"]), [])

            # 3) Simular fallo durante publish_track después de crear sesión en backend -> rollback automático
            ctrl.join_voice_channel(voice_ch["id"], enable_audio_io=False)
            deadline = time.time() + 5.0
            while time.time() < deadline and not ctrl.voice_engine.media_transport_active:
                self._pump(0.03)
            self.assertTrue(ctrl.voice_engine.media_transport_active)

            orig_start = ctrl.voice_engine.start_screen_share
            ctrl.voice_engine.start_screen_share = lambda **_kw: False
            try:
                with self.assertRaises(CommunityApiError):
                    ctrl.start_screen_share(channel_id=voice_ch["id"])
                self.assertFalse(ctrl.voice_engine.is_screen_sharing)
                self.assertFalse(view.right_panel.screen_active)
                self.assertEqual(ctrl.api.list_active_streams(comm["id"]), [])
            finally:
                ctrl.voice_engine.start_screen_share = orig_start
        finally:
            view.close()
            ctrl.shutdown()

    def test_04_rbac_denies_stream_without_voice_stream_permission(self):
        from backend.communities.desktop_client import CommunityApiError
        from backend.communities.service import CommunitiesService

        ctrl_owner, ctrl_member, comm, voice_ch = self._register_and_connect_pair("s4")
        svc = CommunitiesService.get_instance()
        try:
            owner_id = ctrl_owner.session.user_id
            member_id = ctrl_member.session.user_id
            no_stream_role = svc.create_role(
                comm["id"],
                owner_id,
                name="VozSinStream",
                permissions=["messages.read", "voice.connect", "voice.speak"],
            )
            mrec = svc.repo.get_member(comm["id"], member_id)
            for r in list(mrec.get("roles") or []):
                if r["id"] != no_stream_role["id"]:
                    svc.repo.remove_role_from_member(comm["id"], member_id, r["id"])
            svc.repo.assign_role_to_member(comm["id"], member_id, no_stream_role["id"])

            with self.assertRaises(CommunityApiError) as ctx:
                ctrl_member.start_screen_share(channel_id=voice_ch["id"])
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertFalse(ctrl_member.voice_engine.is_screen_sharing)
            self.assertEqual(ctrl_owner.api.list_active_streams(comm["id"]), [])
        finally:
            ctrl_owner.shutdown()
            ctrl_member.shutdown()


if __name__ == "__main__":
    unittest.main()
