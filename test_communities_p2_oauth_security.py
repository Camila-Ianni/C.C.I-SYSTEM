"""test_communities_p2_oauth_security.py - Certificación E2E P2: Spotify OAuth PKCE, Keychain y Hardening.

Verifica de punta a punta con backend Flask/Socket.IO real, servidor HTTP local simulando
Spotify OAuth/API, Qt `CommunityExploreView` y almacén seguro de credenciales (`SecureTokenStore`):
1. Almacenamiento seguro de sesión JWT/OAuth: `desktop_session.json` no persiste `"token"` en texto
   plano; el JWT vive en Keychain/keyring (o bóveda autenticada) con migración automática desde v1
   y revocación local + server-side (`/api/v1/auth/logout` + denylist `jti`) al cerrar sesión.
2. Flujo Spotify OAuth 2.0 + PKCE S256 opt-in y revocable:
   - Validación anti-Open-Redirect en `redirect_uri`, `state` anti-CSRF vinculado al usuario y PKCE estricto.
   - Tokens cifrados en reposo en SQLite (`cci-enc-v1:...`) sin exposición en API ni BD en texto plano.
   - Loopback callback real (`127.0.0.1`), refresh automático de access token, presencia `listening` en tiempo
     real para amigos (respetando juego activo y visibilidad), opt-out y revocación total inmediata.
3. Hardening de producción: validación de `CCI_CORS_ORIGINS` / secretos Spotify, cabeceras de seguridad
   HTTP (`nosniff`, `DENY`, HSTS, `Cache-Control: no-store` en auth/integraciones), rechazo JWT `alg=none`,
   rate limiting con `429` + `Retry-After` y manejo JSON sanitizado para HTTP `413`.
"""
from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"
os.environ["CCI_DISABLE_AUDIO_IO"] = "1"
os.environ["CCI_RATE_LIMIT_ENABLED"] = "true"

import requests
from PySide6.QtWidgets import QApplication


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_until(app: QApplication, predicate, timeout: float = 6.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.03)
    app.processEvents()
    return bool(predicate())


class _MockSpotifyState:
    def __init__(self) -> None:
        self.access_token = "sp-access-initial-secret-001"
        self.refresh_token = "sp-refresh-initial-secret-999"
        self.token_version = 1
        self.display_name = "Mimi Beats"
        self.spotify_user_id = "spotify_mimi_42"
        self.is_playing = True
        self.track_name = "Midnight City"
        self.artists = ["M83"]
        self.token_requests: List[Dict[str, Any]] = []


