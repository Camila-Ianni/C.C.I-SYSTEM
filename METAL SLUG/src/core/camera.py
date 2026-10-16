"""
Metal Slug 2D Arcade Camera.
Features:
- Horizontal leading scroll with lookahead.
- Left-edge backward scroll prevention (classic arcade lock).
- Arena and Boss gate locking.
- Screen shake effect on explosions.
"""
import random
import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT

class Camera:
    def __init__(self, world_width=4000, world_height=224):
        self.world_width = world_width
        self.world_height = world_height
        self.x = 0.0
        self.y = 0.0
        
        # In Metal Slug, camera only scrolls forward (rightwards)
        self.max_scrolled_x = 0.0
        self.lock_x = None  # Arena gate lock
        
        # Screen Shake
        self.shake_time = 0.0
        self.shake_magnitude = 0.0
        self.shake_offset_x = 0
        self.shake_offset_y = 0

    def trigger_shake(self, duration_frames=12, magnitude=3):
        self.shake_time = duration_frames
        self.shake_magnitude = magnitude

    def update(self, target_x, target_y=None):
        # Metal Slug keeps player slightly to the left of the center (approx 120px from left)
        desired_x = target_x - 120.0
        
        # Never scroll backwards (leftwards)
        if desired_x > self.max_scrolled_x:
            self.max_scrolled_x = desired_x
        
        self.x = self.max_scrolled_x
        
        # Apply arena gate lock if active
        if self.lock_x is not None:
            self.x = min(self.x, self.lock_x)
            
        # Clamp to world bounds
        self.x = max(0.0, min(self.x, self.world_width - VIRTUAL_WIDTH))
        self.y = 0.0  # Mission 1 is primarily horizontally scrolled
        
        # Process Screen Shake
        if self.shake_time > 0:
            self.shake_time -= 1
            self.shake_offset_x = random.randint(-int(self.shake_magnitude), int(self.shake_magnitude))
            self.shake_offset_y = random.randint(-int(self.shake_magnitude), int(self.shake_magnitude))
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0

    def apply(self, world_x, world_y):
        """Translates world coordinates to screen coordinates with camera offset."""
        screen_x = int(world_x - self.x) + self.shake_offset_x
        screen_y = int(world_y - self.y) + self.shake_offset_y
        return screen_x, screen_y

    def lock_at(self, lock_x_pos):
        self.lock_x = lock_x_pos

    def unlock(self):
        self.lock_x = None

    @property
    def is_locked(self):
        return self.lock_x is not None
