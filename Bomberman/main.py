#!/usr/bin/env python3
"""
BOMBERMAN (Pygame Retro Arcade Edition)
Adapted for C.C.I. SYSTEM Virtual Console
"""
import os
import sys

# Ensure current directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)
os.chdir(CURRENT_DIR)

import pygame
from bomberman import Bomberman
from manage import Manage
from board import Board
from check import checkboard
from enemy import Enemy

# Colors
DARK_BG = (10, 11, 14)
FLOOR_COLOR = (24, 30, 26)
FLOOR_ALT = (20, 26, 22)
WALL_COLOR = (70, 85, 120)
WALL_TOP = (110, 130, 180)
WALL_SHADOW = (40, 50, 75)
BRICK_COLOR = (180, 80, 50)
BRICK_MORTAR = (210, 110, 70)
BRICK_DARK = (130, 50, 30)
WHITE = (245, 247, 250)
YELLOW = (255, 220, 50)
ORANGE = (255, 120, 20)
RED = (230, 40, 40)
CYAN = (80, 220, 240)


class PygameBomberman(Bomberman):
    """Subclass of Bomberman with non-blocking key inputs for Pygame GUI."""

    def move_char(self, char):
        if char == "w" and checkboard(self, Bomberman.bombera, Bomberman.bomberb - 1) == "empty":
            if checkboard(self, Bomberman.bombera, Bomberman.bomberb) != "bomb":
                for j in range(4):
                    Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = " "
                    Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = " "
            Bomberman.bomberb -= 1
            for j in range(4):
                Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = "B"
                Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = "B"

        elif char == "s" and checkboard(self, Bomberman.bombera, Bomberman.bomberb + 1) == "empty":
            if checkboard(self, Bomberman.bombera, Bomberman.bomberb) != "bomb":
                for j in range(4):
                    Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = " "
                    Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = " "
            Bomberman.bomberb += 1
            for j in range(4):
                Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = "B"
                Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = "B"

        elif char == "a" and checkboard(self, Bomberman.bombera - 1, Bomberman.bomberb) == "empty":
            if checkboard(self, Bomberman.bombera, Bomberman.bomberb) != "bomb":
                for j in range(4):
                    Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = " "
                    Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = " "
            Bomberman.bombera -= 1
            for j in range(4):
                Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = "B"
                Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = "B"

        elif char == "d" and checkboard(self, Bomberman.bombera + 1, Bomberman.bomberb) == "empty":
            if checkboard(self, Bomberman.bombera, Bomberman.bomberb) != "bomb":
                for j in range(4):
                    Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = " "
                    Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = " "
            Bomberman.bombera += 1
            for j in range(4):
                Board.board[(Bomberman.bomberb + 1) * 2][(Bomberman.bombera + 1) * 4 + j] = "B"
                Board.board[(Bomberman.bomberb + 1) * 2 + 1][(Bomberman.bombera + 1) * 4 + j] = "B"

        elif char == "b":
            self.generatebomb(Bomberman.bombera, Bomberman.bomberb)


