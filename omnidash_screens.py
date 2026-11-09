"""omnidash_screens.py - Suite Oficial Frutiger Aero de OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE y Libretro ctypes bridge.
Fidelidad absoluta a las capturas y estilos del repositorio oficial OmniDash (aero-home.jpg, aero-library.jpg, aero-settings.jpg):
- Home: Mosaico 1:1 cuadrado (Hero grande + 4 tarjetas cuadradas con arte en color + tarjeta 'My games & apps'),
  reflejos cristalinos sobre el mar turquesa, y 4 tarjetas esmeriladas abajo (Biblioteca, Amigos, Game Pass, Logros).
- Library: Barra lateral izquierda con anillo de almacenamiento y buscador, panel derecho con cuadrícula 1:1 de 5 columnas
  con carátulas completas en color y resplandor neón verde #b6f55a.
- Settings: Panel oficial aero-settings.jpg con 8 categorías con orbes de colores y filas agrupadas as-rows.
- Profile: Ficha de usuario con Gamerscore (18,450 G) y trofeos.
- Community: Grupos de emulación y amigos en línea.
- LaunchAnim: Secuencia oficial 'rises the game logo over key art' con audio startup.mp3.
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
# CARGADOR DE IMÁGENES EN COLOR DE ALTA DEFINICIÓN (CERO PLACAS GRISES)
# ==============================================================================
COLOR_COVERS = {
    # Clásicos Nintendo & Retro
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
    # Colección PlayStation / Modern
    "elden": "assets_ps4/img/elden.png",
    "red": "assets_ps4/img/red.png",
    "destiny": "assets_ps4/img/destiny.png",
    "spider": "assets_ps4/img/spider.png",
    "god": "assets_ps4/img/god.png",
    "horizon": "assets_ps4/img/horizon.png",
    "last": "assets_ps4/img/last.png",
    "mafia": "assets_ps4/img/mafia.png",
    "death": "assets_ps4/img/death.png",
    "tomb": "assets_ps4/img/tomb.png",
    "fifa": "assets_ps4/img/fifa.png",
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
        return "assets_ps4/img/red.png"
    elif console == "ARCADE":
        return "fotos web/metal slug.jpg"
    elif console == "NDS":
        return "fotos web/pokemon.webp"
    elif console == "NEO-GEO":
        return "assets_omnidash/covers/sega.webp"
    else:
        return "assets_ps4/img/elden.png"


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
            "desc": g.get("desc", "Juego oficial C.C.I. SYSTEM.")
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
                    "desc": f"16-Bit Super Nintendo: {clean_name}"
                })

    # 3. ROMs Arcade MAME
    mame_dir = roms_dir / "mame"
    if mame_dir.exists():
        for f in sorted(mame_dir.glob("*.zip")):
            clean_name = f.stem.upper()
            cov = pick_color_cover(clean_name, "ARCADE")
            games.append({
                "id": f"mame_{f.stem}",
                "title": f"Arcade: {clean_name}",
                "console": "Arcade",
                "badge": "ARCADE",
                "type": "libretro",
                "core": "cores/mame2003_plus_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "year": "1996",
                "developer": "SNK / Capcom / Midway",
                "desc": f"Recreativa Arcade clásica: {clean_name}"
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
                "desc": f"Aventura poligonal 64-Bit: {clean_name}"
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
                "desc": f"CD-ROM PlayStation 1: {clean_name}"
            })

    # 6. ROMs NDS
    nds_dir = roms_dir / "nds"
    if nds_dir.exists():
        for f in sorted(nds_dir.rglob("*.nds")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                if parts[0].isdigit():
                    clean_name = parts[1].strip()
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
                "desc": f"Doble pantalla táctil Nintendo DS: {clean_name}"
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
                "desc": f"Arcade 24-Bit Neo-Geo: {clean_name}"
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

# Títulos destacados de la fila principal Home (aero-home.jpg)
FEATURED_RECENT = [
    {
        "id": "hero_mario",
        "title": "Super Mario World",
        "subtitle": "Super Nintendo • Jugado hoy",
        "badge": "SNES",
        "cover": "fotos web/super mario.jpg",
        "core": "cores/snes9x_libretro.dylib",
        "rom": "roms/snes/Super Mario World 2 - Yoshi's Island (U) (V1.1).smc",
    },
    {
        "id": "rec_zelda",
        "title": "The Legend of Zelda",
        "subtitle": "N64 • 60 FPS",
        "badge": "N64",
        "cover": "fotos web/The_Legend_of_Zelda_film_logo.jpg",
        "core": "cores/mupen64plus_next_libretro.dylib",
        "rom": "roms/n64/Super Mario 64 (U) [!].z64",
    },
    {
        "id": "rec_slug",
        "title": "Metal Slug 2",
        "subtitle": "Arcade MAME",
        "badge": "ARCADE",
        "cover": "fotos web/metal slug.jpg",
        "core": "cores/mame2003_plus_libretro.dylib",
        "rom": "roms/mame/mslug2.zip",
    },
    {
        "id": "rec_pokemon",
        "title": "Pokémon White 2",
        "subtitle": "Nintendo DS",
        "badge": "NDS",
        "cover": "fotos web/pokemon.webp",
        "core": "cores/melonds_libretro.dylib",
        "rom": "roms/nds/Pokemon White Version 2/Pokemon White Version 2 (DSi Enhanced)(U)(frieNDS).nds",
    },
    {
        "id": "rec_castlevania",
        "title": "Castlevania: SotN",
        "subtitle": "PlayStation 1",
        "badge": "PS1",
        "cover": "fotos web/castlevania.webp",
        "core": "cores/mednafen_psx_hw_libretro.dylib",
        "rom": "roms/ps1/Castlevania - Symphony of the Night (USA).cue",
    },
    {
        "id": "rec_sonic",
        "title": "Sonic The Hedgehog",
        "subtitle": "Sega / 16-Bit",
        "badge": "SEGA",
        "cover": "assets_omnidash/covers/sonic.webp",
        "core": "cores/snes9x_libretro.dylib",
        "rom": "roms/snes/Doom (USA).sfc",
    },
]

# Consolas para compatibilidad
CONSOLES = FEATURED_RECENT

# Cache de texturas
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


def draw_glossy_square_card(surface: pygame.Surface, rect: pygame.Rect, img_path: str, is_focused: bool, title: str | None = None, badge: str | None = None, draw_reflection: bool = True):
    """Renderiza una tarjeta CUADRADA 1:1 con brillo de vidrio Frutiger Aero, resplandor verde #b6f55a y reflejo en el agua."""
    w, h = rect.width, rect.height
    rx, ry = rect.x, rect.y

    # 1. Imagen a sangre completa
    img = get_image(img_path, w, h)
    if img:
        surface.blit(img, (rx, ry))
    else:
        pygame.draw.rect(surface, (18, 54, 85), rect, border_radius=8)

    # 2. Gradiente de Brillo de Cristal Frutiger Aero (Top Half Gloss)
    # Exacto como en garrison-theme-aero.css::after
    gloss_surf = pygame.Surface((w, h // 2), pygame.SRCALPHA)
    for y in range(h // 2):
        alpha = int(75 * (1.0 - y / (h * 0.5)))
        pygame.draw.line(gloss_surf, (255, 255, 255, alpha), (0, y), (w, y))
    surface.blit(gloss_surf, (rx, ry))

    # Línea blanca brillante de 1px en el borde superior
    pygame.draw.line(surface, (255, 255, 255, 180), (rx + 4, ry), (rx + w - 4, ry))

    # 3. Estado de Foco o Borde Normal
    if is_focused:
        # Resplandor neón verde oficial OmniDash (--a-glow: #b6f55a)
        glow_col = (182, 245, 90)
        # Capa exterior translúcida
        glow_rect = rect.inflate(8, 8)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_col, 80), (0, 0, glow_rect.width, glow_rect.height), width=3, border_radius=12)
        surface.blit(glow_surf, glow_rect.topleft)

        # Borde interior nítido de 3px
        pygame.draw.rect(surface, glow_col, rect, width=3, border_radius=8)

        # Scrim inferior oscuro con título
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
        # Borde sutil de cristal
        pygame.draw.rect(surface, (255, 255, 255, 90), rect, width=1, border_radius=8)

    # 4. Reflejo cristalino sobre el mar debajo de la tarjeta (Home recent row)
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
        self.selected_idx = 0  # 0 es el Hero grande, 1-4 los pequeños, 5 My games & apps

        # Coordenadas exactas adaptadas de aero-home.jpg a 1280x720:
        # Hero grande: 200x200
        self.hero_rect = pygame.Rect(110, 155, 204, 204)

        # Fila de 4 tarjetas cuadradas pequeñas: 122x122 (alineadas abajo con el Hero)
        self.small_size = 122
        self.small_y = 155 + (204 - self.small_size)  # 237
        self.small_rects: list[pygame.Rect] = []
        for idx in range(4):
            sx = 330 + idx * (self.small_size + 14)
            self.small_rects.append(pygame.Rect(sx, self.small_y, self.small_size, self.small_size))

        # Tarjeta 6: 'My games & apps' al final de la fila
        mx = 330 + 4 * (self.small_size + 14)
        self.my_games_rect = pygame.Rect(mx, self.small_y, self.small_size, self.small_size)

        # 4 Tarjetas esmeriladas inferiores (aero-home.jpg)
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

            # Clic en Hero tile
            if self.hero_rect.collidepoint(mx, my):
                self.selected_idx = 0
                self.engine.play_sound("reward")
                return {"action": "LAUNCH_DIRECT", "item": FEATURED_RECENT[0]}

            # Clic en pequeñas tarjetas
            for idx, r in enumerate(self.small_rects):
                if r.collidepoint(mx, my):
                    self.selected_idx = idx + 1
                    self.engine.play_sound("reward")
                    return {"action": "LAUNCH_DIRECT", "item": FEATURED_RECENT[idx + 1]}

            # Clic en tarjeta My games & apps
            if self.my_games_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "NAVIGATE_UTIL", "destination": "LIBRARY"}

            # Clic en las 4 tarjetas de cristal inferiores
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
                    return {"action": "LAUNCH_DIRECT", "item": FEATURED_RECENT[self.selected_idx]}
                else:
                    return {"action": "NAVIGATE_UTIL", "destination": "LIBRARY"}

        return None

    def render(self, surface: pygame.Surface):
        # 1. Hero Card Grande Cuadrada (Izquierda)
        hero = FEATURED_RECENT[0]
        draw_glossy_square_card(
            surface,
            self.hero_rect,
            hero["cover"],
            is_focused=(self.selected_idx == 0),
            title=hero["title"],
            draw_reflection=True
        )

        # 2. Tarjetas Cuadradas Pequeñas (Derecha)
        for idx, r in enumerate(self.small_rects):
            item = FEATURED_RECENT[idx + 1]
            draw_glossy_square_card(
                surface,
                r,
                item["cover"],
                is_focused=(self.selected_idx == (idx + 1)),
                title=item["title"],
                draw_reflection=True
            )

        # 3. Tarjeta 'My games & apps' de la fila
        mr = self.my_games_rect
        is_m_sel = (self.selected_idx == 5)
        # Fondo cristal azul turquesa oficial
        m_surf = pygame.Surface((mr.width, mr.height), pygame.SRCALPHA)
        pygame.draw.rect(m_surf, (15, 85, 125, 220), (0, 0, mr.width, mr.height), border_radius=8)
        # Línea de brillo
        pygame.draw.line(m_surf, (255, 255, 255, 180), (4, 0), (mr.width - 4, 0))
        surface.blit(m_surf, mr.topleft)

        # Borde de foco o normal
        if is_m_sel:
            pygame.draw.rect(surface, (182, 245, 90), mr, width=3, border_radius=8)
        else:
            pygame.draw.rect(surface, (255, 255, 255, 90), mr, width=1, border_radius=8)

        # Icono de biblioteca y texto
        lib_ico = self.engine.font_hero.render("📚", True, (255, 255, 255))
        surface.blit(lib_ico, lib_ico.get_rect(center=(mr.centerx, mr.centery - 18)))

        lib_t = self.engine.font_badge.render("My games & apps", True, (255, 255, 255))
        surface.blit(lib_t, lib_t.get_rect(center=(mr.centerx, mr.centery + 18)))

        count_t = self.engine.font_badge.render(f"{len(ALL_GAMES)} games", True, (180, 225, 255))
        surface.blit(count_t, count_t.get_rect(center=(mr.centerx, mr.centery + 34)))

        # 4. Cuatro Tarjetas Esmeriladas Inferiores Oficiales (aero-home.jpg)
        glass_cards_data = [
            {
                "title": "My games & apps",
                "sub": f"{len(ALL_GAMES)} games\nReady to play",
                "badge": "LIBRARY",
                "img_preview": "fotos web/donkeykong.jpg"
            },
            {
                "title": "Friends",
                "sub": "Seeker & Night Raid\n3 friends online right now",
                "badge": "FRIENDS",
                "img_preview": None
            },
            {
                "title": "GAME PASS",
                "sub": "Discover\nHundreds of great games",
                "badge": "PASS",
                "img_preview": "assets_omnidash/covers/battlefield.webp"
            },
            {
                "title": "Achievements",
                "sub": "18,450 G\nHorizon Superstar · 40G",
                "badge": "18,450",
                "img_preview": None
            },
        ]

        for idx, gc in enumerate(glass_cards_data):
            r = self.glass_card_rects[idx]
            is_hov = r.collidepoint(pygame.mouse.get_pos())

            # Vidrio esmerilado con gradiente turquesa-azul oficial
            g_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            if gc["badge"] == "PASS":
                # Game Pass usa tinte verde esmeralda (#0d5a2a)
                pygame.draw.rect(g_surf, (13, 90, 42, 210), (0, 0, r.width, r.height), border_radius=10)
            else:
                pygame.draw.rect(g_surf, (25, 110, 150, 180 if is_hov else 140), (0, 0, r.width, r.height), border_radius=10)

            # Brillo superior
            pygame.draw.line(g_surf, (255, 255, 255, 180), (4, 0), (r.width - 4, 0))
            surface.blit(g_surf, r.topleft)

            # Borde
            b_col = (182, 245, 90) if is_hov else (255, 255, 255, 100)
            pygame.draw.rect(surface, b_col, r, width=2 if is_hov else 1, border_radius=10)

            # Textos
            t_t = self.engine.font_body.render(gc["title"], True, (255, 255, 255))
            surface.blit(t_t, (r.x + 16, r.y + 14))

            lines = gc["sub"].split("\n")
            for l_idx, line in enumerate(lines):
                st = self.engine.font_sub.render(line, True, (215, 240, 255))
                surface.blit(st, (r.x + 16, r.y + 60 + l_idx * 18))

            # Imagen de vista previa a la derecha si existe
            if gc["img_preview"]:
                prev_img = get_image(gc["img_preview"], 70, 70)
                if prev_img:
                    surface.blit(prev_img, (r.right - 84, r.y + 16))
                    pygame.draw.rect(surface, (255, 255, 255, 120), (r.right - 84, r.y + 16, 70, 70), width=1, border_radius=6)


