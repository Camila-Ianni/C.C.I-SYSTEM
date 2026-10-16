"""
Enemy Entities for Metal Slug 1 (Rebel Army Infantry).
Features:
- Complete authentic sprite frames without clipping.
- States: IDLE, ALERT (reaction delay), PATROL, ATTACK (knife), GRENADE_TOSS, DEAD.
- Weapon-specific death animations:
  - Bullet collapse (6 frames)
  - Flame incineration (7 frames of running in fire and crumbling to ash)
  - Explosive/Shotgun gory blast
- Authentic stick grenade tossing physics with parabolic arcs and bounces.
"""
import random
import pygame
from src.config import CHROMA_CYAN
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Bullet

class RebelStickGrenade:
    """Stick grenade thrown by rebel soldiers."""
    def __init__(self, x, y, facing_right=False):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.vx = 3.2 if facing_right else -3.2
        self.vy = -4.5
        self.gravity = 0.35
        self.bounces = 0
        self.timer = 55
        self.is_dead = False
        self.damage = 1

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x - 5), int(self.y - 5), 10, 10)

    def update(self, platforms=None, camera=None):
        self.timer -= 1
        if self.timer <= 0:
            self.is_dead = True
            return

        self.vy += self.gravity
        self.x += self.vx
        old_y = self.y
        self.y += self.vy

        # Terrain bounce
        if platforms:
            for plat in platforms:
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None:
                    if self.vy > 0 and old_y <= plat_y + 2 and self.y >= plat_y - 2:
                        self.y = plat_y
                        self.vy = -self.vy * 0.45
                        self.vx *= 0.65
                        self.bounces += 1
                        if self.bounces >= 2:
                            self.vy = 0
                        break

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        # Authentic stick grenade: stick handle + explosive head
        dir_mult = 1 if self.vx > 0 else -1
        pygame.draw.line(surface, (140, 100, 50), (sx, sy), (sx - 6 * dir_mult, sy - 4), 2)
        pygame.draw.circle(surface, (80, 95, 70), (sx, sy), 3)


