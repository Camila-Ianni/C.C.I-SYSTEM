"""
Tick-based Animation Controller for Arcade Sprites.
Handles frame duration, loops, one-shots, and frame-trigger callbacks.
"""
import pygame

class Animation:
    def __init__(self, frames, frame_duration=6, loop=True, name="default"):
        self.name = name
        self.frames = frames  # List of pygame.Surface
        self.frame_duration = frame_duration  # Number of 60Hz ticks per frame
        self.loop = loop
        
        self.current_frame = 0
        self.tick_counter = 0
        self.is_finished = False
        self.frame_callbacks = {}  # {frame_index: callable}

    def reset(self):
        self.current_frame = 0
        self.tick_counter = 0
        self.is_finished = False

    def on_frame(self, frame_index, callback):
        """Registers a callback function to be called when reaching a specific frame."""
        self.frame_callbacks[frame_index] = callback

    def update(self):
        if not self.frames:
            return
        
        if self.is_finished:
            return
        
        self.tick_counter += 1
        if self.tick_counter >= self.frame_duration:
            self.tick_counter = 0
            
            # Check frame callback before advancing
            if self.current_frame in self.frame_callbacks:
                self.frame_callbacks[self.current_frame]()
                
            if self.current_frame + 1 < len(self.frames):
                self.current_frame += 1
            else:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.is_finished = True

    def get_current_surface(self):
        if not self.frames:
            return None
        return self.frames[min(self.current_frame, len(self.frames) - 1)]

    def get_frame_count(self):
        return len(self.frames)
