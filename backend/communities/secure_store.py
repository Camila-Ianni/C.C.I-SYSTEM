"""backend/communities/secure_store.py - Almacenamiento seguro de tokens JWT y OAuth.

Evita persistir tokens sensibles en archivos JSON planos en disco. Selecciona
automáticamente el almacén nativo del sistema operativo:
1. Librería Python `keyring` (si está instalada y activa).
2. macOS Keychain nativo vía `/usr/bin/security` (`login.keychain-db`).
3. Windows DPAPI (`ctypes` `CryptProtectData` / `CryptUnprotectData`).
4. Linux Secret Service (`secret-tool`, libsecret) si hay bus gráfico disponible.
5. Bóveda local cifrada con Encrypt-then-MAC (`SHA256-CTR + HMAC-SHA256`,
   archivo `0600`) como último recurso cuando el entorno carece de llavero de SO
   (p. ej. contenedores Docker headless), nunca JSON en texto plano.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - opcional según entorno
    import keyring as _py_keyring  # type: ignore
except Exception:
    _py_keyring = None

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE = "cci.system.desktop"


def _derive_vault_dir(base_dir: Optional[Path] = None) -> Path:
    if base_dir is not None:
        target = Path(base_dir)
    else:
        env_dir = os.getenv("CCI_SECURE_VAULT_DIR", "").strip()
        if env_dir:
            target = Path(env_dir)
        else:
            target = Path(__file__).resolve().parent.parent.parent / ".cci-user-data" / "vault"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _xor_keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """Genera flujo determinista SHA-256 en modo CTR para cifrar payload en biblioteca estándar."""
    blocks = []
    counter = 0
    produced = 0
    while produced < length:
        ctr_bytes = counter.to_bytes(8, "big")
        block = hmac.new(enc_key, nonce + ctr_bytes, hashlib.sha256).digest()
        blocks.append(block)
        produced += len(block)
        counter += 1
    stream = b"".join(blocks)[:length]
    return stream


def encrypt_blob_authenticated(secret_key: str | bytes, plaintext: bytes) -> str:
    """Cifra bytes con Encrypt-then-MAC (`cci-enc-v1:<base64>`), sin dependencias externas."""
    raw_master = secret_key.encode("utf-8") if isinstance(secret_key, str) else bytes(secret_key)
    enc_key = hmac.new(raw_master, b"cci-enc-key-v1", hashlib.sha256).digest()
    mac_key = hmac.new(raw_master, b"cci-mac-key-v1", hashlib.sha256).digest()
    nonce = os.urandom(16)
    stream = _xor_keystream(enc_key, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
    tag = hmac.new(mac_key, b"v1" + nonce + ciphertext, hashlib.sha256).digest()
    envelope = base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")
    return f"cci-enc-v1:{envelope}"


def decrypt_blob_authenticated(secret_key: str | bytes, token: str) -> bytes:
    """Verifica HMAC-SHA256 en tiempo constante y descifra envelope `cci-enc-v1:...`."""
    if not isinstance(token, str) or not token.startswith("cci-enc-v1:"):
        raise ValueError("Formato de secreto cifrado inválido")
    raw_master = secret_key.encode("utf-8") if isinstance(secret_key, str) else bytes(secret_key)
    enc_key = hmac.new(raw_master, b"cci-enc-key-v1", hashlib.sha256).digest()
    mac_key = hmac.new(raw_master, b"cci-mac-key-v1", hashlib.sha256).digest()

    raw = base64.urlsafe_b64decode(token.split(":", 1)[1].encode("ascii"))
    if len(raw) < 48:
        raise ValueError("Envelope cifrado truncado")
    nonce = raw[:16]
    tag = raw[16:48]
    ciphertext = raw[48:]
    expected_tag = hmac.new(mac_key, b"v1" + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Integridad HMAC inválida o secreto adulterado")
    stream = _xor_keystream(enc_key, nonce, len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, stream))


class SecureTokenStore:
    """Gestor unificado de secretos para tokens JWT de sesión y tokens OAuth (Spotify)."""

    def __init__(
        self,
        service_name: str = _DEFAULT_SERVICE,
        vault_dir: Optional[Path] = None,
        backend: Optional[str] = None,
    ):
        self.service_name = service_name
        self.vault_dir = _derive_vault_dir(vault_dir)
        requested = (backend or os.getenv("CCI_TOKEN_BACKEND", "auto")).strip().lower()
        self.backend_name = self._select_backend(requested)

    def _select_backend(self, requested: str) -> str:
        if requested and requested != "auto":
            return requested
        if _py_keyring is not None:
            try:
                kr_name = type(_py_keyring.get_keyring()).__name__.lower()
                if "fail" not in kr_name and "null" not in kr_name:
                    return "keyring"
            except Exception:
                pass
        if sys.platform == "darwin" and Path("/usr/bin/security").exists():
            return "macos_keychain"
        if sys.platform == "win32":  # pragma: no cover
            return "windows_dpapi"
        if shutil.which("secret-tool") and (os.getenv("DBUS_SESSION_BUS_ADDRESS") or os.getenv("DISPLAY")):
            return "linux_secret_service"
        return "encrypted_vault"

    @staticmethod
    def build_account_key(session_path: Path, kind: str = "jwt") -> str:
        digest = hashlib.sha256(str(Path(session_path).resolve()).encode("utf-8")).hexdigest()[:20]
        return f"cci:{kind}:{digest}"

    # ------------------------------------------------------------------
    # Operaciones públicas
    # ------------------------------------------------------------------

    def set_secret(self, account: str, secret: str) -> str:
        """Guarda un secreto en el backend seguro seleccionado (sin fallback a texto plano)."""
        acct = str(account or "").strip()
        val = str(secret or "")
        if not acct or not val:
            raise ValueError("account y secret son obligatorios")

        if self.backend_name == "keyring" and _py_keyring is not None:
            try:
                _py_keyring.set_password(self.service_name, acct, val)
                return "keyring"
            except Exception as exc:
                logger.warning("keyring set_password failed, falling back to vault: %s", exc)

        if self.backend_name == "macos_keychain":
            if self._macos_set(acct, val):
                return "macos_keychain"

        if self.backend_name == "linux_secret_service":
            if self._linux_set(acct, val):
                return "linux_secret_service"

        if self.backend_name == "windows_dpapi":  # pragma: no cover
            if self._vault_set(acct, val, use_dpapi=True):
                return "windows_dpapi"

        self._vault_set(acct, val, use_dpapi=False)
        return "encrypted_vault"

    def get_secret(self, account: str) -> Optional[str]:
        acct = str(account or "").strip()
        if not acct:
            return None

        if self.backend_name == "keyring" and _py_keyring is not None:
            try:
                val = _py_keyring.get_password(self.service_name, acct)
                if val:
                    return str(val)
            except Exception:
                pass

        if self.backend_name == "macos_keychain":
            val = self._macos_get(acct)
            if val is not None:
                return val

        if self.backend_name == "linux_secret_service":
            val = self._linux_get(acct)
            if val is not None:
                return val

        return self._vault_get(acct)

    def delete_secret(self, account: str) -> bool:
        acct = str(account or "").strip()
        if not acct:
            return False
        removed = False

        if self.backend_name == "keyring" and _py_keyring is not None:
            try:
                _py_keyring.delete_password(self.service_name, acct)
                removed = True
            except Exception:
                pass

        if self.backend_name == "macos_keychain":
            if self._macos_delete(acct):
                removed = True

        if self.backend_name == "linux_secret_service":
            if self._linux_delete(acct):
                removed = True

        if self._vault_delete(acct):
            removed = True
        return removed

    def set_json(self, account: str, payload: Dict[str, Any]) -> str:
        return self.set_secret(account, json.dumps(payload, separators=(",", ":")))

    def get_json(self, account: str) -> Optional[Dict[str, Any]]:
        raw = self.get_secret(account)
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # macOS Keychain (`/usr/bin/security`)
    # ------------------------------------------------------------------

    def _macos_set(self, account: str, secret: str) -> bool:
        try:
            res = subprocess.run(
                [
                    "/usr/bin/security",
                    "add-generic-password",
                    "-U",
                    "-a",
                    account,
                    "-s",
                    self.service_name,
                    "-w",
                    secret,
                ],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _macos_get(self, account: str) -> Optional[str]:
        try:
            res = subprocess.run(
                [
                    "/usr/bin/security",
                    "find-generic-password",
                    "-a",
                    account,
                    "-s",
                    self.service_name,
                    "-w",
                ],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            if res.returncode == 0:
                return res.stdout.rstrip("\r\n")
        except Exception:
            pass
        return None

    def _macos_delete(self, account: str) -> bool:
        try:
            res = subprocess.run(
                [
                    "/usr/bin/security",
                    "delete-generic-password",
                    "-a",
                    account,
                    "-s",
                    self.service_name,
                ],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Linux Secret Service (`secret-tool`)
    # ------------------------------------------------------------------

    def _linux_set(self, account: str, secret: str) -> bool:  # pragma: no cover
        try:
            res = subprocess.run(
                [
                    "secret-tool",
                    "store",
                    "--label",
                    f"{self.service_name}:{account}",
                    "service",
                    self.service_name,
                    "account",
                    account,
                ],
                input=secret,
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _linux_get(self, account: str) -> Optional[str]:  # pragma: no cover
        try:
            res = subprocess.run(
                ["secret-tool", "lookup", "service", self.service_name, "account", account],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout.rstrip("\r\n")
        except Exception:
            pass
        return None

    def _linux_delete(self, account: str) -> bool:  # pragma: no cover
        try:
            res = subprocess.run(
                ["secret-tool", "clear", "service", self.service_name, "account", account],
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Bóveda local cifrada (Encrypt-then-MAC SHA256-CTR + HMAC-SHA256)
    # ------------------------------------------------------------------

    def _vault_master_key(self) -> bytes:
        key_file = self.vault_dir / ".master.key"
        if key_file.exists():
            raw = key_file.read_bytes()
            if len(raw) >= 32:
                return raw[:32]
        new_key = os.urandom(32)
        key_file.write_bytes(new_key)
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        return new_key

    def _vault_file(self) -> Path:
        return self.vault_dir / f"{self.service_name}.vault"

    def _load_vault_map(self) -> Dict[str, str]:
        vf = self._vault_file()
        if not vf.exists():
            return {}
        try:
            content = vf.read_text(encoding="utf-8").strip()
            if not content:
                return {}
            decrypted = decrypt_blob_authenticated(self._vault_master_key(), content)
            parsed = json.loads(decrypted.decode("utf-8"))
            return dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _save_vault_map(self, mapping: Dict[str, str]) -> None:
        vf = self._vault_file()
        raw = json.dumps(mapping, separators=(",", ":")).encode("utf-8")
        encrypted = encrypt_blob_authenticated(self._vault_master_key(), raw)
        vf.write_text(encrypted, encoding="utf-8")
        try:
            os.chmod(vf, 0o600)
        except Exception:
            pass

    def _vault_set(self, account: str, secret: str, use_dpapi: bool = False) -> bool:
        data = secret
        if use_dpapi and sys.platform == "win32":  # pragma: no cover
            data = self._dpapi_protect(secret.encode("utf-8"))
        mapping = self._load_vault_map()
        mapping[account] = data
        self._save_vault_map(mapping)
        return True

    def _vault_get(self, account: str) -> Optional[str]:
        mapping = self._load_vault_map()
        val = mapping.get(account)
        if not val:
            return None
        if sys.platform == "win32" and isinstance(val, str) and val.startswith("dpapi:"):  # pragma: no cover
            try:
                return self._dpapi_unprotect(val).decode("utf-8")
            except Exception:
                return None
        return str(val)

    def _vault_delete(self, account: str) -> bool:
        mapping = self._load_vault_map()
        if account in mapping:
            mapping.pop(account, None)
            self._save_vault_map(mapping)
            return True
        return False

    @staticmethod
    def _dpapi_protect(raw: bytes) -> str:  # pragma: no cover
        import ctypes
        import ctypes.wintypes as wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        in_blob = DATA_BLOB(len(raw), ctypes.create_string_buffer(raw))
        out_blob = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
        ):
            raise OSError("CryptProtectData failed")
        try:
            protected = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return "dpapi:" + base64.b64encode(protected).decode("ascii")
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)

    @staticmethod
    def _dpapi_unprotect(token: str) -> bytes:  # pragma: no cover
        import ctypes
        import ctypes.wintypes as wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        raw = base64.b64decode(token.split(":", 1)[1].encode("ascii"))
        in_blob = DATA_BLOB(len(raw), ctypes.create_string_buffer(raw))
        out_blob = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
        ):
            raise OSError("CryptUnprotectData failed")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
