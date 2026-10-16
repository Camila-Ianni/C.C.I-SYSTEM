"""
Particle and Visual FX Manager for Metal Slug 1.
Handles:
- Explosions (Small, Medium, Big) with animated frames.
- Bullet casings (ejected brass particles with bounce).
- Smoke puffs and debris.
- Hit flashes.
"""
import random
import pygame
from src.config import CHROMA_GREEN
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation

class Particle:
    def __init__(self, x, y, vx, vy, gravity=0.25, max_life=60):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.gravity = gravity
        self.life = max_life
        self.age = 0
        self.is_dead = False

    def update(self):
        self.age += 1
        if self.age >= self.life:
            self.is_dead = True
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity

    def draw(self, surface, camera):
        pass

class BulletCasing(Particle):
    def __init__(self, x, y, facing_right=True):
        # Brass bullet casing flies backwards and up
        vx = random.uniform(-1.8, -0.6) if facing_right else random.uniform(0.6, 1.8)
        vy = random.uniform(-2.5, -1.2)
        super().__init__(x, y, vx, vy, gravity=0.22, max_life=45)
        self.color = (255, 215, 0) # Gold brass

    def update(self):
        super().update()
        # Simulated floor bounce around y = ground
        if self.vy > 0 and self.y > 180: # generic ground level bounce
            self.vy = -self.vy * 0.4
            self.vx *= 0.6

    def draw(self, surface, camera):
        sx, sy = camera.apply(self.x, self.y)
        pygame.draw.rect(surface, self.color, (sx, sy, 2, 2))

class AnimatedFX:
    def __init__(self, x, y, animation, centered=True):
        self.x = float(x)
        self.y = float(y)
        self.animation = animation
        self.animation.loop = False
        self.animation.reset()
        self.centered = centered
        self.is_dead = False

    def update(self):
        self.animation.update()
        if self.animation.is_finished:
            self.is_dead = True

    def draw(self, surface, camera):
        img = self.animation.get_current_surface()
        if img:
            sx, sy = camera.apply(self.x, self.y)
            if self.centered:
                rect = img.get_rect(center=(sx, sy))
                surface.blit(img, rect)
            else:
                surface.blit(img, (sx, sy))

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.animated_effects = []
        self.explosion_sheets_loaded = False
        self.small_explosion_frames = []
        self.medium_explosion_frames = []
        self.big_explosion_frames = []
        self.muzzle_flash_frames = []

    def _slice_row(self, sheet, y, h, gaps):
        """Slice a horizontal strip of contiguous frames separated by gap-column runs.
        `gaps` is a list of the x-coordinate where each gap between frames begins.
        Frames run from the previous gap+3 to the next gap-1."""
        frames = []
        starts = [4] + [g + 3 for g in gaps[:-1]]
        ends = [g - 1 for g in gaps]
        for a, b in zip(starts, ends):
            if b > a:
                frames.append(SpriteLoader.get_subsurface(sheet, a, y, b - a + 1, h))
        return frames

    def load_effects(self):
        """Loads explosion sheets and slices animation frames using verified cell layout."""
        try:
            sheet_path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Explosion SFX.png"
            sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_GREEN)

            # Verified layout (auto-detected contiguous cells with 3px gaps):
            #   small  -> 9 cells, ~27px, y=45
            #   medium -> 18 cells, ~33px, y=5
            #   big    -> 12 cells, ~48px, y=89
            small_gaps = [30, 58, 84, 109, 134, 159, 183, 204, 223]
            medium_gaps = [36, 71, 102, 135, 169, 202, 235, 268, 301,
                           334, 367, 400, 432, 465, 497, 528, 557]
            big_gaps = [52, 103, 149, 195, 245, 292, 341, 391, 441, 489, 537]

            self.small_explosion_frames = self._slice_row(sheet, 42, 30, small_gaps)
            self.medium_explosion_frames = self._slice_row(sheet, 5, 40, medium_gaps)
            self.big_explosion_frames = self._slice_row(sheet, 89, 54, big_gaps)

            # Procedural muzzle flash (avoids depending on a wrongly-sliced sprite)
            self.muzzle_flash_frames = []
            for r in (3, 4, 5):
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 240, 160, 255), (r, r), r)
                pygame.draw.circle(s, (255, 255, 220, 255), (r, r), max(1, r - 1))
                self.muzzle_flash_frames.append(s)

            # Authentic rocket launcher smoke puffs
            sfx_path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Weapon SFX.png"
            sfx_sheet = SpriteLoader.load_sheet(sfx_path, colorkey=CHROMA_GREEN)
            smoke_rects = [
                (4, 473, 14, 10), (21, 472, 14, 11), (38, 471, 15, 12), (56, 471, 15, 12),
                (74, 469, 15, 14), (92, 468, 15, 15), (110, 467, 16, 16), (129, 466, 16, 17),
                (148, 465, 16, 17)
            ]
            self.rocket_smoke_frames = [SpriteLoader.get_subsurface(sfx_sheet, *r) for r in smoke_rects]

            self.explosion_sheets_loaded = True
        except Exception as e:
            print(f"[ParticleSystem] Error loading explosion frames: {e}")

    def spawn_casing(self, x, y, facing_right=True):
        self.particles.append(BulletCasing(x, y, facing_right))

    def spawn_rocket_smoke(self, x, y):
        if not self.explosion_sheets_loaded:
            self.load_effects()
        if hasattr(self, 'rocket_smoke_frames') and self.rocket_smoke_frames:
            anim = Animation(self.rocket_smoke_frames, frame_duration=2, loop=False)
            self.animated_effects.append(AnimatedFX(x, y, anim, centered=True))

    def spawn_muzzle_flash(self, x, y, dir_x=1.0, dir_y=0.0):
        if not self.explosion_sheets_loaded:
            self.load_effects()
        if self.muzzle_flash_frames:
            anim = Animation(self.muzzle_flash_frames, frame_duration=2, loop=False)
            self.animated_effects.append(AnimatedFX(x, y, anim, centered=True))

    def spawn_explosion(self, x, y, size="small"):
        if not self.explosion_sheets_loaded:
            self.load_effects()

        if size == "small":
            frames = self.small_explosion_frames
        elif size == "big":
            frames = self.big_explosion_frames
        else:
            frames = self.medium_explosion_frames
        if frames:
            anim = Animation(frames, frame_duration=3, loop=False)
            self.animated_effects.append(AnimatedFX(x, y, anim, centered=True))

    def update(self):
        # Update free particles
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.is_dead]

        # Update animated effects
        for fx in self.animated_effects:
            fx.update()
        self.animated_effects = [fx for fx in self.animated_effects if not fx.is_dead]

    def draw(self, surface, camera):
        for p in self.particles:
            p.draw(surface, camera)
        for fx in self.animated_effects:
            fx.draw(surface, camera)
