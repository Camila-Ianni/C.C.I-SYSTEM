"""
character_select.py - Pantalla oficial de Selección de Personajes estilo Street Fighter II.

Características:
- Renderizado de assets/backgrounds/player select.png (mapa mundial y cuadrícula de 8 casillas).
- Renderizado auténtico de países: en blanco y negro por defecto, y en COLOR al ser seleccionados.
- Reproducción de voz del locutor oficial para cada país desde assets/audio/Sounds/paises/*.mp3:
  al pasar sobre un país (vía teclado o ratón), se reproduce su audio exactamente una vez.
- Retratos de gran tamaño estilo arcade: Jugador 1 a la izquierda y Jugador 2/CPU a la derecha,
  mostrando únicamente la foto del luchador y su nombre, sin tarjetas de estadísticas ni barras de info.
- Soporte para navegación por teclado (WASD, flechas, Enter/Espacio) y selección por ratón (hover y click).
- Modos 1P vs IA (autoselección y bloqueo de IA) y 2P PVP.
"""

import os
import pygame
import numpy as np
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_WHITE,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BG,
    COLOR_GREEN,
    MODE_PVAI,
    MODE_PVP,
    FPS,
    ARCADE_WIDTH,
    ARCADE_HEIGHT,
    PILLARBOX_OFFSET_X,
)
from character_data import CHARACTERS, get_character_data
from audio_manager import audio_manager
from arcade_font import get_arcade_font