def run_game():
    pygame.init()
    pygame.font.init()

    # Window resolution 1280x720 fullscreen scaled
    SCREEN_W, SCREEN_H = 1280, 720
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN | pygame.SCALED)
    pygame.display.set_caption("BOMBERMAN — C.C.I. SYSTEM")
    clock = pygame.time.Clock()

    # Board layout: 84 cols x 42 rows
    # Cell size on screen: 13x14 pixels = 1092 x 588
    TILE_W, TILE_H = 13, 14
    GRID_X = (SCREEN_W - (84 * TILE_W)) // 2
    GRID_Y = 80

    font_large = pygame.font.SysFont("Courier New", 20, bold=True)
    font_small = pygame.font.SysFont("Courier New", 14, bold=True)

    # Initialize game objects
    game = PygameBomberman()
    manager = Manage()
    Manage.lives = 3
    Manage.score = 0
    Manage.time = 180

    # Reset board state
    for i in range(42):
        if i < 2 or i >= 40:
            Board.board[i] = Board.boundaryWalls[:]
        elif (i - 2) % 4 < 2:
            Board.board[i] = Board.normalRow[:]
        else:
            Board.board[i] = Board.normalRowWithBricks[:]

    Enemy.enemypostions = []
    Bomberman.bombera = 0
    Bomberman.bomberb = 0

    game.generatebricks()
    game.generateenemies()
    game.generatebomberman()

    step_counter = 0
    timer_second_accum = 0.0
    running = True

    while running:
        dt = clock.tick(30) / 1000.0
        timer_second_accum += dt
        if timer_second_accum >= 1.0:
            timer_second_accum -= 1.0
            if Manage.time > 0:
                Manage.time -= 1

        pending_char = ""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_w, pygame.K_UP):
                    pending_char = "w"
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    pending_char = "s"
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    pending_char = "a"
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    pending_char = "d"
                elif event.key in (pygame.K_SPACE, pygame.K_b):
                    pending_char = "b"

        if pending_char:
            game.move_char(pending_char)

        # Enemies move every 8 frames
        step_counter += 1
        if step_counter >= 8:
            game.moveenemies()
            game.bombcounter()
            step_counter = 0

        # Draw frame
        screen.fill(DARK_BG)

        # Header HUD
        hud_bar = pygame.Rect(GRID_X, 20, 84 * TILE_W, 46)
        pygame.draw.rect(screen, (18, 20, 26), hud_bar, border_radius=6)
        pygame.draw.rect(screen, (60, 70, 90), hud_bar, 2, border_radius=6)

        t_lives = font_large.render(f"LIVES: {Manage.lives}", True, CYAN)
        t_score = font_large.render(f"SCORE: {Manage.score:05d}", True, YELLOW)
        t_time = font_large.render(f"TIME: {Manage.time}s", True, WHITE if Manage.time > 30 else RED)
        t_controls = font_small.render("ARROWS/WASD: MOVE   SPACE: BOMB   ESC: SALIR", True, (140, 145, 155))

        screen.blit(t_lives, (hud_bar.x + 20, hud_bar.y + 12))
        screen.blit(t_score, (hud_bar.centerx - t_score.get_width() // 2, hud_bar.y + 12))
        screen.blit(t_time, (hud_bar.right - t_time.get_width() - 20, hud_bar.y + 12))
        screen.blit(t_controls, (SCREEN_W // 2 - t_controls.get_width() // 2, SCREEN_H - 35))

        # Arena background
        arena_rect = pygame.Rect(GRID_X, GRID_Y, 84 * TILE_W, 42 * TILE_H)
        pygame.draw.rect(screen, FLOOR_COLOR, arena_rect)
        pygame.draw.rect(screen, WALL_TOP, arena_rect, 2)

        # Draw cells
        for row in range(42):
            for col in range(84):
                ch = Board.board[row][col]
                x = GRID_X + col * TILE_W
                y = GRID_Y + row * TILE_H
                cell_rect = pygame.Rect(x, y, TILE_W, TILE_H)

                if ch == "X":
                    pygame.draw.rect(screen, WALL_COLOR, cell_rect)
                    pygame.draw.rect(screen, WALL_TOP, (x, y, TILE_W, 2))
                    pygame.draw.rect(screen, WALL_SHADOW, (x, y + TILE_H - 2, TILE_W, 2))
                elif ch == "/":
                    pygame.draw.rect(screen, BRICK_COLOR, cell_rect)
                    pygame.draw.rect(screen, BRICK_MORTAR, cell_rect, 1)
                elif ch == "B":
                    pygame.draw.rect(screen, WHITE, cell_rect.inflate(-1, -1), border_radius=2)
                    pygame.draw.rect(screen, CYAN, (x + 2, y + 2, TILE_W - 4, 3))
                elif ch == "E":
                    pygame.draw.rect(screen, RED, cell_rect.inflate(-1, -1), border_radius=2)
                    pygame.draw.circle(screen, YELLOW, (x + TILE_W // 2, y + TILE_H // 2), 2)
                elif ch in ("1", "2", "3", "[", "]"):
                    pygame.draw.circle(screen, (30, 30, 35), cell_rect.center, min(TILE_W, TILE_H) // 2)
                    pygame.draw.circle(screen, ORANGE, cell_rect.center, 3)
                elif ch == "e":
                    pygame.draw.rect(screen, ORANGE, cell_rect)
                    pygame.draw.rect(screen, YELLOW, cell_rect.inflate(-3, -3))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_game()
