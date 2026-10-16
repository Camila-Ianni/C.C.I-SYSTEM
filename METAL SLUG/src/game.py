"""
Main Game Loop and Engine State Coordinator for Metal Slug 1 (Phases 1-8 Complete).
Manages:
- Title Screen, Character Selection (Marco/Tarma), Campaign Progression (M1-M6),
  Mission Results, Game Over & Continue Flow, Victory Sequence.
- Pixel-perfect 320x224 Neo-Geo arcade emulation scaled 3x (960x672).
"""
import sys
import pygame
from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT,
    FPS, TITLE, COLOR_BLACK, ACTION_UP, ACTION_JUMP, ACTION_SHOOT
)
from src.core.input_manager import InputManager
from src.core.sound_manager import SoundManager
from src.core.camera import Camera
from src.engine.particle_system import ParticleSystem
from src.ui.hud import HUD
from src.ui.menu_screens import (
    TitleScreen, CharacterSelectScreen, MissionResultsScreen,
    GameOverScreen, VictoryScreen
)
from src.levels.stage_manager import StageManager
from src.entities.player import Player
from src.engine.layers import LayeredRenderer, RenderLayer
from src.engine.pymunk_physics import PymunkPhysicsWorld

# Game States
STATE_TITLE = "title"
STATE_CHAR_SELECT = "char_select"
STATE_GAMEPLAY = "gameplay"
STATE_RESULTS = "results"
STATE_GAMEOVER = "gameover"
STATE_VICTORY = "victory"

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.virtual_screen = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Core Systems
        self.input_manager = InputManager()
        self.sound_manager = SoundManager()
        self.particle_system = ParticleSystem()
        self.particle_system.load_effects()
        self.hud = HUD()
        self.stage_manager = StageManager()
        self.camera = Camera(world_width=4153, world_height=224)
        
        # Menu Screens
        self.title_screen = TitleScreen()
        self.char_select_screen = None
        self.results_screen = None
        self.game_over_screen = None
        self.victory_screen = None
        
        # Layered Rendering & Pymunk Physics Systems
        self.layered_renderer = LayeredRenderer()
        self.physics_world = PymunkPhysicsWorld()

        # State Management
        self.state = STATE_TITLE
        self.selected_character = "marco"
        self.player = None
        self.level = None
        self.player_projectiles = []
        self.enemy_projectiles = []
        self.time_remaining = 60.0
        self.results_delay_timer = 0
        self.is_running = True

    def start_new_campaign(self, character="marco"):
        self.selected_character = character
        self.player = Player(x=60, y=160, character=character)
        self.stage_manager.load_mission(1)
        self.level = self.stage_manager.active_level
        self.camera = Camera(world_width=self.level.stage_width, world_height=224)
        self.physics_world.clear()
        for plat in self.level.platforms:
            self.physics_world.add_platform(plat)
        self.player_projectiles.clear()
        self.enemy_projectiles.clear()
        self.time_remaining = 60.0
        self.results_delay_timer = 0
        self.state = STATE_GAMEPLAY
        self.sound_manager.play_mission_bgm(1)

    def setup_next_mission(self):
        self.level = self.stage_manager.active_level
        self.camera = Camera(world_width=self.level.stage_width, world_height=224)
        self.physics_world.clear()
        for plat in self.level.platforms:
            self.physics_world.add_platform(plat)
        self.player.physics.x = 60
        self.player.physics.y = 160
        self.player.physics.vx = 0
        self.player.physics.vy = 0
        self.player.is_dead = False
        self.player_projectiles.clear()
        self.enemy_projectiles.clear()
        self.time_remaining = 60.0
        self.results_delay_timer = 0
        self.state = STATE_GAMEPLAY
        self.sound_manager.play_mission_bgm(self.stage_manager.current_mission_index)

    def _is_confirm_event(self, event):
        if event.type == pygame.KEYDOWN:
            return event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j, pygame.K_z, pygame.K_f, pygame.K_1, pygame.K_KP1)
        elif event.type == pygame.JOYBUTTONDOWN:
            jid = getattr(event, 'instance_id', getattr(event, 'joy', 0))
            if jid == 0 and event.button in (0, 2, 6, 9, 10):  # Cross, Square, Options, L1, R1
                return True
        return False

    def _is_p2_start_event(self, event):
        if event.type == pygame.KEYDOWN:
            return event.key in (pygame.K_2, pygame.K_KP2)
        elif event.type == pygame.JOYBUTTONDOWN:
            jid = getattr(event, 'instance_id', getattr(event, 'joy', 0))
            if jid > 0 and event.button in (0, 2, 6, 9, 10):  # P2 Controller Start/Action
                return True
        return False

    def _is_coin_event(self, event):
        if event.type == pygame.KEYDOWN:
            return event.key in (pygame.K_5, pygame.K_c)
        elif event.type == pygame.JOYBUTTONDOWN:
            return event.button in (4, 15)  # Share/Create, Touchpad click
        return False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.is_running = False

            # Menu navigation & progression (Keyboard + PS5 Gamepad)
            if self.state == STATE_TITLE:
                if self.title_screen.stage != TitleScreen.STAGE_TITLE:
                    # While attract sequence is playing, any user action skips forward to Title screen
                    if self._is_confirm_event(event) or self._is_p2_start_event(event) or self._is_coin_event(event) or (event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN)):
                        self.title_screen.skip_to_title()
                else:
                    if self._is_coin_event(event):
                        self.title_screen.add_credit()
                        self.sound_manager.play_voice("bingo")
                    elif self._is_p2_start_event(event):
                        # Player 2 Start -> Authentic Metal Slug 1 default: Tarma Roving (ginger/brunette)
                        if self.title_screen.credits <= 0:
                            self.title_screen.add_credit()
                        self.title_screen.credits -= 1
                        self.start_new_campaign("tarma")
                    elif self._is_confirm_event(event):
                        # Player 1 Start -> Authentic Metal Slug 1 default: Marco Rossi (blonde)
                        if self.title_screen.credits <= 0:
                            self.title_screen.add_credit()
                        self.title_screen.credits -= 1
                        self.start_new_campaign("marco")

            elif self.state == STATE_CHAR_SELECT:
                # Direct fallback into gameplay if ever accessed
                char = self.char_select_screen.get_selected_character() if self.char_select_screen else "marco"
                self.start_new_campaign(char)

            elif self.state == STATE_RESULTS:
                if self._is_confirm_event(event):
                    if self.stage_manager.advance_to_next_mission():
                        self.setup_next_mission()
                    else:
                        self.victory_screen = VictoryScreen(final_score=self.player.score)
                        self.state = STATE_VICTORY
                        self.sound_manager.play_victory_bgm()

            elif self.state == STATE_GAMEOVER:
                if self._is_confirm_event(event):
                    # Continue game
                    self.player.lives = 3
                    self.player.is_dead = False
                    self.player.physics.x = 60
                    self.player.physics.y = 160
                    self.player_projectiles.clear()
                    self.enemy_projectiles.clear()
                    self.state = STATE_GAMEPLAY
                    self.sound_manager.play_mission_bgm(self.stage_manager.current_mission_index)

            elif self.state == STATE_VICTORY:
                if self._is_confirm_event(event):
                    self.state = STATE_TITLE
                    self.sound_manager.play_title_bgm()

            elif self.state == STATE_GAMEPLAY:
                # Metal Slug Attack shortcut: Key U or Gamepad Triangle (3)
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_u) or (event.type == pygame.JOYBUTTONDOWN and event.button == 3):
                    if self.level:
                        for s in self.level.slugs:
                            if s.is_occupied:
                                s.trigger_metal_slug_attack()

            self.input_manager.process_event(event)

    def update(self):
        if self.state == STATE_TITLE:
            self.title_screen.update()
            self.input_manager.update()
            return
        elif self.state == STATE_CHAR_SELECT:
            if self.char_select_screen:
                self.char_select_screen.update(self.input_manager)
            self.input_manager.update()
            return
        elif self.state == STATE_RESULTS:
            if self.results_screen:
                self.results_screen.update()
            self.input_manager.update()
            return
        elif self.state == STATE_GAMEOVER:
            if self.game_over_screen:
                self.game_over_screen.update()
                if self.game_over_screen.countdown <= 0:
                    self.state = STATE_TITLE
            self.input_manager.update()
            return
        elif self.state == STATE_VICTORY:
            if self.victory_screen:
                self.victory_screen.update()
            self.input_manager.update()
            return

        # STATE_GAMEPLAY Active Update
        if self.time_remaining > 0:
            self.time_remaining -= 1.0 / FPS
        if self.time_remaining <= 0:
            self.time_remaining = 0.0
            if not self.player.is_dead:
                self.player.is_dead = True

        # Check Active Slug
        active_slug = None
        for s in self.level.slugs:
            if s.is_occupied:
                active_slug = s
                break

        # 1. Player Boarding Logic
        if not active_slug:
            for s in self.level.slugs:
                if not s.is_dead and abs(s.physics.x - self.player.physics.x) < 36 and abs(s.physics.y - self.player.physics.y) < 28:
                    if self.input_manager.is_held(ACTION_UP) or self.input_manager.is_just_pressed(ACTION_UP) or self.input_manager.is_just_pressed(ACTION_JUMP):
                        s.enter_vehicle(self.player)
                        active_slug = s
                        break

        # 2. Update Input & Movement (Slug or On-Foot Player)
        if active_slug:
            if getattr(active_slug, '_just_entered', False):
                active_slug._just_entered = False
            else:
                active_slug.handle_input(
                    self.input_manager,
                    self.player_projectiles,
                    self.particle_system,
                    self.sound_manager
                )
            self.player.physics.x = active_slug.physics.x
            self.player.physics.y = active_slug.physics.y
            target_camera_x = active_slug.physics.x
            target_camera_y = active_slug.physics.y
        else:
            self.player.handle_input(
                self.input_manager,
                enemies=self.level.enemies,
                projectiles=self.player_projectiles,
                particle_system=self.particle_system,
                sound_manager=self.sound_manager
            )
            self.player.update(self.level.platforms)
            target_camera_x = self.player.physics.x
            target_camera_y = self.player.physics.y

        # Determine half-width for edge clamping
        half_w = (active_slug.physics.width / 2.0) if active_slug else (self.player.physics.width / 2.0)

        # Clamp position to screen left
        min_x = self.camera.x + half_w
        if target_camera_x < min_x:
            if active_slug:
                active_slug.physics.x = min_x
                if active_slug.physics.vx < 0:
                    active_slug.physics.vx = 0.0
            else:
                self.player.physics.x = min_x
                if self.player.physics.vx < 0:
                    self.player.physics.vx = 0.0

        # Clamp position to screen right when camera is locked or at stage end
        max_x = self.camera.x + VIRTUAL_WIDTH - half_w
        if self.camera.is_locked or self.camera.x >= getattr(self.level, 'stage_width', 4000) - VIRTUAL_WIDTH:
            if target_camera_x > max_x:
                if active_slug:
                    active_slug.physics.x = max_x
                    if active_slug.physics.vx > 0:
                        active_slug.physics.vx = 0.0
                else:
                    self.player.physics.x = max_x
                    if self.player.physics.vx > 0:
                        self.player.physics.vx = 0.0

        # Check Player Death and Lives
        if self.player.is_dead:
            if self.player.lives > 1:
                self.player.lives -= 1
                self.player.is_dead = False
                self.player.is_invincible = True
                self.player.invincible_timer = 120
                new_x = max(min_x + 30, self.player.physics.x - 40)
                self.player.physics.x = new_x
                self.player.physics.vx = 0.0
                self.player.physics.vy = 0.0
                floor_y = 198.0
                if hasattr(self.level, 'platforms'):
                    for p in self.level.platforms:
                        if not p.semi_solid:
                            h = p.get_height_at(new_x)
                            if h is not None:
                                floor_y = h
                                break
                self.player.physics.y = floor_y - 20.0
                self.player.physics.is_grounded = False
                self.time_remaining = 60.0
            else:
                self.game_over_screen = GameOverScreen()
                self.state = STATE_GAMEOVER
                self.sound_manager.play_game_over_bgm()
                return

        # 3. Update Level, Enemies, Pickups, Destructibles & Slugs
        self.level.update(
            self.player, self.camera, self.player_projectiles,
            self.particle_system, self.enemy_projectiles, self.sound_manager
        )

        # Enforce post-update screen clamp on active slug
        if active_slug:
            if active_slug.physics.x < min_x:
                active_slug.physics.x = min_x
                if active_slug.physics.vx < 0:
                    active_slug.physics.vx = 0.0
            if (self.camera.is_locked or self.camera.x >= getattr(self.level, 'stage_width', 4000) - VIRTUAL_WIDTH) and active_slug.physics.x > max_x:
                active_slug.physics.x = max_x
                if active_slug.physics.vx > 0:
                    active_slug.physics.vx = 0.0
        
        # Check Boss Fight BGM trigger
        if self.level.boss and not self.level.boss.is_defeated and self.camera.is_locked:
            self.sound_manager.play_boss_bgm()
        
        # 4. Update Camera
        self.camera.update(target_camera_x, target_camera_y)
        
        # 5. Update Projectiles & Combat Collisions
        for b in self.player_projectiles:
            if hasattr(b, 'target'):
                b.update(self.level.enemies, self.particle_system, self.camera)
            elif hasattr(b, 'bounces') or hasattr(b, 'radius'):
                b.update(self.level.platforms, self.camera)
            else:
                b.update(self.camera)

            # Check if bullet rescues a P.O.W.
            if not b.is_dead and hasattr(b, 'hitbox'):
                for pow_npc in self.level.pows:
                    if not pow_npc.is_rescued and b.hitbox.colliderect(pow_npc.physics.hurtbox):
                        if pow_npc.trigger_rescue(self.sound_manager):
                            self.player.score += 1000
                            self.player.pows_rescued = getattr(self.player, 'pows_rescued', 0) + 1
                        b.is_dead = True
                        break

            # Check projectile collisions against destructibles (crates, barrels, huts)
            if not b.is_dead and hasattr(b, 'hitbox') and hasattr(self.level, 'destructibles'):
                for d in self.level.destructibles:
                    # Bullets pass through ammo crates without obstruction
                    if type(d).__name__ == "DestructibleCrate":
                        continue
                    if not d.is_dead and b.hitbox.colliderect(d.hitbox):
                        damage = getattr(b, 'damage', 1)
                        if hasattr(d, 'take_damage'):
                            if hasattr(d, 'blast_radius'):  # ExplosiveBarrel
                                d.take_damage(damage, enemies=self.level.enemies, particle_system=self.particle_system, sound_manager=self.sound_manager, camera=self.camera)
                            elif hasattr(d, 'shake_timer'): # DestructibleHut
                                d.take_damage(damage, pickups=self.level.pickups, particle_system=self.particle_system, sound_manager=self.sound_manager, camera=self.camera)
                            else: # DestructibleCrate
                                d.take_damage(damage, pickups=self.level.pickups, particle_system=self.particle_system, sound_manager=self.sound_manager)
                        if not hasattr(b, 'hit_enemies'):
                            b.is_dead = True
                        self.player.score += 50
                        break

            # Check projectile collisions against Boss
            if self.level.boss and not self.level.boss.is_defeated and not b.is_dead and hasattr(b, 'hitbox'):
                if b.hitbox.colliderect(self.level.boss.hurtbox):
                    damage = getattr(b, 'damage', 1)
                    self.level.boss.take_damage(damage)
                    if not hasattr(b, 'hit_enemies'):
                        b.is_dead = True
                    self.player.score += 50
                    self.particle_system.spawn_explosion(b.x, b.y, size="small")

            # Check projectile collisions against enemies
            if not b.is_dead and hasattr(b, 'hitbox'):
                for e in self.level.enemies:
                    if not e.is_dead and b.hitbox.colliderect(e.physics.hurtbox):
                        # Penetrating weapon check (Flame Shot)
                        if hasattr(b, 'hit_enemies'):
                            if e in b.hit_enemies:
                                continue
                            b.hit_enemies.add(e)

                        if hasattr(e, 'take_hit_from_projectile'):
                            hit_landed = e.take_hit_from_projectile(b, self.particle_system)
                            if not hasattr(b, 'hit_enemies'):
                                b.is_dead = True
                            if hit_landed and e.is_dead:
                                self.player.score += 200
                                self.particle_system.spawn_explosion(e.physics.x, e.physics.y - 16, size="small")
                        else:
                            damage = getattr(b, 'damage', 1)
                            # Weapon-specific authentic death: Flame Shot incinerates into burning skeleton/ash
                            from src.weapons.special_weapons import FlameShotBall
                            death_type = "flame" if isinstance(b, FlameShotBall) else "bullet"
                            e.take_damage(damage, death_type=death_type)
                            if not hasattr(b, 'hit_enemies'):
                                b.is_dead = True
                            pts = 1000 if hasattr(e, 'patrol_dir') else (500 if hasattr(e, 'speed') else 100)
                            if e.is_dead:
                                self.player.score += pts
                                size = "medium" if hasattr(e, 'patrol_dir') else "small"
                                self.particle_system.spawn_explosion(e.physics.x, e.physics.y - 16, size=size)
                        break
                        
            # Check grenade explosions
            if hasattr(b, 'exploded') and b.exploded:
                self.particle_system.spawn_explosion(b.x, b.y, size="medium")
                self.camera.trigger_shake(duration_frames=8, magnitude=2)
                
                # Check grenade damage to Boss
                if self.level.boss and not self.level.boss.is_defeated:
                    if abs(self.level.boss.x - b.x) < 100:
                        self.level.boss.take_damage(10)
                        self.player.score += 500
                        
                for e in self.level.enemies:
                    if not e.is_dead and abs(e.physics.x - b.x) < 40 and abs(e.physics.y - b.y) < 40:
                        e.take_damage(10, death_type="explosion")
                        if e.is_dead:
                            pts = 1000 if hasattr(e, 'patrol_dir') else 200
                            self.player.score += pts

                # Check grenade damage to destructibles
                if hasattr(self.level, 'destructibles'):
                    for d in self.level.destructibles:
                        if not d.is_dead and abs(d.physics.x - b.x) < 45 and abs(d.physics.y - b.y) < 45:
                            if hasattr(d, 'blast_radius'):
                                d.take_damage(10, enemies=self.level.enemies, particle_system=self.particle_system, sound_manager=self.sound_manager, camera=self.camera)
                            elif hasattr(d, 'shake_timer'):
                                d.take_damage(10, pickups=self.level.pickups, particle_system=self.particle_system, sound_manager=self.sound_manager, camera=self.camera)
                            else:
                                d.take_damage(10, pickups=self.level.pickups, particle_system=self.particle_system, sound_manager=self.sound_manager)

        self.player_projectiles = [p for p in self.player_projectiles if not p.is_dead]
        
        # 6. Update Enemy Projectiles
        for eb in self.enemy_projectiles:
            if hasattr(eb, 'gravity'):
                eb.update(self.level.platforms, self.camera)
            else:
                eb.update(self.camera)
            if hasattr(eb, 'exploded') and eb.exploded:
                self.particle_system.spawn_explosion(eb.x, eb.y, size="small")
                if not self.player.is_invincible and abs(self.player.physics.x - eb.x) < 28 and abs(self.player.physics.y - eb.y) < 28:
                    if active_slug:
                        active_slug.take_damage(1)
                    else:
                        self.player.is_dead = True
        self.enemy_projectiles = [p for p in self.enemy_projectiles if not p.is_dead]
        
        # 7. Update Particles & FX
        self.particle_system.update()

        # 8. Check Mission Complete Transition
        if self.level.is_mission_complete:
            self.results_delay_timer += 1
            if self.results_delay_timer == 1:
                self.sound_manager.play_stage_clear_bgm()
                self.sound_manager.play_mission_complete_voice()
            elif self.results_delay_timer >= 120:  # 2 seconds after victory fanfare
                slug_alive = any(not s.is_dead for s in self.level.slugs)
                self.results_screen = MissionResultsScreen(
                    mission_num=self.stage_manager.current_mission_index,
                    rescued_pows=getattr(self.player, 'pows_rescued', 0),
                    slug_intact=slug_alive,
                    score=self.player.score
                )
                self.state = STATE_RESULTS

        # Clear edge triggers at the end of gameplay frame
        self.input_manager.update()

    def draw(self):
        self.virtual_screen.fill(COLOR_BLACK)

        if self.state == STATE_TITLE:
            self.title_screen.draw(self.virtual_screen)
        elif self.state == STATE_CHAR_SELECT:
            if self.char_select_screen:
                self.char_select_screen.draw(self.virtual_screen)
        elif self.state == STATE_RESULTS:
            if self.results_screen:
                self.results_screen.draw(self.virtual_screen)
        elif self.state == STATE_GAMEOVER:
            if self.game_over_screen:
                self.game_over_screen.draw(self.virtual_screen)
        elif self.state == STATE_VICTORY:
            if self.victory_screen:
                self.victory_screen.draw(self.virtual_screen)
        elif self.state == STATE_GAMEPLAY:
            # 1. Level Background
            self.level.draw_background(self.virtual_screen, self.camera)
            # 2. Level Entities (Boss, Slugs, POWs, Pickups)
            self.level.draw_entities(self.virtual_screen, self.camera)
            # 3. Enemies
            for e in self.level.enemies:
                e.draw(self.virtual_screen, self.camera)
            # 4. Player (if not in slug)
            is_in_slug = any(s.is_occupied for s in self.level.slugs)
            if not is_in_slug:
                self.player.draw(self.virtual_screen, self.camera)
            # 5. Projectiles
            for p in self.player_projectiles:
                p.draw(self.virtual_screen, self.camera)
            for ep in self.enemy_projectiles:
                ep.draw(self.virtual_screen, self.camera)
            # 6. Particles
            self.particle_system.draw(self.virtual_screen, self.camera)
            # 7. Foreground Overlay (Submarine Rib Arches)
            if hasattr(self.level, 'draw_foreground'):
                self.level.draw_foreground(self.virtual_screen, self.camera)
            # 8. HUD
            active_slug = None
            for s in self.level.slugs:
                if s.is_occupied:
                    active_slug = s
                    break
            self.hud.draw(
                self.virtual_screen,
                self.player,
                time_remaining=self.time_remaining,
                show_go=self.level.is_encounter_cleared and not self.level.is_mission_complete,
                slug=active_slug,
                camera=self.camera
            )
            # 8. Mission Clear Overlay
            if self.level.is_mission_complete:
                banner_surf = pygame.Surface((VIRTUAL_WIDTH, 60), pygame.SRCALPHA)
                banner_surf.fill((0, 0, 0, 180))
                self.virtual_screen.blit(banner_surf, (0, 75))
                font_big = pygame.font.Font(None, 24)
                font_small = pygame.font.Font(None, 14)
                complete_txt = font_big.render(f"MISSION {self.stage_manager.current_mission_index} COMPLETE!", False, (248, 208, 0))
                cx = (VIRTUAL_WIDTH - complete_txt.get_width()) // 2
                self.virtual_screen.blit(complete_txt, (cx, 82))
                bonus_txt = font_small.render("ALL REBEL DEFENSES DESTROYED", False, (255, 255, 255))
                bx = (VIRTUAL_WIDTH - bonus_txt.get_width()) // 2
                self.virtual_screen.blit(bonus_txt, (bx, 108))

        # Scale 3x to Window Resolution
        scaled = pygame.transform.scale(self.virtual_screen, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def respawn_player(self):
        """Reset player state and stage timer upon life loss / respawn."""
        self.time_remaining = 60.0
        if self.player.lives > 1:
            self.player.lives -= 1
            self.player.is_dead = False
            self.player.is_invincible = True
            self.player.invincible_timer = 120
            self.player.physics.vx = 0.0
            self.player.physics.vy = 0.0
            floor_y = 198.0
            if hasattr(self.level, 'platforms'):
                for p in self.level.platforms:
                    if not p.semi_solid:
                        h = p.get_height_at(self.player.physics.x)
                        if h is not None:
                            floor_y = h
                            break
            self.player.physics.y = floor_y - 20.0
            self.player.physics.is_grounded = False
        else:
            self.game_over_screen = GameOverScreen()
            self.state = STATE_GAMEOVER

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
