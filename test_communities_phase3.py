"""
test_communities_phase3.py - Pruebas de integración de Fase 3: Salas de Voz y LiveKit SFU.

Verifica de forma estricta los criterios de aceptación:
1. Emisión de tokens LiveKit JWT (RFC 7519) autoritativos con concesiones de sala.
2. Autorización fail-closed: canales privados y usuarios no autorizados reciben 403.
3. Control estricto de cupo máximo de participantes (max_participants -> 422).
4. Concesión granular de micrófono (voice.speak -> canPublish True/False).
5. Ciclo de vida de sesiones de voz (unión, listado de participantes, salida).
6. Señalización en tiempo real vía Socket.IO (unión, salida, mute y active speakers).
7. Moderación de sala (silenciar y desconectar respetando jerarquías).
8. Integración con controladores de audio físico de hardware (AudioDeviceManager/DAC).
9. Reconexión y recuperación transparente de sesión de voz.
"""
from __future__ import annotations

import tempfile
import time
import unittest
from backend.auth import create_access_token
from backend.communities.livekit_token import LiveKitTokenGenerator
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.server import app, socketio
from mobile.audio_drivers import AudioDeviceManager


class TestCommunitiesPhase3(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.temp_dir.name}/test_voice_phase3.sqlite3"
        self.repo = CommunitiesRepository.reset_instance(self.db_path)
        self.svc = CommunitiesService.get_instance(self.repo)
        self.client = app.test_client()

        # Cuentas de prueba independientes
        self.token_alice = create_access_token("u_alice", "Alice")
        self.token_bob = create_access_token("u_bob", "Bob")
        self.token_charlie = create_access_token("u_charlie", "Charlie")
        self.token_eve = create_access_token("u_eve", "Eve")

        # Comunidad base con canales por defecto
        self.comm = self.svc.create_community("u_alice", "Voice Arena", visibility="private")
        self.comm_id = self.comm["id"]

        channels = self.repo.list_channels(self.comm_id)
        self.ch_voice = [c for c in channels if c["name"] == "General Voice"][0]
        self.ch_id = self.ch_voice["id"]

        # Incorporar a Bob y Charlie a la comunidad
        self.repo.add_member(self.comm_id, "u_bob")
        self.repo.add_member(self.comm_id, "u_charlie")

    def tearDown(self):
        self.repo.close()
        self.temp_dir.cleanup()

    def test_01_voice_token_generation_and_jwt_claims(self):
        """Alice solicita token de voz; se genera JWT firmado con concesiones LiveKit válidas."""
        res = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("token", data)
        self.assertIn("url", data)
        self.assertIn("room_name", data)
        self.assertTrue(data["can_publish"])
        self.assertGreater(data["expires_at"], time.time())

        # Validar criptográficamente el JWT LiveKit
        gen = LiveKitTokenGenerator()
        claims = gen.verify_access_token(data["token"])
        self.assertIsNotNone(claims, "Firma del token LiveKit debe ser válida con la clave secreta")
        self.assertEqual(claims["sub"], "u_alice")
        self.assertTrue(claims["video"]["roomJoin"])
        self.assertTrue(claims["video"]["canPublish"])
        self.assertTrue(claims["video"]["canSubscribe"])

    def test_02_voice_token_rejects_unauthorized_user(self):
        """Canal de voz privado rechaza con 403 Forbidden a usuarios sin permiso."""
        ch_priv = self.svc.create_channel(
            self.comm_id,
            "u_alice",
            "Commanders Voice",
            channel_type="voice",
            is_private=True
        )
        ch_priv_id = ch_priv["id"]

        # Eve (no miembro ni autorizada) intenta pedir token -> 403 Forbidden
        res_eve = self.client.post(
            f"/api/v1/channels/{ch_priv_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_eve}"}
        )
        self.assertEqual(res_eve.status_code, 403)

        # Bob (miembro pero sin sobrescritura allow en canal privado) -> 403 Forbidden
        res_bob = self.client.post(
            f"/api/v1/channels/{ch_priv_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_bob.status_code, 403)

    def test_03_voice_token_enforces_participant_limit(self):
        """Canal con límite de 2 participantes rechaza al tercer usuario con 422 Unprocessable."""
        ch_duo = self.svc.create_channel(
            self.comm_id,
            "u_alice",
            "Duo Queue",
            channel_type="voice",
            max_participants=2
        )
        ch_duo_id = ch_duo["id"]

        # Alice y Bob se conectan exitosamente (2 slots ocupados)
        res_a = self.client.post(
            f"/api/v1/channels/{ch_duo_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_a.status_code, 200)

        res_b = self.client.post(
            f"/api/v1/channels/{ch_duo_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_b.status_code, 200)

        # Charlie intenta unirse -> Sala llena (422)
        res_c = self.client.post(
            f"/api/v1/channels/{ch_duo_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_charlie}"}
        )
        self.assertEqual(res_c.status_code, 422)
        self.assertIn("límite", res_c.get_json()["error"].lower())

    def test_04_voice_speak_permission_controls_can_publish(self):
        """Usuario con permiso voice.speak denegado recibe token LiveKit en modo solo escucha."""
        # Alice aplica sobrescritura deny en voice.speak para Charlie
        self.svc.set_channel_override(
            community_id=self.comm_id,
            channel_id=self.ch_id,
            requester_id="u_alice",
            target_type="user",
            target_id="u_charlie",
            permission_id="voice.speak",
            allow=False,
            deny=True
        )

        res_c = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-token",
            headers={"Authorization": f"Bearer {self.token_charlie}"}
        )
        self.assertEqual(res_c.status_code, 200)
        data_c = res_c.get_json()
        self.assertFalse(data_c["can_publish"], "can_publish debe ser False si voice.speak está denegado")

        gen = LiveKitTokenGenerator()
        claims = gen.verify_access_token(data_c["token"])
        self.assertFalse(claims["video"]["canPublish"])
        self.assertTrue(claims["video"]["canSubscribe"])

    def test_05_voice_session_lifecycle_and_participants_listing(self):
        """Registro de sesiones de voz activas y liberación determinista al salir."""
        # Alice y Bob solicitan tokens
        self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_alice}"})
        self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_bob}"})

        # Listar participantes
        res_list = self.client.get(
            f"/api/v1/channels/{self.ch_id}/voice-participants",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_list.status_code, 200)
        participants = res_list.get_json()["participants"]
        self.assertEqual(len(participants), 2)
        active_uids = [p["user_id"] for p in participants]
        self.assertIn("u_alice", active_uids)
        self.assertIn("u_bob", active_uids)

        # Bob se desconecta de la llamada
        res_leave = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-leave",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_leave.status_code, 200)

        # Queda únicamente Alice
        res_list_after = self.client.get(
            f"/api/v1/channels/{self.ch_id}/voice-participants",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        participants_after = res_list_after.get_json()["participants"]
        self.assertEqual(len(participants_after), 1)
        self.assertEqual(participants_after[0]["user_id"], "u_alice")

    def test_06_realtime_voice_participant_events_socketio(self):
        """Eventos Socket.IO en vivo para incorporación, silenciamiento y salida de participantes."""
        sio_a = socketio.test_client(app, auth={"token": self.token_alice})
        sio_b = socketio.test_client(app, auth={"token": self.token_bob})
        self.assertTrue(sio_a.is_connected())
        self.assertTrue(sio_b.is_connected())

        # Ambos se unen a la sala de voz
        sio_a.emit("community:voice:join", {"channel_id": self.ch_id})
        sio_b.emit("community:voice:join", {"channel_id": self.ch_id})

        # Verificar recepción de evento de unión
        rec_b = sio_b.get_received()
        join_events = [ev for ev in rec_b if ev["name"] == "voice.participant_joined"]
        self.assertGreaterEqual(len(join_events), 1)

        # Bob cambia su estado de micrófono a silenciado (mute)
        sio_b.emit("community:voice:mute", {"channel_id": self.ch_id, "is_muted": True})

        rec_a = sio_a.get_received()
        mute_events = [ev for ev in rec_a if ev["name"] == "voice.mute_state_changed"]
        self.assertEqual(len(mute_events), 1)
        self.assertEqual(mute_events[0]["args"][0]["user_id"], "u_bob")
        self.assertTrue(mute_events[0]["args"][0]["is_muted"])

        # Bob sale de la sala de voz
        sio_b.emit("community:voice:leave", {"channel_id": self.ch_id})
        rec_a_leave = sio_a.get_received()
        leave_events = [ev for ev in rec_a_leave if ev["name"] == "voice.participant_left"]
        self.assertEqual(len(leave_events), 1)
        self.assertEqual(leave_events[0]["args"][0]["user_id"], "u_bob")

        sio_a.disconnect()
        sio_b.disconnect()

    def test_07_voice_moderation_mute_and_disconnect(self):
        """Dueña Alice silencia a Bob; terceros son rechazados con 403; nadie puede moderar al dueño."""
        # Alice y Bob en sala
        self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_alice}"})
        self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_bob}"})

        # 1. Alice (dueña) silencia a Bob -> 200 OK
        res_mute = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-moderate",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"target_user_id": "u_bob", "action": "mute"}
        )
        self.assertEqual(res_mute.status_code, 200)
        participants = self.repo.list_active_voice_sessions(self.ch_id)
        p_bob = [p for p in participants if p["user_id"] == "u_bob"][0]
        self.assertTrue(p_bob["is_muted"])

        # 2. Bob intenta moderar a la dueña Alice -> 403 Forbidden
        res_mute_owner = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-moderate",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"target_user_id": "u_alice", "action": "mute"}
        )
        self.assertEqual(res_mute_owner.status_code, 403)

        # 3. Alice desconecta a Bob -> 200 OK
        res_kick = self.client.post(
            f"/api/v1/channels/{self.ch_id}/voice-moderate",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"target_user_id": "u_bob", "action": "disconnect"}
        )
        self.assertEqual(res_kick.status_code, 200)
        participants_after = self.repo.list_active_voice_sessions(self.ch_id)
        self.assertNotIn("u_bob", [p["user_id"] for p in participants_after])

    def test_08_active_speakers_realtime_indicator(self):
        """Indicador de audio activo (VAD) se difunde entre participantes conectados."""
        sio_a = socketio.test_client(app, auth={"token": self.token_alice})
        sio_b = socketio.test_client(app, auth={"token": self.token_bob})
        sio_a.emit("community:voice:join", {"channel_id": self.ch_id})
        sio_b.emit("community:voice:join", {"channel_id": self.ch_id})

        sio_a.emit("community:voice:speakers", {
            "channel_id": self.ch_id,
            "audio_level": 0.85,
            "is_speaking": True
        })

        rec_b = sio_b.get_received()
        speaker_events = [ev for ev in rec_b if ev["name"] == "voice.active_speakers"]
        self.assertEqual(len(speaker_events), 1)
        spk = speaker_events[0]["args"][0]["speakers"][0]
        self.assertEqual(spk["user_id"], "u_alice")
        self.assertTrue(spk["is_speaking"])
        self.assertAlmostEqual(spk["audio_level"], 0.85)

        sio_a.disconnect()
        sio_b.disconnect()

    def test_09_platform_audio_driver_and_device_enumeration(self):
        """Verifica compatibilidad de drivers físicos de audio y selección de dispositivos."""
        mgr = AudioDeviceManager.get_instance()
        driver = mgr.get_driver()
        self.assertIsNotNone(driver)
        self.assertTrue(driver.check_permissions())

        mics = mgr.list_capture_devices()
        spks = mgr.list_playback_devices()
        self.assertGreater(len(mics), 0)
        self.assertGreater(len(spks), 0)

        # Reproducción física en DAC y silencio de hardware
        pcm_frame = b"\x00\x00" * driver.SAMPLES_PER_FRAME
        self.assertTrue(driver.play_frame(pcm_frame))
        driver.set_mute(True)
        self.assertTrue(driver.is_muted)
        driver.set_mute(False)

    def test_10_reconnection_and_session_recovery(self):
        """Reconexión tras pérdida de conexión actualiza sesión sin duplicar registros."""
        # Alice solicita token inicial
        res1 = self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_alice}"})
        self.assertEqual(res1.status_code, 200)

        # Alice simula reconexión solicitando nuevo token en el mismo canal
        res2 = self.client.post(f"/api/v1/channels/{self.ch_id}/voice-token", headers={"Authorization": f"Bearer {self.token_alice}"})
        self.assertEqual(res2.status_code, 200)

        # La base de datos debe contener solo 1 sesión activa para Alice
        active = self.repo.list_active_voice_sessions(self.ch_id)
        alice_active = [p for p in active if p["user_id"] == "u_alice"]
        self.assertEqual(len(alice_active), 1, "Reconexión no debe dejar sesiones fantasma duplicadas")


if __name__ == "__main__":
    unittest.main()