# ==============================================================================
# 2. VISTA BIBLIOTECA OFICIAL OMNIDASH AERO (OmniDashLibraryView)
# ==============================================================================
class OmniDashLibraryView:
    """Pantalla exacta a aero-library.jpg:
    - Barra lateral izquierda con anillo de almacenamiento, buscador y pestañas.
    - Panel derecho de vidrio con título 'Games' y cuadrícula 1:1 de 5 columnas.
    """
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_category = "Games"
        self.selected_game_idx = 0
        self.search_query = ""

        # Rectángulos estructurales oficiales
        self.sidebar_rect = pygame.Rect(32, 24, 250, 672)
        self.content_rect = pygame.Rect(298, 24, 950, 672)
        self.back_btn_rect = pygame.Rect(48, 38, 90, 32)
        self.search_rect = pygame.Rect(48, 140, 218, 34)

        self.categories = [
            {"id": "Games", "label": "Games", "count": len(ALL_GAMES)},
            {"id": "SNES", "label": "Super Nintendo", "count": 15},
            {"id": "ARCADE", "label": "Arcade MAME", "count": 6},
            {"id": "N64", "label": "Nintendo 64", "count": 5},
            {"id": "PS1", "label": "PlayStation 1", "count": 6},
            {"id": "NDS", "label": "Nintendo DS", "count": 6},
            {"id": "NEO-GEO", "label": "Neo-Geo", "count": 3},
            {"id": "CCI", "label": "Juegos C.C.I.", "count": 19},
        ]
        self.cat_rects: list[pygame.Rect] = []
        self.game_card_rects: list[pygame.Rect] = []

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.back_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}

            # Clic en categorías del sidebar
            for idx, r in enumerate(self.cat_rects):
                if r.collidepoint(mx, my):
                    self.selected_category = self.categories[idx]["id"]
                    self.selected_game_idx = 0
                    self.engine.play_sound("navigate")
                    return None

            # Clic en cuadrícula de juegos
            for idx, r in enumerate(self.game_card_rects):
                if r.collidepoint(mx, my):
                    if idx < len(filtered):
                        self.engine.play_sound("reward")
                        return {"action": "LAUNCH_GAME", "game": filtered[idx]}

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
                if self.selected_game_idx + 5 < len(filtered):
                    self.selected_game_idx += 5
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.selected_game_idx - 5 >= 0:
                    self.selected_game_idx -= 5
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if filtered and self.selected_game_idx < len(filtered):
                    self.engine.play_sound("reward")
                    return {"action": "LAUNCH_GAME", "game": filtered[self.selected_game_idx]}

        return None

    def render(self, surface: pygame.Surface):
        # 1. Barra Lateral Izquierda (#g-lib-side en aero-library.jpg)
        sr = self.sidebar_rect
        s_surf = pygame.Surface((sr.width, sr.height), pygame.SRCALPHA)
        pygame.draw.rect(s_surf, (20, 105, 150, 190), (0, 0, sr.width, sr.height), border_radius=14)
        pygame.draw.line(s_surf, (255, 255, 255, 190), (4, 0), (sr.width - 4, 0))
        surface.blit(s_surf, sr.topleft)
        pygame.draw.rect(surface, (255, 255, 255, 110), sr, width=1, border_radius=14)

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 90 if is_back_hov else 40), self.back_btn_rect, border_radius=16)
        pygame.draw.rect(surface, (255, 255, 255, 160), self.back_btn_rect, width=1, border_radius=16)
        bt = self.engine.font_btn.render("⇦  Home", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Anillo de almacenamiento oficial ("72% used")
        ring_center = (sr.centerx, 104)
        pygame.draw.circle(surface, (255, 255, 255, 40), ring_center, 22, width=4)
        pygame.draw.circle(surface, (182, 245, 90), ring_center, 22, width=4)
        r_txt = self.engine.font_badge.render("72%", True, (255, 255, 255))
        surface.blit(r_txt, r_txt.get_rect(center=ring_center))

        # Buscador
        pygame.draw.rect(surface, (255, 255, 255, 40), self.search_rect, border_radius=17)
        pygame.draw.rect(surface, (255, 255, 255, 100), self.search_rect, width=1, border_radius=17)
        srch_t = self.engine.font_sub.render("🔍  Search games...", True, (210, 235, 255))
        surface.blit(srch_t, (self.search_rect.x + 14, self.search_rect.y + 8))

        # Pestañas de categorías
        self.cat_rects = []
        cy = 194
        for idx, cat in enumerate(self.categories):
            r = pygame.Rect(48, cy, 218, 44)
            self.cat_rects.append(r)

            is_sel = (cat["id"] == self.selected_category)
            if is_sel:
                pygame.draw.rect(surface, (255, 255, 255, 70), r, border_radius=10)
                pygame.draw.rect(surface, (182, 245, 90), r, width=2, border_radius=10)

            c_name = self.engine.font_body.render(cat["label"], True, (255, 255, 255))
            surface.blit(c_name, (r.x + 14, r.y + 12))

            c_count = self.engine.font_badge.render(str(cat["count"]), True, (182, 245, 90) if is_sel else (200, 225, 255))
            surface.blit(c_count, (r.right - c_count.get_width() - 14, r.y + 14))

            cy += 50

        # 2. Panel Principal de Contenido (.console-library-content en aero-library.jpg)
        cr = self.content_rect
        c_surf = pygame.Surface((cr.width, cr.height), pygame.SRCALPHA)
        pygame.draw.rect(c_surf, (10, 70, 115, 170), (0, 0, cr.width, cr.height), border_radius=14)
        pygame.draw.line(c_surf, (255, 255, 255, 160), (4, 0), (cr.width - 4, 0))
        surface.blit(c_surf, cr.topleft)
        pygame.draw.rect(surface, (255, 255, 255, 100), cr, width=1, border_radius=14)

        # Encabezado
        filtered = self._filtered_games()
        head_t = self.engine.font_hero.render("Games", True, (255, 255, 255))
        surface.blit(head_t, (cr.x + 30, cr.y + 24))

        sub_t = self.engine.font_sub.render(f"{len(filtered)} games installed  •  Ready to play", True, (210, 235, 255))
        surface.blit(sub_t, (cr.x + 32, cr.y + 56))

        # Botones de filtro y ordenación derecha
        sort_r = pygame.Rect(cr.right - 140, cr.y + 26, 110, 32)
        pygame.draw.rect(surface, (255, 255, 255, 40), sort_r, border_radius=16)
        pygame.draw.rect(surface, (255, 255, 255, 100), sort_r, width=1, border_radius=16)
        st_txt = self.engine.font_sub.render("Sort: A-Z  ▼", True, (255, 255, 255))
        surface.blit(st_txt, st_txt.get_rect(center=sort_r.center))

        # 3. Cuadrícula 1:1 de 5 Columnas de Tarjetas Cuadradas Brillantes
        self.game_card_rects = []
        cols = 5
        card_w = 166
        card_h = 166
        gap_x = 18
        gap_y = 18
        start_x = cr.x + 30
        start_y = cr.y + 96

        for idx, g in enumerate(filtered[:15]):  # 3 filas de 5
            col = idx % cols
            row = idx // cols
            gx = start_x + col * (card_w + gap_x)
            gy = start_y + row * (card_h + gap_y)

            r = pygame.Rect(gx, gy, card_w, card_h)
            self.game_card_rects.append(r)

            draw_glossy_square_card(
                surface,
                r,
                g["cover"],
                is_focused=(idx == self.selected_game_idx),
                title=g["title"],
                draw_reflection=False
            )


# ==============================================================================
# 3. VISTA AJUSTES OFICIAL OMNIDASH AERO (OmniDashSettingsView)
# ==============================================================================
class OmniDashSettingsView:
    """Pantalla exacta a aero-settings.jpg (#g-aero-settings):
    - Fondo de cristal oscuro translúcido.
    - Barra lateral con 8 categorías oficiales y sus orbes circulares de color.
    - Panel derecho con encabezado y opciones agrupadas en filas nítidas.
    """
    def __init__(self, engine: OmniDashEngine, user_data=None, on_apply_display=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.on_apply_display = on_apply_display

        self.categories = [
            {"id": "appearance", "name": "Appearance", "icon": "🎨", "color": (142, 92, 247), "desc": "Frutiger Aero theme, glass effects and UI scale."},
            {"id": "display_sound", "name": "Display & sound", "icon": "📺", "color": (47, 124, 246), "desc": "Resolution, fullscreen mode and audio volumes."},
            {"id": "controllers", "name": "Controllers & headsets", "icon": "🎮", "color": (47, 174, 75), "desc": "Button layout, haptic rumble and triggers."},
            {"id": "notifications", "name": "Notifications", "icon": "🔔", "color": (239, 75, 75), "desc": "Gamerscore achievement toasts and friend alerts."},
            {"id": "library", "name": "Library & Emulation", "icon": "📁", "color": (242, 147, 31), "desc": "60 FPS Libretro cores, ROM directories and regions."},
            {"id": "account", "name": "Profile & system", "icon": "👤", "color": (90, 122, 156), "desc": "Alex (18,450 G), Gamertag and custom avatar."},
            {"id": "accessibility", "name": "Accessibility", "icon": "♿", "color": (31, 155, 224), "desc": "Reduced motion, high contrast focus and text size."},
            {"id": "system", "name": "System", "icon": "⚙️", "color": (122, 127, 135), "desc": "C.C.I. System v2.1.0, disk storage and state saves."},
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

            # Clic en categorías
            for idx, r in enumerate(self.cat_rects):
                if r.collidepoint(mx, my):
                    self.selected_cat_idx = idx
                    self.selected_row_idx = 0
                    self.engine.play_sound("navigate")
                    return None

            # Clic en filas
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
        # Contenedor global de vidrio oscuro con gradiente
        pr = self.panel_rect
        p_surf = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (15, 25, 42, 235), (0, 0, pr.width, pr.height), border_radius=18)
        pygame.draw.line(p_surf, (255, 255, 255, 140), (4, 0), (pr.width - 4, 0))
        surface.blit(p_surf, pr.topleft)
        pygame.draw.rect(surface, (255, 255, 255, 80), pr, width=1, border_radius=18)

        # Encabezado oficial aero-settings.jpg
        t_head = self.engine.font_hero.render("Settings", True, (255, 255, 255))
        surface.blit(t_head, (pr.x + 32, pr.y + 20))

        t_sub = self.engine.font_sub.render("Customise your console, display, audio and accounts", True, (185, 215, 240))
        surface.blit(t_sub, (pr.x + 34, pr.y + 54))

        # Botón Cerrar
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 80 if is_close_hov else 40), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, (255, 255, 255, 140), self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Close", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # 1. Barra Lateral con Orbes de Color
        side_x = pr.x + 28
        side_y = pr.y + 92
        side_w = 320
        self.cat_rects = []

        for idx, cat in enumerate(self.categories):
            cy = side_y + idx * 56
            r = pygame.Rect(side_x, cy, side_w, 48)
            self.cat_rects.append(r)

            is_sel = (idx == self.selected_cat_idx)
            if is_sel:
                pygame.draw.rect(surface, (255, 255, 255, 50), r, border_radius=10)
                pygame.draw.rect(surface, (182, 245, 90), r, width=2, border_radius=10)

            # Orbe circular oficial de color
            orb_center = (side_x + 24, cy + 24)
            pygame.draw.circle(surface, cat["color"], orb_center, 15)
            pygame.draw.circle(surface, (255, 255, 255, 180), orb_center, 15, width=1)
            ico_t = self.engine.font_badge.render(cat["icon"], True, (255, 255, 255))
            surface.blit(ico_t, ico_t.get_rect(center=orb_center))

            c_lbl = self.engine.font_body.render(cat["name"], True, (255, 255, 255) if is_sel else (200, 220, 240))
            surface.blit(c_lbl, (side_x + 50, cy + 14))

        # 2. Panel Derecho de Opciones Agrupadas
        cur_cat = self.categories[self.selected_cat_idx]
        rx = side_x + side_w + 24
        ry = side_y
        rw = pr.width - side_w - 76
        rh = pr.height - 116

        r_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(r_surf, (22, 32, 48, 220), (0, 0, rw, rh), border_radius=14)
        surface.blit(r_surf, (rx, ry))
        pygame.draw.rect(surface, (255, 255, 255, 40), (rx, ry, rw, rh), width=1, border_radius=14)

        # Encabezado de sección
        head_orb = (rx + 34, ry + 32)
        pygame.draw.circle(surface, cur_cat["color"], head_orb, 20)
        h_ico = self.engine.font_title.render(cur_cat["icon"], True, (255, 255, 255))
        surface.blit(h_ico, h_ico.get_rect(center=head_orb))

        st_title = self.engine.font_title.render(cur_cat["name"], True, (255, 255, 255))
        surface.blit(st_title, (rx + 68, ry + 18))

        st_desc = self.engine.font_sub.render(cur_cat["desc"], True, (170, 200, 230))
        surface.blit(st_desc, (rx + 70, ry + 44))

        # Filas de opciones
        rows = self._get_rows()
        self.row_rects = []
        row_y = ry + 80

        for idx, row in enumerate(rows):
            r = pygame.Rect(rx + 16, row_y + idx * 68, rw - 32, 58)
            self.row_rects.append(r)

            is_sel = (idx == self.selected_row_idx)
            row_bg = (255, 255, 255, 45) if is_sel else (255, 255, 255, 12)
            pygame.draw.rect(surface, row_bg, r, border_radius=10)
            if is_sel:
                pygame.draw.rect(surface, (182, 245, 90), r, width=2, border_radius=10)

            l_lbl = self.engine.font_body.render(row["label"], True, (255, 255, 255))
            surface.blit(l_lbl, (r.x + 16, r.y + 10))

            s_lbl = self.engine.font_badge.render(row["sub"], True, (160, 190, 220))
            surface.blit(s_lbl, (r.x + 16, r.y + 32))

            v_lbl = self.engine.font_body.render(str(row["val"]), True, (182, 245, 90) if is_sel else (255, 255, 255))
            surface.blit(v_lbl, (r.right - v_lbl.get_width() - 16, r.y + 18))


# ==============================================================================
# 4. VISTA PERFIL & GAMERSCORE OFICIAL OMNIDASH AERO (OmniDashProfileView)
# ==============================================================================
class OmniDashProfileView:
    def __init__(self, engine: OmniDashEngine, user_data=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.panel_rect = pygame.Rect(54, 40, self.w - 108, self.h - 80)
        self.back_btn_rect = pygame.Rect(self.w - 190, 56, 120, 36)

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
        pr = self.panel_rect
        p_surf = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (15, 25, 42, 235), (0, 0, pr.width, pr.height), border_radius=18)
        surface.blit(p_surf, pr.topleft)
        pygame.draw.rect(surface, (255, 255, 255, 80), pr, width=1, border_radius=18)

        # Botón Cerrar
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 80 if is_close_hov else 40), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, (255, 255, 255, 140), self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Close", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Avatar circular
        av_center = (pr.x + 80, pr.y + 70)
        pygame.draw.circle(surface, (90, 166, 214), av_center, 40)
        pygame.draw.circle(surface, (255, 255, 255), av_center, 40, width=2)
        av_txt = self.engine.font_hero.render("A", True, (255, 255, 255))
        surface.blit(av_txt, av_txt.get_rect(center=av_center))

        name_t = self.engine.font_hero.render("Alex  •  Frutiger Pilot", True, (255, 255, 255))
        surface.blit(name_t, (pr.x + 138, pr.y + 42))

        # Gamerscore 18,450 G
        score_t = self.engine.font_title.render("18,450 G  •  Level 42 Master", True, (182, 245, 90))
        surface.blit(score_t, (pr.x + 140, pr.y + 78))

        # Lista de logros
        trophies = [
            ("Master of Preservation", "Run 50 classic titles with rock-solid 60 FPS.", "🥇 GOLD"),
            ("Super Mario 16-Bit Legend", "Completed Super Mario World with all secrets.", "🥈 SILVER"),
            ("Night Raid Champion", "Won an online match in Street Fighter II Turbo.", "🥉 BRONZE"),
            ("C.C.I. Photomaster", "Captured HD gameplay frame with F12.", "🥉 BRONZE"),
        ]

        tx = pr.x + 40
        ty = pr.y + 146
        st = self.engine.font_title.render("Unlocked Achievements", True, (255, 255, 255))
        surface.blit(st, (tx, ty))

        for idx, (tname, tdesc, tbadge) in enumerate(trophies):
            ry = ty + 38 + idx * 72
            r = pygame.Rect(tx, ry, pr.width - 80, 60)
            pygame.draw.rect(surface, (255, 255, 255, 20), r, border_radius=10)
            pygame.draw.rect(surface, (255, 255, 255, 50), r, width=1, border_radius=10)

            b_t = self.engine.font_badge.render(tbadge, True, (255, 220, 60))
            surface.blit(b_t, (r.x + 16, r.y + 12))

            n_t = self.engine.font_body.render(tname, True, (255, 255, 255))
            surface.blit(n_t, (r.x + 16, r.y + 32))

            d_t = self.engine.font_sub.render(tdesc, True, (180, 205, 235))
            surface.blit(d_t, (r.x + 320, r.y + 20))


