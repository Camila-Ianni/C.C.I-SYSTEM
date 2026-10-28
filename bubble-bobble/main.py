#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUBBLE BOBBLE — Classic Arcade Experience for C.C.I. SYSTEM
Full arcade platformer mechanics:
- Authentic Bub dragon physics: walking, jumping, falling through platforms
- Bubble shooting: trap enemies, float bubbles upward, bounce on bubbles
- Popping trapped enemies: bursts into bonus fruit items (+1000 pts)
- Zen-chan enemies with platform pathfinding, jumping, and angry mode
- Full gamepad / joystick controls + force feedback vibration
"""

import os
import sys
import math
import random
import pygame
import numpy as np

# Change directory and add system path for cci_rumble
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT_DIR)
sys.path.insert(0, os.path.dirname(ROOT_DIR))

# Sound Synthesizer for Retro 8-bit SFX
def make_sound(freq_start, freq_end, duration, wave_type='sine', volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    freqs = np.linspace(freq_start, freq_end, n_samples)
    phase = 2 * np.pi * np.cumsum(freqs) / sample_rate

    if wave_type == 'square':
        wave = np.sign(np.sin(phase))
    elif wave_type == 'saw':
        wave = 2 * (t * freqs - np.floor(0.5 + t * freqs))
    elif wave_type == 'noise':
        wave = np.random.uniform(-1, 1, n_samples)
    else:
        wave = np.sin(phase)

    # Apply envelope
    env = np.linspace(1, 0, n_samples) ** 1.5
    audio = (wave * env * volume * 32767).astype(np.int16)
    audio = np.ascontiguousarray(audio)
    return pygame.sndarray.make_sound(audio)

def main():
    pygame.init()
    pygame.font.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

    try:
        pygame.joystick.init()
        joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for j in joysticks:
            j.init()
    except Exception:
        joysticks = []

    WIDTH, HEIGHT = 960, 720
    flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("BUBBLE BOBBLE — C.C.I. SYSTEM")
    clock = pygame.time.Clock()

    # Generate SFX
    try:
        snd_shoot = make_sound(400, 850, 0.12, 'sine', 0.25)
        snd_jump = make_sound(260, 520, 0.15, 'square', 0.2)
        snd_pop = make_sound(300, 100, 0.18, 'noise', 0.3)
        snd_fruit = make_sound(600, 1200, 0.22, 'sine', 0.3)
        snd_hurt = make_sound(350, 80, 0.35, 'saw', 0.35)
        snd_clear = make_sound(500, 1000, 0.5, 'sine', 0.3)
    except Exception:
        snd_shoot = snd_jump = snd_pop = snd_fruit = snd_hurt = snd_clear = None

    font_hud = pygame.font.SysFont("Courier", 22, bold=True)
    font_large = pygame.font.SysFont("Courier", 44, bold=True)

    # Platforms geometry (Classic Round 1 Tier Layout)
    # Platforms are one-way: player can jump up through them, and land on top
    platforms = [
        # Outer border / floor
        pygame.Rect(40, 680, 880, 24),
        # Tier 1 (Low): Left & Right ledges with middle gap
        pygame.Rect(40, 550, 360, 20),
        pygame.Rect(560, 550, 360, 20),
        # Tier 2 (Mid): Center bridge
        pygame.Rect(230, 420, 500, 20),
        # Tier 3 (High): Left & Right ledges with gap
        pygame.Rect(40, 290, 360, 20),
        pygame.Rect(560, 290, 360, 20),
        # Tier 4 (Top): Center platform
        pygame.Rect(280, 160, 400, 20),
    ]

    # Pre-render Platform Surface with retro green/cyan arcade brick styling
    def draw_platforms(surface):
        for p in platforms:
            # Brick body
            pygame.draw.rect(surface, (20, 140, 180), p, border_radius=4)
            # Top highlight
            pygame.draw.rect(surface, (80, 230, 255), (p.x, p.y, p.w, 4), border_radius=2)
            # Brick mortar lines
            brick_w = 40
            for bx in range(p.x, p.x + p.w, brick_w):
                pygame.draw.line(surface, (10, 80, 110), (bx, p.y), (bx, p.y + p.h), 2)
            pygame.draw.rect(surface, (10, 60, 80), p, 2, border_radius=4)

    # Game State
    score = 0
    high_score = 30000
    lives = 3
    round_num = 1
    round_timer = 0.0
    cleared_timer = 0.0

    # Bub dragon player
    player = {
        "x": 120.0,
        "y": 630.0,
        "w": 40,
        "h": 40,
        "vx": 0.0,
        "vy": 0.0,
        "facing": 1,      # 1 = right, -1 = left
        "on_ground": True,
        "invuln": 2.0,     # Invulnerability seconds after spawn/hit
        "anim_timer": 0.0,
        "mouth_timer": 0.0,
    }

    # Bubbles: list of {x, y, vx, vy, life, radius, trapped_enemy: None or dict, pop: bool}
    bubbles = []
    # Enemies: list of {x, y, vx, vy, facing, state: 'walk'|'angry', jump_timer, anim_timer}
    enemies = []
    # Fruits: list of {x, y, vy, type, value, timer}
    fruits = []
    # Particles for pop animations
    particles = []

    def spawn_enemies(count):
        enemies.clear()
        spawn_spots = [
            (300, 120), (600, 120), (480, 380),
            (160, 250), (800, 250), (480, 120)
        ]
        for i in range(count):
            sp = spawn_spots[i % len(spawn_spots)]
            enemies.append({
                "x": float(sp[0] + random.randint(-40, 40)),
                "y": float(sp[1]),
                "w": 38,
                "h": 38,
                "vx": random.choice([-120.0, 120.0]),
                "vy": 0.0,
                "facing": 1 if random.random() > 0.5 else -1,
                "state": "walk",
                "jump_timer": random.uniform(1.0, 3.5),
                "anim_timer": 0.0,
                "angry": False
            })

    spawn_enemies(3)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)  # Guard against lag spikes

        round_timer += dt
        if player["invuln"] > 0:
            player["invuln"] -= dt
        if player["mouth_timer"] > 0:
            player["mouth_timer"] -= dt

        # Enemies get angry after 25 seconds
        if round_timer > 25.0:
            for e in enemies:
                e["angry"] = True

        # Input handling
        shoot_pressed = False
        jump_pressed = False
        drop_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_z, pygame.K_k):
                    shoot_pressed = True
                elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_x, pygame.K_j):
                    jump_pressed = True
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    drop_pressed = True
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in (0, 2):  # A or X
                    jump_pressed = True
                elif event.button in (1, 3):  # B or Y
                    shoot_pressed = True
                elif event.button in (6, 7):  # Back / Start
                    running = False

        keys = pygame.key.get_pressed()
        move_x = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x += 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            drop_pressed = True

        # Gamepad directional polling
        for j in joysticks:
            try:
                ax = j.get_axis(0)
                ay = j.get_axis(1)
                if abs(ax) > 0.2:
                    move_x += ax
                if ay > 0.5:
                    drop_pressed = True
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    if hx != 0:
                        move_x += hx
                    if hy < 0:
                        drop_pressed = True
                    elif hy > 0 and not jump_pressed:
                        jump_pressed = True
            except Exception:
                pass

        move_x = max(-1.0, min(1.0, move_x))
        if abs(move_x) > 0.1:
            player["vx"] = move_x * 240.0
            player["facing"] = 1 if move_x > 0 else -1
            player["anim_timer"] += dt * 10.0
        else:
            player["vx"] = 0.0

        # Jump physics
        if jump_pressed and player["on_ground"]:
            player["vy"] = -520.0
            player["on_ground"] = False
            if snd_jump:
                snd_jump.play()

        # Drop through platform
        if drop_pressed and player["on_ground"]:
            # Check if not on bottom floor
            if player["y"] < 630.0:
                player["y"] += 6.0
                player["on_ground"] = False

        # Shoot bubble
        if shoot_pressed:
            player["mouth_timer"] = 0.2
            bx = player["x"] + (42 if player["facing"] == 1 else -14)
            by = player["y"] + 8
            bubbles.append({
                "x": bx,
                "y": by,
                "vx": player["facing"] * 420.0,
                "vy": -25.0,
                "life": 5.0,
                "radius": 18,
                "trapped_enemy": None,
                "pop": False
            })
            if snd_shoot:
                snd_shoot.play()
            try:
                import cci_rumble
                cci_rumble.light_rumble()
            except Exception:
                pass

        # Apply gravity to Player
        if not player["on_ground"]:
            player["vy"] += 1100.0 * dt

        player["x"] += player["vx"] * dt
        player["y"] += player["vy"] * dt

        # Horizontal screen wrap / bounds
        if player["x"] < 30:
            player["x"] = 30
        elif player["x"] > WIDTH - 70:
            player["x"] = WIDTH - 70

        # Platform collisions (Only land when falling downwards)
        player_rect = pygame.Rect(int(player["x"]), int(player["y"]), player["w"], player["h"])
        player["on_ground"] = False

        if player["vy"] >= 0:
            feet_prev_y = (player["y"] - player["vy"] * dt) + player["h"]
            for p in platforms:
                # If player feet crossed the top of platform this frame
                if player_rect.right > p.left and player_rect.left < p.right:
                    if feet_prev_y <= p.top + 8 and player_rect.bottom >= p.top:
                        player["y"] = p.top - player["h"]
                        player["vy"] = 0.0
                        player["on_ground"] = True
                        player_rect.bottom = p.top
                        break

        # Bottom floor safety
        if player["y"] >= 640.0:
            player["y"] = 640.0
            player["vy"] = 0.0
            player["on_ground"] = True

        # Update Bubbles
        for b in bubbles:
            b["life"] -= dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            # Rapid initial slowdown, then float gently upward
            b["vx"] *= 0.90
            b["vy"] = max(-65.0, b["vy"] - 60.0 * dt)
            # Gentle horizontal wobble
            b["x"] += math.sin(b["life"] * 6.0) * 0.8

            # Float bounds
            if b["y"] < 90.0:
                b["y"] = 90.0
                b["vy"] = 0.0

            b_rect = pygame.Rect(int(b["x"] - b["radius"]), int(b["y"] - b["radius"]),
                                 int(b["radius"] * 2), int(b["radius"] * 2))

            # Check if bubble traps an enemy
            if b["trapped_enemy"] is None:
                for e in enemies:
                    e_rect = pygame.Rect(int(e["x"]), int(e["y"]), e["w"], e["h"])
                    if b_rect.colliderect(e_rect):
                        b["trapped_enemy"] = e
                        b["radius"] = 24
                        enemies.remove(e)
                        if snd_shoot:
                            snd_shoot.play()
                        break

            # Check if player touches / pops bubble
            if player_rect.colliderect(b_rect):
                # If landing from above, bounce on bubble
                if player["vy"] > 0 and player_rect.bottom <= b_rect.centery + 10:
                    player["vy"] = -420.0
                    player["on_ground"] = False

                # Pop trapped bubble
                if b["trapped_enemy"] is not None:
                    b["pop"] = True
                    score += 1000
                    # Spawn bonus Fruit
                    fruits.append({
                        "x": b["x"],
                        "y": b["y"],
                        "vy": -150.0,
                        "type": random.choice(["banana", "apple", "watermelon"]),
                        "value": 1000,
                        "timer": 8.0
                    })
                    # Spawn sparkle particles
                    for _ in range(12):
                        particles.append({
                            "x": b["x"], "y": b["y"],
                            "vx": random.uniform(-180, 180),
                            "vy": random.uniform(-180, 180),
                            "color": random.choice([(255, 255, 100), (80, 220, 255), (255, 100, 200)]),
                            "life": 0.45
                        })
                    if snd_pop:
                        snd_pop.play()
                    try:
                        import cci_rumble
                        cci_rumble.hit_rumble()
                    except Exception:
                        pass
                else:
                    # Pop normal bubble after brief existence
                    if b["life"] < 4.5:
                        b["pop"] = True
                        for _ in range(6):
                            particles.append({
                                "x": b["x"], "y": b["y"],
                                "vx": random.uniform(-100, 100),
                                "vy": random.uniform(-100, 100),
                                "color": (120, 240, 255),
                                "life": 0.25
                            })

        # Remove dead/popped bubbles
        bubbles = [b for b in bubbles if b["life"] > 0 and not b["pop"]]

        # Update Enemies
        for e in enemies:
            speed = 170.0 if e["angry"] else 110.0
            e["anim_timer"] += dt * (12.0 if e["angry"] else 6.0)
            e["jump_timer"] -= dt

            # Horizontal movement
            e["x"] += e["facing"] * speed * dt
            if e["x"] < 50:
                e["x"] = 50
                e["facing"] = 1
            elif e["x"] > WIDTH - 90:
                e["x"] = WIDTH - 90
                e["facing"] = -1

            # Enemy Jump AI (randomly jump or chase toward player)
            if e["jump_timer"] <= 0:
                e["jump_timer"] = random.uniform(2.0, 5.0)
                if random.random() < 0.6:
                    e["vy"] = -480.0

            # Gravity
            e["vy"] += 1000.0 * dt
            e["y"] += e["vy"] * dt

            # Platform landing
            e_rect = pygame.Rect(int(e["x"]), int(e["y"]), e["w"], e["h"])
            if e["vy"] >= 0:
                for p in platforms:
                    if e_rect.right > p.left and e_rect.left < p.right:
                        if e_rect.bottom >= p.top and e_rect.bottom <= p.top + 20:
                            e["y"] = p.top - e["h"]
                            e["vy"] = 0.0
                            break

            if e["y"] >= 640.0:
                e["y"] = 640.0
                e["vy"] = 0.0

            # Enemy touches Player
            if player["invuln"] <= 0 and player_rect.colliderect(e_rect):
                lives -= 1
                player["invuln"] = 2.5
                player["x"], player["y"] = 120.0, 630.0
                player["vy"] = -300.0
                if snd_hurt:
                    snd_hurt.play()
                try:
                    import cci_rumble
                    cci_rumble.explosion_rumble()
                except Exception:
                    pass

        # Update Fruits
        for fr in fruits:
            fr["timer"] -= dt
            fr["vy"] += 600.0 * dt
            fr["y"] += fr["vy"] * dt
            fr_rect = pygame.Rect(int(fr["x"] - 14), int(fr["y"] - 14), 28, 28)
            # Land on platforms
            if fr["vy"] >= 0:
                for p in platforms:
                    if fr_rect.right > p.left and fr_rect.left < p.right:
                        if fr_rect.bottom >= p.top and fr_rect.bottom <= p.top + 16:
                            fr["y"] = p.top - 14
                            fr["vy"] = 0.0
                            break
            if fr["y"] >= 650.0:
                fr["y"] = 650.0
                fr["vy"] = 0.0

            # Collect fruit
            if player_rect.colliderect(fr_rect):
                score += fr["value"]
                fr["timer"] = 0.0
                if snd_fruit:
                    snd_fruit.play()
                try:
                    import cci_rumble
                    cci_rumble.light_rumble()
                except Exception:
                    pass

        fruits = [fr for fr in fruits if fr["timer"] > 0]

        # Update Particles
        for pt in particles:
            pt["life"] -= dt
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
        particles = [pt for pt in particles if pt["life"] > 0]

        # Wave Clear check
        if len(enemies) == 0 and not any(b["trapped_enemy"] for b in bubbles):
            cleared_timer += dt
            if cleared_timer > 2.0:
                round_num += 1
                round_timer = 0.0
                cleared_timer = 0.0
                score += 2000
                if snd_clear:
                    snd_clear.play()
                # Spawn more enemies up to 7
                spawn_enemies(min(7, 2 + round_num))
        else:
            cleared_timer = 0.0

        # High score
        if score > high_score:
            high_score = score

        # RENDER SCREEN
        screen.fill((8, 10, 18))

        # Background grid pattern
        for gy in range(0, HEIGHT, 40):
            pygame.draw.line(screen, (14, 18, 30), (0, gy), (WIDTH, gy), 1)

        # Draw Platforms
        draw_platforms(screen)

        # Draw Particles
        for pt in particles:
            rad = max(1, int(pt["life"] * 8))
            pygame.draw.circle(screen, pt["color"], (int(pt["x"]), int(pt["y"])), rad)

        # Draw Fruits
        for fr in fruits:
            fx, fy = int(fr["x"]), int(fr["y"])
            if fr["type"] == "banana":
                pygame.draw.ellipse(screen, (255, 230, 40), (fx - 14, fy - 10, 28, 20))
                pygame.draw.circle(screen, (100, 70, 20), (fx - 12, fy - 6), 3)
            elif fr["type"] == "apple":
                pygame.draw.circle(screen, (240, 40, 50), (fx, fy), 12)
                pygame.draw.line(screen, (80, 200, 60), (fx, fy - 12), (fx + 4, fy - 18), 3)
            else:
                pygame.draw.circle(screen, (40, 200, 60), (fx, fy), 14)
                pygame.draw.line(screen, (230, 40, 60), (fx - 10, fy), (fx + 10, fy), 4)

        # Draw Bubbles
        for b in bubbles:
            bx, by = int(b["x"]), int(b["y"])
            r = int(b["radius"])
            bsurf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)

            if b["trapped_enemy"] is not None:
                # Purple/Red trapped bubble
                pygame.draw.circle(bsurf, (230, 80, 160, 150), (r + 3, r + 3), r)
                pygame.draw.circle(bsurf, (255, 180, 220, 220), (r + 3, r + 3), r, 3)
                # Trapped monster face inside
                pygame.draw.circle(bsurf, (180, 40, 90), (r + 3, r + 3), int(r * 0.65))
                pygame.draw.circle(bsurf, (255, 255, 255), (r - 2, r), 4)
                pygame.draw.circle(bsurf, (255, 255, 255), (r + 8, r), 4)
                pygame.draw.circle(bsurf, (0, 0, 0), (r - 1, r), 2)
                pygame.draw.circle(bsurf, (0, 0, 0), (r + 9, r), 2)
            else:
                # Translucent Cyan/Green bubble with shiny highlight
                pygame.draw.circle(bsurf, (60, 210, 240, 130), (r + 3, r + 3), r)
                pygame.draw.circle(bsurf, (200, 250, 255, 220), (r + 3, r + 3), r, 2)
                pygame.draw.circle(bsurf, (255, 255, 255, 240), (r - 4, r - 4), 4)

            screen.blit(bsurf, (bx - r - 3, by - r - 3))

        # Draw Enemies (Zen-chan Wind-up Monsters)
        for e in enemies:
            ex, ey = int(e["x"]), int(e["y"])
            body_color = (230, 40, 50) if e["angry"] else (160, 60, 210)
            # Round monster body
            pygame.draw.circle(screen, body_color, (ex + 19, ey + 20), 18)
            # Wind-up key on head
            wobble = int(math.sin(e["anim_timer"]) * 3)
            pygame.draw.line(screen, (255, 210, 40), (ex + 19, ey + 2), (ex + 19, ey - 7), 3)
            pygame.draw.ellipse(screen, (255, 210, 40), (ex + 12 + wobble, ey - 14, 14, 8), 2)
            # Big Cartoon Eyes
            eye_off = 4 if e["facing"] == 1 else -4
            pygame.draw.circle(screen, (255, 255, 255), (ex + 14 + eye_off, ey + 17), 6)
            pygame.draw.circle(screen, (255, 255, 255), (ex + 24 + eye_off, ey + 17), 6)
            pygame.draw.circle(screen, (20, 20, 20), (ex + 15 + eye_off * 1.3, ey + 17), 3)
            pygame.draw.circle(screen, (20, 20, 20), (ex + 25 + eye_off * 1.3, ey + 17), 3)
            # Walking feet
            foot_w = int(math.sin(e["anim_timer"]) * 4)
            pygame.draw.circle(screen, (255, 140, 30), (ex + 10 + foot_w, ey + 36), 5)
            pygame.draw.circle(screen, (255, 140, 30), (ex + 28 - foot_w, ey + 36), 5)

        # Draw Player (Bub Dragon)
        # Flash if invulnerable
        if player["invuln"] <= 0 or int(player["invuln"] * 12) % 2 == 0:
            px, py = int(player["x"]), int(player["y"])
            bsurf = pygame.Surface((44, 44), pygame.SRCALPHA)
            # Body
            pygame.draw.rect(bsurf, (40, 200, 70), (6, 6, 32, 32), border_radius=9)
            # Yellow belly
            pygame.draw.rect(bsurf, (255, 240, 130), (12, 16, 18, 18), border_radius=6)
            # Orange back spikes
            pygame.draw.polygon(bsurf, (255, 110, 30), [(4, 12), (0, 18), (4, 24)])
            pygame.draw.polygon(bsurf, (255, 110, 30), [(4, 24), (0, 30), (4, 36)])
            # Big eyes
            eye_x = 28 if player["facing"] == 1 else 12
            pygame.draw.circle(bsurf, (255, 255, 255), (eye_x, 15), 6)
            pygame.draw.circle(bsurf, (20, 20, 40), (eye_x + (1 if player["facing"] == 1 else -1), 15), 3)
            # Snout / open mouth when shooting
            if player["mouth_timer"] > 0:
                mx = 36 if player["facing"] == 1 else 4
                pygame.draw.ellipse(bsurf, (255, 70, 70), (mx, 20, 8, 8))
            # Feet
            foot_anim = int(math.sin(player["anim_timer"]) * 4) if player["vx"] != 0 else 0
            pygame.draw.rect(bsurf, (255, 140, 30), (10 + foot_anim, 36, 10, 6), border_radius=3)
            pygame.draw.rect(bsurf, (255, 140, 30), (24 - foot_anim, 36, 10, 6), border_radius=3)

            if player["facing"] == -1:
                bsurf = pygame.transform.flip(bsurf, True, False)
            screen.blit(bsurf, (px, py))

        # HUD Top Bar
        hud_bg = pygame.Surface((WIDTH, 48))
        hud_bg.set_alpha(220)
        hud_bg.fill((8, 12, 24))
        screen.blit(hud_bg, (0, 0))

        score_txt = font_hud.render(f"1UP: {score:06d}   TOP: {high_score:06d}   ROUND: {round_num:02d}   LIVES: {'❤ ' * max(0, lives)}", True, (255, 255, 255))
        screen.blit(score_txt, (30, 12))

        # Controls hint at bottom
        ctrl_txt = font_hud.render("FLECHAS / D-PAD: MOVER   ESPACIO / A: SALTAR   Z / B: BURBUJA   ESC: SALIR", True, (160, 180, 210))
        screen.blit(ctrl_txt, ((WIDTH - ctrl_txt.get_width()) // 2, HEIGHT - 22))

        # Round clear overlay
        if cleared_timer > 0.1:
            clear_lbl = font_large.render("★ ROUND CLEAR! ★", True, (255, 230, 50))
            screen.blit(clear_lbl, ((WIDTH - clear_lbl.get_width()) // 2, HEIGHT // 2 - 40))

        # Game Over check
        if lives <= 0:
            go_lbl = font_large.render("GAME OVER", True, (240, 50, 60))
            screen.blit(go_lbl, ((WIDTH - go_lbl.get_width()) // 2, HEIGHT // 2 - 40))
            pygame.display.flip()
            pygame.time.delay(2000)
            running = False

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
