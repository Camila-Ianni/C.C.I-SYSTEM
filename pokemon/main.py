import pygame
from src.game import Game
from os import path

from src.backend import savegame

mygame = Game()
mygame.dir = path.dirname(__file__)

start_data = savegame.load() or mygame.datahelper.warps["Starting Map"]
mygame.load(start_data)

clock = pygame.time.Clock()
while True:
	clock.tick(60)
	mygame.main()