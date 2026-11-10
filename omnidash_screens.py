"""omnidash_screens.py - Suite Completa y Oficial Frutiger Aero de OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE y Libretro ctypes bridge.
Fidelidad absoluta a cada pantalla del repositorio oficial OmniDash:
1. HOME: Mosaico 1:1 cuadrado (Hero grande + 4 tarjetas cuadradas con arte en color + tarjeta 'My games & apps'),
   reflejos cristalinos en el agua, y 4 tarjetas esmeriladas inferiores (aero-home.jpg).
2. LIBRARY: Barra lateral con anillo de almacenamiento (72% used), buscador, selector de plataformas,
   panel derecho con SCROLL DOWN COMPLETO por rueda de ratón o teclado para los 68 juegos, cuadrícula 1:1 de 5 columnas,
   y barra de desplazamiento lateral (aero-library.jpg).
3. GAME DETAILS: Ficha técnica completa (garrison-details.js / screenshot-game-page.png) con carátula grande 1:1,
   botón verde gel 'PLAY GAME (60 FPS)', chips de capacidades, especificaciones y descripción.
4. SETTINGS: Panel oficial aero-settings.jpg con 8 categorías, orbes circulares de color y opciones agrupadas.
5. PROFILE: Ficha de usuario con 18,450 G, selector de avatar y logros desbloqueados.
6. COMMUNITY: Grupos de emulación C.C.I. (Seeker Hub, Night Raid) y jugadores en línea.
7. LAUNCH_ANIM: Animación cinemática oficial 'rises the game logo over key art' con audio startup.mp3.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path
import pygame

from omnidash_engine import OmniDashEngine, THEMES
from cci_console import CATALOG

ROOT = Path(__file__).resolve().parent

# ==============================================================================
# UTILIDADES DE RENDERIZADO DE CRISTAL TRANSLÚCIDO (ALTO CONTRASTE)
# ==============================================================================
def draw_glass_rect(surface: pygame.Surface, rect: pygame.Rect, bg_rgba: tuple, border_rgba: tuple | None = None, border_radius: int = 0, border_width: int = 1):
    """Dibuja un rectángulo con translucidez alfa real en Pygame-CE.
    Previene el error de renderizar botones como bloques blancos sólidos.
    """
    w, h = rect.width, rect.height
    if w <= 0 or h <= 0:
        return
    g_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(g_surf, bg_rgba, (0, 0, w, h), border_radius=border_radius)
    if border_rgba:
        pygame.draw.rect(g_surf, border_rgba, (0, 0, w, h), width=border_width, border_radius=border_radius)
    surface.blit(g_surf, rect.topleft)


def draw_aero_glass_panel(surface: pygame.Surface, rect: pygame.Rect, border_radius: int = 14):
    """Renderiza el panel de cristal aguamarina translúcido oficial de OmniDash Aero
    (garrison-theme-aero.css: linear-gradient(180deg, rgba(150, 220, 245, .46), rgba(18, 100, 145, .62) 30%, rgba(5, 52, 88, .82))).
    Fidelidad absoluta a las capturas oficiales aero-settings.jpg y aero-library.jpg.
    """
    w, h = rect.width, rect.height
    if w <= 0 or h <= 0:
        return
    p_surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # Gradiente vertical de cristal aguamarina auténtico Frutiger Aero
    for y in range(h):
        prog = y / float(h)
        if prog < 0.3:
            p_sub = prog / 0.3
            r = int(140 * (1 - p_sub) + 20 * p_sub)
            g = int(210 * (1 - p_sub) + 105 * p_sub)
            b = int(240 * (1 - p_sub) + 150 * p_sub)
            a = int(120 * (1 - p_sub) + 165 * p_sub)
        else:
            p_sub = (prog - 0.3) / 0.7
            r = int(20 * (1 - p_sub) + 6 * p_sub)
            g = int(105 * (1 - p_sub) + 52 * p_sub)
            b = int(150 * (1 - p_sub) + 90 * p_sub)
            a = int(165 * (1 - p_sub) + 215 * p_sub)
        pygame.draw.line(p_surf, (r, g, b, a), (0, y), (w, y))

    # Máscara de esquinas redondeadas
    mask_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask_surf, (255, 255, 255, 255), (0, 0, w, h), border_radius=border_radius)
    p_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # Brillo blanco superior (inset 0 1px 0 rgba(255, 255, 255, .6))
    pygame.draw.line(p_surf, (255, 255, 255, 170), (border_radius, 1), (w - border_radius, 1))
    # Borde de cristal translúcido
    pygame.draw.rect(p_surf, (255, 255, 255, 125), (0, 0, w, h), width=1, border_radius=border_radius)

    surface.blit(p_surf, rect.topleft)


# ==============================================================================
# CARGADOR DE IMÁGENES EN COLOR DE ALTA DEFINICIÓN
# ==============================================================================
COLOR_COVERS = {
    # Nintendo & Retro
    "mario": "fotos web/super mario.jpg",
    "zelda": "fotos web/The_Legend_of_Zelda_film_logo.jpg",
    "pokemon": "fotos web/pokemon.webp",
    "donkeykong": "fotos web/donkeykong.jpg",
    "castlevania": "fotos web/castlevania.webp",
    "metalslug": "fotos web/metal slug.jpg",
    "streetfighter": "fotos web/Street_Fighter_old_logo.png",
    "doom": "fotos web/Doom_logo.png",
    "pacman": "fotos web/pac man.jpg",
    "megaman": "fotos web/megaman.jpg",
    "plantsvszombies": "fotos web/pvzr-key-art.png.adapt.crop1x1.767p.png",
    "flappy": "fotos web/Flappy_Bird_icon.png",
    "asteroids": "fotos web/asteroids.jpg",
    "dino": "fotos web/dino.jpg",
    "tetris": "fotos web/tetris logo .jpg",
    "spaceinvaders": "fotos web/space nvaders.jpg",
    "ghostbusters": "fotos web/ghostbusters.webp",
    # Colección AAA OmniDash
    "sonic": "assets_omnidash/covers/sonic.webp",
    "residentevil": "assets_omnidash/covers/resident-evil.webp",
    "battlefield": "assets_omnidash/covers/battlefield.webp",
    "callofduty": "assets_omnidash/covers/call-of-duty.webp",
    "metalgear": "assets_omnidash/covers/metal-gear.webp",
    "batman": "assets_omnidash/covers/batman-arkham.webp",
    "assassinscreed": "assets_omnidash/covers/assassins-creed.webp",
    "needforspeed": "assets_omnidash/covers/need-for-speed.webp",
    "lego": "assets_omnidash/covers/lego.webp",
    "farcry": "assets_omnidash/covers/far-cry.webp",
    # PlayStation / Colección Moderna
    "elden": "assets_omnidash/covers/elden.png",
    "red": "assets_omnidash/covers/red.png",
    "destiny": "assets_omnidash/covers/destiny.png",
    "spider": "assets_omnidash/covers/spider.png",
    "god": "assets_omnidash/covers/god.png",
    "horizon": "assets_omnidash/covers/horizon.png",
    "last": "assets_omnidash/covers/last.png",
    "mafia": "assets_omnidash/covers/mafia.png",
    "death": "assets_omnidash/covers/death.png",
    "tomb": "assets_omnidash/covers/tomb.png",
    "fifa": "assets_omnidash/covers/fifa.png",
    "bratz": "roms/nds/6148 - Bratz Fashion Boutique (U)(frieNDS).jpg",
    "lego": "roms/nds/1633 - Cover.png",
    "star wars": "roms/nds/1633 - Cover.png",
    "sparta": "assets_omnidash/covers/god.png",
    "olympus": "assets_omnidash/covers/god.png",
    "barbie": "assets_omnidash/covers/sega.webp",
    "disney": "assets_omnidash/covers/far-cry.webp",
    "simpsons": "fotos web/Street_Fighter_old_logo.png",
}


def pick_color_cover(name: str, console: str) -> str:
    n = name.lower()
    for key, path in COLOR_COVERS.items():
        if key in n:
            if (ROOT / path).exists():
                return path

    if console == "SNES":
        return "fotos web/super mario.jpg"
    elif console == "N64":
        return "fotos web/The_Legend_of_Zelda_film_logo.jpg"
    elif console == "PS1":
        return "assets_omnidash/covers/red.png"
    elif console == "ARCADE":
        return "fotos web/metal slug.jpg"
    elif console == "NDS":
        return "fotos web/pokemon.webp"
    elif console == "WII":
        return "assets_omnidash/covers/far-cry.webp"
    elif console == "NEO-GEO":
        return "assets_omnidash/covers/sega.webp"
    else:
        return "assets_omnidash/covers/elden.png"


def load_all_games() -> list[dict]:
    games: list[dict] = []
    roms_dir = ROOT / "roms"

    # 1. Juegos Nativos C.C.I. SYSTEM
    for g in CATALOG:
        cid = g.get("id", "")
        cov = pick_color_cover(cid, "CCI")
        games.append({
            "id": f"native_{cid}",
            "title": g.get("title", cid).title(),
            "console": "C.C.I.",
            "badge": "CCI",
            "type": "native",
            "core": None,
            "rom": None,
            "cover": cov,
            "year": "2024",
            "developer": "C.C.I. Studio",
            "desc": g.get("desc", "Juego nativo oficial desarrollado para la plataforma C.C.I. SYSTEM.")
        })

    # 2. ROMs SNES
    snes_dir = roms_dir / "snes"
    if snes_dir.exists():
        for f in sorted(snes_dir.glob("*.*")):
            if f.suffix.lower() in (".sfc", ".smc"):
                clean_name = f.stem.split("(")[0].split("[")[0].strip()
                cov = pick_color_cover(clean_name, "SNES")
                games.append({
                    "id": f"snes_{f.stem}",
                    "title": clean_name,
                    "console": "Super Nintendo",
                    "badge": "SNES",
                    "type": "libretro",
                    "core": "cores/snes9x_libretro.dylib",
                    "rom": str(f.relative_to(ROOT)),
                    "cover": cov,
                    "year": "1992",
                    "developer": "Nintendo EAD",
                    "desc": f"Clásico legendario de 16-Bit Super Nintendo con gráficos Mode 7: {clean_name}"
                })

    # 3. ROMs Arcade MAME
    mame_dir = roms_dir / "mame"
    if mame_dir.exists():
        for f in sorted(mame_dir.glob("*.zip")):
            clean_name = f.stem.upper()
            if f.stem.lower() == "simpsons":
                clean_name = "The Simpsons Arcade"
            cov = pick_color_cover(clean_name, "ARCADE")
            games.append({
                "id": f"mame_{f.stem}",
                "title": f"Arcade: {clean_name}" if not clean_name.startswith("The") else clean_name,
                "console": "Arcade",
                "badge": "ARCADE",
                "type": "libretro",
                "core": "cores/mame2003_plus_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "1991",
                "developer": "Konami",
                "desc": f"Cabina recreativa arcade clásica preservada a 60 FPS estables: {clean_name}"
            })

    # 4. ROMs N64
    n64_dir = roms_dir / "n64"
    if n64_dir.exists():
        for f in sorted(n64_dir.glob("*.z64")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            cov = pick_color_cover(clean_name, "N64")
            games.append({
                "id": f"n64_{f.stem}",
                "title": clean_name,
                "console": "Nintendo 64",
                "badge": "N64",
                "type": "libretro",
                "core": "cores/mupen64plus_next_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "1996",
                "developer": "Nintendo",
                "desc": f"Hito de la revolución poligonal en 3D de 64-Bit: {clean_name}"
            })

    # 5. ROMs PS1
    ps1_dir = roms_dir / "ps1"
    if ps1_dir.exists():
        for f in sorted(ps1_dir.glob("*.cue")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            cov = pick_color_cover(clean_name, "PS1")
            games.append({
                "id": f"ps1_{f.stem}",
                "title": clean_name,
                "console": "PlayStation 1",
                "badge": "PS1",
                "type": "libretro",
                "core": "cores/mednafen_psx_hw_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "1997",
                "developer": "Sony / Konami / Capcom",
                "desc": f"Aventura cinematográfica en formato CD-ROM PlayStation: {clean_name}"
            })

    # 6. ROMs NDS
    nds_dir = roms_dir / "nds"
    if nds_dir.exists():
        for f in sorted(nds_dir.rglob("*.nds")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            num_prefix = ""
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                if parts[0].isdigit():
                    num_prefix = parts[0]
                    clean_name = parts[1].strip()

            # Buscar carátula local si viene desempaquetada
            cov = None
            if num_prefix:
                cov_cand = f.parent / f"{num_prefix} - Cover.png"
                if cov_cand.exists():
                    cov = str(cov_cand.relative_to(ROOT))
            if not cov:
                cov_cand = f.parent / f"{f.stem}.jpg"
                if cov_cand.exists():
                    cov = str(cov_cand.relative_to(ROOT))
            if not cov:
                cov = pick_color_cover(clean_name, "NDS")

            games.append({
                "id": f"nds_{f.stem}",
                "title": clean_name,
                "console": "Nintendo DS",
                "badge": "NDS",
                "type": "libretro",
                "core": "cores/melonds_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "2005",
                "developer": "Nintendo",
                "desc": f"Doble pantalla interactiva de Nintendo DS: {clean_name}"
            })

    # 6b. ROMs Game Boy Advance (GBA)
    gba_dir = roms_dir / "gba"
    if gba_dir.exists():
        for f in sorted(gba_dir.glob("*.gba")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                if parts[0].isdigit():
                    clean_name = parts[1].strip()
            cov = pick_color_cover(clean_name, "GBA")
            games.append({
                "id": f"gba_{f.stem}",
                "title": clean_name,
                "console": "Game Boy Advance",
                "badge": "GBA",
                "type": "libretro",
                "core": "cores/vba_next_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "2004",
                "developer": "Nintendo / Various",
                "desc": f"Clásico de 32-Bit Game Boy Advance: {clean_name}"
            })

    # 7. ROMs Neo-Geo
    neo_dir = roms_dir / "neogeo"
    if neo_dir.exists():
        for f in sorted(neo_dir.glob("*.zip")):
            clean_name = f.stem.upper()
            cov = pick_color_cover(clean_name, "NEO-GEO")
            games.append({
                "id": f"neogeo_{f.stem}",
                "title": f"NeoGeo: {clean_name}",
                "console": "Neo-Geo",
                "badge": "NEO-GEO",
                "type": "libretro",
                "core": "cores/fbneo_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "1995",
                "developer": "SNK Neo-Geo",
                "desc": f"Arcade 24-Bit SNK Neo-Geo: {clean_name}"
            })

    # 8. ROMs Nintendo Wii
    wii_dir = roms_dir / "wii"
    if wii_dir.exists():
        for f in sorted(wii_dir.glob("*.wbfs")):
            clean_name = f.stem.split("[")[0].strip()
            cov = pick_color_cover(clean_name, "WII")
            games.append({
                "id": f"wii_{f.stem}",
                "title": clean_name,
                "console": "Nintendo Wii",
                "badge": "WII",
                "type": "libretro",
                "core": "cores/dolphin_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "2006",
                "developer": "Nintendo",
                "desc": f"Innovación por control de movimiento: {clean_name}"
            })

    return games


ALL_GAMES = load_all_games()

FEATURED_RECENT = [
    {
        "id": "hero_mario",
        "title": "Super Mario World",
        "subtitle": "Super Nintendo • 16-Bit",
        "badge": "SNES",
        "cover": "fotos web/super mario.jpg",
        "core": "cores/snes9x_libretro.dylib",
        "rom": "roms/snes/Super Mario World 2 - Yoshi's Island (U) (V1.1).smc",
        "desc": "El pináculo del género de plataformas 2D con Yoshi y los 96 niveles de Dinosaur Land.",
        "developer": "Nintendo EAD",
        "year": "1990",
    },
    {
        "id": "rec_zelda",
        "title": "The Legend of Zelda",
        "subtitle": "Nintendo 64 • 60 FPS",
        "badge": "N64",
        "cover": "fotos web/The_Legend_of_Zelda_film_logo.jpg",
        "core": "cores/mupen64plus_next_libretro.dylib",
        "rom": "roms/n64/Super Mario 64 (U) [!].z64",
        "desc": "Aventura épica atemporal en las tierras de Hyrule.",
        "developer": "Nintendo",
        "year": "1996",
    },
    {
        "id": "rec_slug",
        "title": "Metal Slug 2",
        "subtitle": "Arcade MAME • Neo-Geo",
        "badge": "ARCADE",
        "cover": "fotos web/metal slug.jpg",
        "core": "cores/mame2003_plus_libretro.dylib",
        "rom": "roms/mame/mslug2.zip",
        "desc": "Acción frenética 'run and gun' con animaciones pixel art legendarias.",
        "developer": "SNK",
        "year": "1998",
    },
    {
        "id": "rec_pokemon",
        "title": "Pokémon White 2",
        "subtitle": "Nintendo DS • DSi Enhanced",
        "badge": "NDS",
        "cover": "fotos web/pokemon.webp",
        "core": "cores/melonds_libretro.dylib",
        "rom": "roms/nds/Pokemon White Version 2/Pokemon White Version 2 (DSi Enhanced)(U)(frieNDS).nds",
        "desc": "Regresa a la región de Teselia dos años después con nuevos líderes de gimnasio.",
        "developer": "Game Freak",
        "year": "2012",
    },
    {
        "id": "rec_castlevania",
        "title": "Castlevania: SotN",
        "subtitle": "PlayStation 1 • CD Audio",
        "badge": "PS1",
        "cover": "fotos web/castlevania.webp",
        "core": "cores/mednafen_psx_hw_libretro.dylib",
        "rom": "roms/ps1/Castlevania - Symphony of the Night (USA).cue",
        "desc": "La obra maestra de Koji Igarashi que definió el género Metroidvania.",
        "developer": "Konami",
        "year": "1997",
    },
    {
        "id": "rec_sonic",
        "title": "Sonic The Hedgehog",
        "subtitle": "Sega Genesis • 16-Bit",
        "badge": "SEGA",
        "cover": "assets_omnidash/covers/sonic.webp",
        "core": "cores/snes9x_libretro.dylib",
        "rom": "roms/snes/Doom (USA).sfc",
        "desc": "Velocidad Supersónica a través de Green Hill Zone.",
        "developer": "Sonic Team",
        "year": "1991",
    },
]

CONSOLES = FEATURED_RECENT
_IMAGE_CACHE: dict[str, pygame.Surface] = {}


def get_image(rel_path: str, w: int, h: int) -> pygame.Surface | None:
    key = f"{rel_path}_{w}_{h}"
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]

    p = ROOT / rel_path
    if p.exists():
        try:
            loaded = pygame.image.load(str(p)).convert_alpha()
            scaled = pygame.transform.smoothscale(loaded, (w, h))
            _IMAGE_CACHE[key] = scaled
            return scaled
        except Exception:
            pass
    return None


def draw_glossy_square_card(surface: pygame.Surface, rect: pygame.Rect, img_path: str, is_focused: bool, title: str | None = None, draw_reflection: bool = True):
    """Renderiza una tarjeta CUADRADA 1:1 oficial de OmniDash Frutiger Aero."""
    w, h = rect.width, rect.height
    rx, ry = rect.x, rect.y

    # 1. Imagen a sangre completa
    img = get_image(img_path, w, h)
    if img:
        surface.blit(img, (rx, ry))
    else:
        pygame.draw.rect(surface, (18, 54, 85), rect, border_radius=8)

    # 2. Gradiente de Brillo de Cristal Frutiger Aero (Top Half Gloss)
    gloss_surf = pygame.Surface((w, h // 2), pygame.SRCALPHA)
    for y in range(h // 2):
        alpha = int(75 * (1.0 - y / (h * 0.5)))
        pygame.draw.line(gloss_surf, (255, 255, 255, alpha), (0, y), (w, y))
    surface.blit(gloss_surf, (rx, ry))
    pygame.draw.line(surface, (255, 255, 255, 180), (rx + 4, ry), (rx + w - 4, ry))

    # 3. Foco Neón Verde #b6f55a
    if is_focused:
        glow_col = (182, 245, 90)
        glow_rect = rect.inflate(8, 8)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_col, 80), (0, 0, glow_rect.width, glow_rect.height), width=3, border_radius=12)
        surface.blit(glow_surf, glow_rect.topleft)
        pygame.draw.rect(surface, glow_col, rect, width=3, border_radius=8)

        if title:
            scrim_h = 42
            scrim_surf = pygame.Surface((w, scrim_h), pygame.SRCALPHA)
            for sy in range(scrim_h):
                sa = int(220 * (sy / scrim_h))
                pygame.draw.line(scrim_surf, (0, 0, 0, sa), (0, sy), (w, sy))
            surface.blit(scrim_surf, (rx, ry + h - scrim_h))

            font = pygame.font.SysFont("Segoe UI, Helvetica", 13, bold=True)
            tt = font.render(title[:22], True, (255, 255, 255))
            surface.blit(tt, (rx + 8, ry + h - 28))
    else:
        pygame.draw.rect(surface, (255, 255, 255, 90), rect, width=1, border_radius=8)

    # 4. Reflejo cristalino sobre el mar debajo de la tarjeta
    if draw_reflection and img:
        ref_h = int(h * 0.35)
        flipped = pygame.transform.flip(img, False, True)
        ref_scaled = pygame.transform.smoothscale(flipped, (w, ref_h))

        mask = pygame.Surface((w, ref_h), pygame.SRCALPHA)
        for my in range(ref_h):
            alpha = int(70 * (1.0 - my / ref_h))
            pygame.draw.line(mask, (255, 255, 255, alpha), (0, my), (w, my))

        ref_scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(ref_scaled, (rx, ry + h + 2))


# ==============================================================================
# 1. VISTA INICIAL AUTÉNTICA OMNIDASH AERO (OmniDashHomeView)
# ==============================================================================
class OmniDashHomeView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.selected_idx = 0

        self.hero_rect = pygame.Rect(110, 155, 204, 204)
        self.small_size = 122
        self.small_y = 155 + (204 - self.small_size)
        self.small_rects: list[pygame.Rect] = []
        for idx in range(4):
            sx = 330 + idx * (self.small_size + 14)
            self.small_rects.append(pygame.Rect(sx, self.small_y, self.small_size, self.small_size))

        mx = 330 + 4 * (self.small_size + 14)
        self.my_games_rect = pygame.Rect(mx, self.small_y, self.small_size, self.small_size)

        card_y = 405
        card_h = 135
        card_w = 252
        spacing = 18
        self.glass_card_rects = []
        for idx in range(4):
            cx = 110 + idx * (card_w + spacing)
            self.glass_card_rects.append(pygame.Rect(cx, card_y, card_w, card_h))

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.hero_rect.collidepoint(mx, my):
                self.selected_idx = 0
                self.engine.play_sound("reward")
                return {"action": "OPEN_DETAILS", "item": FEATURED_RECENT[0]}

            for idx, r in enumerate(self.small_rects):
                if r.collidepoint(mx, my):
                    self.selected_idx = idx + 1
                    self.engine.play_sound("reward")
                    return {"action": "OPEN_DETAILS", "item": FEATURED_RECENT[idx + 1]}

            if self.my_games_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "LIBRARY"}

            if self.glass_card_rects[0].collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "LIBRARY"}
            elif self.glass_card_rects[1].collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "GROUPS"}
            elif self.glass_card_rects[2].collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "PROFILE"}
            elif self.glass_card_rects[3].collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "SETTINGS"}

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_idx < 5:
                    self.selected_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.engine.play_sound("reward")
                if self.selected_idx < 5:
                    return {"action": "OPEN_DETAILS", "item": FEATURED_RECENT[self.selected_idx]}
                else:
                    return {"action": "NAVIGATE_UTIL", "destination": "LIBRARY"}

        return None

    def render(self, surface: pygame.Surface):
        # 1. Hero Card
        hero = FEATURED_RECENT[0]
        draw_glossy_square_card(surface, self.hero_rect, hero["cover"], is_focused=(self.selected_idx == 0), title=hero["title"], draw_reflection=True)

        # 2. Pequeñas tarjetas cuadradas
        for idx, r in enumerate(self.small_rects):
            item = FEATURED_RECENT[idx + 1]
            draw_glossy_square_card(surface, r, item["cover"], is_focused=(self.selected_idx == (idx + 1)), title=item["title"], draw_reflection=True)

        # 3. My games & apps
        mr = self.my_games_rect
        is_m_sel = (self.selected_idx == 5)
        self.engine.draw_acrylic_glass(surface, mr, border_radius=10, border_rgba=(182, 245, 90) if is_m_sel else (255, 255, 255, 120), border_width=3 if is_m_sel else 1)

        lib_ico = self.engine.get_icon("library", (34, 34))
        if lib_ico:
            surface.blit(lib_ico, lib_ico.get_rect(center=(mr.centerx, mr.centery - 18)))

        lib_t = self.engine.font_badge.render("My games & apps", True, (255, 255, 255))
        surface.blit(lib_t, lib_t.get_rect(center=(mr.centerx, mr.centery + 18)))

        count_t = self.engine.font_badge.render(f"{len(ALL_GAMES)} games", True, (180, 225, 255))
        surface.blit(count_t, count_t.get_rect(center=(mr.centerx, mr.centery + 34)))

        # 4. Tarjetas de cristal esmerilado inferior con desenfoque acrílico real (Pillow)
        glass_cards_data = [
            {"title": "My games & apps", "sub": f"{len(ALL_GAMES)} games\nReady to play", "badge": "LIBRARY", "img": "fotos web/donkeykong.jpg", "icon": "apps_list"},
            {"title": "Friends", "sub": "Seeker & Night Raid\n3 friends online right now", "badge": "FRIENDS", "img": None, "icon": "people"},
            {"title": "GAME PASS", "sub": "Discover\nHundreds of great games", "badge": "PASS", "img": "assets_omnidash/covers/battlefield.webp", "icon": "games"},
            {"title": "Achievements", "sub": "18,450 G\nHorizon Superstar · 40G", "badge": "18,450", "img": None, "icon": "star"},
        ]

        for idx, gc in enumerate(glass_cards_data):
            r = self.glass_card_rects[idx]
            is_hov = r.collidepoint(pygame.mouse.get_pos())

            top_t = (20, 140, 70, 160) if gc["badge"] == "PASS" else ((35, 135, 185, 150) if is_hov else (20, 110, 160, 120))
            bot_t = (10, 80, 40, 220) if gc["badge"] == "PASS" else ((12, 70, 110, 220) if is_hov else (8, 55, 95, 200))
            b_col = (182, 245, 90) if is_hov else (255, 255, 255, 140)
            self.engine.draw_acrylic_glass(surface, r, border_radius=12, tint_top=top_t, tint_bot=bot_t, border_rgba=b_col, border_width=2 if is_hov else 1)

            t_t = self.engine.font_body.render(gc["title"], True, (255, 255, 255))
            surface.blit(t_t, (r.x + 16, r.y + 14))

            lines = gc["sub"].split("\n")
            for l_idx, line in enumerate(lines):
                st = self.engine.font_sub.render(line, True, (215, 240, 255))
                surface.blit(st, (r.x + 16, r.y + 60 + l_idx * 18))

            if gc["img"]:
                prev_img = get_image(gc["img"], 70, 70)
                if prev_img:
                    surface.blit(prev_img, (r.right - 84, r.y + 16))
                    pygame.draw.rect(surface, (255, 255, 255, 120), (r.right - 84, r.y + 16, 70, 70), width=1, border_radius=6)
            elif gc.get("icon"):
                c_ico = self.engine.get_icon(gc["icon"], (36, 36))
                if c_ico:
                    surface.blit(c_ico, (r.right - 60, r.y + 20))


# ==============================================================================
# 2. VISTA BIBLIOTECA OFICIAL CON SCROLL DOWN COMPLETO (OmniDashLibraryView)
# ==============================================================================
class OmniDashLibraryView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_category = "Games"
        self.selected_game_idx = 0
        self.search_query = ""
        self.scroll_y = 0.0

        self.sidebar_rect = pygame.Rect(32, 24, 250, 672)
        self.content_rect = pygame.Rect(298, 24, 950, 672)
        self.back_btn_rect = pygame.Rect(48, 38, 100, 34)
        self.search_rect = pygame.Rect(48, 140, 218, 34)

        self.categories = [
            {"id": "Games", "label": "Games", "count": len(ALL_GAMES)},
            {"id": "SNES", "label": "Super Nintendo", "count": 21},
            {"id": "CCI", "label": "Juegos C.C.I.", "count": 19},
            {"id": "PS1", "label": "PlayStation 1", "count": 7},
            {"id": "ARCADE", "label": "Arcade MAME", "count": 6},
            {"id": "NDS", "label": "Nintendo DS", "count": 6},
            {"id": "N64", "label": "Nintendo 64", "count": 5},
            {"id": "NEO-GEO", "label": "Neo-Geo", "count": 3},
            {"id": "WII", "label": "Nintendo Wii", "count": 1},
        ]
        self.cat_rects: list[pygame.Rect] = []
        self.game_card_rects: list[tuple[pygame.Rect, dict]] = []

    def _filtered_games(self) -> list[dict]:
        res = ALL_GAMES
        if self.selected_category != "Games":
            res = [g for g in res if g["badge"] == self.selected_category]
        if self.search_query:
            q = self.search_query.lower()
            res = [g for g in res if q in g["title"].lower()]
        return res

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        filtered = self._filtered_games()
        cols = 5
        card_w, card_h = 166, 166
        gap_y = 18
        total_rows = math.ceil(len(filtered) / cols) if filtered else 1
        total_height = total_rows * (card_h + gap_y)
        visible_h = self.content_rect.height - 110
        max_scroll = max(0, total_height - visible_h + 30)

        # 1. SCROLL DOWN CON RUEDA DE RATÓN (MOUSEWHEEL)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0.0, min(float(max_scroll), self.scroll_y - event.y * 60.0))
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if event.button == 1:
                # Botón volver
                if self.back_btn_rect.collidepoint(mx, my):
                    self.engine.play_sound("navigate")
                    return {"action": "BACK"}

                # Clic en categorías laterales
                for idx, r in enumerate(self.cat_rects):
                    if r.collidepoint(mx, my):
                        self.selected_category = self.categories[idx]["id"]
                        self.selected_game_idx = 0
                        self.scroll_y = 0.0
                        self.engine.play_sound("navigate")
                        return None

                # Clic en tarjetas de juegos (considerando scroll_y)
                if self.content_rect.collidepoint(mx, my):
                    for r, game in self.game_card_rects:
                        if r.collidepoint(mx, my):
                            self.engine.play_sound("reward")
                            return {"action": "OPEN_DETAILS", "item": game}

            elif event.button == 4:  # Wheel up
                self.scroll_y = max(0.0, self.scroll_y - 60.0)
            elif event.button == 5:  # Wheel down
                self.scroll_y = min(float(max_scroll), self.scroll_y + 60.0)

        # 2. NAVEGACIÓN POR TECLADO CON AUTO-SCROLL
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}

            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_game_idx < len(filtered) - 1:
                    self.selected_game_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_game_idx > 0:
                    self.selected_game_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.selected_game_idx + cols < len(filtered):
                    self.selected_game_idx += cols
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.selected_game_idx - cols >= 0:
                    self.selected_game_idx -= cols
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_PAGEUP,):
                self.scroll_y = max(0.0, self.scroll_y - 200.0)
            elif event.key in (pygame.K_PAGEDOWN,):
                self.scroll_y = min(float(max_scroll), self.scroll_y + 200.0)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if filtered and self.selected_game_idx < len(filtered):
                    self.engine.play_sound("reward")
                    return {"action": "OPEN_DETAILS", "item": filtered[self.selected_game_idx]}

            # Auto-scroll para mantener la tarjeta en pantalla
            cur_row = self.selected_game_idx // cols
            card_top = cur_row * (card_h + gap_y)
            if card_top < self.scroll_y:
                self.scroll_y = float(card_top)
            elif card_top + card_h > self.scroll_y + visible_h:
                self.scroll_y = float(card_top + card_h - visible_h + 20)

        return None

    def render(self, surface: pygame.Surface):
        # 1. Barra Lateral Izquierda con Desenfoque Acrílico Real (Pillow)
        sr = self.sidebar_rect
        self.engine.draw_acrylic_glass(surface, sr, border_radius=14, tint_top=(140, 215, 245, 110), tint_bot=(8, 60, 100, 220))

        # Botón Volver con icono Home nítido
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        self.engine.draw_acrylic_glass(surface, self.back_btn_rect, border_radius=16, tint_top=(20, 90, 140, 160), tint_bot=(10, 48, 80, 220), border_rgba=(182, 245, 90) if is_back_hov else (255, 255, 255, 140))
        home_ico = self.engine.get_icon("home", (16, 16))
        if home_ico:
            surface.blit(home_ico, (self.back_btn_rect.x + 14, self.back_btn_rect.centery - 8))
        bt = self.engine.font_btn.render("Home", True, (255, 255, 255))
        surface.blit(bt, (self.back_btn_rect.x + 36, self.back_btn_rect.centery - 7))

        # Anillo de almacenamiento ("72% used")
        ring_center = (sr.centerx, 104)
        pygame.draw.circle(surface, (15, 60, 95), ring_center, 22, width=4)
        pygame.draw.circle(surface, (182, 245, 90), ring_center, 22, width=4)
        r_txt = self.engine.font_badge.render("72%", True, (255, 255, 255))
        surface.blit(r_txt, r_txt.get_rect(center=ring_center))

        # Buscador con alto contraste e icono Search oficial
        self.engine.draw_acrylic_glass(surface, self.search_rect, border_radius=17, tint_top=(15, 75, 120, 160), tint_bot=(8, 42, 75, 220))
        srch_ico = self.engine.get_icon("search", (16, 16))
        if srch_ico:
            surface.blit(srch_ico, (self.search_rect.x + 12, self.search_rect.centery - 8))
        srch_t = self.engine.font_sub.render("Search games...", True, (215, 238, 255))
        surface.blit(srch_t, (self.search_rect.x + 34, self.search_rect.y + 8))

        # Pestañas de categorías
        self.cat_rects = []
        cy = 190
        for idx, cat in enumerate(self.categories):
            r = pygame.Rect(48, cy, 218, 42)
            self.cat_rects.append(r)

            is_sel = (cat["id"] == self.selected_category)
            if is_sel:
                draw_glass_rect(surface, r, (31, 134, 214, 200), (182, 245, 90), border_radius=10, border_width=2)
            else:
                draw_glass_rect(surface, r, (12, 55, 90, 100), (255, 255, 255, 50), border_radius=10, border_width=1)

            c_name = self.engine.font_body.render(cat["label"], True, (255, 255, 255))
            surface.blit(c_name, (r.x + 14, r.y + 11))

            c_count = self.engine.font_badge.render(str(cat["count"]), True, (182, 245, 90) if is_sel else (200, 225, 255))
            surface.blit(c_count, (r.right - c_count.get_width() - 14, r.y + 13))

            cy += 48

        # 2. Panel Principal de Contenido con Desenfoque Acrílico Real
        cr = self.content_rect
        self.engine.draw_acrylic_glass(surface, cr, border_radius=14, tint_top=(140, 215, 245, 95), tint_bot=(6, 52, 90, 210))

        # Encabezado
        filtered = self._filtered_games()
        head_t = self.engine.font_hero.render(self.selected_category if self.selected_category != "Games" else "All Games", True, (255, 255, 255))
        surface.blit(head_t, (cr.x + 30, cr.y + 22))

        sub_t = self.engine.font_sub.render(f"{len(filtered)} games installed  •  Ready to play (60 FPS)", True, (210, 235, 255))
        surface.blit(sub_t, (cr.x + 32, cr.y + 54))

        # Botón Sort con icono de ordenamiento oficial
        sort_r = pygame.Rect(cr.right - 140, cr.y + 24, 110, 32)
        draw_glass_rect(surface, sort_r, (10, 48, 80, 200), (255, 255, 255, 120), border_radius=16)
        sort_ico = self.engine.get_icon("arrow_sort", (14, 14))
        if sort_ico:
            surface.blit(sort_ico, (sort_r.x + 10, sort_r.centery - 7))
        st_txt = self.engine.font_sub.render("Sort: A-Z", True, (255, 255, 255))
        surface.blit(st_txt, (sort_r.x + 28, sort_r.centery - 8))

        # 3. Cuadrícula de Juegos con SCROLL DOWN REAL
        cols = 5
        card_w, card_h = 166, 166
        gap_x, gap_y = 18, 18
        start_x = cr.x + 28
        start_y = cr.y + 90
        visible_h = cr.height - 105

        # Área de recorte (clip) para scroll perfecto
        clip_rect = pygame.Rect(cr.x + 10, start_y, cr.width - 32, visible_h)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        self.game_card_rects = []
        for idx, g in enumerate(filtered):
            col = idx % cols
            row = idx // cols
            gx = start_x + col * (card_w + gap_x)
            gy = start_y + row * (card_h + gap_y) - int(self.scroll_y)

            card_r = pygame.Rect(gx, gy, card_w, card_h)
            # Solo añadir para clic si está dentro del área visible
            if card_r.bottom > start_y and card_r.top < start_y + visible_h:
                self.game_card_rects.append((card_r, g))

            # Solo renderizar si intersecta con la vista
            if gy + card_h >= start_y - 20 and gy <= start_y + visible_h + 20:
                draw_glossy_square_card(
                    surface,
                    card_r,
                    g["cover"],
                    is_focused=(idx == self.selected_game_idx),
                    title=g["title"],
                    draw_reflection=False
                )

        surface.set_clip(old_clip)

        # 4. Barra de Scroll Vertical Visible
        total_rows = math.ceil(len(filtered) / cols) if filtered else 1
        total_height = total_rows * (card_h + gap_y)
        if total_height > visible_h:
            track_r = pygame.Rect(cr.right - 14, start_y, 6, visible_h)
            draw_glass_rect(surface, track_r, (255, 255, 255, 30), border_radius=3)

            thumb_h = max(30, int(visible_h * (visible_h / total_height)))
            thumb_y = start_y + int((self.scroll_y / (total_height - visible_h)) * (visible_h - thumb_h))
            thumb_r = pygame.Rect(cr.right - 14, thumb_y, 6, thumb_h)
            draw_glass_rect(surface, thumb_r, (182, 245, 90, 220), (255, 255, 255, 180), border_radius=3)


# ==============================================================================
# 3. VISTA FICHA TÉCNICA OFICIAL OMNIDASH (OmniDashGameDetailsView)
# ==============================================================================
class OmniDashGameDetailsView:
    """Pantalla oficial de detalles del juego (garrison-details.js / screenshot-game-page.png):
    - Carátula 1:1 grande a la izquierda.
    - Botón verde gel 'PLAY GAME (60 FPS)'.
    - Ficha técnica completa, capacidades y descripción.
    """
    def __init__(self, engine: OmniDashEngine, game_item: dict):
        self.engine = engine
        self.game = game_item
        self.w, self.h = engine.w, engine.h

        self.panel_rect = pygame.Rect(54, 40, self.w - 108, self.h - 80)
        self.back_btn_rect = pygame.Rect(self.w - 190, 56, 120, 36)
        self.play_btn_rect = pygame.Rect(90, 420, 280, 52)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.back_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}
            elif self.play_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "LAUNCH", "item": self.game}

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.engine.play_sound("reward")
                return {"action": "LAUNCH", "item": self.game}

        return None

    def render(self, surface: pygame.Surface):
        pr = self.panel_rect
        self.engine.draw_acrylic_glass(surface, pr, border_radius=18, tint_top=(140, 215, 245, 110), tint_bot=(8, 55, 95, 220))

        # Botón Volver con alto contraste y desenfoque
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        self.engine.draw_acrylic_glass(surface, self.back_btn_rect, border_radius=18, tint_top=(20, 90, 140, 160), tint_bot=(10, 48, 80, 220), border_rgba=(182, 245, 90) if is_close_hov else (255, 255, 255, 140))
        home_ico = self.engine.get_icon("home", (16, 16))
        if home_ico:
            surface.blit(home_ico, (self.back_btn_rect.x + 16, self.back_btn_rect.centery - 8))
        bt = self.engine.font_btn.render("Volver", True, (255, 255, 255))
        surface.blit(bt, (self.back_btn_rect.x + 40, self.back_btn_rect.centery - 7))

        # 1. Columna Izquierda: Carátula Grande y Botón de Inicio
        cov_rect = pygame.Rect(90, 80, 280, 280)
        draw_glossy_square_card(surface, cov_rect, self.game.get("cover", ""), is_focused=False, draw_reflection=False)

        # Botón Verde Gel de Inicio Oficial (#3cb043 / #8eea6e)
        is_play_hov = self.play_btn_rect.collidepoint(pygame.mouse.get_pos())
        p_top = (75, 210, 85, 230) if is_play_hov else (50, 185, 60, 210)
        p_bot = (30, 140, 45, 245) if is_play_hov else (20, 120, 35, 230)
        self.engine.draw_acrylic_glass(surface, self.play_btn_rect, border_radius=14, tint_top=p_top, tint_bot=p_bot, border_rgba=(220, 255, 180) if is_play_hov else (182, 245, 90), border_width=2)
        
        play_ico = self.engine.get_icon("play", (22, 22))
        if play_ico:
            surface.blit(play_ico, (self.play_btn_rect.x + 22, self.play_btn_rect.centery - 11))
        play_txt = self.engine.font_hero.render("JUGAR AHORA (60 FPS)", True, (255, 255, 255))
        surface.blit(play_txt, (self.play_btn_rect.x + 52, self.play_btn_rect.centery - 10))

        # 2. Columna Derecha: Especificaciones y Capacidades
        rx = 410
        ry = 80
        rw = pr.right - rx - 40

        title_t = self.engine.font_hero.render(self.game.get("title", "Game Title"), True, (255, 255, 255))
        surface.blit(title_t, (rx, ry))

        meta_str = f"{self.game.get('console', 'Console')}  •  {self.game.get('developer', 'Official')}  •  {self.game.get('year', '2024')}"
        meta_t = self.engine.font_body.render(meta_str, True, (182, 245, 90))
        surface.blit(meta_t, (rx, ry + 40))

        # Tarjeta de capacidades
        cap_r = pygame.Rect(rx, ry + 78, rw, 80)
        self.engine.draw_acrylic_glass(surface, cap_r, border_radius=12, tint_top=(25, 95, 145, 130), tint_bot=(10, 48, 80, 200))

        caps = ["Single Player", "60 FPS V-Sync", "Controller Support", "Full HD Audio", "State Save"]
        cx = rx + 16
        for c in caps:
            cw = len(c) * 8 + 22
            cr_box = pygame.Rect(cx, ry + 102, cw, 28)
            self.engine.draw_acrylic_glass(surface, cr_box, border_radius=14, tint_top=(31, 134, 214, 180), tint_bot=(12, 70, 120, 220), border_rgba=(255, 255, 255, 140))
            ct = self.engine.font_badge.render(c, True, (255, 255, 255))
            surface.blit(ct, ct.get_rect(center=cr_box.center))
            cx += cw + 10

        # Tarjeta de Descripción
        desc_r = pygame.Rect(rx, ry + 175, rw, 130)
        self.engine.draw_acrylic_glass(surface, desc_r, border_radius=12, tint_top=(25, 95, 145, 130), tint_bot=(10, 48, 80, 200))
        d_lbl = self.engine.font_body.render("Description", True, (255, 255, 255))
        surface.blit(d_lbl, (rx + 16, ry + 188))
        d_txt = self.engine.font_sub.render(self.game.get("desc", "Official title preserved for C.C.I. SYSTEM."), True, (210, 235, 255))
        surface.blit(d_txt, (rx + 16, ry + 220))

        # Tarjeta de Archivo y Core
        info_r = pygame.Rect(rx, ry + 320, rw, 150)
        self.engine.draw_acrylic_glass(surface, info_r, border_radius=12, tint_top=(25, 95, 145, 130), tint_bot=(10, 48, 80, 200))
        i_lbl = self.engine.font_body.render("Emulation Architecture & Core Info", True, (255, 255, 255))
        surface.blit(i_lbl, (rx + 16, ry + 332))

        core_info = f"Libretro Core: {self.game.get('core', 'Native C.C.I. Engine')}"
        rom_info = f"ROM Path: {self.game.get('rom', 'Builtin Executable')}"
        surface.blit(self.engine.font_sub.render(core_info, True, (185, 215, 240)), (rx + 16, ry + 365))
        surface.blit(self.engine.font_sub.render(rom_info, True, (185, 215, 240)), (rx + 16, ry + 395))
        surface.blit(self.engine.font_badge.render("Certified 60 FPS Low Latency Framebuffer", True, (182, 245, 90)), (rx + 16, ry + 425))


# ==============================================================================
# 4. VISTA AJUSTES OFICIAL OMNIDASH AERO (OmniDashSettingsView)
# ==============================================================================
class OmniDashSettingsView:
    def __init__(self, engine: OmniDashEngine, user_data=None, on_apply_display=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.on_apply_display = on_apply_display

        self.categories = [
            {"id": "appearance", "name": "Personalisation", "icon_name": "paint_brush", "color": (142, 92, 247), "desc": "Frutiger Aero theme, glass effects and UI scale."},
            {"id": "display_sound", "name": "Display & sound", "icon_name": "desktop", "color": (47, 124, 246), "desc": "Resolution, fullscreen mode and audio volumes."},
            {"id": "controllers", "name": "Controllers & headsets", "icon_name": "xbox_controller", "color": (47, 174, 75), "desc": "Button layout, haptic rumble and triggers."},
            {"id": "notifications", "name": "Notifications", "icon_name": "alert", "color": (239, 75, 75), "desc": "Gamerscore achievement toasts and friend alerts."},
            {"id": "library", "name": "Library & Emulation", "icon_name": "library", "color": (242, 147, 31), "desc": "60 FPS Libretro cores, ROM directories and regions."},
            {"id": "account", "name": "Profile & system", "icon_name": "person", "color": (90, 122, 156), "desc": "Alex (18,450 G), Gamertag and custom avatar."},
            {"id": "accessibility", "name": "Accessibility", "icon_name": "accessibility", "color": (31, 155, 224), "desc": "Reduced motion, high contrast focus and text size."},
            {"id": "system", "name": "System", "icon_name": "settings", "color": (122, 127, 135), "desc": "C.C.I. System v2.1.0, disk storage and state saves."},
        ]

        self.selected_cat_idx = 0
        self.selected_row_idx = 0

        self.settings = {
            "resolution": "1280 x 720",
            "fullscreen": False,
            "volume_game": 80,
            "volume_music": 70,
            "rumble": True,
            "toasts": True,
            "reduced_motion": False,
        }

        self.panel_rect = pygame.Rect(48, 36, self.w - 96, self.h - 72)
        self.back_btn_rect = pygame.Rect(self.w - 200, 52, 120, 36)
        self.cat_rects: list[pygame.Rect] = []
        self.row_rects: list[pygame.Rect] = []

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.back_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}

            for idx, r in enumerate(self.cat_rects):
                if r.collidepoint(mx, my):
                    self.selected_cat_idx = idx
                    self.selected_row_idx = 0
                    self.engine.play_sound("navigate")
                    return None

            for idx, r in enumerate(self.row_rects):
                if r.collidepoint(mx, my):
                    self.selected_row_idx = idx
                    self._toggle_row()
                    self.engine.play_sound("reward")
                    return None

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}

            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.selected_row_idx > 0:
                    self.selected_row_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.selected_row_idx < len(self._get_rows()) - 1:
                    self.selected_row_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_cat_idx > 0:
                    self.selected_cat_idx -= 1
                    self.selected_row_idx = 0
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_cat_idx < len(self.categories) - 1:
                    self.selected_cat_idx += 1
                    self.selected_row_idx = 0
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._toggle_row()
                self.engine.play_sound("reward")

        return None

    def _get_rows(self) -> list[dict]:
        cid = self.categories[self.selected_cat_idx]["id"]
        if cid == "appearance":
            return [
                {"key": "theme", "label": "Active Theme", "sub": "Current dashboard visual skin", "val": "Frutiger Aero"},
                {"key": "glass", "label": "Frosted Glass Cards", "sub": "Real-time translucency and highlights", "val": "Enabled"},
                {"key": "scale", "label": "UI Scale", "sub": "Dashboard sizing for TV or desktop", "val": "100%"},
            ]
        elif cid == "display_sound":
            return [
                {"key": "res", "label": "Resolution", "sub": "Rendering window size", "val": self.settings["resolution"]},
                {"key": "full", "label": "Fullscreen Mode", "sub": "Cover the entire display monitor", "val": "ON" if self.settings["fullscreen"] else "OFF"},
                {"key": "v_game", "label": "Game Volume", "sub": "Emulator audio level", "val": f"{self.settings['volume_game']}%"},
                {"key": "v_bgm", "label": "Dashboard Music", "sub": "Ambient soundtrack volume", "val": f"{self.settings['volume_music']}%"},
            ]
        elif cid == "controllers":
            return [
                {"key": "layout", "label": "Button Layout", "sub": "Universal Xbox A/B/X/Y mapping", "val": "Xbox Standard"},
                {"key": "rumble", "label": "Controller Vibration", "sub": "Haptic feedback on impacts", "val": "ON" if self.settings["rumble"] else "OFF"},
            ]
        elif cid == "notifications":
            return [
                {"key": "toasts", "label": "Achievement Toasts", "sub": "Popups when unlocking Gamerscore trophies", "val": "ON" if self.settings["toasts"] else "OFF"},
                {"key": "friends_alert", "label": "Friend Online Alerts", "sub": "Notification when a friend starts playing", "val": "Enabled"},
            ]
        elif cid == "library":
            return [
                {"key": "cores", "label": "Libretro Performance", "sub": "Ultra low latency 60 FPS emulation", "val": "60 FPS V-Sync"},
                {"key": "roms", "label": "ROM Library Scan", "sub": "Local verified preservation folders", "val": f"{len(ALL_GAMES)} games detected"},
            ]
        elif cid == "account":
            return [
                {"key": "tag", "label": "Active Player", "sub": "Current console profile", "val": "Alex"},
                {"key": "score", "label": "Total Gamerscore", "sub": "Accumulated game points", "val": "18,450 G"},
            ]
        elif cid == "accessibility":
            return [
                {"key": "motion", "label": "Reduced Motion", "sub": "Calm navigation without camera zoom", "val": "ON" if self.settings["reduced_motion"] else "OFF"},
                {"key": "contrast", "label": "High Contrast Focus", "sub": "Bright neon green glowing borders", "val": "Active (#b6f55a)"},
            ]
        else:
            return [
                {"key": "version", "label": "System Version", "sub": "C.C.I. SYSTEM Virtual Console Core", "val": "v2.1.0 (100% Python)"},
                {"key": "storage", "label": "Free Storage", "sub": "Available space for games and save states", "val": "7.2 GB Free"},
            ]

    def _toggle_row(self):
        rows = self._get_rows()
        if not rows or self.selected_row_idx >= len(rows):
            return
        k = rows[self.selected_row_idx]["key"]
        if k == "res":
            self.settings["resolution"] = "1920 x 1080" if self.settings["resolution"] == "1280 x 720" else "1280 x 720"
        elif k == "full":
            self.settings["fullscreen"] = not self.settings["fullscreen"]
        elif k == "rumble":
            self.settings["rumble"] = not self.settings["rumble"]
        elif k == "toasts":
            self.settings["toasts"] = not self.settings["toasts"]
        elif k == "motion":
            self.settings["reduced_motion"] = not self.settings["reduced_motion"]

    def render(self, surface: pygame.Surface):
        # 1. Overlay atmosférico Frutiger Aero sobre el mar turquesa
        # (linear-gradient(180deg, rgba(0, 40, 90, .55), rgba(0, 50, 80, .35) 40%, rgba(0, 40, 70, .6)))
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y in range(self.h):
            prog = y / float(self.h)
            a = int(90 + 35 * math.sin(prog * math.pi))
            pygame.draw.line(overlay, (0, 35, 75, a), (0, y), (self.w, y))
        surface.blit(overlay, (0, 0))

        # 2. Encabezado Oficial (.as-head de aero-settings.jpg)
        t_head = self.engine.font_hero.render("Settings", True, (255, 255, 255))
        sh_head = self.engine.font_hero.render("Settings", True, (0, 25, 60))
        surface.blit(sh_head, (66, 33))
        surface.blit(t_head, (64, 32))

        t_sub = self.engine.font_sub.render("Change how OmniDash looks, sounds and plays.", True, (215, 240, 255))
        surface.blit(t_sub, (65, 66))

        # Botón Cerrar Oficial (.as-close) en esquina superior derecha
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        draw_glass_rect(surface, self.back_btn_rect, (8, 45, 75, 220 if is_close_hov else 160), (182, 245, 90) if is_close_hov else (255, 255, 255, 140), border_radius=18)
        # Badge circular rojo "B" de Xbox
        kbd_center = (self.back_btn_rect.x + 20, self.back_btn_rect.centery)
        pygame.draw.circle(surface, (208, 56, 58), kbd_center, 10)
        b_txt = self.engine.font_badge.render("B", True, (255, 255, 255))
        surface.blit(b_txt, b_txt.get_rect(center=kbd_center))
        c_txt = self.engine.font_btn.render("Close", True, (255, 255, 255))
        surface.blit(c_txt, (self.back_btn_rect.x + 38, self.back_btn_rect.centery - 7))

        # 3. Dos Paneles de Cristal Independientes con Desenfoque Acrílico Real (Pillow)
        # Panel Izquierdo: Categorías (.as-cats de aero-settings.jpg)
        cats_rect = pygame.Rect(64, 96, 350, 564)
        self.engine.draw_acrylic_glass(surface, cats_rect, border_radius=14, tint_top=(140, 215, 245, 110), tint_bot=(6, 52, 90, 215))

        # Panel Derecho: Ajustes de la Categoría (.as-page de aero-settings.jpg)
        page_rect = pygame.Rect(434, 96, 782, 564)
        self.engine.draw_acrylic_glass(surface, page_rect, border_radius=14, tint_top=(140, 215, 245, 100), tint_bot=(6, 52, 90, 215))

        # Renderizar filas de categorías en Panel Izquierdo
        self.cat_rects = []
        cy = cats_rect.y + 14
        for idx, cat in enumerate(self.categories):
            r = pygame.Rect(cats_rect.x + 12, cy, cats_rect.width - 24, 62)
            self.cat_rects.append(r)

            is_sel = (idx == self.selected_cat_idx)
            is_hov = r.collidepoint(pygame.mouse.get_pos())

            if is_sel:
                draw_glass_rect(surface, r, (31, 134, 214, 195), (182, 245, 90), border_radius=10, border_width=2)
            elif is_hov:
                draw_glass_rect(surface, r, (255, 255, 255, 45), (255, 255, 255, 120), border_radius=10, border_width=1)
            else:
                draw_glass_rect(surface, r, (255, 255, 255, 18), (255, 255, 255, 40), border_radius=10, border_width=1)

            # Orbe de color redondo con brillo e icono Fluent
            orb_center = (r.x + 28, r.centery)
            pygame.draw.circle(surface, cat["color"], orb_center, 18)
            pygame.draw.circle(surface, (255, 255, 255, 190), orb_center, 18, width=1)
            pygame.draw.circle(surface, (255, 255, 255, 120), (orb_center[0], orb_center[1] - 5), 8)
            c_ico = self.engine.get_icon(cat["icon_name"], (18, 18))
            if c_ico:
                surface.blit(c_ico, c_ico.get_rect(center=orb_center))

            c_lbl = self.engine.font_body.render(cat["name"], True, (255, 255, 255))
            surface.blit(c_lbl, (r.x + 58, r.y + 10))

            sub_lbl = self.engine.font_badge.render(cat["desc"][:42] + ("..." if len(cat["desc"]) > 42 else ""), True, (200, 230, 255))
            surface.blit(sub_lbl, (r.x + 58, r.y + 34))

            cy += 68

        # Renderizar Contenido en Panel Derecho (.as-page)
        cur_cat = self.categories[self.selected_cat_idx]

        # Encabezado del panel derecho (.as-page-head)
        head_orb = (page_rect.x + 44, page_rect.y + 44)
        pygame.draw.circle(surface, cur_cat["color"], head_orb, 24)
        pygame.draw.circle(surface, (255, 255, 255, 200), head_orb, 24, width=2)
        pygame.draw.circle(surface, (255, 255, 255, 140), (head_orb[0], head_orb[1] - 7), 10)
        h_ico = self.engine.get_icon(cur_cat["icon_name"], (24, 24))
        if h_ico:
            surface.blit(h_ico, h_ico.get_rect(center=head_orb))

        st_title = self.engine.font_title.render(cur_cat["name"], True, (255, 255, 255))
        surface.blit(st_title, (page_rect.x + 82, page_rect.y + 22))

        st_desc = self.engine.font_sub.render(cur_cat["desc"], True, (215, 240, 255))
        surface.blit(st_desc, (page_rect.x + 84, page_rect.y + 50))

        # Lista de filas de ajustes (.as-rows)
        rows = self._get_rows()
        self.row_rects = []
        row_y = page_rect.y + 92

        for idx, row in enumerate(rows):
            r = pygame.Rect(page_rect.x + 18, row_y + idx * 72, page_rect.width - 36, 62)
            self.row_rects.append(r)

            is_sel = (idx == self.selected_row_idx)
            if is_sel:
                draw_glass_rect(surface, r, (31, 134, 214, 180), (182, 245, 90), border_radius=10, border_width=2)
            else:
                draw_glass_rect(surface, r, (255, 255, 255, 25), (255, 255, 255, 55), border_radius=10, border_width=1)

            # Brillo superior blanco en cada fila
            pygame.draw.line(surface, (255, 255, 255, 110), (r.x + 10, r.y + 1), (r.right - 10, r.y + 1))

            l_lbl = self.engine.font_body.render(row["label"], True, (255, 255, 255))
            surface.blit(l_lbl, (r.x + 18, r.y + 12))

            s_lbl = self.engine.font_badge.render(row["sub"], True, (190, 220, 245))
            surface.blit(s_lbl, (r.x + 18, r.y + 36))

            # Controles oficiales OmniDash (switch pill, slider o choice)
            val_str = str(row["val"])
            if val_str in ("ON", "OFF"):
                # Interruptor de pastilla deslizante Frutiger Aero
                sw_w, sw_h = 50, 26
                sw_r = pygame.Rect(r.right - sw_w - 20, r.centery - sw_h // 2, sw_w, sw_h)
                is_on = (val_str == "ON")
                sw_bg = (47, 174, 75, 230) if is_on else (255, 255, 255, 45)
                draw_glass_rect(surface, sw_r, sw_bg, (255, 255, 255, 140), border_radius=13)
                thumb_x = sw_r.right - 14 if is_on else sw_r.x + 14
                pygame.draw.circle(surface, (255, 255, 255), (thumb_x, sw_r.centery), 10)
                v_lbl = self.engine.font_badge.render(val_str, True, (182, 245, 90) if is_on else (200, 225, 245))
                surface.blit(v_lbl, (sw_r.x - v_lbl.get_width() - 10, r.centery - 6))
            elif "%" in val_str:
                # Barra deslizante con valor porcentual
                val_num = int(val_str.replace("%", "").strip() or 50)
                track_w, track_h = 130, 8
                track_r = pygame.Rect(r.right - track_w - 70, r.centery - track_h // 2, track_w, track_h)
                draw_glass_rect(surface, track_r, (255, 255, 255, 45), border_radius=4)
                fill_w = int(track_w * (val_num / 100.0))
                if fill_w > 0:
                    fill_r = pygame.Rect(track_r.x, track_r.y, fill_w, track_h)
                    draw_glass_rect(surface, fill_r, (182, 245, 90, 230), border_radius=4)
                v_lbl = self.engine.font_body.render(val_str, True, (255, 255, 255))
                surface.blit(v_lbl, (r.right - v_lbl.get_width() - 18, r.centery - 9))
            else:
                v_lbl = self.engine.font_body.render(val_str, True, (182, 245, 90) if is_sel else (255, 255, 255))
                surface.blit(v_lbl, (r.right - v_lbl.get_width() - 18, r.centery - 9))

        # 4. Pie de página con leyendas de botones (.as-hints)
        hints_t = self.engine.font_sub.render("Ⓐ / Enter  Select    •     / 🠄 🠆  Change    •    Ⓑ / Esc  Back", True, (200, 230, 255))
        surface.blit(hints_t, (page_rect.right - hints_t.get_width() - 10, self.h - 38))


# ==============================================================================
# 5. VISTA PERFIL & GAMERSCORE OFICIAL OMNIDASH AERO (OmniDashProfileView)
# ==============================================================================
class OmniDashProfileView:
    def __init__(self, engine: OmniDashEngine, user_data=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.panel_rect = pygame.Rect(80, 50, self.w - 160, self.h - 100)
        self.back_btn_rect = pygame.Rect(self.panel_rect.right - 140, self.panel_rect.y + 24, 116, 36)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.engine.play_sound("navigate")
            return {"action": "BACK"}
        return None

    def render(self, surface: pygame.Surface):
        # Panel de cristal aguamarina translúcido oficial Frutiger Aero
        pr = self.panel_rect
        self.engine.draw_acrylic_glass(surface, pr, border_radius=16, tint_top=(140, 215, 245, 110), tint_bot=(8, 55, 95, 220))

        # Botón Cerrar oficial con badge rojo B
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        self.engine.draw_acrylic_glass(surface, self.back_btn_rect, border_radius=18, tint_top=(20, 90, 140, 160), tint_bot=(10, 48, 80, 220), border_rgba=(182, 245, 90) if is_close_hov else (255, 255, 255, 140))
        kbd_center = (self.back_btn_rect.x + 20, self.back_btn_rect.centery)
        pygame.draw.circle(surface, (208, 56, 58), kbd_center, 10)
        b_txt = self.engine.font_badge.render("B", True, (255, 255, 255))
        surface.blit(b_txt, b_txt.get_rect(center=kbd_center))
        c_txt = self.engine.font_btn.render("Cerrar", True, (255, 255, 255))
        surface.blit(c_txt, (self.back_btn_rect.x + 38, self.back_btn_rect.centery - 7))

        # Avatar circular con borde de cristal
        av_center = (pr.x + 70, pr.y + 70)
        pygame.draw.circle(surface, (90, 166, 214), av_center, 38)
        pygame.draw.circle(surface, (255, 255, 255), av_center, 38, width=2)
        pygame.draw.circle(surface, (255, 255, 255, 120), (av_center[0], av_center[1] - 8), 16)
        p_ico = self.engine.get_icon("person", (32, 32))
        if p_ico:
            surface.blit(p_ico, p_ico.get_rect(center=av_center))
        else:
            av_txt = self.engine.font_hero.render("A", True, (255, 255, 255))
            surface.blit(av_txt, av_txt.get_rect(center=av_center))

        name_t = self.engine.font_hero.render("Alex  •  Frutiger Pilot", True, (255, 255, 255))
        surface.blit(name_t, (pr.x + 128, pr.y + 40))

        score_t = self.engine.font_title.render("18,450 G  •  Level 42 Master", True, (182, 245, 90))
        surface.blit(score_t, (pr.x + 130, pr.y + 76))

        trophies = [
            ("Master of Preservation", "Run 50 classic titles with rock-solid 60 FPS.", "🥇 GOLD"),
            ("Super Mario 16-Bit Legend", "Completed Super Mario World with all secrets.", "🥈 SILVER"),
            ("Night Raid Champion", "Won an online match in Street Fighter II Turbo.", "🥉 BRONZE"),
            ("C.C.I. Photomaster", "Captured HD gameplay frame with F12.", "🥉 BRONZE"),
        ]

        tx = pr.x + 36
        ty = pr.y + 140
        st = self.engine.font_title.render("Unlocked Achievements", True, (255, 255, 255))
        surface.blit(st, (tx, ty))

        for idx, (tname, tdesc, tbadge) in enumerate(trophies):
            ry = ty + 38 + idx * 72
            r = pygame.Rect(tx, ry, pr.width - 72, 60)
            self.engine.draw_acrylic_glass(surface, r, border_radius=10, tint_top=(255, 255, 255, 35), tint_bot=(10, 48, 80, 190), border_rgba=(255, 255, 255, 100))

            star_ico = self.engine.get_icon("star", (20, 20))
            if star_ico:
                surface.blit(star_ico, (r.x + 16, r.y + 18))
                tx_offset = 44
            else:
                tx_offset = 16

            b_t = self.engine.font_badge.render(tbadge, True, (255, 220, 60))
            surface.blit(b_t, (r.x + tx_offset, r.y + 12))

            n_t = self.engine.font_body.render(tname, True, (255, 255, 255))
            surface.blit(n_t, (r.x + tx_offset, r.y + 32))

            d_t = self.engine.font_sub.render(tdesc, True, (215, 238, 255))
            surface.blit(d_t, (r.x + 320, r.y + 20))


# ==============================================================================
# 6. VISTA AMIGOS Y ACTIVIDAD SOCIAL OFICIAL OMNIDASH AERO (.g-friends-flyout)
# ==============================================================================
class OmniDashCommunityView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.panel_rect = pygame.Rect(80, 50, self.w - 160, self.h - 100)
        self.back_btn_rect = pygame.Rect(self.panel_rect.right - 140, self.panel_rect.y + 24, 116, 36)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.engine.play_sound("navigate")
            return {"action": "BACK"}
        return None

    def render(self, surface: pygame.Surface):
        # Panel de cristal aguamarina translúcido oficial Frutiger Aero
        pr = self.panel_rect
        draw_aero_glass_panel(surface, pr, border_radius=16)

        # Botón Cerrar oficial con badge rojo B
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        draw_glass_rect(surface, self.back_btn_rect, (8, 45, 75, 220 if is_close_hov else 160), (182, 245, 90) if is_close_hov else (255, 255, 255, 140), border_radius=18)
        kbd_center = (self.back_btn_rect.x + 20, self.back_btn_rect.centery)
        pygame.draw.circle(surface, (208, 56, 58), kbd_center, 10)
        b_txt = self.engine.font_badge.render("B", True, (255, 255, 255))
        surface.blit(b_txt, b_txt.get_rect(center=kbd_center))
        c_txt = self.engine.font_btn.render("Close", True, (255, 255, 255))
        surface.blit(c_txt, (self.back_btn_rect.x + 38, self.back_btn_rect.centery - 7))

        title_t = self.engine.font_hero.render("👥  Friends & Live Activity", True, (255, 255, 255))
        surface.blit(title_t, (pr.x + 36, pr.y + 24))

        sub_t = self.engine.font_sub.render("Live multiplayer lobbies, tournament presence and voice chat", True, (215, 240, 255))
        surface.blit(sub_t, (pr.x + 38, pr.y + 58))

        friends = [
            ("Alex (You)", "Super Mario World • Star World 5", "● Online", (90, 166, 214)),
            ("Seeker Hub Central", "Metal Slug 2 • 2-Player Co-op Lobby", "● 14 online", (47, 124, 246)),
            ("Night Raid Elite", "Street Fighter II Turbo Tournament", "● 8 online", (142, 92, 247)),
            ("Retro Preservation Society", "Castlevania Symphony of the Night Party", "● 22 online", (47, 174, 75)),
        ]

        for idx, (gname, gactivity, gstatus, gcol) in enumerate(friends):
            gy = pr.y + 104 + idx * 88
            r = pygame.Rect(pr.x + 36, gy, pr.width - 72, 74)
            draw_glass_rect(surface, r, (255, 255, 255, 28), (255, 255, 255, 70), border_radius=12)
            pygame.draw.line(surface, (255, 255, 255, 110), (r.x + 10, r.y + 1), (r.right - 10, r.y + 1))

            orb = (r.x + 36, r.centery)
            pygame.draw.circle(surface, gcol, orb, 20)
            pygame.draw.circle(surface, (255, 255, 255, 190), orb, 20, width=1)
            ico = self.engine.font_body.render("👥", True, (255, 255, 255))
            surface.blit(ico, ico.get_rect(center=orb))

            gn = self.engine.font_body.render(gname, True, (255, 255, 255))
            surface.blit(gn, (r.x + 72, r.y + 16))

            ga = self.engine.font_sub.render(gactivity, True, (210, 235, 255))
            surface.blit(ga, (r.x + 74, r.y + 42))

            gs = self.engine.font_badge.render(gstatus, True, (182, 245, 90))
            surface.blit(gs, (r.right - gs.get_width() - 20, r.centery - 8))


# ==============================================================================
# 7. PANTALLA CINEMÁTICA DE LANZAMIENTO OFICIAL OMNIDASH AERO
# ==============================================================================
class OmniDashLaunchScreenView:
    def __init__(self, engine: OmniDashEngine, target_item: dict):
        self.engine = engine
        self.target = target_item
        self.elapsed = 0.0
        self.duration = 1.5
        self.engine.play_sound("startup")

        self.cover = None
        cpath = target_item.get("cover")
        if cpath:
            p = ROOT / cpath
            if p.exists():
                try:
                    loaded = pygame.image.load(str(p)).convert()
                    self.cover = pygame.transform.smoothscale(loaded, (engine.w, engine.h))
                except Exception:
                    pass

    def update(self, dt: float) -> dict | None:
        self.elapsed += dt
        if self.elapsed >= self.duration:
            return {"action": "LAUNCH_NOW", "target": self.target}
        return None

    def render(self, surface: pygame.Surface):
        progress = min(1.0, self.elapsed / self.duration)
        w, h = self.engine.w, self.engine.h

        if self.cover:
            scale_fac = 1.0 + progress * 0.08
            zw, zh = int(w * scale_fac), int(h * scale_fac)
            scaled = pygame.transform.smoothscale(self.cover, (zw, zh))
            surface.blit(scaled, (-(zw - w) // 2, -(zh - h) // 2))
        else:
            surface.fill((10, 30, 55))

        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((0, 20, 45, int(160 + progress * 50)))
        surface.blit(dim, (0, 0))

        ease_y = math.sin(progress * math.pi / 2)
        logo_y = int(h + 80 - ease_y * (h * 0.55 + 80))

        title_str = self.target.get("title", "Game Launch")
        t_surf = self.engine.font_hero.render(title_str, True, (255, 255, 255))
        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, logo_y)))

        meta_str = f"{self.target.get('console', self.target.get('badge', 'CONSOLA'))}  •  LIBRETRO 60 FPS"
        m_surf = self.engine.font_body.render(meta_str, True, (182, 245, 90))
        surface.blit(m_surf, m_surf.get_rect(center=(w // 2, logo_y + 44)))

        bw, bh = 420, 8
        bx = (w - bw) // 2
        by = h - 68
        pygame.draw.rect(surface, (255, 255, 255, 40), (bx, by, bw, bh), border_radius=4)
        fw = int(bw * progress)
        if fw > 0:
            pygame.draw.rect(surface, (182, 245, 90), (bx, by, fw, bh), border_radius=4)


# ==============================================================================
# 8. ESTADOS DE STATEMACHINE PARA MAIN.PY
# ==============================================================================
_SHARED_ENGINE = None

def get_shared_engine(w=1280, h=720) -> OmniDashEngine:
    global _SHARED_ENGINE
    if _SHARED_ENGINE is None:
        _SHARED_ENGINE = OmniDashEngine(w, h, active_theme="aero")
    return _SHARED_ENGINE


class OmniDashHomeState:
    def __init__(self, state_machine, on_game_launch=None):
        self.state_machine = state_machine
        self.on_game_launch = on_game_launch
        self.engine = get_shared_engine()
        self.home_view = OmniDashHomeView(self.engine)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            shell_res = self.engine.handle_shell_event(event)
            if shell_res:
                if shell_res.get("action") == "QUIT":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                    return
                elif shell_res.get("action") == "NAVIGATE":
                    dest = shell_res["destination"]
                    if dest != "HOME":
                        self.state_machine.change_state(dest)
                        return

            res = self.home_view.handle_event(event)
            if res:
                if res.get("action") == "OPEN_DETAILS":
                    self.state_machine.change_state("DETAILS", item=res["item"])
                elif res.get("action") == "NAVIGATE_UTIL":
                    self.state_machine.change_state(res["destination"])

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.home_view.render(screen)
        self.engine.render_top_bar(screen, active_tab="HOME")
        self.engine.render_bottom_dock(screen)


class OmniDashLibraryState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.library_view = OmniDashLibraryView(self.engine)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.library_view.handle_event(event)
            if res:
                if res.get("action") == "BACK":
                    self.state_machine.change_state("MENU")
                    return
                elif res.get("action") == "OPEN_DETAILS":
                    self.state_machine.change_state("DETAILS", item=res["item"])
                    return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.library_view.render(screen)


class OmniDashDetailsState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.details_view = None

    def enter(self, item=None, **kwargs):
        target = item or FEATURED_RECENT[0]
        self.details_view = OmniDashGameDetailsView(self.engine, target)

    def exit(self):
        pass

    def handle_events(self, events):
        if self.details_view:
            for event in events:
                res = self.details_view.handle_event(event)
                if res:
                    if res.get("action") == "BACK":
                        self.state_machine.change_state("LIBRARY")
                        return
                    elif res.get("action") == "LAUNCH":
                        self.state_machine.change_state("LAUNCH_ANIM", target=res["item"])
                        return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        if self.details_view:
            self.details_view.render(screen)


class OmniDashSettingsState:
    def __init__(self, state_machine, user_data=None, on_apply_display=None):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.settings_view = OmniDashSettingsView(self.engine, user_data, on_apply_display)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.settings_view.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")
                return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.settings_view.render(screen)


class OmniDashProfileState:
    def __init__(self, state_machine, user_data=None):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.profile_view = OmniDashProfileView(self.engine, user_data)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.profile_view.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")
                return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.profile_view.render(screen)


class OmniDashCommunityState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.comm_view = OmniDashCommunityView(self.engine)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.comm_view.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")
                return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.comm_view.render(screen)


class OmniDashLaunchAnimState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.launch_view = None

    def enter(self, target=None, **kwargs):
        if target:
            self.launch_view = OmniDashLaunchScreenView(self.engine, target)

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state_machine.change_state("MENU")
                return

    def update(self, dt):
        if self.launch_view:
            res = self.launch_view.update(dt)
            if res and res.get("action") == "LAUNCH_NOW":
                target = res["target"]
                if target.get("type") == "native" or not target.get("core"):
                    game_id = target.get("id", "").replace("native_", "")
                    self.state_machine.change_state("PLAYING", game_key=game_id)
                else:
                    self.state_machine.change_state(
                        "PLAYING",
                        game_key=target.get("title", "Game"),
                        rom_path=target.get("rom"),
                        core_path=target.get("core")
                    )

    def draw(self, screen):
        if self.launch_view:
            self.launch_view.render(screen)
