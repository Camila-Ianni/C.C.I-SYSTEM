"""
Unit & Integration Test Suite for Weapons, Projectiles, Audio SFX and Player Aiming/Crouch States.
Covers:
1. Player Aiming UP (Standing, Running, Jumping).
2. Player Crouching (Idle ducking, Crawling, Crouch-Shooting, Crouch-Knife, Hitbox height shrink).
3. Handgun Pistol directional firing (Horizontal, Vertical UP, Downwards in air, Crouched).
4. Heavy Machine Gun (H) directional firing (Horizontal, Diagonal UP, Vertical UP, Crouched, continuous fire).
5. Shotgun (S) massive blast cone (Horizontal and Vertical UP penetration).
6. Rocket Launcher (R) guided homing missile (Horizontal and Vertical UP launch, target steering).
7. Flame Shot (F) rolling fireball (Horizontal platform rolling, Vertical UP launch, multi-hit penetration).
8. SFX synthesis and routing.
"""
import os
import unittest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE
)
from src.entities.player import Player
from src.weapons.projectile import Bullet, Grenade
from src.weapons.special_weapons import (
    HeavyMachineGunBullet, ShotgunBlast, RocketMissile, FlameShotBall
)
from src.core.sound_manager import SoundManager
from src.core.sfx_synth import generate_weapon_sfx
from src.core.camera import Camera

class MockInput:
    def __init__(self):
        self.held = set()
        self.just_pressed = set()
        
    def is_held(self, action):
        return action in self.held
        
    def is_just_pressed(self, action):
        return action in self.just_pressed


