"""test_communities_p1_c_soundboard_rtc.py - Certificación E2E P1-C: Soundboard sobre el canal RTC.

Verifica con dos clientes independientes (`CommunityController` + `CommunityInteriorView`) y un servidor
LiveKit SFU real (`livekit-server`):
1. Al reproducir un efecto del soundboard (desde el panel Qt o controlador), el audio PCM se inyecta en
   el track RTC saliente y el peer remoto conectado al canal de voz lo recibe en tiempo real sin
   necesidad de micrófono activo.
2. Subida de archivo MP3 real, descarga autorizada vía `GET /api/v1/sounds/<id>/audio`, decodificación a
   PCM 48 kHz y transmisión real por LiveKit WebRTC al peer remoto.
3. Mezcla simultánea de micrófono (`440 Hz`) + efecto de soundboard (`990 Hz`) dentro del mismo track
   saliente verificada espectralmente en el peer remoto, y detención inmediata (`stop_soundboard_effect`).
4. Control estricto fail-closed: RBAC (`soundboard.play` -> 403), cooldown anti-spam (429) y respeto
   de mute/sordo sobre el track RTC.
"""
from __future__ import annotations

import base64
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

# Muestra MP3 MPEG-2 Layer III real (12.8KB en decodificación / 6.5KB raw frames, 0.65s, peak ~2120)
_REAL_MP3_B64 = (
    "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"
    "//OQcMoXCgc9L2cHbYCoAlysAAAAFKO/FSACEFZ5oABGGhNJZtmd5wnmlLzhUYnkNAS4R0DbwA6C/AGGFwowCIkBEekMMjpq6v////31JO6ST9///////////////0Ox0Rzf/EkGh4BhUk5df////9vdiTHViswfDxDHKO/R/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8AApe11teAAEoZIgSYaPAts"
    "//OQcP8drg0xP2olbgCoAlysAAAA7DS1MZxXAGA/zeBw2+eiKu+ChAgqt6gKWqG0NKnDNAwIRUDPVWau/sngSpmJAvGJDJBrv///////////////Eu48FTr3VVf//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wAAp9ciKLqZQISRNDFJCApd"
    "//OQcP8dpEslKmcYJgCoAlysAAAAmYVtydZp2Sttnu1gGJppmOKeIJCL+pFIPDhZwCHacX6bq60xne2CgIXbnxP53////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAAuRrBkKYsHOUwICkTqoaW"
    "//OQcP8doEsa0GMZJoCoAlysAAAAE+tvNa0UyGoaPkC6EhMmR9ZWl2FyJUPUzWxCv////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////4AA//////////////////////OQcP8dqEUWwGHvJoCoAlysAAAA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAA//////////////////////OQUP8doAEuAAAAAACoAlysAAAA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAA//////////////////////OQUP8doAEuAAAAAACoAlysAAAA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAA//////////////////////OQUP8doAEuAAAAAACoAlysAAAA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAA//////////////////////OQUP8doAEuAAAAAACoAlysAAAA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gAA////////////////////="
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _sine_frame(freq_hz: float, frame_idx: int, amp: float = 12000.0, samples: int = 960, sr: int = 48000) -> np.ndarray:
    t = (np.arange(samples, dtype=np.float64) + frame_idx * samples) / float(sr)
    return (amp * np.sin(2.0 * math.pi * freq_hz * t)).astype(np.int16)


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def _band_energy_ratio(samples: np.ndarray, target_hz: float, sr: int = 48000, tol_hz: float = 45.0) -> float:
    if samples.size < 256:
        return 0.0
    spec = np.abs(np.fft.rfft(samples.astype(np.float64)))
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / sr)
    spec[0] = 0.0
    total = float(np.sum(spec ** 2))
    if total <= 0.0:
        return 0.0
    mask = np.abs(freqs - target_hz) <= tol_hz
    band = float(np.sum(spec[mask] ** 2))
    return band / total


def _dominant_freq(samples: np.ndarray, sr: int = 48000) -> float:
    if samples.size < 256:
        return 0.0
    spec = np.abs(np.fft.rfft(samples.astype(np.float64)))
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / sr)
    spec[0] = 0.0
    return float(freqs[int(np.argmax(spec))])


