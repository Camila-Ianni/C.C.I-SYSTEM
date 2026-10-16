import pygame

# Configuración Global de Da Vinci Fighters

# Pantalla y Rendimiento
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Da Vinci Fighters"

# Formato Arcade Clásico 4:3 con laterales negros (Pillarbox)
ARCADE_WIDTH = 960       # 720 * (4 / 3) = 960 px (proporción arcade cuadrada tradicional)
ARCADE_HEIGHT = 720
PILLARBOX_OFFSET_X = (SCREEN_WIDTH - ARCADE_WIDTH) // 2  # 160 px de margen negro a cada lado

# Física y Escenario
GROUND_Y = 600          # Coordenada Y del suelo
GRAVITY = 0.8           # Fuerza de gravedad
JUMP_FORCE = -16        # Fuerza de salto
PLAYER_SPEED = 6        # Velocidad de movimiento horizontal

# Modos de Juego
MODE_PVP = "pvp"
MODE_PVAI = "pvai"

# Colores (RGB)
COLOR_BG = (25, 25, 35)
COLOR_GROUND = (60, 60, 80)
COLOR_GROUND_LINE = (200, 160, 40)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (220, 50, 50)
COLOR_GREEN = (50, 220, 50)
COLOR_BLUE = (50, 100, 220)
COLOR_YELLOW = (240, 200, 40)

# Mapeo Centralizado de Controles
CONTROLS_P1 = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "crouch": pygame.K_s,
    "punch_light": pygame.K_j,
    "punch_heavy": pygame.K_k,
    "kick_light": pygame.K_u,
    "kick_heavy": pygame.K_i,
    "block": pygame.K_l,
    "special": pygame.K_o,
    "ultimate": pygame.K_p,
}

CONTROLS_P2 = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "crouch": pygame.K_DOWN,
    "punch_light": pygame.K_KP1,
    "punch_heavy": pygame.K_KP2,
    "kick_light": pygame.K_KP4,
    "kick_heavy": pygame.K_KP5,
    "block": pygame.K_KP6,
    "special": pygame.K_KP7,
    "ultimate": pygame.K_KP8,
}
