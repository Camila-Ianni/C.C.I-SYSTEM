"""
test_communities_phase7.py - Suite de pruebas unitarias herméticas para Escalabilidad, Métricas y Operabilidad.

Cubre:
1. Endpoint de salud /api/v1/health (y alias /api/v1/communities/health) retorna 200 y status 'healthy'.
2. Exportador /api/v1/metrics genera formato de texto estándar Prometheus (RFC 0001).
3. Exportador /api/v1/metrics con Accept: application/json genera snapshot estructurado.
4. Consulta de límites operativos en /api/v1/system/limits con cuotas publicadas.
5. Incremento de contadores en creación de comunidades, envío de mensajes y unión a voz.
6. Incremento de contadores en reproducción de soundboard y acciones de moderación.
7. Registro y cálculo de latencia de peticiones en métricas Prometheus.
8. Harness multihilo LoadTestBenchmark evalúa concurrencia con 100% éxito y percentiles p50/p95.
9. Protección contra ráfagas y spam en soundboard mediante respuesta 429 Retry-After.
10. Diagnóstico SRE y degradación controlada ante fallo simulado de base de datos (503).
"""

import base64
import os
import shutil
import tempfile
import time
import unittest
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.communities.metrics import CommunityMetricsCollector
from backend.communities.load_testing import LoadTestBenchmark
from backend.server import app
from backend.auth import create_access_token