class TestCommunitiesP1CSoundboardRTC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p1c_soundboard_")
        tmp_path = Path(cls._tmp_dir.name)
        cls._sounds_dir = tmp_path / "sounds_storage"
        cls._sounds_dir.mkdir(parents=True, exist_ok=True)

        cls._old_env = {
            k: os.environ.get(k)
            for k in (
                "CCI_DATABASE_PATH",
                "CCI_COMMUNITIES_DB_PATH",
                "CCI_SOUNDS_STORAGE_PATH",
                "LIVEKIT_WS_URL",
                "LIVEKIT_API_KEY",
                "LIVEKIT_API_SECRET",
            )
        }
        os.environ["CCI_DATABASE_PATH"] = str(tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(tmp_path / "communities.sqlite3")
        os.environ["CCI_SOUNDS_STORAGE_PATH"] = str(cls._sounds_dir)
        os.environ["LIVEKIT_API_KEY"] = "devkey"
        os.environ["LIVEKIT_API_SECRET"] = "secretkey1234567890abcdef"

        lk_bin = shutil.which("livekit-server")
        assert lk_bin, "Se requiere livekit-server instalado para certificar P1-C WebRTC real"
        cls.lk_http_port = _free_port()
        cls.lk_tcp_port = _free_port()
        ice_base = 55500 + (os.getpid() % 50) * 30
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
        return CommunityController(
            api_url=self.api_url,
            session_path=sess_path,
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
        )

    def _connect_pair_to_voice(self, tag: str):
        ctrl_a = self._new_controller(f"{tag}_a")
        ctrl_b = self._new_controller(f"{tag}_b")

        ctrl_a.register(f"dj_{tag}@cci.test", f"dj_{tag}", "SoundPass123!")
        ctrl_b.register(f"lst_{tag}@cci.test", f"lst_{tag}", "SoundPass123!")

        opened = ctrl_a.create_community(f"Club {tag}", "Soundboard P1-C", "public")
        comm_id = str(opened["community"]["id"])
        voice_ch = next((c for c in opened["channels"] if c.get("type") == "voice"), None)
        if not voice_ch:
            voice_ch = ctrl_a.create_channel(f"voz-{tag}", "voice", "Sala Soundboard")
        inv = ctrl_a.create_invitation(comm_id)
        ctrl_b.join_by_invitation(inv["code"])

        ctrl_a.open_community(comm_id)
        ctrl_b.open_community(comm_id)

        ctrl_a.join_voice_channel(voice_ch["id"])
        ctrl_b.join_voice_channel(voice_ch["id"])
        self.assertTrue(ctrl_a.voice_engine.media_transport_active)
        self.assertTrue(ctrl_b.voice_engine.media_transport_active)

        # Esperar suscripción mutua LiveKit antes de emitir soundboard
        deadline = time.time() + 5.0
        while time.time() < deadline:
            self._pump(0.05)
            p_b = {p["user_id"] for p in ctrl_b.voice_engine.list_participants()}
            if ctrl_a.session.user_id in p_b and len(ctrl_b.voice_engine._subscriber_tasks) >= 1:
                break
        self._pump(0.25)
        return ctrl_a, ctrl_b, comm_id, voice_ch

    def test_01_preset_soundboard_rtc_received_by_remote_peer_qt(self):
        """Reproducir efecto desde UI/controlador inyecta PCM en RTC y el peer remoto lo escucha."""
        from omnidash_qt import CommunityInteriorView

        ctrl_a, ctrl_b, comm_id, _voice_ch = self._connect_pair_to_voice("preset")
        view_a = CommunityInteriorView(ctrl_a)
        view_b = CommunityInteriorView(ctrl_b)

        received_b: list[np.ndarray] = []
        sb_events_b: list[dict] = []
        ctrl_b.voice_engine.on_remote_audio_frame = lambda _pid, pcm, _sr, _ch: received_b.append(pcm.copy())
        ctrl_b.soundboard_event.connect(lambda ev: sb_events_b.append(dict(ev)))

        try:
            view_a.show()
            view_b.show()
            ctrl_a.open_community(comm_id)
            self._pump(0.2)

            # Cargar soundboard y abrir drawer desde RightPanel
            ctrl_a.load_soundboard(comm_id)
            view_a.right_panel.soundboard_btn.click()
            self._pump(0.05)
            self.assertTrue(view_a.right_panel.soundboard_drawer.isVisible())

            # Disparar AIRHORN (sin empujar audio de micrófono)
            res = ctrl_a.play_soundboard_effect("preset_airhorn")
            self.assertTrue(res["rtc_injected"])

            deadline = time.time() + 4.0
            while time.time() < deadline:
                self._pump(0.05)
                tx_sb = ctrl_a.voice_engine.get_diagnostics()["soundboard_tx_frames"]
                if tx_sb >= 12 and len(received_b) >= 12 and any(e.get("action") == "played" for e in sb_events_b):
                    break

            self.assertGreater(ctrl_a.voice_engine.get_diagnostics()["soundboard_tx_frames"], 10)
            self.assertGreaterEqual(len(received_b), 8, "Peer remoto B debía recibir audio RTC del soundboard")
            concat_b = np.concatenate(received_b)
            self.assertGreater(_rms(concat_b), 400.0, "Audio RTC recibido debe contener energía real audible")
            dom = _dominant_freq(concat_b)
            self.assertTrue(
                520.0 <= dom <= 1250.0,
                f"Frecuencia dominante remota {dom:.1f} Hz no corresponde a preset_airhorn (587-1175 Hz)",
            )
            self.assertTrue(any(e.get("sound_id") == "preset_airhorn" for e in sb_events_b))

            # Sordo en B corta audio entrante incluso si vuelve a sonar otro preset
            view_b.right_panel.headset_btn.click()
            self._pump(0.1)
            received_b.clear()
            ctrl_a.play_soundboard_effect("preset_gg")
            self._pump(0.6)
            self.assertEqual(len(received_b), 0)
        finally:
            ctrl_a.voice_engine.on_remote_audio_frame = None
            ctrl_b.voice_engine.on_remote_audio_frame = None
            view_a.close()
            view_b.close()
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            self._pump(0.1)

    def test_02_uploaded_mp3_soundboard_streamed_via_rtc(self):
        """MP3 real subido al backend se descarga, decodifica a 48kHz y suena por RTC en el peer remoto."""
        ctrl_a, ctrl_b, comm_id, _voice_ch = self._connect_pair_to_voice("mp3")
        received_b: list[np.ndarray] = []
        ctrl_b.voice_engine.on_remote_audio_frame = lambda _pid, pcm, _sr, _ch: received_b.append(pcm.copy())

        mp3_path = Path(self._tmp_dir.name) / "fx_clip.mp3"
        mp3_bytes = base64.b64decode(_REAL_MP3_B64)
        mp3_path.write_bytes(mp3_bytes)

        try:
            uploaded = ctrl_a.upload_sound_file(
                str(mp3_path),
                title="Clip Real MP3",
                owner_type="community",
                community_id=comm_id,
                volume_scale=1.5,
                cooldown_seconds=2,
            )
            sid = str(uploaded["id"])
            self.assertEqual(uploaded["title"], "Clip Real MP3")

            # Verificar endpoint binario autenticado en backend para peer B también
            dl_b = ctrl_b.api.download_sound_audio(sid)
            self.assertEqual(dl_b, mp3_bytes)

            # Disparar reproducción en A (limpiando caché para ejercer descarga + decodificación real)
            ctrl_a._sound_audio_cache.pop(sid, None)
            res = ctrl_a.play_soundboard_effect(sid)
            self.assertTrue(res["rtc_injected"])

            deadline = time.time() + 4.0
            while time.time() < deadline:
                self._pump(0.05)
                tx_sb = ctrl_a.voice_engine.get_diagnostics()["soundboard_tx_frames"]
                if tx_sb >= 12 and len(received_b) >= 12:
                    break

            self.assertGreater(ctrl_a.voice_engine.get_diagnostics()["soundboard_tx_frames"], 10)
            concat_b = np.concatenate(received_b)
            self.assertGreater(_rms(concat_b), 80.0, "MP3 real transmitido por RTC debe escucharse en peer B")
        finally:
            ctrl_a.voice_engine.on_remote_audio_frame = None
            ctrl_b.voice_engine.on_remote_audio_frame = None
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            self._pump(0.1)

    def test_03_mic_plus_soundboard_mixing_and_stop(self):
        """Micrófono (440Hz) y soundboard (990Hz) se mezclan en el mismo track saliente y stop corta al instante."""
        ctrl_a, ctrl_b, _comm_id, _voice_ch = self._connect_pair_to_voice("mix")
        received_b: list[np.ndarray] = []
        ctrl_b.voice_engine.on_remote_audio_frame = lambda _pid, pcm, _sr, _ch: received_b.append(pcm.copy())

        try:
            # Inyectar tono soundboard de 1.2s a 990Hz en el engine de A
            t_sb = np.arange(int(48000 * 1.2), dtype=np.float64) / 48000.0
            sb_990 = (9000.0 * np.sin(2.0 * math.pi * 990.0 * t_sb)).astype(np.int16)
            ok = ctrl_a.voice_engine.play_soundboard_pcm(sb_990, sound_id="mix_990", title="Mix 990")
            self.assertTrue(ok)
            self.assertTrue(ctrl_a.voice_engine.get_diagnostics()["soundboard_playing"])

            # Empujar simultáneamente 20 frames (0.4s) de micrófono a 440Hz
            for idx in range(20):
                ctrl_a.voice_engine.push_pcm_frame(_sine_frame(440.0, idx, amp=9000.0))
                self._pump(0.02)

            self._pump(0.35)
            self.assertGreater(len(received_b), 12)
            mixed_pcm = np.concatenate(received_b)
            e_440 = _band_energy_ratio(mixed_pcm, 440.0)
            e_990 = _band_energy_ratio(mixed_pcm, 990.0)
            self.assertGreater(e_440, 0.15, f"Esperado micrófono 440Hz presente en mezcla (ratio={e_440:.3f})")
            self.assertGreater(e_990, 0.15, f"Esperado soundboard 990Hz presente en mezcla (ratio={e_990:.3f})")

            # Detener soundboard inmediatamente
            removed = ctrl_a.stop_soundboard_effect("mix_990")
            self.assertEqual(removed, 1)
            self.assertFalse(ctrl_a.voice_engine.get_diagnostics()["soundboard_playing"])
        finally:
            ctrl_a.voice_engine.on_remote_audio_frame = None
            ctrl_b.voice_engine.on_remote_audio_frame = None
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            self._pump(0.1)

    def test_04_rbac_cooldown_and_mute_enforcement(self):
        """Sin permiso soundboard.play (403), en cooldown (429) o muteado no se emite audio RTC."""
        from backend.communities.desktop_client import CommunityApiError

        ctrl_a, ctrl_b, comm_id, voice_ch = self._connect_pair_to_voice("sec")
        received_a_on_a: list[np.ndarray] = []
        ctrl_a.voice_engine.on_remote_audio_frame = lambda _pid, pcm, _sr, _ch: received_a_on_a.append(pcm.copy())

        try:
            # 1) B (sin permiso soundboard.play por override explícito deny) -> 403 y 0 frames RTC
            ctrl_a.api._request(
                "POST",
                f"/api/v1/communities/{comm_id}/channels/{voice_ch['id']}/overrides",
                json_body={
                    "target_type": "user",
                    "target_id": ctrl_b.session.user_id,
                    "permission_id": "soundboard.play",
                    "deny": True,
                },
            )
            with self.assertRaises(CommunityApiError) as ctx:
                ctrl_b.play_soundboard_effect("preset_airhorn")
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctrl_b.voice_engine.get_diagnostics()["soundboard_tx_frames"], 0)
            self._pump(0.25)
            if received_a_on_a:
                self.assertLess(_rms(np.concatenate(received_a_on_a)), 10.0)

            # 2) A muteado localmente no inyecta soundboard sobre track muteado
            ctrl_a.set_voice_mute(True)
            with self.assertRaises(CommunityApiError) as ctx_mute:
                ctrl_a.play_soundboard_effect("preset_buzzer")
            self.assertEqual(ctx_mute.exception.code, "VOICE_MUTED")

            # 3) Desmuteado dispara 1ra vez OK y 2da rápida recibe 429 cooldown sin doble inyección
            ctrl_a.set_voice_mute(False)
            res1 = ctrl_a.play_soundboard_effect("preset_ko")
            self.assertTrue(res1["rtc_injected"])
            with self.assertRaises(CommunityApiError) as ctx_cd:
                ctrl_a.play_soundboard_effect("preset_ko")
            self.assertEqual(ctx_cd.exception.status_code, 429)
        finally:
            ctrl_a.voice_engine.on_remote_audio_frame = None
            ctrl_b.voice_engine.on_remote_audio_frame = None
            ctrl_a.shutdown()
            ctrl_b.shutdown()
            self._pump(0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
