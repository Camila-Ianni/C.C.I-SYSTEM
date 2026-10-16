import os, sys
os.environ["SDL_VIDEODRIVER"]="dummy"
sys.path.insert(0,"/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((200,200))
from src.engine.sprite_loader import SpriteLoader
from src.config import CHROMA_CYAN
M="Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
sheet = SpriteLoader.load_sheet(M, colorkey=CHROMA_CYAN)
# diagonal band: 7 frames at x=10,44,78,112,146,180,214, each ~29 wide, tops descending
tops=[25,40,85,132,170,193,222]
surf=pygame.Surface((260,260)); surf.fill((60,60,60))
x=0
for i,top in enumerate(tops):
    f=SpriteLoader.get_subsurface(sheet,10+34*i if i<5 else (10+34*i), top, 29, 38)
    surf.blit(f,(x,0)); x+=32
    print(i, f.get_size())
pygame.image.save(surf,"/Users/cami/.lmstudio/scratchpads/q/diag.png")
print("saved")
