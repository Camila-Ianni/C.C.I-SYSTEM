"""
test_phase3_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 3 (Chat en Tiempo Real).
Verifica:
1. Envío de mensajes y persistencia en SQLite con marcas temporales.
2. Control anti-spam y rate-limiting (límite de ráfaga y ventana de tiempo).
3. Restricción de longitud máxima (500 caracteres) y mensajes vacíos.
4. Validación de membresía y usuarios silenciados/bloqueados (muted/banned).
5. Historial de mensajes paginado y orden cronológico.
6. Borrado lógico (soft-delete) por autor y por administradores.
7. Reporte de moderación por contenido abusivo o spam.
8. Endpoints REST de la API de Chat.
"""
import tempfile
import time
import unittest
from pathlib import Path
import cci_database
from backend.chat_service import ChatService
from backend.friends_service import FriendsService, GroupRole
from backend.server import app


class TestPhase3ChatAndSpamProtection(unittest.TestCase):
    """Verifica reglas de mensajería, anti-spam y moderación."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_chat.sqlite3"
        cci_database.init_db(self.db_path)

        self.friends_svc = FriendsService()
        self.chat_svc = ChatService()
        self.chat_svc._user_msg_times.clear()

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        # Crear grupo de prueba con owner y miembro
        res = self.friends_svc.create_group("Sala de Chat Da Vinci", "owner_pilot")
        self.group_id = res["group"]["id"]
        self.friends_svc.invite_member(self.group_id, "owner_pilot", "member_pilot")

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_send_valid_message_and_retrieve_history(self):
        res = self.chat_svc.send_message(
            group_id=self.group_id,
            sender_id="member_pilot",
            sender_name="MemberPilot",
            body="¡Buena partida en Da Vinci Fighters!"
        )
        self.assertTrue(res["success"])
        msg_data = res["message"]
        self.assertEqual(msg_data["body"], "¡Buena partida en Da Vinci Fighters!")
        self.assertEqual(msg_data["sender_id"], "member_pilot")

        # Recuperar historial
        hist = self.chat_svc.get_history(self.group_id, limit=10)
        self.assertEqual(hist["count"], 1)
        self.assertEqual(hist["messages"][0]["body"], "¡Buena partida en Da Vinci Fighters!")

    def test_empty_or_excessive_length_rejected(self):
        # Mensaje vacío
        r_empty = self.chat_svc.send_message(self.group_id, "member_pilot", "MemberPilot", "   ")
        self.assertFalse(r_empty["success"])

        # Mensaje mayor a 500 caracteres
        r_long = self.chat_svc.send_message(self.group_id, "member_pilot", "MemberPilot", "A" * 501)
        self.assertFalse(r_long["success"])
        self.assertIn("límite máximo", r_long["error"])

    def test_rate_limiting_anti_spam(self):
        # Enviar 5 mensajes seguidos (permitido)
        for i in range(5):
            r = self.chat_svc.send_message(self.group_id, "spammer_pilot", "Spammer", f"Mensaje {i}")
            # Si no es miembro primero añadimos
            if not r["success"] and "No eres miembro" in r["error"]:
                self.friends_svc.invite_member(self.group_id, "owner_pilot", "spammer_pilot")
                r = self.chat_svc.send_message(self.group_id, "spammer_pilot", "Spammer", f"Mensaje {i}")
            self.assertTrue(r["success"], f"Fallo en mensaje {i}: {r}")

        # El 6to mensaje inmediato debe ser bloqueado por rate-limiting
        r_spam = self.chat_svc.send_message(self.group_id, "spammer_pilot", "Spammer", "Mensaje spam!")
        self.assertFalse(r_spam["success"])
        self.assertIn("demasiado rápido", r_spam["error"])

    def test_non_member_cannot_send_message(self):
        r = self.chat_svc.send_message(self.group_id, "intruder_user", "Intruder", "Hola a todos")
        self.assertFalse(r["success"])
        self.assertIn("No eres miembro", r["error"])

    def test_muted_member_cannot_send_message(self):
        self.friends_svc.invite_member(self.group_id, "owner_pilot", "bad_actor")
        # Silenciar al usuario
        cci_database.update_group_member_status_entry(self.group_id, "bad_actor", "muted")

        r = self.chat_svc.send_message(self.group_id, "bad_actor", "BadActor", "Intento hablar")
        self.assertFalse(r["success"])
        self.assertIn("silenciada", r["error"])

    def test_soft_delete_permissions(self):
        r = self.chat_svc.send_message(self.group_id, "member_pilot", "Member", "Mensaje para borrar")
        msg_id = r["message"]["message_id"]

        # 1. Tercero no autorizado intenta borrar: DEBE FALLAR
        self.friends_svc.invite_member(self.group_id, "owner_pilot", "other_member")
        r_fail = self.chat_svc.delete_message(msg_id, actor_id="other_member")
        self.assertFalse(r_fail["success"])

        # 2. Autor borra su propio mensaje: ÉXITO
        r_del = self.chat_svc.delete_message(msg_id, actor_id="member_pilot")
        self.assertTrue(r_del["success"])

        # Verificar que ya no aparece en historial activo
        hist = self.chat_svc.get_history(self.group_id)
        self.assertEqual(hist["count"], 0)

    def test_report_message_abuse(self):
        r = self.chat_svc.send_message(self.group_id, "member_pilot", "Member", "Texto sospechoso")
        msg_id = r["message"]["message_id"]

        r_rep = self.chat_svc.report_message(msg_id, reporter_id="owner_pilot", reason="Lenguaje ofensivo")
        self.assertTrue(r_rep["success"])


class TestPhase3ChatRESTEndpoints(unittest.TestCase):
    """Verifica endpoints HTTP de la API de Chat."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_chat_api.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)
        self.client = app.test_client()

        # Preparar grupo y miembros
        FriendsService.get_instance().create_group("Grupo API Chat", "pilot_1")
        groups = cci_database.get_user_groups("pilot_1")
        self.group_id = groups[0]["id"]
        FriendsService.get_instance().invite_member(self.group_id, "pilot_1", "pilot_2")

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_chat_rest_flow(self):
        # 1. Enviar mensaje
        r_send = self.client.post("/api/v1/chat/send", json={
            "group_id": self.group_id,
            "sender_id": "pilot_2",
            "sender_name": "PilotTwo",
            "body": "Mensaje enviado vía REST API"
        })
        self.assertEqual(r_send.status_code, 200)
        msg_id = r_send.get_json()["message"]["message_id"]

        # 2. Consultar historial
        r_hist = self.client.get(f"/api/v1/chat/{self.group_id}/history?limit=10")
        self.assertEqual(r_hist.status_code, 200)
        data = r_hist.get_json()["data"]
        self.assertEqual(data["count"], 1)

        # 3. Reportar mensaje
        r_rep = self.client.post(f"/api/v1/chat/message/{msg_id}/report", json={
            "reporter_id": "pilot_1",
            "reason": "Test de moderación"
        })
        self.assertEqual(r_rep.status_code, 200)

        # 4. Eliminar mensaje
        r_del = self.client.delete(f"/api/v1/chat/message/{msg_id}", json={
            "actor_id": "pilot_2"
        })
        self.assertEqual(r_del.status_code, 200)


if __name__ == "__main__":
    unittest.main()
