import random
import pygame

"""
Tetris Classic Arcade
10 x 20 grid
Faithful replica of arcade layout and color palette.
"""

pygame.font.init()

# Global layout variables
col = 10  # 10 columns
row = 20  # 20 rows
block_size = 31  # 31px block size for crisp, authentic scaling

play_width = col * block_size   # 310
play_height = row * block_size  # 620

s_width = 800
s_height = 720

top_left_x = (s_width - play_width) // 2   # 245
top_left_y = (s_height - play_height) // 2 # 50

import os
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(_CURRENT_DIR, 'highscore.txt')
fontpath = os.path.join(_CURRENT_DIR, 'arcade.TTF')
if not os.path.exists(fontpath):
    fontpath = os.path.join(_CURRENT_DIR, 'arcade.ttf')

# Colors authentic to the original arcade release:
# S: Green (88, 207, 141)
# Z: Red (246, 12, 65)
# I: Cyan (41, 171, 227)
# O: Yellow (255, 222, 9)
# J: Dark Blue (17, 51, 149)
# L: Orange (236, 135, 28)
# T: Purple (178, 19, 132)

S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '.0...',
      '.....']]

I = [['.....',
      '..0..',
      '..0..',
      '..0..',
      '..0..'],
     ['.....',
      '0000.',
      '.....',
      '.....',
      '.....']]

O = [['.....',
      '.....',
      '.00..',
      '.00..',
      '.....']]

J = [['.....',
      '.0...',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..00.',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '...0.',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '.00..',
      '.....']]

L = [['.....',
      '...0.',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '..00.',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '.0...',
      '.....'],
     ['.....',
      '.00..',
      '..0..',
      '..0..',
      '.....']]

T = [['.....',
      '..0..',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '..0..',
      '.....']]

shapes = [S, Z, I, O, J, L, T]
shape_colors = [
    (88, 207, 141),   # S - Light Green
    (246, 12, 65),    # Z - Bright Red
    (41, 171, 227),   # I - Sky Blue / Cyan
    (255, 222, 9),    # O - Yellow
    (17, 51, 149),    # J - Deep Blue
    (236, 135, 28),   # L - Orange
    (178, 19, 132)    # T - Purple / Magenta
]


class Piece(object):
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = shape_colors[shapes.index(shape)]
        self.rotation = 0


def create_grid(locked_pos={}):
    grid = [[(0, 0, 0) for _ in range(col)] for _ in range(row)]
    for y in range(row):
        for x in range(col):
            if (x, y) in locked_pos:
                grid[y][x] = locked_pos[(x, y)]
    return grid


def convert_shape_format(piece):
    positions = []
    shape_format = piece.shape[piece.rotation % len(piece.shape)]
    for i, line in enumerate(shape_format):
        for j, column in enumerate(line):
            if column == '0':
                positions.append((piece.x + j, piece.y + i))
    for i, pos in enumerate(positions):
        positions[i] = (pos[0] - 2, pos[1] - 4)
    return positions


def valid_space(piece, grid):
    accepted_pos = [[(x, y) for x in range(col) if grid[y][x] == (0, 0, 0)] for y in range(row)]
    accepted_pos = [x for item in accepted_pos for x in item]
    formatted_shape = convert_shape_format(piece)
    for pos in formatted_shape:
        if pos not in accepted_pos:
            if pos[1] >= 0:
                return False
    return True


def check_lost(positions):
    for pos in positions:
        x, y = pos
        if y < 1:
            return True
    return False


def get_shape():
    return Piece(5, 0, random.choice(shapes))


