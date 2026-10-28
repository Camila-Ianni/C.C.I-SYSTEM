# -*- coding: utf-8 -*-
import os
import sys
import math
import random
import pathlib
import pygame

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CCI_ROOT = os.path.dirname(ROOT_DIR)
if CCI_ROOT not in sys.path:
    sys.path.insert(0, CCI_ROOT)

from ..personagens.Sonic import SonicSprite

class GreenHillZone:
    
    def __init__(self, tela):
        base = pathlib.Path(__file__).parent.parent.parent
        self.fundo_path = str(base / "img" / "cenarios" / "green-hills.png")
        self.musica_path = str(base / "audio" / "green-hill-zone.wav")
        self.tela = tela

        self.sonic = SonicSprite(x=60, y=350)
        self.grupo_sprites = pygame.sprite.Group(self.sonic)
        self.font = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 48)

        self.reset_zone()

    def reset_zone(self):
        self.time_seconds = 0.0
        self.particles = []

        # Classic Badnik Motobugs (patrolling on ground)
        self.enemies = [
            {"x": 340.0, "y": 385.0, "vx": -2.0, "facing": -1, "min_x": 220, "max_x": 420, "anim": 0.0, "alive": True},
            {"x": 600.0, "y": 385.0, "vx": 2.0, "facing": 1, "min_x": 490, "max_x": 720, "anim": 0.0, "alive": True},
        ]

        # Golden Rings
        self.rings = [
            {"x": 160, "y": 380, "collected": False},
            {"x": 190, "y": 340, "collected": False},
            {"x": 220, "y": 340, "collected": False},
            {"x": 250, "y": 380, "collected": False},
            {"x": 480, "y": 380, "collected": False},
            {"x": 510, "y": 340, "collected": False},
            {"x": 540, "y": 380, "collected": False},
        ]

        # Spikes Hazard
        self.spikes = [
            pygame.Rect(440, 420, 28, 20)
        ]

        self.fundo = pygame.image.load(self.fundo_path).convert()
        self.rodando = True

    def tocar_musica(self):
        try:
            pygame.mixer.music.load(self.musica_path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def renderizar_fundo(self):
        self.tela.blit(self.fundo, [0, 0])

    def rodar_cenario(self):
        self.renderizar_fundo()
        self.tocar_musica()
        self.sonic.x = 60
        self.sonic.y = 350
        self.sonic.velocidade_x = 0
        self.sonic.velocidade_y = 0
        self.sonic.is_jumping = False
        self.reset_zone()
        
    def atualizar_eventos(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_z):
                self.sonic.jump()
        elif evento.type == pygame.JOYBUTTONDOWN:
            if evento.button in (0, 2):  # A or X
                self.sonic.jump()

    def atualizar_cenario(self):
        dt = 0.016
        self.time_seconds += dt

        # Continuous frame-by-frame input (Never gets stuck)
        keys = pygame.key.get_pressed()
        vx = 0.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx += 8.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx -= 8.0

        # Gamepad directional polling
        for j in range(pygame.joystick.get_count()):
            try:
                js = pygame.joystick.Joystick(j)
                ax = js.get_axis(0)
                if abs(ax) > 0.25:
                    vx += 8.0 if ax > 0 else -8.0
                if js.get_numhats() > 0:
                    hx, hy = js.get_hat(0)
                    if hx != 0:
                        vx += 8.0 if hx > 0 else -8.0
                    if hy > 0:
                        self.sonic.jump()
            except Exception:
                pass

        if vx != 0:
            self.sonic.velocidade_x = vx
            self.sonic.facing = 1 if vx > 0 else -1
        else:
            self.sonic.velocidade_x = 0.0

        # Update Sonic
        self.sonic.update()

        # Update Motobugs
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"]
            e["anim"] += 0.2
            if e["x"] > e["max_x"]:
                e["x"] = e["max_x"]
                e["vx"] = -abs(e["vx"])
                e["facing"] = -1
            elif e["x"] < e["min_x"]:
                e["x"] = e["min_x"]
                e["vx"] = abs(e["vx"])
                e["facing"] = 1

            e_rect = pygame.Rect(int(e["x"]), int(e["y"]), 50, 40)
            s_rect = self.sonic.rect

            # Collision with Sonic
            if s_rect.colliderect(e_rect):
                # Jump attack defeats Badnik!
                if self.sonic.is_jumping and self.sonic.velocidade_y > 0 and s_rect.bottom <= e_rect.top + 32:
                    e["alive"] = False
                    self.sonic.score += 100
                    self.sonic.bounce()
                    # Sparkles
                    for _ in range(12):
                        self.particles.append({
                            "x": e["x"] + 25,
                            "y": e["y"] + 20,
                            "vx": random.uniform(-6, 6),
                            "vy": random.uniform(-6, 6),
                            "life": 0.4
                        })
                elif self.sonic.invuln_timer <= 0:
                    self.sonic.take_hit()

        # Update Golden Rings
        s_rect = self.sonic.rect
        for r in self.rings:
            if not r["collected"]:
                r_rect = pygame.Rect(r["x"] - 14, r["y"] - 14, 28, 28)
                if s_rect.colliderect(r_rect):
                    r["collected"] = True
                    self.sonic.rings += 1
                    self.sonic.score += 100
                    try:
                        import cci_rumble
                        cci_rumble.light_rumble()
                    except Exception:
                        pass

        # Spikes collision
        if self.sonic.invuln_timer <= 0:
            for sp in self.spikes:
                if s_rect.colliderect(sp) and not self.sonic.is_jumping:
                    self.sonic.take_hit()

        # Update Particles
        for pt in self.particles:
            pt["x"] += pt["vx"]
            pt["y"] += pt["vy"]
            pt["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]

        # RENDER
        self.renderizar_fundo()

        # Draw Spikes
        for sp in self.spikes:
            pts = [(sp.x, sp.bottom), (sp.x + sp.w // 2, sp.top), (sp.right, sp.bottom)]
            pygame.draw.polygon(self.tela, (180, 190, 210), pts)
            pygame.draw.polygon(self.tela, (240, 245, 255), pts, 2)

        # Draw Golden Rings (Rotating Animation)
        ring_scale = abs(math.cos(self.time_seconds * 5.0)) * 13.0
        for r in self.rings:
            if not r["collected"]:
                rx, ry = r["x"], r["y"]
                rw = max(3, int(ring_scale))
                pygame.draw.ellipse(self.tela, (255, 215, 0), (rx - rw, ry - 14, rw * 2, 28))
                pygame.draw.ellipse(self.tela, (255, 255, 220), (rx - max(1, rw - 3), ry - 9, max(2, (rw - 3) * 2), 18))

        # Draw Classic Badnik Motobugs
        for e in self.enemies:
            if e["alive"]:
                ex, ey = int(e["x"]), int(e["y"])
                facing = e["facing"]
                # Motobug Red Body Shell
                pygame.draw.ellipse(self.tela, (210, 30, 40), (ex, ey, 46, 32))
                pygame.draw.ellipse(self.tela, (255, 80, 80), (ex + 6, ey + 4, 34, 16))
                # Head / Face
                head_x = ex + 32 if facing == 1 else ex - 6
                pygame.draw.circle(self.tela, (180, 20, 30), (head_x + 8, ey + 14), 10)
                # Big Yellow Horn / Antenna
                pygame.draw.polygon(self.tela, (255, 220, 40), [(head_x + 6, ey + 6), (head_x + 12, ey - 4), (head_x + 14, ey + 6)])
                # Cartoon Eye
                eye_x = head_x + 10 if facing == 1 else head_x + 6
                pygame.draw.circle(self.tela, (255, 255, 255), (eye_x, ey + 12), 4)
                pygame.draw.circle(self.tela, (10, 10, 10), (eye_x + (1 if facing == 1 else -1), ey + 12), 2)
                # Black Roller Wheel with spokes
                wheel_anim = int(e["anim"] * 4) % 6
                pygame.draw.circle(self.tela, (30, 30, 35), (ex + 23, ey + 32), 9)
                pygame.draw.circle(self.tela, (160, 160, 180), (ex + 23, ey + 32), 4)

        # Draw Particles
        for pt in self.particles:
            pygame.draw.circle(self.tela, (255, 220, 50), (int(pt["x"]), int(pt["y"])), 4)

        # Draw Sonic (Flash if invulnerable)
        if self.sonic.invuln_timer <= 0 or int(self.sonic.invuln_timer * 12) % 2 == 0:
            self.grupo_sprites.draw(self.tela)

        # Draw HUD (Classic Sonic Top-Left HUD)
        txt_score = self.font.render(f"SCORE   {self.sonic.score}", True, (255, 230, 0))
        mins = int(self.time_seconds // 60)
        secs = int(self.time_seconds % 60)
        txt_time = self.font.render(f"TIME      {mins:02d}:{secs:02d}", True, (255, 230, 0))
        txt_rings = self.font.render(f"RINGS   {self.sonic.rings:02d}", True, (255, 230, 0))
        txt_lives = self.font.render(f"LIVES   {self.sonic.lives}", True, (255, 255, 255))

        self.tela.blit(txt_score, (20, 20))
        self.tela.blit(txt_time, (20, 45))
        self.tela.blit(txt_rings, (20, 70))
        self.tela.blit(txt_lives, (20, 95))