def _start_mock_spotify_server(state: _MockSpotifyState) -> tuple[HTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):  # noqa: N802
            if self.path != "/api/token":
                self._send_json(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8")
            form = {k: v[0] for k, v in parse_qs(body).items()}
            state.token_requests.append(form)
            grant = form.get("grant_type")
            if grant == "authorization_code":
                if not form.get("code") or not form.get("code_verifier"):
                    self._send_json(400, {"error": "invalid_grant"})
                    return
                self._send_json(
                    200,
                    {
                        "access_token": state.access_token,
                        "refresh_token": state.refresh_token,
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "user-read-currently-playing user-read-playback-state",
                    },
                )
                return
            if grant == "refresh_token":
                if form.get("refresh_token") != state.refresh_token:
                    self._send_json(400, {"error": "invalid_refresh"})
                    return
                state.token_version += 1
                state.access_token = f"sp-access-refreshed-{state.token_version}"
                self._send_json(
                    200,
                    {
                        "access_token": state.access_token,
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    },
                )
                return
            self._send_json(400, {"error": "unsupported_grant_type"})

        def do_GET(self):  # noqa: N802
            auth = self.headers.get("Authorization") or ""
            if auth != f"Bearer {state.access_token}":
                self._send_json(401, {"error": {"status": 401, "message": "Invalid access token"}})
                return
            if self.path == "/v1/me":
                self._send_json(200, {"id": state.spotify_user_id, "display_name": state.display_name})
                return
            if self.path == "/v1/me/player/currently-playing":
                if not state.is_playing:
                    self.send_response(204)
                    self.end_headers()
                    return
                self._send_json(
                    200,
                    {
                        "is_playing": True,
                        "item": {
                            "name": state.track_name,
                            "artists": [{"name": a} for a in state.artists],
                        },
                    },
                )
                return
            self._send_json(404, {"error": "not_found"})

        def log_message(self, format, *args):  # noqa: A002
            return

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True, name="CCI-MockSpotify").start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class TestCommunitiesP2OAuthSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p2_sec_")
        cls.tmp_path = Path(cls._tmp_dir.name)

        cls._env_keys = (
            "CCI_DATABASE_PATH",
            "CCI_COMMUNITIES_DB_PATH",
            "CCI_SOUNDS_STORAGE_PATH",
            "CCI_SECURE_VAULT_DIR",
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET",
            "SPOTIFY_AUTHORIZE_URL",
            "SPOTIFY_TOKEN_URL",
            "SPOTIFY_API_BASE",
            "CCI_RATE_LIMIT_LOGIN",
            "CCI_OAUTH_RATE_LIMIT_PER_MIN",
        )
        cls._old_env = {k: os.environ.get(k) for k in cls._env_keys}

        os.environ["CCI_DATABASE_PATH"] = str(cls.tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(cls.tmp_path / "communities.sqlite3")
        os.environ["CCI_SOUNDS_STORAGE_PATH"] = str(cls.tmp_path / "sounds")
        os.environ["CCI_SECURE_VAULT_DIR"] = str(cls.tmp_path / "vault")

        cls.spotify_mock = _MockSpotifyState()
        cls.spotify_srv, cls.spotify_base = _start_mock_spotify_server(cls.spotify_mock)
        os.environ["SPOTIFY_CLIENT_ID"] = "cci-test-spotify-client"
        os.environ["SPOTIFY_CLIENT_SECRET"] = "cci-test-spotify-secret-strong-value"
        os.environ["SPOTIFY_AUTHORIZE_URL"] = f"{cls.spotify_base}/authorize"
        os.environ["SPOTIFY_TOKEN_URL"] = f"{cls.spotify_base}/api/token"
        os.environ["SPOTIFY_API_BASE"] = f"{cls.spotify_base}/v1"

        import cci_database
        from backend.communities.repository import CommunitiesRepository
        from backend.security_hardening import auth_rate_limiter

        auth_rate_limiter.reset()
        cci_database.init_db()
        CommunitiesRepository.reset_instance()

        import backend.server as server_mod

        cls.server_port = _free_port()
        cls.api_url = f"http://127.0.0.1:{cls.server_port}"

        def _serve():
            server_mod.socketio.run(
                server_mod.app,
                host="127.0.0.1",
                port=cls.server_port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        threading.Thread(target=_serve, daemon=True).start()
        deadline = time.time() + 6.0
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", cls.server_port), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        from backend.communities.repository import CommunitiesRepository
        from backend.security_hardening import auth_rate_limiter

        auth_rate_limiter.reset()
        try:
            cls.spotify_srv.shutdown()
            cls.spotify_srv.server_close()
        except Exception:
            pass
        for k, v in cls._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        CommunitiesRepository.reset_instance()
        cls._tmp_dir.cleanup()

    def tearDown(self):
        from backend.security_hardening import auth_rate_limiter

        auth_rate_limiter.reset()

    def test_01_desktop_session_uses_keychain_not_plaintext_and_revokes_on_logout(self):
        from backend.communities.desktop_client import CommunityApiError, CommunityController

        sess_file = self.tmp_path / "alice_session.json"
        ctrl = CommunityController(
            api_url=self.api_url,
            session_path=sess_file,
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
            enable_game_watcher=False,
        )
        try:
            sess = ctrl.register("p2_alice@example.com", "p2_alice", "SuperPass#2026")
            self.assertTrue(sess.token)
            self.assertTrue(_wait_until(self.app, lambda: ctrl.realtime.is_connected(), timeout=5.0))

            # 1) El JSON de sesión en disco NO contiene el token JWT en texto plano.
            raw_text = sess_file.read_text(encoding="utf-8")
            raw_json = json.loads(raw_text)
            self.assertEqual(raw_json.get("version"), 2)
            self.assertNotIn("token", raw_json)
            self.assertNotIn(sess.token, raw_text)
            self.assertTrue(raw_json.get("token_storage"))

            acct_key = ctrl.token_store.build_account_key(sess_file, kind="jwt")
            self.assertEqual(ctrl.token_store.get_secret(acct_key), sess.token)

            # 2) Una nueva instancia restaura la sesión leyendo exclusivamente del store seguro.
            ctrl_reloaded = CommunityController(
                api_url=self.api_url,
                session_path=sess_file,
                heartbeat_interval_ms=0,
                enable_voice_audio_io=False,
                enable_game_watcher=False,
            )
            try:
                restored = ctrl_reloaded.restore_session()
                self.assertIsNotNone(restored)
                assert restored is not None
                self.assertEqual(restored.username.lower(), "p2_alice")
                self.assertEqual(restored.token, sess.token)
            finally:
                ctrl_reloaded.shutdown()

            # 3) Migración automática de sesión legacy v1 con token en JSON plano.
            ctrl.token_store.delete_secret(acct_key)
            sess_file.write_text(
                json.dumps(
                    {
                        "api_url": self.api_url,
                        "token": sess.token,
                        "user_id": sess.user_id,
                        "username": sess.username,
                    }
                ),
                encoding="utf-8",
            )
            migrated = ctrl.restore_session()
            self.assertIsNotNone(migrated)
            migrated_text = sess_file.read_text(encoding="utf-8")
            self.assertNotIn("token", json.loads(migrated_text))
            self.assertNotIn(sess.token, migrated_text)
            self.assertEqual(ctrl.token_store.get_secret(acct_key), sess.token)

            # 4) Logout revoca el JWT en el servidor (denylist jti) y borra Keychain/JSON.
            old_token = sess.token
            ctrl.logout()
            self.assertFalse(sess_file.exists())
            self.assertIsNone(ctrl.token_store.get_secret(acct_key))

            me_resp = requests.get(
                f"{self.api_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {old_token}"},
                timeout=3.0,
            )
            self.assertEqual(me_resp.status_code, 401)
            with self.assertRaises(CommunityApiError):
                ctrl.api.set_token(old_token)
                ctrl.api.get_me()
        finally:
            ctrl.clear_saved_session()
            ctrl.shutdown()

    def test_02_spotify_oauth_pkce_opt_in_sync_and_revocation_e2e(self):
        from backend.communities.desktop_client import CommunityApiError, CommunityController
        from backend.communities.repository import CommunitiesRepository
        from omnidash_qt import CommunityExploreView

        unauth_resp = requests.get(f"{self.api_url}/api/v1/integrations/spotify/status", timeout=3.0)
        self.assertEqual(unauth_resp.status_code, 401)

        alice_ctrl = CommunityController(
            api_url=self.api_url,
            session_path=self.tmp_path / "sp_alice.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
            enable_game_watcher=False,
        )
        bob_ctrl = CommunityController(
            api_url=self.api_url,
            session_path=self.tmp_path / "sp_bob.json",
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
            enable_game_watcher=False,
        )
        explore_view = CommunityExploreView(alice_ctrl)
        try:
            alice_sess = alice_ctrl.register("sp_alice@example.com", "sp_alice", "Pass#Spotify1")
            bob_sess = bob_ctrl.register("sp_bob@example.com", "sp_bob", "Pass#Spotify2")
            self.assertTrue(_wait_until(self.app, lambda: alice_ctrl.realtime.is_connected() and bob_ctrl.realtime.is_connected()))

            alice_ctrl.send_friend_request("sp_bob")
            bob_ctrl.respond_friend_request(alice_sess.user_id, accept=True)
            bob_ctrl.refresh_friends()

            # Validación anti-Open-Redirect
            with self.assertRaises(CommunityApiError) as redirect_err:
                alice_ctrl.start_spotify_oauth_flow(redirect_uri="https://evil.attacker.example/cb")
            self.assertEqual(redirect_err.exception.status_code, 400)

            # Verificar rechazo de PKCE / state cruzado / replay antes del intercambio real
            tamper_start = alice_ctrl.start_spotify_oauth_flow(redirect_uri="http://127.0.0.1:43899/callback")
            # Usuario distinto intentando usar state de alice -> 403
            with self.assertRaises(CommunityApiError) as cross_err:
                bob_ctrl.api.exchange_spotify_oauth(
                    state=tamper_start["state"],
                    code="fake-code",
                    code_verifier="wrong-verifier",
                )
            self.assertEqual(cross_err.exception.status_code, 403)

            # Sin code_verifier cuando hubo code_challenge -> 403 PKCE_REQUIRED
            with self.assertRaises(CommunityApiError) as missing_pkce:
                alice_ctrl.api.exchange_spotify_oauth(
                    state=tamper_start["state"],
                    code="fake-code",
                    code_verifier="",
                )
            self.assertEqual(missing_pkce.exception.status_code, 403)

            # Flujo real completo usando callback loopback local sin navegador interactivo
            # Disparamos un GET automático al redirect_uri en cuanto start_oauth quede escuchando.
            self.spotify_mock.is_playing = True
            self.spotify_mock.track_name = "Resonance"
            self.spotify_mock.artists = ["HOME"]

            loopback_result: Dict[str, Any] = {}
            loopback_err: List[BaseException] = []
            orig_start = alice_ctrl.start_spotify_oauth_flow

            def _wrapped_start(redirect_uri: str = "http://127.0.0.1:43821/callback", share_presence: bool = True):
                res = orig_start(redirect_uri=redirect_uri, share_presence=share_presence)

                def _simulate_browser_redirect():
                    time.sleep(0.05)
                    cb_url = f"{redirect_uri}?code=auth-code-real-01&state={res['state']}"
                    requests.get(cb_url, timeout=3.0)

                threading.Thread(target=_simulate_browser_redirect, daemon=True).start()
                return res

            alice_ctrl.start_spotify_oauth_flow = _wrapped_start  # type: ignore[method-assign]
            try:
                t = threading.Thread(
                    target=lambda: loopback_result.update(
                        alice_ctrl.connect_spotify_via_loopback(share_presence=True, timeout_sec=8.0, open_browser=False)
                    ),
                    daemon=True,
                )
                t.start()
                t.join(timeout=8.0)
            except BaseException as exc:  # pragma: no cover
                loopback_err.append(exc)
            finally:
                alice_ctrl.start_spotify_oauth_flow = orig_start  # type: ignore[method-assign]

            self.assertFalse(loopback_err)
            self.assertTrue(loopback_result.get("connected"))
            self.assertTrue(loopback_result.get("opt_in_enabled"))
            self.assertEqual(loopback_result.get("display_name"), "Mimi Beats")

            # Tokens almacenados en SQLite deben estar cifrados (`cci-enc-v1:...`) y nunca en texto plano
            repo = CommunitiesRepository.get_instance()
            row = repo.get_spotify_connection(alice_sess.user_id)
            self.assertIsNotNone(row)
            assert row is not None
            cipher = str(row.get("token_ciphertext") or "")
            self.assertTrue(cipher.startswith("cci-enc-v1:"))
            self.assertNotIn(self.spotify_mock.access_token, cipher)
            self.assertNotIn(self.spotify_mock.refresh_token, cipher)

            # Sync de reproducción actualiza track + presencia de amigos + botón Qt
            synced = alice_ctrl.sync_spotify_playback()
            self.assertEqual(synced.get("current_track"), "Resonance")
            self.assertEqual(synced.get("current_artist"), "HOME")
            self.assertTrue(
                _wait_until(
                    self.app,
                    lambda: any(
                        str(f.get("username") or "").lower() == "sp_alice"
                        and str(f.get("activity_type") or "") == "listening"
                        and "Resonance" in str(f.get("activity_title") or "")
                        for f in bob_ctrl.active_friends
                    ),
                    timeout=5.0,
                )
            )
            self.app.processEvents()
            self.assertIn("Resonance", explore_view.spotify_btn.text())

            # Si expira el access_token en BD, el siguiente sync hace refresh_token OAuth automáticamente
            repo.update_spotify_connection_state(alice_sess.user_id, expires_at=time.time() - 60.0)
            self.spotify_mock.track_name = "Digital Love"
            self.spotify_mock.artists = ["Daft Punk"]
            refreshed_sync = alice_ctrl.sync_spotify_playback()
            self.assertEqual(refreshed_sync.get("current_track"), "Digital Love")
            self.assertTrue(
                any(req.get("grant_type") == "refresh_token" for req in self.spotify_mock.token_requests)
            )

            # Opt-out limpia presencia listening y bloquea futuros sync
            opted_out = alice_ctrl.set_spotify_preferences(opt_in_enabled=False, share_presence=False)
            self.assertFalse(opted_out.get("opt_in_enabled"))
            with self.assertRaises(CommunityApiError) as optout_err:
                alice_ctrl.sync_spotify_playback()
            self.assertEqual(optout_err.exception.status_code, 403)

            # Revocación total destruye ciphertext en SQLite y limpia presencia + UI
            revoked = alice_ctrl.revoke_spotify_connection()
            self.assertFalse(revoked.get("connected"))
            row_after = repo.get_spotify_connection(alice_sess.user_id)
            self.assertIsNotNone(row_after)
            assert row_after is not None
            self.assertIsNone(row_after.get("token_ciphertext"))
            self.assertIsNotNone(row_after.get("revoked_at"))
            self.app.processEvents()
            self.assertIn("Conectar Spotify", explore_view.spotify_btn.text())
        finally:
            explore_view.deleteLater()
            alice_ctrl.clear_saved_session()
            bob_ctrl.clear_saved_session()
            alice_ctrl.shutdown()
            bob_ctrl.shutdown()

    def test_03_production_hardening_headers_jwt_limits_and_rate_limit(self):
        from backend.auth import create_access_token, verify_access_token
        from backend.config import AppConfig
        from backend.security_hardening import auth_rate_limiter
        import backend.server as server_mod

        # 1) Validación estricta de secretos en producción (CORS '*' y Spotify placeholder prohibidos)
        env_backup = {
            k: os.environ.get(k)
            for k in (
                "CCI_ENV",
                "CCI_SECRET_KEY",
                "LIVEKIT_API_KEY",
                "LIVEKIT_API_SECRET",
                "TURN_SECRET",
                "CCI_CORS_ORIGINS",
                "SPOTIFY_CLIENT_SECRET",
            )
        }
        try:
            os.environ["CCI_ENV"] = "production"
            os.environ["CCI_SECRET_KEY"] = "prod-secret-0123456789abcdef0123456789"
            os.environ["LIVEKIT_API_KEY"] = "lk-prod-key-01"
            os.environ["LIVEKIT_API_SECRET"] = "lk-prod-secret-strong-0123456789abcdef"
            os.environ["TURN_SECRET"] = "turn-prod-secret-strong-0123456789abcdef"
            os.environ["CCI_CORS_ORIGINS"] = "*"
            os.environ["SPOTIFY_CLIENT_SECRET"] = "valid-spotify-secret-value"
            with self.assertRaises(RuntimeError):
                AppConfig.from_env().validate_production_secrets("production")

            os.environ["CCI_CORS_ORIGINS"] = "https://app.ccisystem.org"
            os.environ["SPOTIFY_CLIENT_SECRET"] = "replace-with-spotify-client-secret"
            with self.assertRaises(RuntimeError):
                AppConfig.from_env().validate_production_secrets("production")

            os.environ["SPOTIFY_CLIENT_SECRET"] = "real-prod-spotify-secret-xyz123"
            AppConfig.from_env().validate_production_secrets("production")
        finally:
            for k, v in env_backup.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        # 2) Rechazo de JWT falsificado con `alg=none` y verificación de token válido con `jti`
        fake_header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        fake_payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "1", "user_id": "1", "username": "attacker", "exp": int(time.time()) + 3600}).encode()
        ).decode().rstrip("=")
        self.assertIsNone(verify_access_token(f"{fake_header}.{fake_payload}."))
        genuine_tok = create_access_token("99", "hardening_user")
        decoded = verify_access_token(genuine_tok)
        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertTrue(decoded.get("jti"))

        # 3) Cabeceras de seguridad HTTP + `Cache-Control: no-store` en rutas auth/integraciones + HSTS con ProxyFix
        resp = requests.get(
            f"{self.api_url}/api/v1/integrations/spotify/status",
            headers={"Authorization": f"Bearer {genuine_tok}", "X-Forwarded-Proto": "https"},
            timeout=3.0,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(resp.headers.get("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))
        self.assertIn("max-age=", resp.headers.get("Strict-Transport-Security", ""))

        # 4) Rate limiting con HTTP 429 y Retry-After
        auth_rate_limiter.reset()
        old_limit = os.environ.get("CCI_RATE_LIMIT_LOGIN")
        os.environ["CCI_RATE_LIMIT_LOGIN"] = "3"
        try:
            statuses = []
            last_headers = {}
            for _ in range(4):
                r = requests.post(
                    f"{self.api_url}/api/v1/auth/token",
                    json={"identifier": "nonexistent_rate_limit", "password": "bad"},
                    timeout=3.0,
                )
                statuses.append(r.status_code)
                last_headers = dict(r.headers)
            self.assertEqual(statuses[-1], 429)
            self.assertTrue(int(last_headers.get("Retry-After", "0")) >= 1)
        finally:
            if old_limit is None:
                os.environ.pop("CCI_RATE_LIMIT_LOGIN", None)
            else:
                os.environ["CCI_RATE_LIMIT_LOGIN"] = old_limit
            auth_rate_limiter.reset()

        # 5) Handler sanitizado 413 cuando excede MAX_CONTENT_LENGTH
        old_max = server_mod.app.config.get("MAX_CONTENT_LENGTH")
        server_mod.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            big_resp = requests.post(
                f"{self.api_url}/api/v1/auth/token",
                json={"identifier": "u" * 512, "password": "p" * 512},
                timeout=3.0,
            )
            self.assertEqual(big_resp.status_code, 413)
            self.assertIn("error", big_resp.json())
            self.assertNotIn("Traceback", big_resp.text)
        finally:
            server_mod.app.config["MAX_CONTENT_LENGTH"] = old_max


if __name__ == "__main__":
    unittest.main()
