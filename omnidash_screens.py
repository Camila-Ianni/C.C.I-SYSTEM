"""omnidash_screens.py - Pantallas Auténticas del Sistema OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE.
Implementa el diseño oficial de OmniDash:
- Home: Tarjeta Hero grande a la izquierda + Cuadrícula de tarjetas de cristal brillante y tarjetas de utilidad a la derecha.
- Game Details: Ficha técnica con carátula grande, lista de ROMs y botón directo de lanzamiento Libretro a 60 FPS.
- Settings: Panel de 8 categorías estándar OmniDash.
- Profile: Perfil de usuario con Gamerscore y trofeos.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
from pathlib import Path
import pygame

from omnidash_engine import OmniDashEngine, THEMES

ROOT = Path(__file__).resolve().parent

# Catálogo oficial de Consolas de OmniDash para C.C.I. SYSTEM
CONSOLES = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 21 ROMS DISPONIBLES",
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
        "subtitle": "64-BIT 3D // 5 ROMS PRESERVADAS",
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
        "desc": "Doble pantalla y aventuras inolvidables.",
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
        "desc": "Innovación y diversión en familia a 60 FPS.",
        "roms": [
            {"name": "Wii Sports", "file": "Wii Sports (USA).wbfs", "region": "USA"},
            {"name": "Super Mario Galaxy", "file": "Super Mario Galaxy (USA).wbfs", "region": "USA"},
        ],
    },
]


# ==============================================================================
# 1. VISTA HOME OMNIDASH (Hero Card + Grid de Cristal Frutiger Aero)
# ==============================================================================
class OmniDashHomeView:
    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_console_idx = 0

        # Cargar carátulas
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

        # Rectángulos clickeables
        self.hero_rect = pygame.Rect(36, 120, 330, 460)
        self.hero_btn_rect = pygame.Rect(56, 500, 290, 48)
        self.grid_rects: list[pygame.Rect] = []
        self.util_rects: list[dict] = []

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Hover sobre las tarjetas de la cuadrícula superior
            for idx, r in enumerate(self.grid_rects):
                if r.collidepoint(mx, my):
                    if self.selected_console_idx != idx:
                        self.selected_console_idx = idx
                        self.engine.play_sound("navigate")
                    return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clic en botón Iniciar de la tarjeta Hero
            if self.hero_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "OPEN_DETAILS", "item": CONSOLES[self.selected_console_idx]}

            # Clic en tarjeta Hero
            if self.hero_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                return {"action": "OPEN_DETAILS", "item": CONSOLES[self.selected_console_idx]}

            # Clic en tarjetas de la cuadrícula
            for idx, r in enumerate(self.grid_rects):
                if r.collidepoint(mx, my):
                    self.selected_console_idx = idx
                    self.engine.play_sound("reward")
                    return {"action": "OPEN_DETAILS", "item": CONSOLES[idx]}

            # Clic en tarjetas de utilidad (Amigos, Comunidad, Logros)
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
                return {"action": "OPEN_DETAILS", "item": CONSOLES[self.selected_console_idx]}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme
        cur_console = CONSOLES[self.selected_console_idx]

        # ----------------------------------------------------------------------
        # 1. TARJETA HERO GRANDE (Izquierda - Diseño OmniDash Oficial)
        # ----------------------------------------------------------------------
        hx, hy, hw, hh = self.hero_rect.x, self.hero_rect.y, self.hero_rect.width, self.hero_rect.height

        # Panel de cristal esmerilado de fondo
        h_surf = pygame.Surface((hw, hh), pygame.SRCALPHA)
        pygame.draw.rect(h_surf, t["panel_glass"], (0, 0, hw, hh), border_radius=16)
        pygame.draw.rect(h_surf, t["border_glass"], (0, 0, hw, hh), width=2, border_radius=16)
        surface.blit(h_surf, (hx, hy))

        # Carátula destacada del Hero
        cov = self.covers.get(cur_console.get("cover"))
        if cov:
            scaled_cov = pygame.transform.smoothscale(cov, (hw - 24, 250))
            surface.blit(scaled_cov, (hx + 12, hy + 12))
            pygame.draw.rect(surface, (255, 255, 255, 120), (hx + 12, hy + 12, hw - 24, 250), width=1, border_radius=8)

        # Información del Hero
        ht = self.engine.font_hero.render(cur_console["title"], True, t["text_primary"])
        surface.blit(ht, (hx + 16, hy + 276))

        st = self.engine.font_sub.render(cur_console["subtitle"], True, t["text_secondary"])
        surface.blit(st, (hx + 18, hy + 314))

        meta_t = self.engine.font_badge.render(f"LISTO PARA JUGAR • {len(cur_console['roms'])} ROMS", True, t["accent"])
        surface.blit(meta_t, (hx + 18, hy + 342))

        # Botón 'INICIAR' grande
        is_btn_hov = self.hero_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255) if is_btn_hov else t["accent"], self.hero_btn_rect, border_radius=12)
        btn_txt_col = (10, 20, 35) if is_btn_hov else (255, 255, 255)
        bt = self.engine.font_body.render("▶  INICIAR CONSOLA", True, btn_txt_col)
        surface.blit(bt, bt.get_rect(center=self.hero_btn_rect.center))

        # ----------------------------------------------------------------------
        # 2. CUADRÍCULA DE CRISTAL DERECHA (OmniDash Frutiger Aero)
        # ----------------------------------------------------------------------
        gx = 390
        gy = 120

        # Fila 1: Tarjetas Cuadradas de Consolas (145x145 px)
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

            # Arte de la tarjeta
            c_cov = self.covers.get(con.get("cover"))
            if c_cov:
                scaled = pygame.transform.smoothscale(c_cov, (card_size - 16, 92))
                c_surf.blit(scaled, (8, 8))

            # Título de la tarjeta
            lbl = self.engine.font_badge.render(con["badge"], True, t["text_primary"])
            c_surf.blit(lbl, lbl.get_rect(center=(card_size // 2, card_size - 22)))

            surface.blit(c_surf, (cx, cy))

        # Fila 2: Tarjetas de Utilidad y Servicios (Frosted Glass Cards, 250x180 px)
        self.util_rects = []
        u_y = gy + card_size + 24
        uw = 250
        uh = 160
        u_spacing = 24

        utils = [
            {"id": "friends", "title": "Amigos en Línea", "sub": "3 amigos conectados en C.C.I.", "icon": "👥", "action": "GROUPS"},
            {"id": "library", "title": "Game Pass / Biblioteca", "sub": "27 ROMs preservadas a 60 FPS", "icon": "🎮", "action": "LIBRARY"},
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

            # Icono + Título
            ico_t = self.engine.font_hero.render(u["icon"], True, t["text_primary"])
            u_surf.blit(ico_t, (16, 16))

            t_t = self.engine.font_body.render(u["title"], True, t["text_primary"])
            u_surf.blit(t_t, (16, 68))

            s_t = self.engine.font_sub.render(u["sub"], True, t["text_secondary"])
            u_surf.blit(s_t, (16, 98))

            surface.blit(u_surf, (ux, u_y))


# ==============================================================================
# 2. VISTA DETALLES DE JUEGO / CONSOLA (OmniDashGameDetailsView)
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

        # Panel de Cristal de Detalles
        px, py = 36, 80
        pw, ph = 1208, 600
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, t["panel_glass"], (0, 0, pw, ph), border_radius=16)
        pygame.draw.rect(p_surf, t["border_glass"], (0, 0, pw, ph), width=2, border_radius=16)
        surface.blit(p_surf, (px, py))

        # Carátula
        cx, cy = px + 36, py + 36
        if self.cover_surf:
            surface.blit(self.cover_surf, (cx, cy))
            pygame.draw.rect(surface, (255, 255, 255, 140), (cx, cy, 280, 280), width=2, border_radius=8)

        # Especificaciones
        ix = px + 350
        title_t = self.engine.font_hero.render(self.item["title"], True, t["text_primary"])
        surface.blit(title_t, (ix, cy))

        meta_str = f"{self.item['developer']} • {self.item['year']} • Núcleo: {self.item.get('core', 'Nativo')}"
        meta_t = self.engine.font_sub.render(meta_str, True, t["text_secondary"])
        surface.blit(meta_t, (ix, cy + 38))

        desc_t = self.engine.font_body.render(self.item.get("desc", ""), True, t["text_primary"])
        surface.blit(desc_t, (ix, cy + 74))

        # Botón Lanzar
        pygame.draw.rect(surface, t["accent"], self.launch_btn_rect, border_radius=10)
        l_txt = self.engine.font_body.render("▶  INICIAR JUEGO (60 FPS)", True, (255, 255, 255))
        surface.blit(l_txt, l_txt.get_rect(center=self.launch_btn_rect.center))

        # Lista de ROMs
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


# ==============================================================================
# 3. VISTA AJUSTES (OmniDashSettingsView)
# ==============================================================================
class OmniDashSettingsView:
    def __init__(self, engine: OmniDashEngine):
        from ps4_settings_ui import PS4SettingsUI
        self.engine = engine
        self.inner_ui = PS4SettingsUI(engine.w, engine.h)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        return self.inner_ui.handle_event(event)

    def render(self, surface: pygame.Surface):
        self.inner_ui.render(surface)


# ==============================================================================
# 4. VISTA PERFIL (OmniDashProfileView)
# ==============================================================================
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
            # 1. Shell global
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

            # 2. Vista Home
            res = self.home_view.handle_event(event)
            if res:
                if res.get("action") == "OPEN_DETAILS":
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
                    rom_path = f"roms/{item['id']}/{rom['file']}"
                    core_path = item["core"]
                    self.state_machine.change_state(
                        "PLAYING",
                        game_key=rom["name"],
                        rom_path=rom_path,
                        core_path=core_path
                    )
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
