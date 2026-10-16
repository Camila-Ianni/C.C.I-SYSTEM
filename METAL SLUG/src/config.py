"""
Global Configuration and Constants for Metal Slug 1 Replica.
"""
import pygame

# Native Neo-Geo Resolution
VIRTUAL_WIDTH = 320
VIRTUAL_HEIGHT = 224

# Default Scaling Factor (3x = 960x672, 4x = 1280x896)
DEFAULT_SCALE = 3
WINDOW_WIDTH = VIRTUAL_WIDTH * DEFAULT_SCALE
WINDOW_HEIGHT = VIRTUAL_HEIGHT * DEFAULT_SCALE

FPS = 60
TITLE = "METAL SLUG: SUPER VEHICLE-001 (SNK Arcade Replica)"

# Physics Constants (Neo-Geo tuned: 60 ticks/sec)
GRAVITY = 0.38
MAX_FALL_SPEED = 7.0
PLAYER_WALK_SPEED = 1.75
PLAYER_JUMP_IMPULSE = -6.2
SLUG_SPEED = 1.6
SLUG_JUMP_IMPULSE = -5.0

# Chroma Key Colors used across ripped sprite sheets
CHROMA_CYAN = (153, 217, 234)    # #99D9EA (Marco, Tarma, Rebel Soldier, Slug)
CHROMA_GREEN = (0, 248, 0)       # #00F800 (SFX, Explosions, Weapon SFX)
CHROMA_MAGENTA = (255, 0, 255)   # #FF00FF (Background parts)
CHROMA_WHITE = (255, 255, 255)   # #FFFFFF (HUD & Interface)

# Standard Arcade Palette Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_HUD_YELLOW = (248, 208, 0)
COLOR_HUD_ORANGE = (248, 120, 0)
COLOR_HUD_RED = (232, 40, 0)

# Input Action Enums
ACTION_UP = "UP"
ACTION_DOWN = "DOWN"
ACTION_LEFT = "LEFT"
ACTION_RIGHT = "RIGHT"
ACTION_SHOOT = "SHOOT"     # Button A
ACTION_JUMP = "JUMP"       # Button B
ACTION_GRENADE = "GRENADE" # Button C
ACTION_START = "START"
ACTION_COIN = "COIN"

# Default Keyboard Controls
KEY_BINDINGS = {
    # Directionals
    pygame.K_LEFT: ACTION_LEFT,
    pygame.K_a: ACTION_LEFT,
    pygame.K_RIGHT: ACTION_RIGHT,
    pygame.K_d: ACTION_RIGHT,
    pygame.K_UP: ACTION_UP,
    pygame.K_w: ACTION_UP,
    pygame.K_DOWN: ACTION_DOWN,
    pygame.K_s: ACTION_DOWN,
    
    # Action Buttons (A, B, C)
    pygame.K_j: ACTION_SHOOT,       # A Button: Shoot / Melee
    pygame.K_k: ACTION_JUMP,        # B Button: Jump
    pygame.K_l: ACTION_GRENADE,     # C Button: Grenade / Bomb
    
    # Modern & Alternative action keys (Space, Z, X, C, F, E)
    pygame.K_SPACE: ACTION_JUMP,
    pygame.K_f: ACTION_SHOOT,
    pygame.K_e: ACTION_GRENADE,
    pygame.K_z: ACTION_SHOOT,
    pygame.K_x: ACTION_JUMP,
    pygame.K_c: ACTION_GRENADE,
    
    # System Keys
    pygame.K_RETURN: ACTION_START,
    pygame.K_5: ACTION_COIN,
    pygame.K_1: ACTION_START,
}
