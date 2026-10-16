"""
Projectiles and Grenades for Metal Slug 1.
Features:
- Directional Pistol bullets (Horizontal, Vertical Up, Downwards in air, Crouched).
- Parabolic Grenades with physics, bounce, fuse timer and explosion trigger.
- Uses pygame.FRect for sub-pixel precision.
"""
import math
import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT, COLOR_HUD_YELLOW, CHROMA_GREEN
from src.engine.sprite_loader import SpriteLoader

class Bullet:
    bullet_r = None
    bullet_l = None
    bullet_u = None
    bullet_d = None

    @classmethod
    def load_sprites(cls):
        if cls.bullet_r is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            cls.bullet_r = sheet.subsurface((4, 20, 30, 5)).copy()
            cls.bullet_l = pygame.transform.flip(cls.bullet_r, True, False)
            cls.bullet_u = pygame.transform.rotate(cls.bullet_r, 90)
            cls.bullet_d = pygame.transform.rotate(cls.bullet_r, -90)
        except Exception as e:
            print(f"[Bullet] Error loading bullet sprites: {e}")

    def __init__(self, x, y, dir_x=1.0, dir_y=0.0, speed=10.0, damage=1):
        self.x = float(x)
        self.y = float(y)
        self.dir_x = float(dir_x)
        self.dir_y = float(dir_y)
        self.speed = float(speed)
        self.damage = damage
        self.is_dead = False
        self.width = 12.0
        self.height = 8.0
        self.load_sprites()

    @property
    def hitbox(self):
        # Uses pygame.FRect for modern sub-pixel collision precision
        if hasattr(pygame, "FRect"):
            return pygame.FRect(self.x - self.width / 2.0, self.y - self.height / 2.0, self.width, self.height)
        return pygame.Rect(int(self.x - self.width / 2.0), int(self.y - self.height / 2.0), int(self.width), int(self.height))

    def update(self, camera=None, platforms=None):
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed
        
        # Despawn if leaving virtual screen boundaries
        if camera:
            sx, sy = camera.apply(self.x, self.y)
            if sx < -30 or sx > VIRTUAL_WIDTH + 30 or sy < -30 or sy > VIRTUAL_HEIGHT + 30:
                self.is_dead = True

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        if self.dir_y < -0.5 and self.bullet_u:
            surface.blit(self.bullet_u, (sx - self.bullet_u.get_width() // 2, sy - self.bullet_u.get_height() // 2))
        elif self.dir_y > 0.5 and self.bullet_d:
            surface.blit(self.bullet_d, (sx - self.bullet_d.get_width() // 2, sy - self.bullet_d.get_height() // 2))
        elif self.dir_x > 0 and self.bullet_r:
            surface.blit(self.bullet_r, (sx - self.bullet_r.get_width() // 2, sy - self.bullet_r.get_height() // 2))
        elif self.dir_x < 0 and self.bullet_l:
            surface.blit(self.bullet_l, (sx - self.bullet_l.get_width() // 2, sy - self.bullet_l.get_height() // 2))
        else:
            # Fallback fast tracer
            if self.dir_y == 0:
                length = 8
                start_x = sx - int(self.dir_x * length)
                pygame.draw.line(surface, COLOR_HUD_YELLOW, (start_x, sy), (sx, sy), 2)
                pygame.draw.line(surface, (255, 255, 255), (sx - int(self.dir_x * 2), sy), (sx, sy), 1)
            elif self.dir_x == 0:
                length = 8
                start_y = sy - int(self.dir_y * length)
                pygame.draw.line(surface, COLOR_HUD_YELLOW, (sx, start_y), (sx, sy), 2)
                pygame.draw.line(surface, (255, 255, 255), (sx, sy - int(self.dir_y * 2)), (sx, sy), 1)

class Grenade:
    frames = None

    @classmethod
    def load_sprites(cls):
        if cls.frames is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            boxes = [
                (4, 299, 14, 22), (20, 299, 14, 22), (36, 298, 14, 23), (52, 300, 14, 21),
                (68, 298, 14, 23), (84, 300, 14, 21), (100, 298, 14, 23), (116, 301, 15, 20),
                (133, 300, 15, 21), (150, 302, 16, 19), (168, 301, 17, 20), (187, 304, 17, 17),
                (206, 303, 19, 18), (227, 305, 19, 16), (248, 305, 20, 16), (270, 306, 19, 15),
                (291, 306, 21, 15), (314, 307, 21, 14), (337, 307, 22, 14), (361, 307, 21, 14),
                (384, 307, 23, 14), (409, 307, 21, 14), (432, 307, 18, 14)
            ]
            cls.frames = [SpriteLoader.get_subsurface(sheet, *b) for b in boxes]
        except Exception as e:
            print(f"[Grenade] Error loading grenade sprites: {e}")
            cls.frames = []

    def __init__(self, x, y, facing_right=True):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.vx = 3.6 if facing_right else -3.6
        self.vy = -4.5
        self.gravity = 0.35
        self.bounces = 0
        self.max_bounces = 2
        self.timer = 50  # 50 frames until explosion if no direct hit
        self.anim_tick = 0
        self.is_dead = False
        self.exploded = False
        self.radius = 7.0
        self.load_sprites()

    @property
    def hitbox(self):
        if hasattr(pygame, "FRect"):
            return pygame.FRect(self.x - self.radius, self.y - self.radius, self.radius * 2.0, self.radius * 2.0)
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), int(self.radius * 2), int(self.radius * 2))

    def update(self, platforms=None, camera=None):
        self.timer -= 1
        self.anim_tick += 1
        if self.timer <= 0:
            self.explode()
            return
            
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        
        # Ground bounce detection
        if platforms:
            for plat in platforms:
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None and self.vy > 0 and self.y >= plat_y:
                    self.y = plat_y
                    self.vy = -self.vy * 0.45
                    self.vx *= 0.7
                    self.bounces += 1
                    if self.bounces >= self.max_bounces:
                        self.explode()
                        break

    def explode(self):
        self.exploded = True
        self.is_dead = True

    def draw(self, surface, camera):
        if not self.is_dead:
            sx, sy = camera.apply(self.x, self.y)
            if self.frames:
                frame_idx = (self.anim_tick // 2) % len(self.frames)
                img = self.frames[frame_idx]
                if not self.facing_right:
                    img = pygame.transform.flip(img, True, False)
                surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
            else:
                pygame.draw.circle(surface, (100, 100, 100), (sx, sy), int(self.radius))
