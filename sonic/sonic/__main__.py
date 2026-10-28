#!/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import pygame
import configparser
import pathlib

# Ensure root directory is on sys.path for cci_rumble
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from .game.cenarios.GreenHillZone import GreenHillZone
from .game.cenarios.MarbleZone import MarbleZone
from .game.telas.TelaDeInicio import TelaDeInicio

pygame.mixer.pre_init(44100, 16, 2, 1024)
pygame.init()
try:
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
except Exception:
    joysticks = []

config = configparser.ConfigParser()
config_file = pathlib.Path(__file__).parent / "config.ini"
if not config_file.exists():
    config_file = pathlib.Path("sonic/config.ini")
config.read(str(config_file))
JANELA = [int(config['JANELA']['LARGURA']), int(config['JANELA']['ALTURA'])]

tela = pygame.display.set_mode(JANELA, pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("SONIC THE HEDGEHOG — C.C.I. SYSTEM")
clock = pygame.time.Clock()

fase_object = [
    TelaDeInicio(tela),
    GreenHillZone(tela),
    MarbleZone(tela)
]
fase = 0
fase_object[fase].rodar_cenario()

executando = True
while executando:

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            executando = False
        elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_q):
            executando = False
        elif evento.type == pygame.JOYBUTTONDOWN and evento.button in (6, 7):
            executando = False
        else:
            if fase == 0:
                fase_object[fase].atualizar_eventos(evento, fase)
            else:
                fase_object[fase].atualizar_eventos(evento)

    # Update scene once per frame
    fase_object[fase].atualizar_cenario()

    if not fase_object[fase].rodando:
        fase = (fase + 1) % len(fase_object)
        fase_object[fase].rodar_cenario()

    clock.tick(60)
    pygame.display.flip()

pygame.quit()