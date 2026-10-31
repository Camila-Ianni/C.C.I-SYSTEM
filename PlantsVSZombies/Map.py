import pygame
import os
from setting import *
from time import *
from plant import *
from zombie import *
from pygame.locals import *
import sys
import time
import threading
import psutil
import subprocess
from multiprocessing import Process
from PIL import Image
import math

class Menu():
	def __init__(self):
		pygame.init()
		pygame.mixer.init()
		pygame.display.set_caption("Plant VS Zombies")
		icon=pygame.image.load('Picture/Others/Flower.ico')
		icon.set_colorkey((0,0,0))
		pygame.display.set_icon(icon)
		flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
		self.screen=pygame.display.set_mode((Screen_Width, Screen_Height), flags)
		self.clock=pygame.time.Clock()
		self.bgp=pygame.image.load('Picture/Menu/MainMenu.png').convert()

	def Click(self,click):
		pos=( int(round(click[0])),int(round(click[1])) )
		# START ADVENTURE
		if (490 <= pos[0] <= 735 and 55 <= pos[1] <= 160):
			return 1
		# SURVIVAL
		if (490 <= pos[0] <= 705 and 330 <= pos[1] <= 410):
			return 2
		# QUIT
		if (710 <= pos[0] <= 785 and 470 <= pos[1] <= 570):
			return -1
		return 0

	def Run(self):
		while 1:
			mouse_pos = pygame.mouse.get_pos()
			self.screen.blit(self.bgp, (0, 0))

			# Hover en START ADVENTURE
			if 490 <= mouse_pos[0] <= 735 and 55 <= mouse_pos[1] <= 160:
				glow = pygame.Surface((735 - 490, 160 - 55), pygame.SRCALPHA)
				glow.fill((255, 255, 200, 35))
				self.screen.blit(glow, (490, 55))
			# Hover en SURVIVAL
			elif 490 <= mouse_pos[0] <= 705 and 330 <= mouse_pos[1] <= 410:
				glow = pygame.Surface((705 - 490, 410 - 330), pygame.SRCALPHA)
				glow.fill((255, 255, 200, 35))
				self.screen.blit(glow, (490, 330))
			# Hover en QUIT florero
			elif 710 <= mouse_pos[0] <= 785 and 470 <= mouse_pos[1] <= 570:
				glow = pygame.Surface((785 - 710, 570 - 470), pygame.SRCALPHA)
				glow.fill((255, 100, 100, 40))
				self.screen.blit(glow, (710, 470))

			for event in pygame.event.get():
				if (event.type==pygame.QUIT):
					return 0
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					return 0
				if event.type == pygame.MOUSEBUTTONUP:
					x=self.Click(pygame.mouse.get_pos())
					if (x>0):
						return	x
					elif (x == -1):
						return 0

			pygame.display.flip()
			self.clock.tick(Fps)
'''
游戏初始页面
'''

PLANT_REWARDS = [
	{
		"id": 0, "name": "GIRASOL", "card": "Picture/Cards/1.png", "folder": "Picture/Plants/SunFlower",
		"sub": "", "frames": 18, "desc": "Proporciona sol adicional vital para plantar más defensas.",
		"cost": 50, "recharge": "RÁPIDA",
	},
	{
		"id": 1, "name": "LANZAGUISANTES", "card": "Picture/Cards/2.png", "folder": "Picture/Plants/PeaShooter",
		"sub": "", "frames": 13, "desc": "Tu primera línea de defensa. Dispara guisantes a los zombis.",
		"cost": 100, "recharge": "RÁPIDA",
	},
	{
		"id": 2, "name": "NUEZ", "card": "Picture/Cards/3.png", "folder": "Picture/Plants/WallNut/Nolmal",
		"sub": "", "frames": 16, "desc": "Cáscara dura que bloquea el paso de los zombis y protege tus plantas.",
		"cost": 50, "recharge": "LENTA",
	},
	{
		"id": 3, "name": "HIELAGUISANTES", "card": "Picture/Cards/4.png", "folder": "Picture/Plants/SnowPea",
		"sub": "", "frames": 15, "desc": "Dispara guisantes helados que ralentizan y dañan a los zombis.",
		"cost": 175, "recharge": "RÁPIDA",
	},
	{
		"id": 4, "name": "REPETIDORA", "card": "Picture/Cards/5.png", "folder": "Picture/Plants/RepeaterPea",
		"sub": "", "frames": 15, "desc": "Dispara dos guisantes al mismo tiempo. Duplica tu potencia de fuego.",
		"cost": 200, "recharge": "RÁPIDA",
	},
	{
		"id": 5, "name": "PATATAPUM", "card": "Picture/Cards/6.png", "folder": "Picture/Plants/PotatoMine/Nolmal",
		"sub": "", "frames": 8, "desc": "Explota al contacto con zombis, pero tarda un momento en armarse bajo tierra.",
		"cost": 25, "recharge": "LENTA",
	},
	{
		"id": 6, "name": "PINCHORROCA", "card": "Picture/Cards/7.png", "folder": "Picture/Plants/Spikeweed",
		"sub": "", "frames": 19, "desc": "Pincha a los zombis que caminan sobre ella e inutiliza vehículos.",
		"cost": 100, "recharge": "RÁPIDA",
	},
	{
		"id": 7, "name": "PLANTA CARNÍVORA", "card": "Picture/Cards/8.png", "folder": "Picture/Plants/Chomper/Nolmal",
		"sub": "", "frames": 13, "desc": "Devora zombis enteros de un solo bocado. Muy poderosa pero mastica despacio.",
		"cost": 150, "recharge": "RÁPIDA",
	},
]

