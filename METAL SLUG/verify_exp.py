import os, sys
os.environ["SDL_VIDEODRIVER"]="dummy"
sys.path.insert(0,"/Users/cami/Desktop/METAL SLUG")
import pygame
pygame.init(); pygame.display.set_mode((200,200))
from src.engine.particle_system import ParticleSystem
ps = ParticleSystem(); ps.load_effects()
print("small", len(ps.small_explosion_frames), "medium", len(ps.medium_explosion_frames), "big", len(ps.big_explosion_frames))
surf = pygame.Surface((620,180)); surf.fill((60,60,60))
x=0
for f in ps.small_explosion_frames: surf.blit(f,(x,0)); x+=f.get_width()+2
x=0
for f in ps.medium_explosion_frames: surf.blit(f,(x,60)); x+=f.get_width()+2
x=0
for f in ps.big_explosion_frames: surf.blit(f,(x,120)); x+=f.get_width()+2
pygame.image.save(surf,"/Users/cami/.lmstudio/scratchpads/q/verify_exp.png")
print("saved")
