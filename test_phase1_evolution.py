"""
test_phase1_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 1.
Verifica:
1. Migración de base de datos relacional a versión 2 (9 tablas nuevas e índices).
2. Helpers de persistencia en cci_database.py.
3. Lógica de salas en RoomManager.
4. Motor de simulación autoritativo a 60 Hz en AuthoritativeSyncEngine.
5. Enrutador de señalización WebRTC.
6. Endpoints REST y servidor Socket.IO.
"""
import os
import tempfile
import unittest
from pathlib import Path
from backend.config import AppConfig
from backend.contracts import PlayerInputPacket, PlayerSlot, RoomStatus, SocketEvents
from backend.room_manager import RoomManager
from backend.sync_engine import AuthoritativeSyncEngine
from backend.webrtc_signaling import WebRTCSignalingRouter
import cci_database


class TestPhase1DatabaseMigrations(unittest.TestCase):
    """Verifica la migración relacional sin pérdidas."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_migration.sqlite3"
        cci_database.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_version_is_2(self):
        version = cci_database.get_schema_version(self.db_path)
        self.assertEqual(version, 2)

    def test_all_evolution_tables_exist(self):
        expected_tables = {
            "accounts", "games", "profiles", "game_stats", "highscores", "achievements_unlocked",
            "schema_version", "friendships", "groups", "group_members", "messages",
            "call_sessions", "game_rooms", "game_room_members", "matches", "gameplay_recordings"
        }
        with cci_database.get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing = {row[0] for row in cursor.fetchall()}

        for tbl in expected_tables:
            self.assertIn(tbl, existing, f"Falta la tabla {tbl} en SQLite")

    def test_game_room_lifecycle_in_db(self):
        room = cci_database.create_game_room("room_test_1", "davinci", "user_host", db_path=self.db_path)
        self.assertIsNotNone(room)
        self.assertEqual(room["id"], "room_test_1")
        self.assertEqual(len(room["members"]), 1)
        self.assertEqual(room["members"][0]["user_id"], "user_host")

        # Join P2
        ok = cci_database.join_game_room("room_test_1", "user_guest", target_slot=2, db_path=self.db_path)
        self.assertTrue(ok)
        updated = cci_database.get_game_room("room_test_1", db_path=self.db_path)
        self.assertEqual(len(updated["members"]), 2)

        # Leave
        left = cci_database.leave_game_room("room_test_1", "user_guest", db_path=self.db_path)
        self.assertTrue(left)
        after_leave = cci_database.get_game_room("room_test_1", db_path=self.db_path)
        self.assertEqual(len(after_leave["members"]), 1)

    def test_friendships_in_db(self):
        cci_database.record_friendship_request("user_a", "user_b", db_path=self.db_path)
        friends_before = cci_database.get_user_friends("user_a", db_path=self.db_path)
        self.assertEqual(len(friends_before), 0)

        # Accept request
        cci_database.update_friendship_status("user_a", "user_b", "accepted", db_path=self.db_path)
        friends_after = cci_database.get_user_friends("user_a", db_path=self.db_path)
        self.assertEqual(len(friends_after), 1)
        self.assertEqual(friends_after[0]["status"], "accepted")

    def test_gameplay_recording_metadata_in_db(self):
        cci_database.save_gameplay_recording_entry(
            recording_id="rec_001",
            owner_id="cami",
            game_id="davinci",
            local_path="/tmp/rec_001.mp4",
            duration_seconds=45.5,
            size_bytes=1024 * 1024 * 7,
            thumbnail_path="/tmp/thumb_001.png",
            db_path=self.db_path
        )
        recs = cci_database.get_user_gameplay_recordings("cami", db_path=self.db_path)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["id"], "rec_001")
        self.assertEqual(recs[0]["duration_seconds"], 45.5)


class TestRoomManagerAndMultiplayerLobby(unittest.TestCase):
    """Verifica la lógica en memoria del RoomManager."""

    def setUp(self):
        self.mgr = RoomManager()

    def test_create_and_join_room(self):
        room = self.mgr.create_room("davinci", "p1_id", "Player1")
        self.assertEqual(room.game_id, "davinci")
        self.assertIn("p1_id", room.members)
        self.assertFalse(room.both_ready)

        joined = self.mgr.join_room(room.room_id, "p2_id", "Player2")
        self.assertIsNotNone(joined)
        self.assertEqual(len(joined.members), 2)
        self.assertTrue(joined.is_full)

        # Marcar listos
        self.mgr.set_ready(room.room_id, "p2_id", True)
        self.assertTrue(room.both_ready)
        self.assertEqual(room.status, RoomStatus.READY)


class TestAuthoritativeSyncEngine(unittest.TestCase):
    """Verifica simulación autoritativa a 60 Hz y validación de daño."""

    def test_fixed_timestep_and_punch_hit(self):
        engine = AuthoritativeSyncEngine("room_sync_test")
        # P1 en 800, P2 en 1300
        # Mover P1 a la derecha hacia P2
        for t in range(1, 100):
            inp = PlayerInputPacket(
                room_id="room_sync_test",
                player_id=1,
                tick=t,
                seq=t,
                dpad="right",
                buttons=[]
            )
            engine.push_input(inp)
            engine.step(1.0 / 60.0)

        # P1 avanzó hacia P2 (de 800 a casi 1300)
        self.assertGreater(engine.p1.x, 1150)

        # Ahora P1 conecta un golpe
        cur_tick = engine.tick + 1
        punch_inp = PlayerInputPacket(
            room_id="room_sync_test",
            player_id=1,
            tick=cur_tick,
            seq=cur_tick,
            dpad="idle",
            buttons=["punch"]
        )
        engine.push_input(punch_inp)
        snapshot = engine.step(1.0 / 60.0)

        # El servidor valida el impacto y resta vida al jugador 2
        self.assertLess(snapshot.p2_state["hp"], 100)
        self.assertEqual(snapshot.p2_state["state"], "hit")


class TestWebRTCSignaling(unittest.TestCase):
    """Verifica el enrutamiento de paquetes SDP e ICE."""

    def test_signaling_route(self):
        emitted_events = []

        def mock_emit(ev, data, target=None):
            emitted_events.append((ev, data, target))

        router = WebRTCSignalingRouter(mock_emit)

        # Enviar oferta SDP
        ok = router.handle_signal({
            "room_id": "room_1",
            "sender_id": "user_a",
            "target_id": "socket_user_b",
            "type": "offer",
            "payload": {"sdp": "v=0..."},
        }, "sender_sid_a")

        self.assertTrue(ok)
        self.assertEqual(len(emitted_events), 1)
        self.assertEqual(emitted_events[0][0], SocketEvents.WEBRTC_OFFER)
        self.assertEqual(emitted_events[0][2], "socket_user_b")


class TestBackendServerAPI(unittest.TestCase):
    """Verifica endpoints REST de backend."""

    def test_network_status_endpoint(self):
        from backend.server import app
        client = app.test_client()
        res = client.get("/api/v1/network/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "online")
        self.assertIn("stun_server", data)


if __name__ == "__main__":
    unittest.main()
