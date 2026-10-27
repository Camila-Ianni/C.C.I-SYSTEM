import sys
import math
import pygame
from laser import Laser

class Player(pygame.sprite.Sprite):
	def __init__(self, gs=None):
		pygame.sprite.Sprite.__init__(self)
		self.gs = gs
		self.image = pygame.image.load("deathstar.png")
		self.rect = self.image.get_rect()
		# keep original image to limit resize errors
		self.orig_image = self.image
		# if I can fire laser beams, this flag will say
		# whether I should be firing them /right now/
		self.tofire = False
		self.angle = 0
		self.firing_angle = 0.
		self.firing_x = 185.
		self.firing_y = 185.
		self.music_playing = False

	def tick(self):
		# get the mouse x and y position on the screen
		(mx, my) = pygame.mouse.get_pos()
		# this conditional prevents movement while firing
		if self.tofire == True:
			# code to emit a laser beam block
			self.battle()
		else:
			# code to calculate the angle between my current
			# direction and the mouse position (see math.atan2)
			# ... use this angle to rotate the image so that it
			# faces the mouse
			angle = math.atan2(float(my)-self.rect.y, float(mx)-self.rect.x)
			angle_degrees = (angle * (180.0/math.pi) * -1.) - 35
			center = self.rect.center
			self.image = pygame.transform.rotate(self.orig_image, angle_degrees)
			self.angle = angle_degrees
			self.rect = self.image.get_rect()
			self.rect.center = center

	def move(self, key_num):
		if key_num == 276:
			self.rect = self.rect.move(-4, 0)
		if key_num == 275:
			self.rect = self.rect.move(4, 0)
		if key_num == 274:
			self.rect = self.rect.move(0, 4)
		if key_num == 273:
			self.rect = self.rect.move(0, -4)

	def battle(self):
		if self.music_playing == False:
			pygame.mixer.music.load("screammachine.wav")
			pygame.mixer.music.play(-1)
			self.music_playing = True
		laser = Laser(self.angle, self.rect.center, self.gs)
		self.gs.laser_list.append(laser)
