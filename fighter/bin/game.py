# -*- coding: utf-8 -*-
"""
STREET FIGHTER II — Classic Arcade Experience for C.C.I. SYSTEM
Ryu (P1) vs Chun-Li (CPU) with authentic Street Fighter II arcade mechanics:
- Responsive combat: Light Punch, Heavy Punch, Roundhouse Kick, Hadouken Fireball
- Active AI Opponent: Chun-Li advances, kicks, strikes, defends, and counters
- Real hit detection, damage flinch animations, life bars, round timer, and K.O.
- Full Gamepad / Joystick support + force feedback vibration
"""

import os
import sys
import math
import random
import pygame
import numpy as np
from pygame.locals import *
from sprite import Sprite

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CCI_ROOT = os.path.dirname(ROOT_DIR)
if CCI_ROOT not in sys.path:
    sys.path.insert(0, CCI_ROOT)

def make_sfx(freq_start, freq_end, duration, wave_type='square', volume=0.3):
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        freqs = np.linspace(freq_start, freq_end, n_samples)
        phase = 2 * np.pi * np.cumsum(freqs) / sample_rate

        if wave_type == 'square':
            wave = np.sign(np.sin(phase))
        elif wave_type == 'noise':
            wave = np.random.uniform(-1, 1, n_samples)
        else:
            wave = np.sin(phase)

        env = np.linspace(1, 0, n_samples) ** 1.8
        audio = (wave * env * volume * 32767).astype(np.int16)
        audio = np.ascontiguousarray(audio)
        return pygame.sndarray.make_sound(audio)
    except Exception:
        return None

