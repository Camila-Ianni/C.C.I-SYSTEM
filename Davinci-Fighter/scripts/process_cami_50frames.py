"""
Procesa las hojas de sprites de CAMI (50 frames por accion) y genera hojas
horizontales listas para el juego en assets/characters/cami/<accion>.png.

- Detecta automaticamente cada fotograma (segmentacion por bloques), por lo que
  tolera layouts irregulares (titulos, filas con distinta cantidad de frames,
  frames superpuestos).
- Elimina el fondo blanco con flood-fill desde los bordes (preserva blancos
  internos como ojos o hebillas) y suaviza el borde para evitar halos blancos.
- Escala uniforme por hoja (el personaje no "cambia de tamano" entre frames)
  y pies apoyados en la base de cada celda.

Uso:  ./.venv/bin/python Davinci-Fighter/scripts/process_cami_50frames.py
"""
import os
import numpy as np
import pygame

pygame.init()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "assets", "CAMI")
OUT_DIR = os.path.join(BASE, "assets", "characters", "cami")
DEBUG_DIR = os.path.join(BASE, "scratch_crop", "debug_50")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

FRAME_W = 320          # celda ancha para que patadas/efectos no se recorten
FRAME_H = 260
CHAR_H = 240           # altura del personaje de pie dentro de la celda
TOTAL_FRAMES = 50
BG_THRESH = 228        # min(r,g,b) >= esto se considera fondo blanco


def to_rgb_array(surface):
    return pygame.surfarray.array3d(surface).transpose(1, 0, 2).astype(np.int16)  # (h, w, 3)


def content_mask(rgb):
    return rgb.min(axis=2) < BG_THRESH


def find_bands(mask, expected_rows):
    """Bandas horizontales con contenido; devuelve las `expected_rows` mas altas (filas de luchadores)."""
    h, w = mask.shape
    x1, x2 = int(w * 0.22), int(w * 0.98)  # evita el titulo de la esquina superior izquierda
    proj = mask[:, x1:x2].sum(axis=1)
    bands, start = [], None
    for y in range(h):
        if proj[y] > 3 and start is None:
            start = y
        elif proj[y] <= 3 and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, h))
    # Dividir bandas fusionadas (dos filas unidas por polvo/estelas) en el punto de menor tinta
    for _ in range(3):
        tall = sorted(b[1] - b[0] for b in bands if b[1] - b[0] > 40)
        if not tall:
            break
        med = tall[len(tall) // 2]
        new = []
        for b0, b1 in bands:
            if b1 - b0 > med * 1.6:
                lo, hi = b0 + int((b1 - b0) * 0.3), b0 + int((b1 - b0) * 0.7)
                cut = lo + int(np.argmin(proj[lo:hi]))
                new += [(b0, cut), (cut + 1, b1)]
            else:
                new.append((b0, b1))
        bands = new
    bands = sorted(bands, key=lambda b: b[1] - b[0], reverse=True)[:expected_rows]
    return sorted(bands)


def find_segments(mask, y1, y2, rgb=None):
    """Segmenta una banda en luchadores individuales por huecos en la proyeccion vertical."""
    band = mask[y1:y2]
    bh = y2 - y1
    proj = band.sum(axis=0)
    segs, start = [], None
    for x in range(len(proj)):
        if proj[x] > 0 and start is None:
            start = x
        elif proj[x] == 0 and start is not None:
            segs.append([start, x])
            start = None
    if start is not None:
        segs.append([start, len(proj)])

    # Unir fragmentos separados por huecos pequenos (mechones de pelo, chispas)
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 10:
            merged[-1][1] = s[1]
        else:
            merged.append(s)

    # Descartar texto (titulos/numeros): poca altura o sin color (el texto es gris/negro puro)
    result = []
    for sx1, sx2 in merged:
        sub = band[:, sx1:sx2]
        rows = np.where(sub.any(axis=1))[0]
        if len(rows) == 0:
            continue
        extent = rows[-1] - rows[0]
        if extent < bh * 0.35 or (sx2 - sx1) < 25:
            continue
        if rgb is not None:
            px = rgb[y1:y2, sx1:sx2][sub]
            chroma = (px.max(axis=1) - px.min(axis=1)) > 35
            if chroma.mean() < 0.03:
                continue
        result.append((sx1, sx2))
    return result


def split_wide(segments, med, sheet_w=None, cols=10, band_mask=None):
    """Separa luchadores pegados (segmento mucho mas ancho que la mediana global).
    Los cortes se ubican en la columna con menos tinta cerca de cada limite esperado."""
    proj = band_mask.sum(axis=0) if band_mask is not None else None
    final = []
    for sx1, sx2 in segments:
        if sheet_w and (sx2 - sx1) > sheet_w * 0.5:
            # Fila entera fusionada (p.ej. patadas extendidas): usar el paso de columna esperado
            k = max(2, int(round((sx2 - sx1) / (sheet_w / float(cols)))))
        else:
            k = int(round((sx2 - sx1) / float(med)))
        if k >= 2 and (sx2 - sx1) > med * 1.4:
            step = (sx2 - sx1) / float(k)
            cuts = [sx1]
            for i in range(1, k):
                ideal = int(sx1 + i * step)
                if proj is not None:
                    r = int(step * 0.3)
                    lo, hi = max(cuts[-1] + 10, ideal - r), min(sx2 - 10, ideal + r)
                    ideal = lo + int(np.argmin(proj[lo:hi])) if hi > lo else ideal
                cuts.append(ideal)
            cuts.append(sx2)
            final += [(cuts[i], cuts[i + 1]) for i in range(k)]
        else:
            final.append((sx1, sx2))
    return final


def remove_background(cell_surface):
    """Fondo blanco conectado al borde -> transparente, con borde suavizado."""
    rgb = to_rgb_array(cell_surface)
    h, w, _ = rgb.shape
    mn = rgb.min(axis=2)
    white = mn >= BG_THRESH

    # Mascara de "blancos" y componentes conectados al borde
    wsurf = pygame.Surface((w, h))
    arr = np.zeros((w, h, 3), dtype=np.uint8)
    arr[white.T] = 255
    pygame.surfarray.blit_array(wsurf, arr)
    wmask = pygame.mask.from_threshold(wsurf, (255, 255, 255), (1, 1, 1, 255))
    bg = pygame.mask.Mask((w, h))
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not bg.get_at((x, y)):
                bg.draw(wmask.connected_component((x, y)), (0, 0))
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not bg.get_at((x, y)):
                bg.draw(wmask.connected_component((x, y)), (0, 0))

    bg_arr = np.zeros((h, w), dtype=bool)
    bg_surf = bg.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0))
    bg_arr = pygame.surfarray.array3d(bg_surf)[:, :, 0].T > 0

    alpha = np.full((h, w), 255, dtype=np.float32)
    alpha[bg_arr] = 0
    # Suavizado: pixeles claros vecinos al fondo -> alpha parcial (elimina halo blanco)
    nb = np.zeros_like(bg_arr)
    nb[1:, :] |= bg_arr[:-1, :]
    nb[:-1, :] |= bg_arr[1:, :]
    nb[:, 1:] |= bg_arr[:, :-1]
    nb[:, :-1] |= bg_arr[:, 1:]
    edge = nb & ~bg_arr
    soft_low = BG_THRESH - 70
    fac = np.clip((BG_THRESH - mn) / float(BG_THRESH - soft_low), 0.0, 1.0)
    alpha[edge] = np.minimum(alpha[edge], fac[edge] * 255)

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(out, rgb.transpose(1, 0, 2).astype(np.uint8))
    out = out.convert_alpha() if pygame.display.get_init() and pygame.display.get_surface() else out
    pa = pygame.surfarray.pixels_alpha(out)
    pa[:, :] = alpha.T.astype(np.uint8)
    del pa
    return out


