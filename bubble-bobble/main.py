#!/usr/bin/env python3
import os
import sys
import glob
import math
import random
import pygame

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 960, 896
    flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Bubble Bobble - Classic Arcade")
    clock = pygame.time.Clock()

    # Load arcade frames
    frame_files = sorted(glob.glob("assets_arcade/frame_*.png"))
    frames = []
    if frame_files:
        for f in frame_files:
            frames.append(pygame.image.load(f).convert())
    else:
        # Fallback dark background
        fb = pygame.Surface((WIDTH, HEIGHT))
        fb.fill((10, 10, 20))
        frames.append(fb)

    font_hud = pygame.font.SysFont("Courier", 24, bold=True)
    font_large = pygame.font.SysFont("Courier", 36, bold=True)

    # Bub Dragon Player state
    px, py = 120.0, 750.0
    vx, vy = 0.0, 0.0
    on_ground = True
    facing = 1  # 1 = right, -1 = left

    # Bubbles list: [{'x', 'y', 'vx', 'vy', 'life', 'radius'}]
    bubbles = []
    score = 0
    lives = 3
    frame_idx = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        frame_idx = (frame_idx + 12.0 * dt) % len(frames)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Shoot bubble
                    bx = px + (40 if facing == 1 else -10)
                    by = py + 15
                    bubbles.append({
                        "x": bx,
                        "y": by,
                        "vx": facing * 320.0,
                        "vy": -40.0,
                        "life": 4.5,
                        "radius": 16,
                        "pop": False
                    })
                    try:
                        import cci_rumble
                        cci_rumble.light_rumble()
                    except Exception:
                        pass
                elif event.key in (pygame.K_UP, pygame.K_w) and on_ground:
                    vy = -450.0
                    on_ground = False

        keys = pygame.key.get_pressed()
        vx = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx = -220.0
            facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx = 220.0
            facing = 1

        # Gravity & Physics
        if not on_ground:
            vy += 980.0 * dt
        px += vx * dt
        py += vy * dt

        # Floor collision
        if py >= 750.0:
            py = 750.0
            vy = 0.0
            on_ground = True

        px = max(60.0, min(WIDTH - 100.0, px))

        # Update Bubbles
        for b in bubbles:
            b["life"] -= dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            # Decelerate horizontal, drift up
            b["vx"] *= 0.94
            b["vy"] = max(-100.0, b["vy"] - 40.0 * dt)
            # Wobble
            b["x"] += math.sin(b["life"] * 10.0) * 1.2
            if b["y"] < 120.0:
                b["y"] = 120.0
                b["vy"] = 0.0

        # Remove dead bubbles
        bubbles = [b for b in bubbles if b["life"] > 0]

        # Draw Frame
        current_bg = frames[int(frame_idx)]
        screen.blit(current_bg, (0, 0))

        # Draw Bubbles
        for b in bubbles:
            bx, by = int(b["x"]), int(b["y"])
            r = int(b["radius"])
            # Transparent cyan bubble with shiny highlight
            surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (80, 220, 255, 140), (r + 2, r + 2), r)
            pygame.draw.circle(surf, (220, 255, 255, 220), (r + 2, r + 2), r, 2)
            pygame.draw.circle(surf, (255, 255, 255, 240), (r - 3, r - 3), 4)
            screen.blit(surf, (bx - r, by - r))

        # Draw Player (Retro Green Dinosaur Bub)
        bub_rect = pygame.Rect(int(px), int(py), 42, 44)
        bub_surf = pygame.Surface((44, 46), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(bub_surf, (50, 205, 50), (6, 8, 32, 34), border_radius=8)
        # Belly
        pygame.draw.rect(bub_surf, (255, 255, 150), (12, 18, 20, 20), border_radius=6)
        # Spikes
        pygame.draw.polygon(bub_surf, (255, 120, 50), [(4, 14), (0, 20), (4, 26)])
        pygame.draw.polygon(bub_surf, (255, 120, 50), [(4, 26), (0, 32), (4, 38)])
        # Eye
        eye_x = 28 if facing == 1 else 14
        pygame.draw.circle(bub_surf, (255, 255, 255), (eye_x, 16), 5)
        pygame.draw.circle(bub_surf, (20, 20, 20), (eye_x + (1 if facing == 1 else -1), 16), 3)

        if facing == -1:
            bub_surf = pygame.transform.flip(bub_surf, True, False)
        screen.blit(bub_surf, bub_rect)

        # HUD Overlay
        score_txt = font_hud.render(f"1UP: {score:06d}   LIVES: {'❤' * lives}   FLECHAS: MOVER   ESPACIO: DISPARAR BURBUJA   ESC: SALIR", True, (255, 255, 255))
        hud_bg = pygame.Surface((WIDTH, 44))
        hud_bg.set_alpha(190)
        hud_bg.fill((10, 10, 25))
        screen.blit(hud_bg, (0, 0))
        screen.blit(score_txt, (30, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
