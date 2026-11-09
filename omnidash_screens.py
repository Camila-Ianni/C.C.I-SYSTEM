"""omnidash_screens.py - Pantallas Principales Unificadas estilo OmniDash.
100% Python puro con Pygame-CE.
Vistas implementadas:
1. OmniDashHomeView: Cinta central de tarjetas de arte cuadrado, foco dinámico por tema y lanzador rápido.
2. OmniDashGameDetailsView: Ficha completa de juego/consola con carátula grande, especificaciones, lista de ROMs y botón 'Iniciar'.
3. OmniDashSettingsView: Panel de configuración de 8 categorías estándar OmniDash adaptable al tema activo.
4. OmniDashProfileView: Perfil de usuario con Gamerscore, trofeos oficiales y selector de avatares.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import datetime
import math
import shutil
from pathlib import Path
import pygame

from omnidash_engine import OmniDashEngine, THEMES

ROOT = Path(__file__).resolve().parent

# Colección Principal de Consolas y Juegos para el Home de OmniDash
HOME_ITEMS = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 21 ROMS PRESERVADAS",
        "badge": "SNES",
        "cover": "start.png",
        "year": "1990",
        "developer": "Nintendo EAD",
        "core": "cores/snes9x_libretro.dylib",
        "desc": "La cúspide del pixel art de 16 bits. Incluye Super Mario World, Super Metroid, Donkey Kong Country y Zelda A Link to the Past.",
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
        "year": "1993",
        "developer": "Capcom / Midway / SNK",
        "core": "cores/fbneo_libretro.dylib",
        "desc": "Las máquinas recreativas más icónicas de la historia. Acción frenética a 60 FPS con Metal Slug, Marvel vs Capcom y Final Fight.",
        "roms": [
            {"name": "Metal Slug 2", "file": "mslug2.zip", "region": "ARCADE"},
            {"name": "Marvel vs Capcom", "file": "mvsc.zip", "region": "ARCADE"},
            {"name": "Pac-Man (Midway)", "file": "pacman.zip", "region": "ARCADE"},
            {"name": "Final Fight", "file": "ffight.zip", "region": "ARCADE"},
            {"name": "Cruis'n USA", "file": "crusnusa.zip", "region": "ARCADE"},
        ],
    },
    {
        "id": "ps1",
        "title": "PlayStation",
        "subtitle": "32-BIT CD-ROM // CRASH & RESIDENT EVIL",
        "badge": "PS1",
        "cover": "ps.png",
        "year": "1994",
        "developer": "Sony Computer Entertainment",
        "core": "cores/pcsx_rearmed_libretro.dylib",
        "desc": "La revolución del CD-ROM y los gráficos 3D poligonales. Audio estéreo digital y clásicos legendarios.",
        "roms": [
            {"name": "Crash Bandicoot 3: Warped", "file": "Crash Bandicoot - Warped (USA).7z", "region": "USA"},
            {"name": "Resident Evil 3: Nemesis", "file": "Resident Evil 3 - Nemesis (E) [SLES-02529].7z", "region": "EUR"},
            {"name": "Castlevania: Symphony of the Night", "file": "Castlevania - Symphony of the Night (USA).7z", "region": "USA"},
            {"name": "Metal Slug X", "file": "Metal Slug X (USA).7z", "region": "USA"},
            {"name": "Yu-Gi-Oh! Forbidden Memories", "file": "Yu-Gi-Oh! Forbidden Memories (USA).7z", "region": "USA"},
        ],
    },
    {
        "id": "neogeo",
        "title": "SNK Neo-Geo",
        "subtitle": "24-BIT // 330 MEGA PRO-GEAR",
        "badge": "NEO-GEO",
        "cover": "red.png",
        "year": "1990",
        "developer": "SNK Corporation",
        "core": "cores/fbneo_libretro.dylib",
        "desc": "El hardware arcade más potente llevado al salón. Gráficos 2D colosales y bandas sonoras magistrales.",
        "roms": [
            {"name": "The King of Fighters 2002", "file": "kof2002.zip", "region": "ARCADE"},
            {"name": "Metal Slug X (MVS)", "file": "mslugx.zip", "region": "ARCADE"},
            {"name": "Samurai Shodown II", "file": "samsho2.zip", "region": "ARCADE"},
            {"name": "Garou: Mark of the Wolves", "file": "garou.zip", "region": "ARCADE"},
        ],
    },
    {
        "id": "n64",
        "title": "Nintendo 64",
        "subtitle": "64-BIT 3D // MARIO 64 & ZELDA",
        "badge": "N64",
        "cover": "elden.png",
        "year": "1996",
        "developer": "Nintendo",
        "core": "cores/mupen64plus_next_libretro.dylib",
        "desc": "La era dorada del 3D en cartucho. Control analógico de 360 grados y mundos tridimensionales abiertos.",
        "roms": [
            {"name": "Super Mario 64", "file": "Super Mario 64 (USA).z64", "region": "USA"},
            {"name": "The Legend of Zelda: Ocarina of Time", "file": "Legend of Zelda, The - Ocarina of Time (USA).z64", "region": "USA"},
            {"name": "Super Smash Bros.", "file": "Super Smash Bros. (USA).z64", "region": "USA"},
            {"name": "Mario Kart 64", "file": "Mario Kart 64 (USA).z64", "region": "USA"},
            {"name": "Banjo-Kazooie", "file": "Banjo-Kazooie (USA).z64", "region": "USA"},
        ],
    },
    {
        "id": "nds",
        "title": "Nintendo DS",
        "subtitle": "DUAL SCREEN // POKÉMON & MARIO",
        "badge": "NDS",
        "cover": "destiny.png",
        "year": "2004",
        "developer": "Nintendo",
        "core": "cores/melonds_libretro.dylib",
        "desc": "Innovación táctil con doble pantalla. Millones de aventuras portátiles en la palma de tu mano.",
        "roms": [
            {"name": "Pokémon White Version 2", "file": "Pokemon White Version 2.nds", "region": "USA"},
            {"name": "Mario Kart DS", "file": "0168 - Mario Kart DS (U)(SCZ).nds", "region": "USA"},
            {"name": "New Super Mario Bros.", "file": "0434 - New Super Mario Bros. (U)(Psyfer).nds", "region": "USA"},
            {"name": "Animal Crossing: Wild World", "file": "0389 - Animal Crossing - Wild World (E)(Legacy).nds", "region": "EUR"},
        ],
    },
    {
        "id": "wii",
        "title": "Nintendo Wii",
        "subtitle": "MOTION CONTROL // WII SPORTS & GALAXY",
        "badge": "WII",
        "cover": "detroit.png",
        "year": "2006",
        "developer": "Nintendo",
        "core": "cores/dolphin_libretro.dylib",
        "desc": "Control por movimiento que revolucionó la industria. Clásicos familiares y aventuras inolvidables.",
        "roms": [
            {"name": "Wii Sports", "file": "Wii Sports (USA).wbfs", "region": "USA"},
            {"name": "Super Mario Galaxy", "file": "Super Mario Galaxy (USA).wbfs", "region": "USA"},
            {"name": "Mario Kart Wii", "file": "Mario Kart Wii (USA).wbfs", "region": "USA"},
        ],
    },
    {
        "id": "community",
        "title": "Comunidad C.C.I.",
        "subtitle": "HUB MULTIJUGADOR, GRUPOS Y CHAT",
        "badge": "COMMUNITY",
        "cover": "friends.png",
        "year": "2026",
        "developer": "C.C.I. Core Team",
        "core": None,
        "desc": "Espacio social para compartir partidas, competir en tablas de clasificación y chatear en tiempo real.",
        "roms": [],
    },
]


# ==============================================================================
# 1. VISTA HOME / DASHBOARD (OmniDashHomeView)
# ==============================================================================
class OmniDashHomeView:
    """Cinta de tarjetas de arte cuadrado estilo OmniDash con separación limpia y foco dinámico."""

    def __init__(self, engine: OmniDashEngine):
        self.engine = engine
        self.w, self.h = engine.w, engine.h
        self.selected_idx = 0
        self.scroll_x = 0.0

        # Cargar carátulas cacheadas
        self.covers = {}
        for it in HOME_ITEMS:
            cname = it.get("cover")
            if cname:
                cp = ROOT / "assets_ps4" / "img" / cname
                if cp.exists():
                    try:
                        self.covers[cname] = pygame.image.load(str(cp)).convert_alpha()
                    except Exception:
                        pass

        self.card_rects: list[pygame.Rect] = []
        self.start_btn_rect: pygame.Rect | None = None

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for idx, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    if self.selected_idx != idx:
                        self.selected_idx = idx
                        self.engine.play_sound("navigate")
                    return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Clic en botón iniciar
            if self.start_btn_rect and self.start_btn_rect.collidepoint(mx, my):
                self.engine.play_sound("reward")
                item = HOME_ITEMS[self.selected_idx]
                return {"action": "OPEN_DETAILS", "item": item}

            # Clic en tarjeta
            for idx, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    if self.selected_idx == idx:
                        self.engine.play_sound("reward")
                        return {"action": "OPEN_DETAILS", "item": HOME_ITEMS[idx]}
                    else:
                        self.selected_idx = idx
                        self.engine.play_sound("navigate")
                        return None

        elif event.type == pygame.MOUSEWHEEL:
            if event.y < 0 and self.selected_idx < len(HOME_ITEMS) - 1:
                self.selected_idx += 1
                self.engine.play_sound("navigate")
            elif event.y > 0 and self.selected_idx > 0:
                self.selected_idx -= 1
                self.engine.play_sound("navigate")

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_idx < len(HOME_ITEMS) - 1:
                    self.selected_idx += 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                    self.engine.play_sound("navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_x):
                self.engine.play_sound("reward")
                return {"action": "OPEN_DETAILS", "item": HOME_ITEMS[self.selected_idx]}

        return None

    def render(self, surface: pygame.Surface):
        t = self.engine.theme
        sel_idx = self.selected_idx

        # Parámetros geométricos OmniDash
        card_w_normal, card_h_normal = 190, 190
        card_w_focused, card_h_focused = 245, 245
        gap = 26
        baseline_y = 445

        widths = [card_w_focused if i == sel_idx else card_w_normal for i in range(len(HOME_ITEMS))]
        heights = [card_h_focused if i == sel_idx else card_h_normal for i in range(len(HOME_ITEMS))]

        # Posicionamiento secuencial exacto (cero colisión)
        rel_x = [0]
        for i in range(1, len(HOME_ITEMS)):
            rel_x.append(rel_x[-1] + widths[i - 1] + gap)

        target_scroll = 90 - rel_x[sel_idx]
        self.scroll_x += (target_scroll - self.scroll_x) * 0.22

        self.card_rects = []
        self.start_btn_rect = None

        for idx, item in enumerate(HOME_ITEMS):
            is_sel = (idx == sel_idx)
            cw = widths[idx]
            ch = heights[idx]
            cx = rel_x[idx] + int(self.scroll_x)
            cy = baseline_y - ch

            card_rect = pygame.Rect(cx, cy, cw, ch)
            self.card_rects.append(card_rect)

            if cx + cw < -60 or cx > self.w + 60:
                continue

            card_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, t["card_bg"], (0, 0, cw, ch), border_radius=10)

            # Carátula
            cov = self.covers.get(item.get("cover"))
            if cov:
                art_h = ch - 44 if is_sel else ch
                scaled_art = pygame.transform.smoothscale(cov, (cw, art_h))
                card_surf.blit(scaled_art, (0, 0))

            if is_sel:
                # Foco y resplandor
                glow_r = pygame.Rect(cx - 3, cy - 3, cw + 6, ch + 6)
                pygame.draw.rect(surface, (255, 255, 255, 45), glow_r, width=2, border_radius=14)
                pygame.draw.rect(card_surf, t["focus_glow"], (0, 0, cw, ch), width=3, border_radius=10)

                # Botón 'INICIAR' prolijo
                btn_h = 36
                btn_pill = pygame.Surface((cw - 12, btn_h), pygame.SRCALPHA)
                pygame.draw.rect(btn_pill, (255, 255, 255), (0, 0, cw - 12, btn_h), border_radius=6)
                btn_t = self.engine.font_btn.render("▶  INICIAR", True, (10, 20, 35))
                btn_pill.blit(btn_t, btn_t.get_rect(center=((cw - 12) // 2, btn_h // 2)))
                card_surf.blit(btn_pill, (6, ch - btn_h - 4))

                self.start_btn_rect = pygame.Rect(cx + 6, cy + ch - btn_h - 4, cw - 12, btn_h)
            else:
                pygame.draw.rect(card_surf, (255, 255, 255, 25), (0, 0, cw, ch), width=1, border_radius=10)
                badge_bar = pygame.Surface((cw, 28), pygame.SRCALPHA)
                badge_bar.fill((0, 0, 0, 160))
                bt = self.engine.font_badge.render(item["badge"], True, t["text_secondary"])
                badge_bar.blit(bt, bt.get_rect(center=(cw // 2, 14)))
                card_surf.blit(badge_bar, (0, ch - 28))

            surface.blit(card_surf, (cx, cy))

            if is_sel:
                info_y = baseline_y + 18
                mt = self.engine.font_title.render(item["title"], True, t["text_primary"])
                surface.blit(mt, (cx, info_y))
                st = self.engine.font_sub.render(item["subtitle"], True, t["text_secondary"])
                surface.blit(st, (cx, info_y + 36))


# ==============================================================================
# 2. VISTA DETALLES DE JUEGO / CONSOLA (OmniDashGameDetailsView)
# ==============================================================================
class OmniDashGameDetailsView:
    """Ficha interactiva de juego y consola con carátula grande, lista de ROMs y botón directo de inicio."""

    def __init__(self, engine: OmniDashEngine, item: dict):
        self.engine = engine
        self.item = item
        self.w, self.h = engine.w, engine.h
        self.selected_rom_idx = 0

        # Carátula
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

        self.back_btn_rect = pygame.Rect(40, 24, 110, 36)
        self.launch_btn_rect = pygame.Rect(380, 260, 220, 48)
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
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hov else 25), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, t["text_primary"], self.back_btn_rect, width=1, border_radius=18)
        bt = self.engine.font_btn.render("⇦ VOLVER", True, t["text_primary"])
        surface.blit(bt, bt.get_rect(center=self.back_btn_rect.center))

        # Panel Principal
        px, py = 40, 80
        pw, ph = 1200, 600
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, t["panel_bg"], (0, 0, pw, ph), border_radius=14)
        surface.blit(p_surf, (px, py))

        # 1. Carátula Destacada Izquierda
        cx, cy = px + 40, py + 40
        if self.cover_surf:
            surface.blit(self.cover_surf, (cx, cy))
            pygame.draw.rect(surface, t["focus_glow"], (cx, cy, 280, 280), width=2, border_radius=8)

        # 2. Información del Juego / Plataforma Derecha
        ix = px + 360
        title_t = self.engine.font_title.render(self.item["title"], True, t["text_primary"])
        surface.blit(title_t, (ix, cy))

        meta_str = f"{self.item['developer']} • {self.item['year']} • Núcleo: {self.item.get('core', 'Nativo')}"
        meta_t = self.engine.font_sub.render(meta_str, True, t["text_secondary"])
        surface.blit(meta_t, (ix, cy + 38))

        # Descripción
        desc_t = self.engine.font_body.render(self.item.get("desc", ""), True, t["text_primary"])
        surface.blit(desc_t, (ix, cy + 74))

        # Botón grande de Lanzamiento
        pygame.draw.rect(surface, t["accent"], self.launch_btn_rect, border_radius=10)
        l_txt = self.engine.font_body.render("▶  INICIAR JUEGO (60 FPS)", True, (255, 255, 255))
        surface.blit(l_txt, l_txt.get_rect(center=self.launch_btn_rect.center))

        # 3. Lista de ROMs Disponibles
        list_y = cy + 220
        lh_t = self.engine.font_body.render("TÍTULOS Y ROMS VERIFICADAS:", True, t["text_primary"])
        surface.blit(lh_t, (ix, list_y))

        self.rom_rects = []
        roms = self.item.get("roms", [])
        for idx, r in enumerate(roms):
            ry = list_y + 35 + idx * 46
            r_rect = pygame.Rect(ix, ry, 760, 40)
            self.rom_rects.append(r_rect)

            is_sel = (idx == self.selected_rom_idx)
            bg_col = t["card_hover"] if is_sel else t["card_bg"]
            pygame.draw.rect(surface, bg_col, r_rect, border_radius=6)
            if is_sel:
                pygame.draw.rect(surface, t["focus_glow"], r_rect, width=2, border_radius=6)

            rt = self.engine.font_body.render(f"🎮  {r['name']}", True, t["text_primary"])
            surface.blit(rt, (r_rect.x + 14, r_rect.y + 11))

            reg_t = self.engine.font_badge.render(f"[{r['region']}]", True, t["accent"] if is_sel else t["text_secondary"])
            surface.blit(reg_t, (r_rect.right - 80, r_rect.y + 13))


# ==============================================================================
# 3. VISTA AJUSTES (OmniDashSettingsView)
# ==============================================================================
class OmniDashSettingsView:
    """Panel de Ajustes OmniDash de 8 secciones estándar."""

    def __init__(self, engine: OmniDashEngine):
        from ps4_settings_ui import PS4SettingsUI
        self.engine = engine
        self.inner_ui = PS4SettingsUI(engine.w, engine.h)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        return self.inner_ui.handle_event(event)

    def render(self, surface: pygame.Surface):
        self.inner_ui.render(surface)


# ==============================================================================
# 4. VISTA PERFIL DE USUARIO (OmniDashProfileView)
# ==============================================================================
class OmniDashProfileView:
    """Panel de Perfil OmniDash con Gamerscore, trofeos y avatares."""

    def __init__(self, engine: OmniDashEngine):
        from ps4_profile_ui import PS4ProfileUI
        self.engine = engine
        self.inner_ui = PS4ProfileUI(engine.w, engine.h)

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        return self.inner_ui.handle_event(event)

    def render(self, surface: pygame.Surface):
        self.inner_ui.render(surface)