class RebelSoldier:
    def __init__(self, x, y, facing_right=False, soldier_type="rifle"):
        self.physics = PhysicsBody(x, y, width=20, height=34)
        self.facing_right = facing_right
        self.soldier_type = soldier_type # "rifle" or "grenadier"
        self.health = 1
        self.is_dead = False
        self.death_timer = 0
        self.death_type = "bullet"

        # AI States: 'IDLE', 'ALERT', 'PATROL', 'ATTACK_KNIFE', 'ATTACK_GRENADE', 'DEAD'
        self.state = "IDLE"
        self.state_timer = random.randint(20, 60)
        self.attack_cooldown = random.randint(90, 180)
        self.is_active = False

        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Rebel Soldier.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)

        # 1. Idle Grunt (y: 44, h: 38, 4 frames with complete helmet and boots - raw sheet faces RIGHT)
        idle_rects = [
            (5, 44, 27, 38),
            (37, 45, 27, 37),
            (69, 46, 26, 36),
            (100, 47, 24, 35)
        ]
        self.idle_frames_r = SpriteLoader.extract_frames(sheet, idle_rects, flip_x=False)
        self.idle_frames_l = SpriteLoader.extract_frames(sheet, idle_rects, flip_x=True)

        # 2. Authentic Run / Patrol (y: 308, h: 40, 12 frames - raw sheet faces LEFT)
        run_rects = [
            (5, 308, 22, 40),
            (30, 308, 22, 40),
            (55, 308, 24, 40),
            (83, 309, 26, 39),
            (114, 310, 24, 38),
            (143, 310, 22, 38),
            (170, 310, 21, 38),
            (197, 308, 21, 40),
            (223, 308, 22, 40),
            (250, 309, 25, 39),
            (280, 310, 22, 38),
            (307, 310, 19, 38)
        ]
        self.run_frames_r = SpriteLoader.extract_frames(sheet, run_rects, flip_x=True)
        self.run_frames_l = SpriteLoader.extract_frames(sheet, run_rects, flip_x=False)

        # 3. Knife Attack (y: 857..862, 10 frames - raw sheet faces LEFT)
        knife_rects = [
            (5, 860, 19, 37), (29, 861, 20, 36), (54, 862, 19, 35), (78, 857, 23, 40),
            (106, 857, 29, 39), (140, 857, 30, 37), (175, 857, 32, 35), (212, 857, 30, 33),
            (247, 857, 30, 34), (282, 857, 27, 35)
        ]
        self.knife_frames_r = SpriteLoader.extract_frames(sheet, knife_rects, flip_x=True)
        self.knife_frames_l = SpriteLoader.extract_frames(sheet, knife_rects, flip_x=False)

        # 4. Grenade Throw (y: 651, h: 40, 10 frames - raw sheet faces LEFT)
        toss_rects = [
            (5, 651, 21, 40), (31, 651, 21, 40), (57, 652, 23, 39), (85, 654, 26, 37),
            (116, 654, 25, 37), (146, 654, 26, 37), (177, 654, 26, 37), (208, 654, 27, 37),
            (240, 654, 25, 37), (270, 653, 25, 38)
        ]
        self.toss_frames_r = SpriteLoader.extract_frames(sheet, toss_rects, flip_x=True)
        self.toss_frames_l = SpriteLoader.extract_frames(sheet, toss_rects, flip_x=False)

        # 5. Authentic Falling Bullet Death (y: 478, h: 38, 6 frames - raw sheet faces RIGHT)
        death_rects = [
            (5, 478, 27, 38),
            (36, 478, 31, 38),
            (72, 478, 36, 38),
            (113, 478, 44, 38),
            (162, 478, 37, 38),
            (204, 478, 31, 38)
        ]
        self.death_frames_r = SpriteLoader.extract_frames(sheet, death_rects, flip_x=False)
        self.death_frames_l = SpriteLoader.extract_frames(sheet, death_rects, flip_x=True)

        # 6. Authentic Flame Incineration Death (y: 2433..2443, 7 frames - raw sheet faces RIGHT)
        flame_rects = [
            (147, 2443, 40, 46), (192, 2441, 41, 48), (238, 2437, 42, 52), (285, 2434, 44, 54),
            (334, 2433, 46, 53), (385, 2433, 46, 46), (436, 2434, 46, 40)
        ]
        self.flame_death_r = SpriteLoader.extract_frames(sheet, flame_rects, flip_x=False)
        self.flame_death_l = SpriteLoader.extract_frames(sheet, flame_rects, flip_x=True)

        # Directional animation instances
        self.anim_idle_r = Animation(self.idle_frames_r, frame_duration=8, loop=True)
        self.anim_idle_l = Animation(self.idle_frames_l, frame_duration=8, loop=True)
        self.anim_run_r = Animation(self.run_frames_r, frame_duration=6, loop=True)
        self.anim_run_l = Animation(self.run_frames_l, frame_duration=6, loop=True)
        self.anim_knife_r = Animation(self.knife_frames_r, frame_duration=3, loop=False)
        self.anim_knife_l = Animation(self.knife_frames_l, frame_duration=3, loop=False)
        self.anim_toss_r = Animation(self.toss_frames_r, frame_duration=4, loop=False)
        self.anim_toss_l = Animation(self.toss_frames_l, frame_duration=4, loop=False)
        self.anim_death_r = Animation(self.death_frames_r, frame_duration=6, loop=False)
        self.anim_death_l = Animation(self.death_frames_l, frame_duration=6, loop=False)
        self.anim_flame_death_r = Animation(self.flame_death_r, frame_duration=5, loop=False)
        self.anim_flame_death_l = Animation(self.flame_death_l, frame_duration=5, loop=False)

    def take_damage(self, amount, death_type="bullet"):
        if self.is_dead:
            return
        self.health -= amount
        if self.health <= 0:
            self.is_dead = True
            self.death_type = death_type
            self.death_timer = 50 if death_type != "flame" else 60
            if death_type == "flame":
                if self.facing_right:
                    self.anim_flame_death_r.reset()
                else:
                    self.anim_flame_death_l.reset()
            else:
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
            if self.death_type == "flame":
                if self.facing_right:
                    self.anim_flame_death_r.update()
                else:
                    self.anim_flame_death_l.update()
            else:
                if self.facing_right:
                    self.anim_death_r.update()
                else:
                    self.anim_death_l.update()
            return

        dist_x = player.physics.x - self.physics.x
        abs_dist = abs(dist_x)

        # Proximity activation
        if abs_dist > 350:
            return

        # Alert reaction trigger when first spotting player
        if not self.is_active:
            self.is_active = True
            self.state = "ALERT"
            self.state_timer = 14

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

        if abs_dist < 240 and self.state != "ATTACK_GRENADE":
            self.facing_right = (dist_x > 0)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # 1. Alert State: brief pause when spotting player
        if self.state == "ALERT":
            self.physics.vx = 0.0
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "PATROL"

        # 2. Close range: Knife attack (< 28 px)
        elif abs_dist <= 28:
            self.physics.vx = 0.0
            anim = self.anim_knife_r if self.facing_right else self.anim_knife_l
            
            if self.attack_cooldown == 0:
                self.state = "ATTACK_KNIFE"
                self.attack_cooldown = 50
                anim.reset()
                if abs_dist < 24 and not player.is_invincible:
                    player.is_dead = True
            
            if self.state == "ATTACK_KNIFE":
                anim.update()
                if anim.is_finished:
                    self.state = "IDLE"
            else:
                self.state = "IDLE"
                if self.facing_right:
                    self.anim_idle_r.update()
                else:
                    self.anim_idle_l.update()

        # 3. Mid range: Grenadier or Rifle attack
        elif 50 < abs_dist < 200 and self.attack_cooldown == 0 and enemy_projectiles is not None:
            if self.soldier_type == "grenadier" or random.random() < 0.35:
                # Toss Stick Grenade
                self.state = "ATTACK_GRENADE"
                self.physics.vx = 0.0
                self.state_timer = 30
                self.attack_cooldown = 160
                if self.facing_right:
                    self.anim_toss_r.reset()
                else:
                    self.anim_toss_l.reset()
                spawn_x = self.physics.x + (12 if self.facing_right else -12)
                spawn_y = self.physics.y - 20
                enemy_projectiles.append(RebelStickGrenade(spawn_x, spawn_y, facing_right=self.facing_right))
            else:
                # Shoot Rifle Bullet
                self.state = "IDLE"
                self.physics.vx = 0.0
                self.attack_cooldown = 140
                spawn_x = self.physics.x + (14 if self.facing_right else -14)
                spawn_y = self.physics.y - 18
                dir_x = 1.0 if self.facing_right else -1.0
                enemy_projectiles.append(Bullet(spawn_x, spawn_y, dir_x=dir_x, dir_y=0.0, speed=4.2, damage=1))

        # 4. Handle Active Grenade Toss Animation
        elif self.state == "ATTACK_GRENADE":
            self.physics.vx = 0.0
            self.state_timer -= 1
            if self.facing_right:
                self.anim_toss_r.update()
            else:
                self.anim_toss_l.update()
            if self.state_timer <= 0:
                self.state = "PATROL"

        # 5. Patrol towards player
        elif abs_dist > 80:
            self.state = "PATROL"
            self.physics.vx = 0.75 if self.facing_right else -0.75

            # Guard edge boundary check: stay on elevated perches without walking off into thin air
            if self.physics.current_platform and self.physics.current_platform.semi_solid:
                min_x = max(self.physics.current_platform.x1 + 8, 850.0 if self.physics.current_platform.y1 == 142 else self.physics.current_platform.x1 + 8)
                max_x = self.physics.current_platform.x2 - 8
                if (self.physics.vx < 0 and self.physics.x <= min_x) or (self.physics.vx > 0 and self.physics.x >= max_x):
                    self.physics.vx = 0.0
                    self.state = "IDLE"

            if self.physics.vx != 0.0:
                if self.facing_right:
                    self.anim_run_r.update()
                else:
                    self.anim_run_l.update()
            else:
                if self.facing_right:
                    self.anim_idle_r.update()
                else:
                    self.anim_idle_l.update()

        # 6. Idle
        else:
            self.state = "IDLE"
            self.physics.vx = 0.0
            if self.facing_right:
                self.anim_idle_r.update()
            else:
                self.anim_idle_l.update()

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.physics.x, self.physics.y)

        if self.is_dead:
            if self.death_timer > 0:
                if self.death_type == "flame":
                    anim = self.anim_flame_death_r if self.facing_right else self.anim_flame_death_l
                else:
                    anim = self.anim_death_r if self.facing_right else self.anim_death_l
                img = anim.get_current_surface()
                if img:
                    surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
            return

        # Active draw
        if self.state == "ATTACK_KNIFE":
            anim = self.anim_knife_r if self.facing_right else self.anim_knife_l
        elif self.state == "ATTACK_GRENADE":
            anim = self.anim_toss_r if self.facing_right else self.anim_toss_l
        elif self.state == "PATROL":
            anim = self.anim_run_r if self.facing_right else self.anim_run_l
        else:
            anim = self.anim_idle_r if self.facing_right else self.anim_idle_l

        img = anim.get_current_surface()
        if img:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
