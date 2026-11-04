"""
test_audit_remediation.py - Suite de verificación de cumplimiento de la Auditoría C.C.I. SYSTEM:
1. P0: Configuración URL de producción (Render) y variables de entorno.
2. P0: Sistema de Autenticación, Hashing criptográfico y Tokens de Sesión.
3. P0: Validación Anti-Cheat y límites de puntuación en base de datos y API.
4. P1: Dashboard web privado (/dashboard, /login, /register, /logout) y vinculación de perfiles.
5. P1: Navegación y Demostración en video en la sección de Arquitectura.
"""
import json
import os
import unittest
import urllib.parse
import urllib.request
import urllib.error

import cci_database
import cci_sync
import cci_updater
from web.app import app


class TestAuditRemediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cci_database.init_db()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_01_p0_production_api_url_default(self):
        """Verifica que cci_sync y cci_updater apunten por defecto a Render en producción."""
        self.assertEqual(
            cci_sync.DEFAULT_API_URL,
            "https://c-c-i-system.onrender.com",
            "cci_sync debe tener como valor por defecto la URL de producción en Render"
        )
        self.assertEqual(
            cci_updater.DEFAULT_API_URL,
            "https://c-c-i-system.onrender.com",
            "cci_updater debe tener como valor por defecto la URL de producción en Render"
        )

    def test_02_p0_account_crypto_and_persistence(self):
        """Verifica hash seguro de contraseñas y unicidad de emails."""
        unique_email = f"audit_pilot_{os.urandom(4).hex()}@da-vinci.edu"
        acc = cci_database.create_account(unique_email, "AUDIT_PILOT", "ClaveSegura2026!")
        self.assertIsNotNone(acc["id"])
        self.assertEqual(acc["email"], unique_email)
        self.assertEqual(len(acc["token"]), 48)

        # Autenticación exitosa
        auth = cci_database.authenticate_account(unique_email, "ClaveSegura2026!")
        self.assertIsNotNone(auth)
        self.assertEqual(auth["id"], acc["id"])

        # Autenticación errónea
        auth_fail = cci_database.authenticate_account(unique_email, "WrongPassword")
        self.assertIsNone(auth_fail)

        # Token lookup
        by_token = cci_database.get_account_by_token(acc["token"])
        self.assertIsNotNone(by_token)
        self.assertEqual(by_token["id"], acc["id"])

        # Duplicado de email rechazado
        with self.assertRaises(ValueError):
            cci_database.create_account(unique_email, "OTRO", "12345678")

    def test_03_p0_anticheat_score_bounds_validation(self):
        """Verifica que puntuaciones absurdas o nombres inválidos sean rechazados."""
        # Puntuación <= 0
        with self.assertRaises(ValueError):
            cci_database.record_highscore("pacman", "PILOT", score=0)

        # Puntuación astronómica > 99,999,999
        with self.assertRaises(ValueError):
            cci_database.record_highscore("pacman", "CHEATER", score=100000000)

        # Nombre muy corto (< 2 chars)
        with self.assertRaises(ValueError):
            cci_database.record_highscore("pacman", "A", score=1000)

        # Nivel fuera de rango
        with self.assertRaises(ValueError):
            cci_database.record_highscore("pacman", "PILOT", score=1000, level=1000)

        # A través de API REST
        resp = self.client.post("/api/v1/leaderboards", json={
            "game_id": "pacman",
            "player_name": "CHEATER",
            "score": 999999999,
            "level": 1
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json()["status"])

    def test_04_p1_rest_api_auth_endpoints(self):
        """Prueba los endpoints REST /api/v1/auth/register, login, me y dashboard."""
        unique_email = f"api_user_{os.urandom(4).hex()}@arcade.com"
        
        # Registro vía API
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "username": "PILOTO_API",
            "password": "Password123!"
        })
        self.assertEqual(reg_resp.status_code, 201)
        reg_data = reg_resp.get_json()
        token = reg_data["account"]["token"]
        acc_id = reg_data["account"]["id"]

        # Login vía API
        log_resp = self.client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Password123!"
        })
        self.assertEqual(log_resp.status_code, 200)

        # Me con Bearer token
        me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.get_json()["account"]["id"], acc_id)

        # Dashboard con Bearer token
        dash_resp = self.client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn("dashboard", dash_resp.get_json())

    def test_05_p1_profile_linking_and_dashboard_aggregation(self):
        """Verifica que perfiles sincronizados con Bearer token se enlacen a la cuenta y se reflejen en el dashboard."""
        unique_email = f"linked_user_{os.urandom(4).hex()}@arcade.com"
        acc = cci_database.create_account(unique_email, "LINKED_PILOT", "Password123!")
        token = acc["token"]
        prof_id = f"prof_{os.urandom(4).hex()}"

        # Sincronizar perfil con cabecera de autenticación
        sync_resp = self.client.post(
            "/api/v1/profiles/sync",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "id": prof_id,
                "player_name": "LINKED PILOT",
                "avatar": 2,
                "total_seconds": 7200,
                "launch_count": 10,
                "game_stats": {
                    "davinci": {"seconds": 3600, "launches": 5, "progress": 60},
                    "pacman": {"seconds": 3600, "launches": 5, "progress": 40}
                },
                "claimed_achievements": ["davinci:ROUND 1"]
            }
        )
        self.assertEqual(sync_resp.status_code, 200)
        self.assertEqual(sync_resp.get_json()["account_linked"], acc["id"])

        # Insertar récord asociado al perfil
        cci_database.record_highscore("davinci", "LINKED PILOT", score=125000, profile_id=prof_id)

        # Verificar dashboard agregado
        dash = cci_database.get_account_dashboard(acc["id"])
        self.assertIsNotNone(dash)
        self.assertEqual(dash["total_seconds"], 7200)
        self.assertEqual(dash["playtime_formatted"], "2h 00m")
        self.assertEqual(len(dash["profiles"]), 1)
        self.assertEqual(len(dash["game_stats"]), 2)
        self.assertEqual(len(dash["highscores"]), 1)
        self.assertEqual(dash["highscores"][0]["score"], 125000)

    def test_06_p1_web_views_auth_and_session(self):
        """Verifica navegación web por cookies (/login, /register, /dashboard, /logout)."""
        unique_email = f"web_user_{os.urandom(4).hex()}@cci.org"

        # GET /login y /register responden 200 con HTML temático
        resp_login_get = self.client.get("/login")
        self.assertEqual(resp_login_get.status_code, 200)
        self.assertIn("ACCESO AL ECOSISTEMA CLOUD", resp_login_get.data.decode("utf-8"))

        resp_reg_get = self.client.get("/register")
        self.assertEqual(resp_reg_get.status_code, 200)
        self.assertIn("REGISTRO DE PILOTO", resp_reg_get.data.decode("utf-8"))

        # Acceso no autenticado a /dashboard redirige a /login
        resp_dash_unauth = self.client.get("/dashboard")
        self.assertEqual(resp_dash_unauth.status_code, 302)
        self.assertIn("/login", resp_dash_unauth.headers["Location"])

        # POST /register crea cuenta y redirige a /dashboard con cookie
        resp_reg_post = self.client.post("/register", data={
            "email": unique_email,
            "username": "WEB_PILOT",
            "password": "PasswordWeb123!"
        })
        self.assertEqual(resp_reg_post.status_code, 302)
        self.assertIn("/dashboard", resp_reg_post.headers["Location"])

        # GET /dashboard con cookie de sesión activa
        resp_dash_auth = self.client.get("/dashboard")
        self.assertEqual(resp_dash_auth.status_code, 200)
        html = resp_dash_auth.data.decode("utf-8")
        self.assertIn("PANEL DE PILOTO ARCADE", html)
        self.assertIn("TOKEN DE VINCULACIÓN", html)
        self.assertIn("WEB_PILOT", html)

        # GET /logout borra la cookie
        resp_logout = self.client.get("/logout")
        self.assertEqual(resp_logout.status_code, 302)
        self.assertIn("/login", resp_logout.headers["Location"])

    def test_07_p1_landing_page_navigation_and_gameplay_demo(self):
        """Verifica que la landing page incluya enlace a Mi Cuenta y video demo en Arquitectura."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Enlace en la barra HUD
        self.assertIn('href="/dashboard"', html, "Debe tener enlace a /dashboard en el HUD")
        self.assertIn("Mi Cuenta", html, "Debe tener texto 'Mi Cuenta' en el HUD")

        # Demostración en video en Arquitectura
        self.assertIn('id="arquitectura"', html, "Debe existir la sección #arquitectura")
        self.assertIn("/assets/video/CCI_INTRO.mp4", html, "Debe incluir reproductor de video en Arquitectura")
        self.assertIn("DEMO EN VIVO: ORQUESTACIÓN A 60 FPS", html, "Debe incluir título de la demo técnica")
        self.assertIn("PIPELINE DE PROCESAMIENTO DETERMINISTA", html, "Debe incluir diagrama del pipeline")


if __name__ == "__main__":
    unittest.main()
