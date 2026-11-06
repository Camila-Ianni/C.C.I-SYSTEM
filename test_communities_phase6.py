"""
test_communities_phase6.py - Suite de pruebas unitarias herméticas para Moderación y Auditoría.

Cubre:
1. Emisión de advertencias formales (warn) con motivo y registro en audit log.
2. Silenciamiento (mute) temporal/permanente: rechazo de envío de mensajes (403) y recuperación con unmute.
3. Expulsión (kick) respetando jerarquías y remoción de membresía.
4. Prohibición de acceso (ban) y bloqueo fail-closed de reingreso por código de invitación (403).
5. Desbaneo (unban) y autorización posterior de ingreso.
6. Protección de jerarquía: imposibilidad de moderar roles superiores o al propietario (403).
7. Rechazo estricto de acciones administrativas a usuarios no autorizados (403).
8. Flujo completo de reportes: creación por usuario, consulta y resolución por moderador.
9. Trazabilidad e inmutabilidad del log de auditoría (audit_log).
10. Expiración automática de sanciones temporales de ban sin intervención manual.
"""

import os
import shutil
import tempfile
import time
import unittest
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.server import app
from backend.auth import create_access_token


class TestCommunitiesPhase6Moderation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cci_test_mod_")
        self.db_path = os.path.join(self.temp_dir, "test_communities_phase6.db")

        self.repo = CommunitiesRepository(db_path=self.db_path)
        self.service = CommunitiesService(repo=self.repo)

        CommunitiesRepository._instance = self.repo
        CommunitiesService._instance = self.service

        app.config["TESTING"] = True
        self.client = app.test_client()

        # Sembrar usuarios
        self.owner_id = "user_owner_601"
        self.admin_mod_id = "user_mod_admin_602"
        self.jr_mod_id = "user_mod_jr_603"
        self.bad_user_id = "user_troll_604"
        self.regular_id = "user_reg_605"

        self.token_owner = create_access_token(self.owner_id, "owner6")
        self.token_admin_mod = create_access_token(self.admin_mod_id, "modadmin6")
        self.token_jr_mod = create_access_token(self.jr_mod_id, "modjr6")
        self.token_bad_user = create_access_token(self.bad_user_id, "troll6")
        self.token_regular = create_access_token(self.regular_id, "reg6")

        # Crear comunidad principal
        self.comm = self.service.create_community(
            owner_id=self.owner_id,
            name="Comunidad de Moderacion Test",
            slug="mod-test-comm-6"
        )
        self.comm_id = self.comm["id"]

        # Crear canal de texto
        self.chat_chan = self.service.create_channel(
            community_id=self.comm_id,
            requester_id=self.owner_id,
            name="chat-general",
            channel_type="text"
        )
        self.channel_id = self.chat_chan["id"]

        # Incorporar usuarios
        invite_code = self.service.create_invitation(self.comm_id, self.owner_id, max_uses=0)["code"]
        self.invite_code = invite_code
        self.service.join_via_invitation(invite_code, self.admin_mod_id)
        self.service.join_via_invitation(invite_code, self.jr_mod_id)
        self.service.join_via_invitation(invite_code, self.bad_user_id)
        self.service.join_via_invitation(invite_code, self.regular_id)

        # Crear roles jerárquicos: Admin Mod (pos=10) y Jr Mod (pos=20)
        self.role_admin_mod = self.service.create_role(
            community_id=self.comm_id,
            requester_id=self.owner_id,
            name="Admin Mod",
            permissions=[
                "community.manage",
                "community.members.kick",
                "community.members.ban",
                "voice.mute_members",
                "messages.manage"
            ]
        )
        self.repo.update_role(self.role_admin_mod["id"], {"position": 10})

        self.role_jr_mod = self.service.create_role(
            community_id=self.comm_id,
            requester_id=self.owner_id,
            name="Junior Mod",
            permissions=[
                "community.members.kick",
                "voice.mute_members"
            ]
        )
        self.repo.update_role(self.role_jr_mod["id"], {"position": 20})

        self.service.assign_role(self.comm_id, self.owner_id, self.admin_mod_id, self.role_admin_mod["id"])
        self.service.assign_role(self.comm_id, self.owner_id, self.jr_mod_id, self.role_jr_mod["id"])

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        CommunitiesRepository._instance = None
        CommunitiesService._instance = None

    def test_01_warn_member_success_and_audit(self):
        """Moderador emite advertencia con motivo; se registra en moderation_actions y audit_log."""
        res = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/warn",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={
                "target_user_id": self.bad_user_id,
                "reason": "Lenguaje inapropiado en chat general"
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["action"], "warn")
        self.assertEqual(data["target_id"], self.bad_user_id)
        self.assertEqual(data["actor_id"], self.admin_mod_id)

        # Comprobar historial de acciones
        res_actions = self.client.get(
            f"/api/v1/communities/{self.comm_id}/moderation/actions?target_id={self.bad_user_id}",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"}
        )
        self.assertEqual(res_actions.status_code, 200)
        actions = res_actions.get_json()["actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "warn")

        # Comprobar audit log
        res_audit = self.client.get(
            f"/api/v1/communities/{self.comm_id}/audit-log?action_type=member.warn",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"}
        )
        self.assertEqual(res_audit.status_code, 200)
        entries = res_audit.get_json()["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["target_id"], self.bad_user_id)

    def test_02_mute_and_unmute_member(self):
        """Usuario silenciado no puede enviar mensajes (403); al levantar mute vuelve a escribir."""
        # 1. Silenciar a bad_user_id por 30 minutos
        res_mute = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/mute",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={
                "target_user_id": self.bad_user_id,
                "duration_minutes": 30,
                "reason": "Spam reiterado"
            }
        )
        self.assertEqual(res_mute.status_code, 201)

        # 2. bad_user_id intenta enviar mensaje -> 403 Forbidden
        res_msg_fail = self.client.post(
            f"/api/v1/channels/{self.channel_id}/messages",
            headers={"Authorization": f"Bearer {self.token_bad_user}"},
            json={"content": "Intentando hablar mientras estoy muteado"}
        )
        self.assertEqual(res_msg_fail.status_code, 403)
        self.assertIn("silenciado", res_msg_fail.get_json()["error"])

        # 3. Moderador levanta el silenciamiento (unmute)
        res_unmute = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/unmute",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={"target_user_id": self.bad_user_id, "reason": "Disculpas aceptadas"}
        )
        self.assertEqual(res_unmute.status_code, 200)

        # 4. bad_user_id vuelve a enviar mensaje -> 201 Created
        res_msg_ok = self.client.post(
            f"/api/v1/channels/{self.channel_id}/messages",
            headers={"Authorization": f"Bearer {self.token_bad_user}"},
            json={"content": "Hola de nuevo, ya no estoy silenciado"}
        )
        self.assertEqual(res_msg_ok.status_code, 201)

    def test_03_kick_member_removes_from_community(self):
        """Expulsión remueve al miembro de la comunidad registrando auditoría."""
        res_kick = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/kick",
            headers={"Authorization": f"Bearer {self.token_jr_mod}"},
            json={"target_user_id": self.bad_user_id, "reason": "Infracción leve reiterada"}
        )
        self.assertEqual(res_kick.status_code, 200)
        self.assertTrue(res_kick.get_json()["kicked"])

        # Verificar que bad_user_id ya no es miembro
        member = self.repo.get_member(self.comm_id, self.bad_user_id)
        self.assertIsNone(member)

    def test_04_ban_member_and_block_rejoin(self):
        """Usuario baneado no puede reingresar mediante enlace de invitación (403 Forbidden)."""
        res_ban = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/ban",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={
                "target_user_id": self.bad_user_id,
                "reason": "Comportamiento tóxico grave",
                "duration_hours": 24
            }
        )
        self.assertEqual(res_ban.status_code, 201)

        # Intento de reingreso por código de invitación
        res_join = self.client.post(
            "/api/v1/invitations/join",
            headers={"Authorization": f"Bearer {self.token_bad_user}"},
            json={"code": self.invite_code}
        )
        self.assertEqual(res_join.status_code, 403)
        self.assertIn("ban", res_join.get_json()["error"].lower())

    def test_05_unban_member_allows_rejoin(self):
        """Levantar la sanción de ban permite al usuario volver a incorporarse con invitación."""
        # 1. Banear
        self.service.ban_member(self.comm_id, self.admin_mod_id, self.bad_user_id, reason="Ban inicial")
        self.assertTrue(self.repo.is_user_banned(self.comm_id, self.bad_user_id))

        # 2. Desbanear
        res_unban = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/unban",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={"target_user_id": self.bad_user_id, "reason": "Apelación aprobada"}
        )
        self.assertEqual(res_unban.status_code, 200)
        self.assertFalse(self.repo.is_user_banned(self.comm_id, self.bad_user_id))

        # 3. Reingresar exitosamente
        res_rejoin = self.client.post(
            "/api/v1/invitations/join",
            headers={"Authorization": f"Bearer {self.token_bad_user}"},
            json={"code": self.invite_code}
        )
        self.assertEqual(res_rejoin.status_code, 200)

    def test_06_hierarchy_protection(self):
        """Protección estricta: un moderador no puede sancionar a moderadores superiores ni al dueño."""
        # 1. Jr Mod (pos=20) intenta banear a Admin Mod (pos=10) -> 403 Forbidden
        res_fail1 = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/ban",
            headers={"Authorization": f"Bearer {self.token_jr_mod}"},
            json={"target_user_id": self.admin_mod_id}
        )
        self.assertEqual(res_fail1.status_code, 403)

        # 2. Admin Mod (pos=10) intenta banear al Owner -> 403 Forbidden
        res_fail2 = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/ban",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={"target_user_id": self.owner_id}
        )
        self.assertEqual(res_fail2.status_code, 403)
        self.assertIn("propietario", res_fail2.get_json()["error"].lower())

    def test_07_unauthorized_moderation_rejected(self):
        """Usuarios regulares sin permisos no pueden ejecutar acciones de moderación ni ver auditoría."""
        # 1. Usuario regular intenta mutear -> 403 Forbidden
        res_mute = self.client.post(
            f"/api/v1/communities/{self.comm_id}/moderation/mute",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={"target_user_id": self.bad_user_id}
        )
        self.assertEqual(res_mute.status_code, 403)

        # 2. Usuario regular intenta consultar log de auditoría -> 403 Forbidden
        res_audit = self.client.get(
            f"/api/v1/communities/{self.comm_id}/audit-log",
            headers={"Authorization": f"Bearer {self.token_regular}"}
        )
        self.assertEqual(res_audit.status_code, 403)

    def test_08_create_and_resolve_report(self):
        """Flujo de reportes: usuario reporta mensaje abusivo y moderador lo resuelve con notas."""
        # 1. bad_user publica mensaje tóxico
        msg = self.service.send_message(self.comm_id, self.channel_id, self.bad_user_id, "Contenido ofensivo")
        msg_id = msg["id"]

        # 2. regular_id reporta el mensaje
        res_report = self.client.post(
            f"/api/v1/communities/{self.comm_id}/reports",
            headers={"Authorization": f"Bearer {self.token_regular}"},
            json={
                "target_type": "message",
                "target_id": msg_id,
                "reason": "Acoso y lenguaje de odio"
            }
        )
        self.assertEqual(res_report.status_code, 201)
        report_id = res_report.get_json()["id"]

        # 3. Moderador lista reportes abiertos
        res_list = self.client.get(
            f"/api/v1/communities/{self.comm_id}/reports?status=open",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"}
        )
        self.assertEqual(res_list.status_code, 200)
        reports = res_list.get_json()["reports"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["id"], report_id)

        # 4. Moderador resuelve el reporte
        res_resolve = self.client.patch(
            f"/api/v1/communities/{self.comm_id}/reports/{report_id}",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"},
            json={
                "status": "resolved",
                "resolution_notes": "Mensaje eliminado y usuario advertido"
            }
        )
        self.assertEqual(res_resolve.status_code, 200)
        self.assertEqual(res_resolve.get_json()["status"], "resolved")
        self.assertEqual(res_resolve.get_json()["resolved_by"], self.admin_mod_id)

    def test_09_audit_log_traceability(self):
        """Verifica trazabilidad del audit_log tras múltiples operaciones de moderación."""
        self.service.warn_member(self.comm_id, self.admin_mod_id, self.bad_user_id, "Warn 1")
        self.service.mute_member(self.comm_id, self.admin_mod_id, self.bad_user_id, duration_minutes=10)

        res = self.client.get(
            f"/api/v1/communities/{self.comm_id}/audit-log",
            headers={"Authorization": f"Bearer {self.token_admin_mod}"}
        )
        self.assertEqual(res.status_code, 200)
        entries = res.get_json()["entries"]
        action_types = [e["action_type"] for e in entries]
        self.assertIn("member.warn", action_types)
        self.assertIn("member.mute", action_types)

    def test_10_ban_expiration(self):
        """Ban temporal cuya fecha de expiración ha pasado se considera inactivo y permite reingreso."""
        past_timestamp = time.time() - 3600  # Expiró hace 1 hora
        self.repo.create_moderation_action(
            action_id="action_expired_ban_1",
            community_id=self.comm_id,
            actor_id=self.admin_mod_id,
            target_id=self.bad_user_id,
            action="ban",
            reason="Ban expirado de prueba",
            expires_at=past_timestamp
        )
        # Remover membresía como ocurre al banear
        self.repo.remove_member(self.comm_id, self.bad_user_id)

        # Comprobar que is_user_banned retorna False
        self.assertFalse(self.repo.is_user_banned(self.comm_id, self.bad_user_id))

        # Reingreso permitido porque el ban expiró
        res_rejoin = self.client.post(
            "/api/v1/invitations/join",
            headers={"Authorization": f"Bearer {self.token_bad_user}"},
            json={"code": self.invite_code}
        )
        self.assertEqual(res_rejoin.status_code, 200)


if __name__ == "__main__":
    unittest.main()
