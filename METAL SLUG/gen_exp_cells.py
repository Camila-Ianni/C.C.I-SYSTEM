import os, sys
os.environ["SDL_VIDEODRIVER"]="dummy"
sys.path.insert(0,"/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((200,200))
from src.engine.sprite_loader import SpriteLoader
from src.config import CHROMA_GREEN
E="Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Explosion SFX.png"
sheet = SpriteLoader.load_sheet(E, colorkey=CHROMA_GREEN)

def cells(gaps, y, h):
    out=[]
    xs=[4]+[g+3 for g in gaps]
    xe=[g-1 for g in gaps]+[592-1]
    for a,b in zip(xs,xe):
        if b>a:
            out.append(SpriteLoader.get_subsurface(sheet,a,y,b-a+1,h))
    return out

R1_gaps=[36,71,102,135,169,202,235,268,301,334,367,400,432,465,497,528,557]
R3_gaps=[52,103,149,195,245,292,341,391,441,489,537]
R2_gaps=[246,288]  # small: before text x4..238, and after

r1 = cells(R1_gaps, 5, 40)
r3 = cells(R3_gaps, 89, 54)
print("R1 cells:", len(r1), "R3 cells:", len(r3), "sizes:", [(f.get_width(),f.get_height()) for f in r1][:6])

surf = pygame.Surface((600,200)); surf.fill((60,60,60))
x=0
for f in r1:
    surf.blit(f,(x,0)); x+=f.get_width()+2
x=0
for f in r3:
    surf.blit(f,(x,100)); x+=f.get_width()+2
pygame.image.save(surf,"/Users/cami/.lmstudio/scratchpads/q/exp_cells.png")
print("saved")