# ==============================================================================
# 5. VISTA COMUNIDAD C.C.I. OMNIDASH AERO (OmniDashCommunityView)
# ==============================================================================
class OmniDashCommunityView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.panel_rect = pygame.Rect(54, 40, self.w - 108, self.h - 80)
        self.back_btn_rect = pygame.Rect(self.w - 190, 56, 120, 36)

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
        pr = self.panel_rect
        p_surf = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (15, 25, 42, 235), (0, 0, pr.width, pr.height), border_radius=18)
        surface.blit(p_surf, pr.topleft)
        pygame.draw.rect(surface, (255, 255, 255, 80), pr, width=1, border_radius=18)

        # Botón Cerrar
        is_close_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 80 if is_close_hov else 40), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, (255, 255, 255, 140), self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Close", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        title_t = self.engine.font_hero.render("C.C.I. Gaming Communities & Friends", True, (255, 255, 255))
        surface.blit(title_t, (pr.x + 36, pr.y + 24))

        sub_t = self.engine.font_sub.render("Live multiplayer lobbies, tournament chats and presence", True, (185, 215, 240))
        surface.blit(sub_t, (pr.x + 38, pr.y + 56))

        groups = [
            ("Seeker Hub Central", "3 friends playing Metal Slug 2", "● 14 online", (47, 124, 246)),
            ("Night Raid Elite", "Street Fighter II Turbo Tournament", "● 8 online", (142, 92, 247)),
            ("Retro Preservation Society", "Castlevania Symphony of the Night Party", "● 22 online", (47, 174, 75)),
        ]

        for idx, (gname, gactivity, gstatus, gcol) in enumerate(groups):
            gy = pr.y + 110 + idx * 96
            r = pygame.Rect(pr.x + 36, gy, pr.width - 72, 78)
            pygame.draw.rect(surface, (255, 255, 255, 22), r, border_radius=12)
            pygame.draw.rect(surface, (255, 255, 255, 60), r, width=1, border_radius=12)

            orb = (r.x + 36, r.y + 39)
            pygame.draw.circle(surface, gcol, orb, 20)
            ico = self.engine.font_body.render("👥", True, (255, 255, 255))
            surface.blit(ico, ico.get_rect(center=orb))

            gn = self.engine.font_body.render(gname, True, (255, 255, 255))
            surface.blit(gn, (r.x + 72, r.y + 18))

            ga = self.engine.font_sub.render(gactivity, True, (185, 215, 240))
            surface.blit(ga, (r.x + 74, r.y + 44))

            gs = self.engine.font_badge.render(gstatus, True, (182, 245, 90))
            surface.blit(gs, (r.right - gs.get_width() - 20, r.y + 30))


