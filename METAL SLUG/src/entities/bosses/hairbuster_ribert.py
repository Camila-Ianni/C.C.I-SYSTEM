"""
Mission 2 Boss: 'Hairbuster Ribert' (General Morden's Heavy Assault Helicopter).
Features:
- Heavy twin-rotor gunship flying overhead.
- Dual attack modes: Aerial carpet bombs and homing rocket salvos.
- 100 HP with smoke damage stages and fiery explosion sequence.
"""
import random
import math
import pygame
from src.config import (
    CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    COLOR_HUD_YELLOW, COLOR_HUD_ORANGE
)
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Grenade

class RibertHomingMissile:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy) or 1.0
        self.vx = (dx / dist) * 3.5
        self.vy = (dy / dist) * 3.5
        self.radius = 4
        self.is_dead = False
        self.exploded = False
        self.life = 120

    def update(self, platforms=None, camera=None):
        self.life -= 1
        if self.life <= 0:
            self.exploded = True
            self.is_dead = True
            return
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface, camera):
        if not self.is_dead:
            sx, sy = camera.apply(self.x, self.y)
            pygame.draw.circle(surface, (230, 50, 0), (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 200, 0), (sx, sy), self.radius - 2)

class HairbusterRibertBoss:
    def __init__(self, x=600, y=60):
        self.x = float(x)
        self.y = float(y)
        self.vx = 1.2
        self.max_health = 100
        self.health = 100
        self.phase = 1
        self.is_dead = False
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        self.bomb_cooldown = 80
        self.missile_cooldown = 140
        self.flash_timer = 0
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Hairbuster Ribert.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        
        # Flight frames (y=40, w=110, h=65 approx, 4 frames)
        fly_rects = [(10 + i * 115, 40, 110, 65) for i in range(4)]
        self.fly_frames = SpriteLoader.extract_frames(sheet, fly_rects, flip_x=False)
        self.anim_fly = Animation(self.fly_frames, frame_duration=5, loop=True)

    @property
    def hurtbox(self):
        return pygame.Rect(int(self.x - 50), int(self.y - 25), 100, 55)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4
        if self.health <= 50 and self.phase == 1:
            self.phase = 2
            self.bomb_cooldown = 40
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.is_defeated = True
            self.defeat_timer = 180

    def update(self, player, platforms, enemy_projectiles, particle_system, camera):
        if abs(player.physics.x - self.x) < 320 or camera.is_locked:
            self.is_active = True
        if not self.is_active:
            return

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.is_defeated:
            self.defeat_timer -= 1
            if self.defeat_timer % 6 == 0 and particle_system:
                rx = self.x + random.randint(-40, 40)
                ry = self.y + random.randint(-20, 20)
                particle_system.spawn_explosion(rx, ry, size="medium")
                camera.trigger_shake(duration_frames=6, magnitude=3)
            return

        # Patrol back and forth in sky
        self.x += self.vx
        if abs(self.x - player.physics.x) > 160:
            self.vx *= -1

        self.anim_fly.update()

        # Attack 1: Carpet bombing
        self.bomb_cooldown -= 1
        if self.bomb_cooldown <= 0:
            self.bomb_cooldown = 90 if self.phase == 1 else 50
            from src.entities.vehicles.flying_tara import AerialBomb
            enemy_projectiles.append(AerialBomb(self.x, self.y + 25))

        # Attack 2: Homing missiles
        self.missile_cooldown -= 1
        if self.missile_cooldown <= 0:
            self.missile_cooldown = 130
            enemy_projectiles.append(RibertHomingMissile(self.x - 20, self.y + 10, player.physics.x, player.physics.y))
            enemy_projectiles.append(RibertHomingMissile(self.x + 20, self.y + 10, player.physics.x, player.physics.y))

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        img = self.anim_fly.get_current_surface()
        if img:
            draw_x = sx - img.get_width() // 2
            draw_y = sy - img.get_height() // 2
            if self.flash_timer > 0:
                flash_surf = img.copy()
                flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash_surf, (draw_x, draw_y))
            else:
                surface.blit(img, (draw_x, draw_y))

        # Health bar
        if self.is_active and not self.is_defeated:
            bar_w = 140
            bar_h = 5
            bx = (VIRTUAL_WIDTH - bar_w) // 2
            by = 36
            pygame.draw.rect(surface, (0, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))
            fill_w = int((self.health / self.max_health) * bar_w)
            color = COLOR_HUD_YELLOW if self.phase == 1 else (240, 40, 0)
            pygame.draw.rect(surface, color, (bx, by, fill_w, bar_h))
            font = pygame.font.Font(None, 12)
            label = font.render("BOSS: HAIRBUSTER RIBERT", False, COLOR_HUD_YELLOW)
            surface.blit(label, (bx, by - 10))
