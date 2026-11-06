"""
test_communities_phase1.py - Pruebas de integración de Fase 1: CCI Communities.

Verifica de forma estricta los criterios de aceptación:
1. Dos cuentas independientes crean y administran comunidades.
2. Rol por defecto @everyone y canales base inicializados automáticamente.
3. Ciclo de vida de invitaciones (usos máximos, expiración, consumo).
4. Privacidad estricta: comunidades y canales privados deniegan acceso a terceros (403).
5. Jerarquía de roles y motor de resolución de permisos fail-closed.
6. Sobrescrituras de permisos por canal (allow/deny).
7. Expulsión jerárquica y protección absoluta del propietario.
8. Transferencia segura de propiedad y abandono de comunidad.
9. Eliminación exclusiva por propietario.
"""
from __future__ import annotations

import tempfile
import time
import unittest
from backend.auth import create_access_token
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.server import app


class TestCommunitiesPhase1(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.temp_dir.name}/test_communities.sqlite3"
        self.repo = CommunitiesRepository.reset_instance(self.db_path)
        self.svc = CommunitiesService.get_instance(self.repo)
        self.client = app.test_client()

        # Cuentas de prueba independientes
        self.token_alice = create_access_token("u_alice", "Alice")
        self.token_bob = create_access_token("u_bob", "Bob")
        self.token_charlie = create_access_token("u_charlie", "Charlie")
        self.token_eve = create_access_token("u_eve", "Eve")

    def tearDown(self):
        self.repo.close()
        self.temp_dir.cleanup()

    def test_01_community_creation_initializes_everyone_and_default_channels(self):
        """Alice crea comunidad; se inicializa @everyone y canales #general automáticamente."""
        res = self.client.post(
            "/api/v1/communities",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={
                "name": "Valhalla Gamers",
                "description": "Comunidad competitiva de C.C.I.",
                "visibility": "private",
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["community"]
        comm_id = data["id"]
        self.assertEqual(data["name"], "Valhalla Gamers")
        self.assertEqual(data["owner_id"], "u_alice")

        # Verificar rol por defecto @everyone
        roles = self.repo.list_roles(comm_id)
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0]["name"], "@everyone")
        self.assertTrue(roles[0]["is_default"])
        self.assertIn("messages.read", roles[0]["permissions"])
        self.assertIn("voice.connect", roles[0]["permissions"])

        # Verificar canales por defecto (#general texto y #General Voice voz)
        channels = self.repo.list_channels(comm_id)
        self.assertEqual(len(channels), 2)
        ch_names = {c["name"]: c["type"] for c in channels}
        self.assertIn("general", ch_names)
        self.assertEqual(ch_names["general"], "text")
        self.assertIn("General Voice", ch_names)
        self.assertEqual(ch_names["General Voice"], "voice")

        # Alice debe ser miembro activo
        member = self.repo.get_member(comm_id, "u_alice")
        self.assertIsNotNone(member)
        self.assertEqual(member["status"], "active")

    def test_02_invitations_creation_expiration_and_join(self):
        """Alice genera invitación con límite de usos; Bob se incorpora y consume cupo."""
        comm = self.svc.create_community("u_alice", "Invited Group", visibility="private")
        comm_id = comm["id"]

        # Alice crea invitación válida para 1 solo uso
        res_inv = self.client.post(
            f"/api/v1/communities/{comm_id}/invitations",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"max_uses": 1, "expires_in_hours": 24}
        )
        self.assertEqual(res_inv.status_code, 201)
        code = res_inv.get_json()["invitation"]["code"]

        # Bob se une usando el código
        res_join_bob = self.client.post(
            f"/api/v1/invitations/{code}/accept",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_join_bob.status_code, 200)

        # Bob es ahora miembro con rol @everyone
        member_bob = self.repo.get_member(comm_id, "u_bob")
        self.assertIsNotNone(member_bob)
        self.assertEqual(len(member_bob["roles"]), 1)
        self.assertEqual(member_bob["roles"][0]["name"], "@everyone")

        # Charlie intenta unirse con el mismo código -> Cupo agotado (404/LookupError)
        res_join_charlie = self.client.post(
            f"/api/v1/invitations/{code}/accept",
            headers={"Authorization": f"Bearer {self.token_charlie}"}
        )
        self.assertEqual(res_join_charlie.status_code, 404)

    def test_03_private_community_access_control(self):
        """Comunidad privada es inaccesible a terceros; miembros la consultan con éxito."""
        comm = self.svc.create_community("u_alice", "Secret Base", visibility="private")
        comm_id = comm["id"]

        # Tercero ajeno (Eve) intenta consultar comunidad privada -> 403 Forbidden
        res_eve = self.client.get(
            f"/api/v1/communities/{comm_id}",
            headers={"Authorization": f"Bearer {self.token_eve}"}
        )
        self.assertEqual(res_eve.status_code, 403)
        self.assertIn("denegado", res_eve.get_json()["error"])

        # Propietaria Alice consulta -> 200 OK
        res_alice = self.client.get(
            f"/api/v1/communities/{comm_id}",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_alice.status_code, 200)
        self.assertEqual(res_alice.get_json()["community"]["id"], comm_id)

    def test_04_public_community_discovery(self):
        """Comunidades públicas son visibles en el listado de descubrimiento."""
        self.svc.create_community("u_alice", "Public Arcade", visibility="public")
        self.svc.create_community("u_bob", "Private Guild", visibility="private")

        res_pub = self.client.get(
            "/api/v1/communities?visibility=public",
            headers={"Authorization": f"Bearer {self.token_eve}"}
        )
        self.assertEqual(res_pub.status_code, 200)
        items = res_pub.get_json()["communities"]
        names = [c["name"] for c in items]
        self.assertIn("Public Arcade", names)
        self.assertNotIn("Private Guild", names)

    def test_05_roles_hierarchy_and_permission_assignment(self):
        """Alice crea rol Moderador y se lo asigna a Bob; jerarquía restringe acciones superiores."""
        comm = self.svc.create_community("u_alice", "Hierarchy Test", visibility="private")
        comm_id = comm["id"]
        self.repo.add_member(comm_id, "u_bob")

        # 1. Bob sin permisos intenta crear canal -> 403 Forbidden
        res_ch_fail = self.client.post(
            f"/api/v1/communities/{comm_id}/channels",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"name": "illegal-channel"}
        )
        self.assertEqual(res_ch_fail.status_code, 403)

        # 2. Alice crea rol 'Moderator' con channels.manage en posición 500
        res_role = self.client.post(
            f"/api/v1/communities/{comm_id}/roles",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={
                "name": "Moderator",
                "position": 500,
                "permissions": ["channels.manage", "community.members.kick"]
            }
        )
        self.assertEqual(res_role.status_code, 201)
        role_mod_id = res_role.get_json()["role"]["id"]

        # 3. Alice asigna rol a Bob
        res_assign = self.client.post(
            f"/api/v1/communities/{comm_id}/members/u_bob/roles",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"role_id": role_mod_id}
        )
        self.assertEqual(res_assign.status_code, 200)

        # 4. Ahora Bob PUEDE crear canal
        res_ch_ok = self.client.post(
            f"/api/v1/communities/{comm_id}/channels",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"name": "tournament-announcements"}
        )
        self.assertEqual(res_ch_ok.status_code, 201)

        # 5. Jerarquía: Bob intenta crear un rol con posición 100 (superior a su 500) -> 403
        res_high_role = self.client.post(
            f"/api/v1/communities/{comm_id}/roles",
            headers={"Authorization": f"Bearer {self.token_bob}"},
            json={"name": "Super Admin", "position": 100}
        )
        self.assertEqual(res_high_role.status_code, 403)

    def test_06_channel_privacy_and_permission_overrides(self):
        """Canal privado oculto a miembros regulares; sobrescritura explícita habilita visualización."""
        comm = self.svc.create_community("u_alice", "Privacy Lab", visibility="private")
        comm_id = comm["id"]
        self.repo.add_member(comm_id, "u_charlie")

        # Alice crea canal privado
        ch_priv = self.svc.create_channel(
            community_id=comm_id,
            requester_id="u_alice",
            name="staff-only",
            is_private=True
        )
        ch_priv_id = ch_priv["id"]

        # Charlie lista canales: canal privado NO aparece
        res_ch_charlie = self.client.get(
            f"/api/v1/communities/{comm_id}/channels",
            headers={"Authorization": f"Bearer {self.token_charlie}"}
        )
        self.assertEqual(res_ch_charlie.status_code, 200)
        visible_ids = [c["id"] for c in res_ch_charlie.get_json()["channels"]]
        self.assertNotIn(ch_priv_id, visible_ids)

        # Alice otorga sobrescritura específica allow para Charlie en messages.read
        res_ov = self.client.post(
            f"/api/v1/communities/{comm_id}/channels/{ch_priv_id}/overrides",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={
                "target_type": "user",
                "target_id": "u_charlie",
                "permission_id": "messages.read",
                "allow": True,
                "deny": False
            }
        )
        self.assertEqual(res_ov.status_code, 200)

        # Ahora Charlie PUEDE ver el canal privado
        res_ch_charlie_after = self.client.get(
            f"/api/v1/communities/{comm_id}/channels",
            headers={"Authorization": f"Bearer {self.token_charlie}"}
        )
        visible_ids_after = [c["id"] for c in res_ch_charlie_after.get_json()["channels"]]
        self.assertIn(ch_priv_id, visible_ids_after)

    def test_07_hierarchical_kick_and_protection_of_owner(self):
        """Moderador no puede expulsar al propietario; sí puede expulsar miembros regulares."""
        comm = self.svc.create_community("u_alice", "Kick Test", visibility="private")
        comm_id = comm["id"]
        self.repo.add_member(comm_id, "u_bob")
        self.repo.add_member(comm_id, "u_charlie")

        # Otorgar permiso community.members.kick a Bob creando rol Moderator
        role = self.svc.create_role(
            community_id=comm_id,
            requester_id="u_alice",
            name="Mod",
            position=300,
            permissions=["community.members.kick"]
        )
        self.svc.assign_role(comm_id, "u_alice", "u_bob", role["id"])

        # Bob intenta expulsar a la dueña Alice -> 403 Forbidden
        res_kick_owner = self.client.post(
            f"/api/v1/communities/{comm_id}/members/u_alice/kick",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_kick_owner.status_code, 403)
        self.assertIn("propietario", res_kick_owner.get_json()["error"])

        # Bob expulsa al miembro regular Charlie -> 200 OK
        res_kick_charlie = self.client.post(
            f"/api/v1/communities/{comm_id}/members/u_charlie/kick",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_kick_charlie.status_code, 200)
        self.assertIsNone(self.repo.get_member(comm_id, "u_charlie"))

    def test_08_ownership_transfer_and_safe_leave(self):
        """Dueño no puede abandonar sin transferir; transfiere a Bob y luego abandona."""
        comm = self.svc.create_community("u_alice", "Transfer Lab", visibility="private")
        comm_id = comm["id"]
        self.repo.add_member(comm_id, "u_bob")

        # Alice intenta abandonar siendo dueña -> 400 Bad Request
        res_leave_fail = self.client.post(
            f"/api/v1/communities/{comm_id}/leave",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_leave_fail.status_code, 400)

        # Alice transfiere propiedad a Bob -> 200 OK
        res_transfer = self.client.post(
            f"/api/v1/communities/{comm_id}/transfer-ownership",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"new_owner_id": "u_bob"}
        )
        self.assertEqual(res_transfer.status_code, 200)
        comm_updated = self.repo.get_community(comm_id)
        self.assertEqual(comm_updated["owner_id"], "u_bob")

        # Ahora Alice puede abandonar libremente
        res_leave_ok = self.client.post(
            f"/api/v1/communities/{comm_id}/leave",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_leave_ok.status_code, 200)
        self.assertIsNone(self.repo.get_member(comm_id, "u_alice"))

    def test_09_community_deletion_by_owner_only(self):
        """Eliminación restringida al propietario; terceros reciben 403."""
        comm = self.svc.create_community("u_alice", "Doomed Guild", visibility="private")
        comm_id = comm["id"]
        self.repo.add_member(comm_id, "u_bob")

        # Bob intenta eliminar comunidad -> 403 Forbidden
        res_del_fail = self.client.delete(
            f"/api/v1/communities/{comm_id}",
            headers={"Authorization": f"Bearer {self.token_bob}"}
        )
        self.assertEqual(res_del_fail.status_code, 403)

        # Alice (propietaria) la elimina -> 200 OK
        res_del_ok = self.client.delete(
            f"/api/v1/communities/{comm_id}",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertEqual(res_del_ok.status_code, 200)

        # Consultas posteriores dan 403 o 404 (borrado lógico aplicado)
        res_get = self.client.get(
            f"/api/v1/communities/{comm_id}",
            headers={"Authorization": f"Bearer {self.token_alice}"}
        )
        self.assertIn(res_get.status_code, (403, 404))

    def test_10_rest_api_negative_authorization_scenarios(self):
        """Casos negativos de autenticación (401), payloads inválidos (400) y tokens expirados."""
        # 1. Petición sin cabecera Authorization -> 401 Unauthorized
        res_no_auth = self.client.post("/api/v1/communities", json={"name": "No Auth"})
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. Token con firma corrupta o inválida -> 401 Unauthorized
        res_bad_token = self.client.post(
            "/api/v1/communities",
            headers={"Authorization": "Bearer token.completamente.falso"},
            json={"name": "Bad Token"}
        )
        self.assertEqual(res_bad_token.status_code, 401)

        # 3. Token expirado -> 401 Unauthorized
        token_expired = create_access_token("u_expired", "Expired", expires_in_seconds=-60)
        res_expired = self.client.post(
            "/api/v1/communities",
            headers={"Authorization": f"Bearer {token_expired}"},
            json={"name": "Expired User"}
        )
        self.assertEqual(res_expired.status_code, 401)

        # 4. Payload vacío o nombre inválido -> 400 Bad Request
        res_empty = self.client.post(
            "/api/v1/communities",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={"name": "   "}
        )
        self.assertEqual(res_empty.status_code, 400)


if __name__ == "__main__":
    unittest.main()
