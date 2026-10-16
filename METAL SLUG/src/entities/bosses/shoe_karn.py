"""
Mission 4 Bosses: 'Shoe & Karn' (Twin Mountain Assault Battle Tanks).
Features:
- Dual independent armored tanks working together.
- Forward high-explosive tank shell barrages and vertical mortar launches.
- Defeating both tanks triggers the mission clear.
"""
import random
import pygame
from src.config import (
    CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    COLOR_HUD_YELLOW, COLOR_HUD_ORANGE
)
from src.engine.sprite_loader import SpriteLoader
from src.entities.vehicles.dicokka import TankCannonball

class SingleTankBoss:
    def __init__(self, name, x, y, max_health=65):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.max_health = max_health
        self.health = max_health
        self.is_dead = False
        self.is_defeated = False
        self.defeat_timer = 0
        self.cannon_cooldown = random.randint(40, 90)
        self.flash_timer = 0
        self.surf = None

    @property
    def hurtbox(self):
        return pygame.Rect(int(self.x), int(self.y - 70), 120, 65)

    def take_damage(self, amount):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.is_defeated = True
            self.defeat_timer = 150

    def update(self, player, enemy_projectiles, particle_system, camera):
        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.is_defeated:
            self.defeat_timer -= 1
            if self.defeat_timer % 8 == 0 and particle_system:
                rx = self.x + random.randint(10, 110)
                ry = self.y - random.randint(10, 60)
                particle_system.spawn_explosion(rx, ry, size="medium")
            return

        self.cannon_cooldown -= 1
        if self.cannon_cooldown <= 0:
            self.cannon_cooldown = random.randint(70, 110)
            enemy_projectiles.append(TankCannonball(self.x + 10, self.y - 35, vx=-4.0, vy=-1.2))
            if particle_system:
                particle_system.spawn_explosion(self.x + 5, self.y - 35, size="small")

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y - 75)
        if self.surf:
            if self.flash_timer > 0:
                flash = self.surf.copy()
                flash.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash, (sx, sy))
            else:
                surface.blit(self.surf, (sx, sy))

class ShoeKarnBoss:
    def __init__(self, x=3650, y=184):
        self.x = float(x)
        self.y = float(y)
        self.max_health = 130
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        
        self.shoe = SingleTankBoss("SHOE", x + 130, y, max_health=65)
        self.karn = SingleTankBoss("KARN", x, y, max_health=65)
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Shoe & Karn.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        # Shoe tank sprite (olive green)
        self.shoe.surf = SpriteLoader.get_subsurface(sheet, 10, 50, 130, 80)
        # Karn tank sprite (camo brown)
        self.karn.surf = SpriteLoader.get_subsurface(sheet, 150, 50, 130, 80)

    @property
    def health(self):
        return self.shoe.health + self.karn.health

    @property
    def hurtbox(self):
        # Target the living tank first
        if not self.karn.is_dead:
            return self.karn.hurtbox
        return self.shoe.hurtbox

    def take_damage(self, amount, death_type="bullet"):
        if not self.karn.is_dead:
            self.karn.take_damage(amount)
        elif not self.shoe.is_dead:
            self.shoe.take_damage(amount)

    def update(self, player, platforms, enemy_projectiles, particle_system, camera):
        if abs(player.physics.x - self.x) < 320 or camera.is_locked:
            self.is_active = True
        if not self.is_active:
            return

        self.karn.update(player, enemy_projectiles, particle_system, camera)
        self.shoe.update(player, enemy_projectiles, particle_system, camera)

        if self.karn.is_defeated and self.shoe.is_defeated and not self.is_defeated:
            self.is_defeated = True
            self.defeat_timer = 180

        if self.is_defeated:
            self.defeat_timer -= 1
            if self.defeat_timer % 6 == 0 and particle_system:
                camera.trigger_shake(duration_frames=6, magnitude=3)

    def draw(self, surface, camera):
        self.karn.draw(surface, camera)
        self.shoe.draw(surface, camera)

        # Joint Health Bar
        if self.is_active and not self.is_defeated:
            bar_w = 140
            bar_h = 5
            bx = (VIRTUAL_WIDTH - bar_w) // 2
            by = 36
            pygame.draw.rect(surface, (0, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))
            fill_w = int((self.health / self.max_health) * bar_w)
            pygame.draw.rect(surface, COLOR_HUD_YELLOW, (bx, by, fill_w, bar_h))
            font = pygame.font.Font(None, 12)
            label = font.render("BOSS: SHOE & KARN", False, COLOR_HUD_YELLOW)
            surface.blit(label, (bx, by - 10))
