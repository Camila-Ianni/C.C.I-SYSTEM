# -*- coding: utf-8 -*-
import os
import pygame
from pygame.locals import *
from sprite import Sprite
import itertools


class Game(object):
    size = (640, 480)

    def __init__(self):
        """
        Initialize the game
        """
        pygame.init()
        self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("STREET FIGHTER II — C.C.I. SYSTEM")
        pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP])
        # build background
        path = os.path.dirname(os.path.realpath(__file__))
        self.background = pygame.image.load(
            path + '/../assets/background-1.jpg'
        ).convert()
        self.background = pygame.transform.scale2x(self.background)
        # calculate center
        left = (self.background.get_width() - self.size[0]) / 2
        self.position = [-left, 0]
        self.walking = False
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.sprites = Sprite().build_spriteset()

    def run(self):
        """
        Main loop
        """
        running = True
        self.sprite = itertools.cycle(self.sprites['idle'])
        self.p2_sprite = itertools.cycle([pygame.transform.flip(s, True, False) for s in self.sprites['idle']])
        self.p1left = 100
        p2left = 420
        while running:
            self.clock.tick(20)
            running = self.handleEvents()
            # blit the background
            self.screen.blit(self.background, self.position)

            # blit fighters
            self.screen.blit(next(self.sprite), (self.p1left, 250))
            self.screen.blit(next(self.p2_sprite), (p2left, 250))

            # HUD Life bars (Street Fighter II style)
            pygame.draw.rect(self.screen, (220, 20, 20), (40, 25, 230, 18))
            pygame.draw.rect(self.screen, (255, 220, 0), (40, 25, 200, 18))
            pygame.draw.rect(self.screen, (255, 255, 255), (38, 23, 234, 22), 2)
            lbl1 = self.font.render("RYU", True, (255, 255, 255))
            self.screen.blit(lbl1, (40, 48))

            pygame.draw.rect(self.screen, (220, 20, 20), (370, 25, 230, 18))
            pygame.draw.rect(self.screen, (255, 220, 0), (400, 25, 200, 18))
            pygame.draw.rect(self.screen, (255, 255, 255), (368, 23, 234, 22), 2)
            lbl2 = self.font.render("KEN", True, (255, 255, 255))
            self.screen.blit(lbl2, (560, 48))

            # Controls HUD at bottom
            hint = self.font.render("A/D o FLECHAS: MOVER   |   ESC: VOLVER A LA CONSOLA", True, (220, 220, 220))
            self.screen.blit(hint, ((self.size[0] - hint.get_width()) // 2, 450))

            pygame.display.flip()

    def handleEvents(self):
        """
        Poll for pygame events
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                # if the user presses escape or 'q', quit the event loop.
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
        pressed = pygame.key.get_pressed()
        # movement control controlling background for now
        move = 'idle'
        if pressed[pygame.K_LEFT] or pressed[pygame.K_a]:
            move = 'left'
            self.p1left -= 9
        if pressed[pygame.K_RIGHT] or pressed[pygame.K_d]:
            move = 'right'
            self.p1left += 9
        if move in ('left', 'right'):
            if not self.walking:
                self.walking = True
                self.sprite = itertools.cycle(self.sprites['walking'])
        else:
            if self.walking:
                self.walking = False
                self.sprite = itertools.cycle(self.sprites['idle'])
        return True