class TestCommunitiesPhase7Scalability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cci_test_p7_")
        self.db_path = os.path.join(self.temp_dir, "test_communities_phase7.db")

        self.repo = CommunitiesRepository(db_path=self.db_path)
        self.service = CommunitiesService(repo=self.repo)

        CommunitiesRepository._instance = self.repo
        CommunitiesService._instance = self.service

        app.config["TESTING"] = True
        self.client = app.test_client()

        # Reiniciar métricas para pruebas limpias
        collector = CommunityMetricsCollector.get_instance()
        for k in collector._counts:
            collector._counts[k] = 0
        collector._latencies.clear()

        # Usuarios de prueba
        self.owner_id = "user_owner_701"
        self.user2_id = "user_member_702"
        self.token_owner = create_access_token(self.owner_id, "owner7")
        self.token_user2 = create_access_token(self.user2_id, "member7")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_health_check_healthy(self):
        """Verifica que el endpoint de salud retorne 200 con componentes listos."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["livekit_sfu"], "ready")
        self.assertIn("uptime_seconds", data)

        # Verificar alias
        resp_alias = self.client.get("/api/v1/communities/health")
        self.assertEqual(resp_alias.status_code, 200)

    def test_02_metrics_prometheus_format(self):
        """Verifica que /api/v1/metrics retorne formato estándar Prometheus (RFC 0001)."""
        resp = self.client.get("/api/v1/metrics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp.content_type)
        body = resp.get_data(as_text=True)

        self.assertIn("# HELP communities_uptime_seconds", body)
        self.assertIn("# TYPE communities_uptime_seconds gauge", body)
        self.assertIn("communities_uptime_seconds", body)
        self.assertIn("communities_created_total", body)
        self.assertIn("communities_messages_total", body)
        self.assertIn("communities_voice_joins_total", body)

    def test_03_metrics_json_snapshot(self):
        """Verifica que /api/v1/metrics con Accept: application/json retorne snapshot estructurado."""
        resp = self.client.get("/api/v1/metrics", headers={"Accept": "application/json"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("uptime_seconds", data)
        self.assertIn("counters", data)
        self.assertIn("avg_latency_seconds", data)
        self.assertIsInstance(data["counters"], dict)

    def test_04_system_limits_endpoint(self):
        """Verifica que /api/v1/system/limits publique formalmente los límites operativos."""
        resp = self.client.get("/api/v1/system/limits")
        self.assertEqual(resp.status_code, 200)
        limits = resp.get_json()["limits"]
        self.assertEqual(limits["max_members_per_community"], 500)
        self.assertEqual(limits["max_channels_per_community"], 100)
        self.assertEqual(limits["max_roles_per_community"], 50)
        self.assertEqual(limits["max_streams_per_channel"], 1)
        self.assertEqual(limits["max_voice_participants_per_channel"], 100)
        self.assertEqual(limits["max_message_length_chars"], 2000)
        self.assertEqual(limits["sound_cooldown_seconds"], 5)
        self.assertEqual(limits["stream_max_fps"], 60)

    def test_05_community_message_voice_metrics_increment(self):
        """Verifica que crear comunidad, mensaje y pedir token de voz incrementen contadores."""
        # Crear comunidad
        resp_c = self.client.post(
            "/api/v1/communities",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"name": "Comunidad Metricas", "slug": "comm-metrics-7"}
        )
        self.assertEqual(resp_c.status_code, 201)
        comm_id = resp_c.get_json()["community"]["id"]

        collector = CommunityMetricsCollector.get_instance()
        self.assertEqual(collector.get_snapshot()["counters"]["communities_created_total"], 1)

        # Crear canal de texto y enviar mensaje
        ch_text = self.service.create_channel(
            community_id=comm_id,
            requester_id=self.owner_id,
            name="chat-metricas",
            channel_type="text"
        )
        resp_m = self.client.post(
            f"/api/v1/channels/{ch_text['id']}/messages",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"content": "Mensaje de telemetria"}
        )
        self.assertEqual(resp_m.status_code, 201)
        self.assertEqual(collector.get_snapshot()["counters"]["communities_messages_total"], 1)

        # Crear canal de voz y solicitar token
        ch_voice = self.service.create_channel(
            community_id=comm_id,
            requester_id=self.owner_id,
            name="voz-metricas",
            channel_type="voice"
        )
        resp_v = self.client.post(
            f"/api/v1/channels/{ch_voice['id']}/voice-token",
            headers={"Authorization": f"Bearer {self.token_owner}"}
        )
        self.assertEqual(resp_v.status_code, 200)
        self.assertEqual(collector.get_snapshot()["counters"]["communities_voice_joins_total"], 1)

    def test_06_soundboard_and_moderation_metrics_increment(self):
        """Verifica que soundboard y moderación incrementen sus contadores correspondientes."""
        comm = self.service.create_community(owner_id=self.owner_id, name="Comm Mod", slug="comm-mod-7")
        ch_voice = self.service.create_channel(
            community_id=comm["id"], requester_id=self.owner_id, name="voice-deck", channel_type="voice"
        )
        self.repo.add_member(community_id=comm["id"], user_id=self.user2_id)

        # Crear sonido válido
        mp3_dummy = b"\xff\xfb\x90\x00" + b"\x00" * 2000
        sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            title="Ta-Da",
            file_bytes=mp3_dummy,
            owner_id=comm["id"],
        )

        collector = CommunityMetricsCollector.get_instance()
        collector._counts["communities_soundboard_plays_total"] = 0
        collector._counts["communities_moderation_actions_total"] = 0

        # Reproducir sonido
        resp_play = self.client.post(
            f"/api/v1/sounds/{sound['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"channel_id": ch_voice["id"]}
        )
        self.assertEqual(resp_play.status_code, 200)
        self.assertEqual(collector.get_snapshot()["counters"]["communities_soundboard_plays_total"], 1)

        # Advertencia de moderación
        resp_warn = self.client.post(
            f"/api/v1/communities/{comm['id']}/moderation/warn",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"target_user_id": self.user2_id, "reason": "Test moderacion"}
        )
        self.assertEqual(resp_warn.status_code, 201)
        self.assertEqual(collector.get_snapshot()["counters"]["communities_moderation_actions_total"], 1)

        # Mute de moderación
        resp_mute = self.client.post(
            f"/api/v1/communities/{comm['id']}/moderation/mute",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"target_user_id": self.user2_id, "duration_minutes": 10, "reason": "Mute test"}
        )
        self.assertEqual(resp_mute.status_code, 201)
        self.assertEqual(collector.get_snapshot()["counters"]["communities_moderation_actions_total"], 2)

    def test_07_api_latency_tracking(self):
        """Verifica que el recolector almacene latencias y calcule promedios y reporte en Prometheus."""
        collector = CommunityMetricsCollector.get_instance()
        collector.record_latency(0.010)
        collector.record_latency(0.020)
        collector.record_latency(0.030)

        snapshot = collector.get_snapshot()
        self.assertGreaterEqual(snapshot["latency_sample_count"], 3)
        self.assertAlmostEqual(snapshot["avg_latency_seconds"], 0.020, places=3)

        prom_text = collector.format_prometheus()
        self.assertIn("communities_api_latency_seconds", prom_text)

    def test_08_load_test_benchmark_multithreaded(self):
        """Verifica que LoadTestBenchmark ejecute peticiones concurrentes y reporte estadísticas válidas."""
        benchmark = LoadTestBenchmark(concurrency=4, total_requests=20)

        def dummy_request():
            resp = self.client.get("/api/v1/health")
            return resp.status_code == 200

        results = benchmark.run_benchmark(dummy_request)
        self.assertEqual(results["total_requests"], 20)
        self.assertEqual(results["concurrency"], 4)
        self.assertEqual(results["success_count"], 20)
        self.assertEqual(results["failure_count"], 0)
        self.assertEqual(results["success_rate_percent"], 100.0)
        self.assertGreater(results["requests_per_second"], 0)
        self.assertGreaterEqual(results["latency_p50_ms"], 0)
        self.assertGreaterEqual(results["latency_p95_ms"], 0)

    def test_09_soundboard_spam_cooldown_protection(self):
        """Verifica protección de cooldown (429 con Retry-After) al disparar ráfagas de soundboard."""
        comm = self.service.create_community(owner_id=self.owner_id, name="Spam Comm", slug="comm-spam-7")
        ch_voice = self.service.create_channel(
            community_id=comm["id"], requester_id=self.owner_id, name="spam-voice", channel_type="voice"
        )
        mp3_dummy = b"\xff\xfb\x90\x00" + b"\x00" * 2000
        sound = self.service.upload_sound(
            actor_id=self.owner_id,
            owner_type="community",
            title="Horn",
            file_bytes=mp3_dummy,
            owner_id=comm["id"],
        )

        # Primer disparo: permitido
        resp1 = self.client.post(
            f"/api/v1/sounds/{sound['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"channel_id": ch_voice["id"]}
        )
        self.assertEqual(resp1.status_code, 200)

        # Segundo disparo inmediato: rechazado con 429
        resp2 = self.client.post(
            f"/api/v1/sounds/{sound['id']}/play-authorize",
            headers={"Authorization": f"Bearer {self.token_owner}"},
            json={"channel_id": ch_voice["id"]}
        )
        self.assertEqual(resp2.status_code, 429)
        self.assertEqual(resp2.get_json()["error"], "SOUND_COOLDOWN")
        self.assertIn("Retry-After", resp2.headers)

    def test_10_runbook_diagnostic_health_and_degraded_state(self):
        """Verifica detección de degradación en health check si la base de datos no está disponible."""
        # Estado normal
        resp_healthy = self.client.get("/api/v1/health")
        self.assertEqual(resp_healthy.status_code, 200)
        self.assertEqual(resp_healthy.get_json()["status"], "healthy")

        # Simular base de datos inaccesible sustituyendo el repositorio por uno roto
        broken_repo = type("BrokenRepo", (), {
            "get_community": lambda self, cid: (_ for _ in ()).throw(RuntimeError("DB_CONNECTION_LOST"))
        })()
        original_repo = self.service._repo
        self.service._repo = broken_repo

        try:
            resp_degraded = self.client.get("/api/v1/health")
            self.assertEqual(resp_degraded.status_code, 503)
            data = resp_degraded.get_json()
            self.assertEqual(data["status"], "degraded")
            self.assertEqual(data["database"], "disconnected")
        finally:
            self.service._repo = original_repo

        # Restaurado
        resp_restored = self.client.get("/api/v1/health")
        self.assertEqual(resp_restored.status_code, 200)
        self.assertEqual(resp_restored.get_json()["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
