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
        self.gamma_dir = base / "img" / "gamma"
        self.tela = tela

        self.sonic = SonicSprite(x=60, y=350)
        self.grupo_sprites = pygame.sprite.Group(self.sonic)
        self.font = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 48)

        # Load Gamma Badnik robot sprites
        self.gamma_frames_left = [
            pygame.image.load(str(self.gamma_dir / f"gamma-esquerda-{i}.png")).convert_alpha()
            for i in (1, 2, 3)
        ]
        self.gamma_frames_right = [
            pygame.image.load(str(self.gamma_dir / f"gamma-direita-{i}.png")).convert_alpha()
            for i in (1, 2, 3)
        ]

        self.reset_zone()

    def reset_zone(self):
        self.time_seconds = 0.0
        self.particles = []

        # Enemies: Badnik Robots
        self.enemies = [
            {"x": 340.0, "y": 380.0, "vx": -2.0, "facing": -1, "min_x": 240, "max_x": 420, "frame": 0.0, "alive": True},
            {"x": 620.0, "y": 380.0, "vx": 2.0, "facing": 1, "min_x": 520, "max_x": 740, "frame": 0.0, "alive": True},
        ]

        # Golden Rings: {x, y, collected}
        self.rings = [
            {"x": 160, "y": 380, "collected": False},
            {"x": 190, "y": 350, "collected": False},
            {"x": 220, "y": 350, "collected": False},
            {"x": 250, "y": 380, "collected": False},
            {"x": 480, "y": 380, "collected": False},
            {"x": 510, "y": 350, "collected": False},
            {"x": 540, "y": 380, "collected": False},
        ]

        # Spikes Obstacle: {x, y, w, h}
        self.spikes = [
            pygame.Rect(450, 420, 24, 20)
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
            if evento.key in (pygame.K_RIGHT, pygame.K_d):
                self.sonic.velocidade_x = 8
                self.sonic.facing = 1
            elif evento.key in (pygame.K_LEFT, pygame.K_a):
                self.sonic.velocidade_x = -8
                self.sonic.facing = -1
            elif evento.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_z):
                self.sonic.jump()
        elif evento.type == pygame.KEYUP:
            if evento.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_LEFT, pygame.K_a):
                self.sonic.stop()
        elif evento.type == pygame.JOYBUTTONDOWN:
            if evento.button in (0, 2):  # A or X
                self.sonic.jump()
        elif evento.type == pygame.JOYHATMOTION:
            hx, hy = evento.value
            if hx > 0:
                self.sonic.velocidade_x = 8
                self.sonic.facing = 1
            elif hx < 0:
                self.sonic.velocidade_x = -8
                self.sonic.facing = -1
            else:
                self.sonic.stop()
            if hy > 0:
                self.sonic.jump()

    def atualizar_cenario(self):
        dt = 0.016
        self.time_seconds += dt

        # Update Sonic
        self.sonic.update()

        # Update Enemies
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"]
            e["frame"] = (e["frame"] + 0.15) % 3.0
            if e["x"] > e["max_x"]:
                e["x"] = e["max_x"]
                e["vx"] = -abs(e["vx"])
                e["facing"] = -1
            elif e["x"] < e["min_x"]:
                e["x"] = e["min_x"]
                e["vx"] = abs(e["vx"])
                e["facing"] = 1

            e_rect = pygame.Rect(int(e["x"]), int(e["y"]), 45, 60)
            s_rect = self.sonic.rect

            # Collision with Sonic
            if s_rect.colliderect(e_rect):
                # Sonic hits from above while jumping (Badnik defeat!)
                if self.sonic.is_jumping and self.sonic.velocidade_y > 0 and s_rect.bottom <= e_rect.top + 30:
                    e["alive"] = False
                    self.sonic.score += 100
                    self.sonic.bounce()
                    # Sparkles
                    for _ in range(10):
                        self.particles.append({
                            "x": e["x"] + 22,
                            "y": e["y"] + 30,
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
                r_rect = pygame.Rect(r["x"] - 12, r["y"] - 12, 24, 24)
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

        # Check end of stage
        if self.sonic.rect[0] > self.tela.get_rect()[2]:
            try:
                pygame.mixer.music.fadeout(500)
            except Exception:
                pass
            self.rodando = False

        # RENDER
        self.renderizar_fundo()

        # Draw Spikes
        for sp in self.spikes:
            pts = [(sp.x, sp.bottom), (sp.x + sp.w // 2, sp.top), (sp.right, sp.bottom)]
            pygame.draw.polygon(self.tela, (180, 190, 210), pts)
            pygame.draw.polygon(self.tela, (230, 240, 255), pts, 2)

        # Draw Golden Rings (Rotating Animation)
        ring_scale = abs(math.cos(self.time_seconds * 5.0)) * 12.0
        for r in self.rings:
            if not r["collected"]:
                rx, ry = r["x"], r["y"]
                rw = max(3, int(ring_scale))
                pygame.draw.ellipse(self.tela, (255, 215, 0), (rx - rw, ry - 12, rw * 2, 24))
                pygame.draw.ellipse(self.tela, (255, 255, 200), (rx - max(1, rw - 3), ry - 8, max(2, (rw - 3) * 2), 16))

        # Draw Badnik Robots
        for e in self.enemies:
            if e["alive"]:
                frames = self.gamma_frames_left if e["facing"] == -1 else self.gamma_frames_right
                frame_img = frames[int(e["frame"])]
                self.tela.blit(frame_img, (int(e["x"]), int(e["y"])))

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
