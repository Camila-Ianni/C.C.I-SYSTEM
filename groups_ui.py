"""Pantallas modulares de Grupos y Comunidad para C.C.I. System.

Construidas con las 4 bases limpias vacías y los sprites recortados de las hojas
transparentes Photoroom en 'Grupos assets ', manteniendo la barra lateral
compartida (sidebar_ui.py) idéntica en todas las pantallas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import pygame

from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from backend.communities.stream_adapter import CCI_TITLES, capture_stream_frame
from sidebar_ui import draw_sidebar, load_sidebar, make_sidebar_font, sidebar_destination
from states import BaseState, SCREEN_HEIGHT, SCREEN_WIDTH


# ---------------------------------------------------------------------------
# Catálogo de comunidades y modelos de datos interactivos
# ---------------------------------------------------------------------------

COMMUNITIES_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "night_raid",
        "group_id": "grp_night_raid",
        "name": "NIGHT RAID",
        "subtitle": "COMUNIDAD DE JUEGOS • 24 MIEMBROS",
        "description": "Comunidad enfocada en juegos competitivos, eventos y proyectos de C.C.I.",
        "privacy": "Grupo privado",
        "members_count": 24,
        "online_count": 5,
        "channels_count": 12,
        "voice_count": 3,
        "is_owner": True,
        "card_sprite": "card_0_night_raid.png",
        "banner_idx": 0,
        "emblem_idx": 0,
        "recent_rank": 0,
    },
    {
        "id": "sakura_club",
        "group_id": "grp_sakura_club",
        "name": "SAKURA CLUB",
        "subtitle": "ARTE Y CULTURA • 18 MIEMBROS",
        "description": "Espacio de ilustración pixel art, estética japonesa, música lo-fi y charlas.",
        "privacy": "Grupo público",
        "members_count": 18,
        "online_count": 3,
        "channels_count": 8,
        "voice_count": 2,
        "is_owner": False,
        "card_sprite": "card_1_sakura_club.png",
        "banner_idx": 1,
        "emblem_idx": 1,
        "recent_rank": 1,
    },
    {
        "id": "da_vinci_team",
        "group_id": "grp_davinci_team",
        "name": "DA VINCI TEAM",
        "subtitle": "DESARROLLO C.C.I. • 12 MIEMBROS",
        "description": "Equipo de desarrollo de videojuegos indie, motores gráficos y torneos.",
        "privacy": "Grupo privado",
        "members_count": 12,
        "online_count": 2,
        "channels_count": 10,
        "voice_count": 2,
        "is_owner": True,
        "card_sprite": "card_2_davinci_team.png",
        "banner_idx": 2,
        "emblem_idx": 2,
        "recent_rank": 2,
    },
    {
        "id": "pixel_squad",
        "group_id": "grp_pixel_squad",
        "name": "PIXEL SQUAD",
        "subtitle": "ARCADE & RETRO • 30 MIEMBROS",
        "description": "Comunidad de speedruns, retos semanales de arcade y récords cooperativos.",
        "privacy": "Grupo público",
        "members_count": 30,
        "online_count": 9,
        "channels_count": 14,
        "voice_count": 4,
        "is_owner": False,
        "card_sprite": "card_3_pixel_squad.png",
        "banner_idx": 3,
        "emblem_idx": 3,
        "recent_rank": 3,
    },
    {
        "id": "kpop_zone",
        "group_id": "grp_kpop_zone",
        "name": "K-POP ZONE",
        "subtitle": "MÚSICA Y RITMO • 56 MIEMBROS",
        "description": "Eventos de juegos de ritmo, watch parties en vivo y listas colaborativas.",
        "privacy": "Grupo público",
        "members_count": 56,
        "online_count": 14,
        "channels_count": 16,
        "voice_count": 5,
        "is_owner": False,
        "card_sprite": "card_4_kpop_zone.png",
        "banner_idx": 4,
        "emblem_idx": 4,
        "recent_rank": 4,
    },
    {
        "id": "cosmos",
        "group_id": "grp_cosmos",
        "name": "COSMOS",
        "subtitle": "EXPLORACIÓN SCI-FI • 20 MIEMBROS",
        "description": "Simuladores espaciales, lore sci-fi y misiones nocturnas de escuadrón.",
        "privacy": "Grupo privado",
        "members_count": 20,
        "online_count": 4,
        "channels_count": 9,
        "voice_count": 2,
        "is_owner": False,
        "card_sprite": "card_5_cosmos.png",
        "banner_idx": 5,
        "emblem_idx": 5,
        "recent_rank": 5,
    },
]


@dataclass
class DirectChatContact:
    contact_id: str
    name: str
    handle: str
    status: str
    activity: str
    last_message: str
    last_time: str
    unread: int = 0
    contact_sprite: str = ""
    messages: List[Tuple[str, str, str]] = field(default_factory=list)


@dataclass
class GroupInviteItem:
    req_id: str
    group_name: str
    inviter: str
    sprite_name: str


@dataclass
class FriendRequestItem:
    req_id: str
    user_name: str
    sprite_name: str


DEFAULT_DMS: List[DirectChatContact] = [
    DirectChatContact(
        contact_id="dm_tomas",
        name="Tomás",
        handle="@tomas_dev",
        status="En línea",
        activity="Jugando: Da Vinci Fighters",
        last_message="Yo llevo soporte, tranqui.",
        last_time="22:18",
        unread=0,
        contact_sprite="dm_contact_0.png",
        messages=[
            ("Tomás", "22:14", "¿Entrás al torneo de esta noche en Night Raid?"),
            ("ALEX", "22:15", "Sí, ya casi termino de configurar el control."),
            ("Tomás", "22:16", "Joya, nos falta uno para completar el squad."),
            ("ALEX", "22:17", "Ahí le aviso a Mira que estaba conectada."),
            ("Tomás", "22:18", "Yo llevo soporte, tranqui."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_martina",
        name="Martina",
        handle="@marti_px",
        status="En línea",
        activity="En Sakura Club",
        last_message="Te pasé los nuevos sprites del menú.",
        last_time="21:40",
        unread=2,
        contact_sprite="dm_contact_1.png",
        messages=[
            ("Martina", "21:38", "¡Hola Alex! ¿Pudiste ver los bocetos del club?"),
            ("Martina", "21:40", "Te pasé los nuevos sprites del menú."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_kai",
        name="Kai",
        handle="@kai_nr",
        status="En línea",
        activity="En sala de voz: Gaming",
        last_message="Estamos en sala Gaming, sumate.",
        last_time="20:55",
        unread=0,
        contact_sprite="dm_contact_2.png",
        messages=[
            ("Kai", "20:50", "¿Sale partida rápida antes del evento?"),
            ("ALEX", "20:52", "Dame 5 minutos y entro."),
            ("Kai", "20:55", "Estamos en sala Gaming, sumate."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_luna",
        name="Luna",
        handle="@luna_craft",
        status="En línea",
        activity="Jugando: Minecraft",
        last_message="Mirá cómo quedó la base del servidor.",
        last_time="19:12",
        unread=1,
        contact_sprite="dm_contact_3.png",
        messages=[
            ("Luna", "19:12", "Mirá cómo quedó la base del servidor."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_ren",
        name="Ren",
        handle="@ren_arcade",
        status="Ausente",
        activity="Ausente",
        last_message="Mañana intento superar tu récord.",
        last_time="Ayer",
        unread=0,
        contact_sprite="dm_contact_4.png",
        messages=[
            ("Ren", "Ayer", "Mañana intento superar tu récord."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_sofia",
        name="Sofía",
        handle="@sofi_kpop",
        status="Sin conexión",
        activity="Desconectada",
        last_message="¡Gracias por la invitación al grupo!",
        last_time="Lun",
        unread=0,
        contact_sprite="dm_contact_5.png",
        messages=[
            ("Sofía", "Lun", "¡Gracias por la invitación al grupo!"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Presets y sintetizador de Soundboard / Sound Deck (Efectos de audio estilo Discord)
# ---------------------------------------------------------------------------

SOUNDBOARD_PRESETS: List[Dict[str, str]] = [
    {"id": "snd_gg", "name": "GG", "icon": "🟢", "desc": "Triunfo retro (C-E-G)", "key": "1"},
    {"id": "snd_airhorn", "name": "AIRHORN", "icon": "📢", "desc": "Bocina MLG", "key": "2"},
    {"id": "snd_ko", "name": "K.O.", "icon": "💥", "desc": "Impacto fatal", "key": "3"},
    {"id": "snd_victory", "name": "VICTORY", "icon": "🏆", "desc": "Fanfarria estelar", "key": "4"},
    {"id": "snd_levelup", "name": "LEVEL UP", "icon": "⚡", "desc": "Subida de nivel", "key": "5"},
    {"id": "snd_buzzer", "name": "BUZZER", "icon": "🛑", "desc": "Alerta / Error", "key": "6"},
]


def play_soundboard_tone(sound_name: str) -> None:
    """Sintetiza efectos de audio para la soundboard sin requerir archivos WAV/MP3 externos."""
    try:
        if not pygame.mixer.get_init():
            return
        sample_rate = 22050
        buf = bytearray()
        s_norm = sound_name.upper().strip()

        if s_norm in ("GG", "SND_GG"):
            tones = [(523.25, 0.08), (659.25, 0.08), (783.99, 0.22)]
        elif s_norm in ("AIRHORN", "SND_AIRHORN"):
            tones = [(587.33, 0.06), (587.33, 0.06), (587.33, 0.06), (880.00, 0.22)]
        elif s_norm in ("K.O.", "KO", "SND_KO"):
            tones = [(440.00, 0.09), (329.63, 0.09), (220.00, 0.11), (110.00, 0.25)]
        elif s_norm in ("VICTORY", "SND_VICTORY"):
            tones = [(440.00, 0.08), (554.37, 0.08), (659.25, 0.08), (880.00, 0.24)]
        elif s_norm in ("LEVEL UP", "LEVELUP", "SND_LEVELUP"):
            tones = [(330.00, 0.07), (392.00, 0.07), (523.25, 0.07), (659.25, 0.18)]
        else:
            tones = [(160.00, 0.12), (130.00, 0.18)]

        for freq, dur in tones:
            n_samples = int(sample_rate * dur)
            for i in range(n_samples):
                t = float(i) / sample_rate
                env = 1.0 - (i / n_samples) * 0.4
                val = int(127 * env) if math.sin(2.0 * math.pi * freq * t) > 0 else int(-128 * env)
                buf.append(val & 0xFF)

        sound = pygame.mixer.Sound(buffer=bytes(buf))
        sound.set_volume(0.35)
        sound.play()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Gestor de capturas F12 y adjuntos para chat
# ---------------------------------------------------------------------------

_THUMB_CACHE: Dict[str, pygame.Surface] = {}

def get_screenshot_thumbnail(file_path: str, width: int = 140, height: int = 80) -> Optional[pygame.Surface]:
    """Carga y genera miniatura escalada de una captura F12 con caché en memoria."""
    key = f"{file_path}_{width}x{height}"
    if key in _THUMB_CACHE:
        return _THUMB_CACHE[key]
    try:
        p = Path(file_path)
        if not p.is_file():
            return None
        orig = pygame.image.load(str(p))
        scaled = pygame.transform.smoothscale(orig, (width, height))
        _THUMB_CACHE[key] = scaled
        return scaled
    except Exception:
        return None

def list_available_screenshots(limit: int = 6) -> List[Dict[str, Any]]:
    """Obtiene las capturas F12 más recientes guardadas en la carpeta capturas/."""
    from screenshot_manager import CAPTURAS_DIR
    CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(CAPTURAS_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: List[Dict[str, Any]] = []
    for p in files[:limit]:
        stat = p.stat()
        mtime_str = time.strftime("%d/%m %H:%M", time.localtime(stat.st_mtime))
        size_kb = round(stat.st_size / 1024, 1)
        out.append({
            "filename": p.name,
            "path": str(p),
            "size_str": f"{size_kb} KB",
            "time_str": mtime_str,
            "size_bytes": stat.st_size,
        })
    return out


# ---------------------------------------------------------------------------
# Caché de bases limpias y sprites Photoroom recortados
# ---------------------------------------------------------------------------

class GruposSpritePack:
    """Carga las 4 bases limpias y todos los sprites transparentes de assets/grupos_sprites."""

    def __init__(self) -> None:
        self.loaded = False
        self.sprites: Dict[str, pygame.Surface] = {}
        self.bases: Dict[str, pygame.Surface] = {}
        self.fonts: Dict[str, pygame.font.Font] = {}

    def ensure_loaded(self) -> None:
        if self.loaded:
            return
        if not pygame.font.get_init():
            pygame.font.init()

        for key, size, bold in [
            ("title", 20, True),
            ("subtitle", 13, False),
            ("tab", 13, True),
            ("card_title", 14, True),
            ("card_sub", 12, False),
            ("body", 13, False),
            ("body_bold", 13, True),
            ("small", 11, False),
            ("small_bold", 11, True),
        ]:
            try:
                self.fonts[key] = pygame.font.SysFont("Arial", size, bold=bold)
            except Exception:
                self.fonts[key] = pygame.font.Font(None, size + 2)

        folder = Path(__file__).resolve().parent / "assets" / "grupos_sprites"
        if folder.exists():
            for png in folder.glob("*.png"):
                try:
                    surf = pygame.image.load(str(png))
                    if png.name.startswith("base_"):
                        surf = surf.convert() if pygame.display.get_surface() else surf
                        self.bases[png.name] = surf
                    else:
                        surf = surf.convert_alpha() if pygame.display.get_surface() else surf
                        self.sprites[png.name] = surf
                except Exception as exc:
                    print(f"[CCI] Error cargando sprite {png.name}: {exc}")

        self.loaded = True


_PACK = GruposSpritePack()


def _wrap_lines(text: str, font: pygame.font.Font, max_w: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        cand = f"{cur} {w}"
        if font.size(cand)[0] <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _draw_cut_rect(
    surf: pygame.Surface,
    rect: pygame.Rect,
    bg_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int],
    cut: int = 7,
    border_w: int = 1,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    pts = [
        (x + cut, y),
        (x + w - cut, y),
        (x + w, y + cut),
        (x + w, y + h - cut),
        (x + w - cut, y + h),
        (x + cut, y + h),
        (x, y + h - cut),
        (x, y + cut),
    ]
    pygame.draw.polygon(surf, bg_color, pts)
    if border_w > 0:
        pygame.draw.polygon(surf, border_color, pts, border_w)


# ---------------------------------------------------------------------------
# Portapapeles Multiplataforma y Plantillas de Canales por Comunidad
# ---------------------------------------------------------------------------

_INTERNAL_CLIPBOARD: str = ""


def copy_to_clipboard(text: str) -> None:
    """Copia texto al portapapeles del sistema (macOS/Windows/Linux) y al buffer interno."""
    global _INTERNAL_CLIPBOARD
    _INTERNAL_CLIPBOARD = text
    try:
        if pygame.scrap.get_init():
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    except Exception:
        pass
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), timeout=1, check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["clip"], input=text.encode("utf-16le"), timeout=1, check=False)
    except Exception:
        pass


def paste_from_clipboard() -> str:
    """Recupera texto del portapapeles del sistema o del buffer interno."""
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(["pbpaste"], timeout=1).decode("utf-8", errors="ignore").strip()
            if out:
                return out
    except Exception:
        pass
    try:
        if pygame.scrap.get_init():
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if raw:
                return raw.decode("utf-8", errors="ignore").rstrip("\x00").strip()
    except Exception:
        pass
    return _INTERNAL_CLIPBOARD


def extract_invite_code(raw_input: str) -> str:
    """Extrae el código de invitación tanto si el usuario ingresa un código directo como un link cci:// o https://."""
    cleaned = raw_input.strip()
    if "/" in cleaned:
        cleaned = cleaned.rstrip("/").split("/")[-1]
    if "?" in cleaned:
        cleaned = cleaned.split("?")[0]
    return cleaned.strip().upper()


