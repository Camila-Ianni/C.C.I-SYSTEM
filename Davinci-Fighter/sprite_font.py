"""
sprite_font.py - Sistema genérico de SpriteFont para Da Vinci Fighters
=====================================================================
Permite renderizar texto a partir de una sprite sheet sin modificar el asset original.

Diseñado para soportar múltiples tipografías de interfaz de forma independiente:
- BootFont (exclusivo para la pantalla inicial de diagnóstico/boot).
- En el futuro: HUDFont, MenuFont, FightFont, etc.
"""

import os
import pygame

class SpriteFont:
    """
    Sistema genérico para renderizar texto a partir de una sprite sheet de caracteres.
    Extrae los glifos en memoria sin modificar la imagen original.
    """
    def __init__(self, image_path, glyphs_dict, space_width=None, default_advance=None, colorkey=(0, 0, 0)):
        self.image_path = image_path
        self.glyphs_dict = glyphs_dict or {}
        self.colorkey = colorkey
        self.sheet = None
        self.glyphs = {}
        self.missing_reported = set()
        self._scale_cache = {}

        # Determinar dimensiones base
        if glyphs_dict:
            first_glyph = next(iter(glyphs_dict.values()))
            self.base_width = first_glyph[2]
            self.base_height = first_glyph[3]
        else:
            self.base_width = 32
            self.base_height = 32

        self.space_width = space_width if space_width is not None else self.base_width
        self.default_advance = default_advance if default_advance is not None else self.base_width

        # Cargar sprite sheet y extraer glifos
        self._load_sheet()

    def _load_sheet(self):
        """Carga la sprite sheet una sola vez y extrae los subsurfaces de cada carácter."""
        if not self.image_path or not os.path.exists(self.image_path):
            print(f"[SpriteFont] Advertencia: Archivo de fuente no encontrado en '{self.image_path}'")
            return

        try:
            self.sheet = pygame.image.load(self.image_path)
            # Extraer subsurfaces para cada carácter
            for ch, (x, y, w, h) in self.glyphs_dict.items():
                if x + w <= self.sheet.get_width() and y + h <= self.sheet.get_height():
                    sub = self.sheet.subsurface(pygame.Rect(x, y, w, h)).convert_alpha()
                    # Si el colorkey es negro puro, limpiar ruido JPEG en el glifo
                    if self.colorkey == (0, 0, 0):
                        w_sub, h_sub = sub.get_size()
                        for gy in range(h_sub):
                            for gx in range(w_sub):
                                r, g, b, a = sub.get_at((gx, gy))
                                if r < 40 and g < 40 and b < 40:
                                    sub.set_at((gx, gy), (0, 0, 0, 0))
                    elif self.colorkey is not None:
                        sub.set_colorkey(self.colorkey)
                    self.glyphs[ch] = sub
                else:
                    print(f"[SpriteFont] Coordenadas fuera de rango para el glifo '{ch}': ({x}, {y}, {w}, {h})")
        except Exception as e:
            print(f"[SpriteFont] Error cargando sprite sheet '{self.image_path}': {e}")

    def _get_scaled_glyph(self, ch, scale):
        """Retorna el glifo escalado utilizando caché en memoria."""
        if ch not in self.glyphs:
            return None

        cache_key = (ch, scale)
        if cache_key in self._scale_cache:
            return self._scale_cache[cache_key]

        orig_glyph = self.glyphs[ch]
        if abs(scale - 1.0) < 0.01:
            scaled = orig_glyph
        else:
            w = max(1, int(orig_glyph.get_width() * scale))
            h = max(1, int(orig_glyph.get_height() * scale))
            scaled = pygame.transform.smoothscale(orig_glyph, (w, h)) if scale < 1.0 else pygame.transform.scale(orig_glyph, (w, h))

        self._scale_cache[cache_key] = scaled
        return scaled

    def get_text_size(self, text, scale=1.0, letter_spacing=0, line_spacing=0):
        """Calcula el ancho y alto total que ocupará una cadena de texto."""
        if not text:
            return (0, 0)

        lines = text.split("\n")
        max_w = 0
        total_h = 0
        line_h = int(self.base_height * scale)

        for line_idx, line in enumerate(lines):
            curr_w = 0
            for ch in line:
                ch_key = ch.upper()
                if ch == " ":
                    curr_w += int(self.space_width * scale) + letter_spacing
                elif ch_key in self.glyphs_dict:
                    w = self.glyphs_dict[ch_key][2]
                    curr_w += int(w * scale) + letter_spacing
                else:
                    curr_w += int(self.default_advance * scale) + letter_spacing

            if curr_w > 0:
                curr_w -= letter_spacing
            if curr_w > max_w:
                max_w = curr_w

            total_h += line_h
            if line_idx < len(lines) - 1:
                total_h += line_spacing

        return (max_w, total_h)

    def draw_text(self, surface, text, x, y, scale=1.0, letter_spacing=0, line_spacing=0):
        """
        Dibuja una cadena de texto en la superficie indicada.
        - Avanza horizontalmente según el ancho real de cada carácter.
        - Respeta los espacios sin requerir un sprite.
        - Maneja caracteres faltantes sin crashear.
        """
        if not text or surface is None:
            return pygame.Rect(x, y, 0, 0)

        start_x = x
        curr_x = x
        curr_y = y
        line_h = int(self.base_height * scale)
        max_x = curr_x

        for ch in text:
            if ch == "\n":
                if curr_x > max_x:
                    max_x = curr_x
                curr_x = start_x
                curr_y += line_h + line_spacing
                continue

            if ch == " ":
                curr_x += int(self.space_width * scale) + letter_spacing
                continue

            # Búsqueda exacta o fallback a mayúscula
            ch_key = ch if ch in self.glyphs else ch.upper()
            if ch_key in self.glyphs:
                glyph = self._get_scaled_glyph(ch_key, scale)
                if glyph:
                    surface.blit(glyph, (curr_x, curr_y))
                    curr_x += glyph.get_width() + letter_spacing
            else:
                # Manejo de glifo faltante: reportar una sola vez sin crashear
                if ch not in self.missing_reported:
                    self.missing_reported.add(ch)
                    print(f"[SpriteFont] Missing glyph: {repr(ch)}")
                curr_x += int(self.default_advance * scale) + letter_spacing

        if curr_x > max_x:
            max_x = curr_x

        total_w = max_x - start_x
        total_h = (curr_y + line_h) - y
        return pygame.Rect(start_x, y, total_w, total_h)

    def render(self, text, scale=1.0, letter_spacing=0, line_spacing=0):
        """Genera y retorna una nueva superficie de Pygame con el texto renderizado."""
        w, h = self.get_text_size(text, scale=scale, letter_spacing=letter_spacing, line_spacing=line_spacing)
        w = max(1, w)
        h = max(1, h)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        self.draw_text(surf, text, 0, 0, scale=scale, letter_spacing=letter_spacing, line_spacing=line_spacing)
        return surf


