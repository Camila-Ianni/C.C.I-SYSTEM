"""
Mission 6 Boss: 'Allen O'Neil & Hi-Do' (The Final Showdown).
Features:
- Allen O'Neil: Machine gun bursts, grenade throws, and relentless laughter.
- Hi-Do Gunship: General Morden's command helicopter raining aerial salvos from above.
- Final climax of the Metal Slug campaign.
"""
import random
import pygame
from src.config import (
    CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    COLOR_HUD_YELLOW, COLOR_HUD_ORANGE
)
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Grenade
from src.entities.bosses.hairbuster_ribert import RibertHomingMissile

class AllenONeilBoss:
    def __init__(self, x=1750, y=184):
        self.x = float(x)
        self.y = float(y)
        self.vx = -1.0
        self.max_health = 160
        self.health = 160
        self.phase = 1
        self.is_dead = False
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        
        self.shoot_cooldown = 45
        self.grenade_cooldown = 110
        self.hido_rocket_cooldown = 160
        self.flash_timer = 0
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Allen O'Neil.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        # Allen standing / shooting (x=10, y=50, w=60, h=65)
        self.idle_surf = SpriteLoader.get_subsurface(sheet, 10, 50, 60, 65)

        hido_sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Hi-Do.png"
        hido_sheet = SpriteLoader.load_sheet(hido_sheet_path, colorkey=None)
        # Hi-Do gunship hull (x=10, y=10, w=160, h=85)
        self.hido_surf = SpriteLoader.get_subsurface(hido_sheet, 10, 10, 160, 85)
        self.hido_surf.set_colorkey(self.hido_surf.get_at((0, 0)))

    @property
    def hurtbox(self):
        return pygame.Rect(int(self.x - 20), int(self.y - 60), 45, 60)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4
        if self.health <= 80 and self.phase == 1:
            self.phase = 2
            self.shoot_cooldown = 25
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.is_defeated = True
            self.defeat_timer = 200

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
                rx = self.x + random.randint(-40, 120)
                ry = self.y - random.randint(20, 130)
                particle_system.spawn_explosion(rx, ry, size="big" if self.defeat_timer < 60 else "medium")
                camera.trigger_shake(duration_frames=6, magnitude=4)
            return

        # Allen pacing
        self.x += self.vx
        if abs(self.x - player.physics.x) < 80:
            self.vx = 1.0
        elif abs(self.x - player.physics.x) > 180:
            self.vx = -1.0

        # Allen rapid machine gun burst
        self.shoot_cooldown -= 1
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 40 if self.phase == 1 else 22
            # Fire 3 bullets forward
            from src.weapons.projectile import Bullet
            b = Bullet(self.x - 25, self.y - 35, vx=-5.0, vy=0)
            enemy_projectiles.append(b)

        # Allen grenade toss
        self.grenade_cooldown -= 1
        if self.grenade_cooldown <= 0:
            self.grenade_cooldown = 90
            g = Grenade(self.x - 20, self.y - 45, vx=-3.5, vy=-4.0)
            enemy_projectiles.append(g)

        # Hi-Do rocket barrage from sky
        self.hido_rocket_cooldown -= 1
        if self.hido_rocket_cooldown <= 0:
            self.hido_rocket_cooldown = 130
            enemy_projectiles.append(RibertHomingMissile(self.x + 80, 50, player.physics.x, player.physics.y))

    def draw(self, surface, camera):
        # Draw Hi-Do helicopter in the sky
        hx, hy = camera.apply(self.x + 40, 40)
        if self.hido_surf:
            surface.blit(self.hido_surf, (hx - 80, hy - 40))

        # Draw Allen O'Neil on the ground
        sx, sy = camera.apply(self.x, self.y - 65)
        if self.idle_surf:
            if self.flash_timer > 0:
                flash = self.idle_surf.copy()
                flash.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash, (sx - 30, sy))
            else:
                surface.blit(self.idle_surf, (sx - 30, sy))

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
            label = font.render("BOSS: ALLEN O'NEIL & HI-DO", False, COLOR_HUD_YELLOW)
            surface.blit(label, (bx, by - 10))
