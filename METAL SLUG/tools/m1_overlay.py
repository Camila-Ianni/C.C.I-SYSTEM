"""Overlay current Mission1 platforms on video frames (mapped to game coords) to compare feet positions."""
import os, sys, json
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame
from PIL import Image

pygame.init(); pygame.display.set_mode((320, 224))
from src.levels.mission1 import Mission1

track = {}
for line in open('test_output/nc_m1_track.log'):
    p, cx, e = line.split()
    t = float(p.rsplit('t_', 1)[1][:-4])
    track[t] = (int(cx), float(e))
for line in open('test_output/nc_m1_track2.log'):
    t, cx, dy, e = line.split()
    track[float(t)] = (int(cx), float(e))

m = Mission1()
times = [float(x) for x in sys.argv[2].split(',')]
out = sys.argv[1]
cells = []
for t in times:
    cx, e = track[t]
    im = Image.open(f'test_output/nc_m1/t_{t:07.2f}.png').convert('RGB').crop((0, 2, 642, 466)).resize((320, 224))
    s = pygame.image.frombytes(im.tobytes(), (320, 224), 'RGB')
    for pl in m.platforms:
        col = (255, 0, 255) if pl.semi_solid else (0, 255, 0)
        pygame.draw.line(s, col, (pl.x1 - cx, pl.y1), (pl.x2 - cx, pl.y2), 1)
    # grid every 16 px y
    for y in range(0, 224, 16):
        pygame.draw.line(s, (255, 255, 0), (0, y), (3, y))
        s.blit(pygame.font.Font(None, 12).render(str(y), True, (255, 255, 0)), (4, y - 3))
    for wx in range((cx // 50 + 1) * 50, cx + 320, 50):
        pygame.draw.line(s, (0, 255, 255), (wx - cx, 220), (wx - cx, 223))
        s.blit(pygame.font.Font(None, 12).render(str(wx), True, (0, 255, 255)), (wx - cx - 8, 212))
    s.blit(pygame.font.Font(None, 14).render(f't={t} cam={cx} e={e}', True, (255, 255, 255), (0, 0, 0)), (180, 30))
    cells.append(s)
cols = 2
sheet = pygame.Surface((cols * 640, ((len(cells) + 1) // cols) * 448))
for k, c in enumerate(cells):
    sheet.blit(pygame.transform.scale(c, (640, 448)), ((k % cols) * 640, (k // cols) * 448))
pygame.image.save(sheet, out)