class Game(object):
    size = (640, 480)

    def __init__(self):
        pygame.init()
        pygame.font.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

        try:
            pygame.joystick.init()
            self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            for j in self.joysticks:
                j.init()
        except Exception:
            self.joysticks = []

        self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("STREET FIGHTER II — C.C.I. SYSTEM")

        # Load Stage Background
        path = os.path.dirname(os.path.realpath(__file__))
        bg_path = os.path.join(path, '..', 'assets', 'background-1.jpg')
        if os.path.isfile(bg_path):
            self.background = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.scale2x(self.background)
        else:
            self.background = pygame.Surface(self.size)
            self.background.fill((20, 25, 40))

        left = (self.background.get_width() - self.size[0]) / 2
        self.bg_pos = [-left, 0]

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 46)
        self.font_timer = pygame.font.Font(None, 36)

        # Load Ryu (P1) and Chun-Li (P2)
        sprite_loader = Sprite()
        self.ryu_sprites = sprite_loader.build_spriteset(character='ryu')
        self.chunli_sprites = sprite_loader.build_spriteset(character='chunli')

        # Generate SFX
        self.snd_punch = make_sfx(320, 160, 0.08, 'noise', 0.25)
        self.snd_hit = make_sfx(160, 60, 0.15, 'noise', 0.4)
        self.snd_hadouken = make_sfx(400, 750, 0.25, 'sine', 0.35)
        self.snd_ko = make_sfx(120, 40, 0.5, 'square', 0.45)

        self.reset_match()

    def reset_match(self):
        # P1: Ryu
        self.p1 = {
            'x': 110.0,
            'y': 250.0,
            'vx': 0.0,
            'vy': 0.0,
            'health': 100,
            'state': 'idle',
            'anim_frame': 0,
            'anim_timer': 0.0,
            'facing': 1,
            'attack_active': False,
            'attack_hit': False,
        }

        # P2: Chun-Li (CPU)
        self.p2 = {
            'x': 440.0,
            'y': 250.0,
            'vx': 0.0,
            'vy': 0.0,
            'health': 100,
            'state': 'idle',
            'anim_frame': 0,
            'anim_timer': 0.0,
            'facing': -1,
            'attack_active': False,
            'attack_hit': False,
            'ai_timer': 0.5,
            'ai_mode': 'advance',  # 'advance', 'retreat', 'wait', 'attack'
        }

        self.projectiles = []
        self.match_timer = 99.0
        self.round_state = 'FIGHT'
        self.ko_timer = 0.0

    def trigger_attack(self, fighter, attack_name):
        if fighter['state'] in ('hit', 'ko'):
            return
        # If already attacking, wait until current attack is halfway
        if fighter['attack_active'] and fighter['anim_frame'] < 1:
            return

        fighter['state'] = attack_name
        fighter['anim_frame'] = 0
        fighter['anim_timer'] = 0.0
        fighter['attack_active'] = True
        fighter['attack_hit'] = False

        if attack_name == 'hadouken':
            if self.snd_hadouken:
                self.snd_hadouken.play()
            fx = fighter['x'] + (70 if fighter['facing'] == 1 else -30)
            self.projectiles.append({
                'x': fx,
                'y': fighter['y'] + 30,
                'vx': fighter['facing'] * 360.0,
                'owner': 1 if fighter is self.p1 else 2,
                'active': True
            })
        else:
            if self.snd_punch:
                self.snd_punch.play()

    def update_anim(self, fighter, sprites, dt):
        fighter['anim_timer'] += dt
        st = fighter['state']

        speed = 0.10
        if st in ('punch_light', 'punch_heavy', 'kick'):
            speed = 0.09
        elif st == 'hadouken':
            speed = 0.12
        elif st in ('hit', 'ko'):
            speed = 0.16

        anim_list = sprites.get(st, sprites['idle'])
        if fighter['anim_timer'] >= speed:
            fighter['anim_timer'] = 0.0
            fighter['anim_frame'] += 1
            if fighter['anim_frame'] >= len(anim_list):
                if st in ('punch_light', 'punch_heavy', 'kick', 'hadouken', 'hit'):
                    fighter['state'] = 'idle'
                    fighter['anim_frame'] = 0
                    fighter['attack_active'] = False
                elif st == 'ko':
                    fighter['anim_frame'] = len(anim_list) - 1
                else:
                    fighter['anim_frame'] = 0

    def apply_damage(self, victim, attacker, dmg):
        victim['health'] = max(0, victim['health'] - dmg)
        victim['state'] = 'hit' if victim['health'] > 0 else 'ko'
        victim['anim_frame'] = 0
        victim['anim_timer'] = 0.0
        victim['attack_active'] = False

        push = 1 if attacker['x'] < victim['x'] else -1
        victim['x'] += push * 26.0

        if self.snd_hit:
            self.snd_hit.play()

        try:
            import cci_rumble
            if victim['health'] <= 0:
                cci_rumble.explosion_rumble()
            else:
                cci_rumble.hit_rumble()
        except Exception:
            pass

    def update_ai(self, dt):
        chun = self.p2
        ryu = self.p1
        if chun['state'] in ('hit', 'ko') or self.round_state == 'KO':
            return

        chun['ai_timer'] -= dt
        dist = abs(chun['x'] - ryu['x'])

        if chun['ai_timer'] <= 0:
            chun['ai_timer'] = random.uniform(0.4, 0.9)
            if dist > 180:
                # Approach or fire
                chun['ai_mode'] = 'advance' if random.random() < 0.75 else 'hadouken'
            elif dist < 85:
                # Close range combat: kick, punch, or step back
                r = random.random()
                if r < 0.45:
                    chun['ai_mode'] = 'kick'
                elif r < 0.80:
                    chun['ai_mode'] = 'punch'
                else:
                    chun['ai_mode'] = 'retreat'
            else:
                chun['ai_mode'] = 'advance' if random.random() < 0.6 else 'kick'

        # Execute AI actions
        if not chun['attack_active']:
            if chun['ai_mode'] == 'advance':
                dir_x = -1 if chun['x'] > ryu['x'] else 1
                chun['x'] += dir_x * 120.0 * dt
                chun['state'] = 'walking'
            elif chun['ai_mode'] == 'retreat':
                dir_x = 1 if chun['x'] > ryu['x'] else -1
                chun['x'] += dir_x * 100.0 * dt
                chun['state'] = 'walking'
            elif chun['ai_mode'] == 'punch':
                self.trigger_attack(chun, 'punch_heavy' if random.random() < 0.5 else 'punch_light')
            elif chun['ai_mode'] == 'kick':
                self.trigger_attack(chun, 'kick')
            elif chun['ai_mode'] == 'hadouken':
                self.trigger_attack(chun, 'hadouken')
            else:
                chun['state'] = 'idle'

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.05)

            if self.round_state == 'FIGHT':
                self.match_timer = max(0.0, self.match_timer - dt)
                if self.match_timer <= 0:
                    if self.p1['health'] > self.p2['health']:
                        self.p2['health'] = 0
                        self.p2['state'] = 'ko'
                    else:
                        self.p1['health'] = 0
                        self.p1['state'] = 'ko'
                    self.round_state = 'KO'
                    if self.snd_ko:
                        self.snd_ko.play()

            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif self.p1['state'] not in ('hit', 'ko'):
                        if event.key in (pygame.K_j, pygame.K_z):
                            self.trigger_attack(self.p1, 'punch_light')
                        elif event.key in (pygame.K_k, pygame.K_x):
                            self.trigger_attack(self.p1, 'punch_heavy')
                        elif event.key in (pygame.K_l, pygame.K_c):
                            self.trigger_attack(self.p1, 'kick')
                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_u):
                            self.trigger_attack(self.p1, 'hadouken')
                        elif event.key in (pygame.K_w, pygame.K_UP):
                            if self.p1['y'] >= 250.0:
                                self.p1['vy'] = -380.0
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:    # A: Light Punch
                        self.trigger_attack(self.p1, 'punch_light')
                    elif event.button == 2:  # X: Heavy Punch
                        self.trigger_attack(self.p1, 'punch_heavy')
                    elif event.button == 1:  # B: Kick
                        self.trigger_attack(self.p1, 'kick')
                    elif event.button == 3:  # Y: Hadouken
                        self.trigger_attack(self.p1, 'hadouken')
                    elif event.button in (6, 7):
                        running = False

            # Player 1 Movement Polling
            if not self.p1['attack_active'] and self.p1['state'] not in ('hit', 'ko'):
                keys = pygame.key.get_pressed()
                mv = 0.0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    mv -= 1.0
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    mv += 1.0

                for j in self.joysticks:
                    try:
                        ax = j.get_axis(0)
                        if abs(ax) > 0.3:
                            mv += (1.0 if ax > 0 else -1.0)
                        if j.get_numhats() > 0:
                            hx, hy = j.get_hat(0)
                            if hx != 0:
                                mv += hx
                            if hy > 0 and self.p1['y'] >= 250.0:
                                self.p1['vy'] = -380.0
                    except Exception:
                        pass

                if mv != 0.0:
                    self.p1['x'] += mv * 160.0 * dt
                    self.p1['state'] = 'walking'
                else:
                    self.p1['state'] = 'idle'

            # Jumps physics
            for f in (self.p1, self.p2):
                if f['y'] < 250.0 or f['vy'] < 0:
                    f['vy'] += 950.0 * dt
                    f['y'] += f['vy'] * dt
                    if f['y'] >= 250.0:
                        f['y'] = 250.0
                        f['vy'] = 0.0

            # Update AI
            self.update_ai(dt)

            # Boundaries
            self.p1['x'] = max(30.0, min(self.size[0] - 120.0, self.p1['x']))
            self.p2['x'] = max(30.0, min(self.size[0] - 120.0, self.p2['x']))
            self.p1['facing'] = 1 if self.p1['x'] <= self.p2['x'] else -1
            self.p2['facing'] = -1 if self.p1['x'] <= self.p2['x'] else 1

            # Update Animations
            self.update_anim(self.p1, self.ryu_sprites, dt)
            self.update_anim(self.p2, self.chunli_sprites, dt)

            # Hit Detection (Melee)
            dist = abs(self.p1['x'] - self.p2['x'])
            if self.p1['attack_active'] and not self.p1['attack_hit'] and self.p1['state'] in ('punch_light', 'punch_heavy', 'kick'):
                if self.p1['anim_frame'] >= 1 and dist < 85.0:
                    self.p1['attack_hit'] = True
                    dmg = 9 if self.p1['state'] == 'punch_light' else 15
                    self.apply_damage(self.p2, self.p1, dmg)

            if self.p2['attack_active'] and not self.p2['attack_hit'] and self.p2['state'] in ('punch_light', 'punch_heavy', 'kick'):
                if self.p2['anim_frame'] >= 1 and dist < 85.0:
                    self.p2['attack_hit'] = True
                    dmg = 8 if self.p2['state'] == 'punch_light' else 14
                    self.apply_damage(self.p1, self.p2, dmg)

            # Update Projectiles
            for p in self.projectiles:
                p['x'] += p['vx'] * dt
                target = self.p2 if p['owner'] == 1 else self.p1
                t_rect = pygame.Rect(int(target['x']), int(target['y']), 70, 140)
                if t_rect.collidepoint(int(p['x']), int(p['y'])):
                    p['active'] = False
                    self.apply_damage(target, self.p1 if p['owner'] == 1 else self.p2, 18)

            self.projectiles = [p for p in self.projectiles if p['active'] and 0 <= p['x'] <= self.size[0]]

            # KO Check
            if self.round_state == 'FIGHT':
                if self.p1['health'] <= 0 or self.p2['health'] <= 0:
                    self.round_state = 'KO'
                    if self.snd_ko:
                        self.snd_ko.play()

            if self.round_state == 'KO':
                self.ko_timer += dt
                if self.ko_timer >= 3.5:
                    self.reset_match()

            # RENDER
            self.screen.blit(self.background, self.bg_pos)

            # Draw Projectiles
            ball = self.ryu_sprites.get('hadouken_ball', [None])[0]
            for p in self.projectiles:
                if ball:
                    bsurf = ball
                    if p['vx'] < 0:
                        bsurf = pygame.transform.flip(bsurf, True, False)
                    self.screen.blit(bsurf, (int(p['x']), int(p['y'])))
                else:
                    pygame.draw.circle(self.screen, (90, 200, 255), (int(p['x']), int(p['y'])), 14)

            # Draw Ryu (P1)
            p1_anim = self.ryu_sprites.get(self.p1['state'], self.ryu_sprites['idle'])
            p1_frame = p1_anim[min(self.p1['anim_frame'], len(p1_anim) - 1)]
            if self.p1['facing'] == -1:
                p1_frame = pygame.transform.flip(p1_frame, True, False)
            self.screen.blit(p1_frame, (int(self.p1['x']), int(self.p1['y'])))

            # Draw Chun-Li (P2)
            p2_anim = self.chunli_sprites.get(self.p2['state'], self.chunli_sprites['idle'])
            p2_frame = p2_anim[min(self.p2['anim_frame'], len(p2_anim) - 1)]
            if self.p2['facing'] == 1:
                p2_frame = pygame.transform.flip(p2_frame, True, False)
            self.screen.blit(p2_frame, (int(self.p2['x']), int(self.p2['y'])))

            # HUD
            # P1 Health
            pygame.draw.rect(self.screen, (180, 20, 20), (40, 25, 230, 20))
            p1_w = int(230 * (self.p1['health'] / 100.0))
            if p1_w > 0:
                pygame.draw.rect(self.screen, (255, 225, 20), (40, 25, p1_w, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (38, 23, 234, 24), 2)
            self.screen.blit(self.font.render("RYU", True, (255, 255, 255)), (40, 50))

            # P2 Health
            pygame.draw.rect(self.screen, (180, 20, 20), (370, 25, 230, 20))
            p2_w = int(230 * (self.p2['health'] / 100.0))
            if p2_w > 0:
                pygame.draw.rect(self.screen, (255, 225, 20), (370 + (230 - p2_w), 25, p2_w, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (368, 23, 234, 24), 2)
            self.screen.blit(self.font.render("CHUN-LI", True, (255, 255, 255)), (540, 50))

            # Timer
            timer_txt = self.font_timer.render(f"{int(self.match_timer):02d}", True, (255, 230, 40))
            self.screen.blit(timer_txt, ((self.size[0] - timer_txt.get_width()) // 2, 22))

            # KO Overlay
            if self.round_state == 'KO':
                winner = "RYU" if self.p1['health'] > self.p2['health'] else "CHUN-LI"
                ko_txt = self.font_large.render(f"K.O. — {winner} WINS!", True, (255, 50, 50))
                self.screen.blit(ko_txt, ((self.size[0] - ko_txt.get_width()) // 2, 140))

            # Controls HUD at bottom (clearly visible)
            hint = self.font.render("FLECHAS: MOVER  W: SALTAR  J: GOLPE  K: FUERTE  L: PATADA  ESPACIO: HADOUKEN", True, (240, 240, 240))
            self.screen.blit(hint, ((self.size[0] - hint.get_width()) // 2, 452))

            pygame.display.flip()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()