def is_grayscale(surf, comp_mask):
    """True si los pixeles del componente no tienen color (texto negro/gris)."""
    rgb = to_rgb_array(surf)
    sel = pygame.surfarray.array3d(comp_mask.to_surface()).transpose(1, 0, 2)[:, :, 0] > 0
    px = rgb[sel]
    if len(px) == 0:
        return True
    return ((px.max(axis=1) - px.min(axis=1)) > 35).mean() < 0.05


def keep_main_blobs(surf):
    """Conserva el cuerpo principal y elementos cercanos; elimina restos de frames vecinos."""
    mask = pygame.mask.from_surface(surf, 40)
    comps = mask.connected_components(minimum=30)
    if not comps:
        return surf, None
    main = max(comps, key=lambda m: m.count())
    mrect = main.get_bounding_rects()[0]
    for r in main.get_bounding_rects()[1:]:
        mrect.union_ip(r)
    keep = pygame.mask.Mask(mask.get_size())
    w = mask.get_size()[0]
    for c in comps:
        rects = c.get_bounding_rects()
        cr = rects[0]
        for r in rects[1:]:
            cr.union_ip(r)
        touches_side = cr.left <= 1 or cr.right >= w - 1
        if c is not main and c.count() < main.count() * 0.08 and is_grayscale(surf, c):
            continue  # numeros de frame / restos de texto
        if c is main or (not touches_side and cr.inflate(40, 40).colliderect(mrect)) or c.count() > main.count() * 0.25:
            keep.draw(c, (0, 0))
    out = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    keep.to_surface(out, setsurface=surf, unsetcolor=(0, 0, 0, 0))
    rects = keep.get_bounding_rects()
    bbox = rects[0]
    for r in rects[1:]:
        bbox.union_ip(r)
    return out, bbox


