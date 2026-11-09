"""omnidash_screens.py - Suite Completa de Pantallas Frutiger Aero de OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE.
Flujo Completo de Pantallas de OmniDash Aero:
1. OmniDashHomeView: Isla soleada Frutiger Aero, Hero Card grande, tarjetas de consolas y 4 tarjetas de servicio (Biblioteca, Amigos, Comunidad, Logros).
2. OmniDashLibraryView: Biblioteca completa con pestañas de consolas (Todas, SNES, Arcade, PS1, N64, NDS, Neo-Geo, Wii), buscador y cuadrícula de carátulas.
3. OmniDashGameDetailsView: Ficha técnica con carátula grande, especificaciones, lista de ROMs y botón 'JUGAR AHORA'.
4. OmniDashLaunchScreenView: Pantalla cinemática de arranque oficial ("rises the game's logo over its key art") antes del emulador.
5. OmniDashSettingsView: Panel de Ajustes de 8 categorías en cristal esmerilado.
6. OmniDashProfileView: Perfil de usuario con Gamerscore (18,450 G), trofeos y avatares.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path
import pygame

from omnidash_engine import OmniDashEngine, THEMES

ROOT = Path(__file__).resolve().parent

# Catálogo oficial de Consolas de OmniDash
CONSOLES = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 21 ROMS PRESERVADAS",
        "badge": "SNES",
        "cover": "start.png",
        "developer": "Nintendo EAD",
        "year": "1990",
        "core": "cores/snes9x_libretro.dylib",
        "desc": "La cúspide del pixel art de 16 bits. Clásicos legendarios a 60 FPS.",
        "roms": [
            {"name": "Super Mario World", "file": "Super Mario World (USA).sfc", "region": "USA"},
            {"name": "Super Metroid", "file": "Super Metroid (JU) [!].smc", "region": "USA/JPN"},
            {"name": "The Legend of Zelda: A Link to the Past", "file": "Legend of Zelda, The - A Link to the Past (USA).sfc", "region": "USA"},
            {"name": "Donkey Kong Country", "file": "Donkey Kong Country (USA) (Rev 2).sfc", "region": "USA"},
            {"name": "Street Fighter II Turbo", "file": "Street Fighter II Turbo (USA).sfc", "region": "USA"},
        ],
    },
    {
        "id": "mame",
        "title": "Arcade Classics",
        "subtitle": "COIN-OP // CAPCOM CPS & MIDWAY",
        "badge": "ARCADE",
        "cover": "battle.png",
        "developer": "Capcom / Midway / SNK",
        "year": "1993",
        "core": "cores/fbneo_libretro.dylib",
        "desc": "Las máquinas recreativas más emblemáticas de la historia.",
        "roms": [
            {"name": "Metal Slug 2", "file": "mslug2.zip", "region": "ARCADE"},
            {"name": "Marvel vs Capcom", "file": "mvsc.zip", "region": "ARCADE"},
            {"name": "Pac-Man (Midway)", "file": "pacman.zip", "region": "ARCADE"},
            {"name": "Final Fight", "file": "ffight.zip", "region": "ARCADE"},
            {"name": "Cruis'n USA", "file": "crusnusa.zip", "region": "ARCADE"},
        ],
    },
    {
        "id": "n64",
        "title": "Nintendo 64",
        "subtitle": "64-BIT 3D // MARIO 64 & ZELDA",
        "badge": "N64",
        "cover": "elden.png",
        "developer": "Nintendo",
        "year": "1996",
        "core": "cores/mupen64plus_next_libretro.dylib",
        "desc": "Revolución tridimensional con mundos abiertos y control analógico.",
        "roms": [
            {"name": "Super Mario 64", "file": "Super Mario 64 (USA).z64", "region": "USA"},
            {"name": "The Legend of Zelda: Ocarina of Time", "file": "Legend of Zelda, The - Ocarina of Time (USA).z64", "region": "USA"},
            {"name": "Super Smash Bros.", "file": "Super Smash Bros. (USA).z64", "region": "USA"},
            {"name": "Mario Kart 64", "file": "Mario Kart 64 (USA).z64", "region": "USA"},
        ],
    },
    {
        "id": "ps1",
        "title": "PlayStation",
        "subtitle": "32-BIT CD-ROM // CRASH & RESIDENT EVIL",
        "badge": "PS1",
        "cover": "ps.png",
        "developer": "Sony Computer Entertainment",
        "year": "1994",
        "core": "cores/pcsx_rearmed_libretro.dylib",
        "desc": "La era dorada del CD-ROM poligonal y bandas sonoras maestras.",
        "roms": [
            {"name": "Crash Bandicoot 3: Warped", "file": "Crash Bandicoot - Warped (USA).7z", "region": "USA"},
            {"name": "Resident Evil 3: Nemesis", "file": "Resident Evil 3 - Nemesis (E) [SLES-02529].7z", "region": "EUR"},
            {"name": "Castlevania: Symphony of the Night", "file": "Castlevania - Symphony of the Night (USA).7z", "region": "USA"},
            {"name": "Metal Slug X", "file": "Metal Slug X (USA).7z", "region": "USA"},
        ],
    },
    {
        "id": "neogeo",
        "title": "SNK Neo-Geo",
        "subtitle": "24-BIT // 330 MEGA PRO-GEAR",
        "badge": "NEO-GEO",
        "cover": "red.png",
        "developer": "SNK Corporation",
        "year": "1990",
        "core": "cores/fbneo_libretro.dylib",
        "desc": "Potencia arcade colosal de 330 Megabits en tu pantalla.",
        "roms": [
            {"name": "The King of Fighters 2002", "file": "kof2002.zip", "region": "ARCADE"},
            {"name": "Metal Slug X (MVS)", "file": "mslugx.zip", "region": "ARCADE"},
            {"name": "Samurai Shodown II", "file": "samsho2.zip", "region": "ARCADE"},
        ],
    },
    {
        "id": "nds",
        "title": "Nintendo DS",
        "subtitle": "DUAL SCREEN // POKÉMON WHITE 2",
        "badge": "NDS",
        "cover": "destiny.png",
        "developer": "Nintendo",
        "year": "2004",
        "core": "cores/melonds_libretro.dylib",
        "desc": "Doble pantalla y aventuras portátiles inolvidables.",
        "roms": [
            {"name": "Pokémon White Version 2", "file": "Pokemon White Version 2.nds", "region": "USA"},
            {"name": "Mario Kart DS", "file": "0168 - Mario Kart DS (U)(SCZ).nds", "region": "USA"},
            {"name": "Animal Crossing: Wild World", "file": "0389 - Animal Crossing - Wild World (E)(Legacy).nds", "region": "EUR"},
        ],
    },
    {
        "id": "wii",
        "title": "Nintendo Wii",
        "subtitle": "MOTION CONTROL // WII SPORTS",
        "badge": "WII",
        "cover": "detroit.png",
        "developer": "Nintendo",
        "year": "2006",
        "core": "cores/dolphin_libretro.dylib",
        "desc": "Innovación y diversión por movimiento a 60 FPS.",
        "roms": [
            {"name": "Wii Sports", "file": "Wii Sports (USA).wbfs", "region": "USA"},
            {"name": "Super Mario Galaxy", "file": "Super Mario Galaxy (USA).wbfs", "region": "USA"},
        ],
    },
]

# Catálogo Completo de Juegos Individuales para la Biblioteca OmniDash
ALL_GAMES = [
    # SNES
    {"id": "smw", "title": "Super Mario World", "console": "SNES", "core": "cores/snes9x_libretro.dylib", "rom": "roms/snes/Super Mario World (USA).sfc", "cover": "start.png", "region": "USA", "year": "1990"},
    {"id": "smetroid", "title": "Super Metroid", "console": "SNES", "core": "cores/snes9x_libretro.dylib", "rom": "roms/snes/Super Metroid (JU) [!].smc", "cover": "start.png", "region": "USA", "year": "1994"},
    {"id": "zelda_alttp", "title": "Zelda: A Link to the Past", "console": "SNES", "core": "cores/snes9x_libretro.dylib", "rom": "roms/snes/Legend of Zelda, The - A Link to the Past (USA).sfc", "cover": "start.png", "region": "USA", "year": "1991"},
    {"id": "dkc", "title": "Donkey Kong Country", "console": "SNES", "core": "cores/snes9x_libretro.dylib", "rom": "roms/snes/Donkey Kong Country (USA) (Rev 2).sfc", "cover": "start.png", "region": "USA", "year": "1994"},
    {"id": "sf2t", "title": "Street Fighter II Turbo", "console": "SNES", "core": "cores/snes9x_libretro.dylib", "rom": "roms/snes/Street Fighter II Turbo (USA).sfc", "cover": "start.png", "region": "USA", "year": "1993"},
    # Arcade
    {"id": "mslug2", "title": "Metal Slug 2", "console": "ARCADE", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/mslug2.zip", "cover": "battle.png", "region": "ARCADE", "year": "1998"},
    {"id": "mvsc", "title": "Marvel vs. Capcom", "console": "ARCADE", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/mvsc.zip", "cover": "battle.png", "region": "ARCADE", "year": "1998"},
    {"id": "pacman", "title": "Pac-Man Classic", "console": "ARCADE", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/pacman.zip", "cover": "battle.png", "region": "ARCADE", "year": "1980"},
    {"id": "ffight", "title": "Final Fight", "console": "ARCADE", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/ffight.zip", "cover": "battle.png", "region": "ARCADE", "year": "1989"},
    # PS1
    {"id": "crash3", "title": "Crash Bandicoot 3: Warped", "console": "PS1", "core": "cores/pcsx_rearmed_libretro.dylib", "rom": "roms/ps1/Crash Bandicoot - Warped (USA).7z", "cover": "ps.png", "region": "USA", "year": "1998"},
    {"id": "re3", "title": "Resident Evil 3: Nemesis", "console": "PS1", "core": "cores/pcsx_rearmed_libretro.dylib", "rom": "roms/ps1/Resident Evil 3 - Nemesis (E) [SLES-02529].7z", "cover": "ps.png", "region": "EUR", "year": "1999"},
    {"id": "sotn", "title": "Castlevania: Symphony of the Night", "console": "PS1", "core": "cores/pcsx_rearmed_libretro.dylib", "rom": "roms/ps1/Castlevania - Symphony of the Night (USA).7z", "cover": "ps.png", "region": "USA", "year": "1997"},
    {"id": "mslugx", "title": "Metal Slug X", "console": "PS1", "core": "cores/pcsx_rearmed_libretro.dylib", "rom": "roms/ps1/Metal Slug X (USA).7z", "cover": "ps.png", "region": "USA", "year": "2000"},
    # N64
    {"id": "sm64", "title": "Super Mario 64", "console": "N64", "core": "cores/mupen64plus_next_libretro.dylib", "rom": "roms/n64/Super Mario 64 (USA).z64", "cover": "elden.png", "region": "USA", "year": "1996"},
    {"id": "oot", "title": "Zelda: Ocarina of Time", "console": "N64", "core": "cores/mupen64plus_next_libretro.dylib", "rom": "roms/n64/Legend of Zelda, The - Ocarina of Time (USA).z64", "cover": "elden.png", "region": "USA", "year": "1998"},
    {"id": "smash64", "title": "Super Smash Bros.", "console": "N64", "core": "cores/mupen64plus_next_libretro.dylib", "rom": "roms/n64/Super Smash Bros. (USA).z64", "cover": "elden.png", "region": "USA", "year": "1999"},
    # NDS
    {"id": "pokewhite2", "title": "Pokémon White Version 2", "console": "NDS", "core": "cores/melonds_libretro.dylib", "rom": "roms/nds/Pokemon White Version 2.nds", "cover": "destiny.png", "region": "USA", "year": "2012"},
    {"id": "mkds", "title": "Mario Kart DS", "console": "NDS", "core": "cores/melonds_libretro.dylib", "rom": "roms/nds/0168 - Mario Kart DS (U)(SCZ).nds", "cover": "destiny.png", "region": "USA", "year": "2005"},
    {"id": "acww", "title": "Animal Crossing: Wild World", "console": "NDS", "core": "cores/melonds_libretro.dylib", "rom": "roms/nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds", "cover": "destiny.png", "region": "EUR", "year": "2005"},
    # Neo-Geo
    {"id": "kof2002", "title": "The King of Fighters 2002", "console": "NEO-GEO", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/kof2002.zip", "cover": "red.png", "region": "ARCADE", "year": "2002"},
    {"id": "samsho2", "title": "Samurai Shodown II", "console": "NEO-GEO", "core": "cores/fbneo_libretro.dylib", "rom": "roms/mame/samsho2.zip", "cover": "red.png", "region": "ARCADE", "year": "1994"},
    # Wii
    {"id": "wiisports", "title": "Wii Sports", "console": "WII", "core": "cores/dolphin_libretro.dylib", "rom": "roms/wii/Wii Sports (USA).wbfs", "cover": "detroit.png", "region": "USA", "year": "2006"},
    {"id": "mariogalaxy", "title": "Super Mario Galaxy", "console": "WII", "core": "cores/dolphin_libretro.dylib", "rom": "roms/wii/Super Mario Galaxy (USA).wbfs", "cover": "detroit.png", "region": "USA", "year": "2007"},
]


# ==============================================================================
# 1. VISTA HOME OMNIDASH AERO (OmniDashHomeView)
# ==============================================================================
class OmniDashHomeView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_console_idx = 0

        self.covers = {}
        for c in CONSOLES:
            cname = c.get("cover")
            if cname:
                cp = ROOT / "assets_ps4" / "img" / cname
                if cp.exists():
                    try:
                        self.covers[cname] = pygame.image.load(str(cp)).convert_alpha()
                    except Exception:
                        pass

        self.hero_rect = pygame.Rect(36, 120, 330, 460)
        self.hero_btn_rect = pygame.Rect(56, 500, 290, 48)
        self.grid_rects: list[pygame.Rect] = []
        self.util_rects: list[dict] = []

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for idx, r in enumerate(self.grid_rects):
                if r.collidepoint(mx, my):
                    if self.selected_console_idx != idx:
                        self.selected_console_idx = idx
                        self.engine.play_sound("navigate")
                    return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.hero_btn_rect.collidepoint(mx, my) or self.hero_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "LAUNCH_DIRECT", "item": CONSOLES[self.selected_console_idx]}

            for idx, r in enumerate(self.grid_rects):
                if r.collidepoint(mx, my):
                    self.selected_console_idx = idx
                    self.engine.play_sound("reward")
                    return {"action": "OPEN_DETAILS", "item": CONSOLES[idx]}

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
                return {"action": "LAUNCH_DIRECT", "item": CONSOLES[self.selected_console_idx]}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme
        cur_console = CONSOLES[self.selected_console_idx]

        # 1. Tarjeta Hero Grande (Izquierda)
        hx, hy, hw, hh = self.hero_rect.x, self.hero_rect.y, self.hero_rect.width, self.hero_rect.height
        h_surf = pygame.Surface((hw, hh), pygame.SRCALPHA)
        pygame.draw.rect(h_surf, t["panel_glass"], (0, 0, hw, hh), border_radius=16)
        pygame.draw.rect(h_surf, t["border_glass"], (0, 0, hw, hh), width=2, border_radius=16)
        surface.blit(h_surf, (hx, hy))

        cov = self.covers.get(cur_console.get("cover"))
        if cov:
            scaled_cov = pygame.transform.smoothscale(cov, (hw - 24, 250))
            surface.blit(scaled_cov, (hx + 12, hy + 12))
            pygame.draw.rect(surface, (255, 255, 255, 120), (hx + 12, hy + 12, hw - 24, 250), width=1, border_radius=8)

        ht = self.engine.font_hero.render(cur_console["title"], True, t["text_primary"])
        surface.blit(ht, (hx + 16, hy + 276))

        st = self.engine.font_sub.render(cur_console["subtitle"], True, t["text_secondary"])
        surface.blit(st, (hx + 18, hy + 314))

        meta_t = self.engine.font_badge.render(f"LISTO PARA JUGAR • {len(cur_console['roms'])} ROMS", True, t["accent"])
        surface.blit(meta_t, (hx + 18, hy + 342))

        is_btn_hov = self.hero_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255) if is_btn_hov else t["accent"], self.hero_btn_rect, border_radius=12)
        btn_txt_col = (10, 20, 35) if is_btn_hov else (255, 255, 255)
        bt = self.engine.font_body.render("▶  INICIAR CONSOLA", True, btn_txt_col)
        surface.blit(bt, bt.get_rect(center=self.hero_btn_rect.center))

        # 2. Cuadrícula de Cristal Derecha
        gx, gy = 390, 120
        self.grid_rects = []
        card_size = 145
        spacing_x = 18

        for idx, con in enumerate(CONSOLES[:5]):
            cx = gx + idx * (card_size + spacing_x)
            cy = gy
            rect = pygame.Rect(cx, cy, card_size, card_size)
            self.grid_rects.append(rect)

            is_sel = (idx == self.selected_console_idx)
            c_surf = pygame.Surface((card_size, card_size), pygame.SRCALPHA)
            bg_col = t["card_hover"] if is_sel else t["card_glass"]
            pygame.draw.rect(c_surf, bg_col, (0, 0, card_size, card_size), border_radius=12)
            pygame.draw.rect(c_surf, t["focus_glow"] if is_sel else t["border_glass"], (0, 0, card_size, card_size), width=2 if is_sel else 1, border_radius=12)

            c_cov = self.covers.get(con.get("cover"))
            if c_cov:
                scaled = pygame.transform.smoothscale(c_cov, (card_size - 16, 92))
                c_surf.blit(scaled, (8, 8))

            lbl = self.engine.font_badge.render(con["badge"], True, t["text_primary"])
            c_surf.blit(lbl, lbl.get_rect(center=(card_size // 2, card_size - 22)))
            surface.blit(c_surf, (cx, cy))

        # 3. Tarjetas de Utilidad OmniDash Frutiger Aero (Amigos, Biblioteca, Logros)
        self.util_rects = []
        u_y = gy + card_size + 24
        uw, uh = 250, 160
        u_spacing = 24

        utils = [
            {"id": "library", "title": "Mi Biblioteca", "sub": "27 juegos preservados en 7 consolas", "icon": "📚", "action": "LIBRARY"},
            {"id": "friends", "title": "Amigos en Línea", "sub": "3 amigos conectados en C.C.I.", "icon": "👥", "action": "GROUPS"},
            {"id": "achievements", "title": "Gamerscore & Trofeos", "sub": "18,450 G • 110 Trofeos ganados", "icon": "🏆", "action": "PROFILE"},
        ]

        for idx, u in enumerate(utils):
            ux = gx + idx * (uw + u_spacing)
            u_rect = pygame.Rect(ux, u_y, uw, uh)
            self.util_rects.append({"rect": u_rect, "action": u["action"]})

            is_hov = u_rect.collidepoint(pygame.mouse.get_pos())
            u_surf = pygame.Surface((uw, uh), pygame.SRCALPHA)
            u_bg = t["card_hover"] if is_hov else t["panel_glass"]
            pygame.draw.rect(u_surf, u_bg, (0, 0, uw, uh), border_radius=14)
            pygame.draw.rect(u_surf, t["focus_glow"] if is_hov else t["border_glass"], (0, 0, uw, uh), width=2 if is_hov else 1, border_radius=14)

            ico_t = self.engine.font_hero.render(u["icon"], True, t["text_primary"])
            u_surf.blit(ico_t, (16, 16))

            t_t = self.engine.font_body.render(u["title"], True, t["text_primary"])
            u_surf.blit(t_t, (16, 68))

            s_t = self.engine.font_sub.render(u["sub"], True, t["text_secondary"])
            u_surf.blit(s_t, (16, 98))

            surface.blit(u_surf, (ux, u_y))


# ==============================================================================
# 2. VISTA BIBLIOTECA COMPLETA OMNIDASH (OmniDashLibraryView)
# ==============================================================================
class OmniDashLibraryView:
    """Pantalla de Biblioteca Frutiger Aero con filtros por plataforma, buscador y cuadrícula de carátulas."""

    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_filter = "TODAS"
        self.selected_game_idx = 0
        self.search_query = ""

        self.covers = {}
        for g in ALL_GAMES:
            cname = g.get("cover")
            if cname and cname not in self.covers:
                cp = ROOT / "assets_ps4" / "img" / cname
                if cp.exists():
                    try:
                        self.covers[cname] = pygame.image.load(str(cp)).convert_alpha()
                    except Exception:
                        pass

        self.filters = ["TODAS", "SNES", "ARCADE", "PS1", "N64", "NDS", "NEO-GEO", "WII"]
        self.filter_rects: list[pygame.Rect] = []
        self.game_card_rects: list[pygame.Rect] = []
        self.back_btn_rect = pygame.Rect(36, 24, 110, 36)

    def _filtered_games(self) -> list[dict]:
        res = ALL_GAMES
        if self.selected_filter != "TODAS":
            res = [g for g in res if g["console"] == self.selected_filter]
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

            # Clic en filtros
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
                        game = filtered[idx]
                        return {"action": "LAUNCH_GAME", "game": game}

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

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 80 if is_back_hov else 35), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, t["text_primary"], self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("⇦ VOLVER", True, t["text_primary"])
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Título de la Biblioteca
        title_t = self.engine.font_hero.render("BIBLIOTECA DE JUEGOS Y CONSOLAS", True, t["text_primary"])
        surface.blit(title_t, (170, 26))

        # Pestañas de Filtros de Plataforma
        self.filter_rects = []
        fx = 36
        fy = 78
        for f in self.filters:
            is_active = (f == self.selected_filter)
            tw = len(f) * 10 + 26
            f_rect = pygame.Rect(fx, fy, tw, 34)
            self.filter_rects.append(f_rect)

            bg_col = (255, 255, 255, 120) if is_active else (255, 255, 255, 30)
            pygame.draw.rect(surface, bg_col, f_rect, border_radius=17)
            if is_active:
                pygame.draw.rect(surface, t["accent"], f_rect, width=2, border_radius=17)

            f_txt = self.engine.font_badge.render(f, True, t["text_primary"])
            surface.blit(f_txt, f_txt.get_rect(center=f_rect.center))
            fx += tw + 10

        # Cuadrícula de Juegos (6 columnas)
        filtered = self._filtered_games()
        self.game_card_rects = []
        cols = 6
        cw, ch = 185, 200
        start_x = 36
        start_y = 130
        gap_x, gap_y = 18, 20

        for idx, g in enumerate(filtered):
            col = idx % cols
            row = idx // cols
            cx = start_x + col * (cw + gap_x)
            cy = start_y + row * (ch + gap_y)

            card_rect = pygame.Rect(cx, cy, cw, ch)
            self.game_card_rects.append(card_rect)

            is_sel = (idx == self.selected_game_idx)
            c_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            bg_col = t["card_hover"] if is_sel else t["card_glass"]
            pygame.draw.rect(c_surf, bg_col, (0, 0, cw, ch), border_radius=12)
            pygame.draw.rect(c_surf, t["focus_glow"] if is_sel else t["border_glass"], (0, 0, cw, ch), width=2 if is_sel else 1, border_radius=12)

            # Carátula
            cov = self.covers.get(g.get("cover"))
            if cov:
                scaled = pygame.transform.smoothscale(cov, (cw - 16, 125))
                c_surf.blit(scaled, (8, 8))

            # Título y Plataforma
            g_title = g["title"] if len(g["title"]) < 20 else g["title"][:18] + "..."
            gt = self.engine.font_badge.render(g_title, True, t["text_primary"])
            c_surf.blit(gt, (10, 142))

            plat_t = self.engine.font_badge.render(f"{g['console']} • {g['region']}", True, t["accent"] if is_sel else t["text_secondary"])
            c_surf.blit(plat_t, (10, 164))

            surface.blit(c_surf, (cx, cy))


# ==============================================================================
# 3. VISTA PANTALLA CINEMÁTICA DE ARRANQUE (OmniDashLaunchScreenView)
# ==============================================================================
class OmniDashLaunchScreenView:
    """Pantalla cinemática oficial de OmniDash que eleva el logo sobre el arte del juego antes de lanzar el emulador."""

    def __init__(self, engine: OmniDashEngine, game_or_console: dict):
        self.engine = engine
        self.target = game_or_console
        self.w, self.h = engine.w, engine.h
        self.timer = 0.0
        self.duration = 1.6  # 1.6 segundos de animación fluida

        # Cargar arte
        self.art_surf = None
        cname = game_or_console.get("cover", "start.png")
        cp = ROOT / "assets_ps4" / "img" / cname
        if cp.exists():
            try:
                loaded = pygame.image.load(str(cp)).convert()
                self.art_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Reproducir sonido de arranque oficial
        self.engine.play_sound("startup")

    def update(self, dt: float) -> dict | None:
        self.timer += dt
        if self.timer >= self.duration:
            return {"action": "LAUNCH_NOW", "target": self.target}
        return None

    def render(self, surface: pygame.Surface):
        progress = min(1.0, self.timer / self.duration)
        t = self.engine.theme

        # 1. Zoom sutil del fondo
        if self.art_surf:
            zoom = 1.0 + progress * 0.08
            zw, zh = int(self.w * zoom), int(self.h * zoom)
            scaled = pygame.transform.smoothscale(self.art_surf, (zw, zh))
            surface.blit(scaled, ((self.w - zw) // 2, (self.h - zh) // 2))

            # Overlay oscurecedor para resaltar el logo
            dim_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            dim_surf.fill((0, 0, 0, int(120 + progress * 70)))
            surface.blit(dim_surf, (0, 0))
        else:
            surface.fill(t["bg_base"])

        # 2. Elevación del Logo y Título desde abajo (Curva Easing)
        ease_y = math.sin(progress * math.pi / 2)
        start_y = self.h + 80
        target_y = self.h // 2 - 60
        cur_y = int(start_y - (start_y - target_y) * ease_y)

        # Caja de cristal flotante
        bw, bh = 480, 160
        bx = (self.w - bw) // 2
        box_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (255, 255, 255, 60), (0, 0, bw, bh), border_radius=20)
        pygame.draw.rect(box_surf, (255, 255, 255, 180), (0, 0, bw, bh), width=2, border_radius=20)
        surface.blit(box_surf, (bx, cur_y))

        # Título del juego / consola
        title_txt = self.target.get("title", "Juego Retro")
        tt = self.engine.font_hero.render(title_txt, True, (255, 255, 255))
        surface.blit(tt, tt.get_rect(center=(self.w // 2, cur_y + 45)))

        badge_txt = self.target.get("console", self.target.get("badge", "C.C.I."))
        bt = self.engine.font_sub.render(f"NÚCLEO LIBRETRO A 60 FPS • {badge_txt}", True, t["accent"])
        surface.blit(bt, bt.get_rect(center=(self.w // 2, cur_y + 85)))

        # Barra de progreso brillante inferior
        bar_w = 340
        bar_x = (self.w - bar_w) // 2
        bar_y = cur_y + 115
        pygame.draw.rect(surface, (255, 255, 255, 60), (bar_x, bar_y, bar_w, 8), border_radius=4)
        fill_w = int(bar_w * progress)
        pygame.draw.rect(surface, t["accent"], (bar_x, bar_y, fill_w, 8), border_radius=4)


# ==============================================================================
# 4. VISTAS DETALLES, AJUSTES Y PERFIL OMNIDASH
# ==============================================================================
class OmniDashGameDetailsView:
    def __init__(self, engine: OmniDashEngine, item: dict):
        self.engine = engine
        self.item = item
        self.w, self.h = engine.w, engine.h
        self.selected_rom_idx = 0

        self.cover_surf = None
        cname = item.get("cover")
        if cname:
            cp = ROOT / "assets_ps4" / "img" / cname
            if cp.exists():
                try:
                    loaded = pygame.image.load(str(cp)).convert_alpha()
                    self.cover_surf = pygame.transform.smoothscale(loaded, (280, 280))
                except Exception:
                    pass

        self.back_btn_rect = pygame.Rect(36, 24, 110, 36)
        self.launch_btn_rect = pygame.Rect(360, 240, 240, 48)
        self.rom_rects: list[pygame.Rect] = []

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.back_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}

            if self.launch_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                selected_rom = self.item["roms"][self.selected_rom_idx] if self.item["roms"] else None
                return {"action": "LAUNCH", "item": self.item, "rom": selected_rom}

            for idx, r in enumerate(self.rom_rects):
                if r.collidepoint(mx, my):
                    self.selected_rom_idx = idx
                    self.engine.play_sound("reward")
                    selected_rom = self.item["roms"][idx]
                    return {"action": "LAUNCH", "item": self.item, "rom": selected_rom}

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.engine.play_sound("navigate")
                return {"action": "BACK"}
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.selected_rom_idx < len(self.item.get("roms", [])) - 1:
                    self.selected_rom_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.selected_rom_idx > 0:
                    self.selected_rom_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.engine.play_sound("reward")
                selected_rom = self.item["roms"][self.selected_rom_idx] if self.item["roms"] else None
                return {"action": "LAUNCH", "item": self.item, "rom": selected_rom}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme

        # Botón Volver
        is_back_hov = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 80 if is_back_hov else 35), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, t["text_primary"], self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("⇦ VOLVER", True, t["text_primary"])
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        px, py = 36, 80
        pw, ph = 1208, 600
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, t["panel_glass"], (0, 0, pw, ph), border_radius=16)
        pygame.draw.rect(p_surf, t["border_glass"], (0, 0, pw, ph), width=2, border_radius=16)
        surface.blit(p_surf, (px, py))

        cx, cy = px + 36, py + 36
        if self.cover_surf:
            surface.blit(self.cover_surf, (cx, cy))
            pygame.draw.rect(surface, (255, 255, 255, 140), (cx, cy, 280, 280), width=2, border_radius=8)

        ix = px + 350
        title_t = self.engine.font_hero.render(self.item["title"], True, t["text_primary"])
        surface.blit(title_t, (ix, cy))

        meta_str = f"{self.item['developer']} • {self.item['year']} • Núcleo: {self.item.get('core', 'Nativo')}"
        meta_t = self.engine.font_sub.render(meta_str, True, t["text_secondary"])
        surface.blit(meta_t, (ix, cy + 38))

        desc_t = self.engine.font_body.render(self.item.get("desc", ""), True, t["text_primary"])
        surface.blit(desc_t, (ix, cy + 74))

        pygame.draw.rect(surface, t["accent"], self.launch_btn_rect, border_radius=10)
        l_txt = self.engine.font_body.render("▶  INICIAR JUEGO (60 FPS)", True, (255, 255, 255))
        surface.blit(l_txt, l_txt.get_rect(center=self.launch_btn_rect.center))

        list_y = cy + 200
        lh_t = self.engine.font_body.render("ROMS Y TÍTULOS PRESERVADOS:", True, t["text_primary"])
        surface.blit(lh_t, (ix, list_y))

        self.rom_rects = []
        roms = self.item.get("roms", [])
        for idx, r in enumerate(roms):
            ry = list_y + 32 + idx * 44
            r_rect = pygame.Rect(ix, ry, 780, 38)
            self.rom_rects.append(r_rect)

            is_sel = (idx == self.selected_rom_idx)
            bg_col = t["card_hover"] if is_sel else t["card_glass"]
            pygame.draw.rect(surface, bg_col, r_rect, border_radius=6)
            if is_sel:
                pygame.draw.rect(surface, t["focus_glow"], r_rect, width=2, border_radius=6)

            rt = self.engine.font_body.render(f"🎮  {r['name']}", True, t["text_primary"])
            surface.blit(rt, (r_rect.x + 14, r_rect.y + 10))

            reg_t = self.engine.font_badge.render(f"[{r['region']}]", True, t["accent"] if is_sel else t["text_secondary"])
            surface.blit(reg_t, (r_rect.right - 80, r_rect.y + 12))


class OmniDashSettingsView:
    def __init__(self, engine: OmniDashEngine):
        from ps4_settings_ui import PS4SettingsUI
        self.engine = engine
        self.inner_ui = PS4SettingsUI(engine.w, engine.h)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        return self.inner_ui.handle_event(event)

    def render(self, surface: pygame.Surface):
        self.inner_ui.render(surface)


class OmniDashProfileView:
    def __init__(self, engine: OmniDashEngine):
        from ps4_profile_ui import PS4ProfileUI
        self.engine = engine
        self.inner_ui = PS4ProfileUI(engine.w, engine.h)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        return self.inner_ui.handle_event(event)

    def render(self, surface: pygame.Surface):
        self.inner_ui.render(surface)


# ==============================================================================
# 5. ESTADOS DE STATEMACHINE PARA INTEGRACIÓN CON C.C.I. SYSTEM
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
                    if dest in ("SETTINGS", "PROFILE", "GROUPS", "LIBRARY"):
                        self.state_machine.change_state(dest)
                        return

            res = self.home_view.handle_event(event)
            if res:
                if res.get("action") == "LAUNCH_DIRECT":
                    item = res["item"]
                    self.state_machine.change_state("LAUNCH_ANIM", target=item)
                elif res.get("action") == "OPEN_DETAILS":
                    self.state_machine.change_state("DETAILS", item=res["item"])
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


class OmniDashLaunchAnimState:
    """Estado 'LAUNCH_ANIM' cinemático de OmniDash Aero antes de arrancar Libretro."""
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
                # Determinar core y rom
                if "core" in target and "rom" in target:
                    core_path = target["core"]
                    rom_path = target["rom"]
                    game_title = target["title"]
                elif "roms" in target and target["roms"]:
                    core_path = target["core"]
                    rom_path = f"roms/{target['id']}/{target['roms'][0]['file']}"
                    game_title = target["roms"][0]["name"]
                else:
                    self.state_machine.change_state("MENU")
                    return

                self.state_machine.change_state(
                    "PLAYING",
                    game_key=game_title,
                    rom_path=rom_path,
                    core_path=core_path
                )

    def draw(self, screen):
        if self.launch_view:
            self.launch_view.render(screen)


class OmniDashDetailsState:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        self.details_view = None

    def enter(self, item=None, **kwargs):
        if item:
            self.details_view = OmniDashGameDetailsView(self.engine, item)

    def exit(self):
        pass

    def handle_events(self, events):
        if not self.details_view:
            self.state_machine.change_state("MENU")
            return

        for event in events:
            res = self.details_view.handle_event(event)
            if not res:
                continue
            if res.get("action") == "BACK":
                self.state_machine.change_state("MENU")
                return
            elif res.get("action") == "LAUNCH":
                item = res["item"]
                rom = res.get("rom")
                if item.get("core") and rom:
                    game_data = {
                        "title": rom["name"],
                        "console": item["badge"],
                        "core": item["core"],
                        "rom": f"roms/{item['id']}/{rom['file']}",
                        "cover": item.get("cover", "start.png")
                    }
                    self.state_machine.change_state("LAUNCH_ANIM", target=game_data)
                    return

    def update(self, dt):
        pass

    def draw(self, screen):
        self.engine.render_background(screen)
        if self.details_view:
            self.details_view.render(screen)
        self.engine.render_bottom_dock(screen, extra_actions=[("⌧", "Lanzar Título")])


class OmniDashSettingsState:
    def __init__(self, state_machine, user_data=None, apply_display_callback=None):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        from ps4_settings_ui import PS4SettingsUI
        self.ui = PS4SettingsUI(1280, 720, user_data=user_data, apply_display_callback=apply_display_callback)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.ui.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")

    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui.render(screen)


class OmniDashProfileState:
    def __init__(self, state_machine, user_data=None):
        self.state_machine = state_machine
        self.engine = get_shared_engine()
        from ps4_profile_ui import PS4ProfileUI
        self.ui = PS4ProfileUI(1280, 720, user_data=user_data)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.ui.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")

    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui.render(screen)
