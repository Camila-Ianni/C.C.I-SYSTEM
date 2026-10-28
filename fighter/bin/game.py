# -*- coding: utf-8 -*-
"""
STREET FIGHTER II — Classic Arcade Experience for C.C.I. SYSTEM
Ryu (P1) vs Ken (CPU) with full arcade fighting mechanics:
- Movement: walk forward/back, jump, crouch
- Attacks: Light Punch, Heavy Punch, Roundhouse Kick, Hadouken Fireball
- AI Opponent: Ken distances, attacks, defends, counters
- Hit detection, damage, flinch animations, and K.O. Victory
- Gamepad / Joystick support with force feedback vibration
"""

import os
import sys
import math
import random
import pygame
import numpy as np
from pygame.locals import *
from sprite import Sprite

# Add root directory to sys.path for cci_rumble
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

        # Load Background
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
        self.font_large = pygame.font.Font(None, 48)
        self.font_timer = pygame.font.Font(None, 36)

        # Load Sprites for Ryu (P1) and Ken (P2)
        sprite_loader = Sprite()
        self.ryu_sprites = sprite_loader.build_spriteset(character='ryu')
        self.ken_sprites = sprite_loader.build_spriteset(character='ken')

        # Generate SFX
        self.snd_punch = make_sfx(300, 150, 0.08, 'noise', 0.25)
        self.snd_hit = make_sfx(160, 60, 0.15, 'noise', 0.4)
        self.snd_hadouken = make_sfx(400, 750, 0.25, 'sine', 0.35)
        self.snd_ko = make_sfx(120, 40, 0.5, 'square', 0.45)

        self.reset_match()

    def reset_match(self):
        # Fighters State
        # P1: Ryu
        self.p1 = {
            'x': 100.0,
            'y': 250.0,
            'vx': 0.0,
            'vy': 0.0,
            'health': 100,
            'state': 'idle',     # 'idle', 'walk_fwd', 'walk_back', 'jump', 'crouch', 'punch_light', 'punch_heavy', 'kick', 'hadouken', 'hit', 'ko'
            'anim_frame': 0,
            'anim_timer': 0.0,
            'facing': 1,         # 1 = facing right
            'attack_active': False,
            'attack_hit': False,
        }

        # P2: Ken (CPU)
        self.p2 = {
            'x': 420.0,
            'y': 250.0,
            'vx': 0.0,
            'vy': 0.0,
            'health': 100,
            'state': 'idle',
            'anim_frame': 0,
            'anim_timer': 0.0,
            'facing': -1,        # -1 = facing left
            'attack_active': False,
            'attack_hit': False,
            'ai_timer': 0.0,
            'ai_action': 'idle',
        }

        # Projectiles: list of {x, y, vx, owner: 1 or 2, active: bool}
        self.projectiles = []
        self.match_timer = 99.0
        self.round_state = 'FIGHT'  # 'FIGHT', 'KO'
        self.ko_timer = 0.0

    def trigger_attack(self, fighter, attack_name):
        if fighter['state'] in ('hit', 'ko'):
            return
        fighter['state'] = attack_name
        fighter['anim_frame'] = 0
        fighter['anim_timer'] = 0.0
        fighter['attack_active'] = True
        fighter['attack_hit'] = False

        if attack_name == 'hadouken':
            if self.snd_hadouken:
                self.snd_hadouken.play()
            # Launch fireball
            fx = fighter['x'] + (65 if fighter['facing'] == 1 else -25)
            self.projectiles.append({
                'x': fx,
                'y': fighter['y'] + 30,
                'vx': fighter['facing'] * 340.0,
                'owner': 1 if fighter is self.p1 else 2,
                'active': True
            })
        else:
            if self.snd_punch:
                self.snd_punch.play()

    def update_fighter_anim(self, fighter, sprites, dt):
        fighter['anim_timer'] += dt
        st = fighter['state']

        # Determine frame speed based on state
        speed = 0.10
        if st in ('punch_light', 'punch_heavy', 'kick'):
            speed = 0.08
        elif st == 'hadouken':
            speed = 0.12
        elif st in ('hit', 'ko'):
            speed = 0.15

        anim_list = sprites.get(st, sprites['idle'])
        if fighter['anim_timer'] >= speed:
            fighter['anim_timer'] = 0.0
            fighter['anim_frame'] += 1
            if fighter['anim_frame'] >= len(anim_list):
                # End of attack or hit reaction
                if st in ('punch_light', 'punch_heavy', 'kick', 'hadouken', 'hit'):
                    fighter['state'] = 'idle'
                    fighter['anim_frame'] = 0
                    fighter['attack_active'] = False
                elif st == 'ko':
                    fighter['anim_frame'] = len(anim_list) - 1
                else:
                    fighter['anim_frame'] = 0

    def apply_damage(self, victim, attacker, damage):
        victim['health'] = max(0, victim['health'] - damage)
        victim['state'] = 'hit' if victim['health'] > 0 else 'ko'
        victim['anim_frame'] = 0
        victim['anim_timer'] = 0.0
        victim['attack_active'] = False

        # Knockback
        push_dir = 1 if attacker['x'] < victim['x'] else -1
        victim['x'] += push_dir * 28.0

        if self.snd_hit:
            self.snd_hit.play()

        # Rumble vibration
        try:
            import cci_rumble
            if victim['health'] <= 0:
                cci_rumble.explosion_rumble()
            else:
                cci_rumble.hit_rumble()
        except Exception:
            pass

    def update_ai(self, dt):
        ken = self.p2
        ryu = self.p1
        if ken['state'] in ('hit', 'ko') or self.round_state == 'KO':
            return

        ken['ai_timer'] -= dt
        dist = abs(ken['x'] - ryu['x'])

        if ken['ai_timer'] <= 0:
            ken['ai_timer'] = random.uniform(0.3, 0.9)
            dice = random.random()

            if dist > 220:
                # Far away: advance or throw Hadouken
                if dice < 0.35:
                    self.trigger_attack(ken, 'hadouken')
                else:
                    ken['ai_action'] = 'fwd'
            elif dist < 95:
                # Very close: punch, kick, or step back
                if dice < 0.40:
                    self.trigger_attack(ken, 'punch_heavy' if random.random() < 0.5 else 'punch_light')
                elif dice < 0.75:
                    self.trigger_attack(ken, 'kick')
                else:
                    ken['ai_action'] = 'back'
            else:
                # Mid range: advance, kick, or jump
                if dice < 0.50:
                    ken['ai_action'] = 'fwd'
                elif dice < 0.80:
                    self.trigger_attack(ken, 'kick')
                else:
                    ken['ai_action'] = 'idle'

        # Execute AI movement
        if ken['state'] == 'idle':
            if ken['ai_action'] == 'fwd':
                ken['x'] -= 140.0 * dt
                ken['state'] = 'walking'
            elif ken['ai_action'] == 'back':
                ken['x'] += 120.0 * dt
                ken['state'] = 'walking'

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

            # Poll Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif self.p1['state'] not in ('hit', 'ko'):
                        if event.key == pygame.K_j:
                            self.trigger_attack(self.p1, 'punch_light')
                        elif event.key == pygame.K_k:
                            self.trigger_attack(self.p1, 'punch_heavy')
                        elif event.key == pygame.K_l:
                            self.trigger_attack(self.p1, 'kick')
                        elif event.key == pygame.K_SPACE:
                            self.trigger_attack(self.p1, 'hadouken')
                        elif event.key in (pygame.K_w, pygame.K_UP):
                            if self.p1['y'] >= 250.0:
                                self.p1['vy'] = -380.0
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 2:    # X: Light Punch
                        self.trigger_attack(self.p1, 'punch_light')
                    elif event.button == 3:  # Y: Heavy Punch
                        self.trigger_attack(self.p1, 'punch_heavy')
                    elif event.button == 1:  # B: Kick
                        self.trigger_attack(self.p1, 'kick')
                    elif event.button == 0:  # A: Jump or Hadouken
                        self.trigger_attack(self.p1, 'hadouken')
                    elif event.button in (6, 7):
                        running = False

            # Player 1 Movement Polling
            if self.p1['state'] in ('idle', 'walking'):
                keys = pygame.key.get_pressed()
                mv = 0.0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    mv -= 1.0
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    mv += 1.0

                # Gamepad stick / D-pad
                for j in self.joysticks:
                    try:
                        ax = j.get_axis(0)
                        if abs(ax) > 0.3:
                            mv += ax
                        if j.get_numhats() > 0:
                            hx, hy = j.get_hat(0)
                            if hx != 0:
                                mv += hx
                            if hy > 0 and self.p1['y'] >= 250.0:
                                self.p1['vy'] = -380.0
                    except Exception:
                        pass

                if abs(mv) > 0.1:
                    self.p1['x'] += mv * 160.0 * dt
                    self.p1['state'] = 'walking'
                else:
                    self.p1['state'] = 'idle'

            # Jump physics
            for f in (self.p1, self.p2):
                if f['y'] < 250.0 or f['vy'] < 0:
                    f['vy'] += 1000.0 * dt
                    f['y'] += f['vy'] * dt
                    if f['y'] >= 250.0:
                        f['y'] = 250.0
                        f['vy'] = 0.0

            # Update AI
            self.update_ai(dt)

            # Keep fighters on screen & facing each other
            self.p1['x'] = max(30.0, min(self.size[0] - 120.0, self.p1['x']))
            self.p2['x'] = max(30.0, min(self.size[0] - 120.0, self.p2['x']))
            self.p1['facing'] = 1 if self.p1['x'] <= self.p2['x'] else -1
            self.p2['facing'] = -1 if self.p1['x'] <= self.p2['x'] else 1

            # Update Animations
            self.update_fighter_anim(self.p1, self.ryu_sprites, dt)
            self.update_fighter_anim(self.p2, self.ken_sprites, dt)

            # Hit Collision Detection (Melee attacks)
            dist = abs(self.p1['x'] - self.p2['x'])
            if self.p1['attack_active'] and not self.p1['attack_hit'] and self.p1['state'] in ('punch_light', 'punch_heavy', 'kick'):
                # Attack reaches during middle frame
                if self.p1['anim_frame'] >= 1 and dist < 85.0:
                    self.p1['attack_hit'] = True
                    dmg = 8 if self.p1['state'] == 'punch_light' else 14
                    self.apply_damage(self.p2, self.p1, dmg)

            if self.p2['attack_active'] and not self.p2['attack_hit'] and self.p2['state'] in ('punch_light', 'punch_heavy', 'kick'):
                if self.p2['anim_frame'] >= 1 and dist < 85.0:
                    self.p2['attack_hit'] = True
                    dmg = 8 if self.p2['state'] == 'punch_light' else 14
                    self.apply_damage(self.p1, self.p2, dmg)

            # Update Projectiles (Hadouken)
            for p in self.projectiles:
                p['x'] += p['vx'] * dt
                # Check collision with opponent
                target = self.p2 if p['owner'] == 1 else self.p1
                t_rect = pygame.Rect(int(target['x']), int(target['y']), 70, 140)
                if t_rect.collidepoint(int(p['x']), int(p['y'])):
                    p['active'] = False
                    self.apply_damage(target, self.p1 if p['owner'] == 1 else self.p2, 18)

            self.projectiles = [p for p in self.projectiles if p['active'] and 0 <= p['x'] <= self.size[0]]

            # Check KO
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
            # Background
            self.screen.blit(self.background, self.bg_pos)

            # Draw Projectiles
            ball_sprite = self.ryu_sprites.get('hadouken_ball', [None])[0]
            for p in self.projectiles:
                if ball_sprite:
                    bsurf = ball_sprite
                    if p['vx'] < 0:
                        bsurf = pygame.transform.flip(bsurf, True, False)
                    self.screen.blit(bsurf, (int(p['x']), int(p['y'])))
                else:
                    pygame.draw.circle(self.screen, (100, 200, 255), (int(p['x']), int(p['y'])), 14)
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(p['x']), int(p['y'])), 8)

            # Draw Ryu (P1)
            p1_anim = self.ryu_sprites.get(self.p1['state'], self.ryu_sprites['idle'])
            p1_frame = p1_anim[min(self.p1['anim_frame'], len(p1_anim) - 1)]
            if self.p1['facing'] == -1:
                p1_frame = pygame.transform.flip(p1_frame, True, False)
            self.screen.blit(p1_frame, (int(self.p1['x']), int(self.p1['y'])))

            # Draw Ken (P2)
            p2_anim = self.ken_sprites.get(self.p2['state'], self.ken_sprites['idle'])
            p2_frame = p2_anim[min(self.p2['anim_frame'], len(p2_anim) - 1)]
            if self.p2['facing'] == 1:
                p2_frame = pygame.transform.flip(p2_frame, True, False)
            self.screen.blit(p2_frame, (int(self.p2['x']), int(self.p2['y'])))

            # HUD Life Bars
            # P1 Health (Yellow drains to Red)
            pygame.draw.rect(self.screen, (180, 20, 20), (40, 25, 230, 20))
            p1_w = int(230 * (self.p1['health'] / 100.0))
            if p1_w > 0:
                pygame.draw.rect(self.screen, (255, 225, 20), (40, 25, p1_w, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (38, 23, 234, 24), 2)
            lbl1 = self.font.render("RYU", True, (255, 255, 255))
            self.screen.blit(lbl1, (40, 50))

            # P2 Health (Drains from right to left)
            pygame.draw.rect(self.screen, (180, 20, 20), (370, 25, 230, 20))
            p2_w = int(230 * (self.p2['health'] / 100.0))
            if p2_w > 0:
                pygame.draw.rect(self.screen, (255, 225, 20), (370 + (230 - p2_w), 25, p2_w, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (368, 23, 234, 24), 2)
            lbl2 = self.font.render("KEN", True, (255, 255, 255))
            self.screen.blit(lbl2, (565, 50))

            # Round Timer
            timer_txt = self.font_timer.render(f"{int(self.match_timer):02d}", True, (255, 230, 40))
            self.screen.blit(timer_txt, ((self.size[0] - timer_txt.get_width()) // 2, 22))

            # KO Text Overlay
            if self.round_state == 'KO':
                winner_name = "RYU" if self.p1['health'] > self.p2['health'] else "KEN"
                ko_txt = self.font_large.render(f"K.O. — {winner_name} WINS!", True, (255, 50, 50))
                self.screen.blit(ko_txt, ((self.size[0] - ko_txt.get_width()) // 2, 140))

            # Controls HUD at bottom
            hint = self.font.render("A/D: MOVER  W: SALTAR  J: GOLPE  K: FUERTE  L: PATADA  ESPACIO: HADOUKEN", True, (220, 220, 220))
            self.screen.blit(hint, ((self.size[0] - hint.get_width()) // 2, 452))

            pygame.display.flip()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()
