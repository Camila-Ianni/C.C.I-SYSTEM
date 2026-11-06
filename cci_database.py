"""
cci_database.py - Capa de persistencia SQLite relacional para C.C.I. System.
100% Python nativo utilizando la librería estándar sqlite3.
Compatible con entornos de escritorio locales y despliegue cloud (Render/Vercel).
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / ".cci-user-data"
DEFAULT_DB_FILE = DATA_DIR / "cci_system.sqlite3"

_db_lock = threading.RLock()


def get_db_path() -> Path:
    env_path = os.environ.get("CCI_DATABASE_PATH")
    if env_path:
        p = Path(env_path)
    else:
        p = DEFAULT_DB_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def get_db(db_path: Optional[Path] = None):
    """Context manager seguro para conexiones SQLite."""
    target_path = db_path or get_db_path()
    with _db_lock:
        conn = sqlite3.connect(
            str(target_path),
            check_same_thread=False,
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Inicializa el esquema de tablas y migra datos semilla."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 0. Cuentas de usuario web / nube
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        # 1. Catálogo de títulos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subtitle TEXT,
                developer TEXT,
                year TEXT,
                genre TEXT,
                players TEXT,
                slot INTEGER DEFAULT 0,
                tags TEXT,
                categories TEXT,
                card_url TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 2. Perfiles de usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                avatar INTEGER DEFAULT 0,
                total_seconds INTEGER DEFAULT 0,
                launch_count INTEGER DEFAULT 0,
                account_id INTEGER,
                last_session TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
            )
        """)
        try:
            cursor.execute("ALTER TABLE profiles ADD COLUMN account_id INTEGER REFERENCES accounts(id)")
        except Exception:
            pass

        # 3. Estadísticas por juego
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                seconds INTEGER DEFAULT 0,
                launches INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0,
                last_played TEXT,
                UNIQUE(profile_id, game_id),
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        # 4. Tabla de récords / leaderboards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highscores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                profile_id TEXT,
                score INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        # 5. Logros desbloqueados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements_unlocked (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                achievement_title TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                UNIQUE(profile_id, game_id, achievement_title),
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        # Índices para consultas de alto rendimiento
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_token ON accounts(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highscores_game ON highscores(game_id, score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_profile ON game_stats(profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_achievements_profile ON achievements_unlocked(profile_id)")

        # Sistema de migraciones versionadas sin regresión
        _apply_migrations(cursor)

    _seed_games_catalog(db_path)
    _seed_initial_highscores(db_path)
    _seed_admin_account(db_path)


def _apply_migrations(cursor: sqlite3.Cursor) -> None:
    """Aplica migraciones incrementales versionadas garantizando no-regresión."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT MAX(version) FROM schema_version")
    row = cursor.fetchone()
    current_version = row[0] if (row and row[0] is not None) else 0

    now_iso = datetime.now().isoformat(timespec="seconds")

    if current_version < 1:
        cursor.execute("""
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (1, ?, 'Esquema base de cuentas, perfiles, juegos, stats y trofeos')
        """, (now_iso,))
        current_version = 1

    if current_version < 2:
        # Migración Fase 1: Multijugador, amigos, grupos, chat, voz y grabaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id TEXT NOT NULL,
                addressee_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'rejected', 'blocked')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(requester_id, addressee_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                avatar TEXT,
                visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('private', 'public')),
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('owner', 'admin', 'member')),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'muted', 'banned')),
                joined_at TEXT NOT NULL,
                UNIQUE(group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                edited_at TEXT,
                deleted_at TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_sessions (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                started_by TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'ended')),
                started_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_rooms (
                id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                host_id TEXT NOT NULL,
                visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public', 'private')),
                status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting', 'playing', 'finished')),
                invite_code TEXT UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_room_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                player_slot INTEGER NOT NULL,
                ready_state INTEGER NOT NULL DEFAULT 0,
                connection_state TEXT NOT NULL DEFAULT 'connected' CHECK(connection_state IN ('connected', 'disconnected')),
                joined_at TEXT NOT NULL,
                UNIQUE(room_id, user_id),
                UNIQUE(room_id, player_slot),
                FOREIGN KEY (room_id) REFERENCES game_rooms(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                room_id TEXT,
                game_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                result_metadata TEXT,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gameplay_recordings (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                local_path TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0.0,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('private', 'shared')),
                thumbnail_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        # Índices de rendimiento para las nuevas entidades
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friendships_users ON friendships(requester_id, addressee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_rooms_status ON game_rooms(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_room_members_user ON game_room_members(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_game ON matches(game_id, started_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recordings_owner ON gameplay_recordings(owner_id, created_at DESC)")

        cursor.execute("""
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (2, ?, 'Fase 1: Tablas de amigos, grupos, mensajes, llamadas, salas, partidas y grabaciones')
        """, (now_iso,))


def _seed_games_catalog(db_path: Optional[Path] = None) -> None:
    """Inserta o actualiza los 19 juegos oficiales desde catalog_data."""
    try:
        from catalog_data import CATALOG
    except ImportError:
        return

    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        for g in CATALOG:
            cats = json.dumps(sorted(list(g.get("categories", []))))
            tags = g.get("tags", "")
            cursor.execute("""
                INSERT OR REPLACE INTO games (
                    id, title, subtitle, developer, year, genre, players, slot, tags, categories, card_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                g["id"],
                g["title"],
                g.get("subtitle", ""),
                g.get("developer", "C.C.I. System"),
                str(g.get("year", "2026")),
                g.get("genre", "Arcade"),
                str(g.get("players", "1")),
                int(g.get("slot", 0)),
                tags,
                cats,
                f"/assets/fotos_web/{g['id']}.jpg",
                now_iso
            ))


def _seed_initial_highscores(db_path: Optional[Path] = None) -> None:
    """Carga récords arcade clásicos de referencia si la tabla está vacía."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM highscores")
        row = cursor.fetchone()
        if row and row["total"] > 0:
            return

        seed_data = [
            ("pacman", "BILLY_M", 3333360, 255, "1999-07-03 21:00:00"),
            ("pacman", "CAMI_DEV", 1542000, 120, "2026-10-15 14:32:00"),
            ("pacman", "ARCADE_ACE", 894500, 85, "2026-10-20 18:10:00"),
            ("asteroids", "ED_LOGG", 1250000, 42, "1980-05-12 12:00:00"),
            ("asteroids", "CAMI_DEV", 940000, 31, "2026-10-16 19:22:00"),
            ("asteroids", "VOID_PILOT", 620000, 24, "2026-10-25 22:45:00"),
            ("space_invaders", "TOMOHIRO", 999990, 99, "1978-06-18 10:00:00"),
            ("space_invaders", "RETRO_KING", 450200, 52, "2026-10-14 11:15:00"),
            ("space_invaders", "CAMI_DEV", 380400, 48, "2026-10-21 17:50:00"),
            ("tetris", "JONAS_N", 999999, 29, "2018-10-21 16:00:00"),
            ("tetris", "CAMI_DEV", 685000, 22, "2026-10-18 20:30:00"),
            ("tetris", "LINE_MASTER", 512000, 18, "2026-10-22 13:05:00"),
            ("davinci", "CAMI_DEV", 88500, 15, "2026-10-22 16:40:00"),
            ("davinci", "DRAGON_FIST", 64200, 12, "2026-10-26 15:20:00"),
            ("davinci", "LEONARDO", 52100, 10, "2026-10-28 21:10:00"),
            ("metalslug", "MARCO_ROSSI", 4500000, 6, "2026-10-19 18:40:00"),
            ("metalslug", "CAMI_DEV", 3210000, 5, "2026-10-24 23:15:00"),
            ("metalslug", "TARMA_R", 2150000, 4, "2026-10-27 12:00:00"),
            ("mario", "SPEEDRUN_PRO", 999900, 8, "2026-10-17 19:00:00"),
            ("mario", "CAMI_DEV", 754000, 7, "2026-10-23 20:10:00"),
            ("ghostbusters", "PETER_V", 185000, 4, "2026-10-20 15:30:00"),
            ("dino", "CHROME_RUNNER", 89400, 1, "2026-10-25 18:00:00"),
            ("flappy", "PIXEL_BIRD", 420, 1, "2026-10-26 14:10:00"),
        ]

        cursor.executemany("""
            INSERT INTO highscores (game_id, player_name, score, level, recorded_at)
            VALUES (?, ?, ?, ?, ?)
        """, seed_data)


def _seed_admin_account(db_path: Optional[Path] = None) -> None:
    """Asegura que la cuenta oficial de la autora (mimi) exista en la base de datos cloud."""
    admin_email = "ianni.camila.c@gmail.com"
    admin_user = "MIMI"
    admin_pass = "1234"
    now_iso = datetime.now().isoformat(timespec="seconds")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE email = ?", (admin_email,))
        row = cursor.fetchone()
        if not row:
            token = secrets.token_hex(24)
            pwd_hash = generate_password_hash(admin_pass)
            cursor.execute("""
                INSERT INTO accounts (email, username, password_hash, token, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (admin_email, admin_user, pwd_hash, token, now_iso, now_iso))
            acc_id = cursor.lastrowid
            cursor.execute("""
                INSERT OR IGNORE INTO profiles (id, player_name, avatar, total_seconds, launch_count, created_at, updated_at, account_id)
                VALUES (?, ?, ?, 0, 0, ?, ?, ?)
            """, ("mimi", admin_user, 0, now_iso, now_iso, acc_id))
            cursor.execute("UPDATE profiles SET account_id = ? WHERE id = ?", (acc_id, "mimi"))
        else:
            acc_id = row["id"]
            pwd_hash = generate_password_hash(admin_pass)
            cursor.execute("""
                UPDATE accounts SET username = ?, password_hash = ? WHERE id = ?
            """, (admin_user, pwd_hash, acc_id))
            cursor.execute("""
                INSERT OR IGNORE INTO profiles (id, player_name, avatar, total_seconds, launch_count, created_at, updated_at, account_id)
                VALUES (?, ?, ?, 0, 0, ?, ?, ?)
            """, ("mimi", admin_user, 0, now_iso, now_iso, acc_id))
            cursor.execute("UPDATE profiles SET account_id = ? WHERE id = ?", (acc_id, "mimi"))


# ==============================================================================
# QUERIES: JUEGOS & CATÁLOGO
# ==============================================================================

def get_all_games(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games ORDER BY slot ASC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["categories"] = json.loads(d.get("categories") or "[]")
            except Exception:
                d["categories"] = []
            result.append(d)
        return result


def get_game_by_id(game_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["categories"] = json.loads(d.get("categories") or "[]")
        except Exception:
            d["categories"] = []
        return d


# ==============================================================================
# QUERIES: LEADERBOARDS & HIGH SCORES
# ==============================================================================

def record_highscore(
    game_id: str,
    player_name: str,
    score: int,
    level: int = 1,
    profile_id: Optional[str] = None,
    db_path: Optional[Path] = None
) -> int:
    clean_game = str(game_id).strip().lower()
    clean_name = str(player_name).upper().strip()
    try:
        score_val = int(score)
    except (ValueError, TypeError):
        raise ValueError("La puntuación debe ser un entero.")
    try:
        level_val = int(level)
    except (ValueError, TypeError):
        level_val = 1

    if not clean_game or not clean_name:
        raise ValueError("El ID del juego y el nombre del jugador son obligatorios.")
    if len(clean_name) < 2 or len(clean_name) > 24:
        raise ValueError("El nombre de jugador debe contener entre 2 y 24 caracteres.")
    if score_val <= 0 or score_val > 99999999:
        raise ValueError("Puntuación inválida o fuera de los límites permitidos (1 - 99.999.999).")
    if level_val < 1 or level_val > 999:
        raise ValueError("Nivel de juego fuera de rango (1 - 999).")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO highscores (game_id, player_name, profile_id, score, level, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_game, clean_name, profile_id, score_val, level_val, now_str))
        return cursor.lastrowid


def get_leaderboard(
    game_id: Optional[str] = None,
    limit: int = 10,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if game_id:
            cursor.execute("""
                SELECT h.*, g.title AS game_title
                FROM highscores h
                LEFT JOIN games g ON h.game_id = g.id
                WHERE h.game_id = ?
                ORDER BY h.score DESC, h.recorded_at ASC
                LIMIT ?
            """, (game_id, max(1, limit)))
        else:
            cursor.execute("""
                SELECT h.*, g.title AS game_title
                FROM highscores h
                LEFT JOIN games g ON h.game_id = g.id
                ORDER BY h.score DESC, h.recorded_at ASC
                LIMIT ?
            """, (max(1, limit),))
        return [dict(r) for r in cursor.fetchall()]


# ==============================================================================
# QUERIES: PERFILES & SINCRONIZACIÓN CLOUD
# ==============================================================================

def upsert_profile(
    profile_id: str,
    player_name: str,
    avatar: int = 0,
    total_seconds: int = 0,
    launch_count: int = 0,
    last_session: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    now_iso = datetime.now().isoformat(timespec="seconds")
    clean_id = profile_id.strip().lower()
    clean_name = player_name.strip().upper() or clean_id.upper()

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = ?", (clean_id,))
        existing = cursor.fetchone()

        if existing:
            new_seconds = max(existing["total_seconds"], total_seconds)
            new_launches = max(existing["launch_count"], launch_count)
            cursor.execute("""
                UPDATE profiles
                SET player_name = ?, avatar = ?, total_seconds = ?, launch_count = ?,
                    last_session = COALESCE(?, last_session), updated_at = ?
                WHERE id = ?
            """, (clean_name, int(avatar) % 8, new_seconds, new_launches, last_session, now_iso, clean_id))
        else:
            cursor.execute("""
                INSERT INTO profiles (
                    id, player_name, avatar, total_seconds, launch_count, last_session, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_id, clean_name, int(avatar) % 8, total_seconds, launch_count, last_session, now_iso, now_iso))

        cursor.execute("SELECT * FROM profiles WHERE id = ?", (clean_id,))
        return dict(cursor.fetchone())


def get_all_profiles(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*,
                   COUNT(DISTINCT a.achievement_title) AS total_trophies,
                   COUNT(DISTINCT s.game_id) AS games_played
            FROM profiles p
            LEFT JOIN achievements_unlocked a ON p.id = a.profile_id
            LEFT JOIN game_stats s ON p.id = s.profile_id
            GROUP BY p.id
            ORDER BY p.total_seconds DESC
        """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            sec = int(d.get("total_seconds", 0))
            hours, mins = divmod(sec // 60, 60)
            d["playtime_formatted"] = f"{hours}h {mins:02d}m"
            d["level"] = max(1, (sec // 60 * 10) // 1000 + 1)
            result.append(d)
        return result


def get_profile_detail(profile_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if not row:
            return None

        prof = dict(row)
        sec = int(prof.get("total_seconds", 0))
        hours, mins = divmod(sec // 60, 60)
        prof["playtime_formatted"] = f"{hours}h {mins:02d}m"
        prof["level"] = max(1, (sec // 60 * 10) // 1000 + 1)

        # Estadísticas de juegos
        cursor.execute("""
            SELECT s.*, g.title, g.genre
            FROM game_stats s
            JOIN games g ON s.game_id = g.id
            WHERE s.profile_id = ?
            ORDER BY s.seconds DESC
        """, (profile_id,))
        prof["game_stats"] = [dict(s) for s in cursor.fetchall()]

        # Logros obtenidos
        cursor.execute("""
            SELECT a.*, g.title AS game_title
            FROM achievements_unlocked a
            JOIN games g ON a.game_id = g.id
            WHERE a.profile_id = ?
            ORDER BY a.unlocked_at DESC
        """, (profile_id,))
        prof["achievements"] = [dict(a) for a in cursor.fetchall()]
        prof["total_trophies"] = len(prof["achievements"])

        return prof


def sync_profile_data(payload: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Sincroniza el perfil completo exportado por el emulador de escritorio hacia la base de datos central.
    """
    profile_id = payload.get("id") or payload.get("slug") or "usuario"
    name = payload.get("player_name") or payload.get("name") or profile_id.upper()
    avatar = int(payload.get("avatar", 0))
    total_seconds = int(payload.get("total_seconds", 0))
    launch_count = int(payload.get("launch_count", 0))
    last_session = payload.get("last_session")

    prof = upsert_profile(
        profile_id=profile_id,
        player_name=name,
        avatar=avatar,
        total_seconds=total_seconds,
        launch_count=launch_count,
        last_session=last_session,
        db_path=db_path
    )

    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Sincronizar estadísticas de juegos
        game_stats = payload.get("game_stats", {})
        for gid, stats in game_stats.items():
            if not isinstance(stats, dict):
                continue
            secs = int(stats.get("seconds", 0))
            launches = int(stats.get("launches", 0))
            progress = int(stats.get("progress", 0))
            last_played = stats.get("last_played")
            cursor.execute("""
                INSERT INTO game_stats (profile_id, game_id, seconds, launches, progress, last_played)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, game_id) DO UPDATE SET
                    seconds = MAX(game_stats.seconds, excluded.seconds),
                    launches = MAX(game_stats.launches, excluded.launches),
                    progress = MAX(game_stats.progress, excluded.progress),
                    last_played = COALESCE(excluded.last_played, game_stats.last_played)
            """, (profile_id, gid, secs, launches, progress, last_played))

        # Sincronizar logros reclamados
        claimed = payload.get("claimed_achievements", [])
        for ach_key in claimed:
            # formato típico: "game_id:title" o "title"
            if ":" in ach_key:
                gid, title = ach_key.split(":", 1)
            else:
                gid, title = "global", ach_key

            cursor.execute("""
                INSERT OR IGNORE INTO achievements_unlocked (profile_id, game_id, achievement_title, unlocked_at)
                VALUES (?, ?, ?, ?)
            """, (profile_id, gid, title, now_iso))

    return get_profile_detail(profile_id, db_path=db_path) or prof


# ==============================================================================
# TELEMETRÍA Y ESTADO DEL SISTEMA
# ==============================================================================

def get_telemetry_summary(db_path: Optional[Path] = None) -> Dict[str, Any]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total_games FROM games")
        total_games = cursor.fetchone()["total_games"]

        cursor.execute("SELECT COUNT(*) AS total_profiles FROM profiles")
        total_profiles = cursor.fetchone()["total_profiles"]

        cursor.execute("SELECT COUNT(*) AS total_scores FROM highscores")
        total_scores = cursor.fetchone()["total_scores"]

        cursor.execute("SELECT COALESCE(SUM(total_seconds), 0) AS playtime_sec FROM profiles")
        playtime_sec = cursor.fetchone()["playtime_sec"]

        cursor.execute("SELECT COUNT(*) AS total_trophies FROM achievements_unlocked")
        total_trophies = cursor.fetchone()["total_trophies"]

        hours, mins = divmod(playtime_sec // 60, 60)

        return {
            "status": "online",
            "engine": "SQLite 3 (WAL mode)",
            "total_games": total_games,
            "total_profiles": total_profiles,
            "total_highscores": total_scores,
            "total_trophies_unlocked": total_trophies,
            "total_playtime_seconds": playtime_sec,
            "total_playtime_formatted": f"{hours}h {mins:02d}m",
            "server_time": datetime.now().isoformat(timespec="seconds"),
        }


# ==============================================================================
# AUTENTICACIÓN Y CUENTAS DE USUARIO CLOUD
# ==============================================================================

def create_account(
    email: str,
    username: str,
    password: str,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    clean_email = email.strip().lower()
    clean_user = username.strip().upper()
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        raise ValueError("Correo electrónico inválido.")
    if len(password) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")
    if len(clean_user) < 2:
        raise ValueError("El nombre de usuario debe tener al menos 2 caracteres.")

    pwd_hash = generate_password_hash(password)
    token = secrets.token_hex(24)
    now_iso = datetime.now().isoformat(timespec="seconds")

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accounts (email, username, password_hash, token, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (clean_email, clean_user, pwd_hash, token, now_iso, now_iso))
            acc_id = cursor.lastrowid
            return {
                "id": acc_id,
                "email": clean_email,
                "username": clean_user,
                "token": token,
                "created_at": now_iso,
            }
        except sqlite3.IntegrityError:
            raise ValueError("El correo electrónico ya se encuentra registrado.")


def authenticate_account(
    email: str,
    password: str,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    clean_email = email.strip().lower()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return None
        if not check_password_hash(row["password_hash"], password):
            return None

        now_iso = datetime.now().isoformat(timespec="seconds")
        cursor.execute("UPDATE accounts SET last_login = ? WHERE id = ?", (now_iso, row["id"]))

        return {
            "id": row["id"],
            "email": row["email"],
            "username": row["username"],
            "token": row["token"],
            "created_at": row["created_at"],
            "last_login": now_iso,
        }


def get_account_by_token(token: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, username, token, created_at, last_login FROM accounts WHERE token = ?",
            (token.strip(),)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_account_by_id(account_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, username, token, created_at, last_login FROM accounts WHERE id = ?",
            (int(account_id),)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def link_profile_to_account(account_id: int, profile_id: str, db_path: Optional[Path] = None) -> bool:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE profiles SET account_id = ? WHERE id = ?",
            (int(account_id), profile_id.strip().lower())
        )
        return cursor.rowcount > 0


def get_account_dashboard(account_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, username, token, created_at, last_login FROM accounts WHERE id = ?",
            (int(account_id),)
        )
        row = cursor.fetchone()
        if not row:
            return None

        acc = dict(row)
        cursor.execute("SELECT * FROM profiles WHERE account_id = ?", (int(account_id),))
        profiles = [dict(p) for p in cursor.fetchall()]

        prof_ids = [p["id"] for p in profiles]
        if prof_ids:
            placeholders = ",".join("?" for _ in prof_ids)
            cursor.execute(f"""
                SELECT h.*, g.title AS game_title
                FROM highscores h
                LEFT JOIN games g ON h.game_id = g.id
                WHERE h.profile_id IN ({placeholders})
                ORDER BY h.score DESC
            """, prof_ids)
            user_scores = [dict(s) for s in cursor.fetchall()]

            cursor.execute(f"""
                SELECT s.*, g.title AS game_title, g.genre
                FROM game_stats s
                LEFT JOIN games g ON s.game_id = g.id
                WHERE s.profile_id IN ({placeholders})
                ORDER BY s.seconds DESC
            """, prof_ids)
            game_stats = [dict(st) for st in cursor.fetchall()]

            cursor.execute(f"""
                SELECT a.*, g.title AS game_title
                FROM achievements_unlocked a
                LEFT JOIN games g ON a.game_id = g.id
                WHERE a.profile_id IN ({placeholders})
                ORDER BY a.unlocked_at DESC
            """, prof_ids)
            trophies = [dict(t) for t in cursor.fetchall()]
        else:
            user_scores = []
            game_stats = []
            trophies = []

        total_sec = sum(int(p.get("total_seconds", 0)) for p in profiles)
        hours, mins = divmod(total_sec // 60, 60)

        acc["profiles"] = profiles
        acc["total_seconds"] = total_sec
        acc["playtime_formatted"] = f"{hours}h {mins:02d}m"
        acc["total_launches"] = sum(int(p.get("launch_count", 0)) for p in profiles)
        acc["highscores"] = user_scores
        acc["game_stats"] = game_stats
        acc["trophies"] = trophies
        acc["total_trophies"] = len(trophies)

        return acc


# ==============================================================================
# HELPER FUNCTIONS: FASE 1 ENTIDADES RELACIONALES (SALAS, AMIGOS, GRUPOS, CHAT)
# ==============================================================================

def get_schema_version(db_path: Optional[Path] = None) -> int:
    """Retorna la versión actual aplicada de la base de datos."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        return row[0] if (row and row[0] is not None) else 0


def create_game_room(
    room_id: str,
    game_id: str,
    host_id: str,
    visibility: str = "public",
    invite_code: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Crea una sala de juego multijugador y sienta al host en el slot 1."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO game_rooms (id, game_id, host_id, visibility, status, invite_code, created_at)
            VALUES (?, ?, ?, ?, 'waiting', ?, ?)
        """, (room_id, game_id, host_id, visibility, invite_code, now_iso))

        cursor.execute("""
            INSERT INTO game_room_members (room_id, user_id, player_slot, ready_state, connection_state, joined_at)
            VALUES (?, ?, 1, 1, 'connected', ?)
        """, (room_id, host_id, now_iso))

    return get_game_room(room_id, db_path=db_path)


def get_game_room(room_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Obtiene los detalles de una sala y sus miembros."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_rooms WHERE id = ?", (room_id,))
        row = cursor.fetchone()
        if not row:
            return None
        room = dict(row)

        cursor.execute("SELECT * FROM game_room_members WHERE room_id = ? ORDER BY player_slot ASC", (room_id,))
        room["members"] = [dict(m) for m in cursor.fetchall()]
        return room


def join_game_room(
    room_id: str,
    user_id: str,
    target_slot: int = 2,
    db_path: Optional[Path] = None
) -> bool:
    """Agrega un segundo jugador a la sala si el slot está libre."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Verificar estado de sala
        cursor.execute("SELECT status FROM game_rooms WHERE id = ?", (room_id,))
        row = cursor.fetchone()
        if not row or row["status"] != "waiting":
            return False

        # Verificar si el slot está ocupado
        cursor.execute("SELECT id FROM game_room_members WHERE room_id = ? AND player_slot = ?", (room_id, target_slot))
        if cursor.fetchone():
            return False

        cursor.execute("""
            INSERT INTO game_room_members (room_id, user_id, player_slot, ready_state, connection_state, joined_at)
            VALUES (?, ?, ?, 0, 'connected', ?)
        """, (room_id, user_id, target_slot, now_iso))
        return True


def leave_game_room(room_id: str, user_id: str, db_path: Optional[Path] = None) -> bool:
    """Remueve a un jugador de la sala. Si era el host, marca la sala como terminada."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT host_id FROM game_rooms WHERE id = ?", (room_id,))
        room = cursor.fetchone()
        if not room:
            return False

        cursor.execute("DELETE FROM game_room_members WHERE room_id = ? AND user_id = ?", (room_id, user_id))
        if room["host_id"] == user_id:
            cursor.execute("UPDATE game_rooms SET status = 'finished' WHERE id = ?", (room_id,))
        return True


def record_friendship_request(
    requester_id: str,
    addressee_id: str,
    db_path: Optional[Path] = None
) -> bool:
    """Crea una solicitud de amistad en estado pending."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO friendships (requester_id, addressee_id, status, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, ?)
        """, (requester_id, addressee_id, now_iso, now_iso))
        return True


def update_friendship_status(
    requester_id: str,
    addressee_id: str,
    status: str,
    db_path: Optional[Path] = None
) -> bool:
    """Actualiza estado de amistad (accepted, rejected, blocked)."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE friendships
            SET status = ?, updated_at = ?
            WHERE (requester_id = ? AND addressee_id = ?)
               OR (requester_id = ? AND addressee_id = ?)
        """, (status, now_iso, requester_id, addressee_id, addressee_id, requester_id))
        return cursor.rowcount > 0


def get_user_friends(user_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Devuelve la lista de amigos aceptados para un usuario."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM friendships
            WHERE (requester_id = ? OR addressee_id = ?) AND status = 'accepted'
            ORDER BY updated_at DESC
        """, (user_id, user_id))
        return [dict(f) for f in cursor.fetchall()]


def cancel_friendship_request(requester_id: str, addressee_id: str, db_path: Optional[Path] = None) -> bool:
    """Cancela o elimina una solicitud de amistad pendiente."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM friendships
            WHERE requester_id = ? AND addressee_id = ? AND status = 'pending'
        """, (requester_id, addressee_id))
        return cursor.rowcount > 0


def get_pending_friend_requests(user_id: str, db_path: Optional[Path] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Obtiene solicitudes entrantes y salientes pendientes para un usuario."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM friendships WHERE addressee_id = ? AND status = 'pending'", (user_id,))
        incoming = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM friendships WHERE requester_id = ? AND status = 'pending'", (user_id,))
        outgoing = [dict(r) for r in cursor.fetchall()]
        return {"incoming": incoming, "outgoing": outgoing}


def create_group_entry(
    group_id: str,
    name: str,
    owner_id: str,
    avatar: Optional[str] = None,
    visibility: str = "private",
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Crea un grupo y registra al creador como miembro con rol 'owner'."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO groups (id, name, owner_id, avatar, visibility, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (group_id, name, owner_id, avatar, visibility, now_iso))

        cursor.execute("""
            INSERT INTO group_members (group_id, user_id, role, status, joined_at)
            VALUES (?, ?, 'owner', 'active', ?)
        """, (group_id, owner_id, now_iso))

    return get_group_detail(group_id, db_path=db_path)


def get_group_detail(group_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Obtiene información del grupo junto con su lista de miembros."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            return None
        grp = dict(row)

        cursor.execute("SELECT * FROM group_members WHERE group_id = ? ORDER BY joined_at ASC", (group_id,))
        grp["members"] = [dict(m) for m in cursor.fetchall()]
        return grp


def get_user_groups(user_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Obtiene todos los grupos a los que pertenece un usuario."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, gm.role, gm.status AS member_status, gm.joined_at
            FROM groups g
            INNER JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ? AND gm.status != 'banned'
            ORDER BY gm.joined_at DESC
        """, (user_id,))
        return [dict(g) for g in cursor.fetchall()]


def add_group_member_entry(
    group_id: str,
    user_id: str,
    role: str = "member",
    db_path: Optional[Path] = None
) -> bool:
    """Agrega un nuevo miembro al grupo."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO group_members (group_id, user_id, role, status, joined_at)
            VALUES (?, ?, ?, 'active', ?)
        """, (group_id, user_id, role, now_iso))
        return True


def remove_group_member_entry(group_id: str, user_id: str, db_path: Optional[Path] = None) -> bool:
    """Elimina a un miembro del grupo."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        return cursor.rowcount > 0


def update_group_member_role_entry(group_id: str, user_id: str, new_role: str, db_path: Optional[Path] = None) -> bool:
    """Actualiza el rol de un miembro ('admin', 'member')."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE group_members
            SET role = ?
            WHERE group_id = ? AND user_id = ?
        """, (new_role, group_id, user_id))
        return cursor.rowcount > 0


def update_group_member_status_entry(group_id: str, user_id: str, new_status: str, db_path: Optional[Path] = None) -> bool:
    """Actualiza el estado de un miembro ('active', 'muted', 'banned')."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE group_members
            SET status = ?
            WHERE group_id = ? AND user_id = ?
        """, (new_status, group_id, user_id))
        return cursor.rowcount > 0


def transfer_group_ownership_entry(group_id: str, new_owner_id: str, db_path: Optional[Path] = None) -> bool:
    """Transfiere la propiedad del grupo a otro miembro."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Verificar que el nuevo dueño sea miembro
        cursor.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, new_owner_id))
        if not cursor.fetchone():
            return False

        # Actualizar dueño en groups
        cursor.execute("UPDATE groups SET owner_id = ? WHERE id = ?", (new_owner_id, group_id))
        # Actualizar rol en group_members a 'owner'
        cursor.execute("UPDATE group_members SET role = 'owner' WHERE group_id = ? AND user_id = ?", (group_id, new_owner_id))
        return True



def save_gameplay_recording_entry(
    recording_id: str,
    owner_id: str,
    game_id: str,
    local_path: str,
    duration_seconds: float,
    size_bytes: int,
    thumbnail_path: Optional[str] = None,
    db_path: Optional[Path] = None
) -> bool:
    """Guarda los metadatos de un clip de gameplay."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gameplay_recordings (
                id, owner_id, game_id, local_path, duration_seconds, size_bytes, visibility, thumbnail_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'private', ?, ?)
        """, (recording_id, owner_id, game_id, local_path, duration_seconds, size_bytes, thumbnail_path, now_iso))
        return True


def get_user_gameplay_recordings(owner_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Consulta grabaciones registradas de un usuario ordenadas por fecha."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, g.title AS game_title
            FROM gameplay_recordings r
            LEFT JOIN games g ON r.game_id = g.id
            WHERE r.owner_id = ?
            ORDER BY r.created_at DESC
        """, (owner_id,))
        return [dict(r) for r in cursor.fetchall()]


# ==============================================================================
# HELPER FUNCTIONS: FASE 3 CHAT Y MENSAJERÍA GRUPAL
# ==============================================================================

def save_chat_message_entry(
    message_id: str,
    group_id: str,
    sender_id: str,
    body: str,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Guarda un mensaje de texto en el historial del grupo."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (id, group_id, sender_id, body, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, group_id, sender_id, body, now_iso))

    return {
        "id": message_id,
        "group_id": group_id,
        "sender_id": sender_id,
        "body": body,
        "created_at": now_iso,
        "edited_at": None,
        "deleted_at": None,
    }


def get_chat_message_by_id(message_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Obtiene un mensaje por su ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_paged_messages_entry(
    group_id: str,
    limit: int = 30,
    before_created_at: Optional[str] = None,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Obtiene el historial paginado de mensajes de un grupo (excluyendo eliminados)."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if before_created_at:
            cursor.execute("""
                SELECT * FROM messages
                WHERE group_id = ? AND deleted_at IS NULL AND created_at < ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (group_id, before_created_at, limit))
        else:
            cursor.execute("""
                SELECT * FROM messages
                WHERE group_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (group_id, limit))

        rows = [dict(r) for r in cursor.fetchall()]
        # Retornar en orden cronológico ascendente para renderizado de chat
        return sorted(rows, key=lambda m: m["created_at"])


def soft_delete_chat_message_entry(message_id: str, db_path: Optional[Path] = None) -> bool:
    """Borrado lógico de un mensaje (marca deleted_at)."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET deleted_at = ?
            WHERE id = ? AND deleted_at IS NULL
        """, (now_iso, message_id))
        return cursor.rowcount > 0


def record_message_report_entry(
    report_id: str,
    message_id: str,
    reporter_id: str,
    reason: str,
    db_path: Optional[Path] = None
) -> bool:
    """Registra un reporte de moderación para un mensaje."""
    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_reports (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                reporter_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO message_reports (id, message_id, reporter_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (report_id, message_id, reporter_id, reason, now_iso))
        return True


# ==============================================================================
# HELPER FUNCTIONS: FASE 4 MULTIJUGADOR ONLINE Y REGISTRO DE PARTIDAS
# ==============================================================================

def get_room_by_invite_code_entry(invite_code: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Busca una sala de juego por su código de invitación alfanumérico."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_rooms WHERE invite_code = ?", (invite_code.strip().upper(),))
        row = cursor.fetchone()
        if not row:
            return None
        room = dict(row)
        cursor.execute("SELECT * FROM game_room_members WHERE room_id = ? ORDER BY player_slot ASC", (room["id"],))
        room["members"] = [dict(m) for m in cursor.fetchall()]
        return room


def record_match_result_entry(
    match_id: str,
    room_id: str,
    game_id: str,
    started_at: str,
    ended_at: str,
    result_metadata: Dict[str, Any],
    db_path: Optional[Path] = None
) -> bool:
    """Registra el resultado validado de una partida en la tabla matches."""
    meta_json = json.dumps(result_metadata)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO matches (id, room_id, game_id, started_at, ended_at, result_metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (match_id, room_id, game_id, started_at, ended_at, meta_json))
        return True


def get_match_history_entries(
    game_id: Optional[str] = None,
    limit: int = 20,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Consulta el historial de partidas recientes con sus metadatos deserializados."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if game_id:
            cursor.execute("""
                SELECT m.*, g.title AS game_title
                FROM matches m
                LEFT JOIN games g ON m.game_id = g.id
                WHERE m.game_id = ?
                ORDER BY m.started_at DESC
                LIMIT ?
            """, (game_id, limit))
        else:
            cursor.execute("""
                SELECT m.*, g.title AS game_title
                FROM matches m
                LEFT JOIN games g ON m.game_id = g.id
                ORDER BY m.started_at DESC
                LIMIT ?
            """, (limit,))

        results = []
        for row in cursor.fetchall():
            m = dict(row)
            try:
                m["result_metadata"] = json.loads(m["result_metadata"]) if m["result_metadata"] else {}
            except Exception:
                m["result_metadata"] = {}
            results.append(m)
        return results



