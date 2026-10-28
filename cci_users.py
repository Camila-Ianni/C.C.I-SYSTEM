"""
cci_users.py - Gestor multiusuario para C.C.I. System.
Maneja múltiples perfiles de usuario independientes (estadísticas, logros, favoritos, configuración).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from cci_console import DATA_DIR, DATA_FILE, UserData, _deep_default

USERS_DIR = DATA_DIR / "users"
ACTIVE_USER_FILE = DATA_DIR / "active_user.json"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug or "usuario"


class UserManager:
    """Administra múltiples perfiles de usuario independientes."""
    _instance: Optional[UserManager] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, users_dir: Path = USERS_DIR):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.users_dir = users_dir
        self.users: Dict[str, UserData] = {}
        self.active_user_id: str = "cami"
        self._setup_storage()
        self.load_users()

    def _setup_storage(self):
        self.users_dir.mkdir(parents=True, exist_ok=True)
        # Migración de perfil previo si existe system.json y users/ está vacío
        existing_profiles = list(self.users_dir.glob("*.json"))
        if not existing_profiles and DATA_FILE.exists():
            try:
                raw_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                if isinstance(raw_data, dict):
                    # Asignar a usuario principal CAMI manteniendo todo su progreso previo
                    raw_data["player_name"] = "CAMI"
                    cami_path = self.users_dir / "cami.json"
                    cami_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"[UserManager] Perfil migrado con éxito a {cami_path}")
            except Exception as exc:
                print(f"[UserManager] Error en migración de perfil base: {exc}")

        # Si aún no hay usuarios, crear el usuario predeterminado CAMI
        if not list(self.users_dir.glob("*.json")):
            self.create_user("CAMI", avatar=0)

    def load_users(self):
        self.users.clear()
        for p in sorted(self.users_dir.glob("*.json")):
            uid = p.stem
            try:
                ud = UserData(path=p)
                self.users[uid] = ud
            except Exception as exc:
                print(f"[UserManager] No se pudo cargar perfil {p.name}: {exc}")

        # Cargar último usuario activo recordado
        saved_active = None
        if ACTIVE_USER_FILE.exists():
            try:
                data = json.loads(ACTIVE_USER_FILE.read_text(encoding="utf-8"))
                saved_active = data.get("active_user")
            except Exception:
                pass

        if saved_active and saved_active in self.users:
            self.active_user_id = saved_active
        elif "cami" in self.users:
            self.active_user_id = "cami"
        elif self.users:
            self.active_user_id = next(iter(self.users.keys()))
        else:
            self.create_user("CAMI", avatar=0)
            self.active_user_id = "cami"

    def save_active_user_id(self):
        try:
            ACTIVE_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
            ACTIVE_USER_FILE.write_text(
                json.dumps({"active_user": self.active_user_id}, indent=2),
                encoding="utf-8"
            )
        except OSError as exc:
            print(f"[UserManager] No se pudo guardar active_user: {exc}")

    @property
    def active_user(self) -> UserData:
        if self.active_user_id not in self.users:
            if self.users:
                self.active_user_id = next(iter(self.users.keys()))
            else:
                self.create_user("CAMI", avatar=0)
        return self.users[self.active_user_id]

    def select_user(self, user_id: str) -> Optional[UserData]:
        if user_id in self.users:
            self.active_user_id = user_id
            self.save_active_user_id()
            return self.users[user_id]
        return None

    def create_user(self, name: str, avatar: int = 0) -> str:
        clean_name = name.strip() or "JUGADOR"
        base_slug = _slugify(clean_name)
        slug = base_slug
        counter = 2
        while (self.users_dir / f"{slug}.json").exists():
            slug = f"{base_slug}_{counter}"
            counter += 1

        user_path = self.users_dir / f"{slug}.json"
        new_ud = UserData(path=user_path)
        new_ud.data["player_name"] = clean_name.upper()
        new_ud.data["avatar"] = int(avatar) % 8
        new_ud.data["total_seconds"] = 0
        new_ud.data["launch_count"] = 0
        new_ud.data["last_session"] = ""
        new_ud.data["history"] = []
        new_ud.data["favorites"] = []
        new_ud.data["game_stats"] = {}
        new_ud.save()

        self.users[slug] = new_ud
        self.active_user_id = slug
        self.save_active_user_id()
        print(f"[UserManager] Nuevo usuario creado: {clean_name} (id={slug}, avatar={avatar})")
        return slug

    def delete_user(self, user_id: str) -> bool:
        if len(self.users) <= 1:
            print("[UserManager] No se puede eliminar el único usuario restante.")
            return False
        if user_id not in self.users:
            return False

        ud = self.users.pop(user_id)
        try:
            if ud.path.exists():
                ud.path.unlink()
        except OSError as exc:
            print(f"[UserManager] Error al borrar archivo {ud.path}: {exc}")

        if self.active_user_id == user_id:
            self.active_user_id = next(iter(self.users.keys()))
            self.save_active_user_id()
        return True

    def get_users_list(self) -> List[dict]:
        result = []
        for uid, ud in self.users.items():
            seconds = int(ud.data.get("total_seconds", 0))
            xp = (seconds // 60) * 10
            level = max(1, xp // 1000 + 1)
            hours, mins = divmod(seconds // 60, 60)
            result.append({
                "id": uid,
                "name": str(ud.data.get("player_name", uid)).upper(),
                "avatar": int(ud.data.get("avatar", 0)) % 8,
                "total_seconds": seconds,
                "playtime_str": f"{hours}h {mins:02d}m",
                "level": level,
                "trophies": ud.unlocked_count(),
                "user_data": ud,
                "is_active": (uid == self.active_user_id),
            })
        return result
