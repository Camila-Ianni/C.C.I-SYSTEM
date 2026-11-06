"""
test_communities_phase5.py - Suite de pruebas unitarias herméticas para Streaming (Screen & Game Share).

Cubre:
1. Detección de fuentes de captura (pantallas, ventanas, juegos C.C.I.) y perfiles técnicos.
2. Inicio de transmisión exitosa con permiso voice.stream y emisión de token LiveKit (201 Created).
3. Rechazo estricto por falta de permiso voice.stream (403 Forbidden).
4. Límite de streams simultáneos por canal (409 Conflict / STREAM_LIMIT_REACHED).
5. Pausa y reanudación de la transmisión activa (200 OK con is_paused).
6. Finalización de transmisión y liberación inmediata del slot en el canal.
7. Rechazo de perfiles técnicos fuera de norma (resolución inválida, FPS > 60).
8. Consulta del stream activo en canal mediante GET /channels/{id}/stream.
9. Verificación criptográfica del token LiveKit emitido para streaming.
10. Aislamiento fail-closed: usuario sin permisos de moderación no puede detener stream ajeno (403 Forbidden).
"""

import os
import shutil
import tempfile
import unittest
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.communities.livekit_token import LiveKitTokenGenerator
from backend.server import app
from backend.auth import create_access_token


