"""Render zoomed stage strip segments with a world-coordinate grid (including area above the main strip)."""
import sys
from PIL import Image, ImageDraw

SHEET = 'Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 1.png'
STRIP_Y = 893
TOP = int(sys.argv[4]) if len(sys.argv) > 4 else 0  # world y top (can be negative)
im = Image.open(SHEET).convert('RGB')
x0, x1 = int(sys.argv[1]), int(sys.argv[2])
out = sys.argv[3]
Z = 3
crop = im.crop((x0, STRIP_Y + TOP, x1, STRIP_Y + 224)).resize(((x1 - x0) * Z, (224 - TOP) * Z), Image.NEAREST)
d = ImageDraw.Draw(crop)
for y in range((TOP // 8) * 8, 224, 8):
    yy = (y - TOP) * Z
    major = y % 16 == 0
    d.line([(0, yy), (crop.width, yy)], fill=(255, 0, 0) if major else (255, 160, 160), width=1)
    if major:
        for xx in range(0, crop.width, 300):
            d.text((xx + 2, yy - 10), str(y), fill=(255, 255, 0))
for x in range((x0 // 10) * 10, x1, 10):
    xx = (x - x0) * Z
    if x % 50 == 0:
        d.line([(xx, 0), (xx, crop.height)], fill=(0, 200, 255), width=1)
        for yy in range(0, crop.height, 150):
            d.text((xx + 2, yy + 2), str(x), fill=(0, 255, 255))
crop.save(out)
