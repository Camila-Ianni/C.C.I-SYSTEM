"""
test_communities_phase4.py - Suite de pruebas unitarias herméticas para Sound Deck (Soundboard).

Cubre:
1. Creación de categorías y subida exitosa de MP3 válidos (global, personal, comunidad).
2. Rechazo de archivos no MP3 por magic bytes (400 Bad Request).
3. Rechazo de archivos que superan 5 MB (413 Payload Too Large).
4. Rechazo de archivos cuya duración excede 15.0 segundos (400 Bad Request).
5. Segregación de bibliotecas y búsqueda por comunidad y usuario.
6. Gestión de favoritos y teclas rápidas (hotkeys).
7. Edición y eliminación con control de permisos jerárquicos (soundboard.manage vs uploader).
8. Autorización de reproducción exitosa en sala de voz (200 OK).
9. Control de frecuencia y cooldown anti-spam (429 Too Many Requests con retry_after).
10. Aislamiento fail-closed entre comunidades y permisos requeridos.
"""

import os
import shutil
import tempfile
import unittest
import base64
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.server import app
from backend.auth import create_access_token


def make_valid_mp3_bytes(duration_sec: float = 3.0, size_bytes: int = 1024) -> bytes:
    """Genera un payload binario con magic bytes ID3 y frames válidos para tests."""
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    # Frame sync MPEG Layer III 128kbps 44.1kHz
    frame_header = b"\xff\xfb\x90\x00"
    body_len = max(0, size_bytes - len(id3_header) - len(frame_header))
    return id3_header + frame_header + (b"\x00" * body_len)