# Coordenadas y banderas de país para cada profesor en el mapa mundial
# Calculadas con máxima precisión en formato arcade 4:3 centrado (960x720 con offset 160px)
CHARACTER_LOCATIONS = {
    "carloni":  {"country": "JAPÓN",    "flag": "🇯🇵", "stage_name": "Database Suzaku Dojo",        "map_pos": (630, 229), "country_key": "japan"},
    "cavasso":  {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Ken Battle Harbor (USA)",      "map_pos": (860, 78),  "country_key": "usa"},
    "romero":   {"country": "JAPÓN",    "flag": "🇯🇵", "stage_name": "E. Honda Bathhouse (Japan)",   "map_pos": (671, 123), "country_key": "japan_up"},
    "honda":    {"country": "JAPÓN",    "flag": "🇯🇵", "stage_name": "E. Honda Bathhouse (Japan)",   "map_pos": (671, 123), "country_key": "japan_up"},
    "gamaliel": {"country": "BRASIL",   "flag": "🇧🇷", "stage_name": "Blanka Amazon River (Brazil)", "map_pos": (829, 306), "country_key": "brazil"},
    "blanka":   {"country": "BRASIL",   "flag": "🇧🇷", "stage_name": "Blanka Amazon River (Brazil)", "map_pos": (829, 306), "country_key": "brazil"},
    "sellanes": {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Guile Airbase Hangar (USA)",  "map_pos": (870, 187), "country_key": "usa_low"},
    "china":    {"country": "CHINA",    "flag": "🇨🇳", "stage_name": "Market Street (China)",        "map_pos": (552, 112), "country_key": "china"},
    "chunli":   {"country": "CHINA",    "flag": "🇨🇳", "stage_name": "Market Street (China)",        "map_pos": (552, 112), "country_key": "china"},
    "ussr":     {"country": "U.S.S.R.", "flag": "☭",  "stage_name": "Industrial Furnace (U.S.S.R.)", "map_pos": (423, 105), "country_key": "ussr"},
    "zangief":  {"country": "U.S.S.R.", "flag": "☭",  "stage_name": "Industrial Furnace (U.S.S.R.)", "map_pos": (423, 105), "country_key": "ussr"},
    "india":    {"country": "INDIA",    "flag": "🇮🇳", "stage_name": "Maharajah Palace (India)",    "map_pos": (450, 213), "country_key": "india"},
    "dhalsim":  {"country": "INDIA",    "flag": "🇮🇳", "stage_name": "Maharajah Palace (India)",    "map_pos": (450, 213), "country_key": "india"},
    "ken":      {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Ken Battle Harbor (USA)",      "map_pos": (860, 78),  "country_key": "usa"},
    "guile":    {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Guile Airbase Hangar (USA)",  "map_pos": (870, 187), "country_key": "usa_low"},
    "usa":      {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Ken Battle Harbor (USA)",      "map_pos": (860, 78),  "country_key": "usa"},
    "usa_low":  {"country": "EE. UU.",  "flag": "🇺🇸", "stage_name": "Guile Airbase Hangar (USA)",  "map_pos": (870, 187), "country_key": "usa_low"},
}

# Cuadrícula arcade 2x4 (8 casillas exactamente alineadas con MAP.png en formato 4:3 con offset 160px)
GRID_SLOTS = [
    # Fila 0 (Superior)
    {"char_id": "carloni", "name": "CARLONI", "row": 0, "col": 0, "grid_rect": (482, 464, 76, 98),  "country": "japan", "flag_key": "japan", "sound": "japan"},
    {"char_id": "cavasso", "name": "CAVASSO", "row": 0, "col": 1, "grid_rect": (562, 464, 76, 98),  "country": "usa",   "flag_key": "usa",   "sound": "usa"},
    {"char_id": "romero",  "name": "ROMERO",  "row": 0, "col": 2, "grid_rect": (642, 464, 76, 98),  "country": "japan", "flag_key": "japan_up", "sound": "japan"},
    {"char_id": "gamaliel","name": "GAMALIEL","row": 0, "col": 3, "grid_rect": (722, 464, 75, 98),  "country": "brazil", "flag_key": "brazil", "sound": "brazil"},
    # Fila 1 (Inferior)
    {"char_id": "sellanes","name": "USA",      "row": 1, "col": 0, "grid_rect": (482, 565, 76, 97),  "country": "usa",   "flag_key": "usa_low", "sound": "usa"},
    {"char_id": "carloni", "name": "CHINA",    "row": 1, "col": 1, "grid_rect": (562, 565, 76, 97),  "country": "china", "flag_key": "china", "sound": "china"},
    {"char_id": "cavasso", "name": "U.S.S.R.", "row": 1, "col": 2, "grid_rect": (642, 565, 76, 97),  "country": "ussr",  "flag_key": "ussr",  "sound": "ussr"},
    {"char_id": "romero",  "name": "INDIA",    "row": 1, "col": 3, "grid_rect": (722, 565, 75, 97),  "country": "india", "flag_key": "india", "sound": "india"},
]

# Rectángulos de banderas y regiones interactivas en la imagen original MAP.png (1450 x 1085)
RAW_FLAG_RECTS = {
    "ussr":     (401, 161, 81, 56),
    "china":    (593, 171, 89, 63),
    "brazil":   (1013, 462, 93, 58),
    "usa":      (1061, 118, 87, 68),
    "usa_low":  (1076, 282, 86, 70),
    "japan_up": (773, 187, 88, 60),
    "japan":    (711, 347, 88, 54),
    "india":    (439, 322, 91, 68),
    # Aliases de compatibilidad
    "spain":    (1076, 282, 86, 70),
    "thailand": (773, 187, 88, 60),
}

RAW_MAP_REGIONS = {
    "ussr":     (360, 130, 160, 120),
    "china":    (560, 140, 160, 120),
    "japan":    (680, 320, 150, 110),
    "japan_up": (740, 155, 150, 110),
    "usa":      (1020, 90, 160, 115),
    "usa_low":  (1035, 255, 160, 115),
    "india":    (405, 290, 155, 120),
    "brazil":   (970, 430, 170, 120),
    # Aliases de compatibilidad
    "spain":    (1035, 255, 160, 115),
    "thailand": (740, 155, 150, 110),
}


class CharacterSelect:
    """
    Pantalla arcade de Selección de Personajes con mapa mundial, países dinámicos
    (color/blanco y negro), locutor de audio por país y fotos de los jugadores.
    """
    def __init__(self, screen, game_mode=MODE_PVAI, credits_p1=0, credits_p2=0):
        self.screen = screen
        is_pvp = str(game_mode).lower() in (MODE_PVP, "2p", "pvp")
        if is_pvp and credits_p1 == 0 and credits_p2 == 0:
            self.credits_p1 = 1
            self.credits_p2 = 1
            self.game_mode = MODE_PVP
        else:
            self.credits_p1 = max(0, int(credits_p1))
            self.credits_p2 = max(0, int(credits_p2))
            if self.credits_p2 > 0:
                self.game_mode = MODE_PVP
            else:
                self.game_mode = MODE_PVAI

        self.char_keys = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]

        self.font_title = pygame.font.Font(None, 44)
        self.font_header = pygame.font.Font(None, 34)
        self.font_name = pygame.font.Font(None, 38)
        self.font_info = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.arcade_font = get_arcade_font()

        # Selección de casillas (0 a 7 en GRID_SLOTS)
        self.p1_slot_idx = 0
        self.p2_slot_idx = 1
        self.p1_confirmed = False
        self.p2_confirmed = False
        self.transition_timer = 0.0
        self.blink_timer = 0.0

        # Mapeo de país a ranura de la cuadrícula
        self.country_to_slot = {
            "japan": 0,
            "usa": 1,
            "japan_up": 2,
            "thailand": 2,
            "brazil": 3,
            "usa_low": 4,
            "spain": 4,
            "china": 5,
            "ussr": 6,
            "india": 7,
        }

        # Cargar y preparar fondos de mapa mundial
        self.bg_color = None
        self.bg_bw = None
        self.color_flags = {}
        self.scaled_flag_rects = {}
        self.scaled_map_regions = {}
        self._init_map_surfaces()

        # Cache de retratos de personajes (fotos de jugadores)
        self.portraits = {}
        self._init_character_portraits()

        # Cargar archivos de audio del locutor para cada país
        self.country_sounds = {}
        self.country_voice_channel = None
        self.audio_enabled = True
        self._init_country_audio()

        # Rastreador del último país anunciado para reproducir el audio sólo una vez
        self.last_spoken_country_p1 = None
        self.last_spoken_country_p2 = None

        # Iniciar música oficial de Character Select
        audio_manager.play_music("character_select", loop=-1)

        # Reproducir el audio del país inicial (Japón) una sola vez
        initial_country = self.get_p1_country()
        self._play_country_audio(initial_country)
        self.last_spoken_country_p1 = initial_country

    @property
    def p1_idx(self):
        return self.p1_slot_idx % len(self.char_keys)

    @p1_idx.setter
    def p1_idx(self, val):
        self.p1_slot_idx = val % len(self.char_keys)

    @property
    def p2_idx(self):
        return self.p2_slot_idx % len(self.char_keys)

    @p2_idx.setter
    def p2_idx(self, val):
        self.p2_slot_idx = val % len(self.char_keys)

    @property
    def p1_char(self):
        return GRID_SLOTS[self.p1_slot_idx]["char_id"]

    @property
    def p2_char(self):
        return GRID_SLOTS[self.p2_slot_idx]["char_id"]

    def get_p1_country(self):
        return GRID_SLOTS[self.p1_slot_idx]["country"]

    def get_p2_country(self):
        return GRID_SLOTS[self.p2_slot_idx]["country"]

    def get_selected_stage_id(self):
        """Retorna el ID de escenario adecuado según país seleccionado o personaje."""
        c1 = self.get_p1_country()
        c2 = self.get_p2_country()
        f1 = GRID_SLOTS[self.p1_slot_idx].get("flag_key")
        f2 = GRID_SLOTS[self.p2_slot_idx].get("flag_key")

        # 1. Priorizar selección del Jugador 1
        if f1 == "japan_up" or self.p1_slot_idx == 2:
            return "honda"
        if f1 == "usa" or self.p1_slot_idx == 1:
            # USA (el de arriba): Ken Stage
            return "ken"
        if f1 == "usa_low" or self.p1_slot_idx == 4:
            # USA (el de abajo): Guile Stage
            return "guile"
        if c1 == "ussr" or f1 == "ussr" or self.p1_char == "ussr":
            return "ussr"
        if c1 == "china" or f1 == "china" or self.p1_char == "china":
            return "china"
        if c1 == "india" or f1 == "india" or self.p1_char == "india":
            return "india"
        if c1 == "brazil" or f1 == "brazil" or self.p1_char == "gamaliel":
            return "brazil"

        # 2. Si P1 es Carloni (Japón defecto), verificar selección de P2 / CPU
        if f2 == "japan_up" or self.p2_slot_idx == 2:
            return "honda"
        if f2 == "usa" or self.p2_slot_idx == 1:
            # USA (el de arriba): Ken Stage
            return "ken"
        if f2 == "usa_low" or self.p2_slot_idx == 4:
            # USA (el de abajo): Guile Stage
            return "guile"
        if c2 == "ussr" or f2 == "ussr" or self.p2_char == "ussr":
            return "ussr"
        if c2 == "china" or f2 == "china" or self.p2_char == "china":
            return "china"
        if c2 == "india" or f2 == "india" or self.p2_char == "india":
            return "india"
        if c2 == "brazil" or f2 == "brazil" or self.p2_char == "gamaliel":
            return "brazil"

        return None

    def _init_map_surfaces(self):
        """Escala MAP.png y precalcula versiones a color y blanco/negro de las banderas sin artefactos."""
        bg_path = os.path.join("assets", "backgrounds", "MAP.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "backgrounds", "player select.png")
        if not os.path.exists(bg_path):
            return

        try:
            try:
                raw_color = pygame.image.load(bg_path).convert()
            except Exception:
                raw_color = pygame.image.load(bg_path)

            raw_w, raw_h = raw_color.get_size()
            sx = ARCADE_WIDTH / float(raw_w)
            sy = ARCADE_HEIGHT / float(raw_h)

            raw_bw = raw_color.copy()

            # 1. Desaturar con precisión a nivel de pixel en la imagen nativa (1450x1085)
            # Esto evita artefactos de bordes, sangrado en el terreno o corte en el océano
            primary_flag_keys = ["ussr", "china", "japan", "japan_up", "usa", "usa_low", "india", "brazil"]
            for flag_key in primary_flag_keys:
                if flag_key in RAW_FLAG_RECTS:
                    rx, ry, rw, rh = RAW_FLAG_RECTS[flag_key]
                    sub_raw_bw = raw_bw.subsurface((rx, ry, rw, rh))
                    arr = pygame.surfarray.pixels3d(sub_raw_bw)
                    gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.uint8)
                    del arr  # Desbloquear superficie antes del blit
                    gray_3d = np.stack([gray, gray, gray], axis=2)
                    gray_surf = pygame.surfarray.make_surface(gray_3d)
                    raw_bw.blit(gray_surf, (rx, ry))

            # 2. Escalar ambos fondos en formato arcade 4:3 (960x720) y centrarlos con laterales negros (1280x720)
            scaled_color_43 = pygame.transform.scale(raw_color, (ARCADE_WIDTH, ARCADE_HEIGHT))
            scaled_bw_43 = pygame.transform.scale(raw_bw, (ARCADE_WIDTH, ARCADE_HEIGHT))

            self.bg_color = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.bg_bw = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.bg_color.fill((0, 0, 0))
            self.bg_bw.fill((0, 0, 0))

            self.bg_color.blit(scaled_color_43, (PILLARBOX_OFFSET_X, 0))
            self.bg_bw.blit(scaled_bw_43, (PILLARBOX_OFFSET_X, 0))

            # 3. Extraer las banderas a color recortadas directamente del fondo escalado
            for flag_key in primary_flag_keys:
                if flag_key in RAW_FLAG_RECTS:
                    rx, ry, rw, rh = RAW_FLAG_RECTS[flag_key]
                    rect = pygame.Rect(PILLARBOX_OFFSET_X + round(rx * sx), round(ry * sy), round(rw * sx), round(rh * sy))
                    self.scaled_flag_rects[flag_key] = rect
                    self.color_flags[flag_key] = self.bg_color.subsurface(rect).copy()

            # Aliases de banderas para compatibilidad
            if "usa_low" in self.scaled_flag_rects:
                self.scaled_flag_rects["spain"] = self.scaled_flag_rects["usa_low"]
                self.color_flags["spain"] = self.color_flags["usa_low"]
            if "japan_up" in self.scaled_flag_rects:
                self.scaled_flag_rects["thailand"] = self.scaled_flag_rects["japan_up"]
                self.color_flags["thailand"] = self.color_flags["japan_up"]

            # Escalar regiones interactivas del mapa con el offset arcade 4:3
            for country_key, (rx, ry, rw, rh) in RAW_MAP_REGIONS.items():
                self.scaled_map_regions[country_key] = pygame.Rect(
                    PILLARBOX_OFFSET_X + round(rx * sx), round(ry * sy), round(rw * sx), round(rh * sy)
                )

        except Exception as e:
            print(f"[CharacterSelect] Error inicializando superficies de mapa: {e}")

    def _init_character_portraits(self):
        """Carga las fotos/retratos de gran tamaño de los luchadores y mini iconos para la cuadrícula."""
        portrait_dir = os.path.join("assets", "characters", "portraits")
        char_ids = ["carloni", "cavasso", "romero", "gamaliel", "sellanes", "china", "ussr", "india", "default"]

        for cid in char_ids:
            # Buscar primero arte personalizado en carpeta del personaje
            custom_path = os.path.join("assets", "characters", cid, "portrait.png")
            alt_path = os.path.join("assets", "characters", cid, "photo.png")
            cached_path = os.path.join(portrait_dir, f"{cid}.png")
            default_path = os.path.join(portrait_dir, "default.png")

            chosen_path = None
            for p in [custom_path, alt_path, cached_path, default_path]:
                if os.path.exists(p):
                    chosen_path = p
                    break

            if chosen_path:
                try:
                    try:
                        surf = pygame.image.load(chosen_path).convert_alpha()
                    except Exception:
                        surf = pygame.image.load(chosen_path)
                    # Escalar al tamaño arcade adecuado para la vista lateral (~260x340)
                    scaled = pygame.transform.scale(surf, (260, 340))
                    self.portraits[cid] = scaled
                except Exception as e:
                    print(f"[CharacterSelect] Error cargando retrato de {cid}: {e}")

        # Precomputar iconos para las 8 casillas de la cuadrícula
        self.grid_icons = {}
        for slot in GRID_SLOTS:
            cid = slot["char_id"]
            if cid not in self.grid_icons:
                p_surf = self.portraits.get(cid) or self.portraits.get("default")
                if p_surf:
                    gx, gy, gw, gh = slot["grid_rect"]
                    self.grid_icons[cid] = pygame.transform.smoothscale(p_surf, (gw, gh))

    def _init_country_audio(self):
        """Carga los efectos de audio del locutor para cada uno de los 8 países."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                self.audio_enabled = False
                return

        paises_dir = os.path.join("assets", "audio", "Sounds", "paises")
        countries = ["brazil", "china", "india", "japan", "spain", "thailand", "usa", "ussr"]
        
        for c in countries:
            file_path = os.path.join(paises_dir, f"{c}.mp3")
            if os.path.exists(file_path):
                try:
                    sound = pygame.mixer.Sound(file_path)
                    sound.set_volume(0.85)
                    self.country_sounds[c] = sound
                except Exception as e:
                    print(f"[CharacterSelect] Error cargando audio para {c}: {e}")

    def _play_country_audio(self, country_key):
        """Reproduce el audio del locutor para el país seleccionado una sola vez."""
        if not self.audio_enabled or not country_key:
            return
        sound = self.country_sounds.get(country_key)
        if sound:
            try:
                if self.country_voice_channel and self.country_voice_channel.get_busy():
                    self.country_voice_channel.stop()
                self.country_voice_channel = sound.play()
            except Exception as e:
                print(f"[CharacterSelect] Error reproduciendo voz de país {country_key}: {e}")

    def _on_p1_slot_changed(self):
        """Se ejecuta al cambiar de ranura P1: emite SFX de navegación y voz del país."""
        audio_manager.play_sfx("menu_navigate")
        country = self.get_p1_country()
        self._play_country_audio(country)
        self.last_spoken_country_p1 = country

    def _on_p2_slot_changed(self):
        """Se ejecuta al cambiar de ranura P2 en modo PVP."""
        audio_manager.play_sfx("menu_navigate")
        country = self.get_p2_country()
        self._play_country_audio(country)
        self.last_spoken_country_p2 = country

    def handle_input(self, event):
        """Maneja la navegación por teclado y selección por ratón para P1 y P2."""
        # 1. Movimiento del ratón (Hover sobre países en mapa o casillas de cuadrícula)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if not self.p1_confirmed:
                # Comprobar si el cursor del ratón pasa sobre un país en el mapa mundial
                for country_key, rect in self.scaled_map_regions.items():
                    if rect.collidepoint(mx, my):
                        slot_target = self.country_to_slot.get(country_key)
                        if slot_target is not None and slot_target != self.p1_slot_idx:
                            self.p1_slot_idx = slot_target
                            self._on_p1_slot_changed()
                        break

                # Comprobar si el cursor del ratón pasa sobre una casilla de la cuadrícula
                for idx, slot in enumerate(GRID_SLOTS):
                    r = pygame.Rect(slot["grid_rect"])
                    if r.collidepoint(mx, my):
                        if idx != self.p1_slot_idx:
                            self.p1_slot_idx = idx
                            self._on_p1_slot_changed()
                        break
            return None

        # 2. Clic del ratón para confirmar
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not self.p1_confirmed:
                for country_key, rect in self.scaled_map_regions.items():
                    if rect.collidepoint(mx, my):
                        slot_target = self.country_to_slot.get(country_key)
                        if slot_target is not None:
                            self.p1_slot_idx = slot_target
                        break
                for idx, slot in enumerate(GRID_SLOTS):
                    r = pygame.Rect(slot["grid_rect"])
                    if r.collidepoint(mx, my):
                        self.p1_slot_idx = idx
                        break

                if self.credits_p1 == 0 and self.credits_p2 == 0:
                    self.credits_p1 += 1
                    audio_manager.play_sfx("coin")

                self.p1_confirmed = True
                audio_manager.play_sfx("select")
                stage_id = self.get_selected_stage_id()
                if self.p2_slot_idx == self.p1_slot_idx:
                    self.p2_slot_idx = (self.p1_slot_idx + 1) % len(GRID_SLOTS)
                self.p2_confirmed = True
                return {
                    "action": "fight",
                    "action_alt": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                    "stage_id": stage_id,
                }
            return None

        # 3. Teclado
        if event.type == pygame.KEYDOWN:
            # Créditos arcade: 1 para Player 1, 2 para Player 2
            if event.key == pygame.K_1:
                self.credits_p1 += 1
                audio_manager.play_sfx("coin")
                return None
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.credits_p2 += 1
                self.game_mode = MODE_PVP
                audio_manager.play_sfx("coin")
                if self.p1_confirmed and self.p2_confirmed:
                    self.p2_confirmed = False
                    self.transition_timer = 0.0
                return None

            # Controles de Jugador 1
            if not self.p1_confirmed:
                prev_slot = self.p1_slot_idx
                if self.game_mode == MODE_PVAI or self.credits_p2 == 0:
                    if event.key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(GRID_SLOTS)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(GRID_SLOTS)

                    if self.p1_slot_idx != prev_slot:
                        self._on_p1_slot_changed()

                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_j, pygame.K_f):
                        if self.credits_p1 == 0 and self.credits_p2 == 0:
                            self.credits_p1 += 1
                            audio_manager.play_sfx("coin")

                        self.p1_confirmed = True
                        audio_manager.play_sfx("select")
                        if self.p2_slot_idx == self.p1_slot_idx:
                            self.p2_slot_idx = (self.p1_slot_idx + 1) % len(GRID_SLOTS)
                        self.p2_confirmed = True
                        stage_id = self.get_selected_stage_id()
                        return {
                            "action": "fight",
                            "action_alt": "vs",
                            "p1_char": self.p1_char,
                            "p2_char": self.p2_char,
                            "stage_id": stage_id,
                        }

                else:  # MODE_PVP (Ambos jugadores con créditos)
                    if event.key in (pygame.K_a, pygame.K_w):
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(GRID_SLOTS)
                    elif event.key in (pygame.K_d, pygame.K_s):
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(GRID_SLOTS)

                    if self.p1_slot_idx != prev_slot:
                        self._on_p1_slot_changed()

                    if event.key in (pygame.K_SPACE, pygame.K_j, pygame.K_f):
                        if self.credits_p1 == 0 and self.credits_p2 == 0:
                            self.credits_p1 += 1
                            audio_manager.play_sfx("coin")
                        self.p1_confirmed = True
                        audio_manager.play_sfx("select")
                        if self.p2_confirmed:
                            stage_id = self.get_selected_stage_id()
                            return {
                                "action": "fight",
                                "action_alt": "vs",
                                "p1_char": self.p1_char,
                                "p2_char": self.p2_char,
                                "stage_id": stage_id,
                            }

            # Controles de Jugador 2 (Sólo en modo PVP)
            if self.game_mode == MODE_PVP and not self.p2_confirmed:
                prev_p2 = self.p2_slot_idx
                if event.key in (pygame.K_LEFT, pygame.K_UP):
                    self.p2_slot_idx = (self.p2_slot_idx - 1) % len(GRID_SLOTS)
                elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                    self.p2_slot_idx = (self.p2_slot_idx + 1) % len(GRID_SLOTS)

                if self.p2_slot_idx != prev_p2:
                    self._on_p2_slot_changed()

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP1):
                    self.p2_confirmed = True
                    audio_manager.play_sfx("select")
                    if self.p1_confirmed:
                        stage_id = self.get_selected_stage_id()
                        return {
                            "action": "fight",
                            "action_alt": "vs",
                            "p1_char": self.p1_char,
                            "p2_char": self.p2_char,
                            "stage_id": stage_id,
                        }

            if self.p1_confirmed and self.p2_confirmed:
                stage_id = self.get_selected_stage_id()
                return {
                    "action": "fight",
                    "action_alt": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                    "stage_id": stage_id,
                }

        return None

    def update(self, dt=1.0 / FPS):
        """Actualiza animaciones de parpadeo y temporizadores de transición."""
        self.blink_timer += dt

        if self.p1_confirmed and self.p2_confirmed:
            self.transition_timer += dt
            if self.transition_timer >= 0.4:
                stage_id = self.get_selected_stage_id()
                return {
                    "action": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                    "stage_id": stage_id,
                }
        return None

    def draw(self, screen=None):
        """Renderiza la pantalla oficial de selección de personajes."""
        target = screen or self.screen
        if target is None:
            return

        # 1. Fondo del mapa mundial (con países no seleccionados en blanco y negro)
        if self.bg_bw:
            target.blit(self.bg_bw, (0, 0))
        else:
            target.fill(COLOR_BG)

        # 2. Restaurar en COLOR únicamente el país actualmente seleccionado
        p1_slot = GRID_SLOTS[self.p1_slot_idx]
        p2_slot = GRID_SLOTS[self.p2_slot_idx]
        p1_flag = p1_slot.get("flag_key", p1_slot["country"])
        p2_flag = p2_slot.get("flag_key", p2_slot["country"])

        # Bandera de P1 en color
        if p1_flag in self.color_flags and p1_flag in self.scaled_flag_rects:
            target.blit(self.color_flags[p1_flag], self.scaled_flag_rects[p1_flag].topleft)

        # Bandera de P2 en color (únicamente en modo PVP si es diferente a P1)
        if (self.game_mode == MODE_PVP or self.credits_p2 > 0) and p2_flag != p1_flag and p2_flag in self.color_flags and p2_flag in self.scaled_flag_rects:
            target.blit(self.color_flags[p2_flag], self.scaled_flag_rects[p2_flag].topleft)

        # 3. Dibujar soportes/marcos arcade (brackets) sobre las banderas de los países en el mapa
        is_blink_on = (int(self.blink_timer * 6) % 2 == 0)

        # Indicador P1 en el mapa
        if p1_flag in self.scaled_flag_rects:
            p1_flag_rect = self.scaled_flag_rects[p1_flag]
            p1_bracket_color = (60, 140, 255) if (not self.p1_confirmed or is_blink_on) else (50, 255, 50)
            self._draw_arcade_bracket(target, p1_flag_rect.inflate(14, 12), p1_bracket_color, tag="1P")

        # Indicador P2 en el mapa (sólo si P2 tiene créditos o es PVP)
        if (self.game_mode == MODE_PVP or self.credits_p2 > 0) and p2_flag in self.scaled_flag_rects:
            p2_flag_rect = self.scaled_flag_rects[p2_flag]
            p2_bracket_color = (255, 70, 70) if (not self.p2_confirmed or is_blink_on) else (50, 255, 50)
            p2_tag = "2P"
            offset_tag = 16 if p2_flag == p1_flag else 0
            self._draw_arcade_bracket(target, p2_flag_rect.inflate(18, 16), p2_bracket_color, tag=p2_tag, y_offset=offset_tag)

        # 4. Cuadrícula de 8 casillas (Bottom Grid vacía sin personajes) y marcos selectores
        for i, slot in enumerate(GRID_SLOTS):
            x, y, w, h = slot["grid_rect"]
            rect = pygame.Rect(x, y, w, h)

            # Selector de Jugador 1 (AZUL / VERDE al confirmar)
            if i == self.p1_slot_idx:
                c1 = (60, 140, 255) if (not self.p1_confirmed or is_blink_on) else (50, 255, 50)
                self._draw_arcade_bracket(target, rect.inflate(8, 8), c1, tag="1P")

            # Selector de Jugador 2 (ROJO / VERDE al confirmar) - sólo visible si P2 tiene créditos
            if i == self.p2_slot_idx and (self.game_mode == MODE_PVP or self.credits_p2 > 0):
                c2 = (255, 70, 70) if (not self.p2_confirmed or is_blink_on) else (50, 255, 50)
                self._draw_arcade_bracket(target, rect.inflate(14, 14), c2, tag="2P", y_offset=-18 if i == self.p1_slot_idx else 0)

        # 5. Banners arcade INSERT COIN en ambas esquinas superiores (P1 izquierda, P2 derecha)
        p1_center_x = PILLARBOX_OFFSET_X + 25 + 130
        p2_center_x = PILLARBOX_OFFSET_X + ARCADE_WIDTH - 25 - 130

        # Si Player 1 tiene 0 créditos, parpadea INSERT COIN a la izquierda
        if self.credits_p1 == 0 and is_blink_on:
            if self.arcade_font and self.arcade_font.loaded:
                self.arcade_font.render_to(target, (p1_center_x, 30), "INSERT COIN", scale=0.85, align="center")
            else:
                s_coin1 = self.font_header.render("INSERT COIN", True, (255, 80, 80))
                target.blit(s_coin1, (p1_center_x - s_coin1.get_width() // 2, 25))

        # Si Player 2 tiene 0 créditos en modo PVP, parpadea INSERT COIN a la derecha
        if self.game_mode == MODE_PVP and self.credits_p2 == 0 and is_blink_on:
            if self.arcade_font and self.arcade_font.loaded:
                self.arcade_font.render_to(target, (p2_center_x, 30), "INSERT COIN", scale=0.85, align="center")
            else:
                s_coin2 = self.font_header.render("INSERT COIN", True, (255, 80, 80))
                target.blit(s_coin2, (p2_center_x - s_coin2.get_width() // 2, 25))

        # 6 y 7. Los laterales y las casillas quedan completamente vacíos sin personajes ni fotos.

        # 8. Información de créditos arcade e indicador de modo en el pie de pantalla
        total_credits = max(1, self.credits_p1 + self.credits_p2)
        credit_txt = f"CREDIT  {total_credits:02d}"
        mode_txt = "SELECT STAGE"

        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(target, (PILLARBOX_OFFSET_X + ARCADE_WIDTH // 2, 678), mode_txt, scale=0.8, align="center")
            self.arcade_font.render_to(target, (PILLARBOX_OFFSET_X + ARCADE_WIDTH - 140, 678), credit_txt, scale=0.75, align="center")
        else:
            s_mode = self.font_small.render(mode_txt, True, (240, 200, 40))
            s_cred = self.font_small.render(credit_txt, True, COLOR_WHITE)
            target.blit(s_mode, (PILLARBOX_OFFSET_X + ARCADE_WIDTH // 2 - s_mode.get_width() // 2, 678))
            target.blit(s_cred, (PILLARBOX_OFFSET_X + ARCADE_WIDTH - 160, 678))

        # 9. Asegurar franjas negras laterales 4:3 (Pillarbox)
        if PILLARBOX_OFFSET_X > 0:
            pygame.draw.rect(target, (0, 0, 0), (0, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
            pygame.draw.rect(target, (0, 0, 0), (PILLARBOX_OFFSET_X + ARCADE_WIDTH, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))

    def _draw_player_portrait(self, screen, char_id, is_player_1=True):
        """Espacio lateral dejado vacío sin fotos ni nombres de personajes."""
        pass

    def _draw_arcade_bracket(self, target, rect, color, tag="1P", y_offset=0):
        """Dibuja esquinas de selección arcade (brackets en 4 esquinas) y etiqueta de jugador."""
        x, y, w, h = rect
        lw = min(14, w // 4)
        th = 3

        # Esquina superior izquierda
        pygame.draw.line(target, color, (x, y), (x + lw, y), th)
        pygame.draw.line(target, color, (x, y), (x, y + lw), th)

        # Esquina superior derecha
        pygame.draw.line(target, color, (x + w, y), (x + w - lw, y), th)
        pygame.draw.line(target, color, (x + w, y), (x + w, y + lw), th)

        # Esquina inferior izquierda
        pygame.draw.line(target, color, (x, y + h), (x + lw, y + h), th)
        pygame.draw.line(target, color, (x, y + h), (x, y + h - lw), th)

        # Esquina inferior derecha
        pygame.draw.line(target, color, (x + w, y + h), (x + w - lw, y + h), th)
        pygame.draw.line(target, color, (x + w, y + h), (x + w, y + h - lw), th)

        # Etiqueta "1P" / "2P" / "CPU"
        if tag:
            lbl = self.font_small.render(tag, True, color)
            target.blit(lbl, (x + w // 2 - lbl.get_width() // 2, y - 18 + y_offset))
