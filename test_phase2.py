"""
test_phase2.py - Suite de pruebas unitarias y de integración para la Fase 2 de C.C.I. SYSTEM:
- Capa de persistencia SQLite (cci_database.py)
- API REST v1 Flask (web/app.py)
- Cliente de sincronización en segundo plano (cci_sync.py)
- Renderizado de interfaz Hall of Fame (web/landing_page.py)
"""
import json
import time
import urllib.request
import unittest
from pathlib import Path

import cci_database
import cci_sync


class TestPhase2Backend(unittest.TestCase):
    _srv = None

    @classmethod
    def setUpClass(cls):
        import socket
        import threading
        from werkzeug.serving import make_server
        from web.app import app as web_app

        # Asegurar inicialización de base de datos
        cci_database.init_db()
        try:
            with socket.create_connection(("127.0.0.1", 5050), timeout=0.5):
                pass
        except OSError:
            cls._srv = make_server("127.0.0.1", 5050, web_app, threaded=True)
            threading.Thread(target=cls._srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        if cls._srv is not None:
            cls._srv.shutdown()
            cls._srv.server_close()
            cls._srv = None

    def test_01_database_seed_and_games(self):
        games = cci_database.get_all_games()
        self.assertGreaterEqual(len(games), 19, "Debe haber al menos 19 juegos oficiales en la BD")
        pacman = cci_database.get_game_by_id("pacman")
        self.assertIsNotNone(pacman)
        self.assertEqual(pacman["id"], "pacman")
        self.assertIn("ARCADE", pacman["categories"])

    def test_02_database_highscores(self):
        scores = cci_database.get_leaderboard(limit=10)
        self.assertGreater(len(scores), 0, "Debe haber puntuaciones precargadas en el salón de la fama")
        
        # Insertar nuevo récord
        rec_id = cci_database.record_highscore(
            game_id="pacman",
            player_name="TEST_HERO",
            score=999999,
            level=99
        )
        self.assertGreater(rec_id, 0)

        top_pacman = cci_database.get_leaderboard(game_id="pacman", limit=5)
        self.assertTrue(any(s["player_name"] == "TEST_HERO" for s in top_pacman))

    def test_03_database_profile_sync(self):
        mock_profile = {
            "id": "piloto_test",
            "player_name": "PILOTO TEST",
            "avatar": 3,
            "total_seconds": 3600,
            "launch_count": 12,
            "game_stats": {
                "davinci": {"seconds": 1800, "launches": 5, "progress": 50, "last_played": "2026-11-03 20:00"},
                "metalslug": {"seconds": 1800, "launches": 7, "progress": 40, "last_played": "2026-11-03 20:30"},
            },
            "claimed_achievements": ["davinci:PRIMER ASALTO", "metalslug:MISIÓN 1"]
        }
        res = cci_database.sync_profile_data(mock_profile)
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], "piloto_test")
        self.assertEqual(res["avatar"], 3)
        self.assertEqual(res["total_seconds"], 3600)
        self.assertEqual(res["level"], 1)
        self.assertEqual(len(res["game_stats"]), 2)
        self.assertEqual(res["total_trophies"], 2)

    def test_04_http_rest_api_health(self):
        req = urllib.request.Request("http://127.0.0.1:5050/api/v1/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "online")
            self.assertIn("SQLite 3", data["engine"])
            self.assertGreaterEqual(data["total_games"], 19)

    def test_05_http_rest_api_games(self):
        req = urllib.request.Request("http://127.0.0.1:5050/api/v1/games")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertGreaterEqual(data["count"], 19)

    def test_06_http_rest_api_leaderboard_submission(self):
        # Post score
        payload = json.dumps({
            "game_id": "tetris",
            "player_name": "REST_PRO",
            "score": 750000,
            "level": 19
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:5050/api/v1/leaderboards",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 201)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertIn("record_id", data)

        # Get score
        req_get = urllib.request.Request("http://127.0.0.1:5050/api/v1/leaderboards/tetris")
        with urllib.request.urlopen(req_get, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(any(s["player_name"] == "REST_PRO" for s in data["leaderboard"]))

    def test_07_web_profiles_and_auth_removed(self):
        # Verificar que /login y /api/v1/profiles no existen en la web
        for path in ["/login", "/dashboard", "/api/v1/profiles", "/api/v1/profiles/sync"]:
            req = urllib.request.Request(f"http://127.0.0.1:5050{path}")
            try:
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    self.assertEqual(resp.status, 404)
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 404, f"Ruta {path} debe retornar 404 Not Found")

    def test_08_local_disk_user_persistence(self):
        from cci_users import UserManager
        um = UserManager.get_instance()
        test_uid = f"local_test_{int(time.time())}"
        created_slug = um.create_user(test_uid, avatar=2)
        self.assertIn(created_slug, um.users)
        user_file = um.users_dir / f"{created_slug}.json"
        self.assertTrue(user_file.exists(), "El usuario debe guardarse exclusivamente en disco local como JSON")
        um.delete_user(created_slug)
        self.assertFalse(user_file.exists(), "El archivo de usuario local debe eliminarse limpiamente")

    def test_09_web_landing_clean_structure(self):
        req = urllib.request.Request("http://127.0.0.1:5050/")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("ARQUITECTURA DE SOFTWARE 100% PYTHON", html)
            self.assertIn("BIBLIOTECA", html)
            self.assertIn("DESCARGA DEL EMULADOR", html)
            self.assertNotIn('id="records"', html, "La sección de records / salón de la fama debe estar eliminada")


if __name__ == "__main__":
    unittest.main()