class TestCommunitiesPhase4SoundDeck(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cci_test_sounddeck_")
        self.db_path = os.path.join(self.temp_dir, "test_communities_phase4.db")
        self.storage_dir = os.path.join(self.temp_dir, "storage_sounds")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.repo = CommunitiesRepository(db_path=self.db_path)
        self.service = CommunitiesService(repo=self.repo)

        # Inyectar repo y service en Singleton
        CommunitiesRepository._instance = self.repo
        CommunitiesService._instance = self.service

        app.config["TESTING"] = True
        self.client = app.test_client()

        # Sembrar usuarios
        self.admin_id = "user_admin_sys"
        self.owner_id = "user_owner_401"
        self.dj_id = "user_dj_402"
        self.regular_id = "user_regular_403"
        self.stranger_id = "user_stranger_404"

        self.token_admin = create_access_token(self.admin_id, "admin", is_admin=True)
        self.token_owner = create_access_token(self.owner_id, "owner4")
        self.token_dj = create_access_token(self.dj_id, "dj4")
        self.token_regular = create_access_token(self.regular_id, "reg4")
        self.token_stranger = create_access_token(self.stranger_id, "stranger4")

        # Crear comunidad principal
        self.comm_a = self.service.create_community(
            owner_id=self.owner_id,
            name="Comunidad Audio A",
            slug="comunidad-audio-a"
        )
        self.comm_a_id = self.comm_a["id"]

        # Crear canal de voz
        self.voice_chan = self.service.create_channel(
            community_id=self.comm_a_id,
            requester_id=self.owner_id,
            name="Sala DJ General",
            channel_type="voice"
        )
        self.voice_chan_id = self.voice_chan["id"]

        # Incorporar dj_id y regular_id a la comunidad
        code = self.service.create_invitation(self.comm_a_id, self.owner_id)["code"]
        self.service.join_via_invitation(code, self.dj_id)
        self.service.join_via_invitation(code, self.regular_id)

        # Crear rol "DJ" con permisos soundboard.manage y soundboard.play
        self.dj_role = self.service.create_role(
            community_id=self.comm_a_id,
            requester_id=self.owner_id,
            name="DJ",
            permissions=["soundboard.play", "soundboard.manage", "voice.connect", "voice.speak"]
        )
        self.service.assign_role(self.comm_a_id, self.owner_id, self.dj_id, self.dj_role["id"])

        # Dar a @everyone solo voice.connect por defecto
        # regular_id no tiene soundboard.play

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        CommunitiesRepository._instance = None
        CommunitiesService._instance = None

    def test_01_create_category_and_upload_sound_success(self):
        """Crea categorías y sube sonidos válidos en scope global, personal y comunitario."""
        # 1. Admin crea categoría global
        res = self.client.post(
            "/api/v1/sounds/categories",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"scope_type": "global", "name": "Efectos Globales"}
        )
        self.assertEqual(res.status_code, 201)
        cat_global_id = res.get_json()["id"]

        # 2. Admin sube sonido global
        mp3_bytes = make_valid_mp3_bytes(duration_sec=2.5)
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={
                "owner_type": "global",
                "title": "Airhorn Clásico",
                "category_id": cat_global_id,
                "file_base64": base64.b64encode(mp3_bytes).decode("ascii"),
                "duration": 2.5,
                "volume_scale": 1.0,
                "cooldown_seconds": 3
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["title"], "Airhorn Clásico")
        self.assertEqual(data["owner_type"], "global")
        self.assertEqual(data["duration_seconds"], 2.5)

        # 3. DJ sube sonido de comunidad con permiso soundboard.manage
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={
                "owner_type": "community",
                "owner_id": self.comm_a_id,
                "title": "Victoria Gamer",
                "file_base64": base64.b64encode(mp3_bytes).decode("ascii"),
                "duration": 4.0,
                "cooldown_seconds": 5
            }
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["owner_type"], "community")
        self.assertEqual(res.get_json()["owner_id"], self.comm_a_id)

        # 4. Usuario regular sube sonido personal
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={
                "owner_type": "user",
                "title": "Mi Sonido Personal",
                "file_base64": base64.b64encode(mp3_bytes).decode("ascii"),
                "duration": 1.8
            }
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["owner_type"], "user")
        self.assertEqual(res.get_json()["owner_id"], self.regular_id)

    def test_02_reject_invalid_audio_magic_bytes(self):
        """Rechaza archivos con formato inválido o magic bytes no reconocidos."""
        fake_bytes = b"Este no es un archivo de audio MP3, es texto plano!"
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={
                "owner_type": "user",
                "title": "Falso MP3",
                "file_base64": base64.b64encode(fake_bytes).decode("ascii")
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("INVALID_FORMAT", res.get_json()["error"])

    def test_03_reject_oversized_audio_file(self):
        """Rechaza archivos que excedan el límite estricto de 5 MB."""
        oversized_bytes = make_valid_mp3_bytes(duration_sec=5.0, size_bytes=5 * 1024 * 1024 + 100)
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={
                "owner_type": "user",
                "title": "Sonido Gigante",
                "file_base64": base64.b64encode(oversized_bytes).decode("ascii")
            }
        )
        self.assertEqual(res.status_code, 413)

    def test_04_reject_exceeded_duration(self):
        """Rechaza sonidos cuya duración supere los 15.0 segundos reglamentarios."""
        mp3_bytes = make_valid_mp3_bytes(duration_sec=16.0)
        res = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={
                "owner_type": "user",
                "title": "Audio Demasiado Largo",
                "file_base64": base64.b64encode(mp3_bytes).decode("ascii"),
                "duration": 15.5
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("DURATION_EXCEEDED", res.get_json()["error"])

    def test_05_list_sounds_segregation(self):
        """Comprueba que el listado de comunidad une sonidos globales, comunitarios y personales propios."""
        mp3 = make_valid_mp3_bytes(duration_sec=2.0)

        # Sonido global
        self.service.upload_sound(
            actor_id=self.admin_id,
            owner_type="global",
            title="Global Fanfare",
            file_bytes=mp3,
            is_admin=True,
            storage_dir=self.storage_dir
        )
        # Sonido comunidad A
        self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            owner_id=self.comm_a_id,
            title="Comunidad A Theme",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        # Sonido personal de regular_id
        self.service.upload_sound(
            actor_id=self.regular_id,
            owner_type="user",
            title="Personal de Regular",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        # Sonido personal de dj_id (no debe verse por regular_id)
        self.service.upload_sound(
            actor_id=self.dj_id,
            owner_type="user",
            title="Personal Secreto de DJ",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )

        # Consulta regular_id a la comunidad A
        res = self.client.get(
            f"/api/v1/communities/{self.comm_a_id}/sounds",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        )
        self.assertEqual(res.status_code, 200)
        titles = [s["title"] for s in res.get_json()["sounds"]]
        self.assertIn("Global Fanfare", titles)
        self.assertIn("Comunidad A Theme", titles)
        self.assertIn("Personal de Regular", titles)
        self.assertNotIn("Personal Secreto de DJ", titles)

        # Filtro de búsqueda
        res_search = self.client.get(
            f"/api/v1/communities/{self.comm_a_id}/sounds?search=Fanfare",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        )
        search_titles = [s["title"] for s in res_search.get_json()["sounds"]]
        self.assertEqual(search_titles, ["Global Fanfare"])

    def test_06_favorites_and_hotkeys(self):
        """Asigna favoritos y teclas de acceso rápido a un sonido."""
        mp3 = make_valid_mp3_bytes(duration_sec=1.5)
        sound = self.service.upload_sound(
            actor_id=self.regular_id,
            owner_type="user",
            title="Sonido Rápido",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        sound_id = sound["id"]

        # Marcar favorito con hotkey F1
        res = self.client.post(
            f"/api/v1/sounds/{sound_id}/favorite",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={"is_favorite": True, "hotkey": "F1"}
        )
        self.assertEqual(res.status_code, 200)

        # Listar favoritos
        res_favs = self.client.get(
            "/api/v1/sounds/favorites",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        )
        self.assertEqual(res_favs.status_code, 200)
        favs = res_favs.get_json()["favorites"]
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs[0]["sound_id"], sound_id)
        self.assertEqual(favs[0]["hotkey"], "F1")

        # Desmarcar favorito
        res_unfav = self.client.post(
            f"/api/v1/sounds/{sound_id}/favorite",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={"is_favorite": False}
        )
        self.assertEqual(res_unfav.status_code, 200)
        favs_after = self.client.get(
            "/api/v1/sounds/favorites",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        ).get_json()["favorites"]
        self.assertEqual(len(favs_after), 0)

    def test_07_edit_and_delete_permissions(self):
        """Verifica que solo uploader o miembros con soundboard.manage puedan editar/eliminar sonidos."""
        mp3 = make_valid_mp3_bytes(duration_sec=2.0)
        comm_sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            owner_id=self.comm_a_id,
            title="Himno del Gremio",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        sound_id = comm_sound["id"]

        # 1. regular_id intenta editar -> 403 Forbidden
        res = self.client.patch(
            f"/api/v1/sounds/{sound_id}",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={"title": "Hackeado"}
        )
        self.assertEqual(res.status_code, 403)

        # 2. dj_id (tiene soundboard.manage) edita volumen y cooldown -> 200 OK
        res_dj = self.client.patch(
            f"/api/v1/sounds/{sound_id}",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={"volume_scale": 1.5, "cooldown_seconds": 8}
        )
        self.assertEqual(res_dj.status_code, 200)
        self.assertEqual(res_dj.get_json()["volume_scale"], 1.5)
        self.assertEqual(res_dj.get_json()["cooldown_seconds"], 8)

        # 3. regular_id intenta borrar -> 403 Forbidden
        res_del = self.client.delete(
            f"/api/v1/sounds/{sound_id}",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        )
        self.assertEqual(res_del.status_code, 403)

        # 4. dj_id elimina -> 200 OK
        res_del_dj = self.client.delete(
            f"/api/v1/sounds/{sound_id}",
            headers={"Authorization": f"Bearer {self.token_dj}"}
        )
        self.assertEqual(res_del_dj.status_code, 200)

    def test_08_sound_play_authorization_success(self):
        """Autoriza exitosamente la reproducción de un sonido en la sala de voz."""
        mp3 = make_valid_mp3_bytes(duration_sec=3.0)
        sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            owner_id=self.comm_a_id,
            title="Aplausos",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        sound_id = sound["id"]

        # dj_id tiene permiso soundboard.play y solicita reproducir en voice_chan_id
        res = self.client.post(
            f"/api/v1/sounds/{sound_id}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["authorized"])
        self.assertEqual(data["sound_id"], sound_id)
        self.assertEqual(data["channel_id"], self.voice_chan_id)
        self.assertIn("storage_key", data)

    def test_09_sound_play_cooldown_rate_limit(self):
        """Rechaza reproducción con HTTP 429 si se repite antes de vencer el cooldown."""
        mp3 = make_valid_mp3_bytes(duration_sec=2.0)
        sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            owner_id=self.comm_a_id,
            title="Bocina Spam",
            file_bytes=mp3,
            cooldown_seconds=5,
            storage_dir=self.storage_dir
        )
        sound_id = sound["id"]

        # Primer play -> 200 OK
        res1 = self.client.post(
            f"/api/v1/sounds/{sound_id}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res1.status_code, 200)

        # Segundo play inmediato -> 429 Too Many Requests
        res2 = self.client.post(
            f"/api/v1/sounds/{sound_id}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res2.status_code, 429)
        self.assertEqual(res2.get_json()["error"], "SOUND_COOLDOWN")
        self.assertIn("Retry-After", res2.headers)
        self.assertGreater(res2.get_json()["retry_after"], 0)

    def test_10_sound_play_cross_community_isolation(self):
        """Comprueba aislamiento fail-closed: rechaza reproducción en otra comunidad o sin permiso."""
        # Crear Comunidad B aislada
        comm_b = self.service.create_community(
            owner_id=self.stranger_id,
            name="Comunidad Rival B",
            slug="comunidad-rival-b"
        )
        mp3 = make_valid_mp3_bytes(duration_sec=2.0)
        sound_b = self.service.upload_sound(
            actor_id=self.stranger_id,
            owner_type="community",
            owner_id=comm_b["id"],
            title="Sonido Privado B",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )

        # 1. Intentar reproducir sonido de Comunidad B en canal de Comunidad A -> 403 Forbidden
        res_cross = self.client.post(
            f"/api/v1/sounds/{sound_b['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_dj}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res_cross.status_code, 403)

        # 2. stranger_id no es miembro de Comunidad A ni tiene permiso -> 403 Forbidden
        comm_a_sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            owner_id=self.comm_a_id,
            title="Sonido Oficial A",
            file_bytes=mp3,
            storage_dir=self.storage_dir
        )
        res_unauth = self.client.post(
            f"/api/v1/sounds/{comm_a_sound['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_stranger}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res_unauth.status_code, 403)

        # 3. Sobrescritura de canal deniega soundboard.play a regular_id -> 403 Forbidden
        self.service.set_channel_override(
            community_id=self.comm_a_id,
            channel_id=self.voice_chan_id,
            requester_id=self.owner_id,
            target_type="user",
            target_id=self.regular_id,
            permission_id="soundboard.play",
            allow=False,
            deny=True
        )
        res_denied = self.client.post(
            f"/api/v1/sounds/{comm_a_sound['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={"channel_id": self.voice_chan_id}
        )
        self.assertEqual(res_denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
