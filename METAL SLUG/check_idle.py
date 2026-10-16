import os, sys
os.environ["SDL_VIDEODRIVER"]="dummy"
sys.path.insert(0,"/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((200,200))
from src.engine.sprite_loader import SpriteLoader
from src.config import CHROMA_CYAN
M="Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
sheet = SpriteLoader.load_sheet(M, colorkey=CHROMA_CYAN)
frames=[SpriteLoader.get_subsurface(sheet,10+i*34,255,29,37) for i in range(4)]
surf=pygame.Surface((160,48)); surf.fill((60,60,60))
x=0
for f in frames:
    big=pygame.transform.scale(f,(f.get_width()*4,f.get_height()*4))
    pygame.image.save(big,f"/Users/cami/.lmstudio/scratchpads/q/idle_raw_{x}.png")
    x+=1
print("saved sizes", [f.get_size() for f in frames])
