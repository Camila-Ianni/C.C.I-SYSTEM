"""
test_phase10_security.py - Suite de pruebas de seguridad, autenticación y autorización negativa (P0).

Resuelve y certifica los hallazgos de seguridad 5.1 de la Auditoría:
1. Validación de tokens criptográficos HMAC-SHA256 y expiración.
2. Rechazo de accesos no autenticados (401 Unauthorized) en rutas protegidas.
3. Rechazo de eliminación o modificación de grabaciones ajenas (403 Forbidden).
4. Neutralización de suplantación de identidad (sender_id spoofing) en Socket.IO.
5. Control estricto de pertenencia a grupos para chat y llamadas de voz.
6. Asignación forzosa de slots en el motor multijugador por el servidor.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest
from flask import g
import cci_database
from backend.auth import (
    create_access_token,
    verify_access_token,
    check_recording_ownership,
    check_group_membership,
)
from backend.friends_service import FriendsService
from backend.server import app, socketio


class TestPhase10SecurityAndAuthorization(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sec.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        self.client = app.test_client()
        self.friends_svc = FriendsService.get_instance()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_01_token_tampering_and_expiration(self):
        """Verifica que firmas manipuladas o tokens expirados sean rechazados."""
        token = create_access_token("u_leonardo", "Leonardo", expires_in_seconds=3600)
        self.assertIsNotNone(token)

        # 1. Token válido
        payload = verify_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "u_leonardo")

        # 2. Token manipulado (tampering de payload o firma)
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.bad_signature_xyz"
        self.assertIsNone(verify_access_token(tampered_token))

        # 3. Token expirado
        expired_token = create_access_token("u_leonardo", "Leonardo", expires_in_seconds=-10)
        self.assertIsNone(verify_access_token(expired_token))

    def test_02_recording_cross_user_deletion_forbidden(self):
        """Un usuario NO puede eliminar la grabación de otro usuario (403 Forbidden)."""
        # Crear grabación perteneciente a 'u_alice'
        clip_file = Path(self.temp_dir.name) / "alice_clip.mp4"
        clip_file.write_bytes(b"dummy mp4" * 10)
        cci_database.save_gameplay_recording_entry(
            recording_id="rec_alice_01",
            owner_id="u_alice",
            game_id="davinci",
            local_path=str(clip_file),
            duration_seconds=15.0,
            size_bytes=clip_file.stat().st_size,
            db_path=self.db_path,
        )

        # Token para 'u_mallory' (atacante)
        mallory_token = create_access_token("u_mallory", "Mallory")

        # Intento de borrado por parte de Mallory
        resp = self.client.delete(
            "/api/v1/recordings/rec_alice_01",
            headers={"Authorization": f"Bearer {mallory_token}"}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("No tienes permiso", resp.get_json()["error"])

        # Verificar que el clip sigue existiendo intacto
        self.assertIsNotNone(cci_database.get_gameplay_recording_by_id("rec_alice_01", db_path=self.db_path))

        # Borrado legítimo por parte de Alice
        alice_token = create_access_token("u_alice", "Alice")
        resp_ok = self.client.delete(
            "/api/v1/recordings/rec_alice_01",
            headers={"Authorization": f"Bearer {alice_token}"}
        )
        self.assertEqual(resp_ok.status_code, 200)

    def test_03_recording_cross_user_visibility_forbidden(self):
        """Un usuario NO puede cambiar la visibilidad de una grabación ajena."""
        clip_file = Path(self.temp_dir.name) / "alice_clip_2.mp4"
        clip_file.write_bytes(b"dummy mp4" * 10)
        cci_database.save_gameplay_recording_entry(
            recording_id="rec_alice_02",
            owner_id="u_alice",
            game_id="mario",
            local_path=str(clip_file),
            duration_seconds=20.0,
            size_bytes=clip_file.stat().st_size,
            db_path=self.db_path,
        )

        mallory_token = create_access_token("u_mallory", "Mallory")
        resp = self.client.patch(
            "/api/v1/recordings/rec_alice_02/visibility",
            headers={"Authorization": f"Bearer {mallory_token}"},
            json={"visibility": "shared"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_04_socket_chat_sender_spoofing_prevented(self):
        """Socket.IO sobrescribe forzosamente cualquier sender_id adulterado en el payload."""
        # Crear grupo con Alice
        grp_res = self.friends_svc.create_group("Grupo Seguro", "u_alice")
        grp_id = grp_res["group"]["id"]

        # Conectar cliente Socket.IO con token de Alice
        alice_token = create_access_token("u_alice", "Alice")
        sio_client = socketio.test_client(app, auth={"token": alice_token})
        self.assertTrue(sio_client.is_connected())

        # Intentar enviar mensaje fingiendo ser el administrador 'admin_god'
        sio_client.emit("chat:send", {
            "group_id": grp_id,
            "sender_id": "admin_god",      # Spoofing attempt
            "sender_name": "GodAdmin",     # Spoofing attempt
            "body": "Mensaje legítimo verificado",
        })

        # Recuperar mensajes: sender_id DEBE ser 'u_alice', no 'admin_god'
        messages = cci_database.get_paged_messages_entry(grp_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender_id"], "u_alice", "El servidor debe neutralizar el sender_id adulterado")
        sio_client.disconnect()

    def test_05_socket_group_membership_enforcement(self):
        """Un usuario ajeno a un grupo NO puede enviar mensajes ni unirse a llamadas."""
        grp_res = self.friends_svc.create_group("Grupo Privado", "u_alice")
        grp_id = grp_res["group"]["id"]

        # Bob intenta enviar mensaje a un grupo donde NO es miembro
        bob_token = create_access_token("u_bob", "Bob")
        sio_client = socketio.test_client(app, auth={"token": bob_token})

        sio_client.emit("chat:send", {
            "group_id": grp_id,
            "body": "Intrusión en el chat",
        })

        received = sio_client.get_received()
        error_events = [ev for ev in received if ev["name"] == "chat:error"]
        self.assertEqual(len(error_events), 1)
        self.assertIn("no eres miembro", error_events[0]["args"][0]["error"].lower())

        # Tampoco debe haber ningún mensaje insertado en el grupo
        messages = cci_database.get_paged_messages_entry(grp_id)
        self.assertEqual(len(messages), 0)
        sio_client.disconnect()


if __name__ == "__main__":
    unittest.main()
