"""
Mission 3 Boss: 'Tani Oh' (Super-Heavy Siege Locomotive Tank).
Features:
- Massive twin heavy-gauge rail howitzers firing explosive shells.
- Vertical mortar launchers firing parabolic cluster mines.
- Two-phase health structure (120 HP) with Rage Mode cannonades.
- Cascading explosion sequence on defeat.
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

class TaniOhMortarShell:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        self.gravity = 0.22
        dx = target_x - x
        # Parabolic arc
        self.vx = dx / 45.0
        self.vy = -7.5
        self.radius = 4
        self.is_dead = False
        self.exploded = False

    def update(self, platforms=None, camera=None):
        self.x += self.vx
        self.vy += self.gravity
        self.y += self.vy

        if platforms:
            for p in platforms:
                if p.is_point_on_surface(self.x, self.y):
                    self.exploded = True
                    self.is_dead = True
                    return

        if self.y > 230:
            self.exploded = True
            self.is_dead = True

    def draw(self, surface, camera):
        if not self.is_dead:
            sx, sy = camera.apply(self.x, self.y)
            pygame.draw.circle(surface, (255, 120, 0), (int(sx), int(sy)), self.radius)
            pygame.draw.circle(surface, (255, 230, 80), (int(sx), int(sy)), self.radius - 2)

class TaniOhBoss:
    def __init__(self, x=3650, y=184):
        self.x = float(x)
        self.y = float(y)
        self.max_health = 120
        self.health = 120
        self.phase = 1
        self.is_dead = False
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        
        self.cannon_cooldown = 90
        self.mortar_cooldown = 140
        self.flash_timer = 0
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Tani Oh.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        
        # Base hull / chassis (x=10, y=10, w=250, h=150)
        self.hull_surf = SpriteLoader.get_subsurface(sheet, 10, 10, 250, 150)

    @property
    def hurtbox(self):
        # Targetable area across the chassis and turret
        return pygame.Rect(int(self.x), int(self.y - 120), 220, 110)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4
        if self.health <= 60 and self.phase == 1:
            self.phase = 2
            self.cannon_cooldown = 45
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
                rx = self.x + random.randint(20, 200)
                ry = self.y - random.randint(20, 120)
                particle_system.spawn_explosion(rx, ry, size="big" if self.defeat_timer < 60 else "medium")
                camera.trigger_shake(duration_frames=6, magnitude=4)
            return

        # Slight rumble animation
        self.cannon_cooldown -= 1
        if self.cannon_cooldown <= 0:
            self.cannon_cooldown = 80 if self.phase == 1 else 45
            # Fire heavy cannonball forward towards player
            from src.entities.vehicles.dicokka import TankCannonball
            enemy_projectiles.append(TankCannonball(self.x + 30, self.y - 70, vx=-4.5, vy=-1.5))
            if particle_system:
                particle_system.spawn_explosion(self.x + 20, self.y - 70, size="small")
            camera.trigger_shake(duration_frames=4, magnitude=2)

        # Attack 2: Mortar cluster rain
        self.mortar_cooldown -= 1
        if self.mortar_cooldown <= 0:
            self.mortar_cooldown = 130 if self.phase == 1 else 90
            target_px = player.physics.x
            enemy_projectiles.append(TaniOhMortarShell(self.x + 120, self.y - 100, target_px, player.physics.y))
            if self.phase == 2:
                enemy_projectiles.append(TaniOhMortarShell(self.x + 160, self.y - 100, target_px - 40, player.physics.y))

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y - 140)
        if self.hull_surf:
            if self.flash_timer > 0:
                flash = self.hull_surf.copy()
                flash.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash, (sx, sy))
            else:
                surface.blit(self.hull_surf, (sx, sy))

        # Boss Health Bar
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
            label = font.render("BOSS: TANI OH", False, COLOR_HUD_YELLOW)
            surface.blit(label, (bx, by - 10))
