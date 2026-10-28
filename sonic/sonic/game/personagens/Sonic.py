# -*- coding: utf-8 -*-
from pygame.sprite import Sprite
import pygame
import pathlib

def carregar_imagem(nome):
    path = pathlib.Path(__file__).parent.parent.parent / "img" / "sonic" / nome
    return pygame.image.load(str(path)).convert_alpha()

class SonicSprite(Sprite):

    def __init__(self, x=60, y=350):
        super(SonicSprite, self).__init__()

        self.velocidade_x = 0
        self.velocidade_y = 0
        self.x = float(x)
        self.y = float(y)
        self.ground_y = 350.0
        self.is_jumping = False
        self.facing = 1  # 1 = right, -1 = left
        self.rings = 0
        self.score = 0
        self.lives = 3
        self.invuln_timer = 0.0

        self.images_run_left = [
            carregar_imagem("sonic-correndo-esquerda-1.png"),
            carregar_imagem("sonic-correndo-esquerda-2.png"),
            carregar_imagem("sonic-correndo-esquerda-3.png")
        ]
        self.images_run_right = [
            carregar_imagem("sonic-correndo-direita-1.png"),
            carregar_imagem("sonic-correndo-direita-2.png"),
            carregar_imagem("sonic-correndo-direita-3.png")
        ]
        self.img_idle_right = carregar_imagem("sonic-stop.png")
        self.img_idle_left = carregar_imagem("sonic-stop-esquerda.png")
        self.img_jump_right = pygame.transform.scale(carregar_imagem("sonic-pulando-direita.png"), (100, 107))
        self.img_jump_left = pygame.transform.scale(carregar_imagem("sonic-pulando-esquerda.png"), (100, 107))

        self.anim_frame = 0.0
        self.image = self.img_idle_right
        self.rect = pygame.Rect(int(self.x), int(self.y), 70, 85)

    def jump(self):
        if not self.is_jumping and abs(self.y - self.ground_y) < 5:
            self.velocidade_y = -17.0
            self.is_jumping = True
            try:
                import cci_rumble
                cci_rumble.light_rumble()
            except Exception:
                pass

    def bounce(self):
        self.velocidade_y = -13.0
        self.is_jumping = True
        try:
            import cci_rumble
            cci_rumble.hit_rumble()
        except Exception:
            pass

    def take_hit(self):
        if self.invuln_timer <= 0:
            self.invuln_timer = 2.0
            self.velocidade_y = -10.0
            self.velocidade_x = -6.0 if self.facing == 1 else 6.0
            if self.rings > 0:
                self.rings = 0
            else:
                self.lives -= 1
            try:
                import cci_rumble
                cci_rumble.explosion_rumble()
            except Exception:
                pass

    def update(self):
        # Gravity
        if self.is_jumping or self.y < self.ground_y:
            self.velocidade_y += 1.0
            self.y += self.velocidade_y
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.velocidade_y = 0.0
                self.is_jumping = False

        self.x += self.velocidade_x
        self.x = max(20.0, self.x)

        if self.invuln_timer > 0:
            self.invuln_timer -= 0.033

        # Animation state
        if self.is_jumping:
            self.image = self.img_jump_right if self.facing == 1 else self.img_jump_left
        elif abs(self.velocidade_x) > 0:
            self.anim_frame = (self.anim_frame + 0.35) % 3.0
            idx = int(self.anim_frame)
            if self.facing == 1:
                self.image = self.images_run_right[idx]
            else:
                self.image = self.images_run_left[idx]
        else:
            self.image = self.img_idle_right if self.facing == 1 else self.img_idle_left

        self.rect.topleft = (int(self.x), int(self.y))

    def stop(self):
        self.velocidade_x = 0
