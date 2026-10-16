import os, sys
os.environ["SDL_VIDEODRIVER"]="dummy"
sys.path.insert(0,"/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((200,200))
from src.engine.sprite_loader import SpriteLoader
from src.config import CHROMA_CYAN
M="Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
sheet = SpriteLoader.load_sheet(M, colorkey=CHROMA_CYAN)
def big(x,y,w,h):
    f=SpriteLoader.get_subsurface(sheet,x,y,w,h)
    return pygame.transform.scale(f,(f.get_width()*5,f.get_height()*5))
surf=pygame.Surface((620,220)); surf.fill((60,60,60))
# row of candidates
cands = [
  ("crouch263", 10,263,29,29),
  ("s297", 10,305,29,30),
  ("s342", 10,342,29,30),
  ("s383", 10,384,29,27),
  ("s422", 10,422,29,29),
]
x=0
for (n,xx,yy,w,h) in cands:
    b=big(xx,yy,w,h); surf.blit(b,(x,0)); x+=b.get_width()+4
pygame.image.save(surf,"/Users/cami/.lmstudio/scratchpads/q/pose_candidates.png")
print("saved")