def draw_text_middle(text, size, color, surface):
    font = pygame.font.Font(fontpath, size)
    font.set_italic(True)
    label = font.render(text, 1, color)
    surface.blit(label, (top_left_x + play_width // 2 - (label.get_width() // 2),
                         top_left_y + play_height // 2 - (label.get_height() // 2)))


def clear_rows(grid, locked):
    increment = 0
    for i in range(len(grid) - 1, -1, -1):
        grid_row = grid[i]
        if (0, 0, 0) not in grid_row:
            increment += 1
            index = i
            for j in range(len(grid_row)):
                try:
                    del locked[(j, i)]
                except ValueError:
                    continue

    if increment > 0:
        for key in sorted(list(locked), key=lambda a: a[1])[::-1]:
            x, y = key
            if y < index:
                new_key = (x, y + increment)
                locked[new_key] = locked.pop(key)

    return increment


def draw_single_block(surface, x, y, size, color):
    pygame.draw.rect(surface, color, (x, y, size, size))
    # Borde sutil de 1px entre bloques idéntico a las recreaciones clásicas
    pygame.draw.rect(surface, (0, 0, 0), (x, y, size, size), 1)


def draw_next_shape_queue(pieces_queue, surface):
    """Renderiza la columna derecha de NEXT con la cola vertical de próximas piezas."""
    font = pygame.font.Font(fontpath, 26)
    font.set_italic(True)
    label = font.render('NEXT', True, (255, 255, 255))

    rx = top_left_x + play_width + 40
    surface.blit(label, (rx + 25, top_left_y + 10))

    # Alturas verticales de las 3 siguientes piezas en la columna NEXT
    centers_y = [top_left_y + 85, top_left_y + 195, top_left_y + 305]
    mini_block_size = 25

    for idx, piece in enumerate(pieces_queue[:3]):
        shape_fmt = piece.shape[0]  # Orientación estándar para preview
        blocks = [(c, r) for r, line in enumerate(shape_fmt) for c, char in enumerate(line) if char == '0']
        if not blocks:
            continue
        xs = [b[0] for b in blocks]
        ys = [b[1] for b in blocks]
        w = max(xs) - min(xs) + 1
        h = max(ys) - min(ys) + 1
        center_x = rx + 65
        center_y = centers_y[idx]
        start_x = center_x - (w * mini_block_size) // 2
        start_y = center_y - (h * mini_block_size) // 2
        min_x = min(xs)
        min_y = min(ys)
        for bx, by in blocks:
            px = start_x + (bx - min_x) * mini_block_size
            py = start_y + (by - min_y) * mini_block_size
            draw_single_block(surface, px, py, mini_block_size, piece.color)


def draw_window(surface, grid, score=0, level=1, last_score=0):
    """Dibuja el marco arcade fiel a la recreación original."""
    # Fondo gabinete arcade oscuro
    surface.fill((8, 7, 12))

    # Tablero central con fondo azul marino (18, 31, 71)
    pygame.draw.rect(surface, (18, 31, 71), (top_left_x, top_left_y, play_width, play_height))
    # Marco rectangular blanco sólido de 3px alrededor del área de juego
    pygame.draw.rect(surface, (255, 255, 255), (top_left_x - 3, top_left_y - 3, play_width + 6, play_height + 6), 3)

    # Tipografía arcade itálica blanca
    font_title = pygame.font.Font(fontpath, 26)
    font_title.set_italic(True)
    font_val = pygame.font.Font(fontpath, 24)
    font_val.set_italic(True)

    # Columna izquierda: SCORE, LEVEL, HIGH SCORE
    lx = top_left_x - 170

    # 1. SCORE
    t_score = font_title.render("SCORE", True, (255, 255, 255))
    v_score = font_val.render(str(score), True, (255, 255, 255))
    surface.blit(t_score, (lx + (140 - t_score.get_width()) // 2, top_left_y + 40))
    surface.blit(v_score, (lx + (140 - v_score.get_width()) // 2, top_left_y + 75))

    # 2. LEVEL
    t_level = font_title.render("LEVEL", True, (255, 255, 255))
    v_level = font_val.render(str(level), True, (255, 255, 255))
    surface.blit(t_level, (lx + (140 - t_level.get_width()) // 2, top_left_y + 160))
    surface.blit(v_level, (lx + (140 - v_level.get_width()) // 2, top_left_y + 195))

    # 3. HIGH SCORE
    t_high = font_title.render("HIGH", True, (255, 255, 255))
    t_hs = font_title.render("SCORE", True, (255, 255, 255))
    v_high = font_val.render(str(last_score), True, (255, 255, 255))
    surface.blit(t_high, (lx + (140 - t_high.get_width()) // 2, top_left_y + 280))
    surface.blit(t_hs, (lx + (140 - t_hs.get_width()) // 2, top_left_y + 312))
    surface.blit(v_high, (lx + (140 - v_high.get_width()) // 2, top_left_y + 350))

    # Dibujar contenido de la cuadrícula con bloques sólidos
    for i in range(row):
        for j in range(col):
            c_val = grid[i][j]
            if c_val != (0, 0, 0):
                bx = top_left_x + j * block_size
                by = top_left_y + i * block_size
                draw_single_block(surface, bx, by, block_size, c_val)


def update_score(new_score):
    score = get_max_score()
    try:
        with open(filepath, 'w') as file:
            if new_score > score:
                file.write(str(new_score))
            else:
                file.write(str(score))
    except Exception:
        pass


def get_max_score():
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
            if lines:
                return int(lines[0].strip())
    except Exception:
        pass
    return 255


def main(window):
    locked_positions = {}
    change_piece = False
    run = True
    current_piece = get_shape()
    next_pieces_queue = [get_shape() for _ in range(3)]
    clock = pygame.time.Clock()
    fall_time = 0
    fall_speed = 0.35
    score = 0
    lines_cleared_total = 0
    level = 1
    last_score = get_max_score()

    while run:
        fall_time += clock.get_rawtime()
        clock.tick(60)

        if fall_time / 1000 > fall_speed:
            fall_time = 0
            current_piece.y += 1
            grid = create_grid(locked_positions)
            if not valid_space(current_piece, grid) and current_piece.y > 0:
                current_piece.y -= 1
                change_piece = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    run = False
                elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    current_piece.x -= 1
                    grid = create_grid(locked_positions)
                    if not valid_space(current_piece, grid):
                        current_piece.x += 1
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    current_piece.x += 1
                    grid = create_grid(locked_positions)
                    if not valid_space(current_piece, grid):
                        current_piece.x -= 1
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    current_piece.y += 1
                    grid = create_grid(locked_positions)
                    if not valid_space(current_piece, grid):
                        current_piece.y -= 1
                elif event.key == pygame.K_UP or event.key == pygame.K_w or event.key == pygame.K_SPACE:
                    current_piece.rotation = (current_piece.rotation + 1) % len(current_piece.shape)
                    grid = create_grid(locked_positions)
                    if not valid_space(current_piece, grid):
                        current_piece.rotation = (current_piece.rotation - 1) % len(current_piece.shape)

        piece_pos = convert_shape_format(current_piece)

        if change_piece:
            for pos in piece_pos:
                locked_positions[pos] = current_piece.color
            current_piece = next_pieces_queue.pop(0)
            next_pieces_queue.append(get_shape())
            change_piece = False
            cleared = clear_rows(create_grid(locked_positions), locked_positions)
            if cleared > 0:
                lines_cleared_total += cleared
                score += cleared * 10
                level = 1 + (lines_cleared_total // 10)
                fall_speed = max(0.08, 0.35 - (level - 1) * 0.03)
                update_score(score)
                if last_score < score:
                    last_score = score

        grid = create_grid(locked_positions)
        piece_pos = convert_shape_format(current_piece)
        for i in range(len(piece_pos)):
            x, y = piece_pos[i]
            if y >= 0:
                grid[y][x] = current_piece.color

        draw_window(window, grid, score, level, last_score)
        draw_next_shape_queue(next_pieces_queue, window)
        pygame.display.update()

        if check_lost(locked_positions):
            run = False

    draw_text_middle('You Lost', 40, (255, 255, 255), window)
    pygame.display.update()
    pygame.time.delay(1500)


def main_menu(window):
    run = True
    while run:
        draw_text_middle('Press any key to begin', 36, (255, 255, 255), window)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                main(window)
                run = False


if __name__ == '__main__':
    win = pygame.display.set_mode((s_width, s_height))
    pygame.display.set_caption('TETRIS CLASSIC ARCADE')
    main_menu(win)