class GameControl():
	def __init__(self,mode):
		pygame.init()
		pygame.mixer.init()
		pygame.display.set_caption("Plant VS Zombies")
		icon=pygame.image.load('Picture/Others/Flower.ico')
		icon.set_colorkey((0,0,0))
		pygame.display.set_icon(icon)

		flags = pygame.FULLSCREEN | pygame.SCALED if hasattr(pygame, "SCALED") else 0
		self.screen = pygame.display.get_surface()
		if self.screen is None or self.screen.get_size() != (Screen_Width, Screen_Height):
			self.screen = pygame.display.set_mode((Screen_Width, Screen_Height), flags)

		self.all_sprites=pygame.sprite.Group()
		self.clock=pygame.time.Clock()
		self.sun=Sun(self.screen)
		if (mode==1):
			self.sun.sum=50
		else:
			self.sun.sum=3000
		
		info_file = 'Info.in' if os.path.exists('Info.in') else 'info.in'
		try:
			with open(info_file, 'r') as File:
				val = int(File.readline().strip())
				self.level = max(0, min(val - 1, len(Zom_create) - 1))
		except Exception:
			self.level = 0

		self.zomid=0

		self.mode=mode
		self.card=Card(self.screen,[])
		self.map=[[-1 for i in range(9)] for i in range(5)]
		self.plant=[]
		self.zombies=[]
		self.bullet_list=[]
		self.car=Car(self.screen)
		self.time=pygame.time.get_ticks()

		self.horde_banner = pygame.image.load('Picture/Others/HordeBanner.png').convert_alpha()
		self.horde_alert_active = False
		self.horde_alert_start = 0
		self.horde_alert_text = ""
		self.horde_spawned = False
		self.horde_count = 0
		self.max_hordes = 5
		self.all_hordes_spawned = False
		self.survive_tick = pygame.time.get_ticks()
		self.survive_wave_timer = pygame.time.get_ticks()
		self.survive_wave_interval = 35000

	# Page initialization

	def Play_BackGround_Music(self):
		pygame.mixer.music.load('Music/Grasswalk.mp3')
		pygame.mixer.music.play(-1,0)
	#播放BGM

	def blit_alpha(self,source,location,position,val):
		x=location[0]
		y=location[1]
		temp = pygame.Surface((source.get_width(),source.get_height())).convert()
		temp.blit(self.screen,(-position[0],-position[1]))
		temp.blit(source,location)
		temp.set_alpha(val)
		self.screen.blit(temp,position)
	#将一个图片变为半透明

	def Mousedraw(self):
		if self.card.select==-1:
			return
		
		now=pygame.mouse.get_pos()
		pos=( int(round(now[0])),int(round(now[1])) )
		x=(pos[0]-Coordinate_origin[0])//Block_size_width
		y=(pos[1]-Coordinate_origin[1])//Block_size_height
		
		if (x<0 or x>8 or y<0 or y>4):
			return
		if (self.map[y][x]!=-1):
			return
		
		img=pygame.image.load('Picture/Plants/Special//'+str(self.card.select)+'.png').convert_alpha()
		img.set_colorkey(WHITE)
		pos=(Coordinate_origin[0]+Block_size_width*x,Coordinate_origin[1]+Block_size_height*y)
		rect=img.get_rect()
		if (self.card.select==7):
			pos=(pos[0],pos[1]-20)
		if (self.card.select==6):
			pos=(pos[0],pos[1]+Block_size_height*0.5)
		self.blit_alpha(img,rect,pos,150)
		#透明植物绘制

	def SetPlant(self,click):
		pos=( int(round(click[0])),int(round(click[1])) )
		x=(pos[0]-Coordinate_origin[0])//Block_size_width
		y=(pos[1]-Coordinate_origin[1])//Block_size_height
		
		if (x<0 or x>8 or y<0 or y>4):
			self.card.select=-1
			return
		if (self.map[y][x]!=-1):
			self.card.select=-1
			return
		self.map[y][x]=self.card.select
		self.card.Put(self.card.select)
		self.card.select=-1
		self.sun.sum-=self.card.cost_list[self.card.card_list.index(self.map[y][x])]
		if (self.map[y][x]==0):
			self.plant.append(Sunflower(self.screen,0,(y,x)))
		elif (self.map[y][x]==1):
			self.plant.append(PeaShooter(self.screen,1,(y,x)))
		elif (self.map[y][x]==2):
			self.plant.append(WallNut(self.screen,2,(y,x)))
		elif (self.map[y][x]==3):
			self.plant.append(SnowPea(self.screen,3,(y,x)))
		elif (self.map[y][x]==4):
			self.plant.append(RepeaterPea(self.screen,4,(y,x)))
		elif (self.map[y][x]==5):
			self.plant.append(PotatoMine(self.screen,5,(y,x)))
		elif (self.map[y][x]==6):
			self.plant.append(Spikeweed(self.screen,6,(y,x)))
		elif (self.map[y][x]==7):
			self.plant.append(Chomper(self.screen,7,(y,x)))	
		#安放植物
	
	def PlantDraw(self):
		a=[]
		for pla in self.plant:
			if (pla.hp<=0):
				self.map[pla.pos[0]][pla.pos[1]]=-1
				continue
			a.append(pla)
			pla.Draw()

		self.plant=[]
		for pla in a:
			self.plant.append(pla)
	
	def PlantEvent(self):
		a=[]
		for pla in self.plant:
			if (pla.hp<=0):
				self.map[pla.pos[0]][pla.pos[1]]=-1
				continue
			a.append(pla)
			pla.Event(self.sun,
					self.bullet_list,
					self.zombies)

		self.plant=[]
		for pla in a:
			if (pla.hp>0):
				self.plant.append(pla)
	#植物事件判定
	#攻击与特殊事件

	def BulletDraw(self):
		a=[]
		for bull in self.bullet_list:
			if (bull.exist==False):
				continue
			bull.Draw()
			a.append(bull)
		self.bullet_list=[]
		for bull in a:
			if (bull.exist==True):
				self.bullet_list.append(bull)

	def BulletEvent(self):
		a=[]
		for bull in self.bullet_list:
			if (bull.exist==False):
				continue
			bull.Attack(self.zombies)
			a.append(bull)
		self.bullet_list=[]
		for bull in a:
			self.bullet_list.append(bull)
		#子弹判定

	def CreateZom(self):
		now_ticks = pygame.time.get_ticks()
		elapsed = (now_ticks - self.time) / 1000

		if (self.mode == 1):
			if self.zomid >= len(Zom_create[self.level]):
				return

			final_time = Zom_create[self.level][-1][0]
			# Activar alerta de cartel 4 segundos antes de la horda final
			if elapsed >= (final_time - 4) and not self.horde_alert_active and not self.horde_spawned:
				self.horde_alert_active = True
				self.horde_alert_start = now_ticks
				self.horde_alert_text = "¡SE APROXIMA LA GRAN HORDA FINAL!"
				try:
					import cci_rumble
					cci_rumble.explosion_rumble()
				except Exception:
					pass

			# Al alcanzar la hora de la gran horda, añadir Flag Zombie liderando
			if elapsed >= final_time and not self.horde_spawned:
				self.horde_spawned = True
				self.zombies.append(FlagZombie(self.screen, 3, random.randint(0, 4)))

			# Spawnear todos los zombies agendados hasta este segundo
			while self.zomid < len(Zom_create[self.level]) and elapsed >= Zom_create[self.level][self.zomid][0]:
				z_type = Zom_create[self.level][self.zomid][1]
				lane = random.randint(0, 4)
				if z_type == 0:
					self.zombies.append(NolMal_Zombie(self.screen, 0, lane))
				elif z_type == 1:
					self.zombies.append(ConeheadZombie(self.screen, 1, lane))
				else:
					self.zombies.append(BucketheadZombie(self.screen, 2, lane))
				self.zomid += 1
		else:
			# Modo Supervivencia (Modo 2: 3000 soles, 5 Hordas)
			if self.all_hordes_spawned:
				return

			# Zombies constantes entre hordas
			if now_ticks - self.survive_tick >= 3500:
				self.survive_tick = now_ticks
				lane = random.randint(0, 4)
				weights = [0.6, 0.25, 0.1, 0.05]
				if self.horde_count >= 1:
					weights = [0.45, 0.35, 0.12, 0.08]
				if self.horde_count >= 2:
					weights = [0.35, 0.35, 0.2, 0.1]
				if self.horde_count >= 3:
					weights = [0.25, 0.35, 0.25, 0.15]
				r = random.random()
				if r < weights[0]:
					self.zombies.append(NolMal_Zombie(self.screen, 0, lane))
				elif r < weights[0] + weights[1]:
					self.zombies.append(ConeheadZombie(self.screen, 1, lane))
				elif r < weights[0] + weights[1] + weights[2]:
					self.zombies.append(BucketheadZombie(self.screen, 2, lane))
				else:
					self.zombies.append(PaperZombie(self.screen, 4, lane))

			# Alerta previa de horda (4 segundos antes de la oleada)
			time_to_wave = self.survive_wave_interval - (now_ticks - self.survive_wave_timer)
			if time_to_wave <= 4000 and not self.horde_alert_active and self.horde_count < self.max_hordes:
				self.horde_alert_active = True
				self.horde_alert_start = now_ticks
				next_horde = self.horde_count + 1
				if next_horde == self.max_hordes:
					self.horde_alert_text = "¡SE APROXIMA LA GRAN HORDA FINAL! (5/5)"
				else:
					self.horde_alert_text = f"¡SE APROXIMA UNA GRAN HORDA DE ZOMBIS! ({next_horde}/{self.max_hordes})"
				try:
					import cci_rumble
					cci_rumble.explosion_rumble()
				except Exception:
					pass

			# Despacho de la Horda (5 Hordas en total)
			if now_ticks - self.survive_wave_timer >= self.survive_wave_interval and self.horde_count < self.max_hordes:
				self.survive_wave_timer = now_ticks
				self.horde_count += 1

				if self.horde_count == 1:
					self.zombies.append(FlagZombie(self.screen, 3, 2))
					for l in range(5):
						self.zombies.append(NolMal_Zombie(self.screen, 0, l))
					self.zombies.append(ConeheadZombie(self.screen, 1, random.randint(0, 4)))
				elif self.horde_count == 2:
					self.zombies.append(FlagZombie(self.screen, 3, 1))
					for l in range(5):
						self.zombies.append(NolMal_Zombie(self.screen, 0, l))
					self.zombies.append(ConeheadZombie(self.screen, 1, 0))
					self.zombies.append(ConeheadZombie(self.screen, 1, 3))
					self.zombies.append(BucketheadZombie(self.screen, 2, 4))
				elif self.horde_count == 3:
					self.zombies.append(FlagZombie(self.screen, 3, 2))
					for l in range(5):
						self.zombies.append(NolMal_Zombie(self.screen, 0, l))
						if random.random() > 0.4:
							self.zombies.append(ConeheadZombie(self.screen, 1, l))
					self.zombies.append(BucketheadZombie(self.screen, 2, 1))
					self.zombies.append(BucketheadZombie(self.screen, 2, 3))
					self.zombies.append(PaperZombie(self.screen, 4, random.randint(0, 4)))
				elif self.horde_count == 4:
					self.zombies.append(FlagZombie(self.screen, 3, 2))
					for l in range(5):
						self.zombies.append(NolMal_Zombie(self.screen, 0, l))
						self.zombies.append(ConeheadZombie(self.screen, 1, l))
					self.zombies.append(BucketheadZombie(self.screen, 2, 0))
					self.zombies.append(BucketheadZombie(self.screen, 2, 2))
					self.zombies.append(BucketheadZombie(self.screen, 2, 4))
					self.zombies.append(PaperZombie(self.screen, 4, 1))
					self.zombies.append(PaperZombie(self.screen, 4, 3))
				elif self.horde_count >= 5:
					# Horda Final (5/5): Despliegue masivo final
					self.zombies.append(FlagZombie(self.screen, 3, 1))
					self.zombies.append(FlagZombie(self.screen, 3, 3))
					for l in range(5):
						self.zombies.append(NolMal_Zombie(self.screen, 0, l))
						self.zombies.append(ConeheadZombie(self.screen, 1, l))
						if l in (0, 2, 4):
							self.zombies.append(BucketheadZombie(self.screen, 2, l))
						if l in (1, 3):
							self.zombies.append(PaperZombie(self.screen, 4, l))
					self.all_hordes_spawned = True
	#根据关卡信息生成僵尸

	def ZomDraw(self):
		a=[]
		for zom in self.zombies:
			if (zom.die==True):
				continue
			zom.Draw()
			a.append(zom)
		self.zombies=[]
		for zom in a:
			self.zombies.append(zom)
		
	def ZomEvent(self):
		a=[]
		for zom in self.zombies:
			if (zom.die==True):
				continue
			zom.Event(self.plant)
			a.append(zom)
		self.zombies=[]
		for zom in a:
			self.zombies.append(zom)
	#僵尸事件判定

	def SelectDraw(self,screen,lis):
		bgp=pygame.image.load('Picture/BackGround/Day.png')
		cd=pygame.image.load('Picture/BackGround/SeedBank.png')
		screen.blit(bgp,(0,0))
		screen.blit(cd,(0,0))

		board=pygame.image.load('Picture/Menu/Board.png')
		screen.blit(board,(0,87))
		
		if (len(lis)==6):
			img=pygame.image.load('Picture/Menu/Begin.png')
			screen.blit(img,(156,547))
		
		for i in range(len(lis)):
			img=pygame.image.load('Picture/Cards//'+str(lis[i]+1)+'.png')
			screen.blit(img,(Card_pos[0]+i*Card_size,Card_pos[1]))
			#rec=img.get_rect()
			#print(rec[2],rec[3])

		gray=pygame.Surface((Card_scale[0]-2,Card_scale[1]-3),flags=0,depth=32)
		gray.set_alpha(100)
		for i in range(8):
			img=pygame.image.load('Picture/Cards//'+str(i+1)+'.png')
			img=pygame.transform.scale(img,(int(Card_scale[0]*0.95),int(Card_scale[1]*0.95)))
			screen.blit(img,(Card_pos[0]-60+i*(Card_size-7),120+Card_pos[1]))
			if (i in lis):
				screen.blit(gray,(Card_pos[0]-60+i*(Card_size-7),120+Card_pos[1]))
		pygame.display.flip()
		#绘制卡片槽

	def BeginGame(self,lis):
		if (len(lis)<6):
			return False
		click=pygame.mouse.get_pos()
		pos=( int(round(click[0])),int(round(click[1])) )
		if (156<=pos[0]<=390 and 547<=pos[1]<=700):
			return True
		return False

	def SelectPlant(self,lis,click):
		a=[]
		pos=( int(round(click[0])),int(round(click[1])) )
		for i in range(len(lis)):
			x=Card_pos[0]+i*Card_size
			y=Card_pos[1]
			if (x<=pos[0]<=x+Card_size and y<=pos[1]<=y+Card_scale[1]):
				for j in range(len(lis)):
					if (j!=i):
						a.append(lis[j])
				return a
		if (len(lis)>=6):
			return lis
		for i in range(8):
			if (i in lis):
				continue
			x=Card_pos[0]-60+i*(Card_size-7)
			y=120+Card_pos[1]
			if (x<=pos[0]<=x+Card_size-7 and y<=pos[1]<=y+Card_scale[1]):
				for j in lis:
					a.append(j)
				a.append(i)
				return a
		return lis

	def Select(self):
		screen = self.screen
		plants = []

		while 1:
			self.SelectDraw(screen, plants)
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return []
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					return []
				if event.type == pygame.MOUSEBUTTONUP:
					if self.BeginGame(plants):
						return plants
					a = self.SelectPlant(plants, pygame.mouse.get_pos())
					plants = []
					for i in a:
						plants.append(i)
	#游戏开始时选择植物

	def WinCheck(self):
		for zom in self.zombies:
			if (zom.hp <= 0):
				continue
			if (zom.pos <= -90):
				return 0

		if (self.mode == 2):
			if self.all_hordes_spawned and len(self.zombies) == 0:
				return 1
			return -1

		if (self.zomid >= len(Zom_create[self.level]) and len(self.zombies) == 0):
			return 1

		return -1
	#游戏终止判定

	def PlayFanfare(self):
		try:
			if pygame.mixer.get_init():
				import numpy as np
				frequency = 44100
				notes = [(523.25, 0.14), (659.25, 0.14), (784.00, 0.16), (1046.50, 0.70)]
				total_time = sum(d for _, d in notes)
				total_samples = int(frequency * total_time)
				buf = np.zeros(total_samples, dtype=np.float32)
				idx = 0
				for freq, dur in notes:
					n_samples = int(frequency * dur)
					t = np.linspace(0, dur, n_samples, endpoint=False)
					decay = np.exp(-t * (3.2 if dur > 0.3 else 1.8))
					wave = 0.50 * np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t) + 0.15 * np.sin(6 * np.pi * freq * t)
					buf[idx:idx + n_samples] += wave * decay
					idx += n_samples
				buf = np.clip(buf, -1.0, 1.0)
				mono_i16 = (buf * 22000).astype(np.int16)
				stereo_i16 = np.column_stack([mono_i16, mono_i16])
				snd = pygame.mixer.Sound(buffer=stereo_i16.tobytes())
				snd.play()
		except Exception as exc:
			print(f"[PvZ] Error fanfarria: {exc}")

	def ShowNewPlantReward(self):
		if pygame.mixer.get_init():
			pygame.mixer.music.stop()

		self.PlayFanfare()
		try:
			import cci_rumble
			cci_rumble.explosion_rumble()
		except Exception:
			pass

		# Seleccionar planta ganada
		if self.mode == 2:
			plant_idx = 7  # PLANTA CARNÍVORA (Chomper) - Máxima recompensa de Supervivencia 5 Hordas
		else:
			plant_idx = min(7, max(2, self.level + 2))
		plant = PLANT_REWARDS[plant_idx]

		card_raw = pygame.image.load(plant["card"]).convert_alpha()
		plant_frames = []
		folder = plant["folder"]
		for i in range(1, plant["frames"] + 1):
			fp = os.path.join(folder, f"{i}.png")
			if os.path.exists(fp):
				plant_frames.append(pygame.image.load(fp).convert_alpha())
		if not plant_frames:
			plant_frames = [card_raw]

		lawn_snap = self.screen.copy()

		# --- FASE 1: Semilla elevándose y expandiéndose desde el jardín ---
		rise_duration = 1600
		start_rise = pygame.time.get_ticks()
		while True:
			elapsed = pygame.time.get_ticks() - start_rise
			if elapsed >= rise_duration:
				break

			skip = False
			for ev in pygame.event.get():
				if ev.type == pygame.QUIT:
					return
				if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
					skip = True
					break
			if skip:
				break

			prog = min(1.0, elapsed / rise_duration)
			ease = math.sin(prog * math.pi / 2.0)
			cx = 400
			cy = int(340 - 110 * ease)
			scale = 0.6 + 1.6 * ease
			cw = max(1, int(card_raw.get_width() * scale))
			ch = max(1, int(card_raw.get_height() * scale))

			self.screen.blit(lawn_snap, (0, 0))

			shade = pygame.Surface((Screen_Width, Screen_Height), pygame.SRCALPHA)
			shade.fill((0, 0, 0, int(150 * ease)))
			self.screen.blit(shade, (0, 0))

			halo_r = int(70 * scale)
			halo_surf = pygame.Surface((halo_r * 2, halo_r * 2), pygame.SRCALPHA)
			pygame.draw.circle(halo_surf, (255, 230, 80, int(100 * ease)), (halo_r, halo_r), halo_r)
			self.screen.blit(halo_surf, (cx - halo_r, cy - halo_r))

			tilt = math.sin(prog * 12.0) * 10.0 * (1.0 - prog)
			scaled_card = pygame.transform.smoothscale(card_raw, (cw, ch))
			rot_card = pygame.transform.rotate(scaled_card, tilt)
			card_rect = rot_card.get_rect(center=(cx, cy))
			self.screen.blit(rot_card, card_rect)

			pygame.display.flip()
			self.clock.tick(60)

		# --- FASE 2: Pantalla de Celebración y Rayos de Sol Dorados ---
		font_title = pygame.font.SysFont("Helvetica,Arial", 28, bold=True)
		font_subtitle = pygame.font.SysFont("Helvetica,Arial", 14, bold=True)
		font_name = pygame.font.SysFont("Helvetica,Arial", 22, bold=True)
		font_desc = pygame.font.SysFont("Helvetica,Arial", 13)
		font_stats = pygame.font.SysFont("Helvetica,Arial", 12, bold=True)
		font_btn = pygame.font.SysFont("Helvetica,Arial", 15, bold=True)
		font_hint = pygame.font.SysFont("Helvetica,Arial", 11)

		large_card = pygame.transform.smoothscale(card_raw, (120, 168))
		scaled_plant_frames = [
			pygame.transform.smoothscale(f, (int(f.get_width() * 1.6), int(f.get_height() * 1.6)))
			for f in plant_frames
		]

		card_center = (270, 230)
		plant_center = (510, 230)
		btn_rect = pygame.Rect((Screen_Width - 220) // 2, 508, 220, 42)

		ray_angle = 0.0
		frame_idx = 0
		last_frame_tick = pygame.time.get_ticks()

		active = True
		while active:
			dt = self.clock.tick(60) / 1000.0
			ray_angle += 0.6 * dt
			now = pygame.time.get_ticks()

			if now - last_frame_tick >= 85:
				frame_idx = (frame_idx + 1) % len(scaled_plant_frames)
				last_frame_tick = now

			for ev in pygame.event.get():
				if ev.type == pygame.QUIT:
					return
				if ev.type == pygame.KEYDOWN:
					if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
						active = False
				elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
					active = False
				elif ev.type == pygame.JOYBUTTONDOWN:
					active = False

			self.screen.blit(lawn_snap, (0, 0))
			overlay = pygame.Surface((Screen_Width, Screen_Height), pygame.SRCALPHA)
			overlay.fill((10, 14, 20, 210))
			self.screen.blit(overlay, (0, 0))

			# Rayos dorados giratorios
			num_rays = 14
			radius = 340
			center_x, center_y = 400, 230
			ray_surf = pygame.Surface((Screen_Width, Screen_Height), pygame.SRCALPHA)
			for i in range(num_rays):
				a1 = ray_angle + (i * 2.0 * math.pi / num_rays)
				a2 = a1 + (math.pi / num_rays)
				p1 = (center_x, center_y)
				p2 = (center_x + int(radius * math.cos(a1)), center_y + int(radius * math.sin(a1)))
				p3 = (center_x + int(radius * math.cos(a2)), center_y + int(radius * math.sin(a2)))
				color = (255, 225, 70, 36) if i % 2 == 0 else (255, 240, 120, 20)
				pygame.draw.polygon(ray_surf, color, [p1, p2, p3])
			self.screen.blit(ray_surf, (0, 0))

			# Título
			title_txt = "¡HAS OBTENIDO UNA NUEVA PLANTA!"
			t_shadow = font_title.render(title_txt, True, (20, 30, 10))
			self.screen.blit(t_shadow, ((Screen_Width - t_shadow.get_width()) // 2 + 2, 42))
			t_surf = font_title.render(title_txt, True, (255, 220, 40))
			self.screen.blit(t_surf, ((Screen_Width - t_surf.get_width()) // 2, 40))

			if self.mode == 2:
				sub_txt = "¡Sobreviviste a las 5 Grandes Hordas de Zombis!"
			else:
				sub_txt = f"¡Nivel {self.level + 1} defendido con éxito!"
			sub_surf = font_subtitle.render(sub_txt, True, (160, 245, 140))
			self.screen.blit(sub_surf, ((Screen_Width - sub_surf.get_width()) // 2, 78))

			# Carta con resplandor dorado
			c_rect = large_card.get_rect(center=card_center)
			glow_box = c_rect.inflate(12, 12)
			pygame.draw.rect(self.screen, (255, 220, 80), glow_box, 3, border_radius=6)
			self.screen.blit(large_card, c_rect)

			# Planta viva animada
			cur_frame = scaled_plant_frames[frame_idx]
			pf_rect = cur_frame.get_rect(center=plant_center)
			self.screen.blit(cur_frame, pf_rect)

			# Placa descriptiva
			desc_box = pygame.Rect(120, 335, 560, 150)
			pygame.draw.rect(self.screen, (22, 28, 20), desc_box, border_radius=8)
			pygame.draw.rect(self.screen, (215, 180, 50), desc_box, 2, border_radius=8)

			pname_surf = font_name.render(plant["name"], True, (255, 225, 60))
			self.screen.blit(pname_surf, ((Screen_Width - pname_surf.get_width()) // 2, desc_box.y + 12))

			pygame.draw.line(self.screen, (100, 140, 70), (desc_box.x + 40, desc_box.y + 45), (desc_box.right - 40, desc_box.y + 45), 1)

			words = plant["desc"].split(" ")
			lines = []
			curr = ""
			for w in words:
				test = (curr + " " + w).strip()
				if font_desc.size(test)[0] < desc_box.w - 40:
					curr = test
				else:
					lines.append(curr)
					curr = w
			if curr:
				lines.append(curr)
			for li, l_text in enumerate(lines[:2]):
				d_s = font_desc.render(l_text, True, (240, 245, 235))
				self.screen.blit(d_s, ((Screen_Width - d_s.get_width()) // 2, desc_box.y + 55 + li * 20))

			stats_text = f"COSTO: {plant['cost']} SOLES    ·    RECARGA: {plant['recharge']}"
			st_surf = font_stats.render(stats_text, True, (120, 230, 120))
			self.screen.blit(st_surf, ((Screen_Width - st_surf.get_width()) // 2, desc_box.bottom - 32))

			# Botón
			pulse = int(180 + 55 * math.sin(now / 180.0))
			btn_col = (30, int(pulse * 0.7), 30)
			border_col = (100, pulse, 100)
			pygame.draw.rect(self.screen, btn_col, btn_rect, border_radius=6)
			pygame.draw.rect(self.screen, border_col, btn_rect, 2, border_radius=6)
			btn_text_surf = font_btn.render("CONTINUAR", True, (255, 255, 255))
			self.screen.blit(btn_text_surf, btn_text_surf.get_rect(center=btn_rect.center))

			hint_surf = font_hint.render("Clic o presiona ENTER / ESPACIO para avanzar", True, (170, 185, 175))
			self.screen.blit(hint_surf, ((Screen_Width - hint_surf.get_width()) // 2, btn_rect.bottom + 4))

			pygame.display.flip()

	def Test(self):
		bgp=pygame.image.load('Picture/BackGround/Day.png')
		cd=pygame.image.load('Picture/BackGround/SeedBank.png')
		self.Play_BackGround_Music()

		while 1:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					return
				if event.type == pygame.MOUSEBUTTONUP:
					if (self.card.select!=-1):
						self.SetPlant(pygame.mouse.get_pos())
					self.sun.Pick(pygame.mouse.get_pos())
					self.card.Choose(pygame.mouse.get_pos(),self.sun.sum)
			
			self.screen.blit(bgp,(0,0))
			self.screen.blit(cd,(0,0))
			self.card.Draw(self.sun.sum)

			font=pygame.font.SysFont(None,22)
			text=font.render(str(self.sun.sum),True,BLACK)
			self.screen.blit(text,Sun_Pos)

			# Indicador HUD de Hordas / Nivel estilo PvZ en esquina superior derecha
			hud_font = pygame.font.SysFont("Helvetica,Arial", 12, bold=True)
			if self.mode == 2:
				badge_w, badge_h = 195, 42
				bx = Screen_Width - badge_w - 15
				by = 12
				badge_rect = pygame.Rect(bx, by, badge_w, badge_h)
				pygame.draw.rect(self.screen, (24, 30, 20), badge_rect, border_radius=6)
				pygame.draw.rect(self.screen, (90, 160, 70), badge_rect, 1, border_radius=6)

				if self.all_hordes_spawned:
					h_text = "¡HORDA FINAL (5/5)!"
					h_col = (255, 215, 0)
				else:
					cur_h = min(self.max_hordes, self.horde_count + 1)
					h_text = f"HORDA {cur_h} / {self.max_hordes}"
					h_col = (130, 240, 130)

				s_t = hud_font.render(h_text, True, h_col)
				self.screen.blit(s_t, (bx + 12, by + 5))

				# Barra de progreso de hordas
				bar_rect = pygame.Rect(bx + 12, by + 23, badge_w - 24, 11)
				pygame.draw.rect(self.screen, (12, 15, 10), bar_rect, border_radius=4)
				fill_w = int((badge_w - 24) * (self.horde_count / self.max_hordes))
				if fill_w > 0:
					pygame.draw.rect(self.screen, (70, 190, 60), (bar_rect.x, bar_rect.y, fill_w, bar_rect.h), border_radius=4)
				pygame.draw.rect(self.screen, (60, 110, 50), bar_rect, 1, border_radius=4)
				for flag_i in range(1, self.max_hordes + 1):
					fx = bar_rect.x + int((badge_w - 24) * (flag_i / self.max_hordes))
					pygame.draw.line(self.screen, (255, 60, 60), (fx, bar_rect.y - 2), (fx, bar_rect.bottom), 1)
			else:
				badge_rect = pygame.Rect(Screen_Width - 140, 12, 125, 28)
				pygame.draw.rect(self.screen, (24, 30, 20), badge_rect, border_radius=6)
				pygame.draw.rect(self.screen, (90, 160, 70), badge_rect, 1, border_radius=6)
				lvl_surf = hud_font.render(f"NIVEL {self.level + 1} / 5", True, (130, 240, 130))
				self.screen.blit(lvl_surf, lvl_surf.get_rect(center=badge_rect.center))

			#预处理阶段

			self.Mousedraw()
			self.car.Draw()
			self.car.Event(self.zombies)

			self.PlantDraw()
			self.PlantEvent()

			self.CreateZom()
			self.ZomDraw()
			self.ZomEvent()

			self.BulletDraw()
			self.BulletEvent()

			self.sun.Appear()
			self.sun.Draw()

			# Cartel: ¡SE APROXIMA UNA GRAN HORDA DE ZOMBIS!
			if self.horde_alert_active:
				alert_ms = pygame.time.get_ticks() - self.horde_alert_start
				if alert_ms < 3800:
					if (alert_ms // 220) % 2 == 0 or alert_ms < 1200:
						scale = 1.0 + 0.05 * math.sin(alert_ms / 120.0)
						bw = int(self.horde_banner.get_width() * scale)
						bh = int(self.horde_banner.get_height() * scale)
						b_surf = pygame.transform.smoothscale(self.horde_banner, (bw, bh))
						bx = (Screen_Width - bw) // 2
						by = 220
						self.screen.blit(b_surf, (bx, by))
						if self.horde_alert_text:
							h_font = pygame.font.SysFont("Helvetica,Arial", 16, bold=True)
							sh_t = h_font.render(self.horde_alert_text, True, (0, 0, 0))
							tx_t = h_font.render(self.horde_alert_text, True, (255, 230, 70))
							tx_pos = ((Screen_Width - tx_t.get_width()) // 2, by + bh + 4)
							self.screen.blit(sh_t, (tx_pos[0] + 1, tx_pos[1] + 1))
							self.screen.blit(tx_t, tx_pos)
				else:
					self.horde_alert_active = False

			if (self.WinCheck()==0):
				try:
					import cci_rumble
					cci_rumble.explosion_rumble()
				except Exception:
					pass
				img=pygame.image.load('Picture/Menu/Lost.png').convert_alpha()
				rec=img.get_rect()
				self.screen.fill((0, 0, 0))
				self.screen.blit(img, ((Screen_Width - rec.width) // 2, (Screen_Height - rec.height) // 2))
				pygame.display.flip()
				sleep(3)
				return
			elif (self.WinCheck()==1):
				info_file = 'Info.in' if os.path.exists('Info.in') else 'info.in'
				try:
					with open(info_file, 'w') as File:
						x = self.level + 2
						if x > len(Zom_create):
							x = 1
						File.write(str(x))
				except Exception:
					pass

				# Animación de la nueva planta desbloqueada
				self.ShowNewPlantReward()

				img=pygame.image.load('Picture/Menu/Win.png').convert_alpha()
				rec=img.get_rect()
				self.screen.fill((0, 0, 0))
				self.screen.blit(img, ((Screen_Width - rec.width) // 2, (Screen_Height - rec.height) // 2))
				pygame.display.flip()
				sleep(2.5)
				return

			pygame.display.flip()
			# 事件发生阶段

			self.clock.tick(Fps)

	def Run(self,plants):
		self.time=pygame.time.get_ticks()
		self.sun.time=pygame.time.get_ticks()
		self.card=Card(self.screen,plants)
		self.Test()