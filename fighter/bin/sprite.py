# -*- coding: utf-8 -*-
import os
import pygame

class Sprite(object):
    ryu_coords = {
        'idle': [
            (0, 15, 49, 85),
            (49, 15, 49, 85),
            (99, 15, 49, 85),
            (148, 15, 49, 85)
        ],
        'walking': [
            (202, 15, 47, 85),
            (249, 15, 48, 85),
            (298, 15, 48, 85),
            (348, 15, 48, 85),
            (398, 15, 48, 85)
        ],
        'punch_light': [
            (7, 135, 45, 85),
            (56, 135, 60, 85),
            (7, 135, 45, 85)
        ],
        'punch_heavy': [
            (174, 135, 45, 85),
            (280, 135, 72, 85),
            (174, 135, 45, 85)
        ],
        'kick': [
            (6, 265, 45, 85),
            (62, 265, 70, 85),
            (6, 265, 45, 85)
        ],
        'hadouken': [
            (9, 415, 52, 85),
            (61, 415, 65, 85),
            (232, 415, 68, 85)
        ],
        'hit': [
            (6, 880, 48, 85),
            (57, 880, 48, 85)
        ],
        'ko': [
            (160, 880, 48, 85),
            (254, 880, 55, 85)
        ],
        'hadouken_ball': [
            (470, 420, 36, 32)
        ]
    }

    chunli_coords = {
        'idle': [
            (8, 15, 40, 85),
            (61, 15, 40, 85),
            (113, 15, 40, 85),
            (166, 15, 40, 85)
        ],
        'walking': [
            (231, 15, 42, 85),
            (289, 15, 42, 85),
            (345, 15, 42, 85)
        ],
        'punch_light': [
            (4, 150, 55, 85),
            (72, 150, 52, 85),
            (4, 150, 55, 85)
        ],
        'punch_heavy': [
            (132, 150, 60, 85),
            (201, 150, 64, 85),
            (271, 150, 80, 85)
        ],
        'kick': [
            (2, 270, 50, 85),
            (55, 270, 55, 85),
            (115, 270, 75, 85)
        ],
        'hadouken': [
            (4, 150, 55, 85),
            (201, 150, 64, 85),
            (271, 150, 80, 85)
        ],
        'hit': [
            (16, 990, 45, 85),
            (66, 990, 45, 85)
        ],
        'ko': [
            (16, 990, 45, 85),
            (66, 990, 45, 85)
        ],
        'hadouken_ball': [
            (470, 420, 36, 32)
        ]
    }

    def build_spriteset(self, character='ryu'):
        path = os.path.dirname(os.path.realpath(__file__))
        is_chun = (character == 'chunli')
        filename = 'chun-li.gif' if is_chun else 'ryu.gif'
        spriteset = pygame.image.load(os.path.join(path, '..', 'assets', filename)).convert()
        bg = spriteset.get_at((0, 0))
        spriteset.set_colorkey(bg)

        coords_dict = self.chunli_coords if is_chun else self.ryu_coords

        sprites = dict()
        for name, rect_list in coords_dict.items():
            sprites[name] = list()
            for r in rect_list:
                rect = pygame.Rect(*r)
                sprite = spriteset.subsurface(rect).convert()
                sprite.set_colorkey(bg)
                sprite = pygame.transform.scale2x(sprite)
                sprites[name].append(sprite)
        return sprites
