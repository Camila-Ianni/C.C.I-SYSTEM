"""
R-Shobu Rebel Attack Helicopter (Mission 1 Submarine Outpost Mini-Boss).
Features:
- Spawns past the submarine hull (x ≈ 1380..1550).
- Locks screen scrolling until defeated.
- Animated rotor blades and horizontal tilt facing the player.
- Drops aerial bombs and shoots down at the player.
- Cascading destruction explosions on defeat, falling from sky and unlocking the camera.
"""
import math
import random
import pygame
from src.config import CHROMA_GREEN
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Bullet

class RShobuHelicopter:
    def __init__(self, x, y):
        self.physics = PhysicsBody(x, y, width=70, height=45)
        self.health = 25
        self.max_health = 25
        self.facing_right = False
        self.is_dead = False
        self.is_falling = False
        self.hit_flash_timer = 0
        self.attack_cooldown = random.randint(40, 80)
        self.hover_angle = random.uniform(0, math.pi * 2)
        self.start_y = float(y)
        self.vy = 0.0

        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - R-Shobu.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_GREEN)

        # 7 hovering frames with animated rotor blades
        fly_rects = [
            (7, 22, 89, 57),
            (101, 21, 89, 54),
            (194, 18, 89, 55),
            (288, 15, 89, 59),
            (382, 15, 89, 58),
            (477, 14, 89, 61),
            (568, 11, 89, 66)
        ]
        self.fly_frames_l = SpriteLoader.extract_frames(sheet, fly_rects, flip_x=False)
        self.fly_frames_r = SpriteLoader.extract_frames(sheet, fly_rects, flip_x=True)

        self.anim_fly_l = Animation(self.fly_frames_l, frame_duration=3, loop=True)
        self.anim_fly_r = Animation(self.fly_frames_r, frame_duration=3, loop=True)

    @property
    def hurtbox(self):
        return self.physics.hurtbox

    def take_damage(self, amount, death_type="bullet", particle_system=None, *args, **kwargs):
        if self.is_falling or self.is_dead:
            return
        self.health -= amount
        self.hit_flash_timer = 4
        if self.health <= 0:
            self.is_falling = True
            self.vy = -1.5

    def update_ai(self, player, platforms=None, enemy_projectiles=None, particle_system=None):
        if self.is_dead:
            return

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1

        # Falling death sequence
        if self.is_falling:
            self.vy += 0.35
            self.physics.y += self.vy
            self.physics.x += 0.8 if self.facing_right else -0.8
            if particle_system and random.random() < 0.4:
                particle_system.spawn_explosion(
                    self.physics.x + random.randint(-20, 20),
                    self.physics.y + random.randint(-15, 15),
                    size="medium"
                )
            if self.physics.y >= 185:
                self.is_dead = True
                if particle_system:
                    particle_system.spawn_explosion(self.physics.x, self.physics.y, size="large")
            return

        # Active flight AI
        dist_x = player.physics.x - self.physics.x
        self.facing_right = (dist_x > 0)

        # Smooth sine wave hovering motion
        self.hover_angle += 0.05
        target_hover_y = self.start_y + math.sin(self.hover_angle) * 12.0
        self.physics.y += (target_hover_y - self.physics.y) * 0.1

        # Track target x over player
        target_x = player.physics.x + (40.0 if not self.facing_right else -40.0)
        target_x = max(1370.0, min(1620.0, target_x))
        self.physics.x += (target_x - self.physics.x) * 0.04

        # Update rotor animation
        if self.facing_right:
            self.anim_fly_r.update()
        else:
            self.anim_fly_l.update()

        # Attack logic: drop aerial bombs / shoot bullets
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        elif enemy_projectiles is not None:
            self.attack_cooldown = random.randint(70, 110)
            dir_x = 0.5 if self.facing_right else -0.5
            spawn_x = self.physics.x + (15 if self.facing_right else -15)
            spawn_y = self.physics.y + 15
            # Dropping bomb/bullet downwards
            enemy_projectiles.append(Bullet(spawn_x, spawn_y, dir_x=dir_x, dir_y=3.5, speed=3.8, damage=1))

    def draw(self, surface, camera):
        if self.is_dead:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)

        anim = self.anim_fly_r if self.facing_right else self.anim_fly_l
        img = anim.get_current_surface()
        if not img:
            return

        if self.hit_flash_timer > 0:
            flash_surf = img.copy()
            flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(flash_surf, (sx - img.get_width() // 2, sy - img.get_height() // 2))
        else:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