# =============================================================================
# BOOT FONT - Tipografía exclusiva para la pantalla inicial de diagnóstico/boot
# =============================================================================

# Coordenadas exactas obtenidas del análisis visual del asset Diagnostico Font.jpg / boot_font.png
BOOT_GLYPHS = {
    "S": (660, 500, 52, 66),
    "C": (712, 500, 52, 66),
    "R": (764, 500, 52, 66),
    "1": (866, 500, 52, 66),
    "2": (866, 566, 52, 66),
    "3": (866, 632, 52, 66),
    "A": (1069, 500, 52, 66),
    "M": (1121, 500, 52, 66),
    "O": (1220, 500, 52, 66),
    "K": (1272, 500, 52, 66),
    "B": (712, 698, 52, 66),
    "J": (764, 698, 52, 66),
    "E": (816, 698, 52, 66),
    "T": (916, 698, 52, 66),
    "W": (660, 764, 52, 66),
}


class BootFont(SpriteFont):
    """
    Fuente sprite específica para la pantalla de diagnóstico y arranque (Boot).
    """
    _instance = None

    def __init__(self, asset_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Rutas válidas de búsqueda para el asset original
        candidates = [
            asset_path,
            os.path.join(base_dir, "assets", "ui", "fonts", "boot", "boot_font.png"),
            os.path.join(base_dir, "assets", "fonts", "Diagnostico Font.jpg"),
            os.path.join(base_dir, "assets", "fonts", "diagnostico fonts.jpg"),
        ]
        
        chosen_path = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                chosen_path = cand
                break

        super().__init__(
            image_path=chosen_path,
            glyphs_dict=BOOT_GLYPHS,
            space_width=52,
            default_advance=52,
            colorkey=(0, 0, 0)
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BootFont()
        return cls._instance


# Instancia singleton accesible para la pantalla de boot
boot_font = None

def get_boot_font():
    global boot_font
    if boot_font is None:
        boot_font = BootFont.get_instance()
    return boot_font


# =============================================================================
# WARNING FONT - Tipografía exclusiva para la pantalla de advertencia legal (Warning)
# =============================================================================

WARNING_GLYPHS = {
    # Fila 1: A-M (alineadas a baseline)
    'A': (339, 65, 65, 66),
    'B': (478, 65, 58, 66),
    'C': (606, 65, 56, 66),
    'D': (729, 65, 58, 66),
    'E': (847, 65, 58, 66),
    'F': (966, 65, 57, 66),
    'G': (1076, 65, 54, 66),
    'H': (1188, 65, 61, 66),
    'I': (1315, 65, 36, 66),
    'J': (1410, 65, 59, 66),
    'K': (1532, 65, 63, 66),
    'L': (1658, 65, 56, 66),
    'M': (1778, 65, 63, 66),
    # Fila 2: N-Z (alineadas a baseline)
    'N': (341, 165, 62, 66),
    'O': (478, 165, 57, 66),
    'P': (606, 165, 57, 66),
    'Q': (731, 165, 60, 66),
    'R': (846, 165, 60, 66),
    'S': (965, 165, 55, 66),
    'T': (1070, 165, 64, 66),
    'U': (1182, 165, 66, 66),
    'V': (1302, 165, 63, 66),
    'W': (1413, 165, 69, 66),
    'X': (1537, 165, 63, 66),
    'Y': (1658, 165, 62, 66),
    'Z': (1777, 165, 61, 66),
    # Fila 3: a-m (alineadas a baseline)
    'a': (352, 279, 52, 66),
    'b': (475, 279, 50, 66),
    'c': (599, 279, 49, 66),
    'd': (720, 279, 55, 66),
    'e': (841, 279, 50, 66),
    'f': (966, 279, 47, 66),
    'g': (1083, 279, 49, 66),
    'h': (1204, 279, 49, 66),
    'i': (1333, 279, 21, 66),
    'j': (1422, 279, 46, 66),
    'k': (1549, 279, 52, 66),
    'l': (1680, 279, 21, 66),
    'm': (1776, 279, 56, 66),
    # Fila 4: n-z (alineadas a baseline)
    'n': (355, 369, 49, 66),
    'o': (475, 369, 50, 66),
    'p': (596, 369, 49, 66),
    'q': (713, 369, 56, 66),
    'r': (840, 369, 40, 66),
    's': (957, 369, 49, 66),
    't': (1077, 369, 49, 66),
    'u': (1196, 369, 51, 66),
    'v': (1314, 369, 52, 66),
    'w': (1430, 369, 57, 66),
    'x': (1549, 369, 53, 66),
    'y': (1664, 369, 47, 66),
    'z': (1781, 369, 46, 66),
    # Fila 5: 0-9 (alineadas a baseline)
    '0': (529, 480, 52, 66),
    '1': (648, 480, 34, 66),
    '2': (747, 480, 55, 66),
    '3': (858, 480, 55, 66),
    '4': (972, 480, 55, 66),
    '5': (1087, 480, 54, 66),
    '6': (1201, 480, 52, 66),
    '7': (1314, 480, 54, 66),
    '8': (1429, 480, 53, 66),
    '9': (1540, 480, 55, 66),
    # Fila 6: Símbolos (alineadas a baseline)
    '!': (72, 565, 20, 66),
    '?': (127, 565, 52, 66),
    '.': (201, 565, 20, 66),
    ',': (260, 565, 19, 66),
    ':': (318, 565, 18, 66),
    ';': (379, 565, 18, 66),
    "'": (435, 565, 19, 66),
    '"': (488, 565, 41, 66),
    '-': (563, 565, 39, 66),
    '_': (628, 565, 45, 66),
    '(': (704, 565, 30, 66),
    ')': (781, 565, 32, 66),
    '[': (859, 565, 28, 66),
    ']': (926, 565, 26, 66),
    '{': (990, 565, 33, 66),
    '}': (1062, 565, 33, 66),
    '/': (1127, 565, 47, 66),
    '\\': (1208, 565, 47, 66),
    '@': (1295, 565, 65, 66),
    '#': (1395, 565, 59, 66),
    '$': (1488, 565, 52, 66),
    '%': (1574, 565, 62, 66),
    '&': (1669, 565, 56, 66),
    '*': (1756, 565, 47, 66),
    '+': (1835, 565, 49, 66),
    '=': (1908, 565, 50, 66),
    '<': (1996, 565, 38, 66),
    '>': (2063, 565, 38, 66),
}


class WarningFont(SpriteFont):
    """
    Fuente sprite específica para la pantalla de advertencia legal (Warning).
    Extrae los glifos de Warning font.PNG en memoria.
    """
    _instance = None

    def __init__(self, asset_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        candidates = [
            asset_path,
            os.path.join(base_dir, "assets", "fonts", "Warning font.PNG"),
            os.path.join(base_dir, "assets", "fonts", "Warning font.png"),
            os.path.join(base_dir, "assets", "fonts", "warning font.png"),
            os.path.join(base_dir, "assets", "ui", "fonts", "warning", "warning_font.png"),
        ]
        
        chosen_path = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                chosen_path = cand
                break

        super().__init__(
            image_path=chosen_path,
            glyphs_dict=WARNING_GLYPHS,
            space_width=48,
            default_advance=48,
            colorkey=(0, 0, 0)
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = WarningFont()
        return cls._instance


# Instancia singleton accesible para la pantalla de warning
warning_font = None

def get_warning_font():
    global warning_font
    if warning_font is None:
        warning_font = WarningFont.get_instance()
    return warning_font

