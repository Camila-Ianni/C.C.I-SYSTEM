"""
Mission 1 Boss: 'Tetsuyuki' (Submerged Flying Boat / Bomber) Implementation.
Features:
- Massive 2-phase arcade boss fight.
- Phase 1: Heavy nose artillery cannon and deck gunners.
- Phase 2 (Rage Mode < 50% HP): Roof hatch opens, charging and firing giant blue plasma energy orbs.
- Cascading explosion sequence upon defeat.
- Triggers 'MISSION 1 COMPLETE' celebration.
"""
import random
import math
import pygame
from src.config import (
    CHROMA_CYAN, VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    COLOR_HUD_YELLOW, COLOR_HUD_ORANGE, COLOR_WHITE
)
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Grenade

class GiantPlasmaOrb:
    """Colossal energy plasma orb fired by Tetsuyuki in Phase 2."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = -1.2
        self.vy = 2.4
        self.gravity = 0.08
        self.radius = 16
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
            # Glowing cyan/blue energy sphere
            pygame.draw.circle(surface, (0, 180, 255), (sx, sy), self.radius)
            pygame.draw.circle(surface, (150, 230, 255), (sx, sy), int(self.radius * 0.7))
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), int(self.radius * 0.35))

class TetsuyukiBoss:
    def __init__(self, x=3750, y=184):
        self.x = float(x)
        self.y = float(y)
        self.width = 340
        self.height = 220
        
        # Boss Combat Stats
        self.max_health = 80
        self.health = 80
        self.phase = 1
        self.is_dead = False
        self.is_defeated = False
        self.is_active = False
        self.defeat_timer = 0
        
        # Attack Timers
        self.attack_cooldown = 90
        self.plasma_charge_timer = 0
        self.flash_timer = 0
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Tetsuyuki.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        
        # 1. Main Boss Hull (Trimmed cleanly below the "REFERENCE" label)
        # x=627..999 (w=372), y=1560..1849 (h=289)
        self.hull_surf = SpriteLoader.get_subsurface(sheet, 627, 1560, 360, 280, flip_x=False)
        
        # 2. Plasma Turret Frames (Row 1: y=60, 6 frames)
        turret_rects = [(10 + i * 55, 60, 52, 44) for i in range(6)]
        self.turret_frames = SpriteLoader.extract_frames(sheet, turret_rects, flip_x=False)
        self.anim_turret = Animation(self.turret_frames, frame_duration=6, loop=True)

    @property
    def hurtbox(self):
        # Vulnerable target zone: Cockpit and Nose cannon
        return pygame.Rect(int(self.x + 80), int(self.y - 140), 160, 120)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead or self.is_defeated:
            return
        self.health -= amount
        self.flash_timer = 4 # White impact flash
        
        # Trigger Phase 2 Rage Mode at 50% HP
        if self.health <= self.max_health // 2 and self.phase == 1:
            self.phase = 2
            self.attack_cooldown = 40

        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.is_defeated = True
            self.defeat_timer = 180 # 3 seconds of cascading explosions

    def update(self, player, platforms, enemy_projectiles, particle_system, camera):
        if abs(player.physics.x - self.x) < 320 or camera.is_locked:
            self.is_active = True
            
        if not self.is_active:
            return

        if self.flash_timer > 0:
            self.flash_timer -= 1

        # Defeat Sequence: Cascading Explosions across the hull
        if self.is_defeated:
            self.defeat_timer -= 1
            if self.defeat_timer % 6 == 0 and particle_system:
                rand_x = self.x + random.randint(40, 280)
                rand_y = self.y - random.randint(30, 180)
                size = "big" if self.defeat_timer % 12 == 0 else "medium"
                particle_system.spawn_explosion(rand_x, rand_y, size=size)
                camera.trigger_shake(duration_frames=6, magnitude=4)
            return

        # Phase 1: Nose Artillery Salvo
        if self.phase == 1:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 110
                # Fire heavy artillery shell from nose
                spawn_x = self.x + 70
                spawn_y = self.y - 65
                from src.entities.vehicles.dicokka import BallisticShell
                enemy_projectiles.append(BallisticShell(spawn_x, spawn_y, facing_right=False))
                if particle_system:
                    particle_system.spawn_explosion(spawn_x, spawn_y, size="small")

        # Phase 2: Giant Energy Plasma Turret (Rage Mode)
        elif self.phase == 2:
            self.anim_turret.update()
            self.attack_cooldown -= 1
            
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 130
                # Launch Giant Plasma Orb from upper circular mount
                spawn_x = self.x + 140
                spawn_y = self.y - 165
                enemy_projectiles.append(GiantPlasmaOrb(spawn_x, spawn_y))
                if particle_system:
                    particle_system.spawn_explosion(spawn_x, spawn_y, size="medium")
                camera.trigger_shake(duration_frames=10, magnitude=3)

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        
        # 1. Draw Main Tetsuyuki Hull
        if self.hull_surf:
            draw_y = sy - self.hull_surf.get_height()
            
            # Hit Flash Effect
            if self.flash_timer > 0:
                flash_surf = self.hull_surf.copy()
                flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(flash_surf, (sx, draw_y))
            else:
                surface.blit(self.hull_surf, (sx, draw_y))

        # 2. Draw Upper Plasma Turret in Phase 2
        if self.phase == 2 and not self.is_defeated:
            turret_img = self.anim_turret.get_current_surface()
            if turret_img:
                surface.blit(turret_img, (sx + 120, sy - 180))
