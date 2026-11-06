"""
test_phase5_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 5 (Llamadas de Voz WebRTC).
Verifica:
1. Inicio de llamada grupal y persistencia en tabla call_sessions.
2. Garantía de privacidad: grabación desactivada por defecto (no-record).
3. Unión de participantes y disparo de eventos de handshake WebRTC P2P.
4. Silenciamiento (mute/unmute) y actualización de estados de micrófono.
5. Salida de llamada y finalización automática cuando el último miembro abandona.
6. Consulta de llamada activa por grupo.
7. Distribución de servidores STUN y TURN para redes móviles con CGNAT.
8. Enrutamiento de ofertas SDP, respuestas e intercambio de candidatos ICE.
9. Endpoints REST de la API de Voz.
"""
import tempfile
import unittest
from pathlib import Path
import cci_database
from backend.contracts import SocketEvents
from backend.friends_service import FriendsService
from backend.auth import create_access_token
from backend.server import app
from backend.voice_service import VoiceService
from backend.webrtc_signaling import WebRTCSignalingRouter


class TestPhase5VoiceService(unittest.TestCase):
    """Verifica la lógica de negocio y persistencia de llamadas de voz."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_voice.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        self.voice_svc = VoiceService()
        self.voice_svc._active_calls.clear()

        # Crear grupo de prueba
        FriendsService.get_instance().create_group("Grupo Da Vinci Voice", "pilot_1")
        groups = cci_database.get_user_groups("pilot_1")
        self.group_id = groups[0]["id"]
        FriendsService.get_instance().invite_member(self.group_id, "pilot_1", "pilot_2")

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_start_call_and_privacy_guarantee(self):
        res = self.voice_svc.start_call(self.group_id, "pilot_1", "PilotOne")
        self.assertTrue(res["success"])
        call = res["call"]
        self.assertEqual(call["group_id"], self.group_id)
        self.assertEqual(call["started_by"], "pilot_1")
        self.assertEqual(len(call["participants"]), 1)
        # Garantía de privacidad: no grabación por defecto
        self.assertFalse(call["recording_enabled"])

        # Verificar persistencia en SQLite
        db_call = cci_database.get_call_session_by_id(call["session_id"])
        self.assertIsNotNone(db_call)
        self.assertEqual(db_call["status"], "active")

    def test_join_and_mute_toggle(self):
        res_start = self.voice_svc.start_call(self.group_id, "pilot_1", "PilotOne")
        session_id = res_start["call"]["session_id"]

        # Pilot 2 se une
        res_join = self.voice_svc.join_call(session_id, "pilot_2", "PilotTwo")
        self.assertTrue(res_join["success"])
        self.assertEqual(len(res_join["call"]["participants"]), 2)

        # Pilot 2 se silencia
        mute_res = self.voice_svc.toggle_mute(session_id, "pilot_2", muted=True)
        self.assertTrue(mute_res["success"])
        self.assertTrue(mute_res["muted"])

        call = self.voice_svc._active_calls[session_id]
        self.assertTrue(call.participants["pilot_2"].muted)
        self.assertFalse(call.participants["pilot_1"].muted)

    def test_leave_call_and_auto_termination(self):
        res_start = self.voice_svc.start_call(self.group_id, "pilot_1", "PilotOne")
        session_id = res_start["call"]["session_id"]
        self.voice_svc.join_call(session_id, "pilot_2", "PilotTwo")

        # Pilot 1 sale
        leave1 = self.voice_svc.leave_call(session_id, "pilot_1")
        self.assertTrue(leave1["success"])
        self.assertIn(session_id, self.voice_svc._active_calls)

        # Pilot 2 sale -> llamada debe terminar automáticamente
        leave2 = self.voice_svc.leave_call(session_id, "pilot_2")
        self.assertTrue(leave2["success"])
        self.assertNotIn(session_id, self.voice_svc._active_calls)

        # Comprobar estado final en base de datos
        db_call = cci_database.get_call_session_by_id(session_id)
        self.assertEqual(db_call["status"], "ended")
        self.assertIsNotNone(db_call["ended_at"])

    def test_ice_servers_configuration(self):
        servers = self.voice_svc.get_ice_servers()
        self.assertIsInstance(servers, list)
        self.assertGreaterEqual(len(servers), 1)
        # Debe contener al menos servidor STUN
        has_stun = any("stun:" in url for s in servers for url in s.get("urls", []))
        self.assertTrue(has_stun)

    def test_webrtc_signaling_mesh(self):
        signals = []

        def mock_emit(ev, data, target=None):
            signals.append((ev, data, target))

        router = WebRTCSignalingRouter(mock_emit)

        # 1. Oferta
        router.handle_signal({
            "room_id": "call_123",
            "sender_id": "peer_a",
            "target_id": "sock_peer_b",
            "type": "offer",
            "payload": {"sdp": "v=0..."},
        }, "sock_peer_a")
        self.assertEqual(signals[-1][0], SocketEvents.WEBRTC_OFFER)

        # 2. Respuesta
        router.handle_signal({
            "room_id": "call_123",
            "sender_id": "peer_b",
            "target_id": "sock_peer_a",
            "type": "answer",
            "payload": {"sdp": "v=0..."},
        }, "sock_peer_b")
        self.assertEqual(signals[-1][0], SocketEvents.WEBRTC_ANSWER)

        # 3. Candidato ICE
        router.handle_signal({
            "room_id": "call_123",
            "sender_id": "peer_a",
            "target_id": "sock_peer_b",
            "type": "ice-candidate",
            "payload": {"candidate": "candidate:1 1 UDP..."},
        }, "sock_peer_a")
        self.assertEqual(signals[-1][0], SocketEvents.WEBRTC_ICE_CANDIDATE)


class TestPhase5VoiceRESTEndpoints(unittest.TestCase):
    """Verifica endpoints HTTP de la API de Voz."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_voice_api.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)
        self.client = app.test_client()

        # Preparar grupo
        FriendsService.get_instance().create_group("Voice Test API Group", "host_api")
        groups = cci_database.get_user_groups("host_api")
        self.group_id = groups[0]["id"]

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_voice_rest_lifecycle(self):
        token_host = create_access_token("host_api", "HostApi")
        token_guest = create_access_token("guest_api", "GuestApi")

        # 0. Verificación negativa: sin token debe fallar con 401
        r_unauth = self.client.post("/api/v1/voice/calls/start", json={"group_id": self.group_id})
        self.assertEqual(r_unauth.status_code, 401)

        # 1. Iniciar llamada autenticado
        r_start = self.client.post("/api/v1/voice/calls/start", json={
            "group_id": self.group_id,
        }, headers={"Authorization": f"Bearer {token_host}"})
        self.assertEqual(r_start.status_code, 200)
        session_id = r_start.get_json()["call"]["session_id"]

        # 2. Consultar llamada activa
        r_active = self.client.get(f"/api/v1/voice/calls/active/{self.group_id}", headers={"Authorization": f"Bearer {token_host}"})
        self.assertEqual(r_active.status_code, 200)
        self.assertTrue(r_active.get_json()["active"])

        # 3. Unirse autenticado
        r_join = self.client.post(f"/api/v1/voice/calls/{session_id}/join", json={}, headers={"Authorization": f"Bearer {token_guest}"})
        self.assertEqual(r_join.status_code, 200)

        # 4. Silenciar autenticado
        r_mute = self.client.post(f"/api/v1/voice/calls/{session_id}/mute", json={
            "muted": True
        }, headers={"Authorization": f"Bearer {token_guest}"})
        self.assertEqual(r_mute.status_code, 200)

        # 5. Obtener servidores ICE (Público)
        r_ice = self.client.get("/api/v1/voice/ice-servers")
        self.assertEqual(r_ice.status_code, 200)
        self.assertTrue(len(r_ice.get_json()["ice_servers"]) >= 1)

        # 6. Finalizar llamada autenticado
        r_end = self.client.post(f"/api/v1/voice/calls/{session_id}/end", json={}, headers={"Authorization": f"Bearer {token_host}"})
        self.assertEqual(r_end.status_code, 200)


if __name__ == "__main__":
    unittest.main()
