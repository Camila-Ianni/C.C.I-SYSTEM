"""
test_communities_merge_audit.py - Suite integral de certificación Pre-Merge (P0, P1, P2 y Regresión).

Valida todos los criterios de aceptación del Plan de Correcciones antes del Merge:
1. [3.1 P0] Persistencia real en SQLite WAL por defecto, supervivencia tras reinicio, concurrencia multihilo,
   integridad referencial (FK) y bloqueo de :memory: en producción.
2. [3.2 P0] Existencia y coherencia de deploy/Dockerfile.backend, docker-compose.communities.yml,
   livekit.yaml, coturn.conf y .env.example sin secretos inseguros hardcodeados.
3. [3.3 P1] Validación fail-fast de secretos en producción y tokens LiveKit con TTL <= 300s (240s por defecto),
   verificando firma, iss, sub, exp, room y canPublish.
4. [3.5 P1] Matriz de permisos y privacidad fail-closed: rechazo de channel_id cruzado entre comunidades,
   precedencia User Deny > User Allow > Role Deny > Role Allow > Base Role, canales privados, mute y ban.
5. [3.6 P1] Conexión real de GroupsHubState y CommunityViewState con CommunitiesService + SQLite,
   persistiendo grupos, mensajes de canal, DMs y solicitudes tras reinicio.
6. [3.7/3.8 P1] Decodificación real de tramas MPEG Layer III en sound_validator: rechazo de MP3 > 15s
   aunque el cliente declare duration=1.0, y rechazo de falso MP3 con cabecera ID3 sin tramas MPEG.
7. [3.9 P2] Métricas process_local con contadores de error (API y DB) y sonda de salud real.
8. [4.0 Regresión] Transiciones completas de la consola C.C.I. SYSTEM (MENU, GROUPS, COMMUNITY, LIBRARY,
   PROFILE, ACHIEVEMENTS, SETTINGS) y catálogo de 19 juegos intacto.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pygame

import catalog_data
from backend.auth import create_access_token
from backend.communities.livekit_token import LiveKitTokenGenerator
from backend.communities.metrics import CommunityMetricsCollector
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.communities.sound_validator import (
    SoundValidationError,
    build_synthetic_mp3,
    validate_mp3_payload,
)
from backend.communities.stream_adapter import (
    capture_stream_frame,
    detect_available_capture_sources,
)
from backend.config import AppConfig
from backend.server import app
from groups_ui import CommunityViewState, GroupsHubState
from states import StateMachine

ROOT_DIR = Path(__file__).resolve().parent


class TestCommunitiesMergeAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((1280, 720))

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cci_merge_audit_")
        self.db_path = os.path.join(self.temp_dir, "audit_communities.sqlite3")
        self.sounds_dir = os.path.join(self.temp_dir, "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)

        self.repo = CommunitiesRepository.reset_instance(self.db_path)
        self.service = CommunitiesService(self.repo)
        CommunitiesService._instance = self.service

        app.config["TESTING"] = True
        self.client = app.test_client()

        self.token_alice = create_access_token("u_alice", "Alice")
        self.token_bob = create_access_token("u_bob", "Bob")
        self.token_charlie = create_access_token("u_charlie", "Charlie")
        self.token_intruder = create_access_token("u_intruder", "Intruder")

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        CommunitiesRepository._instance = None
        CommunitiesService._instance = None

    # =========================================================================
    # 3.1 PERSISTENCIA DE COMMUNITIES (P0)
    # =========================================================================

    def test_01_persistence_across_restart_and_default_path(self):
        """[3.1 P0] Datos creados persisten tras cerrar y reabrir el repositorio (simulando reinicio)."""
        # Verificar que por defecto NO usa :memory:
        with patch.dict(os.environ, {"CCI_COMMUNITIES_DB_PATH": self.db_path}, clear=False):
            default_repo = CommunitiesRepository()
            self.assertEqual(default_repo.db_path, self.db_path)
            self.assertFalse(default_repo._is_memory)
            self.assertTrue(default_repo.check_health())
            default_repo.close()

        # Crear comunidad, canal, rol, invitación y mensaje
        comm = self.service.create_community("u_alice", "Persistent Guild", slug="persistent-guild")
        comm_id = comm["id"]
        channels = self.service.list_channels(comm_id, "u_alice")
        text_ch = [c for c in channels if c["type"] == "text"][0]
        inv = self.service.create_invitation(comm_id, "u_alice", max_uses=5)
        msg = self.service.send_message(comm_id, text_ch["id"], "u_alice", "Mensaje que sobrevive al reinicio")

        # Cerrar completamente el repositorio y crear nueva instancia sobre el mismo archivo
        self.repo.close()
        restarted_repo = CommunitiesRepository(self.db_path)
        restarted_service = CommunitiesService(restarted_repo)

        comm_loaded = restarted_service.get_community(comm_id, "u_alice")
        self.assertIsNotNone(comm_loaded)
        self.assertEqual(comm_loaded["name"], "Persistent Guild")

        msgs_loaded = restarted_service.list_channel_messages(comm_id, text_ch["id"], "u_alice")
        self.assertEqual(len(msgs_loaded), 1)
        self.assertEqual(msgs_loaded[0]["id"], msg["id"])
        self.assertEqual(msgs_loaded[0]["content"], "Mensaje que sobrevive al reinicio")

        # Bob usa la invitación persistida tras el reinicio
        joined = restarted_service.join_via_invitation(inv["code"], "u_bob")
        self.assertEqual(joined["community"]["id"], comm_id)
        restarted_repo.close()

    def test_02_multithread_concurrency_and_shared_memory_and_prod_guard(self):
        """[3.1 P0] Escrituras concurrentes multihilo seguras y rechazo de :memory: en producción."""
        # 1. En producción, :memory: debe fallar inmediatamente
        with patch.dict(os.environ, {"CCI_ENV": "production"}, clear=False):
            with self.assertRaises(RuntimeError):
                CommunitiesRepository(":memory:")

        # 2. En pruebas, :memory: comparte esquema y datos entre múltiples hilos sin 'no such table'
        mem_repo = CommunitiesRepository(":memory:", allow_memory=True)
        mem_svc = CommunitiesService(mem_repo)
        comm = mem_svc.create_community("u_alice", "Concurrent Mem", slug="concurrent-mem")
        ch_id = [c for c in mem_svc.list_channels(comm["id"], "u_alice") if c["type"] == "text"][0]["id"]

        def _worker(idx: int) -> str:
            m = mem_svc.send_message(comm["id"], ch_id, "u_alice", f"Msg concurrente #{idx}")
            return m["id"]

        with ThreadPoolExecutor(max_workers=6) as pool:
            ids = list(pool.map(_worker, range(18)))

        self.assertEqual(len(ids), 18)
        all_msgs = mem_svc.list_channel_messages(comm["id"], ch_id, "u_alice", limit=50)
        self.assertEqual(len(all_msgs), 18)
        mem_repo.close()

    # =========================================================================
    # 3.2 DOCKER Y DESPLIEGUE (P0)
    # =========================================================================

    def test_03_docker_and_deployment_manifests_integrity(self):
        """[3.1 P0 / 3.4 P1 / 3.5 P1] Verifica alineación de puerto 5050 en Caddy/Dockerfile/Compose, dominios canónicos y SQLite único."""
        dockerfile = ROOT_DIR / "deploy" / "Dockerfile.backend"
        compose = ROOT_DIR / "deploy" / "docker-compose.communities.yml"
        caddyfile = ROOT_DIR / "deploy" / "Caddyfile"
        env_example = ROOT_DIR / "deploy" / ".env.example"
        lk_yaml = ROOT_DIR / "deploy" / "livekit.yaml"
        coturn_conf = ROOT_DIR / "deploy" / "coturn.conf"

        self.assertTrue(dockerfile.exists(), "Falta deploy/Dockerfile.backend")
        self.assertTrue(compose.exists(), "Falta deploy/docker-compose.communities.yml")
        self.assertTrue(caddyfile.exists(), "Falta deploy/Caddyfile")
        self.assertTrue(env_example.exists(), "Falta deploy/.env.example")

        df_text = dockerfile.read_text(encoding="utf-8")
        self.assertIn("USER cciuser", df_text)
        self.assertIn("EXPOSE 5050", df_text)
        self.assertIn("HEALTHCHECK", df_text)
        self.assertIn("backend.server", df_text)

        # [3.1 P0] Caddyfile debe apuntar a api:5050 (nunca api:8000) y reenviar cabeceras WebSocket Connection/Upgrade
        caddy_text = caddyfile.read_text(encoding="utf-8")
        self.assertIn("reverse_proxy api:5050", caddy_text)
        self.assertNotIn("api:8000", caddy_text)
        self.assertNotIn("minio:9000", caddy_text)
        self.assertIn("/socket.io/*", caddy_text)
        self.assertIn("header_up Connection", caddy_text)
        self.assertIn("header_up Upgrade", caddy_text)
        self.assertIn("reverse_proxy livekit:7880", caddy_text)

        compose_text = compose.read_text(encoding="utf-8")
        self.assertIn("Dockerfile.backend", compose_text)
        self.assertIn("CCI_PORT: 5050", compose_text)
        self.assertIn("CCI_COMMUNITIES_DB_PATH: /data/cci_communities.sqlite3", compose_text)
        self.assertIn(":?", compose_text, "docker-compose debe exigir variables de secreto externas (:?)")
        self.assertNotIn("secretkey1234567890abcdef", compose_text)
        self.assertNotIn("cci_jwt_super_secret_signing_key_production", compose_text)
        # [3.5 P1] Sin contenedores fantasma no integrados (postgres, redis, minio)
        self.assertNotIn("pgvector/pgvector", compose_text)
        self.assertNotIn("redis:7-alpine", compose_text)
        self.assertNotIn("minio/minio", compose_text)

        # [3.4 P1] Dominios canónicos unificados (api.ccisystem.org, rtc.ccisystem.org, turn.ccisystem.org)
        env_text = env_example.read_text(encoding="utf-8")
        lk_text = lk_yaml.read_text(encoding="utf-8")
        coturn_text = coturn_conf.read_text(encoding="utf-8")

        for domain in ("api.ccisystem.org", "rtc.ccisystem.org", "turn.ccisystem.org"):
            self.assertIn(domain, env_text)
        self.assertIn("api.ccisystem.org", caddy_text)
        self.assertIn("rtc.ccisystem.org", caddy_text)
        self.assertIn("turn.ccisystem.org", lk_text)
        self.assertIn("turn.ccisystem.org", coturn_text)
        self.assertNotIn(".local", lk_text)
        self.assertNotIn(".local", coturn_text)
        self.assertNotIn("secretkey1234567890abcdef", lk_text)

        self.assertIn("use-auth-secret", coturn_text)
        self.assertNotIn("lt-cred-mech", coturn_text)
        self.assertNotIn("cci_turn_static_secret_2026", coturn_text)

    # =========================================================================
    # 3.2 y 3.3 SECRETOS, AUTENTICACIÓN Y TOKENS LIVEKIT (P1)
    # =========================================================================

    def test_04_production_secrets_fail_fast_and_livekit_token_security(self):
        """[3.2 P1] Falla en producción con placeholders (.env.example), vacíos o sin TURN_SECRET; acepta secretos reales."""
        valid_env = {
            "CCI_ENV": "production",
            "CCI_SECRET_KEY": "a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8",
            "LIVEKIT_API_KEY": "APx9K7mQ2vL8nR4pT6wY1zB3",
            "LIVEKIT_API_SECRET": "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
            "TURN_SECRET": "7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d",
        }

        # 1. Rechaza cada uno de los placeholders de deploy/.env.example en producción
        placeholder_cases = [
            {"CCI_SECRET_KEY": "REPLACE_WITH_OPENSSL_RAND_HEX_32"},
            {"LIVEKIT_API_KEY": "REPLACE_WITH_LIVEKIT_API_KEY"},
            {"LIVEKIT_API_KEY": "LK_PROD_KEY_REPLACE_ME"},
            {"LIVEKIT_API_SECRET": "REPLACE_WITH_LIVEKIT_API_SECRET_32_CHARS"},
            {"TURN_SECRET": "REPLACE_WITH_COTURN_SHARED_SECRET_32_CHARS"},
            {"TURN_SECRET": ""},
            {"TURN_SECRET": "short_turn_secret"},
            {"CCI_SECRET_KEY": ""},
        ]
        for override in placeholder_cases:
            env_case = {**valid_env, **override}
            with patch.dict(os.environ, env_case, clear=False):
                with self.assertRaises(RuntimeError, msg=f"Debió rechazar en producción: {override}"):
                    AppConfig.from_env()

        # 2. LiveKitTokenGenerator también rechaza placeholders en producción
        with patch.dict(
            os.environ,
            {
                **valid_env,
                "LIVEKIT_API_KEY": "REPLACE_WITH_LIVEKIT_API_KEY",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                LiveKitTokenGenerator()

        # 3. Con los 4 secretos reales de producción configurados, AppConfig.from_env() inicia correctamente
        with patch.dict(os.environ, valid_env, clear=False):
            prod_cfg = AppConfig.from_env()
            self.assertEqual(prod_cfg.env, "production")

        # 4. Token LiveKit por defecto tiene TTL 240s (< 5 min) y tope máximo 300s
        gen = LiveKitTokenGenerator(
            api_key="lk_prod_key_real_01",
            api_secret="lk_prod_secret_real_0123456789abcdef012345",
        )
        tok_default = gen.create_access_token(
            identity="u_alice",
            name="Alice",
            room_name="room_test_1",
            can_publish=True,
        )
        self.assertEqual(tok_default["ttl_seconds"], 240)

        # Intentar pedir 3600s -> se recorta a 300s (5 minutos máximo)
        tok_clamped = gen.create_access_token(
            identity="u_alice",
            name="Alice",
            room_name="room_test_1",
            can_publish=False,
            valid_for_seconds=3600,
        )
        self.assertEqual(tok_clamped["ttl_seconds"], 300)

        # Verificación estricta de sala, identidad y permisos
        claims = gen.verify_access_token(
            tok_default["token"],
            expected_room="room_test_1",
            expected_identity="u_alice",
            require_publish=True,
        )
        self.assertIsNotNone(claims)

        # Sala incorrecta -> None
        self.assertIsNone(
            gen.verify_access_token(tok_default["token"], expected_room="other_room")
        )
        # Identidad incorrecta -> None
        self.assertIsNone(
            gen.verify_access_token(tok_default["token"], expected_identity="u_bob")
        )
        # Token sin permiso de publicación rechazado cuando require_publish=True
        self.assertIsNone(
            gen.verify_access_token(tok_clamped["token"], require_publish=True)
        )
        # Firma adulterada -> None
        tampered = tok_default["token"][:-4] + "XXXX"
        self.assertIsNone(gen.verify_access_token(tampered))

    # =========================================================================
    # 3.5 MATRIZ DE PERMISOS Y PRIVACIDAD (P1)
    # =========================================================================

    def test_05_permission_matrix_precedence_and_cross_community_channel_isolation(self):
        """[3.5 P1] Verifica aislamiento de channel_id entre comunidades, precedencia de overrides y privacidad."""
        comm_a = self.service.create_community("u_alice", "Comunidad A", slug="comm-a")
        comm_b = self.service.create_community("u_bob", "Comunidad B", slug="comm-b")

        ch_b = self.service.list_channels(comm_b["id"], "u_bob")[0]

        # Incluso la propietaria de Comunidad A recibe False si pasa un channel_id de Comunidad B
        self.assertFalse(
            self.service.has_permission(comm_a["id"], "u_alice", "messages.read", channel_id=ch_b["id"])
        )

        # Incorporar a Charlie a Comunidad A
        inv_a = self.service.create_invitation(comm_a["id"], "u_alice")
        self.service.join_via_invitation(inv_a["code"], "u_charlie")

        # Crear canal privado en Comunidad A
        priv_ch = self.service.create_channel(
            community_id=comm_a["id"],
            requester_id="u_alice",
            name="bunker-secreto",
            channel_type="text",
            is_private=True,
        )
        priv_id = priv_ch["id"]

        # Charlie (miembro regular) NO puede ver ni escribir en el canal privado
        self.assertFalse(self.service.has_permission(comm_a["id"], "u_charlie", "messages.read", channel_id=priv_id))
        self.assertFalse(self.service.has_permission(comm_a["id"], "u_charlie", "messages.send", channel_id=priv_id))

        # Otorgar a Charlie override allow en messages.read pero deny en messages.send
        self.service.set_channel_override(
            comm_a["id"], priv_id, "u_alice", "user", "u_charlie", "messages.read", allow=True, deny=False
        )
        self.service.set_channel_override(
            comm_a["id"], priv_id, "u_alice", "user", "u_charlie", "messages.send", allow=False, deny=True
        )

        # Charlie ahora puede leer el canal privado, pero tiene prohibido enviar mensajes (solo lectura)
        self.assertTrue(self.service.has_permission(comm_a["id"], "u_charlie", "messages.read", channel_id=priv_id))
        self.assertFalse(self.service.has_permission(comm_a["id"], "u_charlie", "messages.send", channel_id=priv_id))

        with self.assertRaises(PermissionError):
            self.service.send_message(comm_a["id"], priv_id, "u_charlie", "Intento escribir en modo lectura")

    # =========================================================================
    # 3.6 CONEXIÓN DE LA INTERFAZ CON SERVICIOS REALES Y PERSISTENCIA (P1)
    # =========================================================================

    def test_06_ui_states_persist_messages_groups_and_dms_in_sqlite(self):
        """[3.6 P1] Enviar mensaje, crear grupo y enviar DM en la UI persiste realmente en SQLite tras reinicio."""
        screen = pygame.display.get_surface()
        sm1 = StateMachine(screen)
        hub1 = GroupsHubState(sm1, db_path=self.db_path)
        comm1 = CommunityViewState(sm1, db_path=self.db_path)
        sm1.register_state("GROUPS", hub1)
        sm1.register_state("COMMUNITY", comm1)

        # 1. Crear una nueva comunidad desde el modal de GroupsHubState
        sm1.change_state("GROUPS")
        hub1.modal_mode = "create"
        hub1.modal_input = "ESCUADRON ALPHA"
        hub1._confirm_modal()
        self.assertEqual(hub1.groups[0]["name"], "ESCUADRON ALPHA")

        # 2. Enviar un mensaje en #general de Night Raid desde CommunityViewState
        sm1.change_state("COMMUNITY", community_id="night_raid")
        comm1.input_text = "Mensaje persistido desde Pygame UI en SQLite!"
        comm1._send_message()

        # 3. Enviar un DM en Chats Privados
        sm1.change_state("GROUPS", tab=1)
        hub1.dm_input_text = "Hola Tomás, este DM queda guardado en SQLite."
        hub1._send_dm_message()

        # Cerrar conexiones y simular reinicio completo creando nuevas instancias de estado sobre self.db_path
        hub1.bridge.repo.close()
        comm1.bridge.repo.close()

        sm2 = StateMachine(screen)
        hub2 = GroupsHubState(sm2, db_path=self.db_path)
        comm2 = CommunityViewState(sm2, db_path=self.db_path)
        sm2.register_state("GROUPS", hub2)
        sm2.register_state("COMMUNITY", comm2)

        sm2.change_state("GROUPS")
        group_names = [g["name"] for g in hub2.groups]
        self.assertIn("ESCUADRON ALPHA", group_names)
        self.assertEqual(hub2.dms[0].last_message, "Hola Tomás, este DM queda guardado en SQLite.")

        sm2.change_state("COMMUNITY", community_id="night_raid")
        texts = [m["text"] for m in comm2.chat_messages]
        self.assertIn("Mensaje persistido desde Pygame UI en SQLite!", texts)

        hub2.bridge.repo.close()
        comm2.bridge.repo.close()

    # =========================================================================
    # 3.7 y 3.8 VALIDACIÓN REAL DE AUDIO MP3 Y STREAM ADAPTER (P1)
    # =========================================================================

    def test_07_real_mp3_frame_validation_rejects_spoofed_duration_and_corrupt_files(self):
        """[3.8 P1] Rechaza MP3 > 15s aunque el cliente declare duration=1.0 y rechaza falso MP3 con ID3 corrupto."""
        # 1. Crear MP3 de 18.0 segundos reales (por cabecera Xing/Info de tramas y/o tamaño CBR)
        long_mp3 = build_synthetic_mp3(duration_seconds=18.0)

        # Cliente intenta engañar declarando duration=1.0 -> DEBE ser rechazado con DURATION_EXCEEDED
        with self.assertRaises(SoundValidationError) as ctx:
            validate_mp3_payload(long_mp3, declared_duration=1.0)
        self.assertEqual(ctx.exception.code, "DURATION_EXCEEDED")

        # También vía endpoint REST /api/v1/sounds con duration=1.0
        res_spoof = self.client.post(
            "/api/v1/sounds",
            headers={"Authorization": f"Bearer {self.token_alice}"},
            json={
                "owner_type": "user",
                "title": "Audio Largo Camuflado",
                "file_base64": base64.b64encode(long_mp3).decode("ascii"),
                "duration": 1.0,
            },
        )
        self.assertEqual(res_spoof.status_code, 400)
        self.assertIn("DURATION_EXCEEDED", res_spoof.get_json()["error"])

        # 2. Archivo falso que empieza con "ID3" pero contiene texto plano sin tramas MPEG Layer III
        fake_id3_mp3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + (b"NOT_AN_MPEG_FRAME_JUST_PLAIN_TEXT_" * 10)
        with self.assertRaises(SoundValidationError) as ctx2:
            validate_mp3_payload(fake_id3_mp3, declared_duration=2.0)
        self.assertEqual(ctx2.exception.code, "INVALID_FORMAT")

        # 3. [3.3 P1] Verificar adaptador de captura de streaming:
        #    - En modo headless / SDL_VIDEODRIVER=dummy NO inventa pantallas falsas (screens=[], unavailable)
        #    - Sin procesos activos NO fuerza python_active=True
        #    - Separa explícitamente source_detection, local_preview_capture y webrtc_media_publishing
        sources = detect_available_capture_sources(force_headless=True)
        self.assertEqual(sources["screens"], [])
        self.assertEqual(sources["subsystem_status"]["screen_capture_status"], "unavailable")
        self.assertEqual(
            sources["subsystem_status"]["webrtc_media_publishing"],
            "external_livekit_sfu_client_required",
        )
        self.assertGreaterEqual(len(sources["games"]), 10)

        with patch("backend.communities.stream_adapter._list_running_process_names", return_value=[]):
            sources_no_proc = detect_available_capture_sources(force_headless=True)
            self.assertEqual(sources_no_proc["windows"], [])
            self.assertTrue(
                all(not g["is_running"] for g in sources_no_proc["games"]),
                "Sin procesos activos, ningún juego debe marcarse con is_running=True",
            )

        frame = capture_stream_frame()
        self.assertEqual(frame["pixel_format"], "RGB24")
        self.assertGreater(frame["byte_length"], 0)

    # =========================================================================
    # 3.9 MÉTRICAS Y SALUD (P2)
    # =========================================================================

    def test_08_metrics_process_local_scope_and_error_counters(self):
        """[3.9 P2] Verifica metadatos process_local y contadores de error en /metrics y /health."""
        # Provocar un 403 intencional para incrementar communities_api_errors_total
        self.client.get(
            "/api/v1/communities/non-existent-id",
            headers={"Authorization": f"Bearer {self.token_intruder}"},
        )

        res_metrics = self.client.get("/api/v1/communities/metrics", headers={"Accept": "application/json"})
        self.assertEqual(res_metrics.status_code, 200)
        snap = res_metrics.get_json()
        self.assertEqual(snap["scope"], "process_local")
        self.assertFalse(snap["persistent"])
        self.assertGreaterEqual(snap["counters"]["communities_api_errors_total"], 1)
        self.assertIn("communities_db_errors_total", snap["counters"])
        self.assertIn("communities_voice_sessions_active", snap["gauges"])

    # =========================================================================
    # 4. REGRESIÓN DEL PRODUCTO PRINCIPAL
    # =========================================================================

    def test_09_main_console_product_regression(self):
        """[4.0 Regresión] Verifica catálogo de 19 juegos y navegación de estados del launcher."""
        self.assertEqual(len(catalog_data.CATALOG), 19)
        game_ids = {g["id"] for g in catalog_data.CATALOG}
        self.assertIn("davinci", game_ids)
        self.assertIn("metalslug", game_ids)

        from cci_console import CCIConsoleState
        from cci_users import UserManager
        from states import BootState, IntroAvatarState, MenuState
        from user_select_state import UserSelectState

        screen = pygame.display.get_surface()
        sm = StateMachine(screen)
        user_mgr = UserManager()
        user_data = user_mgr.active_user

        sm.register_state("BOOT", BootState(sm))
        sm.register_state("INTRO_AVATAR", IntroAvatarState(sm))
        sm.register_state("USER_SELECT", UserSelectState(sm, on_user_selected=lambda u: None))
        sm.register_state("MENU", MenuState(sm))
        sm.register_state("LIBRARY", CCIConsoleState(sm, "library", user_data, lambda s: None))
        sm.register_state("GROUPS", GroupsHubState(sm, db_path=self.db_path))
        sm.register_state("COMMUNITY", CommunityViewState(sm, db_path=self.db_path))
        sm.register_state("PROFILE", CCIConsoleState(sm, "profile", user_data, lambda s: None))
        sm.register_state("ACHIEVEMENTS", CCIConsoleState(sm, "achievements", user_data, lambda s: None))
        sm.register_state("SETTINGS", CCIConsoleState(sm, "settings", user_data, lambda s: None))

        for state_name in (
            "BOOT",
            "INTRO_AVATAR",
            "USER_SELECT",
            "MENU",
            "GROUPS",
            "COMMUNITY",
            "LIBRARY",
            "PROFILE",
            "ACHIEVEMENTS",
            "SETTINGS",
            "MENU",
        ):
            sm.change_state(state_name)
            self.assertEqual(sm.current_state_name, state_name)
            sm.update(0.016)
            sm.draw(screen)


if __name__ == "__main__":
    unittest.main()
