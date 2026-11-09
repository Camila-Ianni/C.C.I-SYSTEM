"""Barra lateral compartida para todas las pantallas de C.C.I. System."""
from __future__ import annotations

import unicodedata
from pathlib import Path

import pygame

LOGICAL_W, LOGICAL_H = 1280, 720
SIDEBAR_W, SIDEBAR_H = 190, 720
NAV_ROW_TOP = 148
NAV_ROW_STEP = 60
NAV_ROW_HEIGHT = 40

ENTRIES = (
    ("INICIO", "home", "MENU"),
    ("JUEGOS", "library", "LIBRARY"),
    ("GRUPOS", "groups", "GROUPS"),
    ("PERFIL", "profile", "PROFILE"),
    ("LOGROS", "achievements", "ACHIEVEMENTS"),
    ("CONFIGURACIÓN", "settings", "SETTINGS"),
    ("APAGAR", "quit", "QUIT"),
)

_SIDEBAR_CACHE: dict[str, pygame.Surface] = {}


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def get_perfect_sidebar(page: str) -> pygame.Surface | None:
    norm = "home" if page in ("home", "menu") else ("groups" if page in ("groups", "community", "groups_community") else page)
    if norm not in _SIDEBAR_CACHE:
        root = Path(__file__).resolve().parent
        path = root / "assets_ui" / "achievements" / f"sidebar_perfect_{norm}.png"
        if path.exists():
            try:
                _SIDEBAR_CACHE[norm] = pygame.image.load(str(path)).convert_alpha()
            except Exception:
                pass
    return _SIDEBAR_CACHE.get(norm)


def load_sidebar() -> pygame.Surface:
    """Carga la barra lateral unificada C.C.I SYSTEM."""
    root = Path(__file__).resolve().parent
    path = root / "assets_ui" / "achievements" / "sidebar_perfect_achievements.png"
    if path.exists():
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except Exception:
            pass
    surface = pygame.Surface((SIDEBAR_W, SIDEBAR_H))
    surface.fill((11, 12, 14))
    return surface


def make_sidebar_font() -> pygame.font.Font:
    """Fuente sans serif de alto contraste."""
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        return pygame.font.SysFont("Arial", 14, bold=True)
    except Exception:
        return pygame.font.Font(None, 14)


def draw_sidebar(target: pygame.Surface, base: pygame.Surface, active_page: str, font: pygame.font.Font) -> None:
    """Pinta la barra lateral unificada C.C.I SYSTEM en todas las pantallas."""
    perfect = get_perfect_sidebar(active_page)
    if perfect is not None:
        if active_page in ("community", "groups_community"):
            target.blit(perfect, (0, 0), area=pygame.Rect(0, 0, 172, 720))
        else:
            target.blit(perfect, (0, 0))
        return

    if base is not None:
        target.blit(base, (0, 0))


def sidebar_destination(pos: tuple[int, int], max_x: int = 190) -> str | None:
    """Convierte un clic dentro de una fila lateral en un destino de estado."""
    x, y = pos
    if not (18 <= x < max_x):
        return None
    for index, (_label, _page, destination) in enumerate(ENTRIES):
        top = NAV_ROW_TOP + index * NAV_ROW_STEP
        if top - 4 <= y < top + NAV_ROW_HEIGHT + 6:
            return destination
    return None
