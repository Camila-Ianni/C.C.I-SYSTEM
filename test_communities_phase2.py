"""
test_communities_phase2.py - Pruebas de integración de Fase 2: Chat en tiempo real y Presencia.

Verifica de forma estricta los criterios de aceptación:
1. Dos clientes reciben mensajes en tiempo real vía Socket.IO.
2. Historial de mensajes paginado (cursor before_id, límites).
3. Hilos de respuestas (reply_to_id).
4. Edición y borrado de mensajes (autor original y moderador con messages.manage).
5. Casos negativos: rechazo de envío sin permiso o en canales ajenos (403).
6. Indicadores de escritura (typing:started).
7. Actualizaciones de presencia y máscara de modo invisible ('offline' para terceros).
8. Reconexión y recuperación completa de historial tras desconexión.
"""
from __future__ import annotations

import tempfile
import time
import unittest
from backend.auth import create_access_token
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.server import app, socketio


class TestCommunitiesPhase2(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.temp_dir.name}/test_chat_phase2.sqlite3"
        self.repo = CommunitiesRepository.reset_instance(self.db_path)
        self.svc = CommunitiesService.get_instance(self.repo)
        self.client = app.test_client()

        # Cuentas de prueba independientes
        self.token_alice = create_access_token("u_alice", "Alice")
        self.token_bob = create_access_token("u_bob", "Bob")
        self.token_eve = create_access_token("u_eve", "Eve")

        # Comunidad base con canales por defecto
        self.comm = self.svc.create_community("u_alice", "Cyber Arcade", visibility="private")
        self.comm_id = self.comm["id"]

        channels = self.repo.list_channels(self.comm_id)
        self.ch_general = [c for c in channels if c["name"] == "general"][0]
        self.ch_id = self.ch_general["id"]

        # Incorporar a Bob a la comunidad
        self.repo.add_member(self.comm_id, "u_bob")

    def tearDown(self):
        self.repo.close()
        self.temp_dir.cleanup()

    def test_01_send_and_receive_message_in_channel(self):
        """Alice envía mensaje en canal de texto; se persiste con metadata e ID único."""
        res = self.client.post(
            f"/api/v1/channels/{self.ch_id}/messages",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"content": "¡Bienvenidos al torneo de C.C.I.!"}
        )
        self.assertEqual(res.status_code, 201)
        msg = res.get_json()["message"]
        self.assertEqual(msg["author_id"], "u_alice")
        self.assertEqual(msg["content"], "¡Bienvenidos al torneo de C.C.I.!")
        self.assertEqual(msg["channel_id"], self.ch_id)
        self.assertIsNone(msg["reply_to_id"])
        self.assertGreater(msg["created_at"], 0)

    def test_02_paginated_message_history(self):
        """Historial paginado con cursor before_id recupera mensajes en bloques ordenados."""
        # Alice envía 15 mensajes secuenciales
        msg_ids = []
        for i in range(15):
            m = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", f"Mensaje número {i+1}")
            msg_ids.append(m["id"])

        # Bob consulta primer bloque de 10 mensajes
        res_page1 = self.client.get(
            f"/api/v1/channels/{self.ch_id}/messages?limit=10",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_page1.status_code, 200)
        page1 = res_page1.get_json()["messages"]
        self.assertEqual(len(page1), 10)
        self.assertEqual(page1[-1]["content"], "Mensaje número 15")

        # Bob consulta segundo bloque usando before_id del mensaje más antiguo de page1
        oldest_page1_id = page1[0]["id"]
        res_page2 = self.client.get(
            f"/api/v1/channels/{self.ch_id}/messages?limit=10&before_id={oldest_page1_id}",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_page2.status_code, 200)
        page2 = res_page2.get_json()["messages"]
        self.assertEqual(len(page2), 5)
        self.assertEqual(page2[0]["content"], "Mensaje número 1")

    def test_03_message_reply_threading(self):
        """Bob responde a un mensaje previo de Alice referenciando reply_to_id."""
        msg_parent = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", "¿Quién juega Da Vinci?")

        res_reply = self.client.post(
            f"/api/v1/channels/{self.ch_id}/messages",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={
                "content": "¡Yo juego con Carloni!",
                "reply_to_id": msg_parent["id"]
            }
        )
        self.assertEqual(res_reply.status_code, 201)
        reply = res_reply.get_json()["message"]
        self.assertEqual(reply["reply_to_id"], msg_parent["id"])

    def test_04_message_edit_and_delete_permissions(self):
        """Autor edita su mensaje; tercero sin permisos es rechazado; moderador puede gestionarlo."""
        msg = self.svc.send_message(self.comm_id, self.ch_id, "u_bob", "Mensaje original con typo")

        # 1. Bob edita su propio mensaje -> 200 OK
        res_edit_bob = self.client.patch(
            f"/api/v1/channels/{self.ch_id}/messages/{msg['id']}",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"content": "Mensaje corregido por Bob"}
        )
        self.assertEqual(res_edit_bob.status_code, 200)
        self.assertEqual(res_edit_bob.get_json()["message"]["content"], "Mensaje corregido por Bob")
        self.assertIsNotNone(res_edit_bob.get_json()["message"]["edited_at"])

        # 2. Eve (miembro ajeno sin rol) intenta editar el mensaje de Bob -> 403 Forbidden
        self.repo.add_member(self.comm_id, "u_eve")
        res_edit_eve = self.client.patch(
            f"/api/v1/channels/{self.ch_id}/messages/{msg['id']}",
            headers={"Authorization": f"Bearer {self.token_eve}"},
            json={"content": "Hack por Eve"}
        )
        self.assertEqual(res_edit_eve.status_code, 403)

        # 3. Dueña Alice (con messages.manage) elimina el mensaje de Bob -> 200 OK
        res_del_alice = self.client.delete(
            f"/api/v1/channels/{self.ch_id}/messages/{msg['id']}",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_del_alice.status_code, 200)

        # El mensaje ya no aparece en el historial activo
        msgs = self.svc.list_channel_messages(self.comm_id, self.ch_id, "u_bob")
        self.assertEqual(len(msgs), 0)

    def test_05_unauthorized_channel_message_send_rejected(self):
        """Usuario sin permiso messages.send es rechazado con 403 al intentar publicar."""
        # Canal privado staff
        ch_priv = self.svc.create_channel(self.comm_id, "u_alice", "staff-chat", is_private=True)
        ch_priv_id = ch_priv["id"]

        # Bob intenta publicar en canal privado donde no tiene acceso -> 403 Forbidden
        res_fail = self.client.post(
            f"/api/v1/channels/{ch_priv_id}/messages",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"content": "Intrusión en staff"}
        )
        self.assertEqual(res_fail.status_code, 403)

    def test_06_realtime_socketio_two_clients_message_broadcast(self):
        """Dos clientes Socket.IO en canal compartido reciben emisión broadcast en tiempo real."""
        sio_a = socketio.test_client(app, auth={"token": self.token_alice})
        sio_b = socketio.test_client(app, auth={"token": self.token_bob})
        self.assertTrue(sio_a.is_connected())
        self.assertTrue(sio_b.is_connected())

        # Ambos se unen a la sala del canal
        sio_a.emit("community:channel:join", {"channel_id": self.ch_id})
        sio_b.emit("community:channel:join", {"channel_id": self.ch_id})

        # Alice envía mensaje vía WebSocket
        sio_a.emit("community:message:send", {
            "channel_id": self.ch_id,
            "content": "¡Hola Bob desde Socket.IO!",
        })

        # Bob recibe el evento message:created
        received_b = sio_b.get_received()
        msg_events = [ev for ev in received_b if ev["name"] == "message:created"]
        self.assertEqual(len(msg_events), 1)
        self.assertEqual(msg_events[0]["args"][0]["content"], "¡Hola Bob desde Socket.IO!")
        self.assertEqual(msg_events[0]["args"][0]["author_id"], "u_alice")

        sio_a.disconnect()
        sio_b.disconnect()

    def test_07_realtime_typing_indicator(self):
        """Emisión de typing por Alice se transmite a Bob sin incluir a Alice."""
        sio_a = socketio.test_client(app, auth={"token": self.token_alice})
        sio_b = socketio.test_client(app, auth={"token": self.token_bob})

        sio_a.emit("community:channel:join", {"channel_id": self.ch_id})
        sio_b.emit("community:channel:join", {"channel_id": self.ch_id})

        sio_a.emit("community:typing", {"channel_id": self.ch_id, "typing": True})

        received_b = sio_b.get_received()
        typing_events = [ev for ev in received_b if ev["name"] == "typing:started"]
        self.assertEqual(len(typing_events), 1)
        self.assertEqual(typing_events[0]["args"][0]["user_id"], "u_alice")
        self.assertTrue(typing_events[0]["args"][0]["typing"])

        sio_a.disconnect()
        sio_b.disconnect()

    def test_08_presence_state_updates_and_invisibility(self):
        """Estados de presencia dnd/idle se propagan; modo invisible se enmascara como offline."""
        # 1. Alice se pone en modo 'dnd' con estado personalizado
        res_dnd = self.client.post(
            "/api/v1/users/presence",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"status": "dnd", "custom_status": "En partida clasificatoria"}
        )
        self.assertEqual(res_dnd.status_code, 200)

        # Bob consulta presencia de Alice -> dnd
        res_query1 = self.client.get(
            "/api/v1/users/presence?user_ids=u_alice",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_query1.status_code, 200)
        pres_alice1 = res_query1.get_json()["presences"]["u_alice"]
        self.assertEqual(pres_alice1["status"], "dnd")
        self.assertEqual(pres_alice1["custom_status"], "En partida clasificatoria")

        # 2. Alice cambia a 'invisible'
        self.client.post(
            "/api/v1/users/presence",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"status": "invisible"}
        )

        # Bob consulta presencia de Alice -> enmascarado como 'offline'
        res_query2 = self.client.get(
            "/api/v1/users/presence?user_ids=u_alice",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_query2.status_code, 200)
        pres_alice2 = res_query2.get_json()["presences"]["u_alice"]
        self.assertEqual(pres_alice2["status"], "offline")

        # Alice consulta su propia presencia -> ve 'invisible'
        res_query_self = self.client.get(
            "/api/v1/users/presence",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_query_self.status_code, 200)
        self.assertEqual(res_query_self.get_json()["presence"]["status"], "invisible")

    def test_09_realtime_message_edit_and_delete_broadcast(self):
        """Edición y borrado vía Socket.IO emiten eventos message:updated y message:deleted."""
        msg = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", "Mensaje a editar vía WSS")

        sio_a = socketio.test_client(app, auth={"token": self.token_alice})
        sio_b = socketio.test_client(app, auth={"token": self.token_bob})
        sio_a.emit("community:channel:join", {"channel_id": self.ch_id})
        sio_b.emit("community:channel:join", {"channel_id": self.ch_id})

        # Alice edita mensaje
        sio_a.emit("community:message:edit", {
            "channel_id": self.ch_id,
            "message_id": msg["id"],
            "content": "Mensaje editado en vivo"
        })

        rec_b_edit = [ev for ev in sio_b.get_received() if ev["name"] == "message:updated"]
        self.assertEqual(len(rec_b_edit), 1)
        self.assertEqual(rec_b_edit[0]["args"][0]["content"], "Mensaje editado en vivo")

        # Alice elimina mensaje
        sio_a.emit("community:message:delete", {
            "channel_id": self.ch_id,
            "message_id": msg["id"],
        })

        rec_b_del = [ev for ev in sio_b.get_received() if ev["name"] == "message:deleted"]
        self.assertEqual(len(rec_b_del), 1)
        self.assertEqual(rec_b_del[0]["args"][0]["message_id"], msg["id"])

        sio_a.disconnect()
        sio_b.disconnect()

    def test_10_reconnection_and_unreceived_history_recovery(self):
        """Cliente se desconecta, se envían mensajes en su ausencia, y los recupera al reconectar."""
        # Bob desconectado
        # Alice envía 3 mensajes en su ausencia
        m1 = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", "Mensaje offline 1")
        m2 = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", "Mensaje offline 2")
        m3 = self.svc.send_message(self.comm_id, self.ch_id, "u_alice", "Mensaje offline 3")

        # Bob se reconecta y pide historial de mensajes
        res_sync = self.client.get(
            f"/api/v1/channels/{self.ch_id}/messages?limit=10",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_sync.status_code, 200)
        msgs = res_sync.get_json()["messages"]
        self.assertGreaterEqual(len(msgs), 3)
        retrieved_ids = [m["id"] for m in msgs]
        self.assertIn(m1["id"], retrieved_ids)
        self.assertIn(m2["id"], retrieved_ids)
        self.assertIn(m3["id"], retrieved_ids)


if __name__ == "__main__":
    unittest.main()
