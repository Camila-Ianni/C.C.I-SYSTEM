"""
test_phase2_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 2 (Amigos y Grupos).
Verifica:
1. Solicitudes de amistad (envío, aceptación, rechazo, cancelación).
2. Bloqueo de usuarios e impedimento de interacción.
3. Presencia en tiempo real (online, away, busy, offline) y juego activo.
4. Creación de grupos y asignación automática del rol 'owner'.
5. Control de acceso basado en roles (RBAC):
   - Owner puede invitar, expulsar y cambiar roles.
   - Admin puede invitar y expulsar members, pero NO al owner ni a otros admins.
   - Members no pueden invitar ni expulsar.
6. Transferencia de propiedad y abandono seguro del grupo.
7. Endpoints REST de la API de Amigos y Grupos.
"""
import tempfile
import unittest
from pathlib import Path
import cci_database
from backend.friends_service import FriendsService, GroupRole, PresenceStatus
from backend.auth import create_access_token
from backend.server import app


class TestPhase2FriendsAndPresence(unittest.TestCase):
    """Verifica solicitudes de amistad y presencia en tiempo real."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_friends.sqlite3"
        cci_database.init_db(self.db_path)
        self.svc = FriendsService()
        self.svc._presence.clear()

        # Configurar cci_database para apuntar temporalmente a la base de prueba
        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_send_and_accept_friend_request(self):
        # Enviar solicitud de A a B
        res = self.svc.send_friend_request("pilot_a", "pilot_b")
        self.assertTrue(res["success"])

        # Verificar lista de pendientes
        pending = cci_database.get_pending_friend_requests("pilot_b")
        self.assertEqual(len(pending["incoming"]), 1)
        self.assertEqual(pending["incoming"][0]["requester_id"], "pilot_a")

        # B acepta la solicitud
        acc = self.svc.accept_friend_request("pilot_b", "pilot_a")
        self.assertTrue(acc["success"])

        # Ambos son amigos
        friends_a = self.svc.get_friends_list("pilot_a")
        friends_b = self.svc.get_friends_list("pilot_b")
        self.assertEqual(len(friends_a), 1)
        self.assertEqual(len(friends_b), 1)
        self.assertEqual(friends_a[0]["friend_id"], "pilot_b")
        self.assertEqual(friends_b[0]["friend_id"], "pilot_a")

    def test_cannot_friend_self(self):
        res = self.svc.send_friend_request("pilot_a", "pilot_a")
        self.assertFalse(res["success"])

    def test_cancel_and_reject_friend_request(self):
        # Cancelación por el emisor
        self.svc.send_friend_request("pilot_a", "pilot_c")
        cancel_res = self.svc.cancel_friend_request("pilot_a", "pilot_c")
        self.assertTrue(cancel_res["success"])
        pending_c = cci_database.get_pending_friend_requests("pilot_c")
        self.assertEqual(len(pending_c["incoming"]), 0)

        # Rechazo por el receptor
        self.svc.send_friend_request("pilot_a", "pilot_d")
        rej_res = self.svc.reject_friend_request("pilot_d", "pilot_a")
        self.assertTrue(rej_res["success"])
        friends_d = self.svc.get_friends_list("pilot_d")
        self.assertEqual(len(friends_d), 0)

    def test_block_user_prevents_request(self):
        self.svc.block_user("pilot_a", "spammer")
        res = self.svc.send_friend_request("spammer", "pilot_a")
        self.assertFalse(res["success"])

    def test_presence_status_and_current_game(self):
        self.svc.update_presence("pilot_b", status="online", current_game="Da Vinci Fighters")
        p = self.svc.get_presence("pilot_b")
        self.assertEqual(p["status"], "online")
        self.assertEqual(p["current_game"], "Da Vinci Fighters")

        # Agregar como amigos y verificar que la lista expone la presencia
        self.svc.send_friend_request("pilot_a", "pilot_b")
        self.svc.accept_friend_request("pilot_b", "pilot_a")

        friends = self.svc.get_friends_list("pilot_a")
        self.assertEqual(friends[0]["presence"], "online")
        self.assertEqual(friends[0]["current_game"], "Da Vinci Fighters")


class TestPhase2GroupsAndRBAC(unittest.TestCase):
    """Verifica creación de grupos, roles y jerarquía de permisos."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_groups.sqlite3"
        cci_database.init_db(self.db_path)
        self.svc = FriendsService()

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_group_creation_and_owner_role(self):
        res = self.svc.create_group("Escuadrón Da Vinci", "owner_pilot")
        self.assertTrue(res["success"])
        grp = res["group"]
        self.assertEqual(grp["name"], "Escuadrón Da Vinci")
        self.assertEqual(grp["owner_id"], "owner_pilot")
        self.assertEqual(len(grp["members"]), 1)
        self.assertEqual(grp["members"][0]["role"], GroupRole.OWNER.value)

    def test_invitation_permissions(self):
        res = self.svc.create_group("Clan Arcade", "owner_pilot")
        group_id = res["group"]["id"]

        # Owner invita a admin_pilot
        inv1 = self.svc.invite_member(group_id, "owner_pilot", "admin_pilot")
        self.assertTrue(inv1["success"])
        self.svc.update_role(group_id, "owner_pilot", "admin_pilot", GroupRole.ADMIN.value)

        # Admin invita a regular_pilot
        inv2 = self.svc.invite_member(group_id, "admin_pilot", "regular_pilot")
        self.assertTrue(inv2["success"])

        # Regular member intenta invitar: debe fallar
        inv3 = self.svc.invite_member(group_id, "regular_pilot", "intruder")
        self.assertFalse(inv3["success"])

    def test_kick_hierarchy_enforcement(self):
        res = self.svc.create_group("Clan Elite", "owner_pilot")
        group_id = res["group"]["id"]

        self.svc.invite_member(group_id, "owner_pilot", "admin_pilot")
        self.svc.update_role(group_id, "owner_pilot", "admin_pilot", GroupRole.ADMIN.value)
        self.svc.invite_member(group_id, "owner_pilot", "member_pilot")

        # Admin intenta expulsar al owner: DEBE FALLAR
        kick_owner = self.svc.kick_member(group_id, "admin_pilot", "owner_pilot")
        self.assertFalse(kick_owner["success"])

        # Admin expulsa a member_pilot: DEBE TENER ÉXITO
        kick_member = self.svc.kick_member(group_id, "admin_pilot", "member_pilot")
        self.assertTrue(kick_member["success"])

        # Owner expulsa a admin_pilot: DEBE TENER ÉXITO
        kick_admin = self.svc.kick_member(group_id, "owner_pilot", "admin_pilot")
        self.assertTrue(kick_admin["success"])

    def test_transfer_ownership_and_leave(self):
        res = self.svc.create_group("Retro Gamers", "owner_pilot")
        group_id = res["group"]["id"]
        self.svc.invite_member(group_id, "owner_pilot", "second_pilot")

        # Transferir propiedad
        trans = self.svc.transfer_ownership(group_id, "owner_pilot", "second_pilot")
        self.assertTrue(trans["success"])

        info = self.svc.get_group_info(group_id)
        self.assertEqual(info["owner_id"], "second_pilot")

        # Dueño anterior sale del grupo
        leave_res = self.svc.leave_group(group_id, "owner_pilot")
        self.assertTrue(leave_res["success"])
        info2 = self.svc.get_group_info(group_id)
        self.assertEqual(len(info2["members"]), 1)


