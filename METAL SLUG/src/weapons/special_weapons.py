"""
Special Weapons and Projectiles for Metal Slug 1.
Includes authentic sprite graphics from Weapon SFX:
- Heavy Machine Gun golden tracer bullets with authentic angle sprites and rotation.
- Shotgun blast with authentic cloud explosion frames, vertical up blasting, and multi-hit penetration.
- Rocket Launcher authentic missile sprites with exhaust flames, homing steering, and vertical launching.
- Flame Shot authentic rolling fireball animated sprites and upward launching.
"""
import math
import pygame
from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, COLOR_HUD_YELLOW, COLOR_HUD_ORANGE,
    CHROMA_GREEN
)
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation

class HeavyMachineGunBullet:
    sprite_base = None
    sprite_diag = None
    sprite_vert = None

    @classmethod
    def load_sprites(cls):
        if cls.sprite_base is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            cls.sprite_base = SpriteLoader.get_subsurface(sheet, 253, 250, 41, 12)
            cls.sprite_diag = SpriteLoader.get_subsurface(sheet, 273, 59, 33, 33)
            cls.sprite_vert = SpriteLoader.get_subsurface(sheet, 378, 52, 6, 45)
        except Exception as e:
            print(f"[HMG] Error loading sprites: {e}")

    def __init__(self, x, y, dir_x=1.0, dir_y=0.0, speed=12.0, damage=1.5):
        self.x = float(x)
        self.y = float(y)
        self.dir_x = float(dir_x)
        self.dir_y = float(dir_y)
        self.speed = float(speed)
        self.damage = damage
        self.is_dead = False
        self.width = 16.0
        self.height = 10.0
        self.load_sprites()
        
        # Precompute rotated sprite for this bullet's exact trajectory
        angle = math.degrees(math.atan2(-self.dir_y, self.dir_x))
        if self.sprite_base:
            self.rendered_sprite = pygame.transform.rotate(self.sprite_base, angle)
        else:
            self.rendered_sprite = None

    @property
    def hitbox(self):
        if hasattr(pygame, "FRect"):
            return pygame.FRect(self.x - self.width / 2.0, self.y - self.height / 2.0, self.width, self.height)
        return pygame.Rect(int(self.x - self.width / 2.0), int(self.y - self.height / 2.0), int(self.width), int(self.height))

    def update(self, camera=None):
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed
        if camera:
            sx, sy = camera.apply(self.x, self.y)
            if sx < -30 or sx > VIRTUAL_WIDTH + 30 or sy < -30 or sy > VIRTUAL_HEIGHT + 30:
                self.is_dead = True

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        if self.rendered_sprite:
            spr = self.rendered_sprite
            surface.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2))
        else:
            tail_x = sx - int(self.dir_x * 10)
            tail_y = sy - int(self.dir_y * 10)
            pygame.draw.line(surface, COLOR_HUD_YELLOW, (tail_x, tail_y), (sx, sy), 3)


