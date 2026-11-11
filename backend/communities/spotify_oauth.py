"""backend/communities/spotify_oauth.py - Flujo Spotify OAuth 2.0 PKCE opt-in y revocable.

Características de seguridad y privacidad:
1. Consentimiento opt-in explícito y revocable en cualquier momento.
2. Flujo Authorization Code + PKCE (S256) y `state` criptográfico de un solo uso
   vinculado estrictamente al `user_id` autenticado (anti-CSRF y anti-replay).
3. Validación estricta de `redirect_uri` (solo loopback local con puerto o HTTPS autorizado).
4. Los `access_token` y `refresh_token` nunca se guardan en texto plano ni se retornan
   al frontend tras el intercambio: se cifran en SQLite con Encrypt-then-MAC derivado
   de `config.secret_key` (`cci-enc-v1:...`).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from backend.communities.repository import CommunitiesRepository
from backend.communities.secure_store import decrypt_blob_authenticated, encrypt_blob_authenticated
from backend.config import config
from backend.security_hardening import validate_oauth_redirect_uri

DEFAULT_SPOTIFY_SCOPES = "user-read-currently-playing user-read-playback-state"


def generate_pkce_pair() -> tuple[str, str]:
    """Genera `(code_verifier, code_challenge_s256)` conforme a RFC 7636."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def derive_pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class SpotifyOAuthError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, code: str = "SPOTIFY_OAUTH_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class SpotifyOAuthService:
    """Servicio desacoplado de Spotify OAuth opt-in, cifrado y revocable."""

    def __init__(self, repo: CommunitiesRepository):
        self.repo = repo

    @staticmethod
    def _client_id() -> str:
        return (os.getenv("SPOTIFY_CLIENT_ID") or config.spotify_client_id or "").strip()

    @staticmethod
    def _client_secret() -> str:
        return (os.getenv("SPOTIFY_CLIENT_SECRET") or config.spotify_client_secret or "").strip()

    @staticmethod
    def _authorize_url() -> str:
        return os.getenv("SPOTIFY_AUTHORIZE_URL", "https://accounts.spotify.com/authorize").strip()

    @staticmethod
    def _token_url() -> str:
        return os.getenv("SPOTIFY_TOKEN_URL", "https://accounts.spotify.com/api/token").strip()

    @staticmethod
    def _api_base() -> str:
        return os.getenv("SPOTIFY_API_BASE", "https://api.spotify.com/v1").strip().rstrip("/")

    @staticmethod
    def _encryption_secret() -> str:
        return (os.getenv("CCI_SECRET_KEY") or config.secret_key).strip()

    def _sanitize_status(self, row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        cid = self._client_id()
        if not row or not row.get("token_ciphertext"):
            return {
                "configured": bool(cid),
                "connected": False,
                "opt_in_enabled": False,
                "share_presence": False,
                "spotify_user_id": None,
                "display_name": None,
                "scopes": "",
                "current_track": None,
                "current_artist": None,
                "token_expires_at": None,
                "connected_at": row.get("connected_at") if row else None,
                "revoked_at": row.get("revoked_at") if row else None,
            }
        return {
            "configured": bool(cid),
            "connected": True,
            "opt_in_enabled": bool(row.get("opt_in_enabled")),
            "share_presence": bool(row.get("share_presence")),
            "spotify_user_id": row.get("spotify_user_id"),
            "display_name": row.get("display_name"),
            "scopes": row.get("scopes") or "",
            "current_track": row.get("current_track"),
            "current_artist": row.get("current_artist"),
            "token_expires_at": row.get("expires_at"),
            "connected_at": row.get("connected_at"),
            "revoked_at": row.get("revoked_at"),
        }

    def get_status(self, user_id: str) -> Dict[str, Any]:
        row = self.repo.get_spotify_connection(user_id)
        return self._sanitize_status(row)

    def start_oauth(
        self,
        user_id: str,
        redirect_uri: Optional[str] = None,
        code_challenge: Optional[str] = None,
        share_presence: bool = True,
        scopes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inicia flujo Spotify OAuth 2.0 con PKCE S256 y `state` CSRF de un solo uso."""
        client_id = self._client_id()
        if not client_id:
            raise SpotifyOAuthError(
                "Spotify OAuth no configurado en el servidor (falta SPOTIFY_CLIENT_ID).",
                status_code=503,
                code="SPOTIFY_NOT_CONFIGURED",
            )

        raw_redirect = (
            str(redirect_uri or "").strip()
            or os.getenv("SPOTIFY_REDIRECT_URI", "").strip()
            or config.spotify_redirect_uri
        )
        try:
            clean_redirect = validate_oauth_redirect_uri(raw_redirect)
        except ValueError as exc:
            raise SpotifyOAuthError(str(exc), status_code=400, code="INVALID_REDIRECT_URI") from exc

        clean_scopes = str(scopes or DEFAULT_SPOTIFY_SCOPES).strip() or DEFAULT_SPOTIFY_SCOPES
        generated_verifier = None
        challenge = str(code_challenge or "").strip()
        if not challenge:
            generated_verifier, challenge = generate_pkce_pair()

        state = secrets.token_urlsafe(24)
        state_rec = self.repo.create_spotify_oauth_state(
            state=state,
            user_id=user_id,
            redirect_uri=clean_redirect,
            scopes=clean_scopes,
            share_presence=bool(share_presence),
            code_challenge=challenge,
            ttl_seconds=600.0,
        )
        query = urlencode({
            "response_type": "code",
            "client_id": client_id,
            "scope": clean_scopes,
            "redirect_uri": clean_redirect,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "show_dialog": "true",
        })
        auth_url = f"{self._authorize_url()}?{query}"
        res = {
            "authorize_url": auth_url,
            "state": state,
            "redirect_uri": clean_redirect,
            "scopes": clean_scopes,
            "expires_at": state_rec["expires_at"],
            "code_challenge": challenge,
        }
        if generated_verifier:
            res["code_verifier"] = generated_verifier
        return res

    def _request_spotify_token(self, form_data: Dict[str, str]) -> Dict[str, Any]:
        resp = requests.post(
            self._token_url(),
            data=form_data,
            headers={"Accept": "application/json"},
            timeout=6.0,
        )
        if resp.status_code >= 400:
            raise SpotifyOAuthError(
                f"Spotify OAuth rechazó el intercambio de token (HTTP {resp.status_code}).",
                status_code=502 if resp.status_code >= 500 else 400,
                code="SPOTIFY_TOKEN_EXCHANGE_FAILED",
            )
        parsed = resp.json()
        if not isinstance(parsed, dict) or not parsed.get("access_token"):
            raise SpotifyOAuthError("Respuesta inválida de Spotify OAuth sin access_token.", status_code=502)
        return parsed

    def _encrypt_tokens(self, tokens: Dict[str, Any]) -> str:
        raw = json.dumps(tokens, separators=(",", ":")).encode("utf-8")
        return encrypt_blob_authenticated(self._encryption_secret(), raw)

    def _decrypt_tokens(self, ciphertext: str) -> Dict[str, Any]:
        raw = decrypt_blob_authenticated(self._encryption_secret(), ciphertext)
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict) or not parsed.get("access_token"):
            raise SpotifyOAuthError("Token OAuth cifrado inválido.", status_code=401)
        return parsed

    def complete_oauth(
        self,
        user_id: str,
        state: str,
        code: str,
        code_verifier: Optional[str] = None,
        share_presence: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Valida `state` anti-CSRF vinculado al `user_id`, verifica PKCE e intercambia el código."""
        clean_state = str(state or "").strip()
        clean_code = str(code or "").strip()
        if not clean_state or not clean_code:
            raise SpotifyOAuthError("state y code son obligatorios.", status_code=400, code="INVALID_OAUTH_CALLBACK")

        state_rec = self.repo.consume_spotify_oauth_state(clean_state, user_id=user_id)
        if not state_rec:
            raise SpotifyOAuthError(
                "Estado OAuth inválido, expirado, ya consumido o perteneciente a otro usuario.",
                status_code=403,
                code="INVALID_OAUTH_STATE",
            )

        expected_challenge = str(state_rec.get("code_challenge") or "").strip()
        verifier = str(code_verifier or "").strip()
        if expected_challenge:
            if not verifier:
                raise SpotifyOAuthError("PKCE code_verifier obligatorio.", status_code=403, code="PKCE_REQUIRED")
            if derive_pkce_challenge(verifier) != expected_challenge:
                raise SpotifyOAuthError("PKCE code_verifier inválido.", status_code=403, code="PKCE_MISMATCH")

        client_id = self._client_id()
        if not client_id:
            raise SpotifyOAuthError("SPOTIFY_CLIENT_ID no configurado.", status_code=503, code="SPOTIFY_NOT_CONFIGURED")

        form: Dict[str, str] = {
            "grant_type": "authorization_code",
            "code": clean_code,
            "redirect_uri": str(state_rec["redirect_uri"]),
            "client_id": client_id,
        }
        if verifier:
            form["code_verifier"] = verifier
        client_secret = self._client_secret()
        if client_secret:
            form["client_secret"] = client_secret

        tok_data = self._request_spotify_token(form)
        expires_in = max(60, int(tok_data.get("expires_in") or 3600))
        expires_at = time.time() + float(expires_in)

        # Obtener perfil básico /me con el token recién emitido
        spotify_uid: Optional[str] = None
        display_name: Optional[str] = None
        try:
            me_resp = requests.get(
                f"{self._api_base()}/me",
                headers={"Authorization": f"Bearer {tok_data['access_token']}"},
                timeout=5.0,
            )
            if me_resp.status_code == 200:
                me_json = me_resp.json()
                spotify_uid = str(me_json.get("id") or "").strip() or None
                display_name = str(me_json.get("display_name") or spotify_uid or "").strip() or None
        except Exception:
            pass

        encrypted = self._encrypt_tokens({
            "access_token": tok_data["access_token"],
            "refresh_token": tok_data.get("refresh_token"),
            "token_type": tok_data.get("token_type", "Bearer"),
            "scope": tok_data.get("scope", state_rec["scopes"]),
        })
        effective_share = state_rec["share_presence"] if share_presence is None else bool(share_presence)
        saved = self.repo.upsert_spotify_connection(
            user_id=user_id,
            spotify_user_id=spotify_uid,
            display_name=display_name,
            scopes=str(tok_data.get("scope") or state_rec["scopes"]),
            token_ciphertext=encrypted,
            expires_at=expires_at,
            opt_in_enabled=True,
            share_presence=effective_share,
        )
        return self._sanitize_status(saved)

    def _clear_listening_presence(self, user_id: str) -> Optional[Dict[str, Any]]:
        prev = self.repo.get_presence(user_id)
        if prev.get("activity_type") != "listening":
            return None
        cur_status = prev.get("status") if prev.get("status") in ("online", "idle", "dnd", "invisible") else "online"
        return self.repo.set_presence(
            user_id=user_id,
            status=cur_status,
            custom_status=None,
            activity_type=None,
            activity_title=None,
            activity_game_id=None,
            activity_started_at=None,
            preserve_activity=False,
        )

    def update_preferences(
        self,
        user_id: str,
        opt_in_enabled: Optional[bool] = None,
        share_presence: Optional[bool] = None,
    ) -> Dict[str, Any]:
        conn = self.repo.get_spotify_connection(user_id)
        if not conn or not conn.get("token_ciphertext"):
            raise SpotifyOAuthError("Spotify no está conectado.", status_code=403, code="SPOTIFY_NOT_CONNECTED")
        updated = self.repo.update_spotify_connection_state(
            user_id=user_id,
            opt_in_enabled=opt_in_enabled,
            share_presence=share_presence,
        )
        cleared_presence = None
        if updated and (not updated["opt_in_enabled"] or not updated["share_presence"]):
            cleared_presence = self._clear_listening_presence(user_id)
        return {
            "spotify": self._sanitize_status(updated),
            "presence_updated": cleared_presence,
        }

    def sync_playback(self, user_id: str) -> Dict[str, Any]:
        """Consulta el track actual de Spotify si el usuario dio consentimiento opt-in."""
        conn = self.repo.get_spotify_connection(user_id)
        if not conn or not conn.get("token_ciphertext"):
            raise SpotifyOAuthError("Spotify no conectado o revocado.", status_code=403, code="SPOTIFY_NOT_CONNECTED")
        if not conn.get("opt_in_enabled"):
            raise SpotifyOAuthError("Integración Spotify pausada (opt-in desactivado).", status_code=403, code="SPOTIFY_OPT_OUT")

        tokens = self._decrypt_tokens(str(conn["token_ciphertext"]))
        now = time.time()
        if conn.get("expires_at") and float(conn["expires_at"]) <= now + 30.0:
            refresh_tok = tokens.get("refresh_token")
            client_id = self._client_id()
            if refresh_tok and client_id:
                form: Dict[str, str] = {
                    "grant_type": "refresh_token",
                    "refresh_token": str(refresh_tok),
                    "client_id": client_id,
                }
                if self._client_secret():
                    form["client_secret"] = self._client_secret()
                refreshed = self._request_spotify_token(form)
                tokens["access_token"] = refreshed["access_token"]
                if refreshed.get("refresh_token"):
                    tokens["refresh_token"] = refreshed["refresh_token"]
                new_exp = now + float(max(60, int(refreshed.get("expires_in") or 3600)))
                self.repo.update_spotify_connection_state(
                    user_id=user_id,
                    token_ciphertext=self._encrypt_tokens(tokens),
                    expires_at=new_exp,
                )

        pb_resp = requests.get(
            f"{self._api_base()}/me/player/currently-playing",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=5.0,
        )
        if pb_resp.status_code == 401:
            raise SpotifyOAuthError("Token de Spotify expirado o revocado externamente.", status_code=401, code="SPOTIFY_TOKEN_EXPIRED")

        track_name: Optional[str] = None
        artist_name: Optional[str] = None
        is_playing = False

        if pb_resp.status_code == 200:
            pb_data = pb_resp.json() or {}
            is_playing = bool(pb_data.get("is_playing"))
            item = pb_data.get("item")
            if is_playing and isinstance(item, dict):
                track_name = str(item.get("name") or "").strip() or None
                artists = [
                    str(a.get("name") or "").strip()
                    for a in (item.get("artists") or [])
                    if isinstance(a, dict) and a.get("name")
                ]
                artist_name = ", ".join(artists) if artists else None

        updated_conn = self.repo.update_spotify_connection_state(
            user_id=user_id,
            current_track=track_name if is_playing else None,
            current_artist=artist_name if is_playing else None,
        )

        presence_updated = None
        prev_pres = self.repo.get_presence(user_id)
        cur_status = prev_pres.get("status") if prev_pres.get("status") in ("online", "idle", "dnd", "invisible") else "online"
        vis = prev_pres.get("activity_visibility") or "communities"
        playing_game = prev_pres.get("activity_type") == "playing"

        if is_playing and track_name and updated_conn and updated_conn.get("share_presence") and not playing_game:
            formatted = f"{track_name} — {artist_name}" if artist_name else track_name
            show_text = (vis != "private" and cur_status != "invisible")
            presence_updated = self.repo.set_presence(
                user_id=user_id,
                status=cur_status,
                custom_status=f"Escuchando: {formatted}" if show_text else None,
                activity_type="listening",
                activity_title=formatted,
                activity_game_id=None,
                activity_started_at=now,
                activity_visibility=vis,
                preserve_activity=False,
            )
        elif not is_playing and prev_pres.get("activity_type") == "listening":
            presence_updated = self._clear_listening_presence(user_id)

        return {
            "spotify": self._sanitize_status(updated_conn),
            "is_playing": bool(is_playing and track_name),
            "presence_updated": presence_updated,
        }

    def revoke(self, user_id: str) -> Dict[str, Any]:
        """Revoca el enlace Spotify, elimina los tokens cifrados y limpia presencia musical."""
        row = self.repo.revoke_spotify_connection(user_id)
        cleared_presence = self._clear_listening_presence(user_id)
        return {
            "spotify": self._sanitize_status(row),
            "revoked": True,
            "presence_updated": cleared_presence,
        }
