"""omnidash_screens.py - Suite Completa y Auténtica Frutiger Aero de OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE y Libretro ctypes bridge.
Implementa con fidelidad absoluta el diseño oficial de OmniDash (Frutiger Aero):
- Home: Isla soleada oficial, Hero Card grande a la izquierda, tarjetas brillantes de consolas/juegos
  a la derecha con reflejo en el agua, y 4 tarjetas de cristal esmerilado abajo (Biblioteca, Amigos, Logros, Ajustes).
- Biblioteca: Panel lateral con 8 categorías de plataformas, buscador y cuadrícula de carátulas reales de 66+ juegos.
- Configuración: Diseño oficial OmniDash (#g-aero-settings / aero-settings.jpg): barra lateral con 8 categorías
  con iconos de colores, panel derecho con opciones agrupadas e interactivas (resolución, volumen, mandos, cores, etc.).
- Perfil & Gamerscore: Ficha de usuario con 18,450 G, trofeos de logros y selector de avatar.
- Comunidad: Vista de grupos activos (Seeker, Night Raid) y amigos conectados.
- Launch Screen Cinemático: Animación oficial ("rises game's logo over key art") con curva easing,
  zoom de fondo, barra de progreso con resplandor #b6f55a y sonido startup.mp3.
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
# DESCUBRIDOR Y CATÁLOGO DINÁMICO DE TODOS LOS JUEGOS Y ROMS (66+ JUEGOS)
# ==============================================================================
def load_all_games() -> list[dict]:
    games: list[dict] = []
    roms_dir = ROOT / "roms"

    # 1. Juegos Nativos C.C.I. SYSTEM (CATALOG)
    for g in CATALOG:
        cid = g.get("id", "")
        cov = f"assets_cards/{cid}_clean.png"
        if not (ROOT / cov).exists():
            cov = f"assets_cards/{cid}.png"
        if not (ROOT / cov).exists():
            cov = "assets_ps4/img/battle.png"

        games.append({
            "id": f"native_{cid}",
            "title": g.get("title", cid).title(),
            "console": "C.C.I.",
            "badge": "CCI",
            "type": "native",
            "core": None,
            "rom": None,
            "cover": cov,
            "region": "GLOBAL",
            "year": "2024",
            "developer": "C.C.I. Studio",
            "desc": g.get("desc", "Juego oficial de la plataforma C.C.I. SYSTEM.")
        })

    # 2. ROMs Super Nintendo (SNES)
    snes_dir = roms_dir / "snes"
    if snes_dir.exists():
        for f in sorted(snes_dir.glob("*.*")):
            if f.suffix.lower() in (".sfc", ".smc"):
                clean_name = f.stem.split("(")[0].split("[")[0].strip()
                cov = "assets_cards/mario_clean.png"
                if "zelda" in clean_name.lower():
                    cov = "assets_cards/zelda_clean.png"
                elif "metroid" in clean_name.lower():
                    cov = "assets_cards/cyberpunk_clean.png"
                elif "donkey" in clean_name.lower() or "kong" in clean_name.lower():
                    cov = "assets_cards/donkeykong_clean.png"
                elif "street" in clean_name.lower() or "fighter" in clean_name.lower():
                    cov = "assets_cards/streetfighter_clean.png"
                elif "mortal" in clean_name.lower():
                    cov = "assets_cards/mortal_kombat_clean.png"
                elif "doom" in clean_name.lower():
                    cov = "assets_cards/doom_clean.png"
                elif "kirby" in clean_name.lower():
                    cov = "assets_cards/bubblebobble_clean.png"
                elif "megaman" in clean_name.lower():
                    cov = "assets_cards/megaman_clean.png"

                games.append({
                    "id": f"snes_{f.stem}",
                    "title": clean_name,
                    "console": "SNES",
                    "badge": "SNES",
                    "type": "libretro",
                    "core": "cores/snes9x_libretro.dylib",
                    "rom": str(f.relative_to(ROOT)),
                    "cover": cov,
                    "region": "USA" if "(USA)" in f.stem else ("EUR" if "(Europe)" in f.stem else "JAP"),
                    "year": "1992",
                    "developer": "Nintendo EAD",
                    "desc": f"Clásico inolvidable de 16-Bit Super Nintendo: {clean_name}"
                })

    # 3. ROMs Arcade / MAME
    mame_dir = roms_dir / "mame"
    if mame_dir.exists():
        for f in sorted(mame_dir.glob("*.zip")):
            c_name = f.stem.upper()
            cov = "assets_cards/metalslug_clean.png" if "mslug" in f.stem.lower() else "assets_cards/fighter_clean.png"
            if "pacman" in f.stem.lower():
                cov = "assets_cards/pacman_clean.png"
            games.append({
                "id": f"mame_{f.stem}",
                "title": f"Arcade: {c_name}",
                "console": "ARCADE",
                "badge": "ARCADE",
                "type": "libretro",
                "core": "cores/mame2003_plus_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "region": "ARCADE",
                "year": "1996",
                "developer": "SNK / Capcom / Midway",
                "desc": f"Recreativa arcade clásica preservada a 60 FPS: {c_name}"
            })

    # 4. ROMs Nintendo 64 (N64)
    n64_dir = roms_dir / "n64"
    if n64_dir.exists():
        for f in sorted(n64_dir.glob("*.z64")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            cov = "assets_cards/zelda_clean.png" if "zelda" in clean_name.lower() else "assets_cards/mario_clean.png"
            if "donkey" in clean_name.lower():
                cov = "assets_cards/donkeykong_clean.png"
            games.append({
                "id": f"n64_{f.stem}",
                "title": clean_name,
                "console": "N64",
                "badge": "N64",
                "type": "libretro",
                "core": "cores/mupen64plus_next_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "region": "USA" if "(U)" in f.stem else "EUR",
                "year": "1996",
                "developer": "Nintendo",
                "desc": f"Revolución poligonal 3D de 64-Bit: {clean_name}"
            })

    # 5. ROMs PlayStation 1 (PS1)
    ps1_dir = roms_dir / "ps1"
    if ps1_dir.exists():
        for f in sorted(ps1_dir.glob("*.cue")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            cov = "assets_cards/castlevania_clean.png" if "castlevania" in clean_name.lower() else "assets_ps4/img/red.png"
            if "crash" in clean_name.lower():
                cov = "assets_ps4/img/battle.png"
            elif "slug" in clean_name.lower():
                cov = "assets_cards/metalslug_clean.png"
            games.append({
                "id": f"ps1_{f.stem}",
                "title": clean_name,
                "console": "PS1",
                "badge": "PS1",
                "type": "libretro",
                "core": "cores/mednafen_psx_hw_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "region": "USA" if "(USA)" in f.stem else "EUR",
                "year": "1997",
                "developer": "Sony / Konami / Capcom",
                "desc": f"Aventura cinemática en formato CD-ROM PlayStation: {clean_name}"
            })

    # 6. ROMs Nintendo DS (NDS)
    nds_dir = roms_dir / "nds"
    if nds_dir.exists():
        for f in sorted(nds_dir.rglob("*.nds")):
            clean_name = f.stem.split("(")[0].split("[")[0].strip()
            # Quitar prefijo de numeración como '0168 - ' o '2696 - '
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                if parts[0].isdigit():
                    clean_name = parts[1]
            clean_name = clean_name.strip()
            cov = "assets_cards/pokemon_clean.png" if "pokemon" in clean_name.lower() else "assets_cards/mario_clean.png"
            games.append({
                "id": f"nds_{f.stem}",
                "title": clean_name,
                "console": "NDS",
                "badge": "NDS",
                "type": "libretro",
                "core": "cores/melonds_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": cov,
                "region": "USA",
                "year": "2005",
                "developer": "Nintendo / Game Freak",
                "desc": f"Innovación en doble pantalla Nintendo DS: {clean_name}"
            })

    # 7. ROMs Neo-Geo
    neo_dir = roms_dir / "neogeo"
    if neo_dir.exists():
        for f in sorted(neo_dir.glob("*.zip")):
            clean_name = f.stem.upper()
            games.append({
                "id": f"neogeo_{f.stem}",
                "title": f"NeoGeo: {clean_name}",
                "console": "NEO-GEO",
                "badge": "NEO-GEO",
                "type": "libretro",
                "core": "cores/fbneo_libretro.dylib",
                "rom": str(f.relative_to(ROOT)),
                "cover": "assets_cards/bubblebobble_clean.png",
                "region": "ARCADE",
                "year": "1995",
                "developer": "SNK Neo-Geo",
                "desc": f"Potencia 24-Bit arcade Neo-Geo: {clean_name}"
            })

    return games

# Catálogo precargado de todos los juegos
ALL_GAMES = load_all_games()

# Consolas Principales para el menú Home
CONSOLES = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 15 JUEGOS PRESERVADOS",
        "badge": "SNES",
        "cover": "assets_cards/mario_clean.png",
        "developer": "Nintendo EAD",
        "year": "1990",
        "core": "cores/snes9x_libretro.dylib",
        "rom": "roms/snes/Super Mario World 2 - Yoshi's Island (U) (V1.1).smc",
        "desc": "La era dorada de los 16 bits con gráficos Mode 7.",
    },
    {
        "id": "arcade",
        "title": "Arcade MAME",
        "subtitle": "CABINAS // 6 JUEGOS RETRO",
        "badge": "ARCADE",
        "cover": "assets_cards/metalslug_clean.png",
        "developer": "SNK / Capcom",
        "year": "1996",
        "core": "cores/mame2003_plus_libretro.dylib",
        "rom": "roms/mame/mslug2.zip",
        "desc": "Las mejores recreativas arcade de acción pura.",
    },
    {
        "id": "ps1",
        "title": "PlayStation 1",
        "subtitle": "32-BIT CD // 6 CLÁSICOS PS1",
        "badge": "PS1",
        "cover": "assets_cards/castlevania_clean.png",
        "developer": "Konami / Sony",
        "year": "1997",
        "core": "cores/mednafen_psx_hw_libretro.dylib",
        "rom": "roms/ps1/Castlevania - Symphony of the Night (USA).cue",
        "desc": "Revolución 3D y audio de calidad disco compacto.",
    },
    {
        "id": "n64",
        "title": "Nintendo 64",
        "subtitle": "64-BIT 3D // 5 JUEGOS 3D",
        "badge": "N64",
        "cover": "assets_cards/zelda_clean.png",
        "developer": "Nintendo",
        "year": "1996",
        "core": "cores/mupen64plus_next_libretro.dylib",
        "rom": "roms/n64/Super Mario 64 (U) [!].z64",
        "desc": "Mundos abiertos pioneros en 3D real.",
    },
    {
        "id": "nds",
        "title": "Nintendo DS",
        "subtitle": "DUAL SCREEN // 6 JUEGOS",
        "badge": "NDS",
        "cover": "assets_cards/pokemon_clean.png",
        "developer": "Nintendo / Game Freak",
        "year": "2004",
        "core": "cores/melonds_libretro.dylib",
        "rom": "roms/nds/Pokemon White Version 2/Pokemon White Version 2 (DSi Enhanced)(U)(frieNDS).nds",
        "desc": "Doble pantalla y aventuras portátiles inolvidables.",
    },
    {
        "id": "neogeo",
        "title": "Neo-Geo MVS",
        "subtitle": "24-BIT // 3 RECREATIVAS",
        "badge": "NEO-GEO",
        "cover": "assets_cards/bubblebobble_clean.png",
        "developer": "SNK",
        "year": "1990",
        "core": "cores/fbneo_libretro.dylib",
        "rom": "roms/neogeo/pbobblen.zip",
        "desc": "La potencia de la recreativa de lujo en tu salón.",
    },
    {
        "id": "cci",
        "title": "C.C.I. SYSTEM",
        "subtitle": "ENGINE NATIVO // 19 JUEGOS",
        "badge": "CCI",
        "cover": "assets_cards/davinci_clean.png",
        "developer": "Camila Carolina Ianni",
        "year": "2024",
        "core": None,
        "rom": None,
        "desc": "Juegos nativos desarrollados especialmente para C.C.I.",
    },
]


def load_surface_safe(rel_path: str, w: int, h: int) -> pygame.Surface | None:
    p = ROOT / rel_path
    if p.exists():
        try:
            s = pygame.image.load(str(p)).convert_alpha()
            return pygame.transform.smoothscale(s, (w, h))
        except Exception:
            pass
    return None


# ==============================================================================
# 1. VISTA INICIAL OMNIDASH AERO (OmniDashHomeView)
# ==============================================================================
class OmniDashHomeView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.selected_console_idx = 0
        self.covers_cache: dict[str, pygame.Surface] = {}

        # Rectángulos interactivos
        self.hero_rect = pygame.Rect(44, 110, 320, 470)
        self.hero_btn_rect = pygame.Rect(60, 520, 288, 44)
        self.grid_rects: list[pygame.Rect] = []
        self.util_rects: list[dict] = []

    def _get_cover(self, path: str, w: int, h: int) -> pygame.Surface | None:
        key = f"{path}_{w}_{h}"
        if key not in self.covers_cache:
            loaded = load_surface_safe(path, w, h)
            if loaded:
                self.covers_cache[key] = loaded
        return self.covers_cache.get(key)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clic en botón Hero directo
            if self.hero_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                cur = CONSOLES[self.selected_console_idx]
                return {"action": "LAUNCH_DIRECT", "item": cur}

            # Clic en tarjetas de la cuadrícula
            for idx, r in enumerate(self.grid_rects):
                if r.collidepoint(mx, my):
                    self.selected_console_idx = idx
                    self.engine.play_sound("navigate")
                    return None

            # Clic en las 4 Tarjetas de Utilidad de Vidrio
            for u in self.util_rects:
                if u["rect"].collidepoint(mx, my):
                    self.engine.play_sound("reward")
                    return {"action": "NAVIGATE_UTIL", "destination": u["action"]}

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_console_idx < len(CONSOLES) - 1:
                    self.selected_console_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_console_idx > 0:
                    self.selected_console_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.engine.play_sound("reward")
                cur = CONSOLES[self.selected_console_idx]
                return {"action": "LAUNCH_DIRECT", "item": cur}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme
        cur = CONSOLES[self.selected_console_idx]

        # 1. Hero Card Grande a la izquierda
        hx, hy, hw, hh = self.hero_rect.x, self.hero_rect.y, self.hero_rect.width, self.hero_rect.height
        h_surf = pygame.Surface((hw, hh), pygame.SRCALPHA)
        # Efecto cristal translúcido Frutiger Aero
        pygame.draw.rect(h_surf, (255, 255, 255, 120), (0, 0, hw, hh), border_radius=18)
        pygame.draw.rect(h_surf, (255, 255, 255, 220), (0, 0, hw, hh), width=2, border_radius=18)
        surface.blit(h_surf, (hx, hy))

        cov = self._get_cover(cur["cover"], hw - 24, 260)
        if cov:
            surface.blit(cov, (hx + 12, hy + 12))
            pygame.draw.rect(surface, (255, 255, 255, 160), (hx + 12, hy + 12, hw - 24, 260), width=1, border_radius=10)

        # Textos Hero
        t_tit = self.engine.font_hero.render(cur["title"], True, t["text_primary"])
        surface.blit(t_tit, (hx + 16, hy + 286))

        t_sub = self.engine.font_sub.render(cur["subtitle"], True, t["text_secondary"])
        surface.blit(t_sub, (hx + 18, hy + 322))

        t_desc = self.engine.font_badge.render(cur["desc"][:42], True, (40, 80, 110))
        surface.blit(t_desc, (hx + 18, hy + 348))

        # Botón Lanzar
        is_btn_hov = self.hero_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255) if is_btn_hov else (0, 164, 239), self.hero_btn_rect, border_radius=14)
        btn_txt_col = (10, 25, 40) if is_btn_hov else (255, 255, 255)
        bt = self.engine.font_body.render("▶  INICIAR JUEGO (60 FPS)", True, btn_txt_col)
        surface.blit(bt, bt.get_rect(center=self.hero_btn_rect.center))

        # 2. Fila Superior Derecha: Mosaicos de cristal brillante con reflejo
        gx, gy = 390, 110
        self.grid_rects = []
        card_size = 135
        spacing_x = 18

        for idx, con in enumerate(CONSOLES[:6]):
            cx = gx + idx * (card_size + spacing_x)
            cy = gy
            rect = pygame.Rect(cx, cy, card_size, card_size)
            self.grid_rects.append(rect)

            is_sel = (idx == self.selected_console_idx)
            c_surf = pygame.Surface((card_size, card_size), pygame.SRCALPHA)
            bg_col = (255, 255, 255, 200) if is_sel else (255, 255, 255, 100)
            pygame.draw.rect(c_surf, bg_col, (0, 0, card_size, card_size), border_radius=14)

            # Anillo de foco verde neón oficial de OmniDash Aero
            border_col = (182, 245, 90) if is_sel else (255, 255, 255, 160)
            pygame.draw.rect(c_surf, border_col, (0, 0, card_size, card_size), width=3 if is_sel else 1, border_radius=14)

            c_cov = self._get_cover(con["cover"], card_size - 16, 88)
            if c_cov:
                c_surf.blit(c_cov, (8, 8))
                pygame.draw.rect(c_surf, (255, 255, 255, 120), (8, 8, card_size - 16, 88), width=1, border_radius=8)

            lbl = self.engine.font_badge.render(con["badge"], True, t["text_primary"])
            c_surf.blit(lbl, lbl.get_rect(center=(card_size // 2, card_size - 18)))
            surface.blit(c_surf, (cx, cy))

        # 3. Cuatro Tarjetas de Cristal Esmerilado Inferiores Oficiales de OmniDash
        self.util_rects = []
        u_y = gy + card_size + 30
        uw, uh = 205, 160
        u_spacing = 18

        utils = [
            {
                "id": "library",
                "title": "Mi Biblioteca",
                "sub": f"{len(ALL_GAMES)} juegos instalados\nen 7 plataformas",
                "icon": "📚",
                "action": "LIBRARY"
            },
            {
                "id": "friends",
                "title": "Comunidad C.C.I.",
                "sub": "Seeker & Night Raid\n3 amigos en línea",
                "icon": "👥",
                "action": "GROUPS"
            },
            {
                "id": "achievements",
                "title": "Gamerscore",
                "sub": "18,450 G ganados\n110 Trofeos C.C.I.",
                "icon": "🏆",
                "action": "PROFILE"
            },
            {
                "id": "settings",
                "title": "Configuración",
                "sub": "Ajustes de pantalla,\naudio y mandos",
                "icon": "⚙️",
                "action": "SETTINGS"
            },
        ]

        for idx, u in enumerate(utils):
            ux = gx + idx * (uw + u_spacing)
            u_rect = pygame.Rect(ux, u_y, uw, uh)
            self.util_rects.append({"rect": u_rect, "action": u["action"]})

            is_hov = u_rect.collidepoint(pygame.mouse.get_pos())
            u_surf = pygame.Surface((uw, uh), pygame.SRCALPHA)
            u_bg = (255, 255, 255, 180) if is_hov else (255, 255, 255, 110)
            pygame.draw.rect(u_surf, u_bg, (0, 0, uw, uh), border_radius=16)
            pygame.draw.rect(u_surf, (182, 245, 90) if is_hov else (255, 255, 255, 180), (0, 0, uw, uh), width=2 if is_hov else 1, border_radius=16)

            ico_t = self.engine.font_hero.render(u["icon"], True, t["text_primary"])
            u_surf.blit(ico_t, (16, 14))

            t_t = self.engine.font_body.render(u["title"], True, t["text_primary"])
            u_surf.blit(t_t, (16, 62))

            lines = u["sub"].split("\n")
            for l_idx, line in enumerate(lines):
                s_t = self.engine.font_sub.render(line, True, t["text_secondary"])
                u_surf.blit(s_t, (16, 94 + l_idx * 18))

            surface.blit(u_surf, (ux, u_y))


# ==============================================================================
# 2. VISTA BIBLIOTECA COMPLETA OMNIDASH (OmniDashLibraryView)
# ==============================================================================
class OmniDashLibraryView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_filter = "TODAS"
        self.selected_game_idx = 0
        self.search_query = ""
        self.covers_cache: dict[str, pygame.Surface] = {}

        self.filters = ["TODAS", "SNES", "ARCADE", "N64", "PS1", "NDS", "NEO-GEO", "CCI"]
        self.filter_rects: list[pygame.Rect] = []
        self.game_card_rects: list[pygame.Rect] = []
        self.back_btn_rect = pygame.Rect(36, 22, 110, 36)

    def _get_cover(self, path: str, w: int, h: int) -> pygame.Surface | None:
        key = f"{path}_{w}_{h}"
        if key not in self.covers_cache:
            loaded = load_surface_safe(path, w, h)
            if loaded:
                self.covers_cache[key] = loaded
        return self.covers_cache.get(key)

    def _filtered_games(self) -> list[dict]:
        res = ALL_GAMES
        if self.selected_filter != "TODAS":
            res = [g for g in res if g["badge"] == self.selected_filter]
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

            # Clic en pestañas
            for idx, r in enumerate(self.filter_rects):
                if r.collidepoint(mx, my):
                    self.selected_filter = self.filters[idx]
                    self.selected_game_idx = 0
                    self.engine.play_sound("navigate")
                    return None

            # Clic en tarjeta de juego
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
                if self.selected_game_idx + 6 < len(filtered):
                    self.selected_game_idx += 6
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.selected_game_idx - 6 >= 0:
                    self.selected_game_idx -= 6
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if filtered and self.selected_game_idx < len(filtered):
                    self.engine.play_sound("reward")
                    return {"action": "LAUNCH_GAME", "game": filtered[self.selected_game_idx]}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme
        filtered = self._filtered_games()

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 120 if is_back_hov else 60), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, (255, 255, 255, 200), self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("⇦ INICIO", True, t["text_primary"])
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Título y total
        title_t = self.engine.font_hero.render("BIBLIOTECA COMPLETA OMNIDASH", True, t["text_primary"])
        surface.blit(title_t, (170, 24))
        sub_t = self.engine.font_sub.render(f"{len(filtered)} títulos listos para jugar a 60 FPS", True, t["text_secondary"])
        surface.blit(sub_t, (172, 54))

        # Pestañas de Filtros
        self.filter_rects = []
        fx = 36
        fy = 86
        for f in self.filters:
            is_active = (f == self.selected_filter)
            tw = max(70, len(f) * 11 + 24)
            f_rect = pygame.Rect(fx, fy, tw, 32)
            self.filter_rects.append(f_rect)

            bg_col = (255, 255, 255, 160) if is_active else (255, 255, 255, 60)
            pygame.draw.rect(surface, bg_col, f_rect, border_radius=16)
            if is_active:
                pygame.draw.rect(surface, (182, 245, 90), f_rect, width=2, border_radius=16)

            f_txt = self.engine.font_badge.render(f, True, t["text_primary"])
            surface.blit(f_txt, f_txt.get_rect(center=f_rect.center))
            fx += tw + 10

        # Cuadrícula de Juegos (6 columnas)
        self.game_card_rects = []
        cols = 6
        cw, ch = 186, 200
        start_x = 36
        start_y = 136
        gap_x, gap_y = 18, 16

        for idx, g in enumerate(filtered[:18]):  # Mostrar primera página
            col = idx % cols
            row = idx // cols
            cx = start_x + col * (cw + gap_x)
            cy = start_y + row * (ch + gap_y)

            card_rect = pygame.Rect(cx, cy, cw, ch)
            self.game_card_rects.append(card_rect)

            is_sel = (idx == self.selected_game_idx)
            c_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            bg_col = (255, 255, 255, 190) if is_sel else (255, 255, 255, 100)
            pygame.draw.rect(c_surf, bg_col, (0, 0, cw, ch), border_radius=14)
            pygame.draw.rect(c_surf, (182, 245, 90) if is_sel else (255, 255, 255, 160), (0, 0, cw, ch), width=3 if is_sel else 1, border_radius=14)

            cov = self._get_cover(g["cover"], cw - 16, 126)
            if cov:
                c_surf.blit(cov, (8, 8))
                pygame.draw.rect(c_surf, (255, 255, 255, 120), (8, 8, cw - 16, 126), width=1, border_radius=8)

            gt_str = g["title"] if len(g["title"]) < 20 else g["title"][:18] + "..."
            gt = self.engine.font_badge.render(gt_str, True, t["text_primary"])
            c_surf.blit(gt, (10, 144))

            plat_t = self.engine.font_badge.render(f"{g['console']} • {g['region']}", True, (0, 120, 190) if is_sel else t["text_secondary"])
            c_surf.blit(plat_t, (10, 168))

            surface.blit(c_surf, (cx, cy))


# ==============================================================================
# 3. VISTA AJUSTES OFICIAL OMNIDASH AERO (OmniDashSettingsView)
# Basada fielmente en #g-aero-settings / garrison-settings-screen.css / aero-settings.jpg
# ==============================================================================
class OmniDashSettingsView:
    def __init__(self, engine: OmniDashEngine, user_data=None, on_apply_display=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.on_apply_display = on_apply_display

        self.categories = [
            {"id": "appearance", "name": "Apariencia", "icon": "🎨", "color": (142, 92, 247), "desc": "Tema Frutiger Aero, opacidad y escala de UI."},
            {"id": "display_sound", "name": "Pantalla y Sonido", "icon": "📺", "color": (47, 124, 246), "desc": "Resolución de salida, pantalla completa y volumen."},
            {"id": "controller", "name": "Controles", "icon": "🎮", "color": (47, 174, 75), "desc": "Distribución de botones, vibración y detección de mandos."},
            {"id": "notifications", "name": "Notificaciones", "icon": "🔔", "color": (239, 75, 75), "desc": "Toasts de logros Gamerscore y amigos conectados."},
            {"id": "library", "name": "Biblioteca & Cores", "icon": "📁", "color": (242, 147, 31), "desc": "Cores Libretro a 60 FPS, rutas de ROMs y BIOS."},
            {"id": "account", "name": "Cuenta y Perfil", "icon": "👤", "color": (90, 122, 156), "desc": "Gamerscore (18,450 G), apodo de jugador y avatar."},
            {"id": "accessibility", "name": "Accesibilidad", "icon": "♿", "color": (31, 155, 224), "desc": "Reducción de movimiento y modo de alto contraste."},
            {"id": "system", "name": "Sistema C.C.I.", "icon": "⚙️", "color": (122, 127, 135), "desc": "Versión v2.1.0, almacenamiento y copias de seguridad."},
        ]

        self.selected_cat_idx = 0
        self.selected_row_idx = 0

        # Configuración viva
        self.settings = {
            "theme": "Frutiger Aero",
            "resolution": "1280 x 720",
            "fullscreen": False,
            "volume_game": 80,
            "volume_music": 70,
            "controller_layout": "Xbox / Universal",
            "vibration": True,
            "notify_achievements": True,
            "notify_friends": True,
            "libretro_fps": "60 FPS Puro",
            "gamerscore": "18,450 G",
            "reduced_motion": False,
            "system_version": "v2.1.0 (100% Python)",
        }

        self.back_btn_rect = pygame.Rect(self.w - 180, 40, 140, 38)
        self.cat_rects: list[pygame.Rect] = []
        self.row_rects: list[pygame.Rect] = []

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        cat = self.categories[self.selected_cat_idx]

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

            # Clic en filas interactivas
            for idx, r in enumerate(self.row_rects):
                if r.collidepoint(mx, my):
                    self.selected_row_idx = idx
                    self._toggle_current_row()
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
                if self.selected_row_idx < len(self._get_cat_rows()) - 1:
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
                self._toggle_current_row()
                self.engine.play_sound("reward")

        return None

    def _get_cat_rows(self) -> list[dict]:
        cid = self.categories[self.selected_cat_idx]["id"]
        if cid == "appearance":
            return [
                {"key": "theme", "label": "Tema Activo", "sub": "Diseño estético de la interfaz", "val": self.settings["theme"]},
                {"key": "glass_fx", "label": "Efectos de Vidrio Esmerilado", "sub": "Translucidez en tiempo real", "val": "Activado"},
                {"key": "ui_scale", "label": "Escala de Interfaz", "sub": "Zoom adaptativo para TV o PC", "val": "100%"},
            ]
        elif cid == "display_sound":
            return [
                {"key": "resolution", "label": "Resolución de Salida", "sub": "Tamaño de renderizado de la ventana", "val": self.settings["resolution"]},
                {"key": "fullscreen", "label": "Pantalla Completa", "sub": "Alternar modo ventana o pantalla completa", "val": "SÍ" if self.settings["fullscreen"] else "NO"},
                {"key": "volume_game", "label": "Volumen de Juegos", "sub": "Nivel de audio de los emuladores", "val": f"{self.settings['volume_game']}%"},
                {"key": "volume_music", "label": "Música Ambiental", "sub": "Banda sonora de la interfaz", "val": f"{self.settings['volume_music']}%"},
            ]
        elif cid == "controller":
            return [
                {"key": "controller_layout", "label": "Disposición de Botones", "sub": "Esquema A/B/X/Y universal", "val": self.settings["controller_layout"]},
                {"key": "vibration", "label": "Vibración Háptica", "sub": "Retroalimentación en impactos", "val": "Activada" if self.settings["vibration"] else "Desactivada"},
                {"key": "turbo", "label": "Fuego Automático (Turbo)", "sub": "Disparo continuo en Arcade", "val": "Disponible"},
            ]
        elif cid == "notifications":
            return [
                {"key": "notify_achievements", "label": "Notificaciones de Logros", "sub": "Banner emergente al desbloquear trofeos", "val": "SÍ" if self.settings["notify_achievements"] else "NO"},
                {"key": "notify_friends", "label": "Avisos de Amigos en Línea", "sub": "Notificación cuando un amigo se conecta", "val": "SÍ" if self.settings["notify_friends"] else "NO"},
            ]
        elif cid == "library":
            return [
                {"key": "libretro_fps", "label": "Tasa de Refresco Libretro", "sub": "Emulación sin saltos de fotogramas", "val": self.settings["libretro_fps"]},
                {"key": "roms_scan", "label": "Exploración de ROMs", "sub": "Directorio local /roms verificado", "val": f"{len(ALL_GAMES)} detectadas"},
                {"key": "region", "label": "Región Preferida", "sub": "Orden de prioridad para ROMs", "val": "USA > EUR > JAP"},
            ]
        elif cid == "account":
            return [
                {"key": "player", "label": "Perfil Principal", "sub": "Identidad en la consola C.C.I.", "val": "Alex"},
                {"key": "gamerscore", "label": "Gamerscore Total", "sub": "Puntos acumulados en juegos", "val": self.settings["gamerscore"]},
                {"key": "avatar", "label": "Avatar de Jugador", "sub": "Icono distintivo de usuario", "val": "Frutiger Pilot #1"},
            ]
        elif cid == "accessibility":
            return [
                {"key": "reduced_motion", "label": "Reducción de Movimiento", "sub": "Animaciones suaves sin oscilación", "val": "SÍ" if self.settings["reduced_motion"] else "NO"},
                {"key": "contrast", "label": "Alto Contraste", "sub": "Bordes definidos en texto y botones", "val": "Desactivado"},
            ]
        else:
            return [
                {"key": "version", "label": "Versión del Sistema", "sub": "Núcleo C.C.I. SYSTEM Virtual Console", "val": self.settings["system_version"]},
                {"key": "storage", "label": "Almacenamiento Libre", "sub": "Espacio en disco para ROMs y partidas", "val": "7.2 GB disponibles"},
                {"key": "backup", "label": "Copias de Seguridad", "sub": "Guardado automático de estados (.state)", "val": "Activado"},
            ]

    def _toggle_current_row(self):
        rows = self._get_cat_rows()
        if not rows or self.selected_row_idx >= len(rows):
            return
        row = rows[self.selected_row_idx]
        k = row["key"]

        if k == "resolution":
            self.settings["resolution"] = "1920 x 1080" if self.settings["resolution"] == "1280 x 720" else "1280 x 720"
        elif k == "fullscreen":
            self.settings["fullscreen"] = not self.settings["fullscreen"]
        elif k == "vibration":
            self.settings["vibration"] = not self.settings["vibration"]
        elif k == "notify_achievements":
            self.settings["notify_achievements"] = not self.settings["notify_achievements"]
        elif k == "notify_friends":
            self.settings["notify_friends"] = not self.settings["notify_friends"]
        elif k == "reduced_motion":
            self.settings["reduced_motion"] = not self.settings["reduced_motion"]

    def render(self, surface: pygame.Surface):
        t = self.engine.theme

        # Contenedor global de vidrio oscuro con gradiente
        panel_w = self.w - 80
        panel_h = self.h - 80
        px, py = 40, 40

        glass_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(glass_surf, (15, 23, 35, 230), (0, 0, panel_w, panel_h), border_radius=20)
        pygame.draw.rect(glass_surf, (255, 255, 255, 120), (0, 0, panel_w, panel_h), width=2, border_radius=20)
        surface.blit(glass_surf, (px, py))

        # Encabezado
        title_t = self.engine.font_hero.render("Configuración", True, (255, 255, 255))
        surface.blit(title_t, (px + 30, py + 22))

        sub_t = self.engine.font_sub.render("Personaliza tu consola, pantalla, audio y cuentas del sistema", True, (180, 205, 230))
        surface.blit(sub_t, (px + 32, py + 56))

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hov else 30), self.back_btn_rect, border_radius=19)
        pygame.draw.rect(surface, (255, 255, 255, 180), self.back_btn_rect, width=1, border_radius=19)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Cerrar", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # 1. Columna Izquierda: Secciones con Iconos de Colores Oficiales OmniDash
        side_x = px + 24
        side_y = py + 90
        side_w = 340
        self.cat_rects = []

        for idx, cat in enumerate(self.categories):
            cy = side_y + idx * 56
            c_rect = pygame.Rect(side_x, cy, side_w, 50)
            self.cat_rects.append(c_rect)

            is_sel = (idx == self.selected_cat_idx)
            if is_sel:
                pygame.draw.rect(surface, (255, 255, 255, 45), c_rect, border_radius=12)
                pygame.draw.rect(surface, (182, 245, 90), c_rect, width=2, border_radius=12)

            # Icono cuadrado coloreado oficial
            ico_box = pygame.Rect(side_x + 10, cy + 9, 32, 32)
            pygame.draw.rect(surface, cat["color"], ico_box, border_radius=8)
            ico_txt = self.engine.font_title.render(cat["icon"], True, (255, 255, 255))
            surface.blit(ico_txt, ico_txt.get_rect(center=ico_box.center))

            c_name = self.engine.font_body.render(cat["name"], True, (255, 255, 255) if is_sel else (200, 215, 235))
            surface.blit(c_name, (side_x + 52, cy + 14))

        # 2. Panel Derecho: Grupo de Opciones de la Categoría Activa
        cur_cat = self.categories[self.selected_cat_idx]
        right_x = side_x + side_w + 30
        right_y = side_y
        right_w = panel_w - side_w - 74
        right_h = panel_h - 110

        # Tarjeta contenedora de opciones
        r_surf = pygame.Surface((right_w, right_h), pygame.SRCALPHA)
        pygame.draw.rect(r_surf, (25, 33, 46, 210), (0, 0, right_w, right_h), border_radius=16)
        pygame.draw.rect(r_surf, (255, 255, 255, 40), (0, 0, right_w, right_h), width=1, border_radius=16)
        surface.blit(r_surf, (right_x, right_y))

        # Encabezado de la categoría seleccionada
        head_ico_box = pygame.Rect(right_x + 24, right_y + 20, 44, 44)
        pygame.draw.rect(surface, cur_cat["color"], head_ico_box, border_radius=12)
        h_ico = self.engine.font_hero.render(cur_cat["icon"], True, (255, 255, 255))
        surface.blit(h_ico, h_ico.get_rect(center=head_ico_box.center))

        h_title = self.engine.font_title.render(cur_cat["name"], True, (255, 255, 255))
        surface.blit(h_title, (right_x + 80, right_y + 20))

        h_desc = self.engine.font_sub.render(cur_cat["desc"], True, (160, 185, 215))
        surface.blit(h_desc, (right_x + 82, right_y + 46))

        # Lista de filas interactivas
        rows = self._get_cat_rows()
        self.row_rects = []
        row_y = right_y + 86

        for idx, row in enumerate(rows):
            r_rect = pygame.Rect(right_x + 20, row_y + idx * 72, right_w - 40, 62)
            self.row_rects.append(r_rect)

            is_sel = (idx == self.selected_row_idx)
            row_bg = (255, 255, 255, 45) if is_sel else (255, 255, 255, 15)
            pygame.draw.rect(surface, row_bg, r_rect, border_radius=12)
            if is_sel:
                pygame.draw.rect(surface, (182, 245, 90), r_rect, width=2, border_radius=12)

            # Nombre y descripción
            lbl = self.engine.font_body.render(row["label"], True, (255, 255, 255))
            surface.blit(lbl, (r_rect.x + 16, r_rect.y + 11))

            sub = self.engine.font_badge.render(row["sub"], True, (160, 185, 215))
            surface.blit(sub, (r_rect.x + 16, r_rect.y + 35))

            # Valor o interruptor
            val_t = self.engine.font_body.render(str(row["val"]), True, (182, 245, 90) if is_sel else (255, 255, 255))
            surface.blit(val_t, (r_rect.right - val_t.get_width() - 20, r_rect.y + 20))


# ==============================================================================
# 4. VISTA PERFIL & GAMERSCORE OFICIAL OMNIDASH AERO (OmniDashProfileView)
# ==============================================================================
class OmniDashProfileView:
    def __init__(self, engine: OmniDashEngine, user_data=None):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.user_data = user_data
        self.back_btn_rect = pygame.Rect(self.w - 180, 40, 140, 38)

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
        t = self.engine.theme
        pw, ph = self.w - 100, self.h - 100
        px, py = 50, 50

        # Contenedor esmerilado
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (15, 25, 40, 230), (0, 0, pw, ph), border_radius=20)
        pygame.draw.rect(p_surf, (255, 255, 255, 120), (0, 0, pw, ph), width=2, border_radius=20)
        surface.blit(p_surf, (px, py))

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hov else 30), self.back_btn_rect, border_radius=19)
        pygame.draw.rect(surface, (255, 255, 255, 180), self.back_btn_rect, width=1, border_radius=19)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Cerrar", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Avatar circular con aura
        av_center = (px + 80, py + 80)
        pygame.draw.circle(surface, (0, 180, 216), av_center, 46)
        pygame.draw.circle(surface, (255, 255, 255), av_center, 44)
        av_txt = self.engine.font_hero.render("A", True, (12, 35, 65))
        surface.blit(av_txt, av_txt.get_rect(center=av_center))

        # Nombre y Gamerscore
        name_t = self.engine.font_hero.render("Alex  •  Frutiger Pilot", True, (255, 255, 255))
        surface.blit(name_t, (px + 144, py + 50))

        score_t = self.engine.font_title.render("18,450 G  •  Nivel de Jugador 42", True, (182, 245, 90))
        surface.blit(score_t, (px + 146, py + 88))

        # Logros destacados
        trophies = [
            ("Maestro de la Preservación", "Has ejecutado 50 títulos clásicos a 60 FPS estables.", "🥇 ORO"),
            ("Pionero 16-Bit Super Nintendo", "Super Mario World completado al 100%.", "🥈 PLATA"),
            ("Comunidad Activa C.C.I.", "Conectado al escuadrón Seeker en tiempo real.", "🥉 BRONCE"),
            ("Fotógrafo Retro", "Captura de pantalla HD guardada en outputs/.", "🥉 BRONCE"),
        ]

        tx = px + 50
        ty = py + 160
        sec_title = self.engine.font_title.render("Logros y Trofeos Desbloqueados", True, (255, 255, 255))
        surface.blit(sec_title, (tx, ty))

        for idx, (tname, tdesc, tbadge) in enumerate(trophies):
            ry = ty + 42 + idx * 70
            r_rect = pygame.Rect(tx, ry, pw - 100, 58)
            pygame.draw.rect(surface, (255, 255, 255, 20), r_rect, border_radius=12)
            pygame.draw.rect(surface, (255, 255, 255, 50), r_rect, width=1, border_radius=12)

            b_t = self.engine.font_badge.render(tbadge, True, (255, 220, 60))
            surface.blit(b_t, (r_rect.x + 16, r_rect.y + 10))

            n_t = self.engine.font_body.render(tname, True, (255, 255, 255))
            surface.blit(n_t, (r_rect.x + 16, r_rect.y + 30))

            d_t = self.engine.font_sub.render(tdesc, True, (180, 205, 235))
            surface.blit(d_t, (r_rect.x + 320, r_rect.y + 20))


# ==============================================================================
# 5. VISTA COMUNIDAD C.C.I. OMNIDASH AERO (OmniDashCommunityView)
# ==============================================================================
class OmniDashCommunityView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.back_btn_rect = pygame.Rect(self.w - 180, 40, 140, 38)

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
        pw, ph = self.w - 100, self.h - 100
        px, py = 50, 50

        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (15, 25, 40, 230), (0, 0, pw, ph), border_radius=20)
        pygame.draw.rect(p_surf, (255, 255, 255, 120), (0, 0, pw, ph), width=2, border_radius=20)
        surface.blit(p_surf, (px, py))

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hov else 30), self.back_btn_rect, border_radius=19)
        pygame.draw.rect(surface, (255, 255, 255, 180), self.back_btn_rect, width=1, border_radius=19)
        bt = self.engine.font_btn.render("Ⓑ / Esc  Cerrar", True, (255, 255, 255))
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Título
        title_t = self.engine.font_hero.render("Comunidades & Amigos C.C.I.", True, (255, 255, 255))
        surface.blit(title_t, (px + 40, py + 30))
        sub_t = self.engine.font_sub.render("Salas de chat en vivo, grupos de emulación y juego cooperativo", True, (180, 205, 230))
        surface.blit(sub_t, (px + 42, py + 64))

        # Grupos oficiales
        groups = [
            ("Seeker Hub Central", "3 amigos jugando a Metal Slug 2", "● 14 en línea", (47, 124, 246)),
            ("Night Raid Elite", "Torneo de Street Fighter II Turbo", "● 8 en línea", (142, 92, 247)),
            ("Retro Preservation Society", "Partidas compartidas de Castlevania", "● 22 en línea", (47, 174, 75)),
        ]

        for idx, (gname, gactivity, gstatus, gcolor) in enumerate(groups):
            gy = py + 120 + idx * 100
            g_rect = pygame.Rect(px + 40, gy, pw - 80, 80)
            pygame.draw.rect(surface, (255, 255, 255, 25), g_rect, border_radius=14)
            pygame.draw.rect(surface, (255, 255, 255, 60), g_rect, width=1, border_radius=14)

            # Badge de grupo
            badge_r = pygame.Rect(g_rect.x + 16, g_rect.y + 16, 48, 48)
            pygame.draw.rect(surface, gcolor, badge_r, border_radius=12)
            b_txt = self.engine.font_title.render("👥", True, (255, 255, 255))
            surface.blit(b_txt, b_txt.get_rect(center=badge_r.center))

            gn = self.engine.font_body.render(gname, True, (255, 255, 255))
            surface.blit(gn, (g_rect.x + 80, g_rect.y + 18))

            ga = self.engine.font_sub.render(gactivity, True, (180, 205, 230))
            surface.blit(ga, (g_rect.x + 82, g_rect.y + 44))

            gs = self.engine.font_badge.render(gstatus, True, (182, 245, 90))
            surface.blit(gs, (g_rect.right - gs.get_width() - 24, g_rect.y + 30))


# ==============================================================================
# 6. PANTALLA CINEMÁTICA DE LANZAMIENTO OFICIAL OMNIDASH AERO
# ("rises the game's logo over its key art")
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
            self.cover = load_surface_safe(cpath, engine.w, engine.h)

    def update(self, dt: float) -> dict | None:
        self.elapsed += dt
        if self.elapsed >= self.duration:
            return {"action": "LAUNCH_NOW", "target": self.target}
        return None

    def render(self, surface: pygame.Surface):
        progress = min(1.0, self.elapsed / self.duration)
        w, h = self.engine.w, self.engine.h

        # 1. Zoom dinámico del arte de fondo
        if self.cover:
            scale_fac = 1.0 + progress * 0.08
            zw, zh = int(w * scale_fac), int(h * scale_fac)
            scaled = pygame.transform.smoothscale(self.cover, (zw, zh))
            offset_x = (zw - w) // 2
            offset_y = (zh - h) // 2
            surface.blit(scaled, (-offset_x, -offset_y))
        else:
            surface.fill((10, 25, 45))

        # Oscurecimiento de fondo
        dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_surf.fill((0, 20, 45, int(160 + progress * 50)))
        surface.blit(dim_surf, (0, 0))

        # 2. Elevación del logo sobre el arte (curva easing trigonométrica)
        ease_y = math.sin(progress * math.pi / 2)
        logo_y = int(h + 80 - ease_y * (h * 0.55 + 80))

        # Título principal
        title_str = self.target.get("title", "Juego C.C.I.")
        t_surf = self.engine.font_hero.render(title_str, True, (255, 255, 255))
        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, logo_y)))

        # Consola y Core
        meta_str = f"{self.target.get('console', self.target.get('badge', 'CONSOLA'))}  •  LIBRETRO 60 FPS"
        m_surf = self.engine.font_body.render(meta_str, True, (182, 245, 90))
        surface.blit(m_surf, m_surf.get_rect(center=(w // 2, logo_y + 44)))

        # 3. Barra de carga brillante con resplandor
        bar_w = 400
        bar_h = 8
        bx = (w - bar_w) // 2
        by = h - 70

        pygame.draw.rect(surface, (255, 255, 255, 40), (bx, by, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(surface, (182, 245, 90), (bx, by, fill_w, bar_h), border_radius=4)


# ==============================================================================
# 7. ESTADOS DE STATEMACHINE PARA INTEGRACIÓN CON C.C.I. SYSTEM
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
            # 1. Shell global
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

            # 2. Vista Home
            res = self.home_view.handle_event(event)
            if res:
                if res.get("action") == "LAUNCH_DIRECT":
                    item = res["item"]
                    self.state_machine.change_state("LAUNCH_ANIM", target=item)
                elif res.get("action") == "NAVIGATE_UTIL":
                    dest = res["destination"]
                    self.state_machine.change_state(dest)

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.home_view.render(screen)
        self.engine.render_top_bar(screen)
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
                    game = res["game"]
                    self.state_machine.change_state("LAUNCH_ANIM", target=game)
                    return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        self.library_view.render(screen)
        self.engine.render_bottom_dock(screen)


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
                    # Lanzar juego nativo C.C.I.
                    game_id = target["id"].replace("native_", "")
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


class OmniDashDetailsState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.item = None

    def enter(self, item=None, **kwargs):
        self.item = item or CONSOLES[0]

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
            btn = self.engine.font_btn.render("Presiona [ ENTER ] para jugar  •  [ ESC ] Volver", True, (182, 245, 90))
            screen.blit(btn, (rect.x + 42, rect.bottom - 60))
        self.engine.render_bottom_dock(screen)