class ShotgunBlast:
    """Instant massive blast cone with high penetration. Supports horizontal and upward fire."""
    frames_r = None
    frames_l = None
    frames_u = None

    @classmethod
    def load_sprites(cls):
        if cls.frames_r is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            rects = [
                (140, 491, 58, 30),
                (201, 490, 62, 32),
                (266, 490, 64, 32),
                (338, 491, 61, 30),
                (402, 490, 65, 32),
                (470, 489, 65, 33),
                (9, 529, 62, 33),
                (74, 528, 64, 34)
            ]
            cls.frames_r = [SpriteLoader.get_subsurface(sheet, *r) for r in rects]
            cls.frames_l = [pygame.transform.flip(f, True, False) for f in cls.frames_r]
            cls.frames_u = [pygame.transform.rotate(f, 90) for f in cls.frames_r]
        except Exception as e:
            print(f"[Shotgun] Error loading blast frames: {e}")
            cls.frames_r = []
            cls.frames_l = []
            cls.frames_u = []

    def __init__(self, x, y, facing_right=True, aiming_up=False, damage=20, owner=None):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.aiming_up = aiming_up
        self.damage = damage
        self.owner = owner
        self.life = 14
        self.is_dead = False
        self.hit_enemies = set()
        self.load_sprites()
        
        if self.aiming_up:
            frames = self.frames_u
        else:
            frames = self.frames_r if facing_right else self.frames_l
        self.anim = Animation(frames, frame_duration=2, loop=False) if frames else None

    @property
    def hitbox(self):
        if self.aiming_up:
            w, h = 54.0, 85.0
            hx = self.x - w / 2.0
            hy = self.y - h
        else:
            w, h = 85.0, 50.0
            hx = self.x if self.facing_right else (self.x - w)
            hy = self.y - h / 2.0
            
        if hasattr(pygame, "FRect"):
            return pygame.FRect(hx, hy, w, h)
        return pygame.Rect(int(hx), int(hy), int(w), int(h))

    def update(self, camera=None):
        self.life -= 1
        if self.anim:
            self.anim.update()
        if self.life <= 0:
            self.is_dead = True
            return

        # Dynamically track owner position and facing so blast never lags behind while running
        if self.owner and not getattr(self.owner, 'is_dead', False):
            ow_facing = getattr(self.owner, 'facing_right', self.facing_right)
            ow_crouching = getattr(self.owner, 'is_crouching', False)
            if hasattr(self.owner, 'physics'):
                px = self.owner.physics.x
                py = self.owner.physics.y
            else:
                px = getattr(self.owner, 'x', self.x)
                py = getattr(self.owner, 'y', self.y)

            if self.aiming_up:
                self.x = px + (8.0 if ow_facing else -8.0) * 0.4
                self.y = py - 36.0
            elif ow_crouching:
                self.x = px + (18.0 if ow_facing else -18.0)
                self.y = py - 12.0
            else:
                self.x = px + (18.0 if ow_facing else -18.0)
                self.y = py - 22.0

            if ow_facing != self.facing_right:
                self.facing_right = ow_facing
                if not self.aiming_up and self.anim:
                    frames = self.frames_r if self.facing_right else self.frames_l
                    curr_idx = self.anim.current_frame
                    self.anim.frames = frames
                    self.anim.current_frame = min(curr_idx, len(frames) - 1)

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        if self.anim:
            img = self.anim.get_current_surface()
            if img:
                if self.aiming_up:
                    surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
                else:
                    ox = 0 if self.facing_right else -img.get_width()
                    surface.blit(img, (sx + ox, sy - img.get_height() // 2))
                return

        # Fallback polygon
        alpha_surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        color = (255, 255, 240, 200) if self.life > 6 else (255, 200, 100, 120)
        if self.aiming_up:
            pts = [(sx, sy), (sx - 24, sy - 70), (sx, sy - 85), (sx + 24, sy - 70)]
        else:
            pts = [
                (sx, sy),
                (sx + (70 if self.facing_right else -70), sy - 24),
                (sx + (85 if self.facing_right else -85), sy),
                (sx + (70 if self.facing_right else -70), sy + 24),
            ]
        pygame.draw.polygon(alpha_surf, color, pts)
        surface.blit(alpha_surf, (0, 0))


class RocketMissile:
    """Seeking rocket with authentic missile sprites, exhaust smoke and guidance."""
    frames_r = None
    frames_l = None
    frames_u = None

    @classmethod
    def load_sprites(cls):
        if cls.frames_r is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            raw1 = sheet.subsurface(pygame.Rect(4, 253, 50, 8))
            raw2 = sheet.subsurface(pygame.Rect(57, 253, 42, 8))

            f1 = pygame.Surface((52, 16), pygame.SRCALPHA)
            f1.blit(raw1, (52 - raw1.get_width(), 8 - raw1.get_height() // 2))

            f2 = pygame.Surface((52, 16), pygame.SRCALPHA)
            f2.blit(raw2, (52 - raw2.get_width(), 8 - raw2.get_height() // 2))

            cls.frames_r = [f1, f2]
            cls.frames_l = [pygame.transform.flip(f, True, False) for f in cls.frames_r]
            cls.frames_u = [pygame.transform.rotate(f, 90) for f in cls.frames_r]
        except Exception as e:
            print(f"[Rocket] Error loading sprites: {e}")
            cls.frames_r = []
            cls.frames_l = []
            cls.frames_u = []

    def __init__(self, x, y, facing_right=True, aiming_up=False, damage=12):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.aiming_up = aiming_up
        if self.aiming_up:
            self.vx = 0.0
            self.vy = -5.0
        else:
            self.vx = 3.5 if facing_right else -3.5
            self.vy = -1.0
        self.damage = damage
        self.smoke_timer = 0
        self.is_dead = False
        self.target = None
        self.load_sprites()
        
        frames = self.frames_u if self.aiming_up else (self.frames_r if facing_right else self.frames_l)
        self.anim = Animation(frames, frame_duration=3, loop=True) if frames else None

    @property
    def hitbox(self):
        w, h = 26.0, 10.0
        if hasattr(pygame, "FRect"):
            return pygame.FRect(self.x - w / 2.0, self.y - h / 2.0, w, h)
        return pygame.Rect(int(self.x - w / 2.0), int(self.y - h / 2.0), int(w), int(h))

    def update(self, enemies=None, particle_system=None, camera=None):
        if self.anim:
            self.anim.update()

        # Target acquisition for homing
        if not self.target or getattr(self.target, 'is_dead', False):
            if enemies:
                living = [e for e in enemies if not getattr(e, 'is_dead', False)]
                if living:
                    def get_pos(ent):
                        if hasattr(ent, 'physics'):
                            return ent.physics.x, ent.physics.y
                        return getattr(ent, 'x', 0.0), getattr(ent, 'y', 0.0)
                    self.target = min(living, key=lambda e: abs(get_pos(e)[0] - self.x) + abs(get_pos(e)[1] - self.y))

        # Guided steering curvature
        if self.target and not getattr(self.target, 'is_dead', False):
            if hasattr(self.target, 'physics'):
                tx = self.target.physics.x
                ty = self.target.physics.y - 16
            else:
                tx = getattr(self.target, 'x', self.x)
                ty = getattr(self.target, 'y', self.y) - 16
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 5:
                desired_vx = (dx / dist) * 7.0
                desired_vy = (dy / dist) * 7.0
                self.vx += (desired_vx - self.vx) * 0.14
                self.vy += (desired_vy - self.vy) * 0.14
        else:
            if not self.aiming_up:
                self.vx += 0.2 if self.facing_right else -0.2

        self.x += self.vx
        self.y += self.vy

        # Smoke trail behind rocket engine nozzle
        self.smoke_timer += 1
        if self.smoke_timer % 3 == 0 and particle_system:
            angle_rad = math.atan2(self.vy, self.vx)
            smoke_x = self.x - math.cos(angle_rad) * 16.0
            smoke_y = self.y - math.sin(angle_rad) * 16.0
            if hasattr(particle_system, "spawn_rocket_smoke"):
                particle_system.spawn_rocket_smoke(smoke_x, smoke_y)
            else:
                particle_system.spawn_casing(self.x, self.y, self.facing_right)

        if camera:
            sx, sy = camera.apply(self.x, self.y)
            if sx < -50 or sx > VIRTUAL_WIDTH + 50 or sy < -50 or sy > VIRTUAL_HEIGHT + 50:
                self.is_dead = True

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        if self.anim and self.frames_r:
            cur_idx = self.anim.current_frame % len(self.frames_r)
            base_frame = self.frames_r[cur_idx]
            angle = math.degrees(math.atan2(-self.vy, self.vx))
            img = pygame.transform.rotate(base_frame, angle)
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
            return

        # Fallback
        pygame.draw.ellipse(surface, (230, 40, 40), (sx - 11, sy - 7, 22, 14))


class FlameShotBall:
    """Rolling ball of fire with authentic animated fireball sprites and upward fire."""
    frames = None

    @classmethod
    def load_sprites(cls):
        if cls.frames is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=CHROMA_GREEN)
            rects = [
                (335, 608, 39, 32),
                (377, 608, 37, 32),
                (417, 608, 35, 32),
                (455, 607, 32, 33),
                (493, 605, 33, 35),
                (529, 607, 33, 33)
            ]
            cls.frames = [SpriteLoader.get_subsurface(sheet, *r) for r in rects]
        except Exception as e:
            print(f"[FlameShot] Error loading sprites: {e}")
            cls.frames = []

    def __init__(self, x, y, facing_right=True, aiming_up=False, damage=15):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.aiming_up = aiming_up
        if self.aiming_up:
            self.vx = 0.0
            self.vy = -5.5
        else:
            self.vx = 4.5 if facing_right else -4.5
            self.vy = 0.0
        self.damage = damage
        self.life = 75
        self.radius = 16.0
        self.is_dead = False
        self.hit_enemies = set()
        self.load_sprites()
        self.anim = Animation(self.frames, frame_duration=3, loop=True) if self.frames else None

    @property
    def hitbox(self):
        w = self.radius * 2.0
        if hasattr(pygame, "FRect"):
            return pygame.FRect(self.x - self.radius, self.y - self.radius, w, w)
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), int(w), int(w))

    def update(self, platforms=None, camera=None):
        self.life -= 1
        if self.life <= 0:
            self.is_dead = True
            return

        # Defensive check if single camera argument was passed positionally
        if platforms is not None and not hasattr(platforms, '__iter__'):
            camera = platforms
            platforms = None

        if self.anim:
            self.anim.update()

        self.x += self.vx
        self.y += self.vy

        if not self.aiming_up and platforms:
            for plat in platforms:
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None:
                    self.y = plat_y - self.radius + 2
                    break

        if camera:
            sx, sy = camera.apply(self.x, self.y)
            if sx < -40 or sx > VIRTUAL_WIDTH + 40 or sy < -40 or sy > VIRTUAL_HEIGHT + 40:
                self.is_dead = True

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        if self.anim:
            img = self.anim.get_current_surface()
            if img:
                if not self.facing_right and not self.aiming_up:
                    img = pygame.transform.flip(img, True, False)
                surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
                return

        pygame.draw.circle(surface, (240, 50, 0), (sx, sy), int(self.radius))
        pygame.draw.circle(surface, COLOR_HUD_YELLOW, (sx, sy), int(self.radius * 0.5))
