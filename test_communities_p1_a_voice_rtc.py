"""test_communities_p1_a_voice_rtc.py - Certificación E2E P1-A: Audio de voz real sobre LiveKit SFU.

Verifica con dos clientes independientes (`CommunityController` + `CommunitiesView`) y un servidor
LiveKit SFU real (`livekit-server`):
1. Token `/voice-token` conectado a `livekit.rtc.Room` y publicación de `LocalAudioTrack`.
2. Transmisión bidireccional real A -> B (440 Hz) y B -> A (660 Hz) recibida vía WebRTC AudioStream.
3. Mute de micrófono y Deafen (sordo) efectivos sobre el track RTC y cola de reproducción.
4. Permiso `voice.connect` sin `voice.speak` entra como solo-oyente (`can_publish=False`).
5. Fallback honesto a señalización si LiveKit SFU no está alcanzable.
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

from PySide6.QtWidgets import QApplication


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


class TestCommunitiesP1AVoiceRTC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p1a_voice_")
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
        assert lk_bin, "Se requiere livekit-server instalado para certificar P1-A WebRTC real"
        cls.lk_http_port = _free_port()
        cls.lk_tcp_port = _free_port()
        ice_base = 52000 + (os.getpid() % 50) * 30
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
                r = requests.get(f"{cls.api_url}/api/v1/communities/health", timeout=0.5)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "lk_proc", None) is not None:
            cls.lk_proc.terminate()
            try:
                cls.lk_proc.wait(timeout=3.0)
            except Exception:
                cls.lk_proc.kill()
        for k, v in cls._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            cls._tmp_dir.cleanup()
        except Exception:
            pass

    def _pump_until(self, predicate, timeout_s: float = 6.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.025)
        self.app.processEvents()
        return bool(predicate())

    def test_01_livekit_sfu_two_clients_bidirectional_audio_mute_deafen(self):
        import requests
        from backend.communities.desktop_client import CommunityController
        from omnidash_qt import CommunitiesView

        health = requests.get(f"{self.api_url}/api/v1/communities/health", timeout=2.0).json()
        self.assertEqual(health.get("livekit_media_plane"), "reachable")
        self.assertEqual(health.get("voice_media_transport"), "livekit_webrtc_ready")

        ctrl_a = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "rtc_a.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )
        ctrl_b = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "rtc_b.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )
        view_a = CommunitiesView(controller=ctrl_a, auto_connect=False)
        view_b = CommunitiesView(controller=ctrl_b, auto_connect=False)

        rx_lock = threading.Lock()
        rx_a_frames: list[tuple[str, np.ndarray]] = []
        rx_b_frames: list[tuple[str, np.ndarray]] = []

        ctrl_a.voice_engine.on_remote_audio_frame = lambda pid, pcm, _sr, _ch: rx_a_frames.append((pid, pcm))
        ctrl_b.voice_engine.on_remote_audio_frame = lambda pid, pcm, _sr, _ch: rx_b_frames.append((pid, pcm))

        try:
            sa = ctrl_a.register("rtc_a@cci.local", "rtc_alice", "RtcPass123!")
            sb = ctrl_b.register("rtc_b@cci.local", "rtc_bob", "RtcPass123!")

            opened = ctrl_a.create_community("Sala Audio Real", "LiveKit P1-A", "private")
            comm_id = str(opened["community"]["id"])
            voice_ch = next((c for c in opened["channels"] if c.get("type") == "voice"), None)
            if not voice_ch:
                voice_ch = ctrl_a.create_channel("voz-rtc", "voice", "Canal LiveKit")
            voice_id = str(voice_ch["id"])

            inv = ctrl_a.create_invitation(comm_id)
            ctrl_b.join_by_invitation(inv["code"])
            ctrl_b.open_community(comm_id)

            # Ambos se unen de forma asíncrona al mismo canal de voz
            ctrl_a.join_voice_channel_async(voice_id)
            ctrl_b.join_voice_channel_async(voice_id)

            both_media = self._pump_until(
                lambda: (
                    ctrl_a.voice_engine.media_transport_active
                    and ctrl_b.voice_engine.media_transport_active
                    and len(ctrl_a.voice_engine.list_participants()) >= 2
                    and len(ctrl_b.voice_engine.list_participants()) >= 2
                ),
                timeout_s=8.0,
            )
            self.assertTrue(both_media, "Ambos clientes debieron conectar audio WebRTC y verse en participantes")

            self.assertIn("Voz conectada", view_a.interior_view.right_panel.v_st.text())
            self.assertIn("Voz conectada", view_b.interior_view.right_panel.v_st.text())

            # 1) A -> B: tono real de 440 Hz sobre WebRTC
            for i in range(45):
                sent = ctrl_a.voice_engine.push_pcm_frame(_sine_frame(440.0, i))
                self.assertTrue(sent)
                self.app.processEvents()
                time.sleep(0.02)

            got_440 = self._pump_until(
                lambda: any(pid == sa.user_id and _rms(pcm) > 1500.0 for pid, pcm in list(rx_b_frames)),
                timeout_s=4.0,
            )
            self.assertTrue(got_440, "Bob debió recibir audio PCM decodificado desde Alice vía LiveKit SFU")
            loud_b = [pcm for pid, pcm in rx_b_frames if pid == sa.user_id and _rms(pcm) > 1500.0]
            self.assertGreater(len(loud_b), 0)
            merged_b = np.concatenate(loud_b[-4:])
            freq_b = _dominant_freq(merged_b)
            self.assertLess(abs(freq_b - 440.0), 40.0, f"Frecuencia esperada ~440Hz, recibida {freq_b}Hz")

            # 2) B -> A: tono real de 660 Hz sobre WebRTC
            rx_a_frames.clear()
            for i in range(45):
                self.assertTrue(ctrl_b.voice_engine.push_pcm_frame(_sine_frame(660.0, i)))
                self.app.processEvents()
                time.sleep(0.02)

            got_660 = self._pump_until(
                lambda: any(pid == sb.user_id and _rms(pcm) > 1500.0 for pid, pcm in list(rx_a_frames)),
                timeout_s=4.0,
            )
            self.assertTrue(got_660, "Alice debió recibir audio PCM decodificado desde Bob vía LiveKit SFU")
            loud_a = [pcm for pid, pcm in rx_a_frames if pid == sb.user_id and _rms(pcm) > 1500.0]
            freq_a = _dominant_freq(np.concatenate(loud_a[-4:]))
            self.assertLess(abs(freq_a - 660.0), 45.0, f"Frecuencia esperada ~660Hz, recibida {freq_a}Hz")

            # 3) Mute efectivo de Alice desde botón Qt: track RTC muteado y B deja de recibir audio fuerte
            view_a.interior_view.right_panel.mic_btn.click()
            self.app.processEvents()
            self.assertTrue(ctrl_a.voice_engine.is_muted)
            self.assertTrue(ctrl_a.voice_engine._local_track.muted)

            # Dejar drenar buffers y limpiar
            time.sleep(0.25)
            rx_b_frames.clear()
            for i in range(15):
                self.assertFalse(ctrl_a.voice_engine.push_pcm_frame(_sine_frame(440.0, i)))
                time.sleep(0.02)
            time.sleep(0.25)
            loud_while_muted = [pcm for pid, pcm in rx_b_frames if pid == sa.user_id and _rms(pcm) > 1000.0]
            self.assertEqual(loud_while_muted, [], "Bob no debe recibir voz mientras Alice está muteada")

            # Desmutear a Alice desde botón Qt
            view_a.interior_view.right_panel.mic_btn.click()
            self.app.processEvents()
            self.assertFalse(ctrl_a.voice_engine.is_muted)
            self.assertFalse(ctrl_a.voice_engine._local_track.muted)

            # 4) Deafen (Sordo) de Bob desde botón Qt: bloquea audio entrante y mutea su track saliente
            view_b.interior_view.right_panel.headset_btn.click()
            self.app.processEvents()
            self.assertTrue(ctrl_b.voice_engine.is_deafened)
            self.assertTrue(ctrl_b.voice_engine.is_muted)
            self.assertTrue(ctrl_b.voice_engine._local_track.muted)

            rx_b_frames.clear()
            for i in range(25):
                self.assertTrue(ctrl_a.voice_engine.push_pcm_frame(_sine_frame(440.0, i)))
                time.sleep(0.02)
            time.sleep(0.25)
            self.assertEqual(rx_b_frames, [], "Bob ensordecido no debe reproducir frames remotos")

            # Quitar sordo a Bob y confirmar recuperación de audio
            view_b.interior_view.right_panel.headset_btn.click()
            self.app.processEvents()
            self.assertFalse(ctrl_b.voice_engine.is_deafened)
            for i in range(35):
                ctrl_a.voice_engine.push_pcm_frame(_sine_frame(440.0, i))
                self.app.processEvents()
                time.sleep(0.02)
            recovered = self._pump_until(
                lambda: any(pid == sa.user_id and _rms(pcm) > 1500.0 for pid, pcm in list(rx_b_frames)),
                timeout_s=4.0,
            )
            self.assertTrue(recovered, "Bob debe volver a escuchar a Alice tras desactivar sordo")

            # 5) Cierre limpio
            ctrl_a.leave_voice_channel()
            ctrl_b.leave_voice_channel()
            self.app.processEvents()
            diag_a = ctrl_a.get_voice_diagnostics()
            self.assertFalse(diag_a["is_connected"])
            self.assertFalse(diag_a["media_transport_active"])
            self.assertIsNone(diag_a["latency_ms"])
            self.assertEqual(ctrl_a.voice_engine.list_participants(), [])
        finally:
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            view_a.close()
            view_b.close()

    def test_02_unreachable_sfu_fallback_and_listen_only_permission(self):
        from backend.communities.desktop_client import CommunityController
        from backend.communities.service import CommunitiesService

        svc = CommunitiesService.get_instance()
        ctrl_owner = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "ro_owner.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )
        ctrl_listener = CommunityController(
            api_url=self.api_url,
            session_path=Path(self._tmp_dir.name) / "ro_listener.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )
        try:
            so = ctrl_owner.register("ro_o@cci.local", "ro_owner", "Pass12345!")
            sl = ctrl_listener.register("ro_l@cci.local", "ro_listener", "Pass12345!")

            opened = ctrl_owner.create_community("Sala Solo Oyente", "Permisos RTC", "private")
            comm_id = str(opened["community"]["id"])
            v_ch = ctrl_owner.create_channel("voz-ro", "voice", "Voz controlada")
            v_id = str(v_ch["id"])
            inv = ctrl_owner.create_invitation(comm_id)
            ctrl_listener.join_by_invitation(inv["code"])

            # Asignar rol sin voice.speak al oyente
            ro_role = svc.create_role(
                comm_id,
                so.user_id,
                name="OyenteSinMicro",
                permissions=["messages.read", "voice.connect"],
            )
            mrec = svc.repo.get_member(comm_id, sl.user_id)
            for r in list(mrec.get("roles") or []):
                if r["id"] != ro_role["id"]:
                    svc.repo.remove_role_from_member(comm_id, sl.user_id, r["id"])
            svc.repo.assign_role_to_member(comm_id, sl.user_id, ro_role["id"])

            ctrl_listener.open_community(comm_id)
            st_ro = ctrl_listener.join_voice_channel(v_id)
            self.assertTrue(st_ro["connected"])
            self.assertTrue(st_ro["media_ready"])
            self.assertFalse(st_ro["can_publish"])
            self.assertFalse(ctrl_listener.voice_engine.push_pcm_frame(_sine_frame(440.0, 0)))

            # Simular SFU inalcanzable -> degradación honesta sin romper señalización
            dead_port = _free_port()
            os.environ["LIVEKIT_WS_URL"] = f"ws://127.0.0.1:{dead_port}"
            st_down = ctrl_owner.join_voice_channel(v_id)
            self.assertTrue(st_down["connected"])
            self.assertTrue(st_down["token_issued"])
            self.assertFalse(st_down["media_ready"])
            self.assertEqual(st_down["livekit_media_plane"], "unreachable")
        finally:
            os.environ["LIVEKIT_WS_URL"] = self.lk_ws_url
            ctrl_owner.shutdown()
            ctrl_listener.shutdown()


if __name__ == "__main__":
    unittest.main()
