import sys
import pygame
from player import Player
from enemy import Enemy
from laser import Laser

class gamespace():
	def main(self):
		# 1) basic initialization
		pygame.init()
		self.size = self.width, self.height = 640, 480
		self.black = 0, 0, 0
		self.screen = pygame.display.set_mode(self.size)

		# 2) set up game objects
		self.clock = pygame.time.Clock()
		self.player = Player(self)
		self.enemy = Enemy(self)
		self.laser_list = []
		pygame.key.set_repeat(1, 20)
		# 3) game loop
		while 1:
			# 4) clock tick regulation (framerate)
			self.clock.tick(60)
			# 5) this is where you would handle user inputs...
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if event.key >= 273 and event.key <= 276:
						self.player.move(event.key)
				if event.type == pygame.MOUSEBUTTONDOWN:
					self.player.tofire = True
				if event.type == pygame.MOUSEBUTTONUP:
					self.player.tofire = False
				if event.type == pygame.QUIT:
					sys.exit()
			# 6) send a tick to every game object!
			self.player.tick()
			self.enemy.tick()
			for laser in self.laser_list:
				laser.tick()
			# 7) and finally, display the game objects
			self.screen.fill(self.black)
			for laser in self.laser_list:
				self.screen.blit(laser.image, laser.rect)
			self.screen.blit(self.player.image, self.player.rect)
			self.screen.blit(self.enemy.image, self.enemy.rect)
			pygame.display.flip()
	
if __name__ == '__main__':
	gs = gamespace()
	gs.main()
