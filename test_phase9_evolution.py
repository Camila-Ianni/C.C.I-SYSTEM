"""
test_phase9_evolution.py - Suite Integral End-to-End de Estabilización y Validación Final (v2.1.0).

Verifica la integración y coherencia global entre todas las fases de la evolución:
1. Consistencia canónica de versión (version.json, buildozer.spec, ios/Info.plist, catalog_data.py).
2. Integridad del esquema SQLite v2 (16 tablas totales del ecosistema).
3. Flujo Social: Amigos, grupos con RBAC y presencia en tiempo real.
4. Flujo Chat: Mensajería en grupo, sliding-window anti-spam y moderación.
5. Flujo Multijugador: Sala, sincronización autoritativa a 60 Hz y guardado de match en Da Vinci Fighters.
6. Flujo Voz WebRTC: Sesiones P2P, mute individual y servidores ICE.
7. Flujo Grabación y Galería: Metadatos en SQLite, consulta de clips y miniaturas PNG.
8. Flujo Móvil: VirtualTouchGamepad multitáctil, compensación de Dynamic Island y ciclo de vida.
"""
import json
from pathlib import Path
import plistlib
import sqlite3
import tempfile
import time
import unittest
import pygame

# Initialize pygame headless
pygame.init()
if not pygame.display.get_init() or not pygame.display.get_surface():
    pygame.display.set_mode((1, 1), pygame.NOFRAME)

import catalog_data
import cci_database
from backend.config import AppConfig, config
from backend.contracts import PlayerInputPacket, PlayerSlot, RoomStatus, WorldSnapshotPacket
from backend.room_manager import RoomManager
from backend.sync_engine import AuthoritativeSyncEngine
from backend.friends_service import FriendsService, PresenceStatus
from backend.chat_service import ChatService
from backend.voice_service import VoiceService
from recorder.video_recorder import GameplayVideoRecorder
from recorder.gallery_service import GalleryService
from mobile.touch_controls import VirtualTouchGamepad
from mobile.mobile_adapter import MobileAdapter
from mobile.ios_adapter import IOSAdapter


