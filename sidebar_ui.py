"""Barra lateral compartida para todas las pantallas de C.C.I. System."""
from __future__ import annotations

import unicodedata
from pathlib import Path

import pygame

LOGICAL_W, LOGICAL_H = 1280, 720
SIDEBAR_W, SIDEBAR_H = 260, 580
NAV_ROW_TOP = 122
NAV_ROW_STEP = 45
NAV_ROW_HEIGHT = 36

ENTRIES = (
    ("INICIO", "home", "MENU"),
    ("JUEGOS", "library", "LIBRARY"),
    ("GRUPOS", "groups", "GROUPS"),
    ("PERFIL", "profile", "PROFILE"),
    ("LOGROS", "achievements", "ACHIEVEMENTS"),
    ("CONFIGURACIÓN", "settings", "SETTINGS"),
    ("APAGAR", "quit", "QUIT"),
)


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def load_sidebar() -> pygame.Surface:
    """Recorta la marca y el marco de la pantalla base de logros indicada."""
    root = Path(__file__).resolve().parent
    folder = root / "pantallas"
    prefix = _normalized("Interfaz futurista de logros vacía")
    path = next(
        (
            candidate for candidate in folder.iterdir()
            if candidate.is_file()
            and candidate.suffix.lower() == ".png"
            and _normalized(candidate.name).startswith(prefix)
        ),
        None,
    )
    if path is None:
        surface = pygame.Surface((SIDEBAR_W, SIDEBAR_H))
        surface.fill((7, 8, 10))
        return surface
    try:
        source = pygame.image.load(str(path)).convert()
        scaled = pygame.transform.smoothscale(source, (LOGICAL_W, LOGICAL_H))
        return scaled.subsurface(pygame.Rect(0, 0, SIDEBAR_W, SIDEBAR_H)).copy()
    except (pygame.error, OSError) as exc:
        print(f"[CCI] No se pudo cargar la barra de logros: {exc}")
        surface = pygame.Surface((SIDEBAR_W, SIDEBAR_H))
        surface.fill((7, 8, 10))
        return surface


def make_sidebar_font() -> pygame.font.Font:
    """Fuente sans serif de alto contraste, más legible que las fuentes pixel pequeñas."""
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        return pygame.font.SysFont("Arial", 17, bold=True)
    except Exception:
        return pygame.font.Font(None, 17)


def draw_sidebar(target: pygame.Surface, base: pygame.Surface, active_page: str, font: pygame.font.Font) -> None:
    """Pinta el sidebar de logros y los mismos rótulos en todas las vistas."""
    if base is not None:
        if active_page in ("community", "groups_community"):
            # En la vista de comunidad la columna de iconos de servidor empieza en x=174;
            # la base limpia ya contiene el logo C.C.I. SYSTEM completo arriba.
            target.blit(base, (0, 90), area=pygame.Rect(0, 90, 170, SIDEBAR_H - 90))
        elif active_page == "groups":
            # En la vista de grupos el divisor vertical está en x=231 y el contenedor en x=243.
            target.blit(base, (0, 90), area=pygame.Rect(0, 90, 228, SIDEBAR_H - 90))
        else:
            target.blit(base, (0, 0))

    # El asset base muestra LOGROS activo; se limpia el área de opciones para
    # renderizar el estado activo correcto de cada pantalla.
    is_comm = active_page in ("community", "groups_community")
    clear_w = 126 if is_comm else (184 if active_page == "groups" else 196)
    active_w = 124 if is_comm else (182 if active_page == "groups" else 194)
    pygame.draw.rect(target, (8, 9, 11), pygame.Rect(42, 117, clear_w, 325))
    for index, (label, page, _destination) in enumerate(ENTRIES):
        top = NAV_ROW_TOP + index * NAV_ROW_STEP
        active = (active_page == page) or (is_comm and page == "groups")
        if active:
            pygame.draw.rect(target, (27, 28, 31), pygame.Rect(43, top, active_w, NAV_ROW_HEIGHT))
            pygame.draw.rect(target, (242, 244, 247), pygame.Rect(43, top + 2, 7, NAV_ROW_HEIGHT - 4))
        color = (246, 247, 249) if active else (180, 183, 188)
        text = font.render(label, True, color)
        if is_comm and text.get_width() > 104:
            text = pygame.transform.smoothscale(text, (104, text.get_height()))
        target.blit(text, text.get_rect(midleft=(65, top + NAV_ROW_HEIGHT // 2)))


def sidebar_destination(pos: tuple[int, int], max_x: int = SIDEBAR_W) -> str | None:
    """Convierte un clic dentro de una fila lateral en un destino de estado."""
    x, y = pos
    if not (42 <= x < max_x):
        return None
    for index, (_label, _page, destination) in enumerate(ENTRIES):
        top = NAV_ROW_TOP + index * NAV_ROW_STEP
        if top - 2 <= y < top + NAV_ROW_HEIGHT + 2:
            return destination
    return None
