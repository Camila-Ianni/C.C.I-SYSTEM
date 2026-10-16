import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, "/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((320,224))
from src.entities.player import Player
p = Player(x=60,y=160,character="marco")
# scale first idle frame 8x
f = p.idle_frames_r[0]
big = pygame.transform.scale(f, (f.get_width()*8, f.get_height()*8))
pygame.image.save(big, "/Users/cami/.lmstudio/scratchpads/q/big_idle_0.png")
f2 = p.run_frames_r[0]
big2 = pygame.transform.scale(f2, (f2.get_width()*8, f2.get_height()*8))
pygame.image.save(big2, "/Users/cami/.lmstudio/scratchpads/q/big_run_0.png")
f3 = p.run_frames_r[5]
big3 = pygame.transform.scale(f3, (f3.get_width()*8, f3.get_height()*8))
pygame.image.save(big3, "/Users/cami/.lmstudio/scratchpads/q/big_run_5.png")
print("saved", f.get_size(), f2.get_size())