COMMUNITY_CHANNEL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "night-raid": {
        "text": [
            ("anuncios", "Información y comunicados oficiales de Night Raid."),
            ("reglas", "Normas de convivencia de la comunidad."),
            ("bienvenidas", "Nuevos miembros que se unen al servidor."),
            ("general", "Conversación general de la comunidad."),
            ("off-topic", "Charlas libres, música y otros temas."),
            ("clips-y-memes", "Capturas, jugadas destacadas y humor."),
            ("busqueda-de-equipo", "Coordinación de squads y partidas competitivas."),
            ("sugerencias", "Ideas y mejoras para la comunidad."),
        ],
        "voice": [
            ("Sala principal", 16),
            ("Gaming", 8),
            ("Rankeds", 5),
            ("Streaming", 4),
        ],
        "members": [
            ("ALEX", "En línea", "Jugando: Da Vinci Fighters", "OWNER"),
            ("MIRA", "En línea", "En #general", "ADMIN"),
            ("KAI", "En línea", "En voz: Gaming", "MOD"),
            ("ZERO", "En línea", "Jugando: DOOM", "MIEMBRO"),
            ("VALEN", "En línea", "En línea", "MIEMBRO"),
            ("REN", "Ausente", "Ausente hace 15m", "MIEMBRO"),
            ("LUNA", "Ausente", "AFK", "MIEMBRO"),
        ],
    },
    "sakura-club": {
        "text": [
            ("anuncios-club", "Eventos de arte, concursos de pixel-art y avisos."),
            ("reglas", "Respeto creativo y créditos a los autores."),
            ("general", "Charla general de arte, anime y cultura japonesa."),
            ("galeria-pixel", "Compartí tus sprites, fondos e ilustraciones."),
            ("musica-lofi", "Recomendaciones de playlists lo-fi y synthwave."),
            ("encargos-y-collabs", "Colaboraciones entre artistas y desarrolladores."),
        ],
        "voice": [
            ("Atelier Creativo", 12),
            ("Radio Lo-Fi 24/7", 20),
        ],
        "members": [
            ("MARTINA", "En línea", "Dibujando sprites", "OWNER"),
            ("ALEX", "En línea", "Viendo #galeria-pixel", "MIEMBRO"),
            ("HANA", "En línea", "Escuchando Radio Lo-Fi", "MOD"),
            ("SORA", "Ausente", "Ausente", "MIEMBRO"),
        ],
    },
    "da-vinci-team": {
        "text": [
            ("roadmap", "Hitos de desarrollo y lanzamientos de C.C.I. System."),
            ("general", "Coordinación diaria del equipo de desarrollo."),
            ("dev-log", "Avances de motor Pygame-CE, shaders y red 60 Hz."),
            ("bugs-y-qa", "Reporte de bugs, pruebas automatizadas y CI."),
            ("playtesting", "Feedback de balance de Da Vinci Fighters."),
        ],
        "voice": [
            ("Daily Standup", 10),
            ("Pair Programming", 4),
        ],
        "members": [
            ("ALEX", "En línea", "Compilando v2.1.0", "OWNER"),
            ("TOMÁS", "En línea", "En #dev-log", "ADMIN"),
            ("LUCA", "Ausente", "Revisando PRs", "MOD"),
        ],
    },
    "pixel-squad": {
        "text": [
            ("retos-semanales", "Desafíos arcade de la semana y tabla de puntos."),
            ("general", "Charla retro, estrategias y trucos de arcade."),
            ("high-scores", "Capturas F12 de récords verificados."),
            ("speedruns", "Rutas óptimas para Super Mario, Zelda y Metroidvania."),
        ],
        "voice": [
            ("Arcade Cabina 1", 8),
            ("Speedrun Live", 6),
            ("Co-op Retro", 4),
        ],
        "members": [
            ("REN", "En línea", "Speedrun Pac-Man", "OWNER"),
            ("ALEX", "En línea", "En línea", "MIEMBRO"),
            ("MAX", "En línea", "Jugando: Metal Slug", "MOD"),
            ("NICO", "En línea", "Jugando: Tetris", "MIEMBRO"),
        ],
    },
    "kpop-zone": {
        "text": [
            ("anuncios-eventos", "Calendario de watch parties y estrenos."),
            ("general", "Charla principal de música, ritmo y grupos."),
            ("comebacks", "Lanzamientos, MVs y votaciones de la semana."),
            ("watch-party", "Chat en vivo durante las transmisiones."),
        ],
        "voice": [
            ("Stage Principal", 25),
            ("Karaoke & Rhythm", 10),
        ],
        "members": [
            ("SOFÍA", "En línea", "Organizando Watch Party", "OWNER"),
            ("ALEX", "En línea", "En línea", "MIEMBRO"),
            ("MINA", "En línea", "En Stage Principal", "MOD"),
        ],
    },
    "cosmos": {
        "text": [
            ("bitacora-estelar", "Comunicados del comando espacial."),
            ("general", "Punto de encuentro de pilotos y exploradores."),
            ("misiones-coop", "Reclutamiento para incursiones nocturnas."),
            ("lore-scifi", "Teorías, universos sci-fi y simuladores."),
        ],
        "voice": [
            ("Puente de Mando", 12),
            ("Escuadrón Alfa", 6),
        ],
        "members": [
            ("ORION", "En línea", "Jugando: Asteroids", "OWNER"),
            ("ALEX", "En línea", "En línea", "MIEMBRO"),
            ("NOVA", "Ausente", "En órbita", "MOD"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Adaptador de Persistencia Real (CommunitiesService + SQLite)
# ---------------------------------------------------------------------------

class CommunitiesUIBridge:
    """Conecta las pantallas de Grupos y Comunidad con CommunitiesService y persistencia SQLite."""

    DEFAULT_USER_ID = "u_alex"
    DEFAULT_USERNAME = "ALEX"

    def __init__(self, db_path: Optional[str] = None, user_id: str = DEFAULT_USER_ID) -> None:
        self.user_id = user_id
        self.repo = CommunitiesRepository(db_path) if db_path else CommunitiesRepository.get_instance()
        self.service = CommunitiesService(self.repo)
        self._ensure_ui_tables_and_seed()

    def _ensure_ui_tables_and_seed(self) -> None:
        conn = self.repo._get_connection()
        with self.repo._tx_lock, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_social_state (
                    state_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

        # Sembrar las 6 comunidades base en SQLite si aún no existen (salvo CCI_DEMO_SEED=0)
        if os.getenv("CCI_DEMO_SEED", "1") == "0":
            return

        for cat in COMMUNITIES_CATALOG:
            slug = cat["id"].replace("_", "-")
            existing = self.repo.get_community_by_slug(slug)
            if not existing:
                comm = self.service.create_community(
                    owner_id=self.user_id,
                    name=cat["name"],
                    description=cat["description"],
                    visibility="private" if "privado" in cat["privacy"].lower() else "public",
                    slug=slug,
                )
                comm_id = comm["id"]
                tpl = COMMUNITY_CHANNEL_TEMPLATES.get(slug, COMMUNITY_CHANNEL_TEMPLATES["night-raid"])
                existing_ch = {c["name"].lower(): c for c in self.repo.list_channels(comm_id)}
                # Reemplazar 'General Voice' genérico si la plantilla tiene salas propias
                if "general voice" in existing_ch and all(vc[0].lower() != "general voice" for vc in tpl["voice"]):
                    self.repo.delete_channel(existing_ch["general voice"]["id"])
                    existing_ch.pop("general voice", None)

                for idx, (ch_name, ch_topic) in enumerate(tpl["text"]):
                    if ch_name.lower() not in existing_ch:
                        self.repo.create_channel(
                            community_id=comm_id,
                            name=ch_name,
                            channel_type="text",
                            topic=ch_topic,
                            position=idx,
                        )
                    else:
                        self.repo.update_channel(existing_ch[ch_name.lower()]["id"], {"topic": ch_topic, "position": idx})

                for idx, (vc_name, max_p) in enumerate(tpl["voice"]):
                    if vc_name.lower() not in existing_ch:
                        self.repo.create_channel(
                            community_id=comm_id,
                            name=vc_name,
                            channel_type="voice",
                            topic=f"Sala de voz {vc_name}",
                            max_participants=max_p,
                            position=20 + idx,
                        )
                self._ensure_community_invite_code(comm_id)

    def _ensure_community_invite_code(self, comm_id: str) -> str:
        conn = self.repo._get_connection()
        row = conn.execute(
            "SELECT code FROM invitations WHERE community_id = ? AND is_revoked = 0 ORDER BY created_at DESC LIMIT 1",
            (comm_id,),
        ).fetchone()
        if row:
            return str(row["code"])
        inv = self.repo.create_invitation(comm_id, self.user_id, max_uses=0)
        return str(inv["code"])

    def get_or_create_invite(self, slug_or_id: str, regenerate: bool = False) -> Dict[str, str]:
        """Obtiene o regenera el código y link de invitación real para cualquier comunidad."""
        comm = self._resolve_community(slug_or_id)
        if not comm:
            code = slug_or_id.upper()[:8]
        elif regenerate:
            inv = self.repo.create_invitation(comm["id"], self.user_id, max_uses=0)
            code = str(inv["code"])
        else:
            code = self._ensure_community_invite_code(comm["id"])
        return {
            "code": code,
            "uri": f"cci://invite/{code}",
            "link": f"https://c-c-i-system.onrender.com/invite/{code}",
        }

    def _resolve_community(self, slug_or_id: str) -> Optional[Dict[str, Any]]:
        comm = self.repo.get_community(slug_or_id)
        if comm:
            return comm
        slug = slug_or_id.replace("_", "-").lower()
        comm = self.repo.get_community_by_slug(slug)
        if comm:
            return comm
        return self.repo.get_community_by_slug(slug_or_id)

    def load_groups(self) -> List[Dict[str, Any]]:
        """Carga todas las comunidades persistidas en SQLite con conteos reales de canales y código de invitación."""
        db_comms = self.repo.list_communities_for_user(self.user_id)
        catalog_by_slug = {c["id"].replace("_", "-"): c for c in COMMUNITIES_CATALOG}
        catalog_by_name = {c["name"].upper(): c for c in COMMUNITIES_CATALOG}

        custom_items: List[Dict[str, Any]] = []
        preset_items: List[Dict[str, Any]] = []

        for rank_idx, dc in enumerate(db_comms):
            slug = dc["slug"]
            channels = self.repo.list_channels(dc["id"])
            text_cnt = sum(1 for c in channels if c["type"] == "text") or 1
            voice_cnt = sum(1 for c in channels if c["type"] in ("voice", "stream")) or 1
            db_members_cnt = len(self.repo.list_members(dc["id"]))
            invite_info = self.get_or_create_invite(dc["id"])

            preset = catalog_by_slug.get(slug) or catalog_by_name.get(dc["name"].upper())
            if preset:
                item = dict(preset)
                item["db_id"] = dc["id"]
                item["channels_count"] = text_cnt
                item["voice_count"] = voice_cnt
                item["members_count"] = max(item.get("members_count", 1), db_members_cnt)
                item["invite_code"] = invite_info["code"]
                item["invite_link"] = invite_info["link"]
                item["invite_uri"] = invite_info["uri"]
                item["is_custom"] = False
                preset_items.append(item)
            else:
                members_cnt = max(1, db_members_cnt)
                palette_idx = sum(ord(ch) for ch in dc["name"]) % 6
                custom_items.append({
                    "id": dc["slug"],
                    "db_id": dc["id"],
                    "group_id": dc["id"],
                    "name": dc["name"].upper(),
                    "subtitle": f"COMUNIDAD C.C.I. • {members_cnt} MIEMBRO{'S' if members_cnt != 1 else ''}",
                    "description": dc.get("description") or "Comunidad creada desde la consola C.C.I. System.",
                    "privacy": "Grupo privado" if dc.get("visibility") == "private" else "Grupo público",
                    "members_count": members_cnt,
                    "online_count": max(1, min(members_cnt, 4)),
                    "channels_count": text_cnt,
                    "voice_count": voice_cnt,
                    "is_owner": dc.get("owner_id") == self.user_id,
                    "card_sprite": "",
                    "banner_idx": palette_idx,
                    "emblem_idx": palette_idx,
                    "recent_rank": -100 + rank_idx,
                    "invite_code": invite_info["code"],
                    "invite_link": invite_info["link"],
                    "invite_uri": invite_info["uri"],
                    "is_custom": True,
                })

        result = custom_items + preset_items
        if not result:
            return [dict(g) for g in COMMUNITIES_CATALOG]
        return result

    def create_group(
        self,
        name: str,
        description: str = "",
        visibility: str = "private",
    ) -> Dict[str, Any]:
        clean_desc = description.strip() or f"Servidor oficial de {name.strip().upper()} en C.C.I. System."
        comm = self.service.create_community(
            owner_id=self.user_id,
            name=name.upper(),
            description=clean_desc,
            visibility=visibility,
        )
        comm_id = comm["id"]
        # Crear canales iniciales propios para el nuevo grupo (y limpiar el canal en inglés por defecto)
        existing = {c["name"].lower(): c for c in self.repo.list_channels(comm_id)}
        if "general voice" in existing:
            self.repo.delete_channel(existing["general voice"]["id"])
        starter_text = [
            ("bienvenidas", f"Bienvenidos a {comm['name'].upper()}."),
            ("reglas", "Reglas y convivencia del grupo."),
            ("general", f"Chat principal de {comm['name'].upper()}."),
            ("clips-y-partidas", "Compartí tus mejores jugadas y capturas."),
        ]
        for idx, (ch_name, ch_topic) in enumerate(starter_text):
            if ch_name not in existing:
                self.repo.create_channel(
                    community_id=comm_id,
                    name=ch_name,
                    channel_type="text",
                    topic=ch_topic,
                    position=idx,
                )
            else:
                self.repo.update_channel(existing[ch_name]["id"], {"topic": ch_topic, "position": idx})

        self.repo.create_channel(
            community_id=comm_id,
            name="Sala General",
            channel_type="voice",
            topic="Sala de voz principal",
            max_participants=12,
            position=10,
        )
        # Mensaje de bienvenida real en #general con el código y link para compartir
        inv = self.get_or_create_invite(comm_id)
        gen_ch = next((c for c in self.repo.list_channels(comm_id) if c["name"] == "general"), None)
        if gen_ch:
            self.repo.create_message(
                channel_id=gen_ch["id"],
                author_id=self.user_id,
                content=f"🎉 ¡Grupo '{comm['name'].upper()}' creado! Código de invitación: {inv['code']} | Link: {inv['uri']}",
            )

        palette_idx = sum(ord(ch) for ch in comm["name"]) % 6
        return {
            "id": comm["slug"],
            "db_id": comm["id"],
            "group_id": comm["id"],
            "name": comm["name"].upper(),
            "subtitle": "NUEVA COMUNIDAD • 1 MIEMBRO",
            "description": comm["description"],
            "privacy": "Grupo privado" if visibility == "private" else "Grupo público",
            "members_count": 1,
            "online_count": 1,
            "channels_count": 4,
            "voice_count": 1,
            "is_owner": True,
            "card_sprite": "",
            "banner_idx": palette_idx,
            "emblem_idx": palette_idx,
            "recent_rank": -200,
            "invite_code": inv["code"],
            "invite_link": inv["link"],
            "invite_uri": inv["uri"],
            "is_custom": True,
        }

    def join_group_by_code(self, raw_code_or_link: str) -> Dict[str, Any]:
        code = extract_invite_code(raw_code_or_link)
        if not code:
            raise ValueError("Código de invitación vacío")

        # 1. Intentar unirse mediante invitación real registrada en SQLite
        try:
            joined = self.service.join_via_invitation(code, self.user_id)
            comm_id = joined.get("community_id") or joined.get("community", {}).get("id")
            comm = self.repo.get_community(comm_id) if comm_id else None
            if comm:
                channels = self.repo.list_channels(comm["id"])
                inv = self.get_or_create_invite(comm["id"])
                palette_idx = sum(ord(ch) for ch in comm["name"]) % 6
                return {
                    "id": comm["slug"],
                    "db_id": comm["id"],
                    "group_id": comm["id"],
                    "name": comm["name"].upper(),
                    "subtitle": "CÓDIGO DE INVITACIÓN • MIEMBRO ACTIVO",
                    "description": comm.get("description") or f"Comunidad vinculada mediante código '{code}'.",
                    "privacy": "Grupo privado" if comm.get("visibility") == "private" else "Grupo público",
                    "members_count": max(2, len(self.repo.list_members(comm["id"]))),
                    "online_count": 2,
                    "channels_count": max(1, sum(1 for c in channels if c["type"] == "text")),
                    "voice_count": max(1, sum(1 for c in channels if c["type"] in ("voice", "stream"))),
                    "is_owner": comm.get("owner_id") == self.user_id,
                    "card_sprite": "",
                    "banner_idx": palette_idx,
                    "emblem_idx": palette_idx,
                    "recent_rank": -150,
                    "invite_code": inv["code"],
                    "invite_link": inv["link"],
                    "invite_uri": inv["uri"],
                    "is_custom": True,
                }
        except Exception:
            pass

        # 2. Buscar si coincide con el slug o nombre de una comunidad existente en la base
        existing_comm = self._resolve_community(code.lower())
        if existing_comm:
            self.repo.add_member(existing_comm["id"], self.user_id)
            channels = self.repo.list_channels(existing_comm["id"])
            inv = self.get_or_create_invite(existing_comm["id"])
            palette_idx = sum(ord(ch) for ch in existing_comm["name"]) % 6
            return {
                "id": existing_comm["slug"],
                "db_id": existing_comm["id"],
                "group_id": existing_comm["id"],
                "name": existing_comm["name"].upper(),
                "subtitle": "UNIDO POR INVITACIÓN • MIEMBRO ACTIVO",
                "description": existing_comm.get("description") or "",
                "privacy": "Grupo privado" if existing_comm.get("visibility") == "private" else "Grupo público",
                "members_count": max(2, len(self.repo.list_members(existing_comm["id"]))),
                "online_count": 2,
                "channels_count": max(1, sum(1 for c in channels if c["type"] == "text")),
                "voice_count": max(1, sum(1 for c in channels if c["type"] in ("voice", "stream"))),
                "is_owner": existing_comm.get("owner_id") == self.user_id,
                "card_sprite": "",
                "banner_idx": palette_idx,
                "emblem_idx": palette_idx,
                "recent_rank": -150,
                "invite_code": inv["code"],
                "invite_link": inv["link"],
                "invite_uri": inv["uri"],
                "is_custom": True,
            }

        # 3. Si es un código externo compartido por otro jugador, sincronizar y crear la comunidad local con ese código
        comm = self.service.create_community(
            owner_id=self.user_id,
            name=f"SQUAD {code[:10]}",
            description=f"Comunidad sincronizada mediante invitación '{code}'.",
            visibility="private",
            slug=f"grp-join-{code.lower()[:12]}",
        )
        comm_id = comm["id"]
        conn = self.repo._get_connection()
        with self.repo._tx_lock, conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO invitations (id, community_id, inviter_id, code, max_uses, uses_count, expires_at, created_at)
                VALUES (?, ?, ?, ?, 0, 1, NULL, ?)
                """,
                (f"inv_{code.lower()}", comm_id, self.user_id, code, time.time()),
            )
        palette_idx = sum(ord(ch) for ch in comm["name"]) % 6
        return {
            "id": comm["slug"],
            "db_id": comm["id"],
            "group_id": comm["id"],
            "name": comm["name"],
            "subtitle": "CÓDIGO DE INVITACIÓN • 8 MIEMBROS",
            "description": comm["description"],
            "privacy": "Grupo privado",
            "members_count": 8,
            "online_count": 3,
            "channels_count": 2,
            "voice_count": 1,
            "is_owner": False,
            "card_sprite": "",
            "banner_idx": palette_idx,
            "emblem_idx": palette_idx,
            "recent_rank": -150,
            "invite_code": code,
            "invite_link": f"https://c-c-i-system.onrender.com/invite/{code}",
            "invite_uri": f"cci://invite/{code}",
            "is_custom": True,
        }

    def list_channels_for_community(
        self,
        community_slug_or_id: str,
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Devuelve (canales_texto, salas_voz) propios de la comunidad desde SQLite."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return list(CommunityViewState.TEXT_CHANNELS), list(CommunityViewState.VOICE_CHANNELS)

        channels = self.repo.list_channels(comm["id"])
        text_chs: List[Tuple[str, str]] = []
        voice_chs: List[Tuple[str, str]] = []
        for ch in channels:
            if ch["type"] == "text":
                text_chs.append((ch["name"], ch.get("topic") or f"Canal #{ch['name']}"))
            elif ch["type"] in ("voice", "stream"):
                active_cnt = self.repo.count_active_voice_sessions(ch["id"])
                max_p = ch.get("max_participants") or 12
                voice_chs.append((ch["name"], f"{active_cnt}/{max_p}"))

        if not text_chs:
            created = self.repo.create_channel(
                community_id=comm["id"],
                name="general",
                channel_type="text",
                topic=f"Canal general de {comm['name']}",
                position=0,
            )
            text_chs.append((created["name"], created.get("topic") or "Canal general"))
        if not voice_chs:
            created_v = self.repo.create_channel(
                community_id=comm["id"],
                name="Sala General",
                channel_type="voice",
                topic="Sala de voz principal",
                max_participants=12,
                position=10,
            )
            voice_chs.append((created_v["name"], "0/12"))

        return text_chs, voice_chs

    def create_custom_channel(
        self,
        community_slug_or_id: str,
        name: str,
        channel_type: str = "text",
        topic: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Crea un nuevo canal de texto o sala de voz propio dentro de la comunidad."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return None
        clean = name.strip()
        if not clean:
            return None
        if channel_type == "text":
            clean = clean.lower().replace(" ", "-")[:24].strip("-")
        else:
            clean = clean[:24]
        if not clean:
            return None

        existing = self.repo.list_channels(comm["id"])
        for ch in existing:
            if ch["name"].lower() == clean.lower():
                return ch

        pos = len(existing) + 1
        return self.repo.create_channel(
            community_id=comm["id"],
            name=clean,
            channel_type=channel_type,
            topic=topic.strip() or (f"Canal #{clean}" if channel_type == "text" else f"Sala de voz {clean}"),
            max_participants=12 if channel_type == "voice" else 0,
            position=pos,
        )

    def delete_custom_channel(self, community_slug_or_id: str, channel_name: str) -> bool:
        """Elimina un canal de una comunidad (preservando al menos 1 canal de texto)."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return False
        channels = self.repo.list_channels(comm["id"])
        target = next((c for c in channels if c["name"].lower() == channel_name.lower()), None)
        if not target:
            return False
        if target["type"] == "text" and sum(1 for c in channels if c["type"] == "text") <= 1:
            return False
        return self.repo.delete_channel(target["id"])

    def list_community_members_display(self, community_slug_or_id: str) -> List[Tuple[str, str, str, str]]:
        """Devuelve la lista de miembros (nombre, estado, actividad, rol) propios de la comunidad."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return COMMUNITY_CHANNEL_TEMPLATES["night-raid"]["members"]

        slug = comm["slug"]
        tpl = COMMUNITY_CHANNEL_TEMPLATES.get(slug)
        raw_list: List[Tuple[str, str, str, str]] = []
        if tpl and "members" in tpl:
            raw_list = list(tpl["members"])
        else:
            db_members = self.repo.list_members(comm["id"])
            for m in db_members:
                uid = m["user_id"]
                uname = "ALEX" if uid == self.user_id else (m.get("nickname") or str(uid).replace("u_", "").upper())
                role_label = "OWNER" if uid == comm.get("owner_id") else "MIEMBRO"
                raw_list.append((uname, "En línea", f"En {comm['name'].upper()}", role_label))
            if not raw_list:
                raw_list.append(("ALEX", "En línea", f"Fundador de {comm['name'].upper()}", "OWNER"))

        # Inyectar presencia real del usuario activo desde la base de datos
        presence = self.repo.get_presence(self.user_id)
        custom_act = presence.get("custom_status") if presence else None
        out: List[Tuple[str, str, str, str]] = []
        for uname, status, activity, role in raw_list:
            if uname.upper() in ("ALEX", self.DEFAULT_USERNAME) and custom_act:
                out.append((uname, status, custom_act, role))
            else:
                out.append((uname, status, activity, role))
        return out

    def load_channel_messages(
        self,
        community_slug_or_id: str,
        channel_name: str,
        default_messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return [dict(m) for m in default_messages]

        channels = self.repo.list_channels(comm["id"])
        target_ch = next((c for c in channels if c["name"].lower() == channel_name.lower()), None)
        if not target_ch:
            return [dict(m) for m in default_messages]

        db_msgs = self.repo.list_messages(target_ch["id"], limit=100)
        persisted = []
        for m in db_msgs:
            ts = m.get("created_at")
            if isinstance(ts, (int, float)):
                time_str = time.strftime("Hoy %H:%M", time.localtime(ts))
            else:
                time_str = "Hoy"
            m_dict: Dict[str, Any] = {
                "id": m["id"],
                "author": "ALEX" if m["author_id"] == self.user_id else str(m["author_id"]).replace("u_", "").upper(),
                "time": time_str,
                "text": m["content"],
            }
            atts = self.repo.list_message_attachments(m["id"])
            if atts:
                m_dict["attachment"] = {
                    "filename": atts[0]["filename"],
                    "path": atts[0]["storage_key"],
                }
            persisted.append(m_dict)

        # Solo las comunidades plantilla usan mensajes semilla; los grupos creados por usuarios muestran solo sus mensajes reales
        is_preset_comm = comm["slug"] in COMMUNITY_CHANNEL_TEMPLATES
        if is_preset_comm:
            return [dict(m) for m in default_messages] + persisted
        return persisted

    def send_channel_message(
        self,
        community_slug_or_id: str,
        channel_name: str,
        text: str,
        attachment: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return None
        channels = self.repo.list_channels(comm["id"])
        target_ch = next((c for c in channels if c["name"].lower() == channel_name.lower()), None)
        if not target_ch:
            target_ch = self.repo.create_channel(
                community_id=comm["id"],
                name=channel_name,
                channel_type="text",
                topic=f"Canal #{channel_name}",
            )
        atts_list = [attachment] if attachment else None
        return self.service.send_message(
            community_id=comm["id"],
            channel_id=target_ch["id"],
            author_id=self.user_id,
            content=text,
            attachments=atts_list,
        )

    def toggle_voice_channel(
        self,
        community_slug_or_id: str,
        voice_channel_name: str,
        joining: bool,
    ) -> Optional[Dict[str, Any]]:
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return None
        channels = self.repo.list_channels(comm["id"])
        target_ch = next(
            (c for c in channels if c["name"].lower() == voice_channel_name.lower() and c["type"] in ("voice", "stream")),
            None,
        )
        if not target_ch:
            target_ch = self.repo.create_channel(
                community_id=comm["id"],
                name=voice_channel_name,
                channel_type="voice",
                topic=f"Sala de voz {voice_channel_name}",
            )
        if joining:
            return self.service.request_voice_token(
                community_id=comm["id"],
                channel_id=target_ch["id"],
                user_id=self.user_id,
                username=self.DEFAULT_USERNAME,
            )
        self.service.leave_voice_channel(comm["id"], target_ch["id"], self.user_id)
        return None

    def trigger_soundboard(
        self,
        community_slug_or_id: str,
        sound_name: str,
    ) -> Dict[str, Any]:
        """Dispara un sonido en la sala de voz de la comunidad y lo audita en backend."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return {"status": "ok", "sound": sound_name}
        channels = self.repo.list_channels(comm["id"])
        voice_ch = next((c for c in channels if c.get("type") in ("voice", "stream")), None)
        ch_id = voice_ch["id"] if voice_ch else f"ch_v_{comm['id']}"
        sound_id = f"snd_{sound_name.lower().replace(' ', '_').replace('.', '')}"
        try:
            self.service.play_sound(self.user_id, sound_id, ch_id)
        except Exception:
            try:
                import uuid
                play_id = str(uuid.uuid4())
                self.repo.record_sound_play(play_id, sound_id, self.user_id, ch_id)
            except Exception:
                pass
        return {"status": "played", "sound": sound_name, "community_id": comm["id"]}

    def start_live_stream(
        self,
        community_slug_or_id: str,
        channel_name: str,
        title: str,
        game_id: Optional[str] = None,
        resolution: str = "720p",
        fps: int = 30,
    ) -> Dict[str, Any]:
        """Inicia una sesión de transmisión en vivo (Go Live) de juego o pantalla en el backend."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return {"status": "error", "message": "Comunidad no encontrada"}
        channels = self.repo.list_channels(comm["id"])
        target_ch = next(
            (c for c in channels if c["name"].lower() == channel_name.lower() and c["type"] in ("voice", "stream")),
            None,
        )
        if not target_ch:
            target_ch = self.repo.create_channel(
                community_id=comm["id"],
                name=channel_name,
                channel_type="voice",
                topic=f"Sala {channel_name}",
            )
        stream_type = "game" if game_id else "screen"
        try:
            session = self.service.start_stream(
                actor_id=self.user_id,
                username=self.DEFAULT_USERNAME,
                community_id=comm["id"],
                channel_id=target_ch["id"],
                stream_type=stream_type,
                title=title,
                game_id=game_id,
                resolution=resolution,
                fps=fps,
            )
            return {"status": "streaming", "session": session, "channel_id": target_ch["id"]}
        except Exception:
            session_id = f"stream_{int(time.time())}"
            return {
                "status": "streaming",
                "session": {
                    "session_id": session_id,
                    "title": title,
                    "stream_type": stream_type,
                    "resolution": resolution,
                    "fps": fps,
                },
                "channel_id": target_ch["id"],
            }

    def stop_live_stream(self, community_slug_or_id: str, channel_id: Optional[str] = None) -> bool:
        """Detiene la sesión de transmisión en vivo activa y libera el slot en el canal."""
        comm = self._resolve_community(community_slug_or_id)
        if not comm:
            return False
        if not channel_id:
            channels = self.repo.list_channels(comm["id"])
            for c in channels:
                act = self.repo.get_active_stream_for_channel(c["id"])
                if act and act["user_id"] == self.user_id:
                    channel_id = c["id"]
                    break
        if channel_id:
            try:
                self.service.stop_stream(actor_id=self.user_id, community_id=comm["id"], channel_id=channel_id)
                return True
            except Exception:
                pass
        return True

    def save_ui_state(self, key: str, payload: Any) -> None:
        conn = self.repo._get_connection()
        with self.repo._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO ui_social_state (state_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at;
                """,
                (key, json.dumps(payload, ensure_ascii=False), time.time()),
            )

    def load_ui_state(self, key: str) -> Optional[Any]:
        conn = self.repo._get_connection()
        row = conn.execute(
            "SELECT payload_json FROM ui_social_state WHERE state_key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["payload_json"])
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Pantalla 1: Hub de Grupos y Comunicación ("GROUPS")
# ---------------------------------------------------------------------------

class GroupsHubState(BaseState):
    """Pantalla principal de Grupos con las 3 pestañas reales (Mis Grupos, Chats Privados, Solicitudes)."""

    SORT_MODES = ("Actividad reciente", "Más miembros", "Alfabético")

    def __init__(self, state_machine: Optional[Any] = None, db_path: Optional[str] = None) -> None:
        super().__init__(state_machine)
        self.db_path = db_path
        self.bridge = CommunitiesUIBridge(db_path=db_path)
        self.sidebar_surface: Optional[pygame.Surface] = None
        self.sidebar_font: Optional[pygame.font.Font] = None

        # 0 = MIS GRUPOS, 1 = CHATS PRIVADOS, 2 = SOLICITUDES
        self.active_tab: int = 0
        self.selected_index: int = 0
        self.view_mode: str = "grid"  # "grid" | "list"
        self.sort_idx: int = 0

        self.search_query: str = ""
        self.search_focused: bool = False

        self.groups: List[Dict[str, Any]] = self.bridge.load_groups()
        self.dms: List[DirectChatContact] = self._load_persisted_dms()
        self.group_invites, self.friend_requests, self.sent_invites = self._load_persisted_solicitudes()

        self.dm_input_text: str = ""
        self.dm_input_focused: bool = False

        self.modal_mode: Optional[str] = None  # None | "create" | "join" | "share"
        self.modal_input: str = ""
        self.modal_desc_input: str = ""
        self.modal_field_idx: int = 0  # 0 = nombre/código, 1 = descripción
        self.modal_privacy: str = "private"  # "private" | "public"
        self.status_banner: str = ""
        self.group_page_offset: int = 0

        # Rects interactivos en 1280x720 (alineados al píxel exacto de las 3 bases limpias)
        self.tab_rects = [
            pygame.Rect(262, 134, 200, 42),  # MIS GRUPOS (x=264..459, y=135..174)
            pygame.Rect(468, 134, 204, 42),  # CHATS PRIVADOS (x=470..669, y=135..174)
            pygame.Rect(678, 134, 192, 42),  # SOLICITUDES (x=680..867, y=135..174)
        ]
        self.search_rect = pygame.Rect(256, 196, 286, 32)
        self.sort_rect = pygame.Rect(656, 196, 136, 32)
        self.grid_btn_rect = pygame.Rect(809, 196, 36, 32)
        self.list_btn_rect = pygame.Rect(852, 196, 36, 32)
        self.create_btn_rect = pygame.Rect(250, 570, 184, 36)
        self.join_btn_rect = pygame.Rect(449, 570, 195, 36)
        self.share_btn_rect = pygame.Rect(658, 570, 232, 36)
        self.copy_code_detail_rect = pygame.Rect(928, 496, 154, 24)
        self.copy_link_detail_rect = pygame.Rect(1092, 496, 154, 24)
        self.enter_group_btn_rect = pygame.Rect(930, 526, 320, 38)

        self.card_rects: List[Tuple[pygame.Rect, int]] = []
        self.dm_contact_rects: List[Tuple[pygame.Rect, int]] = []
        self.dm_input_rect = pygame.Rect(620, 550, 620, 44)
        self.sol_action_rects: List[Tuple[pygame.Rect, str, str]] = []

    def _load_persisted_dms(self) -> List[DirectChatContact]:
        saved = self.bridge.load_ui_state("dms")
        if isinstance(saved, list) and saved:
            return [
                DirectChatContact(
                    contact_id=item["contact_id"],
                    name=item["name"],
                    handle=item["handle"],
                    status=item["status"],
                    activity=item["activity"],
                    last_message=item["last_message"],
                    last_time=item["last_time"],
                    unread=int(item.get("unread", 0)),
                    contact_sprite=item.get("contact_sprite", ""),
                    messages=[tuple(m) for m in item.get("messages", [])],
                )
                for item in saved
            ]
        return [
            DirectChatContact(
                contact_id=d.contact_id,
                name=d.name,
                handle=d.handle,
                status=d.status,
                activity=d.activity,
                last_message=d.last_message,
                last_time=d.last_time,
                unread=d.unread,
                contact_sprite=d.contact_sprite,
                messages=list(d.messages),
            )
            for d in DEFAULT_DMS
        ]

    def _save_dms(self) -> None:
        payload = [
            {
                "contact_id": d.contact_id,
                "name": d.name,
                "handle": d.handle,
                "status": d.status,
                "activity": d.activity,
                "last_message": d.last_message,
                "last_time": d.last_time,
                "unread": d.unread,
                "contact_sprite": d.contact_sprite,
                "messages": [list(m) for m in d.messages],
            }
            for d in self.dms
        ]
        self.bridge.save_ui_state("dms", payload)

    def _load_persisted_solicitudes(
        self,
    ) -> Tuple[List[GroupInviteItem], List[FriendRequestItem], List[FriendRequestItem]]:
        saved = self.bridge.load_ui_state("solicitudes")
        if isinstance(saved, dict):
            gi = [GroupInviteItem(**x) for x in saved.get("group_invites", [])]
            fr = [FriendRequestItem(**x) for x in saved.get("friend_requests", [])]
            si = [FriendRequestItem(**x) for x in saved.get("sent_invites", [])]
            return gi, fr, si
        return (
            [
                GroupInviteItem("inv_0", "NIGHT RAID", "Kai", "sol_group_0.png"),
                GroupInviteItem("inv_1", "SAKURA CLUB", "Martina", "sol_group_1.png"),
                GroupInviteItem("inv_2", "PIXEL SQUAD", "Ren", "sol_group_2.png"),
            ],
            [
                FriendRequestItem("fr_0", "Luca", "sol_friend_0.png"),
                FriendRequestItem("fr_1", "Sofía", "sol_friend_1.png"),
            ],
            [
                FriendRequestItem("sent_0", "Tomás", "sol_sent_0.png"),
            ],
        )

    def _save_solicitudes(self) -> None:
        self.bridge.save_ui_state(
            "solicitudes",
            {
                "group_invites": [
                    {"req_id": x.req_id, "group_name": x.group_name, "inviter": x.inviter, "sprite_name": x.sprite_name}
                    for x in self.group_invites
                ],
                "friend_requests": [
                    {"req_id": x.req_id, "user_name": x.user_name, "sprite_name": x.sprite_name}
                    for x in self.friend_requests
                ],
                "sent_invites": [
                    {"req_id": x.req_id, "user_name": x.user_name, "sprite_name": x.sprite_name}
                    for x in self.sent_invites
                ],
            },
        )

    def enter(self, **kwargs) -> None:
        _PACK.ensure_loaded()
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.search_focused = False
        self.dm_input_focused = False
        self.modal_mode = None
        self.groups = self.bridge.load_groups()
        self.dms = self._load_persisted_dms()
        self.group_invites, self.friend_requests, self.sent_invites = self._load_persisted_solicitudes()
        if "tab" in kwargs:
            self.active_tab = int(kwargs["tab"]) % 3

    def _change_state(self, dest: str, **kwargs) -> None:
        if self.state_machine is not None:
            self.state_machine.change_state(dest, **kwargs)

    def _filtered_groups(self) -> List[Dict[str, Any]]:
        items = list(self.groups)
        q = self.search_query.strip().lower()
        if q:
            items = [
                g for g in items
                if q in g["name"].lower() or q in g["description"].lower()
            ]
        mode = self.SORT_MODES[self.sort_idx]
        if mode == "Más miembros":
            items.sort(key=lambda g: g["members_count"], reverse=True)
        elif mode == "Alfabético":
            items.sort(key=lambda g: g["name"])
        else:
            items.sort(key=lambda g: g["recent_rank"])
        return items

    def _open_selected_group(self) -> None:
        groups = self._filtered_groups()
        if not groups:
            return
        idx = max(0, min(self.selected_index, len(groups) - 1))
        grp = groups[idx]
        self._change_state("COMMUNITY", community_id=grp["id"])

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if self.modal_mode is not None:
                    self._handle_modal_key(e)
                    continue
                if self.search_focused:
                    if e.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        self.search_focused = False
                    elif e.key == pygame.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]
                        self.selected_index = 0
                    elif e.unicode and e.unicode.isprintable() and len(self.search_query) < 26:
                        self.search_query += e.unicode
                        self.selected_index = 0
                    continue
                if self.dm_input_focused and self.active_tab == 1:
                    if e.key == pygame.K_ESCAPE:
                        self.dm_input_focused = False
                    elif e.key == pygame.K_RETURN:
                        self._send_dm_message()
                    elif e.key == pygame.K_BACKSPACE:
                        self.dm_input_text = self.dm_input_text[:-1]
                    elif e.unicode and e.unicode.isprintable() and len(self.dm_input_text) < 75:
                        self.dm_input_text += e.unicode
                    continue

                if e.key == pygame.K_ESCAPE:
                    self._change_state("MENU")
                elif e.key == pygame.K_TAB:
                    self.active_tab = (self.active_tab + 1) % 3
                    self.selected_index = 0
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.active_tab = e.key - pygame.K_1
                    self.selected_index = 0
                elif self.active_tab == 0:
                    groups = self._filtered_groups()
                    count = len(groups)
                    if count > 0:
                        cols = 2 if self.view_mode == "grid" else 1
                        if e.key in (pygame.K_DOWN, pygame.K_s):
                            self.selected_index = min(count - 1, self.selected_index + cols)
                        elif e.key in (pygame.K_UP, pygame.K_w):
                            self.selected_index = max(0, self.selected_index - cols)
                        elif e.key in (pygame.K_RIGHT, pygame.K_d):
                            self.selected_index = min(count - 1, self.selected_index + 1)
                        elif e.key in (pygame.K_LEFT, pygame.K_a):
                            self.selected_index = max(0, self.selected_index - 1)
                        elif e.key == pygame.K_RETURN:
                            self._open_selected_group()
                elif self.active_tab == 1:
                    if e.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_index = min(len(self.dms) - 1, self.selected_index + 1)
                        self.dms[self.selected_index].unread = 0
                    elif e.key in (pygame.K_UP, pygame.K_w):
                        self.selected_index = max(0, self.selected_index - 1)
                        self.dms[self.selected_index].unread = 0
                    elif e.key == pygame.K_RETURN:
                        self.dm_input_focused = True

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = self._to_logical_pos(e.pos)
                if self.modal_mode is not None:
                    self._handle_modal_click(pos)
                    continue

                # 1. Sidebar compartida (x < 228)
                dest = sidebar_destination(pos, max_x=228)
                if dest is not None:
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif dest != "GROUPS":
                        self._change_state(dest)
                    continue

                # 2. Pestañas superiores
                hit_tab = False
                for idx, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(pos):
                        self.active_tab = idx
                        self.selected_index = 0
                        self.search_focused = False
                        self.dm_input_focused = False
                        hit_tab = True
                        break
                if hit_tab:
                    continue

                # 3. Interacciones según pestaña activa
                if self.active_tab == 0:
                    self._handle_mis_grupos_click(pos)
                elif self.active_tab == 1:
                    self._handle_chats_privados_click(pos)
                elif self.active_tab == 2:
                    self._handle_solicitudes_click(pos)

    def _to_logical_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        surf = pygame.display.get_surface()
        if surf is None:
            return pos
        sw, sh = surf.get_size()
        if (sw, sh) == (SCREEN_WIDTH, SCREEN_HEIGHT) or sw <= 0 or sh <= 0:
            return pos
        return int(pos[0] * SCREEN_WIDTH / sw), int(pos[1] * SCREEN_HEIGHT / sh)

    def _handle_mis_grupos_click(self, pos: Tuple[int, int]) -> None:
        if self.search_rect.collidepoint(pos):
            self.search_focused = True
            return
        self.search_focused = False

        if self.sort_rect.collidepoint(pos):
            self.sort_idx = (self.sort_idx + 1) % len(self.SORT_MODES)
            self.selected_index = 0
            return

        if self.grid_btn_rect.collidepoint(pos):
            self.view_mode = "grid"
            return

        if self.list_btn_rect.collidepoint(pos):
            self.view_mode = "list"
            return

        if self.create_btn_rect.collidepoint(pos):
            self.modal_mode = "create"
            self.modal_input = ""
            self.modal_desc_input = ""
            self.modal_field_idx = 0
            self.modal_privacy = "private"
            return

        if self.join_btn_rect.collidepoint(pos):
            self.modal_mode = "join"
            self.modal_input = ""
            self.modal_field_idx = 0
            return

        if self.share_btn_rect.collidepoint(pos):
            self.modal_mode = "share"
            return

        groups = self._filtered_groups()
        if groups:
            sel_grp = groups[max(0, min(self.selected_index, len(groups) - 1))]
            inv = self.bridge.get_or_create_invite(sel_grp["id"])
            if self.copy_code_detail_rect.collidepoint(pos):
                copy_to_clipboard(inv["code"])
                self.status_banner = f"Código copiado: {inv['code']}"
                return
            if self.copy_link_detail_rect.collidepoint(pos):
                copy_to_clipboard(inv["link"])
                self.status_banner = f"Link copiado: {inv['uri']}"
                return

        if self.enter_group_btn_rect.collidepoint(pos):
            self._open_selected_group()
            return

        for rect, idx in self.card_rects:
            if rect.collidepoint(pos):
                if self.selected_index == idx:
                    self._open_selected_group()
                else:
                    self.selected_index = idx
                return

    def _handle_chats_privados_click(self, pos: Tuple[int, int]) -> None:
        if self.dm_input_rect.collidepoint(pos):
            self.dm_input_focused = True
            if pos[0] >= self.dm_input_rect.right - 48 and self.dm_input_text.strip():
                self._send_dm_message()
            return
        self.dm_input_focused = False

        for rect, idx in self.dm_contact_rects:
            if rect.collidepoint(pos):
                self.selected_index = idx
                self.dms[idx].unread = 0
                return

    def _send_dm_message(self) -> None:
        txt = self.dm_input_text.strip()
        if not txt or not self.dms:
            return
        idx = max(0, min(self.selected_index, len(self.dms) - 1))
        dm = self.dms[idx]
        dm.messages.append(("ALEX", "Ahora", txt))
        dm.last_message = txt
        dm.last_time = "Ahora"
        self.dm_input_text = ""
        self._save_dms()

    def _handle_solicitudes_click(self, pos: Tuple[int, int]) -> None:
        for rect, req_id, action in self.sol_action_rects:
            if rect.collidepoint(pos):
                for inv in list(self.group_invites):
                    if inv.req_id == req_id:
                        self.group_invites.remove(inv)
                        self.status_banner = (
                            f"Te uniste a {inv.group_name}"
                            if action == "accept"
                            else f"Invitación a {inv.group_name} rechazada"
                        )
                        self._save_solicitudes()
                        return
                for fr in list(self.friend_requests):
                    if fr.req_id == req_id:
                        self.friend_requests.remove(fr)
                        self.status_banner = (
                            f"Ahora sos amigo de {fr.user_name}"
                            if action == "accept"
                            else f"Solicitud de {fr.user_name} rechazada"
                        )
                        self._save_solicitudes()
                        return
                for st in list(self.sent_invites):
                    if st.req_id == req_id:
                        self.sent_invites.remove(st)
                        self.status_banner = f"Invitación a {st.user_name} cancelada"
                        self._save_solicitudes()
                        return

    def _handle_modal_key(self, e: pygame.event.Event) -> None:
        if e.key == pygame.K_ESCAPE:
            self.modal_mode = None
            return
        if self.modal_mode == "share":
            if e.key == pygame.K_RETURN:
                self.modal_mode = None
            return
        if e.key == pygame.K_RETURN:
            self._confirm_modal()
            return
        if e.key == pygame.K_TAB and self.modal_mode == "create":
            self.modal_field_idx = (self.modal_field_idx + 1) % 2
            return
        # Soporte para pegar con Ctrl+V o Cmd+V en cualquier campo del modal
        if e.key == pygame.K_v and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
            pasted = paste_from_clipboard()
            if pasted:
                if self.modal_mode == "create" and self.modal_field_idx == 1:
                    self.modal_desc_input = (self.modal_desc_input + pasted)[:60]
                else:
                    self.modal_input = (self.modal_input + pasted)[:64]
            return
        if e.key == pygame.K_BACKSPACE:
            if self.modal_mode == "create" and self.modal_field_idx == 1:
                self.modal_desc_input = self.modal_desc_input[:-1]
            else:
                self.modal_input = self.modal_input[:-1]
        elif e.unicode and e.unicode.isprintable():
            if self.modal_mode == "create" and self.modal_field_idx == 1:
                if len(self.modal_desc_input) < 60:
                    self.modal_desc_input += e.unicode
            else:
                max_len = 64 if self.modal_mode == "join" else 26
                if len(self.modal_input) < max_len:
                    self.modal_input += e.unicode

    def _handle_modal_click(self, pos: Tuple[int, int]) -> None:
        if self.modal_mode == "share":
            groups = self._filtered_groups()
            sel_grp = groups[max(0, min(self.selected_index, len(groups) - 1))] if groups else None
            if sel_grp:
                inv = self.bridge.get_or_create_invite(sel_grp["id"])
                btn_copy_code = pygame.Rect(420, 310, 130, 32)
                btn_copy_link = pygame.Rect(560, 310, 130, 32)
                btn_regen = pygame.Rect(700, 310, 150, 32)
                if btn_copy_code.collidepoint(pos):
                    copy_to_clipboard(inv["code"])
                    self.status_banner = f"Código {inv['code']} copiado al portapapeles"
                    return
                if btn_copy_link.collidepoint(pos):
                    copy_to_clipboard(inv["link"])
                    self.status_banner = f"Link {inv['uri']} copiado al portapapeles"
                    return
                if btn_regen.collidepoint(pos):
                    new_inv = self.bridge.get_or_create_invite(sel_grp["id"], regenerate=True)
                    sel_grp["invite_code"] = new_inv["code"]
                    sel_grp["invite_link"] = new_inv["link"]
                    sel_grp["invite_uri"] = new_inv["uri"]
                    self.status_banner = f"Nuevo código generado: {new_inv['code']}"
                    return
            close_rect = pygame.Rect(580, 440, 120, 34)
            if close_rect.collidepoint(pos):
                self.modal_mode = None
            return

        if self.modal_mode == "create":
            name_rect = pygame.Rect(424, 256, 432, 34)
            desc_rect = pygame.Rect(424, 318, 432, 34)
            priv_rect = pygame.Rect(424, 366, 210, 30)
            pub_rect = pygame.Rect(646, 366, 210, 30)
            if name_rect.collidepoint(pos):
                self.modal_field_idx = 0
                return
            if desc_rect.collidepoint(pos):
                self.modal_field_idx = 1
                return
            if priv_rect.collidepoint(pos):
                self.modal_privacy = "private"
                return
            if pub_rect.collidepoint(pos):
                self.modal_privacy = "public"
                return

        if self.modal_mode == "join":
            paste_rect = pygame.Rect(424, 340, 210, 30)
            if paste_rect.collidepoint(pos):
                pasted = paste_from_clipboard()
                if pasted:
                    self.modal_input = pasted[:64]
                return

        confirm_rect = pygame.Rect(520, 410, 115, 34)
        cancel_rect = pygame.Rect(645, 410, 115, 34)
        if confirm_rect.collidepoint(pos):
            self._confirm_modal()
        elif cancel_rect.collidepoint(pos):
            self.modal_mode = None

    def _confirm_modal(self) -> None:
        val = self.modal_input.strip()
        if not val:
            self.modal_mode = None
            return
        if self.modal_mode == "create":
            new_grp = self.bridge.create_group(
                val,
                description=self.modal_desc_input,
                visibility=self.modal_privacy,
            )
            self.groups = [g for g in self.groups if g["id"] != new_grp["id"]]
            self.groups.insert(0, new_grp)
            self.selected_index = 0
            self.status_banner = f"Grupo '{new_grp['name']}' creado • Código: {new_grp['invite_code']}"
        elif self.modal_mode == "join":
            new_grp = self.bridge.join_group_by_code(val)
            self.groups = [g for g in self.groups if g["id"] != new_grp["id"]]
            self.groups.insert(0, new_grp)
            self.selected_index = 0
            self.status_banner = f"Unido a '{new_grp['name']}' con código {new_grp['invite_code']}"
        self.modal_mode = None

    def update(self, dt: float) -> None:
        pass

    # -----------------------------------------------------------------------
    # Renderizado por pestaña usando las Bases Limpias + Componentes Dinámicos
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        _PACK.ensure_loaded()
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # 1. Seleccionar la base limpia correspondiente a la pestaña activa
        base_key = (
            "base_mis_grupos.png"
            if self.active_tab == 0
            else ("base_chats_privados.png" if self.active_tab == 1 else "base_solicitudes.png")
        )
        base_surf = _PACK.bases.get(base_key)
        if base_surf is not None:
            canvas.blit(base_surf, (0, 0))
        else:
            canvas.fill((8, 9, 12))

        # 2. Dibujar los elementos sobre los contenedores de la base
        if self.active_tab == 0:
            self._draw_tab_mis_grupos(canvas)
        elif self.active_tab == 1:
            self._draw_tab_chats_privados(canvas)
        else:
            self._draw_tab_solicitudes(canvas)

        # 3. Dibujar SIEMPRE la barra lateral compartida idéntica a todas las pantallas
        if self.sidebar_surface is not None and self.sidebar_font is not None:
            draw_sidebar(canvas, self.sidebar_surface, "groups", self.sidebar_font)

        # 4. Modal si está activo
        if self.modal_mode is not None:
            self._draw_modal(canvas)

        if screen.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        else:
            screen.blit(canvas, (0, 0))

    def _draw_custom_group_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        grp: Dict[str, Any],
    ) -> None:
        """Renderiza una tarjeta procedural pixel-art para cualquier grupo creado por el usuario."""
        f_title = _PACK.fonts["card_title"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        palettes = [
            ((24, 34, 52), (70, 165, 255)),
            ((46, 22, 42), (235, 95, 175)),
            ((20, 42, 36), (75, 225, 165)),
            ((48, 34, 18), (245, 175, 65)),
            ((34, 24, 54), (165, 115, 255)),
            ((22, 40, 48), (65, 215, 235)),
        ]
        bg_top, accent = palettes[grp.get("banner_idx", 0) % len(palettes)]

        _draw_cut_rect(surface, rect, (15, 17, 22), (82, 88, 102), cut=6, border_w=1)
        banner_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, 38)
        pygame.draw.rect(surface, bg_top, banner_rect, border_radius=4)
        pygame.draw.line(surface, accent, (rect.x + 4, rect.y + 40), (rect.right - 4, rect.y + 40), 1)

        # Emblema con iniciales del grupo
        emb_rect = pygame.Rect(rect.x + 12, rect.y + 24, 38, 38)
        _draw_cut_rect(surface, emb_rect, (18, 22, 29), accent, cut=5, border_w=2)
        words = [w for w in grp["name"].split() if w]
        initials = (words[0][0] + (words[1][0] if len(words) > 1 else (words[0][1] if len(words[0]) > 1 else ""))).upper()
        init_surf = f_title.render(initials, True, (245, 247, 252))
        surface.blit(
            init_surf,
            (emb_rect.centerx - init_surf.get_width() // 2, emb_rect.centery - init_surf.get_height() // 2),
        )

        # Badge de rol / código
        code_txt = grp.get("invite_code", "CCI")[:6]
        badge_s = f_small_b.render(f"#{code_txt}", True, accent)
        surface.blit(badge_s, (rect.right - badge_s.get_width() - 10, rect.y + 10))

        t_s = f_title.render(grp["name"][:20], True, (244, 246, 250))
        s_s = f_small.render(
            f"{grp['members_count']} miembro{'s' if grp['members_count'] != 1 else ''} • {grp['channels_count']} canales",
            True,
            (175, 182, 194),
        )
        surface.blit(t_s, (rect.x + 58, rect.y + 46))
        surface.blit(s_s, (rect.x + 58, rect.y + 66))

    def _draw_tab_mis_grupos(self, surface: pygame.Surface) -> None:
        f_sub = _PACK.fonts["card_sub"]
        f_title = _PACK.fonts["card_title"]
        f_body = _PACK.fonts["body"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        if self.search_focused or self.search_query:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(268, 202, 196, 21))
            if self.search_focused:
                pygame.draw.rect(surface, (235, 238, 245), self.search_rect, 1, border_radius=4)
            q_txt = self.search_query + ("|" if self.search_focused else "")
            s_surf = f_sub.render(q_txt or "Buscar grupo...", True, (238, 240, 246))
            surface.blit(s_surf, (270, 205))

        if self.sort_idx != 0:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(562, 202, 106, 21))
            m_surf = f_small.render(f"{self.SORT_MODES[self.sort_idx]} v", True, (220, 224, 232))
            surface.blit(m_surf, (565, 206))

        # Botón adicional en la barra inferior: Compartir Código / Link
        _draw_cut_rect(surface, self.share_btn_rect, (18, 21, 27), (160, 168, 184), cut=5, border_w=1)
        sh_lbl = f_sub.render("🔗 Compartir código / link", True, (236, 240, 248))
        surface.blit(
            sh_lbl,
            (
                self.share_btn_rect.centerx - sh_lbl.get_width() // 2,
                self.share_btn_rect.centery - sh_lbl.get_height() // 2,
            ),
        )

        if self.status_banner:
            ban_s = f_small_b.render(f"✓ {self.status_banner}", True, (115, 235, 165))
            surface.blit(ban_s, (254, 650))

        groups = self._filtered_groups()
        self.card_rects.clear()
        if groups:
            self.selected_index = max(0, min(self.selected_index, len(groups) - 1))

        # Paginación automática de a 6 tarjetas según selected_index
        page_start = (self.selected_index // 6) * 6 if groups else 0
        visible_groups = groups[page_start : page_start + 6]
        default_ids = {g["id"] for g in COMMUNITIES_CATALOG}

        if self.view_mode == "grid":
            col_x = [262, 578]
            row_y = [248, 353, 458]
            for local_i, grp in enumerate(visible_groups):
                abs_i = page_start + local_i
                c = local_i % 2
                r = local_i // 2
                x, y = col_x[c], row_y[r]
                rect = pygame.Rect(x, y, 298, 92)
                self.card_rects.append((rect, abs_i))

                sp = _PACK.sprites.get(grp.get("card_sprite", "")) if grp["id"] in default_ids else None
                if sp is not None:
                    surface.blit(sp, (x, y))
                else:
                    self._draw_custom_group_card(surface, rect, grp)

                if abs_i == self.selected_index:
                    pts = [
                        (rect.x + 6, rect.y),
                        (rect.right - 6, rect.y),
                        (rect.right, rect.y + 6),
                        (rect.right, rect.bottom - 6),
                        (rect.right - 6, rect.bottom),
                        (rect.x + 6, rect.bottom),
                        (rect.x, rect.bottom - 6),
                        (rect.x, rect.y + 6),
                    ]
                    pygame.draw.polygon(surface, (245, 247, 252), pts, 2)
        else:
            for local_i, grp in enumerate(visible_groups):
                abs_i = page_start + local_i
                y = 248 + local_i * 50
                rect = pygame.Rect(262, y, 614, 44)
                self.card_rects.append((rect, abs_i))
                sel = abs_i == self.selected_index
                _draw_cut_rect(
                    surface,
                    rect,
                    (22, 25, 31) if sel else (14, 16, 20),
                    (242, 244, 248) if sel else (75, 80, 92),
                    cut=5,
                    border_w=2 if sel else 1,
                )
                emb = _PACK.sprites.get(f"emblem_{grp['emblem_idx']}.png")
                if emb is not None:
                    emb_sm = pygame.transform.smoothscale(emb, (34, 34))
                    surface.blit(emb_sm, (rect.x + 8, rect.y + 5))
                t_s = f_title.render(grp["name"], True, (244, 246, 250))
                m_s = f_sub.render(
                    f"{grp['members_count']} miembros • {grp['channels_count']} canales • Código: {grp.get('invite_code', 'CCI')}",
                    True,
                    (175, 180, 190),
                )
                surface.blit(t_s, (rect.x + 52, rect.y + 6))
                surface.blit(m_s, (rect.x + 52, rect.y + 24))

        # Panel derecho de detalle sobre la base limpia (x=913..1262, y=188..588)
        if groups:
            sel_grp = groups[self.selected_index]
            inv = self.bridge.get_or_create_invite(sel_grp["id"])
            ban = _PACK.sprites.get(f"banner_{sel_grp['banner_idx'] % 6}.png")
            if ban is not None:
                surface.blit(ban, (925, 188))
            emb = _PACK.sprites.get(f"emblem_{sel_grp['emblem_idx'] % 6}.png")
            if emb is not None and not sel_grp.get("is_custom"):
                surface.blit(emb, (928, 252))
            else:
                emb_box = pygame.Rect(928, 252, 54, 54)
                _draw_cut_rect(surface, emb_box, (20, 26, 36), (110, 190, 255), cut=6, border_w=2)
                ini = sel_grp["name"][:2].upper()
                ini_s = _PACK.fonts["title"].render(ini, True, (245, 247, 252))
                surface.blit(
                    ini_s,
                    (emb_box.centerx - ini_s.get_width() // 2, emb_box.centery - ini_s.get_height() // 2),
                )

            n_s = _PACK.fonts["title"].render(sel_grp["name"][:18], True, (245, 247, 252))
            surface.blit(n_s, (996, 264))
            p_s = f_sub.render(f"🔒 {sel_grp['privacy']} • Cód: {inv['code']}", True, (175, 185, 200))
            surface.blit(p_s, (996, 288))

            lines = _wrap_lines(sel_grp["description"], f_sub, 316)
            for li, line in enumerate(lines[:2]):
                l_s = f_sub.render(line, True, (205, 210, 220))
                surface.blit(l_s, (928, 322 + li * 17))

            stats = [
                ("Miembros", str(sel_grp["members_count"]), 368),
                ("En línea", str(sel_grp["online_count"]), 399),
                ("# Canales propios", str(sel_grp["channels_count"]), 431),
                ("Salas de voz", str(sel_grp["voice_count"]), 463),
            ]
            for lbl, val, sy in stats:
                ls = f_body.render(lbl, True, (205, 210, 220))
                vs = f_small_b.render(val, True, (244, 246, 250))
                surface.blit(ls, (946, sy))
                surface.blit(vs, (1244 - vs.get_width(), sy))

            # Botones rápidos para copiar código o link directamente desde el panel derecho
            _draw_cut_rect(surface, self.copy_code_detail_rect, (20, 24, 32), (120, 130, 148), cut=4, border_w=1)
            _draw_cut_rect(surface, self.copy_link_detail_rect, (20, 24, 32), (120, 130, 148), cut=4, border_w=1)
            cc_s = f_small_b.render(f"📋 Código: {inv['code'][:8]}", True, (235, 240, 248))
            cl_s = f_small_b.render("🔗 Copiar Link", True, (235, 240, 248))
            surface.blit(cc_s, (self.copy_code_detail_rect.x + 10, self.copy_code_detail_rect.y + 5))
            surface.blit(cl_s, (self.copy_link_detail_rect.x + 28, self.copy_link_detail_rect.y + 5))

    def _draw_tab_chats_privados(self, surface: pygame.Surface) -> None:
        f_title = _PACK.fonts["card_title"]
        f_body = _PACK.fonts["body"]
        f_small = _PACK.fonts["small"]

        # 1. Lista izquierda de contactos recortados con aire (x=259..569, y=242..598)
        self.dm_contact_rects.clear()
        self.selected_index = max(0, min(self.selected_index, len(self.dms) - 1))

        cur_y = 242
        for i, dm in enumerate(self.dms):
            sp = _PACK.sprites.get(dm.contact_sprite)
            h = sp.get_height() if sp is not None else 52
            rect = pygame.Rect(259, cur_y, 310, h)
            self.dm_contact_rects.append((rect, i))

            if sp is not None:
                surface.blit(sp, (259, cur_y))

            if i == self.selected_index:
                pygame.draw.rect(surface, (242, 244, 248), rect, 2, border_radius=5)

            cur_y += h + 7

        # 2. Panel derecho de conversación con márgenes amplios (x=620..1240, y=194..596)
        active_dm = self.dms[self.selected_index]

        if active_dm.contact_id == "dm_tomas" and len(active_dm.messages) == 5:
            hdr = _PACK.sprites.get("dm_header_tomas.png")
            msgs = _PACK.sprites.get("dm_messages_tomas.png")
            inp = _PACK.sprites.get("dm_input_bar.png")
            if hdr is not None:
                surface.blit(hdr, (620, 194))
            if msgs is not None:
                surface.blit(msgs, (620, 252))
            if inp is not None:
                surface.blit(inp, (620, 550))
        else:
            hdr = _PACK.sprites.get("dm_header_tomas.png")
            if hdr is not None:
                surface.blit(hdr, (620, 194))
                pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(674, 198, 280, 40))
                n_s = f_title.render(f"{active_dm.name}   {active_dm.handle}", True, (242, 244, 248))
                s_s = f_small.render(f"● {active_dm.status} • {active_dm.activity}", True, (175, 185, 195))
                surface.blit(n_s, (678, 200))
                surface.blit(s_s, (678, 219))

            msg_y = 256
            for sender, ts, text in active_dm.messages[-5:]:
                is_me = sender.upper() == "ALEX"
                bw = min(450, max(190, f_body.size(text)[0] + 36))
                bx = 1230 - bw if is_me else 630
                brect = pygame.Rect(bx, msg_y, bw, 46)
                _draw_cut_rect(
                    surface,
                    brect,
                    (28, 31, 38) if is_me else (18, 20, 25),
                    (150, 156, 170) if is_me else (80, 85, 98),
                    cut=6,
                    border_w=1,
                )
                meta = f_small.render(f"{sender}   {ts}", True, (165, 170, 182))
                body = f_body.render(text, True, (242, 244, 248))
                surface.blit(meta, (brect.x + 12, brect.y + 6))
                surface.blit(body, (brect.x + 12, brect.y + 23))
                msg_y += 56

            inp = _PACK.sprites.get("dm_input_bar.png")
            if inp is not None:
                surface.blit(inp, (620, 550))

        if self.dm_input_focused or self.dm_input_text:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(660, 558, 440, 28))
            if self.dm_input_focused:
                pygame.draw.rect(surface, (238, 240, 248), self.dm_input_rect, 1, border_radius=5)
            txt = self.dm_input_text + ("|" if self.dm_input_focused else "")
            t_s = f_body.render(txt or f"Escribir mensaje a {active_dm.name}...", True, (240, 242, 248))
            surface.blit(t_s, (666, 564))

        # 3. Asistente inferior recortado de la hoja Photoroom
        ast = _PACK.sprites.get("dm_assistant_bar.png")
        if ast is not None:
            surface.blit(ast, (38, 636))

    def _draw_tab_solicitudes(self, surface: pygame.Surface) -> None:
        self.sol_action_rects.clear()

        # 1. Invitaciones a grupos en el contenedor izquierdo con margen interno (x=265..777, y=252..576)
        gy = 252
        for inv in self.group_invites:
            sp = _PACK.sprites.get(inv.sprite_name)
            if sp is not None:
                surface.blit(sp, (265, gy))
            acc_rect = pygame.Rect(265 + 324, gy + 54, 86, 32)
            rej_rect = pygame.Rect(265 + 416, gy + 54, 90, 32)
            self.sol_action_rects.append((acc_rect, inv.req_id, "accept"))
            self.sol_action_rects.append((rej_rect, inv.req_id, "reject"))
            gy += 108

        # 2. Solicitudes de amistad en el contenedor superior derecho con margen (x=832..1244, y=248..362)
        fy = 248
        for fr in self.friend_requests:
            sp = _PACK.sprites.get(fr.sprite_name)
            if sp is not None:
                surface.blit(sp, (832, fy))
            acc_rect = pygame.Rect(832 + 236, fy + 10, 82, 32)
            rej_rect = pygame.Rect(832 + 322, fy + 10, 86, 32)
            self.sol_action_rects.append((acc_rect, fr.req_id, "accept"))
            self.sol_action_rects.append((rej_rect, fr.req_id, "reject"))
            fy += 58

        # 3. Invitaciones enviadas en el contenedor medio derecho con margen (x=832..1244, y=446..508)
        sy = 446
        for st in self.sent_invites:
            sp = _PACK.sprites.get(st.sprite_name)
            if sp is not None:
                surface.blit(sp, (832, sy))
            can_rect = pygame.Rect(832 + 306, sy + 10, 98, 32)
            self.sol_action_rects.append((can_rect, st.req_id, "cancel"))
            sy += 58

    def _draw_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        f_title = _PACK.fonts["title"]
        f_body = _PACK.fonts["body"]
        f_body_b = _PACK.fonts["body_bold"]
        f_sub = _PACK.fonts["card_sub"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        if self.modal_mode == "share":
            box = pygame.Rect(390, 190, 500, 300)
            _draw_cut_rect(surface, box, (15, 17, 22), (240, 242, 248), cut=10, border_w=2)
            groups = self._filtered_groups()
            sel_grp = groups[max(0, min(self.selected_index, len(groups) - 1))] if groups else None
            grp_name = sel_grp["name"] if sel_grp else "COMUNIDAD"
            inv = self.bridge.get_or_create_invite(sel_grp["id"]) if sel_grp else {"code": "CCI2026", "uri": "cci://invite/CCI2026", "link": "https://c-c-i-system.onrender.com/invite/CCI2026"}

            surface.blit(f_title.render(f"COMPARTIR {grp_name[:18]}", True, (244, 246, 250)), (box.x + 24, box.y + 20))
            surface.blit(f_sub.render("Invita jugadores con este código o link directo:", True, (185, 190, 200)), (box.x + 24, box.y + 52))

            code_box = pygame.Rect(420, 266, 440, 34)
            _draw_cut_rect(surface, code_box, (10, 12, 16), (110, 210, 255), cut=5, border_w=1)
            surface.blit(
                f_body.render(f"CÓDIGO:  {inv['code']}     |     URI:  {inv['uri']}", True, (244, 246, 250)),
                (code_box.x + 12, code_box.y + 8),
            )

            btn_copy_code = pygame.Rect(420, 310, 130, 32)
            btn_copy_link = pygame.Rect(560, 310, 130, 32)
            btn_regen = pygame.Rect(700, 310, 150, 32)
            _draw_cut_rect(surface, btn_copy_code, (235, 238, 246), (255, 255, 255), cut=5, border_w=1)
            _draw_cut_rect(surface, btn_copy_link, (28, 34, 46), (130, 185, 255), cut=5, border_w=1)
            _draw_cut_rect(surface, btn_regen, (24, 27, 34), (130, 136, 150), cut=5, border_w=1)
            surface.blit(f_small_b.render("Copiar Código", True, (12, 14, 18)), (btn_copy_code.x + 20, btn_copy_code.y + 9))
            surface.blit(f_small_b.render("Copiar Link", True, (235, 240, 248)), (btn_copy_link.x + 26, btn_copy_link.y + 9))
            surface.blit(f_small_b.render("Generar Nuevo", True, (220, 224, 232)), (btn_regen.x + 28, btn_regen.y + 9))

            link_box = pygame.Rect(420, 358, 440, 32)
            _draw_cut_rect(surface, link_box, (10, 12, 16), (80, 86, 98), cut=4, border_w=1)
            surface.blit(f_small.render(inv["link"], True, (165, 195, 235)), (link_box.x + 10, link_box.y + 9))

            if self.status_banner:
                surface.blit(f_small_b.render(f"✓ {self.status_banner}", True, (115, 235, 165)), (420, 404))

            close_rect = pygame.Rect(580, 440, 120, 34)
            _draw_cut_rect(surface, close_rect, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Listo", True, (12, 14, 18)), (close_rect.x + 40, close_rect.y + 9))
            return

        box = pygame.Rect(400, 190, 480, 275)
        _draw_cut_rect(surface, box, (15, 17, 22), (240, 242, 248), cut=10, border_w=2)

        if self.modal_mode == "create":
            surface.blit(f_title.render("CREAR NUEVO SERVIDOR / GRUPO", True, (244, 246, 250)), (box.x + 24, box.y + 18))
            surface.blit(f_small.render("Nombre del grupo (creará sus propios canales y código):", True, (185, 190, 200)), (box.x + 24, box.y + 48))

            name_inp = pygame.Rect(424, 256, 432, 34)
            _draw_cut_rect(
                surface,
                name_inp,
                (10, 12, 15),
                (245, 247, 252) if self.modal_field_idx == 0 else (95, 100, 114),
                cut=5,
                border_w=2 if self.modal_field_idx == 0 else 1,
            )
            c0 = "|" if self.modal_field_idx == 0 else ""
            surface.blit(f_body.render((self.modal_input + c0) or "Ej: ESCUADRÓN ALPHA", True, (244, 246, 250)), (name_inp.x + 12, name_inp.y + 8))

            surface.blit(f_small.render("Descripción / temática (Tab para cambiar de campo):", True, (185, 190, 200)), (box.x + 24, 298))
            desc_inp = pygame.Rect(424, 318, 432, 34)
            _draw_cut_rect(
                surface,
                desc_inp,
                (10, 12, 15),
                (245, 247, 252) if self.modal_field_idx == 1 else (95, 100, 114),
                cut=5,
                border_w=2 if self.modal_field_idx == 1 else 1,
            )
            c1 = "|" if self.modal_field_idx == 1 else ""
            surface.blit(
                f_body.render((self.modal_desc_input + c1) or "Comunidad de juegos, voz y torneos...", True, (210, 215, 225)),
                (desc_inp.x + 12, desc_inp.y + 8),
            )

            priv_rect = pygame.Rect(424, 366, 210, 30)
            pub_rect = pygame.Rect(646, 366, 210, 30)
            is_priv = self.modal_privacy == "private"
            _draw_cut_rect(surface, priv_rect, (28, 34, 44) if is_priv else (14, 16, 20), (240, 242, 248) if is_priv else (80, 85, 96), cut=4, border_w=1)
            _draw_cut_rect(surface, pub_rect, (28, 34, 44) if not is_priv else (14, 16, 20), (240, 242, 248) if not is_priv else (80, 85, 96), cut=4, border_w=1)
            surface.blit(f_small_b.render("🔒 Privado (Solo invitación)", True, (244, 246, 250)), (priv_rect.x + 18, priv_rect.y + 8))
            surface.blit(f_small_b.render("🌐 Público (Abierto)", True, (244, 246, 250)), (pub_rect.x + 36, pub_rect.y + 8))
        else:
            surface.blit(f_title.render("UNIRSE A UN GRUPO (CÓDIGO O LINK)", True, (244, 246, 250)), (box.x + 24, box.y + 20))
            surface.blit(
                f_sub.render("Pegá el código (ej: A8F3K9D2) o el link (cci://invite/...):", True, (185, 190, 200)),
                (box.x + 24, box.y + 56),
            )
            inp = pygame.Rect(424, 282, 432, 38)
            _draw_cut_rect(surface, inp, (10, 12, 15), (220, 224, 232), cut=5, border_w=1)
            surface.blit(f_body.render((self.modal_input + "|")[:46], True, (244, 246, 250)), (inp.x + 12, inp.y + 10))

            paste_rect = pygame.Rect(424, 340, 210, 30)
            _draw_cut_rect(surface, paste_rect, (24, 28, 36), (130, 185, 255), cut=4, border_w=1)
            surface.blit(f_small_b.render("📋 Pegar del portapapeles", True, (235, 240, 248)), (paste_rect.x + 18, paste_rect.y + 8))

        ok_btn = pygame.Rect(520, 410, 115, 34)
        no_btn = pygame.Rect(645, 410, 115, 34)
        _draw_cut_rect(surface, ok_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
        _draw_cut_rect(surface, no_btn, (22, 25, 32), (130, 135, 148), cut=5, border_w=1)

        surface.blit(_PACK.fonts["tab"].render("Confirmar", True, (12, 14, 18)), (ok_btn.x + 22, ok_btn.y + 9))
        surface.blit(_PACK.fonts["tab"].render("Cancelar", True, (220, 224, 232)), (no_btn.x + 26, no_btn.y + 9))


# ---------------------------------------------------------------------------
# Pantalla 2: Vista Interna Dinámica de Comunidad ("COMMUNITY" estilo Discord)
# ---------------------------------------------------------------------------

class CommunityViewState(BaseState):
    """Vista interna de servidor/comunidad con canales propios por grupo, creación de canales e invitaciones."""

    TEXT_CHANNELS = [
        ("anuncios", "Información y comunicados oficiales."),
        ("reglas", "Normas de convivencia de la comunidad."),
        ("bienvenidas", "Nuevos miembros que se unen al servidor."),
        ("general", "Conversación general de la comunidad."),
        ("off-topic", "Charlas libres, música y otros temas."),
        ("clips-y-memes", "Capturas, jugadas destacadas y humor."),
        ("busqueda-de-equipo", "Coordinación de squads y partidas competitivas."),
        ("sugerencias", "Ideas y mejoras para la comunidad."),
    ]

    VOICE_CHANNELS = [
        ("Sala principal", "5/16"),
        ("Gaming", "3/8"),
        ("Rankeds", "0/5"),
        ("Streaming", "1/4"),
    ]

    DEFAULT_GENERAL_MESSAGES: List[Dict[str, str]] = [
        {"author": "ALEX", "time": "Hoy 18:24", "text": "¿Alguien para unas partidas esta noche? 🎮"},
        {"author": "MIRA", "time": "Hoy 18:26", "text": "¡Yo me sumo! Estuve probando el nuevo mapa."},
        {"author": "KAI", "time": "Hoy 18:27", "text": "También me copo, ¿armamos sala en la de Gaming?"},
        {"author": "ALEX", "time": "Hoy 18:28", "text": "Dale, en 10 min la creo. 👌"},
        {"author": "MIRA", "time": "Hoy 18:35", "text": "Les dejo el skin que conseguí hoy 👀"},
        {"author": "KAI", "time": "Hoy 18:40", "text": "Está increíble 🔥"},
    ]

    CHANNEL_PRESETS: Dict[str, List[Dict[str, str]]] = {
        "anuncios": [
            {"author": "ALEX", "time": "Ayer 20:00", "text": "📢 Torneo oficial Night Raid este viernes a las 22:00 hs."},
            {"author": "MIRA", "time": "Ayer 20:15", "text": "Inscripciones abiertas en #busqueda-de-equipo. ¡Premios C.C.I.!"},
            {"author": "KAI", "time": "Hoy 12:00", "text": "Actualización v2.1 del servidor completada sin cortes."},
        ],
        "reglas": [
            {"author": "ALEX", "time": "Fijado", "text": "1. Respeto mutuo entre todos los miembros de la comunidad."},
            {"author": "ALEX", "time": "Fijado", "text": "2. Usar cada canal para su temática correspondiente."},
            {"author": "ALEX", "time": "Fijado", "text": "3. Prohibido el spam o compartir enlaces no verificados."},
        ],
        "bienvenidas": [
            {"author": "KAI", "time": "Ayer 19:10", "text": "¡Bienvenido ZERO a la comunidad! Pasá por #reglas."},
            {"author": "MIRA", "time": "Hoy 14:30", "text": "¡Bienvenida LUNA al escuadrón! 🎉"},
        ],
        "off-topic": [
            {"author": "KAI", "time": "Hoy 16:10", "text": "¿Alguien escuchó el nuevo soundtrack synthwave de C.C.I.?"},
            {"author": "MIRA", "time": "Hoy 16:14", "text": "Sí, lo tengo en loop mientras diseño los mapas."},
            {"author": "ALEX", "time": "Hoy 16:20", "text": "Quedó brutal para jugar de noche."},
        ],
        "clips-y-memes": [
            {"author": "MIRA", "time": "Hoy 17:05", "text": "Subí el clip de la jugada final 1v3 en Da Vinci Fighters 🎬"},
            {"author": "KAI", "time": "Hoy 17:09", "text": "Jajaja ese parry en el último segundo fue de película."},
        ],
        "busqueda-de-equipo": [
            {"author": "ALEX", "time": "Hoy 18:00", "text": "Buscamos +2 para Ranked 5v5 hoy a las 22:00."},
            {"author": "KAI", "time": "Hoy 18:04", "text": "Me anoto de entry/soporte."},
        ],
        "sugerencias": [
            {"author": "MIRA", "time": "Ayer 21:00", "text": "Idea: sumar un canal de retos semanales de speedrun."},
            {"author": "ALEX", "time": "Hoy 10:30", "text": "¡Aprobado! Podés crearlo con el botón [+] de canales."},
        ],
        "galeria-pixel": [
            {"author": "MARTINA", "time": "Hoy 15:20", "text": "Subí los nuevos portraits pixel-art de Sakura Club 🌸"},
            {"author": "HANA", "time": "Hoy 15:25", "text": "¡Me encanta la paleta pastel y neón que usaste!"},
        ],
        "musica-lofi": [
            {"author": "HANA", "time": "Hoy 17:00", "text": "Dejé sonando el mix nocturno en la sala Radio Lo-Fi 24/7 🎧"},
        ],
        "dev-log": [
            {"author": "TOMÁS", "time": "Hoy 19:00", "text": "Motor autoritativo 60 Hz y persistencia SQLite WAL listos."},
            {"author": "ALEX", "time": "Hoy 19:05", "text": "192/192 tests en verde y canales dinámicos por servidor."},
        ],
        "speedruns": [
            {"author": "REN", "time": "Hoy 18:10", "text": "Nuevo PB en Cyberpunk Metroidvania: 14m 22s sin daño ⚡"},
        ],
    }

    def __init__(self, state_machine: Optional[Any] = None, db_path: Optional[str] = None) -> None:
        super().__init__(state_machine)
        self.db_path = db_path
        self.bridge = CommunitiesUIBridge(db_path=db_path)
        self.sidebar_surface: Optional[pygame.Surface] = None
        self.sidebar_font: Optional[pygame.font.Font] = None

        self.groups: List[Dict[str, Any]] = self.bridge.load_groups()
        self.community_id: str = "night_raid"
        self.active_group_idx: int = 0
        self.text_channels: List[Tuple[str, str]] = list(self.TEXT_CHANNELS)
        self.voice_channels: List[Tuple[str, str]] = list(self.VOICE_CHANNELS)
        self.current_channel: str = "general"
        self.active_voice: Optional[str] = "Gaming"
        self.last_voice_token: Optional[Dict[str, Any]] = None

        self.reaction_heart: int = 8
        self.reaction_fire: int = 3
        self.user_hearted: bool = False
        self.user_fired: bool = False

        self.channel_histories: Dict[str, List[Dict[str, str]]] = {}
        self._sync_active_community_data()
        self.chat_messages: List[Dict[str, str]] = self.channel_histories.get(self.current_channel, [])
        self.scroll_offset: int = 0
        self.max_scroll: int = 0

        self.input_text: str = ""
        self.input_focused: bool = False

        # Modales dentro del servidor: None | "create_text_channel" | "create_voice_channel" | "invite" | "create_group"
        self.modal_mode: Optional[str] = None
        self.modal_input: str = ""
        self.modal_topic_input: str = ""
        self.modal_field_idx: int = 0
        self.status_toast: str = ""
        self.soundboard_open: bool = False

        # Rects interactivos sobre la Base Limpia 4 (1280x720)
        self.server_icon_rects: List[Tuple[pygame.Rect, int]] = []
        self.channel_rects: List[Tuple[pygame.Rect, str]] = []
        self.delete_channel_rects: List[Tuple[pygame.Rect, str]] = []
        self.voice_rects: List[Tuple[pygame.Rect, str]] = []
        self.soundboard_btn_rect = pygame.Rect(352, 582, 86, 28)
        self.sound_pad_rects: List[Tuple[pygame.Rect, str]] = []
        self.add_text_ch_rect = pygame.Rect(416, 260, 22, 22)
        self.add_voice_ch_rect = pygame.Rect(416, 420, 22, 22)
        self.invite_btn_rect = pygame.Rect(916, 92, 82, 28)
        self.chat_viewport = pygame.Rect(460, 186, 574, 386)
        self.attach_btn_rect = pygame.Rect(462, 580, 32, 36)
        self.input_rect = pygame.Rect(500, 580, 535, 36)
        self.heart_rect = pygame.Rect(528, 502, 46, 22)
        self.fire_rect = pygame.Rect(578, 502, 46, 22)

        # Estado de adjuntos y capturas F12
        self.pending_attachment: Optional[Dict[str, Any]] = None
        self.pending_chip_cancel_rect = pygame.Rect(738, 554, 20, 20)
        self.preview_image_path: Optional[str] = None
        self.screenshot_picker_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []
        self.attachment_preview_rects: List[Tuple[pygame.Rect, str]] = []

        # Estado de menciones (@mentions) y autocompletado
        self.autocomplete_active: bool = False
        self.autocomplete_candidates: List[str] = []
        self.autocomplete_selected_idx: int = 0
        self.autocomplete_rects: List[Tuple[pygame.Rect, str]] = []

        # Estado de Go Live / Transmisión en Vivo
        self.is_streaming: bool = False
        self.active_stream_info: Optional[Dict[str, Any]] = None
        self.stream_btn_rect = pygame.Rect(246, 548, 192, 28)
        self.stream_pip_rect = pygame.Rect(842, 148, 192, 108)
        self.stream_game_picker_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []
        self.stream_res_selected: str = "720p"
        self.stream_fps_selected: int = 30

    def _active_group_dict(self) -> Dict[str, Any]:
        if not self.groups:
            self.groups = self.bridge.load_groups()
        for i, g in enumerate(self.groups):
            if (
                g["id"] == self.community_id
                or g["id"].replace("-", "_") == self.community_id.replace("-", "_")
                or g.get("group_id") == self.community_id
            ):
                self.active_group_idx = i
                return g
        self.active_group_idx = max(0, min(self.active_group_idx, len(self.groups) - 1))
        return self.groups[self.active_group_idx]

    def _sync_active_community_data(self) -> None:
        """Carga los canales de texto, salas de voz e historial propios de la comunidad activa."""
        self.groups = self.bridge.load_groups()
        grp = self._active_group_dict()
        self.text_channels, self.voice_channels = self.bridge.list_channels_for_community(grp["id"])
        self.channel_histories = {}
        is_night_raid = grp["id"].replace("-", "_") == "night_raid"
        for ch_name, ch_topic in self.text_channels:
            if ch_name == "general" and is_night_raid:
                preset = self.DEFAULT_GENERAL_MESSAGES
            elif ch_name in self.CHANNEL_PRESETS:
                preset = self.CHANNEL_PRESETS[ch_name]
            elif ch_name == "general":
                preset = [
                    {
                        "author": "ALEX",
                        "time": "Hoy",
                        "text": f"¡Bienvenidos al canal #{ch_name} de {grp['name']}! Usá [+] para crear más canales.",
                    }
                ]
            else:
                preset = []
            self.channel_histories[ch_name] = self.bridge.load_channel_messages(grp["id"], ch_name, preset)

        valid_names = [c[0] for c in self.text_channels]
        if self.current_channel not in valid_names:
            self.current_channel = "general" if "general" in valid_names else (valid_names[0] if valid_names else "general")
        self.chat_messages = self.channel_histories.setdefault(self.current_channel, [])

    def _reload_all_channel_histories(self) -> None:
        self._sync_active_community_data()

    def enter(self, **kwargs) -> None:
        _PACK.ensure_loaded()
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.input_focused = False
        self.modal_mode = None
        self.status_toast = ""

        if "community_id" in kwargs and kwargs["community_id"]:
            self.community_id = str(kwargs["community_id"])

        self.current_channel = "general"
        self._sync_active_community_data()
        self.scroll_offset = 0
        self.input_text = ""

    def _switch_channel(self, ch_name: str) -> None:
        grp = self._active_group_dict()
        is_night_raid = grp["id"].replace("-", "_") == "night_raid"
        if ch_name == "general" and is_night_raid:
            preset = self.DEFAULT_GENERAL_MESSAGES
        else:
            preset = self.CHANNEL_PRESETS.get(ch_name, [])
        self.channel_histories[ch_name] = self.bridge.load_channel_messages(
            grp["id"], ch_name, preset
        )
        self.current_channel = ch_name
        self.chat_messages = self.channel_histories[ch_name]
        self.scroll_offset = 0

    def _change_state(self, dest: str, **kwargs) -> None:
        if self.state_machine is not None:
            self.state_machine.change_state(dest, **kwargs)

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.MOUSEWHEEL and self.modal_mode is None:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset - e.y * 36))
                continue

            if e.type == pygame.KEYDOWN:
                if self.modal_mode is not None:
                    self._handle_modal_key(e)
                    continue

                if e.key == pygame.K_RETURN and self.input_text.strip():
                    self._send_message()
                    continue

                if self.input_focused:
                    if self.autocomplete_active and self.autocomplete_candidates:
                        if e.key == pygame.K_TAB:
                            cand = self.autocomplete_candidates[self.autocomplete_selected_idx]
                            self._apply_autocomplete(cand)
                            continue
                        elif e.key == pygame.K_UP:
                            self.autocomplete_selected_idx = (self.autocomplete_selected_idx - 1) % len(self.autocomplete_candidates)
                            continue
                        elif e.key == pygame.K_DOWN:
                            self.autocomplete_selected_idx = (self.autocomplete_selected_idx + 1) % len(self.autocomplete_candidates)
                            continue
                        elif e.key == pygame.K_ESCAPE:
                            self.autocomplete_active = False
                            continue

                    if e.key == pygame.K_ESCAPE:
                        self.input_focused = False
                        self.autocomplete_active = False
                    elif e.key == pygame.K_RETURN:
                        self._send_message()
                    elif e.key == pygame.K_v and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                        pasted = paste_from_clipboard()
                        if pasted:
                            self.input_text = (self.input_text + pasted)[:72]
                            self._update_mention_autocomplete()
                    elif e.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                        self._update_mention_autocomplete()
                    elif e.unicode and e.unicode.isprintable() and len(self.input_text) < 72:
                        self.input_text += e.unicode
                        self._update_mention_autocomplete()
                    continue

                if e.key == pygame.K_ESCAPE:
                    self._change_state("GROUPS")
                elif e.key == pygame.K_PAGEUP:
                    self.scroll_offset = max(0, self.scroll_offset - 72)
                elif e.key == pygame.K_PAGEDOWN:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + 72)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    names = [c[0] for c in self.text_channels] or [c[0] for c in self.TEXT_CHANNELS]
                    idx = names.index(self.current_channel) if self.current_channel in names else 0
                    self._switch_channel(names[(idx + 1) % len(names)])
                elif e.key in (pygame.K_UP, pygame.K_w):
                    names = [c[0] for c in self.text_channels] or [c[0] for c in self.TEXT_CHANNELS]
                    idx = names.index(self.current_channel) if self.current_channel in names else 0
                    self._switch_channel(names[(idx - 1) % len(names)])
                elif e.key == pygame.K_RETURN:
                    self.input_focused = True

            elif e.type == pygame.MOUSEBUTTONDOWN:
                if self.modal_mode is not None and e.button == 1:
                    self._handle_modal_click(self._to_logical_pos(e.pos))
                    continue

                if e.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - 36)
                    continue
                if e.button == 5:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + 36)
                    continue
                if e.button != 1:
                    continue

                pos = self._to_logical_pos(e.pos)

                # 1. Sidebar compartida (x < 170)
                dest = sidebar_destination(pos, max_x=170)
                if dest is not None:
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    else:
                        self._change_state(dest)
                    continue

                # 2. Columna de iconos de comunidades (x = 175..235)
                for rect, idx in self.server_icon_rects:
                    if rect.collidepoint(pos):
                        if idx == -1:
                            self._change_state("GROUPS")
                        elif idx == -2:
                            self.modal_mode = "create_group"
                            self.modal_input = ""
                            self.modal_topic_input = ""
                            self.modal_field_idx = 0
                        elif 0 <= idx < len(self.groups):
                            self.active_group_idx = idx
                            self.community_id = self.groups[idx]["id"]
                            self.current_channel = "general"
                            self._sync_active_community_data()
                            self.scroll_offset = 0
                        return

                # 3. Botón superior [Invitar] para compartir código o link de esta comunidad
                if self.invite_btn_rect.collidepoint(pos):
                    self.modal_mode = "invite"
                    return

                # 3b. Botón Soundboard / Sound Deck
                if self.soundboard_btn_rect.collidepoint(pos):
                    self.modal_mode = "soundboard"
                    return

                # 3c. Botón Go Live / Transmitir en Vivo
                if self.stream_btn_rect.collidepoint(pos):
                    if self.is_streaming:
                        grp = self._active_group_dict()
                        self.bridge.stop_live_stream(grp["id"])
                        self.is_streaming = False
                        self.active_stream_info = None
                        self.status_toast = "Transmisión en vivo finalizada"
                    else:
                        self.modal_mode = "stream_picker"
                    return

                # 3d. Clic en widget PiP de stream activo para ampliar a cine
                if self.is_streaming and self.stream_pip_rect.collidepoint(pos):
                    self.modal_mode = "stream_theater"
                    return

                # 4. Botones [+] para crear canales de texto o salas de voz en esta comunidad
                if self.add_text_ch_rect.collidepoint(pos):
                    self.modal_mode = "create_text_channel"
                    self.modal_input = ""
                    self.modal_topic_input = ""
                    self.modal_field_idx = 0
                    return
                if self.add_voice_ch_rect.collidepoint(pos):
                    self.modal_mode = "create_voice_channel"
                    self.modal_input = ""
                    self.modal_topic_input = ""
                    self.modal_field_idx = 0
                    return

                # 5. Eliminar un canal secundario si se hace clic en su botón [x]
                for d_rect, ch_name in self.delete_channel_rects:
                    if d_rect.collidepoint(pos):
                        grp = self._active_group_dict()
                        if self.bridge.delete_custom_channel(grp["id"], ch_name):
                            self.status_toast = f"Canal #{ch_name} eliminado"
                            self._sync_active_community_data()
                        return

                # 6. Selección de canales de texto propios del grupo (x = 246..438)
                for rect, ch_name in self.channel_rects:
                    if rect.collidepoint(pos):
                        self._switch_channel(ch_name)
                        return

                # 7. Salas de voz propias del grupo (x = 246..438)
                for rect, vc_name in self.voice_rects:
                    if rect.collidepoint(pos):
                        grp = self._active_group_dict()
                        joining = self.active_voice != vc_name
                        self.active_voice = vc_name if joining else None
                        self.last_voice_token = self.bridge.toggle_voice_channel(
                            grp["id"], vc_name, joining=joining
                        )
                        self._sync_active_community_data()
                        return

                # 8. Reacciones interactivas
                if self.current_channel == "general":
                    if self.heart_rect.collidepoint(pos):
                        self.user_hearted = not self.user_hearted
                        self.reaction_heart += 1 if self.user_hearted else -1
                        return
                    if self.fire_rect.collidepoint(pos):
                        self.user_fired = not self.user_fired
                        self.reaction_fire += 1 if self.user_fired else -1
                        return

                # 8b. Clic en miniatura de adjunto en el historial de chat para ampliar a pantalla completa
                for thumb_r, img_path in self.attachment_preview_rects:
                    if thumb_r.collidepoint(pos):
                        self.modal_mode = "image_preview"
                        self.preview_image_path = img_path
                        return

                # 8c. Clic en botón [📎] para abrir selector de capturas F12
                if self.attach_btn_rect.collidepoint(pos):
                    self.modal_mode = "attach_picker"
                    return

                # 8d. Clic en [x] del chip de adjunto pendiente
                if self.pending_attachment and self.pending_chip_cancel_rect.collidepoint(pos):
                    self.pending_attachment = None
                    return

                # 8e. Clic en item de autocompletado de mención
                if self.autocomplete_active:
                    for cand_r, cand_name in self.autocomplete_rects:
                        if cand_r.collidepoint(pos):
                            self._apply_autocomplete(cand_name)
                            return

                # 9. Barra de entrada de mensaje
                if self.input_rect.collidepoint(pos):
                    self.input_focused = True
                    self._update_mention_autocomplete()
                    if pos[0] >= self.input_rect.right - 36 and (self.input_text.strip() or self.pending_attachment):
                        self._send_message()
                    return
                self.input_focused = False
                self.autocomplete_active = False

    def _handle_modal_key(self, e: pygame.event.Event) -> None:
        if e.key == pygame.K_ESCAPE:
            self.modal_mode = None
            return
        if self.modal_mode in ("attach_picker", "image_preview", "stream_picker", "stream_theater"):
            if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.modal_mode = None
                return
        if self.modal_mode == "soundboard":
            if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.modal_mode = None
                return
            if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                idx = e.key - pygame.K_1
                if 0 <= idx < len(SOUNDBOARD_PRESETS):
                    self._fire_soundboard(SOUNDBOARD_PRESETS[idx]["name"])
            return
        if self.modal_mode == "invite":
            if e.key == pygame.K_RETURN:
                self.modal_mode = None
            return
        if e.key == pygame.K_RETURN:
            self._confirm_modal()
            return
        if e.key == pygame.K_TAB:
            self.modal_field_idx = (self.modal_field_idx + 1) % 2
            return
        if e.key == pygame.K_v and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
            pasted = paste_from_clipboard()
            if pasted:
                if self.modal_field_idx == 1:
                    self.modal_topic_input = (self.modal_topic_input + pasted)[:54]
                else:
                    self.modal_input = (self.modal_input + pasted)[:24]
            return
        if e.key == pygame.K_BACKSPACE:
            if self.modal_field_idx == 1:
                self.modal_topic_input = self.modal_topic_input[:-1]
            else:
                self.modal_input = self.modal_input[:-1]
        elif e.unicode and e.unicode.isprintable():
            if self.modal_field_idx == 1:
                if len(self.modal_topic_input) < 54:
                    self.modal_topic_input += e.unicode
            else:
                if len(self.modal_input) < 24:
                    self.modal_input += e.unicode

    def _handle_modal_click(self, pos: Tuple[int, int]) -> None:
        grp = self._active_group_dict()
        if self.modal_mode == "soundboard":
            for pad_r, s_name in self.sound_pad_rects:
                if pad_r.collidepoint(pos):
                    self._fire_soundboard(s_name)
                    return
            close_rect = pygame.Rect(580, 470, 120, 34)
            if close_rect.collidepoint(pos):
                self.modal_mode = None
            return

        if self.modal_mode == "attach_picker":
            for card_r, snap_dict in self.screenshot_picker_rects:
                if card_r.collidepoint(pos):
                    self.pending_attachment = snap_dict
                    self.modal_mode = None
                    self.status_toast = f"Captura '{snap_dict['filename']}' adjuntada"
                    return
            close_btn = pygame.Rect(580, 505, 120, 32)
            if close_btn.collidepoint(pos):
                self.modal_mode = None
            return

        if self.modal_mode == "image_preview":
            close_btn = pygame.Rect(580, 620, 120, 32)
            if close_btn.collidepoint(pos) or not pygame.Rect(160, 60, 960, 600).collidepoint(pos):
                self.modal_mode = None
            return

        if self.modal_mode == "stream_picker":
            btn_720 = pygame.Rect(354, 150, 96, 26)
            btn_1080 = pygame.Rect(458, 150, 96, 26)
            if btn_720.collidepoint(pos):
                self.stream_res_selected = "720p"
                self.stream_fps_selected = 30
                return
            if btn_1080.collidepoint(pos):
                self.stream_res_selected = "1080p"
                self.stream_fps_selected = 60
                return
            for card_r, game_item in self.stream_game_picker_rects:
                if card_r.collidepoint(pos):
                    target_ch = self.active_voice or "General"
                    st = self.bridge.start_live_stream(
                        community_slug_or_id=grp["id"],
                        channel_name=target_ch,
                        title=f"Jugando {game_item['title']}",
                        game_id=game_item["game_id"],
                        resolution=self.stream_res_selected,
                        fps=self.stream_fps_selected,
                    )
                    self.is_streaming = True
                    self.active_stream_info = {
                        "title": game_item["title"],
                        "game_id": game_item["game_id"],
                        "channel": target_ch,
                        "resolution": self.stream_res_selected,
                        "fps": self.stream_fps_selected,
                        "started_at": time.time(),
                        "session": st.get("session"),
                    }
                    self.modal_mode = None
                    self.status_toast = f"🔴 En vivo: {game_item['title']} ({self.stream_res_selected} @ {self.stream_fps_selected} FPS)"
                    return
            close_btn = pygame.Rect(580, 505, 120, 32)
            if close_btn.collidepoint(pos):
                self.modal_mode = None
            return

        if self.modal_mode == "stream_theater":
            btn_stop = pygame.Rect(460, 582, 170, 32)
            btn_close = pygame.Rect(646, 582, 170, 32)
            if btn_stop.collidepoint(pos):
                self.bridge.stop_live_stream(grp["id"])
                self.is_streaming = False
                self.active_stream_info = None
                self.modal_mode = None
                self.status_toast = "Transmisión en vivo finalizada"
                return
            if btn_close.collidepoint(pos) or not pygame.Rect(180, 40, 920, 584).collidepoint(pos):
                self.modal_mode = None
                return

        if self.modal_mode == "invite":
            inv = self.bridge.get_or_create_invite(grp["id"])
            btn_copy_code = pygame.Rect(420, 310, 130, 32)
            btn_copy_link = pygame.Rect(560, 310, 130, 32)
            btn_regen = pygame.Rect(700, 310, 150, 32)
            if btn_copy_code.collidepoint(pos):
                copy_to_clipboard(inv["code"])
                self.status_toast = f"Código copiado: {inv['code']}"
                return
            if btn_copy_link.collidepoint(pos):
                copy_to_clipboard(inv["link"])
                self.status_toast = f"Link copiado: {inv['uri']}"
                return
            if btn_regen.collidepoint(pos):
                new_inv = self.bridge.get_or_create_invite(grp["id"], regenerate=True)
                grp["invite_code"] = new_inv["code"]
                grp["invite_link"] = new_inv["link"]
                grp["invite_uri"] = new_inv["uri"]
                self.status_toast = f"Nuevo código generado: {new_inv['code']}"
                return
            close_rect = pygame.Rect(580, 435, 120, 34)
            if close_rect.collidepoint(pos):
                self.modal_mode = None
            return

        name_rect = pygame.Rect(424, 268, 432, 34)
        topic_rect = pygame.Rect(424, 336, 432, 34)
        if name_rect.collidepoint(pos):
            self.modal_field_idx = 0
            return
        if topic_rect.collidepoint(pos):
            self.modal_field_idx = 1
            return

        confirm_rect = pygame.Rect(520, 410, 115, 34)
        cancel_rect = pygame.Rect(645, 410, 115, 34)
        if confirm_rect.collidepoint(pos):
            self._confirm_modal()
        elif cancel_rect.collidepoint(pos):
            self.modal_mode = None

    def _confirm_modal(self) -> None:
        val = self.modal_input.strip()
        if not val:
            self.modal_mode = None
            return
        grp = self._active_group_dict()
        if self.modal_mode == "create_text_channel":
            created = self.bridge.create_custom_channel(
                grp["id"], val, channel_type="text", topic=self.modal_topic_input
            )
            if created:
                self._sync_active_community_data()
                self._switch_channel(created["name"])
                self.status_toast = f"Canal #{created['name']} creado en {grp['name']}"
        elif self.modal_mode == "create_voice_channel":
            created_v = self.bridge.create_custom_channel(
                grp["id"], val, channel_type="voice", topic=self.modal_topic_input
            )
            if created_v:
                self.active_voice = created_v["name"]
                self.last_voice_token = self.bridge.toggle_voice_channel(
                    grp["id"], created_v["name"], joining=True
                )
                self._sync_active_community_data()
                self.status_toast = f"Sala de voz '{created_v['name']}' creada en {grp['name']}"
        elif self.modal_mode == "create_group":
            new_grp = self.bridge.create_group(val, description=self.modal_topic_input, visibility="private")
            self.community_id = new_grp["id"]
            self.current_channel = "general"
            self._sync_active_community_data()
            self.status_toast = f"Servidor '{new_grp['name']}' creado (Código: {new_grp['invite_code']})"
        self.modal_mode = None

    def _fire_soundboard(self, s_name: str) -> None:
        """Reproduce un tono sintetizado y registra la emisión del efecto en el backend."""
        play_soundboard_tone(s_name)
        grp = self._active_group_dict()
        self.bridge.trigger_soundboard(grp["id"], s_name)
        self.status_toast = f"Sonido '{s_name}' reproducido en {grp['name']}"

    def _to_logical_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        surf = pygame.display.get_surface()
        if surf is None:
            return pos
        sw, sh = surf.get_size()
        if (sw, sh) == (SCREEN_WIDTH, SCREEN_HEIGHT) or sw <= 0 or sh <= 0:
            return pos
        return int(pos[0] * SCREEN_WIDTH / sw), int(pos[1] * SCREEN_HEIGHT / sh)

    def _update_mention_autocomplete(self) -> None:
        """Detecta si el usuario está escribiendo una mención con @ para sugerir miembros."""
        if not self.input_focused:
            self.autocomplete_active = False
            return
        words = self.input_text.split()
        last_word = words[-1] if words and not self.input_text.endswith(" ") else (self.input_text if self.input_text.startswith("@") else "")
        if last_word.startswith("@"):
            query = last_word[1:].upper()
            grp = self._active_group_dict()
            members = self.bridge.list_community_members_display(grp["id"])
            all_candidates = ["EVERYONE"] + [m[0].upper() for m in members]
            unique_cands: List[str] = []
            for c in all_candidates:
                if c not in unique_cands:
                    unique_cands.append(c)
            matches = [f"@{c}" for c in unique_cands if query in c]
            if matches:
                self.autocomplete_active = True
                self.autocomplete_candidates = matches[:5]
                self.autocomplete_selected_idx = max(0, min(self.autocomplete_selected_idx, len(matches) - 1))
                return
        self.autocomplete_active = False

    def _apply_autocomplete(self, mention_str: str) -> None:
        """Aplica la sugerencia elegida de mención en la barra de texto."""
        words = self.input_text.split()
        if words and not self.input_text.endswith(" "):
            words[-1] = mention_str
            self.input_text = " ".join(words) + " "
        elif self.input_text.startswith("@"):
            self.input_text = mention_str + " "
        else:
            self.input_text += mention_str + " "
        self.autocomplete_active = False

    def _send_message(self) -> None:
        txt = self.input_text.strip()
        att = self.pending_attachment
        if not txt and not att:
            return
        if not txt and att:
            txt = f"📎 [Captura adjunta: {att['filename']}]"

        grp = self._active_group_dict()
        self.bridge.send_channel_message(grp["id"], self.current_channel, txt, attachment=att)
        now_str = time.strftime("Hoy %H:%M")
        msg_payload: Dict[str, Any] = {"author": "ALEX", "time": now_str, "text": txt}
        if att:
            msg_payload["attachment"] = dict(att)
        self.chat_messages.append(msg_payload)

        # Si el mensaje incluye mención a otro miembro, mostrar toast
        if "@" in txt:
            for part in txt.split():
                if part.startswith("@"):
                    self.status_toast = f"Mencionaste a {part}"
                    break

        self.input_text = ""
        self.pending_attachment = None
        self.autocomplete_active = False
        self.scroll_offset = 999999

    def update(self, dt: float) -> None:
        pass

    def _draw_dynamic_channels_sidebar(
        self,
        canvas: pygame.Surface,
        grp: Dict[str, Any],
    ) -> None:
        """Renderiza dinámicamente los canales propios de cada comunidad (con botones [+] estilo Discord)."""
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]
        f_body = _PACK.fonts["body"]
        f_body_b = _PACK.fonts["body_bold"]

        # Limpiar el interior de la columna de canales (x=243..442, y=148..616) manteniendo el marco metálico exterior
        pygame.draw.rect(canvas, (7, 8, 10), pygame.Rect(243, 148, 199, 468))

        self.channel_rects.clear()
        self.delete_channel_rects.clear()
        self.voice_rects.clear()

        info_names = {"anuncios", "anuncios-club", "anuncios-eventos", "reglas", "bienvenidas", "roadmap", "bitacora-estelar", "retos-semanales"}
        info_chs = [(n, t) for (n, t) in self.text_channels if n.lower() in info_names]
        chat_chs = [(n, t) for (n, t) in self.text_channels if n.lower() not in info_names]
        if not info_chs and len(chat_chs) > 2:
            info_chs = chat_chs[:1]
            chat_chs = chat_chs[1:]

        cur_y = 154

        # 1. Categoría INFORMACIÓN
        if info_chs:
            canvas.blit(f_small_b.render("▾ INFORMACIÓN", True, (175, 182, 195)), (250, cur_y))
            cur_y += 22
            for ch_name, _ in info_chs[:3]:
                rect = pygame.Rect(246, cur_y, 192, 22)
                self.channel_rects.append((rect, ch_name))
                is_sel = ch_name == self.current_channel
                if is_sel:
                    pygame.draw.rect(canvas, (44, 48, 58), rect, border_radius=5)
                    pygame.draw.rect(canvas, (238, 240, 248), rect, 1, border_radius=5)
                icon = "📢" if "anuncio" in ch_name else ("📜" if "regla" in ch_name else "★")
                canvas.blit(f_small.render(icon, True, (210, 215, 225)), (254, cur_y + 3))
                canvas.blit(
                    (f_body_b if is_sel else f_body).render(ch_name[:18], True, (245, 247, 252) if is_sel else (188, 194, 206)),
                    (274, cur_y + 2),
                )
                cur_y += 24
            pygame.draw.line(canvas, (38, 42, 50), (248, cur_y + 2), (436, cur_y + 2), 1)
            cur_y += 8

        # 2. Categoría CHATS DE TEXTO + botón [+] para crear canales en este grupo
        self.add_text_ch_rect = pygame.Rect(416, cur_y - 2, 22, 20)
        canvas.blit(f_small_b.render("▾ CHATS DE TEXTO", True, (175, 182, 195)), (250, cur_y))
        pygame.draw.rect(canvas, (22, 26, 34), self.add_text_ch_rect, border_radius=4)
        pygame.draw.rect(canvas, (120, 185, 255), self.add_text_ch_rect, 1, border_radius=4)
        canvas.blit(f_body_b.render("+", True, (235, 242, 255)), (self.add_text_ch_rect.x + 6, self.add_text_ch_rect.y + 1))
        cur_y += 22

        for ch_name, _ in chat_chs[:7]:
            rect = pygame.Rect(246, cur_y, 192, 23)
            self.channel_rects.append((rect, ch_name))
            is_sel = ch_name == self.current_channel
            if is_sel:
                pygame.draw.rect(canvas, (44, 48, 58), rect, border_radius=5)
                pygame.draw.rect(canvas, (238, 240, 248), rect, 1, border_radius=5)
            canvas.blit(f_body_b.render("#", True, (215, 220, 232) if is_sel else (145, 152, 165)), (254, cur_y + 2))
            canvas.blit(
                (f_body_b if is_sel else f_body).render(ch_name[:17], True, (245, 247, 252) if is_sel else (188, 194, 206)),
                (272, cur_y + 3),
            )
            if ch_name != "general" and len(self.text_channels) > 1:
                del_r = pygame.Rect(418, cur_y + 3, 16, 16)
                self.delete_channel_rects.append((del_r, ch_name))
                if is_sel:
                    canvas.blit(f_small.render("×", True, (175, 180, 192)), (del_r.x + 4, del_r.y))
            cur_y += 24

        pygame.draw.line(canvas, (38, 42, 50), (248, cur_y + 3), (436, cur_y + 3), 1)
        cur_y += 10

        # 3. Categoría SALAS DE VOZ + botón [+] para crear sala de voz en este grupo
        self.add_voice_ch_rect = pygame.Rect(416, cur_y - 2, 22, 20)
        canvas.blit(f_small_b.render("▾ SALAS DE VOZ", True, (175, 182, 195)), (250, cur_y))
        pygame.draw.rect(canvas, (22, 26, 34), self.add_voice_ch_rect, border_radius=4)
        pygame.draw.rect(canvas, (110, 230, 165), self.add_voice_ch_rect, 1, border_radius=4)
        canvas.blit(f_body_b.render("+", True, (225, 250, 235)), (self.add_voice_ch_rect.x + 6, self.add_voice_ch_rect.y + 1))
        cur_y += 22

        for vc_name, cap_str in self.voice_channels[:4]:
            if cur_y > 530:
                break
            rect = pygame.Rect(246, cur_y, 192, 23)
            self.voice_rects.append((rect, vc_name))
            is_act = self.active_voice == vc_name
            if is_act:
                pygame.draw.rect(canvas, (22, 48, 34), rect, border_radius=5)
                pygame.draw.rect(canvas, (105, 235, 150), rect, 1, border_radius=5)
                pygame.draw.circle(canvas, (105, 235, 150), (rect.x + 11, rect.centery), 4)
            else:
                canvas.blit(f_small.render("🔊", True, (175, 182, 195)), (250, cur_y + 3))

            canvas.blit(
                (f_body_b if is_act else f_body).render(vc_name[:11], True, (242, 248, 244) if is_act else (188, 194, 206)),
                (272, cur_y + 3),
            )
            # Badge [🔴 LIVE] si se está transmitiendo en esta sala
            if self.is_streaming and (is_act or (not self.active_voice and vc_name == "General")):
                live_pill = pygame.Rect(350, cur_y + 3, 46, 17)
                pygame.draw.rect(canvas, (180, 30, 30), live_pill, border_radius=4)
                canvas.blit(f_small_b.render("🔴 LIVE", True, (255, 255, 255)), (live_pill.x + 4, live_pill.y + 1))
            else:
                pill = pygame.Rect(400, cur_y + 3, 34, 17)
                pygame.draw.rect(canvas, (16, 18, 24), pill, border_radius=4)
                pygame.draw.rect(canvas, (95, 102, 118), pill, 1, border_radius=4)
                c_s = f_small.render(cap_str, True, (205, 210, 222))
                canvas.blit(c_s, (pill.centerx - c_s.get_width() // 2, pill.y + 1))
            cur_y += 25

        # 4. Botón Go Live (Transmitir en Vivo juego o pantalla a 30 FPS)
        if self.is_streaming:
            _draw_cut_rect(canvas, self.stream_btn_rect, (62, 18, 18), (255, 85, 85), cut=4, border_w=1)
            canvas.blit(
                f_small_b.render("🔴 EN VIVO — DETENER", True, (255, 225, 225)),
                (self.stream_btn_rect.x + 24, self.stream_btn_rect.y + 7),
            )
        else:
            _draw_cut_rect(canvas, self.stream_btn_rect, (20, 28, 40), (110, 195, 255), cut=4, border_w=1)
            canvas.blit(
                f_small_b.render("🎥 GO LIVE (30 FPS)", True, (225, 240, 255)),
                (self.stream_btn_rect.x + 32, self.stream_btn_rect.y + 7),
            )

        # 5. Pie de columna: invitación y Sound Deck (Soundboard)
        inv = self.bridge.get_or_create_invite(grp["id"])
        footer_rect = pygame.Rect(246, 582, 106, 28)
        self.soundboard_btn_rect = pygame.Rect(356, 582, 82, 28)
        _draw_cut_rect(canvas, footer_rect, (14, 17, 22), (85, 92, 108), cut=4, border_w=1)
        canvas.blit(
            f_small_b.render(f"🔗 {inv['code'][:6]}", True, (185, 210, 245)),
            (footer_rect.x + 8, footer_rect.y + 7),
        )
        _draw_cut_rect(canvas, self.soundboard_btn_rect, (24, 28, 38), (110, 195, 255), cut=4, border_w=1)
        canvas.blit(
            f_small_b.render("🔊 SOUNDS", True, (240, 245, 255)),
            (self.soundboard_btn_rect.x + 7, self.soundboard_btn_rect.y + 7),
        )

    def _draw_dynamic_members_sidebar(
        self,
        canvas: pygame.Surface,
        grp: Dict[str, Any],
    ) -> None:
        """Renderiza la columna derecha de miembros propia de cada comunidad."""
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]
        f_body_b = _PACK.fonts["body_bold"]

        # Si es Night Raid y no hay actividad en juego ni sala de voz conectada, usar sprites base
        presence = self.bridge.repo.get_presence(self.bridge.user_id)
        has_custom = presence and presence.get("custom_status") and presence.get("custom_status") != "En el Menú"
        if grp["id"].replace("-", "_") == "night_raid" and not has_custom and not self.active_voice:
            mem_on = _PACK.sprites.get("nr_members_online.png")
            mem_aw = _PACK.sprites.get("nr_members_away.png")
            if mem_on is not None:
                canvas.blit(mem_on, (1074, 194))
            if mem_aw is not None:
                canvas.blit(mem_aw, (1074, 446))
            return

        # Para cualquier otra comunidad o grupo creado por el usuario, limpiar y dibujar su lista real
        pygame.draw.rect(canvas, (7, 8, 10), pygame.Rect(1068, 152, 196, 464))
        members = self.bridge.list_community_members_display(grp["id"])
        online_m = [m for m in members if m[1] == "En línea"]
        away_m = [m for m in members if m[1] != "En línea"]

        y = 162
        canvas.blit(f_small_b.render(f"▸ EN LÍNEA — {len(online_m)}", True, (185, 192, 205)), (1076, y))
        pygame.draw.line(canvas, (45, 50, 60), (1076, y + 18), (1254, y + 18), 1)
        y += 26

        for uname, status, activity, role in online_m[:6]:
            card_r = pygame.Rect(1074, y, 182, 42)
            _draw_cut_rect(canvas, card_r, (15, 18, 24), (72, 78, 92), cut=4, border_w=1)
            pygame.draw.circle(canvas, (95, 230, 145), (card_r.x + 16, card_r.centery), 5)
            canvas.blit(f_body_b.render(uname[:12], True, (242, 245, 250)), (card_r.x + 28, card_r.y + 5))
            r_col = (255, 200, 90) if role == "OWNER" else ((115, 195, 255) if role in ("ADMIN", "MOD") else (150, 156, 168))
            canvas.blit(f_small_b.render(role, True, r_col), (card_r.right - 52, card_r.y + 6))
            if uname == "ALEX":
                if self.is_streaming:
                    st_game = self.active_stream_info.get("title", "Juego") if self.active_stream_info else "Juego"
                    act_txt = f"🔴 En vivo: {st_game[:12]}"
                elif self.active_voice:
                    act_txt = f"🔊 {self.active_voice}"
                else:
                    act_txt = activity[:22]
            else:
                act_txt = activity[:22]
            act_col = (255, 115, 115) if (uname == "ALEX" and self.is_streaming) else (165, 172, 186)
            canvas.blit(f_small.render(act_txt, True, act_col), (card_r.x + 28, card_r.y + 23))
            y += 48

        y += 10
        canvas.blit(f_small_b.render(f"▸ AUSENTE / OFFLINE — {len(away_m)}", True, (160, 166, 178)), (1076, y))
        pygame.draw.line(canvas, (45, 50, 60), (1076, y + 18), (1254, y + 18), 1)
        y += 26
        for uname, status, activity, role in away_m[:3]:
            card_r = pygame.Rect(1074, y, 182, 38)
            _draw_cut_rect(canvas, card_r, (12, 14, 18), (55, 60, 70), cut=4, border_w=1)
            pygame.draw.circle(canvas, (235, 175, 70), (card_r.x + 16, card_r.centery), 4)
            canvas.blit(f_body_b.render(uname[:12], True, (195, 200, 210)), (card_r.x + 28, card_r.y + 4))
            canvas.blit(f_small.render(activity[:22], True, (135, 140, 152)), (card_r.x + 28, card_r.y + 20))
            y += 44

    def draw(self, screen: pygame.Surface) -> None:
        _PACK.ensure_loaded()
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        base_surf = _PACK.bases.get("base_community.png")
        if base_surf is not None:
            canvas.blit(base_surf, (0, 0))
        else:
            canvas.fill((8, 9, 12))

        f_title = _PACK.fonts["title"]
        f_sub = _PACK.fonts["card_sub"]
        f_body = _PACK.fonts["body"]
        f_body_b = _PACK.fonts["body_bold"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        grp = self._active_group_dict()
        topic_map = dict(self.text_channels)

        # 2. Columna izquierda de servidores (soporta los grupos del catálogo y los grupos creados por el usuario)
        self.server_icon_rects = [(pygame.Rect(184, 108, 44, 42), -1)]
        slot_ys = [160, 222, 282, 342, 402, 462]
        default_ids = {g["id"] for g in COMMUNITIES_CATALOG}

        for slot_i, sy in enumerate(slot_ys):
            r_slot = pygame.Rect(180, sy, 52, 52)
            if slot_i < len(self.groups):
                g_item = self.groups[slot_i]
                self.server_icon_rects.append((r_slot, slot_i))
                # Si es un grupo creado por el usuario, pintar su icono con iniciales sobre el slot
                if g_item["id"] not in default_ids or slot_i != g_item.get("emblem_idx", slot_i):
                    _draw_cut_rect(canvas, r_slot, (16, 20, 28), (95, 105, 122), cut=6, border_w=1)
                    emb = _PACK.sprites.get(f"emblem_{g_item['emblem_idx'] % 6}.png")
                    if emb is not None and not g_item.get("is_custom"):
                        canvas.blit(pygame.transform.smoothscale(emb, (42, 42)), (r_slot.x + 5, r_slot.y + 5))
                    else:
                        ini = g_item["name"][:2].upper()
                        ini_s = f_body_b.render(ini, True, (242, 245, 252))
                        canvas.blit(
                            ini_s,
                            (r_slot.centerx - ini_s.get_width() // 2, r_slot.centery - ini_s.get_height() // 2),
                        )
                if slot_i == self.active_group_idx:
                    pygame.draw.rect(canvas, (242, 244, 248), r_slot, 2, border_radius=6)

        # Botón [+] al final del riel de servidores (x=180, y=522) para crear un nuevo servidor desde acá
        plus_srv_rect = pygame.Rect(180, 522, 52, 52)
        self.server_icon_rects.append((plus_srv_rect, -2))

        # 3. Cabecera del servidor activo (nombre, subtítulo, cantidad real de miembros y canales)
        pygame.draw.rect(canvas, (12, 14, 18), pygame.Rect(278, 88, 360, 48))
        emb = _PACK.sprites.get(f"emblem_{grp['emblem_idx'] % 6}.png")
        if emb is not None and not grp.get("is_custom"):
            pygame.draw.rect(canvas, (12, 14, 18), pygame.Rect(218, 88, 48, 48))
            canvas.blit(pygame.transform.smoothscale(emb, (42, 42)), (221, 91))
        elif grp.get("is_custom"):
            emb_box = pygame.Rect(219, 89, 44, 44)
            _draw_cut_rect(canvas, emb_box, (18, 24, 34), (110, 195, 255), cut=5, border_w=2)
            ini_s = f_body_b.render(grp["name"][:2].upper(), True, (245, 247, 252))
            canvas.blit(ini_s, (emb_box.centerx - ini_s.get_width() // 2, emb_box.centery - ini_s.get_height() // 2))

        canvas.blit(f_title.render(grp["name"][:22], True, (245, 247, 252)), (280, 91))
        sub_txt = f"{grp['members_count']} MIEMBROS • {len(self.text_channels)} CANALES • CÓD: {grp.get('invite_code', 'CCI')}"
        canvas.blit(f_sub.render(sub_txt, True, (180, 185, 196)), (280, 115))

        # 4. Columna izquierda de canales propia del grupo activo
        self._draw_dynamic_channels_sidebar(canvas, grp)

        # 5. Cabecera del canal activo y barra de escritura
        pygame.draw.rect(canvas, (14, 16, 20), pygame.Rect(462, 150, 385, 28))
        ch_desc = topic_map.get(self.current_channel, f"Canal #{self.current_channel} de {grp['name']}")
        canvas.blit(f_body_b.render(f"#  {self.current_channel}", True, (245, 247, 252)), (466, 155))
        canvas.blit(f_small.render(ch_desc[:45], True, (175, 180, 192)), (615, 158))

        if not self.input_focused and not self.input_text:
            pygame.draw.rect(canvas, (14, 16, 20), pygame.Rect(504, 586, 370, 24))
            canvas.blit(
                f_body.render(f"Enviar un mensaje a #{self.current_channel}...", True, (150, 155, 168)),
                (508, 590),
            )

        # 6. Área central de mensajes con recorte (clip), ajuste multilínea y scroll real
        vp = self.chat_viewport
        items_heights: List[Tuple[str, Any, int]] = []
        is_night_raid = grp["id"].replace("-", "_") == "night_raid"

        if self.current_channel == "general" and is_night_raid:
            default_sprites = [
                ("nr_msg_0_alex.png", 44),
                ("nr_msg_1_mira.png", 42),
                ("nr_msg_2_kai.png", 42),
                ("nr_msg_3_alex.png", 38),
                ("nr_msg_4_mira_skin.png", 132),
                ("nr_msg_5_kai.png", 44),
            ]
            for sp_name, sh in default_sprites:
                items_heights.append(("sprite", sp_name, sh))
            for msg in self.chat_messages[len(self.DEFAULT_GENERAL_MESSAGES) :]:
                wrapped = _wrap_lines(msg.get("text", ""), f_body, 455)
                h = max(50, 32 + len(wrapped) * 18)
                if msg.get("attachment"):
                    h += 92
                items_heights.append(("msg", (msg, wrapped), h))
        else:
            items_heights.append(("welcome", (self.current_channel, ch_desc), 54))
            for msg in self.chat_messages:
                wrapped = _wrap_lines(msg.get("text", ""), f_body, 455)
                h = max(52, 32 + len(wrapped) * 18)
                if msg.get("attachment"):
                    h += 92
                items_heights.append(("msg", (msg, wrapped), h))

        gap = 8
        total_h = sum(h for _, _, h in items_heights) + max(0, len(items_heights) - 1) * gap
        self.max_scroll = max(0, total_h - (vp.height - 14))
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

        old_clip = canvas.get_clip()
        canvas.set_clip(vp)

        self.attachment_preview_rects.clear()
        cur_y = vp.y + 8 - self.scroll_offset
        for kind, payload, h in items_heights:
            if cur_y + h >= vp.y and cur_y <= vp.bottom:
                if kind == "sprite":
                    sp = _PACK.sprites.get(payload)
                    if sp is not None:
                        canvas.blit(sp, (470, cur_y))
                    if payload == "nr_msg_4_mira_skin.png":
                        self.heart_rect = pygame.Rect(528, cur_y + 114, 46, 22)
                        self.fire_rect = pygame.Rect(578, cur_y + 114, 46, 22)
                        if self.user_hearted:
                            pygame.draw.rect(canvas, (36, 40, 50), self.heart_rect, border_radius=4)
                            pygame.draw.rect(canvas, (242, 244, 248), self.heart_rect, 1, border_radius=4)
                            canvas.blit(
                                f_small_b.render(f"♥ {self.reaction_heart}", True, (245, 247, 252)),
                                (self.heart_rect.x + 10, self.heart_rect.y + 4),
                            )
                        if self.user_fired:
                            pygame.draw.rect(canvas, (36, 40, 50), self.fire_rect, border_radius=4)
                            pygame.draw.rect(canvas, (242, 244, 248), self.fire_rect, 1, border_radius=4)
                            canvas.blit(
                                f_small_b.render(f"🔥 {self.reaction_fire}", True, (245, 247, 252)),
                                (self.fire_rect.x + 10, self.fire_rect.y + 4),
                            )
                elif kind == "welcome":
                    ch_title, ch_sub = payload
                    info_rect = pygame.Rect(470, cur_y, 536, h)
                    _draw_cut_rect(canvas, info_rect, (16, 18, 23), (85, 92, 106), cut=5, border_w=1)
                    canvas.blit(
                        f_body_b.render(f"Bienvenido a #{ch_title} ({grp['name']})", True, (242, 244, 248)),
                        (484, cur_y + 8),
                    )
                    canvas.blit(f_sub.render(ch_sub[:64], True, (175, 180, 192)), (484, cur_y + 28))
                elif kind == "msg":
                    msg_dict, wrapped_lines = payload
                    txt = msg_dict.get("text", "")
                    is_mentioned = ("@ALEX" in txt.upper()) or ("@EVERYONE" in txt.upper())
                    m_rect = pygame.Rect(470, cur_y, 536, h)
                    if is_mentioned:
                        _draw_cut_rect(canvas, m_rect, (28, 25, 18), (245, 195, 65), cut=5, border_w=1)
                        pygame.draw.rect(canvas, (245, 195, 65), pygame.Rect(m_rect.x, m_rect.y, 4, m_rect.height), border_radius=2)
                    else:
                        _draw_cut_rect(canvas, m_rect, (18, 20, 26), (72, 78, 90), cut=5, border_w=1)

                    author = msg_dict.get("author", "ALEX").upper()
                    av_key = "av_mira.png" if "MIRA" in author else ("av_kai.png" if "KAI" in author else "av_alex.png")
                    av_sp = _PACK.sprites.get(av_key)
                    if av_sp is not None:
                        canvas.blit(av_sp, (478, cur_y + 7))
                    canvas.blit(f_body_b.render(author, True, (244, 246, 250)), (526, cur_y + 7))
                    t_x = 526 + f_body_b.size(author)[0] + 12
                    canvas.blit(f_small.render(msg_dict.get("time", "Hoy"), True, (150, 156, 168)), (t_x, cur_y + 9))

                    line_y = cur_y + 26
                    for line in wrapped_lines:
                        if "@" in line:
                            words = line.split(" ")
                            cur_x = 526
                            for w in words:
                                if w.startswith("@") and len(w) > 1:
                                    w_surf = f_body_b.render(w, True, (255, 220, 100) if "EVERYONE" in w.upper() else (125, 210, 255))
                                    w_w, w_h = w_surf.get_size()
                                    badge_bg = (60, 48, 16) if "EVERYONE" in w.upper() else (24, 44, 68)
                                    pygame.draw.rect(canvas, badge_bg, pygame.Rect(cur_x - 2, line_y - 1, w_w + 4, w_h + 2), border_radius=3)
                                    canvas.blit(w_surf, (cur_x, line_y))
                                    cur_x += w_w + 6
                                else:
                                    w_surf = f_body.render(w, True, (226, 230, 238))
                                    canvas.blit(w_surf, (cur_x, line_y))
                                    cur_x += w_surf.get_width() + 6
                        else:
                            canvas.blit(f_body.render(line, True, (226, 230, 238)), (526, line_y))
                        line_y += 18

                    # Miniatura de captura adjunta si existe
                    if msg_dict.get("attachment"):
                        att = msg_dict["attachment"]
                        thumb_r = pygame.Rect(526, line_y + 4, 140, 78)
                        self.attachment_preview_rects.append((thumb_r, att.get("path", "")))
                        _draw_cut_rect(canvas, thumb_r, (12, 14, 18), (110, 195, 255), cut=4, border_w=1)
                        th = get_screenshot_thumbnail(att.get("path", ""), width=136, height=74)
                        if th is not None:
                            canvas.blit(th, (thumb_r.x + 2, thumb_r.y + 2))
                        else:
                            canvas.blit(f_small_b.render("📸 FOTO", True, (180, 205, 235)), (thumb_r.x + 40, thumb_r.centery - 8))
                        canvas.blit(f_small_b.render(f"📎 {att.get('filename', 'captura.png')[:22]}", True, (215, 235, 255)), (thumb_r.right + 12, thumb_r.y + 16))
                        canvas.blit(f_small.render("[Clic para ampliar]", True, (140, 148, 162)), (thumb_r.right + 12, thumb_r.y + 38))
            cur_y += h + gap

        canvas.set_clip(old_clip)

        # Barra de scroll derecha
        track_top, track_h = 200, 356
        pygame.draw.rect(canvas, (18, 20, 25), pygame.Rect(1030, track_top, 6, track_h), border_radius=3)
        if self.max_scroll > 0:
            thumb_h = max(36, int(track_h * (vp.height / (total_h + 1))))
            thumb_y = track_top + int((track_h - thumb_h) * (self.scroll_offset / self.max_scroll))
        else:
            thumb_h = track_h
            thumb_y = track_top
        pygame.draw.rect(canvas, (170, 176, 188), pygame.Rect(1030, thumb_y, 6, thumb_h), border_radius=3)

        # 6b. Widget flotante PiP (Picture-in-Picture) de transmisión activa
        if self.is_streaming:
            _draw_cut_rect(canvas, self.stream_pip_rect, (14, 17, 24), (255, 75, 75), cut=6, border_w=2)
            inner_prev = pygame.Rect(self.stream_pip_rect.x + 4, self.stream_pip_rect.y + 4, self.stream_pip_rect.width - 8, 66)
            pygame.draw.rect(canvas, (7, 9, 13), inner_prev, border_radius=4)
            # Scanlines sutiles en miniatura
            for sy in range(inner_prev.y + 6, inner_prev.bottom - 4, 10):
                pygame.draw.line(canvas, (18, 24, 34), (inner_prev.x + 4, sy), (inner_prev.right - 4, sy), 1)

            st_title = self.active_stream_info.get("title", "En Vivo") if self.active_stream_info else "En Vivo"
            # Badge LIVE
            live_badge = pygame.Rect(inner_prev.x + 6, inner_prev.y + 6, 44, 16)
            pygame.draw.rect(canvas, (200, 30, 30), live_badge, border_radius=3)
            canvas.blit(f_small_b.render("LIVE", True, (255, 255, 255)), (live_badge.x + 8, live_badge.y + 1))
            canvas.blit(f_small.render("30 FPS", True, (190, 200, 215)), (inner_prev.right - 44, inner_prev.y + 7))

            canvas.blit(f_small_b.render(st_title[:16], True, (244, 246, 252)), (self.stream_pip_rect.x + 8, self.stream_pip_rect.y + 73))
            canvas.blit(f_small.render("🗗 Clic para Cine", True, (135, 195, 255)), (self.stream_pip_rect.x + 8, self.stream_pip_rect.y + 89))

        # 7. Botón [📎] para adjuntar capturas F12
        _draw_cut_rect(
            canvas,
            self.attach_btn_rect,
            (32, 58, 86) if self.pending_attachment else (22, 26, 36),
            (110, 195, 255) if self.pending_attachment else (85, 92, 108),
            cut=4,
            border_w=1,
        )
        canvas.blit(f_body_b.render("📎", True, (245, 248, 255)), (self.attach_btn_rect.x + 8, self.attach_btn_rect.y + 8))

        # Chip de captura F12 adjunta pendiente
        if self.pending_attachment:
            chip_r = pygame.Rect(500, 552, 280, 22)
            self.pending_chip_cancel_rect = pygame.Rect(chip_r.right - 20, chip_r.y + 2, 18, 18)
            _draw_cut_rect(canvas, chip_r, (20, 36, 52), (110, 195, 255), cut=4, border_w=1)
            canvas.blit(f_small.render(f"📎 {self.pending_attachment['filename'][:26]}", True, (235, 242, 255)), (chip_r.x + 8, chip_r.y + 3))
            canvas.blit(f_small_b.render("×", True, (245, 120, 120)), (self.pending_chip_cancel_rect.x + 4, self.pending_chip_cancel_rect.y + 1))

        # Popup flotante de autocompletado de menciones
        if self.autocomplete_active and self.autocomplete_candidates:
            pop_w = 210
            pop_h = 24 + len(self.autocomplete_candidates) * 26
            pop_rect = pygame.Rect(500, 580 - pop_h - 4, pop_w, pop_h)
            _draw_cut_rect(canvas, pop_rect, (16, 20, 28), (110, 195, 255), cut=6, border_w=1)
            canvas.blit(f_small_b.render("MIEMBROS // MENCIONES (TAB)", True, (160, 190, 230)), (pop_rect.x + 10, pop_rect.y + 5))
            self.autocomplete_rects.clear()
            for ci, cand in enumerate(self.autocomplete_candidates):
                item_r = pygame.Rect(pop_rect.x + 6, pop_rect.y + 22 + ci * 26, pop_w - 12, 22)
                self.autocomplete_rects.append((item_r, cand))
                is_cur = ci == self.autocomplete_selected_idx
                if is_cur:
                    pygame.draw.rect(canvas, (35, 55, 80), item_r, border_radius=4)
                    pygame.draw.rect(canvas, (110, 195, 255), item_r, 1, border_radius=4)
                c_col = (255, 215, 90) if "EVERYONE" in cand else (240, 245, 252)
                canvas.blit(f_body_b.render(cand, True, c_col), (item_r.x + 8, item_r.y + 3))

        # 8. Barra de entrada de texto inferior
        if self.input_focused or self.input_text:
            pygame.draw.rect(canvas, (14, 16, 20), pygame.Rect(504, 586, 480, 24))
            if self.input_focused:
                pygame.draw.rect(canvas, (240, 242, 248), pygame.Rect(500, 580, 535, 36), 1, border_radius=5)
            txt = self.input_text + ("|" if self.input_focused else "")
            canvas.blit(
                f_body.render(txt or f"Enviar un mensaje a #{self.current_channel}...", True, (242, 244, 248)),
                (508, 590),
            )

        # 8. Columna derecha de miembros dinámica para la comunidad activa
        self._draw_dynamic_members_sidebar(canvas, grp)

        # Toast de estado en el asistente inferior si se creó un canal o se copió invitación
        if self.status_toast:
            pygame.draw.rect(canvas, (10, 12, 15), pygame.Rect(124, 650, 520, 42))
            canvas.blit(f_body_b.render(f"✓ {self.status_toast}", True, (115, 235, 165)), (128, 654))
            canvas.blit(
                f_small.render("Usá [+] en la barra de canales para crear canales o [Invitar] para compartir el grupo.", True, (185, 190, 202)),
                (128, 674),
            )

        # 9. Barra lateral compartida
        if self.sidebar_surface is not None and self.sidebar_font is not None:
            draw_sidebar(canvas, self.sidebar_surface, "community", self.sidebar_font)

        # 10. Modal activo (Crear Canal / Sala de Voz / Invitar con Código y Link)
        if self.modal_mode is not None:
            self._draw_community_modal(canvas, grp)

        if screen.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        else:
            screen.blit(canvas, (0, 0))

    def _draw_community_modal(self, surface: pygame.Surface, grp: Dict[str, Any]) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        f_title = _PACK.fonts["title"]
        f_body = _PACK.fonts["body"]
        f_body_b = _PACK.fonts["body_bold"]
        f_sub = _PACK.fonts["card_sub"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        if self.modal_mode == "soundboard":
            box = pygame.Rect(360, 160, 560, 360)
            _draw_cut_rect(surface, box, (15, 17, 23), (110, 195, 255), cut=10, border_w=2)
            surface.blit(f_title.render("SOUND DECK // SOUNDBOARD", True, (244, 246, 250)), (box.x + 24, box.y + 18))
            surface.blit(
                f_sub.render(f"Efectos en vivo para salas de voz (Clic en un pad o presiona 1..6):", True, (185, 192, 206)),
                (box.x + 24, box.y + 46),
            )

            self.sound_pad_rects.clear()
            grid_xs = [box.x + 24, box.x + 196, box.x + 368]
            grid_ys = [box.y + 76, box.y + 168]

            for i, item in enumerate(SOUNDBOARD_PRESETS):
                col = i % 3
                row = i // 3
                pad_r = pygame.Rect(grid_xs[col], grid_ys[row], 162, 80)
                self.sound_pad_rects.append((pad_r, item["name"]))

                _draw_cut_rect(surface, pad_r, (22, 26, 36), (90, 100, 120), cut=6, border_w=1)

                badge_r = pygame.Rect(pad_r.right - 26, pad_r.y + 6, 20, 18)
                _draw_cut_rect(surface, badge_r, (12, 14, 18), (140, 146, 160), cut=3, border_w=1)
                surface.blit(f_small_b.render(item["key"], True, (230, 235, 245)), (badge_r.x + 6, badge_r.y + 2))

                surface.blit(f_body.render(item["icon"], True, (245, 247, 252)), (pad_r.x + 12, pad_r.y + 12))
                surface.blit(f_body_b.render(item["name"], True, (245, 247, 252)), (pad_r.x + 38, pad_r.y + 12))
                surface.blit(f_small.render(item["desc"][:22], True, (165, 172, 186)), (pad_r.x + 12, pad_r.y + 44))

            if self.status_toast:
                surface.blit(f_small_b.render(f"✓ {self.status_toast}", True, (115, 235, 165)), (box.x + 24, box.y + 264))

            close_rect = pygame.Rect(580, 470, 120, 34)
            _draw_cut_rect(surface, close_rect, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Cerrar", True, (12, 14, 18)), (close_rect.x + 36, close_rect.y + 9))
            return

        if self.modal_mode == "attach_picker":
            box = pygame.Rect(330, 110, 620, 440)
            _draw_cut_rect(surface, box, (15, 18, 24), (110, 195, 255), cut=10, border_w=2)
            surface.blit(f_title.render("ADJUNTAR CAPTURA F12 // CAPTURAS/", True, (244, 246, 250)), (box.x + 24, box.y + 18))
            surface.blit(
                f_sub.render(f"Seleccioná una captura de pantalla guardada para enviar a {grp['name'][:14]}:", True, (185, 192, 206)),
                (box.x + 24, box.y + 46),
            )

            self.screenshot_picker_rects.clear()
            snaps = list_available_screenshots(limit=6)

            if not snaps:
                info_r = pygame.Rect(box.x + 24, box.y + 90, box.width - 48, 120)
                _draw_cut_rect(surface, info_r, (18, 22, 30), (85, 95, 110), cut=6, border_w=1)
                surface.blit(
                    f_body_b.render("📸 No hay capturas en la carpeta capturas/", True, (240, 244, 252)),
                    (info_r.x + 20, info_r.y + 30),
                )
                surface.blit(
                    f_small.render("Presioná F12 en cualquier momento dentro de un juego o consola para tomar fotos.", True, (170, 178, 192)),
                    (info_r.x + 20, info_r.y + 60),
                )
            else:
                grid_xs = [box.x + 24, box.x + 316]
                grid_ys = [box.y + 80, box.y + 175, box.y + 270]
                for si, snap in enumerate(snaps):
                    col = si % 2
                    row = si // 2
                    card_r = pygame.Rect(grid_xs[col], grid_ys[row], 280, 84)
                    self.screenshot_picker_rects.append((card_r, snap))
                    _draw_cut_rect(surface, card_r, (22, 26, 36), (90, 105, 128), cut=6, border_w=1)

                    th = get_screenshot_thumbnail(snap["path"], width=96, height=60)
                    if th is not None:
                        surface.blit(th, (card_r.x + 10, card_r.y + 12))
                    else:
                        pygame.draw.rect(surface, (12, 14, 18), pygame.Rect(card_r.x + 10, card_r.y + 12, 96, 60))
                        surface.blit(f_small_b.render("PNG", True, (140, 150, 168)), (card_r.x + 44, card_r.y + 32))

                    surface.blit(f_small_b.render(snap["filename"][:18], True, (242, 246, 252)), (card_r.x + 114, card_r.y + 14))
                    surface.blit(f_small.render(snap["size_str"], True, (160, 168, 180)), (card_r.x + 114, card_r.y + 36))
                    surface.blit(f_small.render(snap["time_str"], True, (130, 138, 150)), (card_r.x + 114, card_r.y + 54))

            close_btn = pygame.Rect(580, 505, 120, 32)
            _draw_cut_rect(surface, close_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Cerrar", True, (12, 14, 18)), (close_btn.x + 36, close_btn.y + 8))
            return

        if self.modal_mode == "image_preview":
            overlay_dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay_dark.fill((0, 0, 0, 235))
            surface.blit(overlay_dark, (0, 0))

            fn = os.path.basename(self.preview_image_path or "captura.png")
            surface.blit(f_title.render(f"VISTA PREVIA // {fn}", True, (244, 246, 250)), (180, 28))
            surface.blit(f_small.render("Presioná ESC o Cerrar para volver al chat", True, (170, 175, 188)), (180, 56))

            if self.preview_image_path and os.path.isfile(self.preview_image_path):
                try:
                    img = pygame.image.load(self.preview_image_path)
                    iw, ih = img.get_size()
                    max_w, max_h = 920, 520
                    scale = min(max_w / max(1, iw), max_h / max(1, ih), 1.0)
                    dw, dh = int(iw * scale), int(ih * scale)
                    scaled_img = pygame.transform.smoothscale(img, (dw, dh))
                    frame_r = pygame.Rect(SCREEN_WIDTH // 2 - dw // 2, 335 - dh // 2, dw, dh)
                    pygame.draw.rect(surface, (110, 195, 255), frame_r.inflate(4, 4), 2, border_radius=4)
                    surface.blit(scaled_img, frame_r)
                except Exception:
                    pass

            close_btn = pygame.Rect(580, 620, 120, 32)
            _draw_cut_rect(surface, close_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Cerrar", True, (12, 14, 18)), (close_btn.x + 36, close_btn.y + 8))
            return

        if self.modal_mode == "stream_picker":
            box = pygame.Rect(320, 100, 640, 460)
            _draw_cut_rect(surface, box, (15, 18, 24), (255, 80, 80), cut=10, border_w=2)
            surface.blit(f_title.render("TRANSMISIÓN EN VIVO // GO LIVE", True, (244, 246, 250)), (box.x + 24, box.y + 16))
            surface.blit(
                f_sub.render(f"Elegí qué juego querés transmitir en vivo a {grp['name'][:18]}:", True, (185, 192, 206)),
                (box.x + 24, box.y + 44),
            )

            # Botones de resolución
            btn_720 = pygame.Rect(box.x + 24, box.y + 70, 110, 26)
            btn_1080 = pygame.Rect(box.x + 144, box.y + 70, 110, 26)
            is_720 = self.stream_res_selected == "720p"
            _draw_cut_rect(surface, btn_720, (30, 45, 65) if is_720 else (20, 24, 32), (110, 195, 255) if is_720 else (80, 88, 102), cut=4, border_w=1)
            _draw_cut_rect(surface, btn_1080, (30, 45, 65) if not is_720 else (20, 24, 32), (110, 195, 255) if not is_720 else (80, 88, 102), cut=4, border_w=1)
            surface.blit(f_small_b.render("720p @ 30 FPS", True, (245, 248, 255) if is_720 else (170, 175, 188)), (btn_720.x + 12, btn_720.y + 6))
            surface.blit(f_small_b.render("1080p @ 60 FPS", True, (245, 248, 255) if not is_720 else (170, 175, 188)), (btn_1080.x + 10, btn_1080.y + 6))
            surface.blit(f_small.render("Bitrate optimizado • LiveKit SFU Ready", True, (140, 150, 168)), (box.x + 270, box.y + 75))

            self.stream_game_picker_rects.clear()
            grid_xs = [box.x + 24, box.x + 324]
            grid_ys = [box.y + 112, box.y + 196, box.y + 280]

            for gi, g_item in enumerate(CCI_TITLES[:6]):
                col = gi % 2
                row = gi // 2
                card_r = pygame.Rect(grid_xs[col], grid_ys[row], 292, 72)
                self.stream_game_picker_rects.append((card_r, g_item))
                _draw_cut_rect(surface, card_r, (22, 26, 36), (90, 105, 128), cut=6, border_w=1)

                icon_box = pygame.Rect(card_r.x + 10, card_r.y + 10, 52, 52)
                pygame.draw.rect(surface, (12, 14, 18), icon_box, border_radius=4)
                pygame.draw.rect(surface, (110, 195, 255), icon_box, 1, border_radius=4)
                surface.blit(f_body_b.render("🎮", True, (240, 245, 255)), (icon_box.x + 14, icon_box.y + 14))

                surface.blit(f_body_b.render(g_item["title"][:18], True, (244, 246, 252)), (card_r.x + 72, card_r.y + 12))
                surface.blit(f_small.render(f"ID: {g_item['game_id']}", True, (160, 168, 180)), (card_r.x + 72, card_r.y + 32))
                surface.blit(f_small_b.render("▶ TRANSMITIR", True, (255, 95, 95)), (card_r.x + 72, card_r.y + 49))

            close_btn = pygame.Rect(580, 505, 120, 32)
            _draw_cut_rect(surface, close_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Cancelar", True, (12, 14, 18)), (close_btn.x + 30, close_btn.y + 8))
            return

        if self.modal_mode == "stream_theater":
            overlay_dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay_dark.fill((0, 0, 0, 240))
            surface.blit(overlay_dark, (0, 0))

            theater_box = pygame.Rect(180, 30, 920, 595)
            _draw_cut_rect(surface, theater_box, (10, 12, 16), (255, 75, 75), cut=8, border_w=2)

            st_title = self.active_stream_info.get("title", "Transmisión en Vivo") if self.active_stream_info else "Transmisión en Vivo"
            st_res = self.active_stream_info.get("resolution", "720p") if self.active_stream_info else "720p"
            st_fps = self.active_stream_info.get("fps", 30) if self.active_stream_info else 30

            # Cabecera de cine
            surface.blit(f_title.render(f"🔴 CINE // {st_title.upper()}", True, (244, 246, 250)), (theater_box.x + 20, theater_box.y + 16))
            surface.blit(
                f_small_b.render(f"{st_res.upper()} @ {st_fps} FPS • 1500 KBPS • LIVEKIT SFU • SIN RETARDO", True, (255, 120, 120)),
                (theater_box.x + 20, theater_box.y + 44),
            )

            # Pantalla central de video / cine
            screen_r = pygame.Rect(theater_box.x + 20, theater_box.y + 68, theater_box.width - 40, 490)
            pygame.draw.rect(surface, (5, 6, 8), screen_r, border_radius=6)
            pygame.draw.rect(surface, (35, 40, 52), screen_r, 1, border_radius=6)

            # Dibujar scanlines / grid de video simulando stream en vivo
            for y_line in range(screen_r.y + 10, screen_r.bottom - 10, 28):
                pygame.draw.line(surface, (14, 18, 25), (screen_r.x + 10, y_line), (screen_r.right - 10, y_line), 1)

            # Marco central simulado
            center_logo = f_title.render(f"[ {st_title} ]", True, (220, 226, 240))
            surface.blit(center_logo, (screen_r.centerx - center_logo.get_width() // 2, screen_r.centery - 24))
            sub_live = f_body_b.render("🔴 TRANSMISIÓN LOCAL DIRECTA EN TIEMPO REAL", True, (255, 95, 95))
            surface.blit(sub_live, (screen_r.centerx - sub_live.get_width() // 2, screen_r.centery + 12))

            # Barra de controles de cine
            btn_stop = pygame.Rect(460, 580, 170, 32)
            btn_close = pygame.Rect(646, 580, 170, 32)
            _draw_cut_rect(surface, btn_stop, (70, 22, 22), (255, 95, 95), cut=5, border_w=1)
            _draw_cut_rect(surface, btn_close, (24, 28, 38), (140, 150, 168), cut=5, border_w=1)
            surface.blit(f_small_b.render("⏹ DETENER STREAM", True, (255, 230, 230)), (btn_stop.x + 24, btn_stop.y + 8))
            surface.blit(f_small_b.render("🗗 MINIMIZAR A PiP", True, (230, 236, 246)), (btn_close.x + 26, btn_close.y + 8))
            return

        if self.modal_mode == "invite":
            box = pygame.Rect(390, 190, 500, 295)
            _draw_cut_rect(surface, box, (15, 17, 22), (240, 242, 248), cut=10, border_w=2)
            inv = self.bridge.get_or_create_invite(grp["id"])
            surface.blit(f_title.render(f"INVITAR A {grp['name'][:18]}", True, (244, 246, 250)), (box.x + 24, box.y + 20))
            surface.blit(
                f_sub.render("Compartí este código o link para que otros se unan a tus canales:", True, (185, 190, 200)),
                (box.x + 24, box.y + 52),
            )

            code_box = pygame.Rect(420, 266, 440, 34)
            _draw_cut_rect(surface, code_box, (10, 12, 16), (110, 210, 255), cut=5, border_w=1)
            surface.blit(
                f_body.render(f"CÓDIGO:  {inv['code']}     |     URI:  {inv['uri']}", True, (244, 246, 250)),
                (code_box.x + 12, code_box.y + 8),
            )

            btn_copy_code = pygame.Rect(420, 310, 130, 32)
            btn_copy_link = pygame.Rect(560, 310, 130, 32)
            btn_regen = pygame.Rect(700, 310, 150, 32)
            _draw_cut_rect(surface, btn_copy_code, (235, 238, 246), (255, 255, 255), cut=5, border_w=1)
            _draw_cut_rect(surface, btn_copy_link, (28, 34, 46), (130, 185, 255), cut=5, border_w=1)
            _draw_cut_rect(surface, btn_regen, (24, 27, 34), (130, 136, 150), cut=5, border_w=1)
            surface.blit(f_small_b.render("Copiar Código", True, (12, 14, 18)), (btn_copy_code.x + 20, btn_copy_code.y + 9))
            surface.blit(f_small_b.render("Copiar Link", True, (235, 240, 248)), (btn_copy_link.x + 26, btn_copy_link.y + 9))
            surface.blit(f_small_b.render("Generar Nuevo", True, (220, 224, 232)), (btn_regen.x + 28, btn_regen.y + 9))

            link_box = pygame.Rect(420, 358, 440, 32)
            _draw_cut_rect(surface, link_box, (10, 12, 16), (80, 86, 98), cut=4, border_w=1)
            surface.blit(f_small.render(inv["link"], True, (165, 195, 235)), (link_box.x + 10, link_box.y + 9))

            if self.status_toast:
                surface.blit(f_small_b.render(f"✓ {self.status_toast}", True, (115, 235, 165)), (420, 402))

            close_rect = pygame.Rect(580, 435, 120, 34)
            _draw_cut_rect(surface, close_rect, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
            surface.blit(_PACK.fonts["tab"].render("Listo", True, (12, 14, 18)), (close_rect.x + 40, close_rect.y + 9))
            return

        box = pygame.Rect(400, 195, 480, 265)
        _draw_cut_rect(surface, box, (15, 17, 22), (240, 242, 248), cut=10, border_w=2)

        if self.modal_mode == "create_text_channel":
            hdr = f"CREAR CANAL DE TEXTO EN {grp['name'][:14]}"
            lbl1 = "Nombre del canal (ej: clips-torneo):"
            lbl2 = "Tema o descripción del canal (Tab para cambiar):"
        elif self.modal_mode == "create_voice_channel":
            hdr = f"CREAR SALA DE VOZ EN {grp['name'][:14]}"
            lbl1 = "Nombre de la sala de voz (ej: Squad 2):"
            lbl2 = "Descripción de la sala (Tab para cambiar):"
        else:
            hdr = "CREAR NUEVO SERVIDOR / GRUPO"
            lbl1 = "Nombre del nuevo servidor:"
            lbl2 = "Descripción de la comunidad:"

        surface.blit(f_title.render(hdr, True, (244, 246, 250)), (box.x + 24, box.y + 20))
        surface.blit(f_small.render(lbl1, True, (185, 190, 200)), (box.x + 24, box.y + 52))

        name_rect = pygame.Rect(424, 268, 432, 34)
        _draw_cut_rect(
            surface,
            name_rect,
            (10, 12, 15),
            (245, 247, 252) if self.modal_field_idx == 0 else (95, 100, 114),
            cut=5,
            border_w=2 if self.modal_field_idx == 0 else 1,
        )
        c0 = "|" if self.modal_field_idx == 0 else ""
        prefix = "# " if self.modal_mode == "create_text_channel" else ("🔊 " if self.modal_mode == "create_voice_channel" else "")
        surface.blit(f_body.render(prefix + self.modal_input + c0, True, (244, 246, 250)), (name_rect.x + 12, name_rect.y + 8))

        surface.blit(f_small.render(lbl2, True, (185, 190, 200)), (box.x + 24, 314))
        topic_rect = pygame.Rect(424, 336, 432, 34)
        _draw_cut_rect(
            surface,
            topic_rect,
            (10, 12, 15),
            (245, 247, 252) if self.modal_field_idx == 1 else (95, 100, 114),
            cut=5,
            border_w=2 if self.modal_field_idx == 1 else 1,
        )
        c1 = "|" if self.modal_field_idx == 1 else ""
        surface.blit(f_body.render(self.modal_topic_input + c1, True, (215, 220, 230)), (topic_rect.x + 12, topic_rect.y + 8))

        ok_btn = pygame.Rect(520, 410, 115, 34)
        no_btn = pygame.Rect(645, 410, 115, 34)
        _draw_cut_rect(surface, ok_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
        _draw_cut_rect(surface, no_btn, (22, 25, 32), (130, 135, 148), cut=5, border_w=1)
        surface.blit(_PACK.fonts["tab"].render("Crear", True, (12, 14, 18)), (ok_btn.x + 36, ok_btn.y + 9))
        surface.blit(_PACK.fonts["tab"].render("Cancelar", True, (220, 224, 232)), (no_btn.x + 26, no_btn.y + 9))