class TestPhase2RESTEndpoints(unittest.TestCase):
    """Verifica los endpoints REST de Amigos y Grupos."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_api.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_rest_friend_flow(self):
        token_a = create_access_token("rest_a", "RestA")
        token_b = create_access_token("rest_b", "RestB")

        # 0. Verificación negativa: sin token debe fallar con 401
        r_unauth = self.client.post("/api/v1/friends/request", json={"addressee_id": "rest_b"})
        self.assertEqual(r_unauth.status_code, 401)

        # 1. Enviar solicitud autenticada
        r = self.client.post("/api/v1/friends/request", json={
            "addressee_id": "rest_b"
        }, headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(r.status_code, 200)

        # 2. Consultar lista
        r_get = self.client.get("/api/v1/friends/rest_b", headers={"Authorization": f"Bearer {token_b}"})
        self.assertEqual(r_get.status_code, 200)
        data = r_get.get_json()
        self.assertEqual(len(data["pending"]["incoming"]), 1)

        # 3. Aceptar solicitud
        r_acc = self.client.post("/api/v1/friends/respond", json={
            "requester_id": "rest_a",
            "action": "accept"
        }, headers={"Authorization": f"Bearer {token_b}"})
        self.assertEqual(r_acc.status_code, 200)

    def test_rest_group_flow(self):
        token_api = create_access_token("user_api", "UserApi")

        # 0. Verificación negativa: sin token debe fallar con 401
        r_unauth = self.client.post("/api/v1/groups/create", json={"name": "Grupo REST"})
        self.assertEqual(r_unauth.status_code, 401)

        # Crear grupo autenticado
        r = self.client.post("/api/v1/groups/create", json={
            "name": "Grupo REST",
        }, headers={"Authorization": f"Bearer {token_api}"})
        self.assertEqual(r.status_code, 200)
        grp_id = r.get_json()["group"]["id"]

        # Consultar grupo
        r_get = self.client.get(f"/api/v1/groups/{grp_id}", headers={"Authorization": f"Bearer {token_api}"})
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(r_get.get_json()["group"]["name"], "Grupo REST")


if __name__ == "__main__":
    unittest.main()
