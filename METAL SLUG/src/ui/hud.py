"""
Metal Slug 1 Neo-Geo Arcade HUD System.
Renders:
- 1UP Score & Top Score.
- Countdown Timer (60s) using classic yellow/orange arcade numerals.
- ARMS & BOMB counters.
- Player Lives icon and count.
- Flashing 'GO! ->' indicator when path is clear.
"""
import math
import pygame
from src.config import (
    VIRTUAL_WIDTH, COLOR_HUD_YELLOW, COLOR_HUD_ORANGE, COLOR_WHITE,
    CHROMA_WHITE
)
from src.engine.sprite_loader import SpriteLoader

class HUD:
    def __init__(self):
        self.font_loaded = False
        self.time_digits = {}
        self.status_sheet = None
        self.go_sign_frames = []
        self.go_anim_tick = 0
        self.load_hud_assets()

    def load_hud_assets(self):
        try:
            # 1. Load Time Numbers (0-9)
            time_sheet_path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Time Numbers.png"
            time_img = pygame.image.load(time_sheet_path).convert()
            pa = pygame.PixelArray(time_img)
            pa.replace((195, 195, 195), (163, 73, 164))
            del pa
            time_img.set_colorkey((163, 73, 164))
            
            digit_w = 14
            digit_h = 16
            digit_y = 18
            for d in range(10):
                dx = 7 + d * 16
                if dx + digit_w <= time_img.get_width():
                    self.time_digits[str(d)] = SpriteLoader.get_subsurface(time_img, dx, digit_y, digit_w, digit_h)

            # 2. Load Status Sheet (ARMS, BOMB labels)
            status_sheet_path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Player Status.png"
            self.status_sheet = SpriteLoader.load_sheet(status_sheet_path, colorkey=CHROMA_WHITE)
            
            # Safe bounding boxes for 97x131 image
            self.arms_label = SpriteLoader.get_subsurface(self.status_sheet, 5, 1, 30, 11)
            self.bomb_label = SpriteLoader.get_subsurface(self.status_sheet, 68, 1, 27, 11)
            
            # Pygame native fallback font for crisp arcade score text
            self.font = pygame.font.Font(None, 14)
            self.font_loaded = True
        except Exception as e:
            print(f"[HUD] Error loading HUD graphics: {e}")
            self.font = pygame.font.Font(None, 14)

    def draw(self, surface, player, time_remaining=60, top_score=50000, show_go=False, slug=None, camera=None):
        # 2. Top Bar: 1UP Score & TOP / INSERT COIN
        score_str = f"1UP  {player.score:06d}"
        score_surf = self.font.render(score_str, False, COLOR_HUD_YELLOW)
        surface.blit(score_surf, (16, 5))
        
        lives_str = f"1UP={getattr(player, 'lives', 3)}"
        lives_surf = self.font.render(lives_str, False, COLOR_HUD_YELLOW)
        surface.blit(lives_surf, (16, 14))

        coin_surf = self.font.render("INSERT COIN", False, COLOR_WHITE)
        surface.blit(coin_surf, (220, 5))

        # 3. Weapon & Bomb Info / Tank HUD
        if slug and getattr(slug, 'is_occupied', False) and not getattr(slug, 'is_dead', False):
            # Tank Mode HUD: CANNON [ammo] and armor bar
            cannon_label = self.font.render("CANNON", False, COLOR_HUD_YELLOW)
            surface.blit(cannon_label, (16, 25))
            cannon_ammo = getattr(slug, 'cannon_ammo', 10)
            ammo_surf = self.font.render(f"{cannon_ammo:02d}", False, COLOR_WHITE)
            surface.blit(ammo_surf, (68, 25))
            
            # Tank Armor Bar under player score
            armor = max(0, getattr(slug, 'armor', 3))
            max_armor = getattr(slug, 'max_armor', 3)
            for i in range(max_armor):
                box_color = (0, 220, 0) if i < armor else (80, 80, 80)
                pygame.draw.rect(surface, box_color, (16 + i * 14, 34, 11, 6))
                pygame.draw.rect(surface, (0, 0, 0), (16 + i * 14, 34, 11, 6), 1)
        elif hasattr(self, 'arms_label') and self.arms_label:
            surface.blit(self.arms_label, (16, 25))
            surface.blit(self.bomb_label, (70, 25))
            
            # Weapon Type Badge and Ammo Text
            if player.weapon_type != "PISTOL":
                badge_surf = self.font.render(f"[{player.weapon_type}]", False, COLOR_HUD_YELLOW)
                surface.blit(badge_surf, (16, 36))
                ammo_str = f"{player.ammo:03d}"
                ammo_surf = self.font.render(ammo_str, False, COLOR_WHITE)
                surface.blit(ammo_surf, (36, 36))
            else:
                ammo_str = "inf"
                ammo_surf = self.font.render(ammo_str, False, COLOR_WHITE)
                surface.blit(ammo_surf, (22, 36))
            
            # Bomb Count
            bomb_str = f"{player.grenades:02d}"
            bomb_surf = self.font.render(bomb_str, False, COLOR_WHITE)
            surface.blit(bomb_surf, (82, 36))

        # 4. Time Countdown (Center Top)
        time_str = f"{max(0, int(time_remaining)):02d}"
        center_x = VIRTUAL_WIDTH // 2 - 14
        for i, char in enumerate(time_str):
            if char in self.time_digits:
                surface.blit(self.time_digits[char], (center_x + i * 14, 8))
            else:
                t_surf = self.font.render(char, False, COLOR_HUD_YELLOW)
                surface.blit(t_surf, (center_x + i * 14, 8))

        # 5. Flashing "GO! ->" Arrow when arena clear
        if show_go:
            self.go_anim_tick += 1
            if (self.go_anim_tick // 15) % 2 == 0:
                go_surf = self.font.render("GO! >>", False, COLOR_HUD_ORANGE)
                surface.blit(go_surf, (VIRTUAL_WIDTH - 65, 32))

        # 6. Bottom Arcade Indicators (LEVEL-4, CREDIT 00, Rescued POW badges)
        lvl_surf = self.font.render("LEVEL-4", False, COLOR_WHITE)
        surface.blit(lvl_surf, (100, 208))
        
        pows = getattr(player, 'pows_rescued', 0)
        if pows > 0:
            pow_badge = self.font.render(f"POW x{pows}", False, COLOR_HUD_YELLOW)
            surface.blit(pow_badge, (16, 208))
            
        cred_surf = self.font.render("CREDIT 00", False, COLOR_WHITE)
        surface.blit(cred_surf, (220, 208))
