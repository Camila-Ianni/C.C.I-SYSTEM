"""
Mission 5 Boss: 'Iron Nokana' (Armored Assault Fortress Tank).
Features:
- Giant rolling battle fortress.
- Front heavy cannon and underbelly flamethrower jets.
- Rear Girida-O turret detachment at phase 2 (< 50% HP).
- 140 HP with massive cascading explosions.
"""
import random
import pygame
from src.config import (
    CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    COLOR_HUD_YELLOW, COLOR_HUD_ORANGE
)
from src.engine.sprite_loader import SpriteLoader
from src.entities.vehicles.dicokka import TankCannonball

class IronNokanaBoss:
    def __init__(self, x=3600, y=184):
        self.x = float(x)
        self.y = float(y)
        self.max_health = 140
        self.health = 140
        self.phase = 1
        self.is_dead = False
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        
        self.cannon_cooldown = 70
        self.flame_cooldown = 130
        self.flame_active_timer = 0
        self.flash_timer = 0
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Iron Nokana.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        # Giant fortress chassis (x=10, y=100, w=280, h=140)
        self.chassis_surf = SpriteLoader.get_subsurface(sheet, 10, 100, 280, 140)

    @property
    def hurtbox(self):
        return pygame.Rect(int(self.x), int(self.y - 120), 260, 110)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4
        if self.health <= 70 and self.phase == 1:
            self.phase = 2
            self.cannon_cooldown = 40
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
                rx = self.x + random.randint(20, 240)
                ry = self.y - random.randint(20, 110)
                particle_system.spawn_explosion(rx, ry, size="big" if self.defeat_timer < 60 else "medium")
                camera.trigger_shake(duration_frames=6, magnitude=4)
            return

        # Cannon barrage
        self.cannon_cooldown -= 1
        if self.cannon_cooldown <= 0:
            self.cannon_cooldown = 65 if self.phase == 1 else 38
            enemy_projectiles.append(TankCannonball(self.x + 20, self.y - 65, vx=-4.5, vy=-1.0))
            if particle_system:
                particle_system.spawn_explosion(self.x + 10, self.y - 65, size="small")

        # Flame blast undercarriage
        self.flame_cooldown -= 1
        if self.flame_cooldown <= 0:
            self.flame_cooldown = 120
            self.flame_active_timer = 40
            camera.trigger_shake(duration_frames=8, magnitude=2)

        if self.flame_active_timer > 0:
            self.flame_active_timer -= 1
            if particle_system and self.flame_active_timer % 3 == 0:
                fx = self.x - random.randint(10, 60)
                fy = self.y - 20
                particle_system.spawn_explosion(fx, fy, size="small")
            # If player is close to front underside, burn player
            if abs(player.physics.x - (self.x - 30)) < 40 and not player.is_invincible:
                player.is_dead = True

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y - 135)
        if self.chassis_surf:
            if self.flash_timer > 0:
                flash = self.chassis_surf.copy()
                flash.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash, (sx, sy))
            else:
                surface.blit(self.chassis_surf, (sx, sy))

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
            label = font.render("BOSS: IRON NOKANA", False, COLOR_HUD_YELLOW)
            surface.blit(label, (bx, by - 10))
