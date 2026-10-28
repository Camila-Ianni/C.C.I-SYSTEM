# -*- coding: utf-8 -*-
import os
import pygame

class Sprite(object):
    coords = {
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

    def build_spriteset(self, character='ryu'):
        path = os.path.dirname(os.path.realpath(__file__))
        spriteset = pygame.image.load(path + '/../assets/ryu.gif').convert()
        transparent_pixel = (0, 0)
        bg = spriteset.get_at(transparent_pixel)
        spriteset.set_colorkey(bg)

        # For Ken, convert white gi to crimson red
        if character == 'ken':
            w, h = spriteset.get_size()
            for x in range(w):
                for y in range(h):
                    c = spriteset.get_at((x, y))
                    if c != bg and c.r > 140 and c.g > 140 and c.b > 140 and abs(c.r - c.g) < 30 and abs(c.g - c.b) < 30:
                        spriteset.set_at((x, y), pygame.Color(min(255, c.r + 20), int(c.g * 0.15), int(c.b * 0.15), c.a))

        sprites = dict()
        for name, rect_list in self.coords.items():
            sprites[name] = list()
            for r in rect_list:
                rect = pygame.Rect(*r)
                sprite = spriteset.subsurface(rect).convert()
                sprite.set_colorkey(bg)
                sprite = pygame.transform.scale2x(sprite)
                sprites[name].append(sprite)
        return sprites
