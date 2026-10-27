import sys
import pygame
from twisted.internet import reactor

# Class to handle the pygame, gets data from server and updates accordingly
class MarioKart():
	def __init__(self, playerNum):
		self.isPlayer1 = False
		if playerNum == 1:
			self.isPlayer1 = True
		self.width = 1200
		self.height = 900
		self.size = self.width, self.height
		pygame.init()
		self.screen = pygame.display.set_mode(self.size)
		self.background = pygame.image.load("assets/mario-kart-circuit.png")
		self.background_rect = self.background.get_rect()
		
		# Mario initialization
		self.marioX = 474
		self.marioY = 134
		self.mario_image = pygame.image.load("assets/mario.png")
		self.mario_image_old = self.mario_image
		self.mario_image = pygame.transform.flip(self.mario_image_old, True, False)
		self.mario_rect = self.mario_image.get_rect()
		self.mario_rect.x = self.marioX
		self.mario_rect.y = self.marioY
		self.mario_in_banana = False
		self.mario_rotation_counter = 0

		# Yoshi initialization
		self.yoshiX = 474
		self.yoshiY = 208
		self.yoshi_image = pygame.image.load("assets/yoshi.png")
		self.yoshi_image_old = self.yoshi_image
		self.yoshi_image = pygame.transform.flip(self.yoshi_image_old, True, False)
		self.yoshi_rect = self.yoshi_image.get_rect()
		self.yoshi_rect.x = self.yoshiX
		self.yoshi_rect.y = self.yoshiY
		self.yoshi_in_banana = False
		self.yoshi_rotation_counter = 0

		# Boost arrows
		self.boost1_x = 320
		self.boost1_y = 160
		self.boost1_image = pygame.image.load("assets/boost_arrow.png")
		self.boost1_image_old = self.boost1_image
		self.boost1_image = pygame.transform.flip(self.boost1_image_old, True, False)
		self.boost1_rect = self.boost1_image.get_rect()
		self.boost1_rect.x = self.boost1_x
		self.boost1_rect.y = self.boost1_y

		self.boost2_x = 140
		self.boost2_y = 420
		self.boost2_image = pygame.image.load("assets/boost_arrow.png")
		self.boost2_image_old = self.boost2_image
		self.boost2_image = pygame.transform.rotate(self.boost2_image_old, 270.)
		self.boost2_rect = self.boost2_image.get_rect()
		self.boost2_rect.x = self.boost2_x
		self.boost2_rect.y = self.boost2_y

		self.boost3_x = 930
		self.boost3_y = 490
		self.boost3_image = pygame.image.load("assets/boost_arrow.png")
		self.boost3_image_old = self.boost3_image
		self.boost3_image = pygame.transform.rotate(self.boost3_image_old, 90.)
		self.boost3_rect = self.boost3_image.get_rect()
		self.boost3_rect.x = self.boost3_x
		self.boost3_rect.y = self.boost3_y

		self.boost4_x = 530
		self.boost4_y = 710
		self.boost4_image = pygame.image.load("assets/boost_arrow.png")
		self.boost4_image_old = self.boost4_image
		self.boost4_rect = self.boost4_image.get_rect()
		self.boost4_rect.x = self.boost4_x
		self.boost4_rect.y = self.boost4_y

		self.banana1_x = 160
		self.banana1_y = 216
		self.banana1_image = pygame.image.load("assets/banana.png")
		self.banana1_image_old = self.banana1_image
		self.banana1_rect = self.banana1_image.get_rect()
		self.banana1_rect.x = self.banana1_x
		self.banana1_rect.y = self.banana1_y
		self.disp_b1 = True

		self.banana2_x = 356
		self.banana2_y = 755
		self.banana2_image = pygame.image.load("assets/banana.png")
		self.banana2_image_old = self.banana2_image
		self.banana2_rect = self.banana2_image.get_rect()
		self.banana2_rect.x = self.banana2_x
		self.banana2_rect.y = self.banana2_y
		self.disp_b2 = True

		self.banana3_x = 620
		self.banana3_y = 174
		self.banana3_image = pygame.image.load("assets/banana.png")
		self.banana3_image_old = self.banana3_image
		self.banana3_rect = self.banana3_image.get_rect()
		self.banana3_rect.x = self.banana3_x
		self.banana3_rect.y = self.banana3_y
		self.disp_b3 = True

		# Winner images
		self.mario_won = False
		self.mario_winner_image = pygame.image.load("assets/mario_winner.png")
		self.mario_winner_rect = self.mario_winner_image.get_rect()
		self.mario_winner_rect.x = 474
		self.mario_winner_rect.y = 230
		
		self.yoshi_won = False
		self.yoshi_winner_image = pygame.image.load("assets/yoshi_winner.png")
		self.yoshi_winner_rect = self.yoshi_winner_image.get_rect()
		self.yoshi_winner_rect.x = 474
		self.yoshi_winner_rect.y = 230
		
		pygame.key.set_repeat(1, 30)

	def rotate(self):
		if self.mario_in_banana:
			old = self.mario_rect.center
			rotation_angle = 10 * self.mario_rotation_counter
			self.mario_image = pygame.transform.rotate(self.mario_image_old, rotation_angle)
			self.mario_rect = self.mario_image.get_rect()
			self.mario_rect.center = old
		if self.yoshi_in_banana:
			old = self.yoshi_rect.center
			rotation_angle = 10 * self.yoshi_rotation_counter
			self.yoshi_image = pygame.transform.rotate(self.yoshi_image_old, rotation_angle)
			self.yoshi_rect = self.yoshi_image.get_rect()
			self.yoshi_rect.center = old
		
	def game_tick(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				reactor.stop()
			if event.type == pygame.KEYDOWN:
				if event.key >= 273 and event.key <= 276:
					# this is a movement key
					self.sendData(event.key)

		self.screen.blit(self.background, self.background_rect)
		if self.mario_in_banana:
			if self.mario_rotation_counter < 36:
				self.rotate()
				self.mario_rotation_counter += 1
			else:
				self.mario_rotation_counter = 0
				old = self.mario_rect.center
				self.mario_image = pygame.transform.rotate(self.mario_image_old, 0)
				self.mario_rect = self.mario_image.get_rect()
				self.mario_rect.center = old
				self.mario_in_banana = False
		if self.yoshi_in_banana:
			if self.yoshi_rotation_counter < 36:
				self.rotate()
				self.yoshi_rotation_counter += 1
			else:
				self.yoshi_rotation_counter = 0
				old = self.yoshi_rect.center
				self.yoshi_image = pygame.transform.rotate(self.yoshi_image_old, 0)
				self.yoshi_rect = self.yoshi_image.get_rect()
				self.yoshi_rect.center = old
				self.yoshi_in_banana = False

		self.screen.blit(self.mario_image, self.mario_rect)
		self.screen.blit(self.yoshi_image, self.yoshi_rect)
		self.screen.blit(self.boost1_image, self.boost1_rect)
		self.screen.blit(self.boost2_image, self.boost2_rect)
		self.screen.blit(self.boost3_image, self.boost3_rect)
		self.screen.blit(self.boost4_image, self.boost4_rect)

		if self.disp_b1:
			self.screen.blit(self.banana1_image, self.banana1_rect)
		if self.disp_b2:
			self.screen.blit(self.banana2_image, self.banana2_rect)
		if self.disp_b3:
			self.screen.blit(self.banana3_image, self.banana3_rect)

		if self.yoshi_won:
			self.screen.blit(self.yoshi_winner_image, self.yoshi_winner_rect)
		if self.mario_won:
			self.screen.blit(self.mario_winner_image, self.mario_winner_rect)
		pygame.display.flip()

	def sendData(self, keyNum):
		if self.isPlayer1:
			if not self.mario_in_banana:
				self.outgoingConn.transport.write("1:" + str(keyNum))
			else:
				self.outgoingConn.transport.write("1:" + "b")
		else:
			if not self.yoshi_in_banana:
				self.outgoingConn.transport.write("2:" + str(keyNum))
			else:
				self.outgoingConn.transport.write("2:" + "b")

	def transferConnectionObject(self, obj):
		self.outgoingConn = obj

	def handleData(self, data):
		self.mario_rect.x = int(data['mario_x'])
		self.mario_rect.y = int(data['mario_y'])
		self.yoshi_rect.x = int(data['yoshi_x'])
		self.yoshi_rect.y = int(data['yoshi_y'])
		if data['yoshi_won'] == "True":
			self.yoshi_won = True
		if data['mario_won'] == "True":
			self.mario_won = True

		if data['mario_in_banana'] == "True":
			self.mario_in_banana = True
			#self.disp_b1 = False


		if data['yoshi_in_banana'] == "True":
			self.yoshi_in_banana = True
			#self.disp_b1 = False

		
		