# ==============================================================================
# 6. PANTALLA CINEMÁTICA DE LANZAMIENTO OFICIAL OMNIDASH AERO
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

        # Easing curve para elevación de logo
        ease_y = math.sin(progress * math.pi / 2)
        logo_y = int(h + 80 - ease_y * (h * 0.55 + 80))

        title_str = self.target.get("title", "Game Launch")
        t_surf = self.engine.font_hero.render(title_str, True, (255, 255, 255))
        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, logo_y)))

        meta_str = f"{self.target.get('console', self.target.get('badge', 'CONSOLA'))}  •  LIBRETRO 60 FPS"
        m_surf = self.engine.font_body.render(meta_str, True, (182, 245, 90))
        surface.blit(m_surf, m_surf.get_rect(center=(w // 2, logo_y + 44)))

        # Barra de carga verde neón #b6f55a
        bw, bh = 420, 8
        bx = (w - bw) // 2
        by = h - 68
        pygame.draw.rect(surface, (255, 255, 255, 40), (bx, by, bw, bh), border_radius=4)
        fw = int(bw * progress)
        if fw > 0:
            pygame.draw.rect(surface, (182, 245, 90), (bx, by, fw, bh), border_radius=4)


# ==============================================================================
# 7. ESTADOS PARA STATEMACHINE EN MAIN.PY
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
                if res.get("action") == "LAUNCH_DIRECT":
                    self.state_machine.change_state("LAUNCH_ANIM", target=res["item"])
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
                elif res.get("action") == "LAUNCH_GAME":
                    self.state_machine.change_state("LAUNCH_ANIM", target=res["game"])
                    return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.library_view.render(screen)


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


class OmniDashDetailsState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.item = None

    def enter(self, item=None, **kwargs):
        self.item = item or FEATURED_RECENT[0]

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.state_machine.change_state("MENU")
                    return
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.item:
                        self.state_machine.change_state("LAUNCH_ANIM", target=self.item)
                        return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        if self.item:
            w, h = screen.get_size()
            rect = pygame.Rect(100, 100, w - 200, h - 200)
            pygame.draw.rect(screen, (20, 30, 45, 230), rect, border_radius=16)
            pygame.draw.rect(screen, (182, 245, 90), rect, width=2, border_radius=16)
            t = self.engine.font_hero.render(self.item.get("title", ""), True, (255, 255, 255))
            screen.blit(t, (rect.x + 40, rect.y + 40))
            sub = self.engine.font_body.render(self.item.get("subtitle", self.item.get("desc", "")), True, (180, 210, 240))
            screen.blit(sub, (rect.x + 42, rect.y + 90))
            btn = self.engine.font_btn.render("Press [ ENTER ] to play  •  [ ESC ] Back", True, (182, 245, 90))
            screen.blit(btn, (rect.x + 42, rect.bottom - 60))
        self.engine.render_bottom_dock(screen)


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