def extract_frames(filename, expected_rows=5, cols=10):
    img = pygame.image.load(os.path.join(RAW_DIR, filename))
    rgb = to_rgb_array(img)
    mask = content_mask(rgb)
    bands = find_bands(mask, expected_rows)
    per_band = [(b, find_segments(mask, b[0], b[1], rgb)) for b in bands]
    widths = sorted(s[1] - s[0] for _, segs in per_band for s in segs)
    med = widths[len(widths) // 2] if widths else 150
    frames = []
    for (y1, y2), segs in per_band:
        y1p, y2p = max(0, y1 - 25), min(img.get_height(), y2 + 6)
        for sx1, sx2 in split_wide(segs, med, img.get_width(), cols, mask[y1:y2]):
            pad = 6
            x1, x2 = max(0, sx1 - pad), min(img.get_width(), sx2 + pad)
            cell = img.subsurface((x1, y1p, x2 - x1, y2p - y1p)).copy()
            clean, bbox = keep_main_blobs(remove_background(cell))
            if bbox and bbox.w > 5 and bbox.h > 5:
                frames.append(clean.subsurface(bbox).copy())
    # Descartar recortes casi vacios (astillas de cortes entre frames pegados)
    if frames:
        areas = sorted(f.get_width() * f.get_height() for f in frames)
        med_area = areas[len(areas) // 2]
        frames = [f for f in frames if f.get_width() * f.get_height() >= med_area * 0.3]
    return frames


def resample(frames, n=TOTAL_FRAMES):
    if len(frames) == n:
        return frames
    return [frames[int(round(i * (len(frames) - 1) / float(n - 1)))] for i in range(n)]


def build_sheet(frames, ref_height):
    scale = CHAR_H / float(ref_height)
    sheet = pygame.Surface((len(frames) * FRAME_W, FRAME_H), pygame.SRCALPHA)
    for i, f in enumerate(frames):
        w, h = f.get_size()
        s = scale
        # Nunca exceder la celda
        s = min(s, (FRAME_W - 4) / float(w), (FRAME_H - 4) / float(h))
        dw, dh = max(1, int(w * s)), max(1, int(h * s))
        scaled = pygame.transform.smoothscale(f, (dw, dh))
        sheet.blit(scaled, (i * FRAME_W + (FRAME_W - dw) // 2, FRAME_H - dh - 2))
    return sheet


SHEETS = [
    # (salida, archivo fuente, filas esperadas)
    ("idle.png", "Hoja de sprites_ reposo y guardia pixel art.png", 4, 11),
    ("walk.png", "Gemini_Generated_Image_s1h2rrs1h2rrs1h2.jpeg", 5),
    ("jump.png", "Gemini_Generated_Image_hoph1shoph1shoph.jpeg", 5),
    ("crouch.png", "Hoja de sprites_ guardia baja de luchadora.png", 4),
    ("punch_light.png", "Gemini_Generated_Image_ptd13tptd13tptd1.jpeg", 5),
    ("punch_heavy.png", "Gemini_Generated_Image_abq9wwabq9wwabq9.jpeg", 5),
    ("kick_light.png", "Gemini_Generated_Image_kp7dnwkp7dnwkp7d.jpeg", 5),
    ("kick_heavy.png", "Gemini_Generated_Image_wzyl7ewzyl7ewzyl.jpeg", 5),
    ("block.png", "Hoja de sprites_ Bloqueo y defensa.png", 3, 17),
    ("special.png", "Gemini_Generated_Image_h3h7vdh3h7vdh3h7.jpeg", 5),
    ("ultimate.png", "Gemini_Generated_Image_27zbz627zbz627zb.jpeg", 5),
    ("hurt.png", "Sprite sheet de impacto y recuperación en 50 fotogramas.png", 5),
    ("ko.png", "Hoja de sprites de derrota K.O.png", 5),
]

if __name__ == "__main__":
    for entry in SHEETS:
        out_name, src, rows = entry[:3]
        cols = entry[3] if len(entry) > 3 else 10
        frames = extract_frames(src, rows, cols)
        # Altura de referencia: percentil 90 de alturas (pose de pie), robusto ante efectos
        heights = sorted(f.get_height() for f in frames)
        ref_h = heights[int(len(heights) * 0.9) - 1] if heights else CHAR_H
        print(f"{out_name:16s} <- {src[:45]:45s} frames detectados={len(frames):3d} ref_h={ref_h}")
        frames = resample(frames)
        sheet = build_sheet(frames, ref_h)
        pygame.image.save(sheet, os.path.join(OUT_DIR, out_name))

        # Preview de depuracion (10 frames sobre fondo verde)
        prev = pygame.Surface((FRAME_W * 10, FRAME_H))
        prev.fill((0, 160, 0))
        for k in range(10):
            idx = k * 5
            prev.blit(sheet.subsurface((idx * FRAME_W, 0, FRAME_W, FRAME_H)), (k * FRAME_W, 0))
        pygame.image.save(prev, os.path.join(DEBUG_DIR, out_name))
    print("OK - hojas de 50 frames generadas en", OUT_DIR)
