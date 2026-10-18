"""Barra lateral compartida para todas las pantallas de C.C.I. System."""
from __future__ import annotations

import unicodedata
from pathlib import Path

import pygame

LOGICAL_W, LOGICAL_H = 1280, 720
SIDEBAR_W, SIDEBAR_H = 260, 580
NAV_ROW_TOP = 120
NAV_ROW_STEP = 44
NAV_ROW_HEIGHT = 37

ENTRIES = (
    ("INICIO", "home", "MENU"),
    ("JUEGOS", "library", "LIBRARY"),
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
    return pygame.font.SysFont("Arial", 17, bold=True)


def draw_sidebar(target: pygame.Surface, base: pygame.Surface, active_page: str, font: pygame.font.Font) -> None:
    """Pinta el sidebar de logros y los mismos rótulos en todas las vistas."""
    if base is not None:
        target.blit(base, (0, 0))

    # El asset base muestra LOGROS activo; se limpia el área de opciones para
    # renderizar el estado activo correcto de cada pantalla.
    pygame.draw.rect(target, (8, 9, 11), pygame.Rect(42, 117, 196, 288))
    for index, (label, page, _destination) in enumerate(ENTRIES):
        top = NAV_ROW_TOP + index * NAV_ROW_STEP
        active = active_page == page
        if active:
            pygame.draw.rect(target, (27, 28, 31), pygame.Rect(43, top, 194, NAV_ROW_HEIGHT))
            pygame.draw.rect(target, (242, 244, 247), pygame.Rect(43, top + 2, 7, NAV_ROW_HEIGHT - 4))
        color = (246, 247, 249) if active else (180, 183, 188)
        text = font.render(label, True, color)
        target.blit(text, text.get_rect(midleft=(65, top + NAV_ROW_HEIGHT // 2)))


def sidebar_destination(pos: tuple[int, int]) -> str | None:
    """Convierte un clic dentro de una fila lateral en un destino de estado."""
    x, y = pos
    if not (42 <= x < SIDEBAR_W):
        return None
    for index, (_label, _page, destination) in enumerate(ENTRIES):
        top = NAV_ROW_TOP + index * NAV_ROW_STEP
        if top - 2 <= y < top + NAV_ROW_HEIGHT + 2:
            return destination
    return None
