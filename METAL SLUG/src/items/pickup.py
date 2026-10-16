"""
Collectible Items and Weapon Crates for Metal Slug 1 (Phase 2).
Handles:
- Weapon boxes: [H], [R], [S], [F].
- Ammo & Bomb crates: +10 Grenades.
- Gas Can: Heals Metal Slug Armor (+1).
- Food items: Banana, Fish, Chicken (Score points).
- Physics bounce and blink before despawn.
"""
import math
import random
import pygame
from src.config import GRAVITY
from src.engine.sprite_loader import SpriteLoader

class PickupItem:
    def __init__(self, x, y, item_type="H"):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = -3.2
        self.item_type = item_type  # 'H', 'R', 'S', 'F', 'BOMB', 'GAS', 'FOOD'
        self.is_dead = False
        self.life = 600  # 10 seconds before despawn
        self.bounces = 0
        self.is_grounded = False
        self.width = 22
        self.height = 17
        
        self.load_sprite()

    def load_sprite(self):
        sheet_path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Items.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=None)
        
        # Weapon box coordinates from Items.png (y=233, w=22, h=17)
        icon_coords = {
            "H": (470, 233, 22, 17),
            "R": (496, 233, 22, 17),
            "S": (522, 233, 22, 17),
            "F": (548, 233, 22, 17),
            "BOMB": (340, 60, 20, 20),
            "GAS": (230, 20, 24, 24),
            "FOOD": (10, 480, 24, 18),
            "AMMO": (90, 28, 32, 28),
        }
        coords = icon_coords.get(self.item_type, icon_coords["H"])
        self.sprite = SpriteLoader.get_subsurface(sheet, coords[0], coords[1], coords[2], coords[3])
        self.width = coords[2]
        self.height = coords[3]

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x - self.width / 2), int(self.y - self.height), self.width, self.height)

    def update(self, platforms=None):
        self.life -= 1
        if self.life <= 0:
            self.is_dead = True
            return

        # Vertical Gravity
        if not self.is_grounded:
            self.vy += GRAVITY
            self.y += self.vy
            self.x += self.vx
        else:
            self.vx *= 0.85

        # Platform Collision
        if platforms and not self.is_grounded:
            for plat in platforms:
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None and self.vy >= 0 and self.y >= plat_y:
                    self.y = plat_y
                    self.vy = -self.vy * 0.4
                    self.bounces += 1
                    if self.bounces >= 2 or abs(self.vy) < 0.5:
                        self.vy = 0
                        self.is_grounded = True
                    break

    def on_collect(self, player, slug=None, sound_manager=None):
        """Applies item effect to the player or current slug vehicle."""
        self.is_dead = True
        if sound_manager is None:
            from src.core.sound_manager import SoundManager
            sound_manager = SoundManager()
        
        if self.item_type in ["H", "R", "S", "F"]:
            player.weapon_type = self.item_type
            if self.item_type == "H":
                player.ammo = 200
            elif self.item_type in ["R", "S", "F"]:
                player.ammo = 30
            player.score += 1000
            if sound_manager:
                sound_manager.play_announcer_weapon(self.item_type)
                
        elif self.item_type == "BOMB":
            player.grenades = min(player.grenades + 10, 99)
            player.score += 500
            if sound_manager:
                sound_manager.play_announcer_weapon("BOMB")
                
        elif self.item_type == "GAS":
            if slug:
                slug.repair()
            player.score += 1000
            if sound_manager:
                sound_manager.play_announcer_weapon("GAS")
            
        elif self.item_type == "FOOD":
            player.score += 1000
            if sound_manager:
                sound_manager.play_announcer_weapon("FOOD")

        elif self.item_type == "AMMO":
            if player.ammo > 0:
                player.ammo += 50
            elif player.weapon_type == "PISTOL":
                player.weapon_type = "H"
                player.ammo = 50
                player.sync_weapon_visuals()
                if sound_manager:
                    sound_manager.play_announcer_weapon("H")
            else:
                player.ammo = 50
            player.score += 500
            if sound_manager:
                sound_manager.play_voice("ok")

    def draw(self, surface, camera):
        # Flicker during final 120 frames before despawning
        if self.life < 120 and (self.life // 4) % 2 == 0:
            return
            
        if self.sprite:
            sx, sy = camera.apply(self.x, self.y)
            surface.blit(self.sprite, (sx - self.width // 2, sy - self.height))
