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

class MarbleZone:
    
    def __init__(self, tela):
        base = pathlib.Path(__file__).parent.parent.parent
        self.fundo_path = str(base / "img" / "cenarios" / "marble-zone.jpg")
        self.musica_path = str(base / "audio" / "marble-zone.wav")
        self.eggman_dir = base / "img" / "eggman"
        self.tela = tela

        self.sonic = SonicSprite(x=40, y=350)
        self.grupo_sprites = pygame.sprite.Group(self.sonic)
        self.font = pygame.font.Font(None, 28)

        # Load Dr. Robotnik / Eggman
        self.eggman_img = pygame.image.load(str(self.eggman_dir / "esquerda.png")).convert_alpha()

        self.reset_zone()

    def reset_zone(self):
        self.time_seconds = 0.0
        self.fundo = pygame.image.load(self.fundo_path).convert()
        self.rodando = True

        # Eggman Boss hovering
        self.eggman = {
            "x": 640.0,
            "y": 200.0,
            "hp": 5,
            "hover": 0.0,
            "alive": True
        }

        # Rings
        self.rings = [
            {"x": 180, "y": 380, "collected": False},
            {"x": 220, "y": 340, "collected": False},
            {"x": 260, "y": 380, "collected": False},
            {"x": 440, "y": 360, "collected": False},
            {"x": 480, "y": 360, "collected": False},
        ]

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
        self.sonic.x = 40
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
        self.time_seconds += 0.016
        self.sonic.update()

        # Update Eggman
        if self.eggman["alive"]:
            self.eggman["hover"] += 0.05
            self.eggman["y"] = 220.0 + math.sin(self.eggman["hover"]) * 40.0
            e_rect = pygame.Rect(int(self.eggman["x"]), int(self.eggman["y"]), 55, 55)
            s_rect = self.sonic.rect

            # Hit Eggman
            if s_rect.colliderect(e_rect) and self.sonic.is_jumping:
                self.eggman["hp"] -= 1
                self.sonic.bounce()
                self.sonic.score += 500
                if self.eggman["hp"] <= 0:
                    self.eggman["alive"] = False

        # Rings
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

        # End of zone wrap
        if self.sonic.rect[0] > self.tela.get_rect()[2]:
            try:
                pygame.mixer.music.fadeout(500)
            except Exception:
                pass
            self.rodando = False

        # RENDER
        self.renderizar_fundo()

        # Draw Rings
        ring_scale = abs(math.cos(self.time_seconds * 5.0)) * 12.0
        for r in self.rings:
            if not r["collected"]:
                rx, ry = r["x"], r["y"]
                rw = max(3, int(ring_scale))
                pygame.draw.ellipse(self.tela, (255, 215, 0), (rx - rw, ry - 12, rw * 2, 24))

        # Draw Eggman
        if self.eggman["alive"]:
            self.tela.blit(self.eggman_img, (int(self.eggman["x"]), int(self.eggman["y"])))

        # Draw Sonic
        if self.sonic.invuln_timer <= 0 or int(self.sonic.invuln_timer * 12) % 2 == 0:
            self.grupo_sprites.draw(self.tela)

        # Draw HUD
        txt_score = self.font.render(f"SCORE   {self.sonic.score}", True, (255, 230, 0))
        mins = int(self.time_seconds // 60)
        secs = int(self.time_seconds % 60)
        txt_time = self.font.render(f"TIME      {mins:02d}:{secs:02d}", True, (255, 230, 0))
        txt_rings = self.font.render(f"RINGS   {self.sonic.rings:02d}", True, (255, 230, 0))
        self.tela.blit(txt_score, (20, 20))
        self.tela.blit(txt_time, (20, 45))
        self.tela.blit(txt_rings, (20, 70))