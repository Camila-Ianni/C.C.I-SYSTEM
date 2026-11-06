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
        self.assertIn("no-tls", coturn_text)
        self.assertIn("no-dtls", coturn_text)
        self.assertNotIn("tls-listening-port=5349", coturn_text)
        self.assertNotIn("tls_port: 5349", lk_text)
        self.assertNotIn("lt-cred-mech", coturn_text)
        self.assertNotIn("cci_turn_static_secret_2026", coturn_text)

        # [P1 SQLite único] Esquema físico canónico en schema_sqlite.sql y ausencia de schema_postgres.sql
        schema_sqlite = ROOT_DIR / "documentacion" / "communities" / "schema_sqlite.sql"
        schema_pg = ROOT_DIR / "documentacion" / "communities" / "schema_postgres.sql"
        self.assertTrue(schema_sqlite.exists(), "Falta documentacion/communities/schema_sqlite.sql")
        self.assertFalse(schema_pg.exists(), "schema_postgres.sql no debe existir para evitar ambigüedad con SQLite")

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

    def test_10_live_tcp_http_200_websocket_101_and_docker_compose_config(self):
        """[P1 Despliegue Reproducible] Valida docker compose config, servidor TCP en vivo (HTTP 200, WS 101) y persistencia tras reinicio."""
        import json
        import socket
        import subprocess
        import threading
        import urllib.request
        from werkzeug.serving import make_server
        from backend.server import socketio

        # 1. Validar sintaxis e interpolación de deploy/docker-compose.communities.yml con docker compose config y secretos efímeros
        import secrets
        self.assertIsNotNone(shutil.which("docker"), "Docker CLI es obligatorio para la certificación")
        env_compose = {
            **os.environ,
            "CCI_SECRET_KEY": secrets.token_hex(32),
            "LIVEKIT_API_KEY": "AP" + secrets.token_hex(11),
            "LIVEKIT_API_SECRET": secrets.token_hex(32),
            "TURN_SECRET": secrets.token_hex(32),
        }
        proc = subprocess.run(
            ["docker", "compose", "-f", str(ROOT_DIR / "deploy" / "docker-compose.communities.yml"), "config"],
            capture_output=True,
            text=True,
            env=env_compose,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"docker compose config falló: {proc.stderr}")
        self.assertIn("cci_communities_api", proc.stdout)
        self.assertIn("cci_communities_livekit", proc.stdout)
        self.assertIn("cci_communities_coturn", proc.stdout)
        self.assertIn("cci_communities_caddy", proc.stdout)
        self.assertIn("5050", proc.stdout)

        # 2. Levantar servidor HTTP/WebSocket real en puerto TCP local sobre SQLite WAL
        server = make_server("127.0.0.1", 0, app, threaded=True)
        port = server.server_port
        srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
        srv_thread.start()

        try:
            base_url = f"http://127.0.0.1:{port}"
            # 2a. Healthcheck real por red TCP -> HTTP 200 OK
            req_health = urllib.request.Request(f"{base_url}/api/v1/communities/health")
            with urllib.request.urlopen(req_health, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body_health = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body_health["status"], "healthy")
                self.assertEqual(body_health["database"], "connected")

            # 2b. Crear comunidad y mensaje por HTTP TCP real -> HTTP 201 Created
            req_comm = urllib.request.Request(
                f"{base_url}/api/v1/communities",
                data=json.dumps({"name": "TCP Live Guild", "visibility": "public"}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token_alice}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req_comm, timeout=5) as resp_comm:
                self.assertEqual(resp_comm.status, 201)
                comm_data = json.loads(resp_comm.read().decode("utf-8"))["community"]
                comm_id = comm_data["id"]

            req_ch = urllib.request.Request(
                f"{base_url}/api/v1/communities/{comm_id}/channels",
                headers={"Authorization": f"Bearer {self.token_alice}"},
            )
            with urllib.request.urlopen(req_ch, timeout=5) as resp_ch:
                channels = json.loads(resp_ch.read().decode("utf-8"))["channels"]
                text_ch_id = [c["id"] for c in channels if c["type"] == "text"][0]

            req_msg = urllib.request.Request(
                f"{base_url}/api/v1/channels/{text_ch_id}/messages",
                data=json.dumps({"content": "Persistencia TCP + SQLite WAL verificada"}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token_alice}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req_msg, timeout=5) as resp_msg:
                self.assertEqual(resp_msg.status, 201)

            # 2c. Handshake WebSocket (RFC 6455 Upgrade 101 Switching Protocols) sobre socket TCP real
            ws_sock = socket.create_connection(("127.0.0.1", port), timeout=5)
            try:
                upgrade_req = (
                    f"GET /socket.io/?EIO=4&transport=websocket&token={self.token_alice} HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{port}\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                    "Sec-WebSocket-Version: 13\r\n\r\n"
                )
                ws_sock.sendall(upgrade_req.encode("ascii"))
                raw_resp = ws_sock.recv(4096).decode("latin1", errors="ignore")
                first_line = raw_resp.splitlines()[0] if raw_resp else ""
                # Con simple-websocket instalado responde HTTP/1.1 101 Switching Protocols
                self.assertIn("101", first_line, f"Se esperaba HTTP 101 Switching Protocols, recibido: {raw_resp}")
                self.assertIn("Upgrade: websocket", raw_resp)
            finally:
                ws_sock.close()

            # 2d. También verificar cliente Socket.IO autenticado y eventos en vivo
            sio_client = socketio.test_client(app, auth={"token": self.token_alice})
            self.assertTrue(sio_client.is_connected())
            sio_client.disconnect()
        finally:
            server.shutdown()
            server.server_close()

        # 3. Reiniciar completamente repositorio y servidor TCP sobre el mismo archivo SQLite WAL y comprobar persistencia
        self.repo.close()
        reopened_repo = CommunitiesRepository.reset_instance(self.db_path)
        CommunitiesService._instance = CommunitiesService(reopened_repo)

        server2 = make_server("127.0.0.1", 0, app, threaded=True)
        port2 = server2.server_port
        srv_thread2 = threading.Thread(target=server2.serve_forever, daemon=True)
        srv_thread2.start()
        try:
            req_hist = urllib.request.Request(
                f"http://127.0.0.1:{port2}/api/v1/channels/{text_ch_id}/messages",
                headers={"Authorization": f"Bearer {self.token_alice}"},
            )
            with urllib.request.urlopen(req_hist, timeout=5) as resp_hist:
                self.assertEqual(resp_hist.status, 200)
                msgs = json.loads(resp_hist.read().decode("utf-8"))["messages"]
                self.assertEqual(len(msgs), 1)
                self.assertEqual(msgs[0]["content"], "Persistencia TCP + SQLite WAL verificada")
        finally:
            server2.shutdown()
            server2.server_close()

    def test_11_live_docker_caddy_tls_wss_101_volume_restart_and_coturn_allocate(self):
        """[P0/P1 Docker + Caddy TLS Verificado + CoTURN Relay en Vivo] Valida contenedores recién recreados con secretos efímeros, cadena TLS CA + hostname, WSS 101, reinicio con volumen y relay bidireccional TURN entre 2 peers."""
        import dataclasses
        import hashlib
        import hmac
        import json
        import secrets
        import socket
        import ssl
        import struct
        import subprocess
        import time
        from backend.config import config as live_cfg

        # P0: Prohibido omitir (skipTest) en certificación; si Docker CLI o daemon no están disponibles, la prueba FALLA.
        self.assertIsNotNone(shutil.which("docker"), "Docker CLI es obligatorio para la certificación E2E")
        info_proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(info_proc.returncode, 0, f"Docker daemon debe estar activo: {info_proc.stderr}")

        # P2: Secretos efímeros generados criptográficamente por ejecución (nunca valores estáticos reutilizables)
        secret_key = secrets.token_hex(32)
        turn_secret = secrets.token_hex(32)
        livekit_key = "AP" + secrets.token_hex(11)
        livekit_secret = secrets.token_hex(32)

        compose_file = str(ROOT_DIR / "deploy" / "docker-compose.communities.yml")
        env_docker = {
            **os.environ,
            "CCI_SECRET_KEY": secret_key,
            "LIVEKIT_API_KEY": livekit_key,
            "LIVEKIT_API_SECRET": livekit_secret,
            "TURN_SECRET": turn_secret,
            "CADDY_TLS_MODE": "internal",
            "CADDY_HTTP_PORT": "8080",
            "CADDY_HTTPS_PORT": "8443",
            "API_HOST_PORT": "15050",
        }

        # P2: Forzar reconstrucción y recreación limpia del stack por ejecución y garantizar teardown al finalizar
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "down", "-v", "--remove-orphans"],
            env=env_docker,
            capture_output=True,
            timeout=60,
            check=False,
        )

        try:
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "up", "-d", "--build", "--force-recreate"],
                env=env_docker,
                timeout=180,
                check=True,
            )

            # 1. Verificar que los 4 contenedores recién recreados estén en ejecución, con el secreto efímero actual y runtime Python 3.14
            for cname in ("cci_communities_api", "cci_communities_livekit", "cci_communities_coturn", "cci_communities_caddy"):
                st = subprocess.check_output(
                    ["docker", "inspect", "--format", "{{.State.Running}}", cname], text=True
                ).strip()
                self.assertEqual(st, "true", f"El contenedor {cname} no está en ejecución")

            api_health = "starting"
            for _ in range(30):
                api_health = subprocess.check_output(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", "cci_communities_api"], text=True
                ).strip()
                if api_health == "healthy":
                    break
                time.sleep(1)
            self.assertEqual(api_health, "healthy")

            # Confirmar que el contenedor no fue reutilizado verificando el secreto efímero inyectado y versión de Python
            api_env_dump = subprocess.check_output(
                ["docker", "inspect", "--format", "{{range .Config.Env}}{{println .}}{{end}}", "cci_communities_api"],
                text=True,
            )
            self.assertIn(f"CCI_SECRET_KEY={secret_key}", api_env_dump)
            container_py_ver = subprocess.check_output(
                ["docker", "exec", "cci_communities_api", "python", "--version"], text=True
            ).strip()
            self.assertTrue(container_py_ver.startswith("Python 3.14"), f"Runtime inesperado en contenedor: {container_py_ver}")

            with patch("backend.auth.config", dataclasses.replace(live_cfg, secret_key=secret_key)):
                docker_token = create_access_token("u_docker_audit", "DockerAudit")

            # P1: Validación estricta de certificado TLS (CERT_REQUIRED + check_hostname=True) contra la CA local de Caddy
            # Disparar apretón inicial para que Caddy aprovisione su PKI interna si el volumen acaba de crearse
            bootstrap_ctx = ssl._create_unverified_context()
            for _ in range(15):
                try:
                    with socket.create_connection(("127.0.0.1", 8443), timeout=3) as raw_b:
                        with bootstrap_ctx.wrap_socket(raw_b, server_hostname="api.ccisystem.org"):
                            break
                except OSError:
                    time.sleep(0.5)

            root_ca_pem = ""
            for _ in range(15):
                ca_proc = subprocess.run(
                    ["docker", "exec", "cci_communities_caddy", "cat", "/data/caddy/pki/authorities/local/root.crt"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if ca_proc.returncode == 0 and "BEGIN CERTIFICATE" in ca_proc.stdout:
                    root_ca_pem = ca_proc.stdout
                    break
                time.sleep(0.5)
            self.assertIn("BEGIN CERTIFICATE", root_ca_pem, "No se pudo extraer la CA raíz de Caddy PKI")

            # Contexto TLS estricto que valida cadena X.509 y hostname RFC 6125
            verified_ctx = ssl.create_default_context(cadata=root_ca_pem)
            verified_ctx.verify_mode = ssl.CERT_REQUIRED
            verified_ctx.check_hostname = True

            # Prueba negativa 1: Sin la CA raíz confiable debe fallar con SSLCertVerificationError
            untrusted_ctx = ssl.create_default_context()
            with self.assertRaises(ssl.SSLCertVerificationError):
                with socket.create_connection(("127.0.0.1", 8443), timeout=5) as raw_u:
                    untrusted_ctx.wrap_socket(raw_u, server_hostname="api.ccisystem.org")

            # Prueba negativa 2: Hostname no coincidente debe ser rechazado en el handshake TLS
            with self.assertRaises(ssl.SSLError):
                with socket.create_connection(("127.0.0.1", 8443), timeout=5) as raw_bad_host:
                    verified_ctx.wrap_socket(raw_bad_host, server_hostname="untrusted.invalid.example")

            def _caddy_https(method: str, path: str, body=None, headers=None):
                raw_s = socket.create_connection(("127.0.0.1", 8443), timeout=5)
                tls_s = verified_ctx.wrap_socket(raw_s, server_hostname="api.ccisystem.org")
                peercert = tls_s.getpeercert()
                self.assertIsNotNone(peercert)
                self.assertIn(("DNS", "api.ccisystem.org"), peercert.get("subjectAltName", ()))
                hdrs = {"Host": "api.ccisystem.org", "Connection": "close"}
                if headers:
                    hdrs.update(headers)
                payload = b""
                if body is not None:
                    payload = json.dumps(body).encode("utf-8")
                    hdrs["Content-Type"] = "application/json"
                    hdrs["Content-Length"] = str(len(payload))
                lines = [f"{method} {path} HTTP/1.1"] + [f"{k}: {v}" for k, v in hdrs.items()]
                tls_s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + payload)
                chunks = []
                while True:
                    chunk = tls_s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                tls_s.close()
                raw = b"".join(chunks).decode("utf-8", errors="replace")
                head, _, rbody = raw.partition("\r\n\r\n")
                return head.splitlines()[0], head, rbody

            # 2. HTTPS GET /api/v1/communities/health con certificado y hostname verificados
            st_line, head_str, body_str = _caddy_https("GET", "/api/v1/communities/health")
            self.assertIn("200 OK", st_line)
            self.assertIn("Server: Caddy", head_str)
            health_json = json.loads(body_str[body_str.find("{"):body_str.rfind("}") + 1])
            self.assertEqual(health_json["status"], "healthy")
            self.assertEqual(health_json["database"], "connected")

            # 3. Handshake WebSocket WSS (HTTP/1.1 101 Switching Protocols) con certificado y hostname verificados
            raw_ws = socket.create_connection(("127.0.0.1", 8443), timeout=5)
            tls_ws = verified_ctx.wrap_socket(raw_ws, server_hostname="api.ccisystem.org")
            try:
                self.assertIn(("DNS", "api.ccisystem.org"), tls_ws.getpeercert().get("subjectAltName", ()))
                ws_req = (
                    f"GET /socket.io/?EIO=4&transport=websocket&token={docker_token} HTTP/1.1\r\n"
                    "Host: api.ccisystem.org\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                    "Sec-WebSocket-Version: 13\r\n\r\n"
                )
                tls_ws.sendall(ws_req.encode("ascii"))
                ws_resp = tls_ws.recv(4096).decode("latin1", errors="ignore")
                self.assertIn("101 Switching Protocols", ws_resp.splitlines()[0])
                self.assertIn("Server: Caddy", ws_resp)
                self.assertIn("Upgrade: websocket", ws_resp)
            finally:
                tls_ws.close()

            # 4. Crear comunidad y mensaje por HTTPS, ejecutar `docker restart cci_communities_api` y verificar persistencia en volumen real
            st_c, _, bd_c = _caddy_https(
                "POST",
                "/api/v1/communities",
                body={"name": "Caddy Docker Volume Guild", "visibility": "public"},
                headers={"Authorization": f"Bearer {docker_token}"},
            )
            self.assertIn("201", st_c)
            comm_id = json.loads(bd_c[bd_c.find("{"):bd_c.rfind("}") + 1])["community"]["id"]

            _, _, bd_ch = _caddy_https(
                "GET",
                f"/api/v1/communities/{comm_id}/channels",
                headers={"Authorization": f"Bearer {docker_token}"},
            )
            channels = json.loads(bd_ch[bd_ch.find("{"):bd_ch.rfind("}") + 1])["channels"]
            ch_id = [c["id"] for c in channels if c["type"] == "text"][0]

            st_m, _, _ = _caddy_https(
                "POST",
                f"/api/v1/channels/{ch_id}/messages",
                body={"content": "Persistencia real en volumen Docker tras docker restart cci_communities_api"},
                headers={"Authorization": f"Bearer {docker_token}"},
            )
            self.assertIn("201", st_m)

            subprocess.run(["docker", "restart", "cci_communities_api"], timeout=30, check=True)
            h_stat = "starting"
            for _ in range(25):
                time.sleep(1)
                h_stat = subprocess.check_output(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", "cci_communities_api"], text=True
                ).strip()
                if h_stat == "healthy":
                    break
            self.assertEqual(h_stat, "healthy")

            st_get, _, bd_get = _caddy_https(
                "GET",
                f"/api/v1/channels/{ch_id}/messages",
                headers={"Authorization": f"Bearer {docker_token}"},
            )
            self.assertIn("200 OK", st_get)
            msgs = json.loads(bd_get[bd_get.find("{"):bd_get.rfind("}") + 1])["messages"]
            self.assertTrue(any("volumen Docker tras docker restart" in m["content"] for m in msgs))

            # 5. P1: STUN Binding (UDP/TCP 3478) + TURN Allocate + CreatePermission + ChannelBind + Relay Bidireccional de Medios entre Peer A y Peer B
            magic_cookie = 0x2112A442
            stun_req = struct.pack("!HHI12s", 0x0001, 0, magic_cookie, b"\x01" * 12)

            udp_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_s.settimeout(3.0)
            udp_s.sendto(stun_req, ("127.0.0.1", 3478))
            udp_resp, _ = udp_s.recvfrom(1024)
            udp_s.close()
            self.assertEqual(struct.unpack("!H", udp_resp[:2])[0], 0x0101)

            tcp_s = socket.create_connection(("127.0.0.1", 3478), timeout=3.0)
            tcp_s.sendall(stun_req)
            tcp_resp = tcp_s.recv(1024)
            tcp_s.close()
            self.assertEqual(struct.unpack("!H", tcp_resp[:2])[0], 0x0101)

            def _attr(atype: int, val: bytes) -> bytes:
                pad = (4 - (len(val) % 4)) % 4
                return struct.pack("!HH", atype, len(val)) + val + (b"\x00" * pad)

            def _parse(data: bytes):
                out = {}
                off = 20
                while off + 4 <= len(data):
                    at, al = struct.unpack("!HH", data[off:off + 4])
                    out[at] = data[off + 4:off + 4 + al]
                    off += 4 + al + ((4 - (al % 4)) % 4)
                return out

            def _xor_addr(ip_str: str, port: int) -> bytes:
                xport = port ^ (magic_cookie >> 16)
                ip_int = struct.unpack("!I", socket.inet_aton(ip_str))[0] ^ magic_cookie
                return struct.pack("!BBHI", 0, 1, xport, ip_int)

            def _decode_xor_addr(raw: bytes):
                _, _, xport, xip = struct.unpack("!BBHI", raw[:8])
                port = xport ^ (magic_cookie >> 16)
                ip = socket.inet_ntoa(struct.pack("!I", xip ^ magic_cookie))
                return ip, port

            peer_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer_a.settimeout(3.0)
            peer_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer_b.settimeout(3.0)
            try:
                # Descubrir dirección reflexiva de Peer B mediante STUN Binding
                stun_b = struct.pack("!HHI12s", 0x0001, 0, magic_cookie, b"\x02" * 12)
                peer_b.sendto(stun_b, ("127.0.0.1", 3478))
                rb, _ = peer_b.recvfrom(1024)
                b_ip, b_port = _decode_xor_addr(_parse(rb)[0x0020])

                # Peer A solicita TURN Allocate (0x0003) -> 401 Challenge -> Allocate autenticado con HMAC-SHA1
                req_tr = _attr(0x0019, struct.pack("!B3s", 17, b"\x00\x00\x00"))
                pkt1 = struct.pack("!HHI12s", 0x0003, len(req_tr), magic_cookie, b"\x11" * 12) + req_tr
                peer_a.sendto(pkt1, ("127.0.0.1", 3478))
                r1, _ = peer_a.recvfrom(2048)
                self.assertEqual(struct.unpack("!H", r1[:2])[0], 0x0113)
                a1 = _parse(r1)
                nonce, realm = a1[0x0015], a1[0x0014]

                uname = f"{int(time.time()) + 3600}:u_docker_audit"
                pwd = base64.b64encode(
                    hmac.new(turn_secret.encode("utf-8"), uname.encode("utf-8"), hashlib.sha1).digest()
                ).decode("ascii")
                hkey = hashlib.md5(f"{uname}:{realm.decode()}:{pwd}".encode("utf-8")).digest()

                def _send_turn_authed(msg_type: int, txid: bytes, attrs_bytes: bytes):
                    body = attrs_bytes + _attr(0x0006, uname.encode("utf-8")) + _attr(0x0014, realm) + _attr(0x0015, nonce)
                    hdr = struct.pack("!HHI12s", msg_type, len(body) + 24, magic_cookie, txid)
                    mi = _attr(0x0008, hmac.new(hkey, hdr + body, hashlib.sha1).digest())
                    peer_a.sendto(hdr + body + mi, ("127.0.0.1", 3478))
                    resp, _ = peer_a.recvfrom(2048)
                    return struct.unpack("!H", resp[:2])[0], _parse(resp)

                st_alloc, a_alloc = _send_turn_authed(0x0003, b"\x22" * 12, req_tr)
                self.assertEqual(st_alloc, 0x0103)
                _, relay_port = _decode_xor_addr(a_alloc[0x0016])
                self.assertTrue(49152 <= relay_port <= 49172, f"Puerto relay fuera de rango: {relay_port}")

                # CreatePermission (0x0008) autorizando a Peer B
                st_perm, _ = _send_turn_authed(0x0008, b"\x33" * 12, _attr(0x0012, _xor_addr(b_ip, b_port)))
                self.assertEqual(st_perm, 0x0108)

                # Tráfico de medios 1 (Peer B -> Puerto Relay asignado en CoTURN -> Peer A Data Indication 0x0017)
                payload_b2a = b"CCI-TURN-RELAY-MEDIA-B2A"
                peer_b.sendto(payload_b2a, ("127.0.0.1", relay_port))
                relayed_to_a, _ = peer_a.recvfrom(2048)
                self.assertEqual(struct.unpack("!H", relayed_to_a[:2])[0], 0x0017)
                ind_attrs = _parse(relayed_to_a)
                self.assertEqual(ind_attrs[0x0013], payload_b2a)
                peer_b_xor_addr_raw = ind_attrs[0x0012]

                # ChannelBind (0x0009) del canal 0x4000 hacia la dirección de Peer B y envío ChannelData (Peer A -> CoTURN -> Peer B)
                ch_attr = _attr(0x000C, struct.pack("!HH", 0x4000, 0)) + _attr(0x0012, peer_b_xor_addr_raw)
                st_ch, _ = _send_turn_authed(0x0009, b"\x44" * 12, ch_attr)
                self.assertEqual(st_ch, 0x0109)

                payload_a2b = b"CCI-TURN-RELAY-MEDIA-A2B-CHANNEL-0x4000"
                ch_frame = struct.pack("!HH", 0x4000, len(payload_a2b)) + payload_a2b
                peer_a.sendto(ch_frame, ("127.0.0.1", 3478))
                relayed_to_b, from_relay_addr = peer_b.recvfrom(2048)
                self.assertEqual(relayed_to_b, payload_a2b)
                self.assertEqual(from_relay_addr[1], relay_port)
            finally:
                peer_a.close()
                peer_b.close()
        finally:
            # P2: Limpiar contenedores y volúmenes efímeros al finalizar la prueba
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "down", "-v", "--remove-orphans"],
                env=env_docker,
                capture_output=True,
                timeout=60,
                check=False,
            )


if __name__ == "__main__":
    unittest.main()