class TestWeaponsAndAiming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

    def setUp(self):
        self.player_m = Player(x=100, y=180, character="marco")
        self.player_t = Player(x=100, y=180, character="tarma")
        self.input = MockInput()
        self.sound = SoundManager()

    # --- 1. Player Aiming UP Tests ---
    def test_standing_aim_up(self):
        """Holding UP while grounded activates aim up without horizontal velocity."""
        self.input.held.add(ACTION_UP)
        self.player_m.physics.is_grounded = True
        self.player_m.handle_input(self.input)
        self.assertTrue(self.player_m.is_aiming_up)
        self.assertFalse(self.player_m.is_crouching)
        self.assertEqual(self.player_m.physics.vx, 0.0)

    def test_running_aim_up(self):
        """Holding UP and RIGHT while grounded runs while aiming diagonally/upwards."""
        self.input.held.add(ACTION_UP)
        self.input.held.add(ACTION_RIGHT)
        self.player_m.physics.is_grounded = True
        self.player_m.handle_input(self.input)
        self.assertTrue(self.player_m.is_aiming_up)
        self.assertGreater(self.player_m.physics.vx, 0.0)

    def test_air_aim_up_and_down(self):
        """In mid-air, holding UP aims UP, holding DOWN aims DOWN."""
        self.player_m.physics.is_grounded = False
        
        self.input.held = {ACTION_UP}
        self.player_m.handle_input(self.input)
        self.assertTrue(self.player_m.is_aiming_up)
        self.assertFalse(self.player_m.is_aiming_down)
        
        self.input.held = {ACTION_DOWN}
        self.player_m.handle_input(self.input)
        self.assertFalse(self.player_m.is_aiming_up)
        self.assertTrue(self.player_m.is_aiming_down)

    # --- 2. Player Crouching Tests ---
    def test_crouching_hitbox_shrink(self):
        """Crouching shrinks player collision box from height 34 to 18 (dodging high fire)."""
        self.player_m.physics.is_grounded = True
        self.assertEqual(self.player_m.physics.height, 34.0)
        
        self.input.held = {ACTION_DOWN}
        self.player_m.handle_input(self.input)
        self.assertTrue(self.player_m.is_crouching)
        self.assertEqual(self.player_m.physics.height, 18.0)
        
        # Releasing DOWN restores full standing height
        self.input.held.clear()
        self.player_m.handle_input(self.input)
        self.assertFalse(self.player_m.is_crouching)
        self.assertEqual(self.player_m.physics.height, 34.0)

    def test_crouch_crawling(self):
        """Holding DOWN and RIGHT moves the player forward at reduced crawl speed."""
        self.player_m.physics.is_grounded = True
        self.input.held = {ACTION_DOWN, ACTION_RIGHT}
        self.player_m.handle_input(self.input)
        self.assertTrue(self.player_m.is_crouching)
        self.assertAlmostEqual(self.player_m.physics.vx, 1.75 * 0.6, places=2)

    def test_crouch_shoot_state(self):
        """Firing while crouched activates crouch shoot animation state."""
        self.player_m.physics.is_grounded = True
        self.input.held = {ACTION_DOWN}
        self.input.just_pressed = {ACTION_SHOOT}
        projectiles = []
        self.player_m.handle_input(self.input, projectiles=projectiles)
        self.assertTrue(self.player_m.is_crouching)
        self.assertTrue(self.player_m.is_crouch_shooting)
        self.assertEqual(len(projectiles), 1)
        # Bullet spawned at low crouch height (y - 12)
        self.assertAlmostEqual(projectiles[0].y, self.player_m.physics.y - 12.0)

    # --- 3. Handgun Pistol Directional Tests ---
    def test_handgun_upward_fire(self):
        """Pistol fires straight UP when holding UP."""
        self.player_m.physics.is_grounded = True
        self.input.held = {ACTION_UP}
        self.input.just_pressed = {ACTION_SHOOT}
        projectiles = []
        self.player_m.handle_input(self.input, projectiles=projectiles)
        self.assertEqual(len(projectiles), 1)
        bullet = projectiles[0]
        self.assertEqual(bullet.dir_x, 0.0)
        self.assertEqual(bullet.dir_y, -1.0)

    def test_handgun_downward_air_fire(self):
        """Pistol fires straight DOWN when jumping and holding DOWN."""
        self.player_m.physics.is_grounded = False
        self.input.held = {ACTION_DOWN}
        self.input.just_pressed = {ACTION_SHOOT}
        projectiles = []
        self.player_m.handle_input(self.input, projectiles=projectiles)
        self.assertEqual(len(projectiles), 1)
        bullet = projectiles[0]
        self.assertEqual(bullet.dir_x, 0.0)
        self.assertEqual(bullet.dir_y, 1.0)

    # --- 4. Heavy Machine Gun Tests ---
    def test_hmg_diagonal_and_vertical_fire(self):
        """HMG fires diagonally when running and aiming up, and straight up when standing."""
        self.player_m.weapon_type = "H"
        self.player_m.physics.is_grounded = True
        
        # Standing straight up
        self.input.held = {ACTION_UP, ACTION_SHOOT}
        projectiles = []
        self.player_m.handle_input(self.input, projectiles=projectiles)
        self.assertEqual(len(projectiles), 1)
        self.assertEqual(projectiles[0].dir_x, 0.0)
        self.assertEqual(projectiles[0].dir_y, -1.0)
        
        # Moving diagonal up
        self.player_m.shoot_cooldown = 0
        self.input.held = {ACTION_UP, ACTION_RIGHT, ACTION_SHOOT}
        projectiles.clear()
        self.player_m.handle_input(self.input, projectiles=projectiles)
        self.assertEqual(len(projectiles), 1)
        self.assertAlmostEqual(projectiles[0].dir_x, 0.707, places=2)
        self.assertAlmostEqual(projectiles[0].dir_y, -0.707, places=2)

    # --- 5. Shotgun Tests ---
    def test_shotgun_horizontal_and_upward_blast(self):
        """Shotgun blasts horizontally or straight upwards with massive penetration hitboxes."""
        sg_h = ShotgunBlast(100, 150, facing_right=True, aiming_up=False)
        self.assertGreater(sg_h.hitbox.width, sg_h.hitbox.height)
        
        sg_u = ShotgunBlast(100, 150, facing_right=True, aiming_up=True)
        self.assertGreater(sg_u.hitbox.height, sg_u.hitbox.width)
        self.assertEqual(sg_u.damage, 20)

    # --- 6. Rocket Launcher Tests ---
    def test_rocket_missile_upward_and_homing(self):
        """Rocket missile launches vertically when aiming up, and horizontal with initial forward velocity."""
        rk_u = RocketMissile(100, 150, facing_right=True, aiming_up=True)
        self.assertEqual(rk_u.vx, 0.0)
        self.assertLess(rk_u.vy, 0.0)
        
        rk_h = RocketMissile(100, 150, facing_right=True, aiming_up=False)
        self.assertGreater(rk_h.vx, 0.0)

    # --- 7. Flame Shot Tests ---
    def test_flame_shot_rolling_and_upward(self):
        """Flame shot fireball rolls along platforms or launches upwards."""
        fl_u = FlameShotBall(100, 150, facing_right=True, aiming_up=True)
        self.assertEqual(fl_u.vx, 0.0)
        self.assertLess(fl_u.vy, 0.0)
        
        fl_h = FlameShotBall(100, 150, facing_right=True, aiming_up=False)
        self.assertGreater(fl_h.vx, 0.0)
        self.assertEqual(fl_h.damage, 15)

    # --- 8. Tarma Roving Support ---
    def test_tarma_roving_aiming_and_crouch(self):
        """Tarma Roving character initializes and handles aiming and crouching identically."""
        self.player_t.physics.is_grounded = True
        self.input.held = {ACTION_DOWN}
        self.player_t.handle_input(self.input)
        self.assertTrue(self.player_t.is_crouching)
        self.assertEqual(self.player_t.physics.height, 18.0)

    # --- 9. Audio Synthesis Tests ---
    def test_weapon_sfx_synthesis(self):
        """Verifies synthesized arcade sound effects are generated cleanly."""
        sfx = generate_weapon_sfx()
        expected = ["gunshot", "heavy_machine_gun_shot", "shotgun_blast", "rocket_fire", "flame_fire", "knife", "grenade_bounce"]
        for k in expected:
            self.assertIn(k, sfx)
    # --- 10. Weapon Visual Synchronization & Animation Integrity ---
    def test_default_weapon_is_pistol_with_handgun_sprites(self):
        """Player defaults to PISTOL and maintains authentic handgun crouch and standing frames."""
        self.assertEqual(self.player_m.weapon_type, "PISTOL")
        self.assertEqual(self.player_m.current_weapon_visual, "PISTOL")
        # Ensure crouch idle, crawl, shoot exist and have valid dimensions
        self.assertIsNotNone(self.player_m.crouch_idle_r)
        self.assertGreater(len(self.player_m.crouch_crawl_r), 0)
        self.assertGreater(len(self.player_m.crouch_shoot_r), 0)
        # Verify crouching frames are sized 48x48
        self.assertEqual(self.player_m.crouch_idle_r.get_size(), (48, 48))
        self.assertEqual(self.player_m.crouch_shoot_r[0].get_size(), (48, 48))

    def test_heavy_weapon_visual_switch_and_integrity(self):
        """Picking up Heavy Machine Gun or other heavy weapons updates visual frames cleanly."""
        self.player_m.weapon_type = "H"
        self.player_m.sync_weapon_visuals()
        self.assertEqual(self.player_m.current_weapon_visual, "H")
        
        # Verify heavy weapon frames are loaded and valid
        self.assertGreater(len(self.player_m.idle_frames_r), 0)
        self.assertGreater(len(self.player_m.run_frames_r), 0)
        self.assertGreater(len(self.player_m.aim_up_frames_r), 0)
        self.assertGreater(len(self.player_m.crouch_shoot_r), 0)
        self.assertEqual(self.player_m.jump_frame_r.get_size(), (48, 48))
        self.assertEqual(self.player_m.jump_aim_down_r.get_size(), (48, 48))

        # Tarma as well
        self.player_t.weapon_type = "H"
        self.player_t.sync_weapon_visuals()
        self.assertEqual(self.player_t.current_weapon_visual, "H")
    def test_heavy_weapon_running_no_walkie_talkie(self):
        """Verify that Heavy Machine Gun running animation has 12 distinct 48x48 frames for both Marco and Tarma."""
        self.player_m.weapon_type = "H"
        self.player_m.sync_weapon_visuals()
        self.assertEqual(len(self.player_m.run_frames_r), 12)
        for frame in self.player_m.run_frames_r:
            self.assertEqual(frame.get_size(), (48, 48))

        self.player_t.weapon_type = "H"
        self.player_t.sync_weapon_visuals()
        self.assertEqual(len(self.player_t.run_frames_r), 12)
        for frame in self.player_t.run_frames_r:
            self.assertEqual(frame.get_size(), (48, 48))

    def test_pistol_authentic_aim_up_frames(self):
        """Verify pistol aim_up frames exist and are 48x48 for both Marco and Tarma."""
        self.player_m.weapon_type = "PISTOL"
        self.player_m.sync_weapon_visuals()
        self.assertEqual(len(self.player_m.aim_up_frames_r), 4)
        for frame in self.player_m.aim_up_frames_r:
            self.assertEqual(frame.get_size(), (48, 48))

        self.player_t.weapon_type = "PISTOL"
        self.player_t.sync_weapon_visuals()
        self.assertEqual(len(self.player_t.aim_up_frames_r), 4)
        for frame in self.player_t.aim_up_frames_r:
            self.assertEqual(frame.get_size(), (48, 48))

    def test_running_animation_cadence(self):
        """Verify running leg animation cadence is set to fast authentic arcade speed (3 ticks per frame)."""
        self.assertEqual(self.player_m.anim_run.frame_duration, 3)
        self.assertEqual(self.player_m.anim_aim_up_run.frame_duration, 3)
        self.assertEqual(self.player_t.anim_run.frame_duration, 3)
        self.assertEqual(self.player_t.anim_aim_up_run.frame_duration, 3)

    def test_jump_aim_up_legs_visible(self):
        """Verify jump aim up sprite retains full legs (thighs, knees, boots) for Marco and Tarma across weapons."""
        for p in [self.player_m, self.player_t]:
            for wt in ["PISTOL", "H", "S", "R", "F"]:
                p.weapon_type = wt
                p.sync_weapon_visuals()
                # Surface canvas size accommodates full torso and full jump legs
                self.assertEqual(p.jump_aim_up_r.get_size(), (48, 64))
                self.assertEqual(p.jump_aim_up_l.get_size(), (48, 64))

                # Verify substantial non-empty pixels in the leg region (y from 37 to 62)
                leg_pixels = 0
                for y in range(37, 62):
                    for x in range(48):
                        if p.jump_aim_up_r.get_at((x, y)).a > 0:
                            leg_pixels += 1
                self.assertGreater(leg_pixels, 50, f"Missing legs for {p.character} {wt}")

    def test_ammo_crate_walkthrough_and_boost(self):
        """Verify walking over ammo crates claims them directly and adds +50 bullets regardless of weapon."""
        from src.entities.destructibles import DestructibleCrate
        from src.levels.mission1 import Mission1

        level = Mission1()
        # 1. Player with 5 bullets in any special weapon gets +50 bullets (now 55)
        for wt in ["H", "S", "R", "F"]:
            player = Player(x=100, y=198, character="marco")
            player.weapon_type = wt
            player.ammo = 5
            crate = DestructibleCrate(x=100, y=198)
            level.destructibles = [crate]
            level.update(player, Camera())
            self.assertTrue(crate.is_dead, f"Crate should be claimed when player walks over it for weapon {wt}")
            self.assertEqual(player.ammo, 55, f"Expected 55 bullets for {wt}, got {player.ammo}")
            self.assertEqual(player.weapon_type, wt)

        # 2. Player with Pistol acquires Heavy Machine Gun with 50 bullets
        player = Player(x=100, y=198, character="marco")
        player.weapon_type = "PISTOL"
        player.ammo = -1
        crate = DestructibleCrate(x=100, y=198)
        level.destructibles = [crate]
        level.update(player, Camera())
        self.assertTrue(crate.is_dead)
        self.assertEqual(player.weapon_type, "H")
        self.assertEqual(player.ammo, 50)

    def test_ammo_crate_bullets_pass_through(self):
        """Verify bullets pass through ammo crates without being absorbed as shields."""
        from src.game import Game
        from src.entities.destructibles import DestructibleCrate
        from src.weapons.projectile import Bullet

        game = Game()
        game.start_new_campaign("marco")
        crate = DestructibleCrate(x=150, y=170)
        game.level.destructibles = [crate]
        
        # Fire bullet through crate
        bullet = Bullet(x=140, y=170, dir_x=1.0, dir_y=0.0, speed=6.0)
        game.player_projectiles = [bullet]
        game.update()
        self.assertFalse(bullet.is_dead, "Bullet should not be destroyed by ammo crate")
        self.assertFalse(crate.is_dead, "Ammo crate should not be destroyed by bullet impact")

    def test_standing_shoot_animation(self):
        """Verify standing still and firing plays authentic shooting animation and sets timer."""
        for p in [self.player_m, self.player_t]:
            for wt in ["PISTOL", "H"]:
                p.weapon_type = wt
                p.sync_weapon_visuals()
                p.physics.is_grounded = True
                p.physics.vx = 0.0
                p.is_aiming_up = False
                p.is_crouching = False
                p.shoot_cooldown = 0
                
                inp = MockInput()
                inp.just_pressed.add(ACTION_SHOOT)
                projectiles = []
                p.handle_input(inp, projectiles=projectiles)
                
                self.assertTrue(p.is_standing_shooting, f"Standing shoot should trigger for {p.character} {wt}")
                expected_timer = 12 if wt == "H" else 16
                self.assertEqual(p.standing_shoot_timer, expected_timer)
                self.assertIsNotNone(p.anim_shoot)
                self.assertGreater(len(p.anim_shoot.frames), 0)
                
                # Check draw surface is shoot animation
                surf = pygame.Surface((320, 224))
                cam = Camera()
                p.draw(surf, cam)
                
                # Moving cancels standing shoot immediately
                p.physics.vx = 2.0
                p.update()
                self.assertFalse(p.is_standing_shooting)
                self.assertEqual(p.standing_shoot_timer, 0)
                p.physics.vx = 0.0
                p.shoot_cooldown = 0

    def test_jump_aim_down_sprites_intact(self):
        """Verify jump aim down sprites are anatomically complete with intact legs for Marco and Tarma."""
        for p in [self.player_m, self.player_t]:
            for wt in ["PISTOL", "H", "S", "R", "F"]:
                p.weapon_type = wt
                p.sync_weapon_visuals()
                self.assertEqual(p.jump_aim_down_r.get_size(), (48, 48))
                self.assertEqual(p.jump_aim_down_l.get_size(), (48, 48))
                
                # Verify non-empty pixels in lower half (legs)
                lower_pixels = 0
                for y in range(24, 48):
                    for x in range(48):
                        if p.jump_aim_down_r.get_at((x, y)).a > 0:
                            lower_pixels += 1
                self.assertGreater(lower_pixels, 40, f"Jump aim down lower body empty for {p.character} {wt}")

    def test_rocket_launcher_cylindrical_missile(self):
        """Verify rocket launcher loads authentic cylindrical rockets and emits rocket smoke."""
        from src.engine.particle_system import ParticleSystem
        RocketMissile.load_sprites()
        self.assertIsNotNone(RocketMissile.frames_r)
        self.assertEqual(len(RocketMissile.frames_r), 2)
        # Verify frame dimensions (cylindrical elongated rocket canvas 52x16)
        f = RocketMissile.frames_r[0]
        self.assertEqual(f.get_size(), (52, 16))
        
        # Verify missile spawning and smoke emission
        ps = ParticleSystem()
        missile = RocketMissile(100, 100, facing_right=True)
        # Advance 3 frames to trigger smoke trail
        for _ in range(3):
            missile.update(particle_system=ps)
        self.assertGreater(len(ps.animated_effects), 0, "Rocket should emit smoke trail particles")


    def test_run_shoot_animation(self):
        """Verify that running and firing triggers run-shoot animation with legs and torso firing forward."""
        for p in [self.player_m, self.player_t]:
            for wt in ["PISTOL", "H", "S", "R", "F"]:
                p.weapon_type = wt
                p.sync_weapon_visuals()
                p.physics.is_grounded = True
                p.physics.vx = 2.0
                p.is_aiming_up = False
                p.is_crouching = False
                p.shoot_cooldown = 0
                
                inp = MockInput()
                inp.held.add(ACTION_RIGHT)
                inp.just_pressed.add(ACTION_SHOOT)
                projectiles = []
                p.handle_input(inp, projectiles=projectiles)
                
                self.assertTrue(p.is_run_shooting, f"Run-shoot should be active for {p.character} {wt}")
                self.assertEqual(p.run_shoot_timer, 12)
                self.assertFalse(p.is_standing_shooting)
                self.assertIsNotNone(p.anim_run_shoot)
                self.assertEqual(len(p.anim_run_shoot.frames), 12)
                
                # Check draw surface renders run-shoot animation
                surf = pygame.Surface((320, 224))
                cam = Camera()
                p.draw(surf, cam)
                
                # Advance 12 frames without firing -> should revert to normal running
                inp_run_only = MockInput()
                inp_run_only.held.add(ACTION_RIGHT)
                for _ in range(12):
                    p.handle_input(inp_run_only)
                    p.update()
                self.assertFalse(p.is_run_shooting)

    def test_shotgun_blast_owner_tracking(self):
        """Verify ShotgunBlast dynamically tracks owner's muzzle position while moving."""
        p = self.player_m
        p.physics.x = 100.0
        p.physics.y = 150.0
        p.facing_right = True
        p.weapon_type = "S"
        p.sync_weapon_visuals()
        
        projectiles = []
        inp = MockInput()
        inp.just_pressed.add(ACTION_SHOOT)
        p.handle_input(inp, projectiles=projectiles)
        
        self.assertEqual(len(projectiles), 1)
        blast = projectiles[0]
        self.assertIsInstance(blast, ShotgunBlast)
        self.assertIs(blast.owner, p)
        initial_x = blast.x
        
        # Move player forward by 30 pixels
        p.physics.x += 30.0
        blast.update()
        
        # Blast must track player forward without lagging behind
        self.assertAlmostEqual(blast.x, initial_x + 30.0, delta=1.0)
        self.assertAlmostEqual(blast.hitbox.left, (initial_x + 30.0), delta=1.0)

    def test_heavy_machine_gun_hair_uncut(self):
        """Verify Heavy Machine Gun shoot frames have full uncut hair height (30px)."""
        for p in [self.player_m, self.player_t]:
            p.weapon_type = "H"
            p.sync_weapon_visuals()
            self.assertIsNotNone(p.shoot_frames_r)
            for frame in p.shoot_frames_r:
                self.assertEqual(frame.get_size(), (48, 48))
                # Verify non-empty pixels exist in top rows (head/hair)
                top_hair_pixels = sum(
                    1 for y in range(5, 15) for x in range(10, 30) if frame.get_at((x, y)).a > 0
                )
                self.assertGreater(top_hair_pixels, 20, f"Top hair missing in H shoot frame for {p.character}")


if __name__ == "__main__":
    unittest.main()


