#!/usr/bin/env python3
import os
import sys
import math
import random
import pygame

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 960, 720
    flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Wonder Boy in Monster World - Retro Arcade Edition")
    clock = pygame.time.Clock()

    font_hud = pygame.font.SysFont("Courier", 22, bold=True)
    font_title = pygame.font.SysFont("Courier", 32, bold=True)

    # Hero state
    px, py = 150.0, 520.0
    vx, vy = 0.0, 0.0
    on_ground = True
    facing = 1  # 1 = right, -1 = left
    attacking = 0  # timer
    gold = 150
    hearts = 4
    max_hearts = 5

    # Slimes / Monsters
    monsters = [
        {"x": 450.0, "y": 530.0, "vx": 60.0, "min_x": 380, "max_x": 580, "alive": True},
        {"x": 750.0, "y": 530.0, "vx": -50.0, "min_x": 680, "max_x": 860, "alive": True},
    ]

    # Floating chests/gems
    gems = [
        {"rect": pygame.Rect(320, 420, 24, 24), "collected": False},
        {"rect": pygame.Rect(600, 380, 24, 24), "collected": False},
        {"rect": pygame.Rect(800, 440, 24, 24), "collected": False},
    ]

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_z, pygame.K_x, pygame.K_j, pygame.K_SPACE):
                    attacking = 15
                elif event.key in (pygame.K_UP, pygame.K_w) and on_ground:
                    vy = -480.0
                    on_ground = False

        keys = pygame.key.get_pressed()
        vx = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx = -220.0
            facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx = 220.0
            facing = 1

        # Physics
        if not on_ground:
            vy += 980.0 * dt
        px += vx * dt
        py += vy * dt

        if py >= 520.0:
            py = 520.0
            vy = 0.0
            on_ground = True

        px = max(40.0, min(WIDTH - 80.0, px))

        if attacking > 0:
            attacking -= 1

        # Hero hitbox
        hero_box = pygame.Rect(int(px), int(py), 38, 54)
        sword_box = pygame.Rect(int(px + (38 if facing == 1 else -30)), int(py + 15), 32, 25) if attacking > 0 else None

        # Update Monsters
        for m in monsters:
            if m["alive"]:
                m["x"] += m["vx"] * dt
                if m["x"] > m["max_x"] or m["x"] < m["min_x"]:
                    m["vx"] *= -1
                m_rect = pygame.Rect(int(m["x"]), int(m["y"]), 36, 32)
                # Sword hit
                if sword_box and sword_box.colliderect(m_rect):
                    m["alive"] = False
                    gold += 50
                # Player collision
                elif hero_box.colliderect(m_rect) and attacking == 0:
                    px -= facing * 30.0

        # Collect gems
        for g in gems:
            if not g["collected"] and hero_box.colliderect(g["rect"]):
                g["collected"] = True
                gold += 100

        # Draw Sky Background & Sun
        screen.fill((70, 145, 220))
        pygame.draw.circle(screen, (255, 240, 140), (820, 120), 45)

        # Clouds
        for cx, cy in [(140, 110), (450, 80), (670, 150)]:
            pygame.draw.ellipse(screen, (245, 250, 255), (cx, cy, 140, 45))
            pygame.draw.ellipse(screen, (245, 250, 255), (cx + 30, cy - 15, 80, 50))

        # Castle Silhouette
        pygame.draw.rect(screen, (90, 100, 140), (740, 280, 150, 290))
        pygame.draw.polygon(screen, (70, 80, 120), [(720, 280), (815, 180), (910, 280)])
        pygame.draw.rect(screen, (50, 60, 90), (795, 480, 40, 90), border_top_left_radius=20, border_top_right_radius=20)

        # Green Rolling Hills
        pygame.draw.ellipse(screen, (40, 140, 60), (-100, 420, 650, 350))
        pygame.draw.ellipse(screen, (55, 165, 75), (420, 440, 650, 350))

        # Ground Platform
        pygame.draw.rect(screen, (139, 90, 43), (0, 574, WIDTH, 146))
        pygame.draw.rect(screen, (46, 139, 87), (0, 560, WIDTH, 24))

        # Draw Gems
        for g in gems:
            if not g["collected"]:
                gx, gy = g["rect"].x, g["rect"].y
                pygame.draw.polygon(screen, (0, 220, 255), [(gx + 12, gy), (gx + 24, gy + 12), (gx + 12, gy + 24), (gx, gy + 12)])
                pygame.draw.polygon(screen, (255, 255, 255), [(gx + 12, gy + 4), (gx + 18, gy + 12), (gx + 12, gy + 18), (gx + 6, gy + 12)])

        # Draw Monsters (Snail / Slime)
        for m in monsters:
            if m["alive"]:
                mx, my = int(m["x"]), int(m["y"])
                pygame.draw.ellipse(screen, (210, 80, 80), (mx, my + 8, 36, 24))
                pygame.draw.circle(screen, (255, 255, 255), (mx + (26 if m['vx'] > 0 else 10), my + 14), 5)
                pygame.draw.circle(screen, (30, 30, 30), (mx + (28 if m['vx'] > 0 else 8), my + 14), 2)

        # Draw Wonder Boy Hero
        hx, hy = int(px), int(py)
        # Armor Body
        pygame.draw.rect(screen, (60, 130, 230), (hx + 6, hy + 18, 26, 24), border_radius=4)
        # Head / Hair
        pygame.draw.circle(screen, (255, 210, 175), (hx + 19, hy + 12), 11)
        pygame.draw.arc(screen, (90, 50, 25), (hx + 8, hy + 2, 22, 18), 0, 3.14, 5)
        # Shield (on back or hand)
        shield_x = hx - 4 if facing == 1 else hx + 26
        pygame.draw.ellipse(screen, (218, 165, 32), (shield_x, hy + 16, 14, 22))
        # Sword
        if attacking > 0:
            sw_x = hx + 30 if facing == 1 else hx - 28
            pygame.draw.rect(screen, (230, 240, 255), (sw_x, hy + 22, 28, 6), border_radius=2)
            pygame.draw.rect(screen, (160, 110, 50), (sw_x - (2 if facing == 1 else -24), hy + 20, 6, 10))

        # HUD Top
        hud_bg = pygame.Surface((WIDTH, 48))
        hud_bg.set_alpha(200)
        hud_bg.fill((15, 20, 35))
        screen.blit(hud_bg, (0, 0))

        hud_txt = font_hud.render(f"WONDER BOY   HEARTS: {'❤ ' * hearts}  GOLD: {gold}G   ARROWS: MOVER   Z / ESPACIO: ESPADA   ESC: SALIR", True, (255, 255, 255))
        screen.blit(hud_txt, (20, 12))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
