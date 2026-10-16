"""
Rebel Soldier with Riot Shield (Phase 4).
Features:
- Marches forward protecting troops behind.
- Frontal riot shield ricochets regular pistol/machinegun bullets with sparks.
- Vulnerable to grenades, attacks from behind (flanking), knife melee and shotgun blasts.
- Smooth directional animations without frame flicker.
"""
import random
import pygame
from src.config import CHROMA_WHITE
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Bullet

class ShieldSoldier:
    def __init__(self, x, y, facing_right=False):
        self.physics = PhysicsBody(x, y, width=22, height=34)
        self.facing_right = facing_right
        self.health = 3
        self.shield_health = 4
        self.is_dead = False
        self.death_timer = 0
        self.attack_cooldown = random.randint(40, 90)
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Rebel Soldier (Shield).png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_WHITE)
        
        # 1. Marching with Shield (Row 2: y=46, h=41, 12 frames)
        march_rects = [
            (3, 46, 30, 41), (35, 46, 29, 41), (66, 46, 30, 41),
            (99, 46, 32, 41), (133, 46, 32, 41), (167, 46, 32, 41),
            (202, 46, 30, 41), (235, 46, 30, 41), (267, 46, 29, 41),
            (298, 46, 29, 41), (329, 46, 28, 41), (359, 46, 28, 41)
        ]
        self.march_frames_r = SpriteLoader.extract_frames(sheet, march_rects, flip_x=True)
        self.march_frames_l = SpriteLoader.extract_frames(sheet, march_rects, flip_x=False)
        
        # 2. Peeking and Shooting Pistol (Row 3: y=90, h=38, 4 frames)
        shoot_rects = [
            (3, 90, 32, 38), (38, 90, 32, 38), (73, 90, 36, 38), (112, 90, 32, 38)
        ]
        self.shoot_frames_r = SpriteLoader.extract_frames(sheet, shoot_rects, flip_x=True)
        self.shoot_frames_l = SpriteLoader.extract_frames(sheet, shoot_rects, flip_x=False)
        
        # 3. Authentic Falling Death (Row 8: y=379..427, 7 frames)
        death_rects = [
            (3, 389, 33, 38), (39, 388, 40, 39), (82, 379, 41, 48),
            (126, 379, 38, 48), (167, 385, 48, 42), (218, 389, 53, 38),
            (274, 389, 49, 38)
        ]
        self.death_frames_r = SpriteLoader.extract_frames(sheet, death_rects, flip_x=True)
        self.death_frames_l = SpriteLoader.extract_frames(sheet, death_rects, flip_x=False)
        
        self.anim_march_r = Animation(self.march_frames_r, frame_duration=5, loop=True)
        self.anim_march_l = Animation(self.march_frames_l, frame_duration=5, loop=True)
        self.anim_shoot_r = Animation(self.shoot_frames_r, frame_duration=5, loop=False)
        self.anim_shoot_l = Animation(self.shoot_frames_l, frame_duration=5, loop=False)
        self.anim_death_r = Animation(self.death_frames_r, frame_duration=6, loop=False)
        self.anim_death_l = Animation(self.death_frames_l, frame_duration=6, loop=False)

    def take_hit_from_projectile(self, projectile, particle_system=None):
        """Checks if projectile impacts the frontal shield or vulnerable back."""
        is_explosive_or_heavy = getattr(projectile, 'damage', 1) >= 10
        bullet_coming_from_front = (projectile.x < self.physics.x) if not self.facing_right else (projectile.x > self.physics.x)
        
        if bullet_coming_from_front and not is_explosive_or_heavy:
            self.shield_health -= 1
            # Slight knockback recoil
            self.physics.x += (3 if not self.facing_right else -3)
            if particle_system:
                particle_system.spawn_casing(self.physics.x, self.physics.y - 20, not self.facing_right)
            if self.shield_health <= 0:
                self.take_damage(self.health)
                return True
            return False # Blocked but damaged
        else:
            damage = getattr(projectile, 'damage', 1)
            self.take_damage(damage)
            return True

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead:
            return
        self.health -= amount
        if self.health <= 0:
            self.is_dead = True
            self.death_timer = 42
            if self.facing_right:
                self.anim_death_r.reset()
            else:
                self.anim_death_l.reset()
            try:
                from src.core.sound_manager import SoundManager
                SoundManager().play_soldier_scream()
            except Exception:
                pass

    def update_ai(self, player, platforms=None, enemy_projectiles=None):
        if self.is_dead:
            self.death_timer -= 1
            if self.facing_right:
                self.anim_death_r.update()
            else:
                self.anim_death_l.update()
            return

        dist_x = player.physics.x - self.physics.x
        abs_dist = abs(dist_x)
        
        # Proximity activation
        if abs_dist > 340:
            return

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

        self.facing_right = (dist_x > 0)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # March towards player behind shield
        if abs_dist > 65:
            self.physics.vx = 0.6 if self.facing_right else -0.6
            if self.facing_right:
                self.anim_march_r.update()
            else:
                self.anim_march_l.update()
        else:
            # Close range: stop and shoot pistol
            self.physics.vx = 0.0
            if self.attack_cooldown == 0 and enemy_projectiles is not None:
                self.attack_cooldown = 100
                if self.facing_right:
                    self.anim_shoot_r.reset()
                else:
                    self.anim_shoot_l.reset()
                dir_x = 1.0 if self.facing_right else -1.0
                spawn_x = self.physics.x + (16 if self.facing_right else -16)
                spawn_y = self.physics.y - 18
                enemy_projectiles.append(Bullet(spawn_x, spawn_y, dir_x, 0.0, speed=5.5))
            if self.facing_right:
                self.anim_shoot_r.update()
            else:
                self.anim_shoot_l.update()

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        if self.is_dead:
            if self.death_timer > 0:
                anim = self.anim_death_r if self.facing_right else self.anim_death_l
                img = anim.get_current_surface()
                if img:
                    surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
            return

        if self.attack_cooldown > 80:
            anim = self.anim_shoot_r if self.facing_right else self.anim_shoot_l
        else:
            anim = self.anim_march_r if self.facing_right else self.anim_march_l
        img = anim.get_current_surface()
        if img:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
