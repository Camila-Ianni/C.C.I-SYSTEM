"""
test_phase4_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 4 (Multijugador Piloto).
Verifica:
1. Declaración de capacidades multijugador en catalog_data (Da Vinci Fighters online=True).
2. Creación de salas públicas y privadas con código de invitación.
3. Bloqueo de acceso no autorizado a salas privadas con código incorrecto.
4. Gestión de anfitrión: expulsión y transferencia de rol.
5. Sincronización autoritativa a 60 Hz con validación de daño en servidor.
6. Transición de rounds (Best of 3) y registro final de partida en SQLite.
7. Desconexión temporal, pausa, recuperación de estado completo (FullWorldSync) y victoria por abandono (Forfeit).
8. Medición de RTT/latencia en MultiplayerNetworkClient.
9. Endpoints REST de salas y consulta de historial de partidas.
"""
import tempfile
import time
import unittest
from pathlib import Path
import catalog_data
import cci_database
from backend.contracts import ConnectionState, PlayerInputPacket, PlayerSlot, RoomStatus, SocketEvents
from backend.multiplayer_client import MultiplayerNetworkClient
from backend.room_manager import RoomManager
from backend.server import app
from backend.sync_engine import AuthoritativeSyncEngine


class TestPhase4MultiplayerPilot(unittest.TestCase):
    """Verifica salas, sincronización, desconexión y servidor autoritativo."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_multiplayer.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        self.room_mgr = RoomManager()
        self.room_mgr._rooms.clear()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_catalog_multiplayer_capabilities(self):
        # Da Vinci Fighters debe declarar soporte online y local
        cap_df = catalog_data.get_multiplayer_capabilities("davinci")
        self.assertTrue(cap_df["online"])
        self.assertTrue(cap_df["local"])

        # Otros juegos deben declarar online=False
        cap_ast = catalog_data.get_multiplayer_capabilities("asteroids")
        self.assertFalse(cap_ast["online"])

        cap_ms = catalog_data.get_multiplayer_capabilities("metalslug")
        self.assertFalse(cap_ms["online"])
        self.assertTrue(cap_ms["local"])

    def test_private_room_invite_code_authorization(self):
        # Crear sala privada
        room = self.room_mgr.create_room("davinci", "host_pilot", "HostPilot", visibility="private")
        self.assertEqual(room.visibility, "private")
        self.assertIsNotNone(room.invite_code)

        # Intento de unión sin código o con código erróneo: DEBE RECHAZAR
        fail_join = self.room_mgr.join_room(room.room_id, "intruder", "Intruder", invite_code="WRONG")
        self.assertIsNone(fail_join)

        # Intento con código correcto: DEBE PERMITIR
        ok_join = self.room_mgr.join_room(room.room_id, "guest_pilot", "GuestPilot", invite_code=room.invite_code)
        self.assertIsNotNone(ok_join)
        self.assertEqual(len(ok_join.members), 2)

    def test_host_controls_kick_and_transfer(self):
        room = self.room_mgr.create_room("davinci", "host_a", "HostA")
        self.room_mgr.join_room(room.room_id, "guest_b", "GuestB")

        # Expulsar miembro
        kicked = self.room_mgr.kick_member(room.room_id, actor_id="host_a", target_user_id="guest_b")
        self.assertIsNotNone(kicked)
        self.assertEqual(len(kicked.members), 1)

        # Unir de nuevo y transferir anfitrión
        self.room_mgr.join_room(room.room_id, "guest_b", "GuestB")
        transferred = self.room_mgr.transfer_host(room.room_id, actor_id="host_a", new_host_id="guest_b")
        self.assertIsNotNone(transferred)
        self.assertEqual(transferred.host_id, "guest_b")
        self.assertEqual(transferred.members["guest_b"].slot, PlayerSlot.P1)
        self.assertEqual(transferred.members["host_a"].slot, PlayerSlot.P2)

    def test_authoritative_simulation_and_best_of_3(self):
        engine = AuthoritativeSyncEngine("room_match_test")
        self.assertEqual(engine.current_round, 1)

        # P1 noquea a P2 en Round 1
        engine.p2.hp = 5
        hit_packet = PlayerInputPacket(
            room_id="room_match_test",
            player_id=1,
            tick=1,
            seq=1,
            dpad="idle",
            buttons=["punch"]
        )
        engine.p1.x = 1250.0  # en rango
        engine.push_input(hit_packet)
        snap1 = engine.step()

        self.assertEqual(snap1.status, "round_ended")
        self.assertEqual(engine.p1_wins, 1)

        # Iniciar Round 2
        engine.start_next_round()
        self.assertEqual(engine.current_round, 2)
        self.assertEqual(engine.p2.hp, 100)

        # P1 noquea a P2 en Round 2 -> Partida finalizada (Best of 3)
        engine.p2.hp = 4
        hit_packet2 = PlayerInputPacket(
            room_id="room_match_test",
            player_id=1,
            tick=2,
            seq=2,
            dpad="idle",
            buttons=["punch"]
        )
        engine.p1.x = 1250.0
        engine.push_input(hit_packet2)
        snap2 = engine.step()

        self.assertEqual(snap2.status, "match_over")
        self.assertEqual(engine.get_winner_slot(), 1)

        # Persistir resultado en SQLite
        ok = cci_database.record_match_result_entry(
            match_id="mat_test_01",
            room_id="room_match_test",
            game_id="davinci",
            started_at="2026-11-05T21:00:00",
            ended_at="2026-11-05T21:02:30",
            result_metadata={"winner_slot": 1, "p1_wins": 2, "p2_wins": 0}
        )
        self.assertTrue(ok)

        history = cci_database.get_match_history_entries(game_id="davinci")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["result_metadata"]["winner_slot"], 1)

    def test_disconnection_pause_and_full_recovery(self):
        room = self.room_mgr.create_room("davinci", "p1", "Pilot1", socket_id="sock_p1")
        self.room_mgr.join_room(room.room_id, "p2", "Pilot2", socket_id="sock_p2")
        room.status = RoomStatus.PLAYING

        engine = AuthoritativeSyncEngine(room.room_id)

        # Simular corte de red de P2
        self.room_mgr.handle_disconnect("sock_p2", grace_seconds=5.0)
        self.assertEqual(room.status, RoomStatus.PAUSED)
        self.assertEqual(room.members["p2"].connection_state, ConnectionState.DISCONNECTED)

        # P2 reconecta antes de vencer los 5s
        rec_room = self.room_mgr.join_room(room.room_id, "p2", "Pilot2", socket_id="new_sock_p2")
        self.assertIsNotNone(rec_room)
        self.assertEqual(rec_room.status, RoomStatus.PLAYING)

        # Recuperar estado completo
        full_sync = engine.get_full_world_sync()
        self.assertTrue(full_sync["full_recovery"])
        self.assertEqual(full_sync["room_id"], room.room_id)

    def test_forfeit_on_abandonment(self):
        engine = AuthoritativeSyncEngine("room_forfeit")
        snap = engine.handle_forfeit(quitter_slot=2)  # P2 abandona
        self.assertEqual(snap.status, "match_over")
        self.assertEqual(engine.get_winner_slot(), 1)
        self.assertEqual(engine.p1_wins, 2)

    def test_multiplayer_network_client_rtt(self):
        client = MultiplayerNetworkClient(room_id="room_net", player_id=1, user_id="p1")
        # Simular medición de latencia
        sent_time = (time.time() - 0.04) * 1000.0  # 40ms RTT
        ping = client.update_rtt(sent_time)
        self.assertGreater(ping, 10.0)
        self.assertLess(ping, 50.0)

        # Emitir entrada
        inp = client.emit_input(dpad="right", buttons=["punch"])
        self.assertEqual(inp.dpad, "right")
        self.assertEqual(client.tick, 1)

        # Recibir snapshot
        client.receive_snapshot({
            "room_id": "room_net",
            "tick": 1,
            "p1_state": {"x": 805, "hp": 100},
            "p2_state": {"x": 1295, "hp": 92},
            "status": "fighting"
        })
        remote = client.get_remote_fighter_state()
        self.assertEqual(remote["hp"], 92)


class TestPhase4RESTEndpoints(unittest.TestCase):
    """Verifica endpoints HTTP de la API Multijugador."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_multi_api.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_rest_multiplayer_room_and_history(self):
        # 1. Crear sala vía REST
        r_create = self.client.post("/api/v1/multiplayer/rooms/create", json={
            "game_id": "davinci",
            "host_id": "api_host",
            "username": "ApiHost"
        })
        self.assertEqual(r_create.status_code, 200)
        room_data = r_create.get_json()["room"]
        room_id = room_data["room_id"]
        invite_code = room_data["invite_code"]

        # 2. Unirse por código
        r_join = self.client.post("/api/v1/multiplayer/rooms/join", json={
            "invite_code": invite_code,
            "user_id": "api_guest",
            "username": "ApiGuest"
        })
        self.assertEqual(r_join.status_code, 200)

        # 3. Consultar sala
        r_get = self.client.get(f"/api/v1/multiplayer/rooms/{room_id}")
        self.assertEqual(r_get.status_code, 200)

        # 4. Consultar historial
        r_hist = self.client.get("/api/v1/multiplayer/matches/history")
        self.assertEqual(r_hist.status_code, 200)


if __name__ == "__main__":
    unittest.main()