class TestCommunitiesPhase5Streaming(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cci_test_stream_")
        self.db_path = os.path.join(self.temp_dir, "test_communities_phase5.db")

        self.repo = CommunitiesRepository(db_path=self.db_path)
        self.service = CommunitiesService(repo=self.repo)

        CommunitiesRepository._instance = self.repo
        CommunitiesService._instance = self.service

        app.config["TESTING"] = True
        self.client = app.test_client()

        # Sembrar usuarios
        self.owner_id = "user_owner_501"
        self.streamer_id = "user_streamer_502"
        self.viewer_id = "user_viewer_503"
        self.stranger_id = "user_stranger_504"

        self.token_owner = create_access_token(self.owner_id, "owner5")
        self.token_streamer = create_access_token(self.streamer_id, "streamer5")
        self.token_viewer = create_access_token(self.viewer_id, "viewer5")
        self.token_stranger = create_access_token(self.stranger_id, "stranger5")

        # Crear comunidad principal
        self.comm = self.service.create_community(
            owner_id=self.owner_id,
            name="Comunidad Gaming & Stream",
            slug="gaming-stream-5"
        )
        self.comm_id = self.comm["id"]

        # Crear canal de voz/streaming
        self.stream_chan = self.service.create_channel(
            community_id=self.comm_id,
            requester_id=self.owner_id,
            name="Sala Stream en Vivo",
            channel_type="voice"
        )
        self.channel_id = self.stream_chan["id"]

        # Incorporar streamer y viewer
        code = self.service.create_invitation(self.comm_id, self.owner_id)["code"]
        self.service.join_via_invitation(code, self.streamer_id)
        self.service.join_via_invitation(code, self.viewer_id)

        # Crear rol "Streamer" con permiso voice.stream y voice.connect
        self.streamer_role = self.service.create_role(
            community_id=self.comm_id,
            requester_id=self.owner_id,
            name="Streamer",
            permissions=["voice.stream", "voice.connect", "voice.speak"]
        )
        self.service.assign_role(self.comm_id, self.owner_id, self.streamer_id, self.streamer_role["id"])

        # Quitar voice.stream de @everyone si existiera para aislar viewer_id
        self.service.set_channel_override(
            community_id=self.comm_id,
            channel_id=self.channel_id,
            requester_id=self.owner_id,
            target_type="user",
            target_id=self.viewer_id,
            permission_id="voice.stream",
            allow=False,
            deny=True
        )

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        CommunitiesRepository._instance = None
        CommunitiesService._instance = None

    def test_01_detect_capture_sources_and_profiles(self):
        """Consulta fuentes de captura (pantallas, ventanas, juegos C.C.I.) y perfiles técnicos."""
        res = self.client.get(
            "/api/v1/streams/sources",
            headers={"Authorization": f"Bearer {self.token_streamer}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("screens", data)
        self.assertIn("windows", data)
        self.assertIn("games", data)
        self.assertIn("profiles", data)

        # Verificar presencia de juegos emblemáticos de C.C.I.
        game_names = [g["name"] for g in data["games"]]
        self.assertIn("METAL SLUG", game_names)
        self.assertIn("Davinci-Fighter", game_names)

        # Verificar perfiles estándar
        self.assertIn("1080p_60fps", data["profiles"])

    def test_02_start_stream_success(self):
        """Inicia una transmisión de juego autorizada emitiendo credenciales LiveKit válidas."""
        res = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={
                "stream_type": "game",
                "game_id": "metal-slug",
                "title": "METAL SLUG Campaña 60 FPS",
                "resolution": "1080p",
                "fps": 60,
                "bitrate_kbps": 4500,
                "has_audio": True
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("session", data)
        self.assertIn("livekit", data)

        session = data["session"]
        self.assertEqual(session["channel_id"], self.channel_id)
        self.assertEqual(session["user_id"], self.streamer_id)
        self.assertEqual(session["stream_type"], "game")
        self.assertEqual(session["resolution"], "1080p")
        self.assertEqual(session["fps"], 60)
        self.assertTrue(session["has_audio"])
        self.assertFalse(session["is_paused"])

        # Verificar que el token LiveKit tiene permisos de publicación
        lk = data["livekit"]
        self.assertTrue(lk["can_publish"])
        self.assertIn("token", lk)

    def test_03_reject_stream_without_permission(self):
        """Rechaza inicio de stream si el usuario carece de permiso voice.stream (403 Forbidden)."""
        res = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_viewer}"},
            json={
                "stream_type": "screen",
                "title": "Stream no autorizado",
                "resolution": "720p",
                "fps": 30
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("voice.stream", res.get_json()["error"])

    def test_04_enforce_max_streams_per_channel_limit(self):
        """Rechaza una segunda transmisión simultánea en el mismo canal (409 Conflict)."""
        # Primer stream por streamer_id
        res1 = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"stream_type": "game", "title": "Stream 1", "resolution": "1080p", "fps": 60}
        )
        self.assertEqual(res1.status_code, 201)

        # Propietario tiene permisos pero el canal ya tiene 1 stream activo
        res2 = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"stream_type": "screen", "title": "Stream 2", "resolution": "1080p", "fps": 60}
        )
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.get_json()["error"], "STREAM_LIMIT_REACHED")

    def test_05_stream_pause_and_resume(self):
        """Pausa y reanuda la transmisión activa actualizando el estado."""
        res_start = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"stream_type": "screen", "title": "Stream Pausable"}
        )
        self.assertEqual(res_start.status_code, 201)
        session_id = res_start.get_json()["session"]["id"]

        # Pausar transmisión
        res_pause = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-pause",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"session_id": session_id}
        )
        self.assertEqual(res_pause.status_code, 200)
        self.assertTrue(res_pause.get_json()["is_paused"])

        # Reanudar transmisión
        res_resume = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-resume",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"session_id": session_id}
        )
        self.assertEqual(res_resume.status_code, 200)
        self.assertFalse(res_resume.get_json()["is_paused"])

    def test_06_stop_stream_releases_channel_slot(self):
        """Detiene la transmisión activa y libera el cupo para permitir un nuevo stream."""
        res_start = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"stream_type": "game", "title": "Stream a finalizar"}
        )
        session_id = res_start.get_json()["session"]["id"]

        # Detener transmisión
        res_stop = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-stop",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"session_id": session_id}
        )
        self.assertEqual(res_stop.status_code, 200)
        self.assertEqual(res_stop.get_json()["status"], "stopped")

        # Verificar que el canal ahora está libre para que otro transmita
        res_owner = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"stream_type": "screen", "title": "Nuevo Stream del Owner"}
        )
        self.assertEqual(res_owner.status_code, 201)

    def test_07_reject_invalid_stream_profile(self):
        """Rechaza perfiles de transmisión con resolución inválida o FPS no permitidos."""
        # Resolución inexistente
        res_bad_res = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"resolution": "8k", "fps": 60}
        )
        self.assertEqual(res_bad_res.status_code, 400)
        self.assertEqual(res_bad_res.get_json()["error"], "INVALID_RESOLUTION")

        # FPS no soportados (120 FPS)
        res_bad_fps = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"resolution": "1080p", "fps": 120}
        )
        self.assertEqual(res_bad_fps.status_code, 400)
        self.assertEqual(res_bad_fps.get_json()["error"], "INVALID_FPS")

    def test_08_get_active_channel_stream(self):
        """Obtiene la información y metadatos del stream activo en el canal."""
        self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"stream_type": "game", "game_id": "cuphead", "title": "Cuphead Co-op"}
        )

        # Viewer consulta stream activo
        res = self.client.get(
            f"/api/v1/channels/{self.channel_id}/stream",
            headers={"Authorization": f"Bearer {self.token_viewer}"}
        )
        self.assertEqual(res.status_code, 200)
        stream = res.get_json()["stream"]
        self.assertIsNotNone(stream)
        self.assertEqual(stream["title"], "Cuphead Co-op")
        self.assertEqual(stream["game_id"], "cuphead")
        self.assertEqual(stream["user_id"], self.streamer_id)

    def test_09_stream_token_livekit_grants(self):
        """Comprueba que el token generado por LiveKit es un JWT criptográficamente verificable."""
        generator = LiveKitTokenGenerator()
        token = generator.create_access_token(
            identity="test_streamer",
            name="Streamer One",
            room_name="test_stream_room",
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            valid_for_seconds=300
        )["token"]

        payload = generator.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "test_streamer")
        self.assertEqual(payload["name"], "Streamer One")
        self.assertTrue(payload["video"]["roomJoin"])
        self.assertTrue(payload["video"]["canPublish"])
        self.assertTrue(payload["video"]["canPublishData"])

    def test_10_cross_channel_and_user_isolation(self):
        """Verifica que un usuario común no pueda detener ni pausar la transmisión de otro."""
        res_start = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-start",
            headers={"Authorization": f"Bearer {self.token_streamer}"},
            json={"stream_type": "screen", "title": "Stream Intocable"}
        )
        session_id = res_start.get_json()["session"]["id"]

        # 1. viewer_id intenta pausar el stream de streamer_id -> 403 Forbidden
        res_pause = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-pause",
            headers={"Authorization": f"Bearer {self.token_viewer}"},
            json={"session_id": session_id}
        )
        self.assertEqual(res_pause.status_code, 403)

        # 2. stranger_id (no pertenece a la comunidad) intenta detener -> 403 Forbidden
        res_stop = self.client.post(
            f"/api/v1/channels/{self.channel_id}/stream-stop",
            headers={"Authorization": f"Bearer {self.token_stranger}"},
            json={"session_id": session_id}
        )
        self.assertEqual(res_stop.status_code, 403)


if __name__ == "__main__":
    unittest.main()
