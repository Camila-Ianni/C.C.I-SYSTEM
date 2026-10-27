#!/usr/bin/env python3
import os
import sys
import math
import pygame

# Set local directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 1200, 900
    flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Mario Kart - Retro Arcade Circuit")
    clock = pygame.time.Clock()

    # Load assets
    bg = pygame.image.load("assets/mario-kart-circuit.png").convert()
    bg_rect = bg.get_rect()

    mario_img_raw = pygame.image.load("assets/mario.png").convert_alpha()
    mario_orig = pygame.transform.flip(mario_img_raw, True, False)
    mario_rect = mario_orig.get_rect()

    yoshi_img_raw = pygame.image.load("assets/yoshi.png").convert_alpha()
    yoshi_orig = pygame.transform.flip(yoshi_img_raw, True, False)
    yoshi_rect = yoshi_orig.get_rect()

    boost_img = pygame.image.load("assets/boost_arrow.png").convert_alpha()
    banana_img = pygame.image.load("assets/banana.png").convert_alpha()

    # Boost locations & rotations
    boosts = [
        {"x": 320, "y": 160, "img": pygame.transform.flip(boost_img, True, False)},
        {"x": 140, "y": 420, "img": pygame.transform.rotate(boost_img, 270.0)},
        {"x": 930, "y": 490, "img": pygame.transform.rotate(boost_img, 90.0)},
        {"x": 530, "y": 710, "img": boost_img},
    ]
    for b in boosts:
        b["rect"] = b["img"].get_rect(topleft=(b["x"], b["y"]))

    # Bananas
    bananas = [
        {"rect": banana_img.get_rect(topleft=(160, 216)), "active": True},
        {"rect": banana_img.get_rect(topleft=(356, 755)), "active": True},
        {"rect": banana_img.get_rect(topleft=(620, 174)), "active": True},
        {"rect": banana_img.get_rect(topleft=(880, 410)), "active": True},
    ]

    # Player states
    mario_x, mario_y = 474.0, 134.0
    mario_angle = 0.0
    mario_speed = 0.0
    mario_spin = 0

    yoshi_x, yoshi_y = 474.0, 208.0
    yoshi_angle = 0.0
    yoshi_speed = 0.0
    yoshi_spin = 0

    font_hud = pygame.font.SysFont("Courier", 24, bold=True)
    font_large = pygame.font.SysFont("Courier", 36, bold=True)

    lap = 1
    max_laps = 3
    race_time = 0.0
    winner = None

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        if not winner:
            race_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()

        # Mario Driving (Player 1 - Arrows)
        if mario_spin > 0:
            mario_spin -= 1
            mario_angle += 25
            mario_speed *= 0.85
        else:
            if keys[pygame.K_UP]:
                mario_speed = min(mario_speed + 14.0 * dt, 7.5)
            elif keys[pygame.K_DOWN]:
                mario_speed = max(mario_speed - 12.0 * dt, -3.5)
            else:
                mario_speed *= 0.95

            if abs(mario_speed) > 0.3:
                steer = 3.5 if mario_speed > 0 else -3.5
                if keys[pygame.K_LEFT]:
                    mario_angle += steer
                if keys[pygame.K_RIGHT]:
                    mario_angle -= steer

        rad_m = math.radians(mario_angle)
        mario_x += mario_speed * math.cos(rad_m)
        mario_y -= mario_speed * math.sin(rad_m)

        # Boundaries
        mario_x = max(40, min(WIDTH - 80, mario_x))
        mario_y = max(40, min(HEIGHT - 80, mario_y))

        m_rot = pygame.transform.rotate(mario_orig, mario_angle)
        m_rect = m_rot.get_rect(center=(int(mario_x), int(mario_y)))

        # Yoshi Simple AI or Player 2 (WASD)
        has_p2 = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
        if has_p2:
            if yoshi_spin > 0:
                yoshi_spin -= 1
                yoshi_angle += 25
                yoshi_speed *= 0.85
            else:
                if keys[pygame.K_w]:
                    yoshi_speed = min(yoshi_speed + 14.0 * dt, 7.0)
                elif keys[pygame.K_s]:
                    yoshi_speed = max(yoshi_speed - 12.0 * dt, -3.0)
                else:
                    yoshi_speed *= 0.95
                if abs(yoshi_speed) > 0.3:
                    if keys[pygame.K_a]:
                        yoshi_angle += 3.5
                    if keys[pygame.K_d]:
                        yoshi_angle -= 3.5
            rad_y = math.radians(yoshi_angle)
            yoshi_x += yoshi_speed * math.cos(rad_y)
            yoshi_y -= yoshi_speed * math.sin(rad_y)
        else:
            # Subtle bot drift
            yoshi_x += 1.8 * math.cos(race_time * 0.8)
            yoshi_y += 1.2 * math.sin(race_time * 0.8)

        yoshi_x = max(40, min(WIDTH - 80, yoshi_x))
        yoshi_y = max(40, min(HEIGHT - 80, yoshi_y))
        y_rot = pygame.transform.rotate(yoshi_orig, yoshi_angle)
        y_rect = y_rot.get_rect(center=(int(yoshi_x), int(yoshi_y)))

        # Boost pads
        for b in boosts:
            if m_rect.colliderect(b["rect"]):
                mario_speed = min(mario_speed + 3.0, 12.0)
            if y_rect.colliderect(b["rect"]):
                yoshi_speed = min(yoshi_speed + 3.0, 11.0)

        # Bananas
        for ban in bananas:
            if ban["active"]:
                if m_rect.colliderect(ban["rect"]) and mario_spin == 0:
                    mario_spin = 30
                    ban["active"] = False
                elif y_rect.colliderect(ban["rect"]) and yoshi_spin == 0:
                    yoshi_spin = 30
                    ban["active"] = False

        # Draw Frame
        screen.blit(bg, bg_rect)

        for b in boosts:
            screen.blit(b["img"], b["rect"])

        for ban in bananas:
            if ban["active"]:
                screen.blit(banana_img, ban["rect"])

        screen.blit(y_rot, y_rect)
        screen.blit(m_rot, m_rect)

        # HUD
        speed_kmh = int(abs(mario_speed) * 18.0)
        hud_txt = font_hud.render(f"SPEED: {speed_kmh} KM/H   TIME: {race_time:.1f}s   P1: ARROWS (DRIVE)   ESC: SALIR", True, (255, 255, 255))
        hud_box = hud_txt.get_rect(topleft=(30, 20))
        bg_bar = pygame.Surface((hud_box.w + 20, hud_box.h + 10))
        bg_bar.set_alpha(180)
        bg_bar.fill((10, 10, 20))
        screen.blit(bg_bar, (hud_box.x - 10, hud_box.y - 5))
        screen.blit(hud_txt, hud_box)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
