"""
Flying Tara Monoplane Bomber Entity for Metal Slug 1 (Phase 5).
Features:
- High altitude horizontal bombing strafes.
- Triggers when player/camera approaches its patrol airspace.
- Drops aerial bombs with gravity above player positions.
- Explodes in mid-air upon destruction.
"""
import random
import pygame
from src.config import CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Grenade

class AerialBomb:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = -1.2
        self.vy = 1.0
        self.gravity = 0.18
        self.is_dead = False
        self.exploded = False
        self.radius = 6

    def update(self, platforms=None, camera=None):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        if platforms:
            for plat in platforms:
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None and self.vy > 0 and self.y >= plat_y:
                    self.y = plat_y
                    self.exploded = True
                    self.is_dead = True
                    break

    def draw(self, surface, camera):
        if not self.is_dead:
            sx, sy = camera.apply(self.x, self.y)
            pygame.draw.circle(surface, (60, 60, 60), (sx, sy), self.radius)
            pygame.draw.line(surface, (200, 200, 200), (sx - 2, sy - 2), (sx + 2, sy + 2), 2)

class FlyingTara:
    def __init__(self, x, y=48, speed=2.2):
        self.physics = PhysicsBody(x, y, width=54, height=28)
        self.speed = speed
        self.health = 5
        self.is_dead = False
        self.is_active = False
        self.has_dropped_bomb = False
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Flying Tara & Eaca-B.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        
        # Flying frames (y=40, 3 frames)
        fly_rects = [
            (10, 40, 58, 30),
            (75, 40, 58, 30),
            (140, 40, 58, 30),
        ]
        self.fly_frames = SpriteLoader.extract_frames(sheet, fly_rects, flip_x=False)
        self.anim_fly = Animation(self.fly_frames, frame_duration=4, loop=True)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead:
            return
        self.health -= amount
        if self.health <= 0:
            self.is_dead = True

    def update_ai(self, player, platforms=None, enemy_projectiles=None):
        if self.is_dead:
            return

        # Trigger only when player approaches within 280 px
        if not self.is_active:
            if player.physics.x >= self.physics.x - 300:
                self.is_active = True
            else:
                return

        # Fly horizontally from right to left
        self.physics.x -= self.speed
        self.anim_fly.update()

        # Check if directly above player to drop bomb
        if not self.has_dropped_bomb and abs(self.physics.x - player.physics.x) < 35 and enemy_projectiles is not None:
            self.has_dropped_bomb = True
            enemy_projectiles.append(AerialBomb(self.physics.x, self.physics.y + 14))

        # Despawn if far to the left of the player
        if self.physics.x < player.physics.x - 300:
            self.is_dead = True

    def draw(self, surface, camera):
        if self.is_dead or not self.is_active:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        img = self.anim_fly.get_current_surface()
        if img:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
