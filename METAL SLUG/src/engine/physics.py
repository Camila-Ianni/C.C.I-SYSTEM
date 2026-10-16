"""
Metal Slug 2D Arcade Physics and Collision Engine.
Handles:
- Sub-pixel float movement and velocity accumulation.
- Semi-solid platforms (pass-through from below, drop-through with Down+B).
- Slopes and solid terrain detection.
- Hurtbox / Hitbox intersection testing.
"""
import pygame
from src.config import GRAVITY, MAX_FALL_SPEED
from src.engine.pymunk_physics import PymunkPhysicsWorld

class Platform:
    """Represents a walkable horizontal or sloped surface in world coordinates."""
    def __init__(self, x1, y1, x2, y2, semi_solid=True):
        self.x1 = float(min(x1, x2))
        self.y1 = float(y1 if x1 <= x2 else y2)
        self.x2 = float(max(x1, x2))
        self.y2 = float(y2 if x1 <= x2 else y1)
        self.semi_solid = semi_solid

    def get_height_at(self, x):
        """Returns the y-coordinate of the platform surface at the given world x."""
        if not (self.x1 <= x <= self.x2):
            return None
        if self.x2 == self.x1:
            return self.y1
        # Linear interpolation for slopes
        t = (x - self.x1) / (self.x2 - self.x1)
        return self.y1 + t * (self.y2 - self.y1)

    @property
    def frect(self):
        """Floating-point FRect for subpixel collision bounding."""
        FRectClass = getattr(pygame, 'FRect', pygame.Rect)
        return FRectClass(
            self.x1,
            min(self.y1, self.y2),
            max(1.0, self.x2 - self.x1),
            max(1.0, abs(self.y2 - self.y1))
        )

class PhysicsBody:
    def __init__(self, x, y, width=20, height=36):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = width
        self.height = height
        
        self.is_grounded = False
        self.current_platform = None
        self.ignore_platform_timer = 0  # Used when dropping down platforms
        self.ignored_platform = None

    @property
    def bottom(self):
        return self.y

    @property
    def center_x(self):
        return self.x

    @property
    def hurtbox(self):
        # Bounding rect centered at (self.x, self.y - height)
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height),
            int(self.width),
            int(self.height)
        )

    @property
    def frect(self):
        """High-precision floating-point FRect for subpixel hit testing."""
        FRectClass = getattr(pygame, 'FRect', pygame.Rect)
        return FRectClass(
            float(self.x - self.width / 2.0),
            float(self.y - self.height),
            float(self.width),
            float(self.height)
        )

    def apply_gravity(self, custom_gravity=GRAVITY):
        if not self.is_grounded:
            self.vy = min(self.vy + custom_gravity, MAX_FALL_SPEED)

    def update_movement(self, platforms=None):
        """Applies velocity, performs terrain checking and updates grounded state."""
        # Horizontal Movement with Step/Wall Collision
        old_x = self.x
        self.x += self.vx

        if platforms and self.is_grounded and self.vx != 0:
            for plat in platforms:
                if not plat.semi_solid:
                    plat_y = plat.get_height_at(self.x)
                    if plat_y is not None and plat_y < self.y - 12.0:
                        # Impassable vertical wall check (wall height > 12px)
                        self.x = old_x
                        self.vx = 0.0
                        break
        
        # Platform dropping cooldown
        if self.ignore_platform_timer > 0:
            self.ignore_platform_timer -= 1
            if self.ignore_platform_timer == 0:
                self.ignored_platform = None
        
        # Vertical Movement
        old_y = self.y
        self.y += self.vy
        was_grounded = self.is_grounded
        was_platform = self.current_platform
        self.is_grounded = False
        self.current_platform = None
        
        if platforms:
            snap_tolerance = max(2.0, abs(self.vx) * 0.5 + 2.0)
            step_down_max = 8.0  # Max height per frame to step down steps smoothly
            step_up_max = 12.0   # Max height per frame to step up steps/slopes
            
            best_plat = None
            best_plat_y = None
            min_dist = float('inf')

            for plat in platforms:
                if self.ignore_platform_timer > 0:
                    if self.ignored_platform is not None and plat is self.ignored_platform:
                        continue
                    elif self.ignored_platform is None and plat.semi_solid:
                        continue
                    
                plat_y = plat.get_height_at(self.x)
                if plat_y is not None:
                    dy = plat_y - old_y
                    is_valid = False

                    # 1. Standard Landing / Ground Snapping from above
                    if self.vy >= 0 and old_y <= plat_y + snap_tolerance and self.y >= plat_y - 2.0:
                        is_valid = True
                    # 2. Stepping DOWN a small drop when already grounded
                    elif was_grounded and self.vy >= 0 and 0 < dy <= step_down_max:
                        if not plat.semi_solid or was_platform is plat:
                            is_valid = True
                    # 3. Stepping UP a step or slope when already grounded
                    elif was_grounded and self.vx != 0 and -step_up_max <= dy < 0:
                        if not plat.semi_solid or was_platform is plat:
                            is_valid = True

                    if is_valid:
                        dist = abs(dy)
                        if dist < min_dist:
                            min_dist = dist
                            best_plat = plat
                            best_plat_y = plat_y

            if best_plat is not None:
                self.y = best_plat_y
                self.vy = 0.0
                self.is_grounded = True
                self.current_platform = best_plat
                self.ignored_platform = None
                self.ignore_platform_timer = 0

    def drop_through_platform(self):
        """Allows character to fall through semi-solid platforms (Down + Jump)."""
        if self.is_grounded and self.current_platform and self.current_platform.semi_solid:
            self.is_grounded = False
            self.ignore_platform_timer = 12  # Ignore platform for 12 frames
            self.ignored_platform = self.current_platform
            self.y += 1.0
            self.vy = 1.0
