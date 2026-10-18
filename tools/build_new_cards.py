"""
Recorta las 5 tarjetas nuevas del carrusel desde "Selección retro de juegos pixel art.png"
y las deja en assets_cards/<key>_clean.png (RGBA, fondo exterior transparente),
con el mismo tamaño que el resto de las tarjetas (1109x282).

Uso: ./.venv/bin/python tools/build_new_cards.py
"""
import os

import numpy as np
import pygame

pygame.init()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Selección retro de juegos pixel art.png")
OUT = os.path.join(ROOT, "assets_cards")
CARD_SIZE = (1109, 282)
BG_THRESH = 235

# (clave, rect aproximado de busqueda x1, y1, x2, y2) en la imagen de 1536x1024
CARDS = [
    ("minecraft", (20, 140, 770, 385)),
    ("flappy", (765, 140, 1520, 385)),
    ("dino", (20, 390, 770, 630)),
    ("ghostbusters", (765, 390, 1520, 630)),
    ("cyberpunk", (320, 635, 1220, 880)),
]


def outside_background(rgb):
    """Fondo blanco conectado al borde de la imagen -> True."""
    h, w, _ = rgb.shape
    white = rgb.min(axis=2) >= BG_THRESH
    surf = pygame.Surface((w, h))
    arr = np.zeros((w, h, 3), dtype=np.uint8)
    arr[white.T] = 255
    pygame.surfarray.blit_array(surf, arr)
    mask = pygame.mask.from_threshold(surf, (255, 255, 255), (1, 1, 1, 255))
    bg = pygame.mask.Mask((w, h))
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if white[y, x]:
            bg.draw(mask.connected_component((x, y)), (0, 0))
    out = pygame.surfarray.array3d(bg.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0)))
    return out[:, :, 0].T > 0


def main():
    sheet = pygame.image.load(SRC)
    for key, (x1, y1, x2, y2) in CARDS:
        crop = sheet.subsurface((x1, y1, x2 - x1, y2 - y1)).copy()
        rgb = pygame.surfarray.array3d(crop).transpose(1, 0, 2).astype(np.int16)
        bg = outside_background(rgb)

        card = pygame.Surface(crop.get_size(), pygame.SRCALPHA)
        card.blit(crop, (0, 0))
        alpha = np.where(bg, 0, 255).astype(np.uint8)
        # Suaviza 1px del borde para evitar halo blanco
        edge = np.zeros_like(bg)
        edge[1:, :] |= bg[:-1, :]
        edge[:-1, :] |= bg[1:, :]
        edge[:, 1:] |= bg[:, :-1]
        edge[:, :-1] |= bg[:, 1:]
        light = rgb.min(axis=2)
        soft = np.clip((BG_THRESH - light) / 90.0, 0, 1) * 255
        alpha = np.where(edge & ~bg, np.minimum(255, soft), alpha).astype(np.uint8)
        pa = pygame.surfarray.pixels_alpha(card)
        pa[:, :] = alpha.T
        del pa

        rects = pygame.mask.from_surface(card, 20).get_bounding_rects()
        box = rects[0].unionall(rects[1:])
        tight = card.subsurface(box).copy()
        final = pygame.transform.smoothscale(tight, CARD_SIZE)
        for name in (f"{key}_clean.png", f"{key}.png"):
            pygame.image.save(final, os.path.join(OUT, name))
        print(f"{key}: recorte {box.size} -> {CARD_SIZE}")


if __name__ == "__main__":
    main()
