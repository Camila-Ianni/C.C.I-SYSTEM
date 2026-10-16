"""
Type 02 'Di-Cokka' Heavy Rebel Battle Tank (Phase 5).
Features:
- Heavy tracked armored vehicle.
- Drives forward and backward on terrain.
- Elevates turret and fires parabolic explosive cannon shells.
- 15 HP with multi-hit flashes and fiery destruction sequence.
"""
import random
import pygame
from src.config import CHROMA_WHITE
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Grenade

class BallisticShell:
    """Arced heavy cannon shell fired by Di-Cokka tank and heavy vehicles."""
    def __init__(self, x, y, facing_right=False, vx=None, vy=None):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx) if vx is not None else (3.2 if facing_right else -3.2)
        self.vy = float(vy) if vy is not None else -4.2
        self.gravity = 0.22
        self.radius = 5
        self.exploded = False
        self.is_dead = False

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
            # Fiery red-orange cannonball
            pygame.draw.circle(surface, (230, 40, 0), (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 200, 0), (sx, sy), self.radius - 2)

TankCannonball = BallisticShell

class DiCokkaTank:
    def __init__(self, x, y, facing_right=False):
        self.physics = PhysicsBody(x, y, width=64, height=48)
        self.facing_right = facing_right
        self.health = 15
        self.max_health = 15
        self.is_dead = False
        self.death_timer = 0
        self.shoot_cooldown = 110
        self.patrol_dir = 1 if facing_right else -1
        self.origin_x = x
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Type 02 ''Di-Cokka''.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_WHITE)
        
        # 1. Drive Track Frames (Row 2: y=121, h=56, w=71, 6 frames)
        drive_rects = [
            (3, 121, 71, 56),
            (77, 121, 71, 56),
            (151, 122, 71, 55),
            (225, 122, 71, 55),
            (299, 122, 71, 55),
            (373, 122, 71, 55),
        ]
        self.drive_frames_l = SpriteLoader.extract_frames(sheet, drive_rects, flip_x=False)
        self.drive_frames_r = SpriteLoader.extract_frames(sheet, drive_rects, flip_x=True)
        
        self.anim_drive = Animation(self.drive_frames_l, frame_duration=5, loop=True)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead:
            return
        self.health -= amount
        if self.health <= 0:
            self.is_dead = True
            self.death_timer = 60

    def update_ai(self, player, platforms=None, enemy_projectiles=None):
        if self.is_dead:
            self.death_timer -= 1
            return

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

        # Patrol within range of origin
        self.physics.vx = 0.5 * self.patrol_dir
        if abs(self.physics.x - self.origin_x) > 40:
            self.patrol_dir *= -1

        # Track player direction for shooting
        dist_x = player.physics.x - self.physics.x
        self.facing_right = (dist_x > 0)

        # Firing Logic
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        elif abs(dist_x) < 220 and enemy_projectiles is not None:
            self.shoot_cooldown = 140
            spawn_x = self.physics.x + (25 if self.facing_right else -25)
            spawn_y = self.physics.y - 32
            enemy_projectiles.append(BallisticShell(spawn_x, spawn_y, facing_right=self.facing_right))

        self.anim_drive.frames = self.drive_frames_r if self.facing_right else self.drive_frames_l
        self.anim_drive.update()

    def draw(self, surface, camera):
        if self.is_dead:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        img = self.anim_drive.get_current_surface()
        if img:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
            
        # Draw Armor bar above Di-Cokka
        bar_w = 40
        bar_h = 3
        bx = sx - bar_w // 2
        by = sy - 56
        pygame.draw.rect(surface, (0, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))
        fill_w = int((max(0, self.health) / self.max_health) * bar_w)
        pygame.draw.rect(surface, (230, 160, 0), (bx, by, fill_w, bar_h))