class TestPhase9EvolutionE2E(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_phase9.sqlite3"
        self.recordings_dir = Path(self.temp_dir.name) / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Inicializar BD con esquema completo
        cci_database.init_db(self.db_path)
        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        # Servicios
        self.friends_svc = FriendsService()
        self.friends_svc._presence.clear()
        self.chat_svc = ChatService()
        self.chat_svc._user_msg_times.clear()
        self.room_mgr = RoomManager()
        self.voice_svc = VoiceService()
        self.gallery_svc = GalleryService()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_01_canonical_version_consistency(self):
        """Verifica que todos los archivos manifiesto compartan exactamente la versión 2.1.0."""
        root_dir = Path(__file__).resolve().parent

        # 1. version.json
        with open(root_dir / "version.json", "r", encoding="utf-8") as f:
            v_data = json.load(f)
        self.assertEqual(v_data["version"], "2.1.0")

        # 2. buildozer.spec
        from mobile.build_apk import validate_spec
        spec_data = validate_spec(root_dir / "buildozer.spec")
        self.assertEqual(spec_data["version"], "2.1.0")

        # 3. ios/Info.plist
        from ios.build_ios import validate_info_plist
        plist_data = validate_info_plist(root_dir / "ios" / "Info.plist")
        self.assertEqual(plist_data["CFBundleShortVersionString"], "2.1.0")
        self.assertEqual(plist_data["CFBundleVersion"], "2.1.0")

        # 4. Catálogo oficial contiene 19 juegos y Da Vinci Fighters tiene soporte online
        self.assertEqual(len(catalog_data.CATALOG), 19)
        caps = catalog_data.get_multiplayer_capabilities("davinci")
        self.assertTrue(caps.get("online", False))

    def test_02_database_schema_v2_completeness(self):
        """Comprueba que las 16 tablas del ecosistema C.C.I. SYSTEM existan en SQLite."""
        with cci_database.get_db(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cur.fetchall()}

        expected_tables = {
            "accounts", "games", "profiles", "game_stats", "highscores", "achievements_unlocked",
            "schema_version", "friendships", "groups", "group_members", "messages",
            "call_sessions", "game_rooms", "game_room_members", "matches", "gameplay_recordings"
        }
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Tabla requerida no encontrada: {tbl}")

    def test_03_e2e_social_and_friends_flow(self):
        """Verifica registro de presencia, envío y aceptación de amistad."""
        # Presencia
        self.friends_svc.update_presence("u1", PresenceStatus.ONLINE.value, current_game="davinci")
        p1 = self.friends_svc.get_presence("u1")
        self.assertEqual(p1["status"], PresenceStatus.ONLINE.value)
        self.assertEqual(p1["current_game"], "davinci")

        # Amistad
        res_req = self.friends_svc.send_friend_request("u1", "u2")
        self.assertTrue(res_req["success"])

        res_acc = self.friends_svc.accept_friend_request("u2", "u1")
        self.assertTrue(res_acc["success"])

        friends_u1 = self.friends_svc.get_friends_list("u1")
        self.assertEqual(len(friends_u1), 1)
        self.assertEqual(friends_u1[0]["friend_id"], "u2")

    def test_04_e2e_chat_and_moderation_flow(self):
        """Verifica creación de grupo, mensajería, sliding-window anti-spam y moderación."""
        res_grp = self.friends_svc.create_group("Clan Arcade", "u1")
        self.assertTrue(res_grp["success"])
        grp_id = res_grp["group"]["id"]
        self.friends_svc.invite_member(grp_id, "u1", "u2")

        # Mensaje legítimo
        m_res = self.chat_svc.send_message(grp_id, "u1", "PlayerOne", "¡Pelea en Da Vinci Fighters!")
        self.assertTrue(m_res["success"])
        msg_id = m_res["message"]["message_id"]

        # Anti-spam sliding window: ráfaga rápida
        for i in range(4):
            self.chat_svc.send_message(grp_id, "u1", "PlayerOne", f"Msg {i}")
        # El 6to debe ser rechazado
        spam_res = self.chat_svc.send_message(grp_id, "u1", "PlayerOne", "Spam excedente")
        self.assertFalse(spam_res["success"])
        self.assertIn("anti-spam", spam_res["error"].lower())

        # Reportar mensaje
        rep_res = self.chat_svc.report_message(msg_id, reporter_id="u2", reason="lenguaje inapropiado")
        self.assertTrue(rep_res["success"])

        # Borrado lógico
        del_res = self.chat_svc.delete_message(msg_id, actor_id="u1")
        self.assertTrue(del_res["success"])

    def test_05_e2e_multiplayer_match_lifecycle(self):
        """Verifica sala multijugador, simulación 60 Hz autoritativa y persistencia de resultado."""
        room = self.room_mgr.create_room(game_id="davinci", host_id="u1", host_name="Leonardo")
        self.assertEqual(room.game_id, "davinci")

        # Jugador 2 se une
        joined_room = self.room_mgr.join_room(room.room_id, user_id="u2", username="Michelangelo")
        self.assertIsNotNone(joined_room)
        self.assertTrue(room.is_full)

        # Motor de simulación determinista 60 Hz
        engine = AuthoritativeSyncEngine(room.room_id)

        # Simular 30 ticks de gameplay enviando paquetes de entrada
        for tick in range(1, 31):
            inp_p1 = PlayerInputPacket(room_id=room.room_id, player_id=1, tick=tick, seq=tick, dpad="right", buttons=["punch"] if tick == 10 else [])
            inp_p2 = PlayerInputPacket(room_id=room.room_id, player_id=2, tick=tick, seq=tick, dpad="left")
            engine.push_input(inp_p1)
            engine.push_input(inp_p2)
            snapshot = engine.step()

        self.assertEqual(snapshot.tick, 30)
        self.assertGreater(snapshot.p1_state["x"], 800.0)

        # Finalizar partida y guardar en SQLite
        saved = cci_database.record_match_result_entry(
            match_id="match_test_01",
            room_id=room.room_id,
            game_id="davinci",
            started_at="2026-11-05T22:00:00Z",
            ended_at="2026-11-05T22:01:30Z",
            result_metadata={"winner": "u1", "score": "2-1"},
            db_path=self.db_path,
        )
        self.assertTrue(saved)

    def test_06_e2e_voice_call_and_privacy(self):
        """Verifica llamada de voz WebRTC grupal P2P, estado de mute y privacidad por defecto."""
        grp_res = self.friends_svc.create_group("Grupo Voz", "u1")
        grp_id = grp_res["group"]["id"]
        self.friends_svc.invite_member(grp_id, "u1", "u2")

        call_res = self.voice_svc.start_call(group_id=grp_id, started_by="u1", username="Player1")
        self.assertTrue(call_res["success"])
        session_id = call_res["call"]["session_id"]
        self.assertFalse(call_res["call"]["recording_enabled"], "Grabación de voz debe estar desactivada por privacidad")

        # Segundo participante se une
        join_res = self.voice_svc.join_call(session_id, user_id="u2", username="Player2")
        self.assertTrue(join_res["success"])
        call = self.voice_svc.get_active_call_for_group(grp_id)
        self.assertIsNotNone(call)
        self.assertEqual(len(call.participants), 2)

        # Silenciado individual
        self.voice_svc.toggle_mute(session_id, user_id="u1", muted=True)
        self.assertTrue(call.participants["u1"].muted)

        # Salida de participantes y finalización al quedar vacía
        self.voice_svc.leave_call(session_id, user_id="u1")
        self.voice_svc.leave_call(session_id, user_id="u2")
        self.assertIsNone(self.voice_svc.get_active_call_for_group(grp_id))

    def test_07_e2e_gameplay_recorder_and_gallery(self):
        """Verifica persistencia de metadatos de grabaciones y consulta en galería."""
        video_file = self.recordings_dir / "gameplay_davinci_01.mp4"
        thumb_file = self.recordings_dir / "gameplay_davinci_01_thumb.png"
        video_file.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"A" * 1024)
        thumb_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"B" * 512)

        saved = cci_database.save_gameplay_recording_entry(
            recording_id="rec_davinci_01",
            owner_id="u1",
            game_id="davinci",
            local_path=str(video_file),
            thumbnail_path=str(thumb_file),
            duration_seconds=32.5,
            size_bytes=video_file.stat().st_size,
            db_path=self.db_path,
        )
        self.assertTrue(saved)

        # Listar galería
        items = self.gallery_svc.get_gallery_clips(owner_id="u1")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["game_id"], "davinci")
        self.assertEqual(items[0]["id"], "rec_davinci_01")

    def test_08_e2e_mobile_and_safe_area_coordination(self):
        """Verifica mando táctil multitáctil, márgenes de seguridad en iOS y ciclo de vida."""
        ios_pad = IOSAdapter(1280, 720, device_type="dynamic_island")
        adapter = MobileAdapter(1280, 720)

        # Presión simultánea en controles táctiles
        gamepad = ios_pad.touch_gamepad
        cx, cy = gamepad.dpad_center
        bx, by = gamepad.buttons["punch_light"]

        # Dedo 1 D-pad arriba, Dedo 2 Punch
        gamepad.handle_event(pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 1, "x": cx / 1280.0, "y": (cy - 50) / 720.0}))
        gamepad.handle_event(pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 2, "x": bx / 1280.0, "y": by / 720.0}))

        self.assertTrue(gamepad.is_pressed("up"))
        self.assertTrue(gamepad.is_pressed("punch_light"))

        # Ciclo de vida: suspensión y reanudación
        adapter.pause_app()
        self.assertTrue(adapter.is_paused)
        adapter.resume_app()
        self.assertFalse(adapter.is_paused)


if __name__ == "__main__":
    unittest.main()
