"""
cci_database.py - Capa de persistencia SQLite relacional para C.C.I. System.
100% Python nativo utilizando la librería estándar sqlite3.
Compatible con entornos de escritorio locales y despliegue cloud (Render/Vercel).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
                last_session TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highscores_game ON highscores(game_id, score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_profile ON game_stats(profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_achievements_profile ON achievements_unlocked(profile_id)")

    _seed_games_catalog(db_path)
    _seed_initial_highscores(db_path)


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
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO highscores (game_id, player_name, profile_id, score, level, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (game_id, player_name.upper().strip(), profile_id, int(score), int(level), now_str))
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
