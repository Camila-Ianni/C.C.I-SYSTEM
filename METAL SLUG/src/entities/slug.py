"""
Super Vehicle-001 (Metal Slug SV-001) Implementation (Phase 3).
Features:
- Track drive animation, suspension squash on jump and landing.
- Twin 360-degree Vulcan cannons with rapid fire.
- Heavy AP Cannon with explosive shells.
- Pilot Boarding and 'Slug Out' emergency bail with invincibility frames.
- 3 Armor points with damage smoke stages and GAS canister repairs.
- Metal Slug Attack (Kamikaze ramming self-destruction).
"""
import math
import pygame
from src.config import (
    CHROMA_CYAN, SLUG_SPEED, SLUG_JUMP_IMPULSE, GRAVITY,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE
)
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.special_weapons import HeavyMachineGunBullet
from src.weapons.projectile import Grenade

class MetalSlug:
    def __init__(self, x, y):
        self.physics = PhysicsBody(x, y, width=54, height=44)
        self.facing_right = True
        self.is_occupied = False
        self.pilot = None
        
        # Vehicle Stats
        self.max_armor = 3
        self.armor = 3
        self.cannon_ammo = 10
        self.is_dead = False
        self.is_exploding = False
        self.self_destruct_charging = False
        self.entry_hop_timer = 0
        self.shoot_cooldown = 0
        self.cannon_cooldown = 0
        
        # Aim angles
        self.turret_angle_deg = 0.0  # 0 = forward, 90 = up, -90 = down
        
        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Slugs/Neo Geo _ NGCD - Metal Slug - Slugs - Metal Slug.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_CYAN)
        
        # 1. Idle Body (y=24, 3 frames)
        idle_rects = [
            (11, 24, 58, 51),
            (76, 24, 59, 51),
            (141, 24, 58, 51)
        ]
        self.idle_frames_r = SpriteLoader.extract_frames(sheet, idle_rects, flip_x=False)
        self.idle_frames_l = SpriteLoader.extract_frames(sheet, idle_rects, flip_x=True)
        
        # 2. Driving Tracks (y=98, 8 frames)
        drive_rects = [
            (11, 98, 58, 52),
            (76, 99, 59, 51),
            (141, 100, 59, 50),
            (207, 99, 59, 51),
            (272, 98, 59, 52),
            (337, 99, 60, 51),
            (403, 101, 60, 49),
            (470, 100, 60, 50)
        ]
        self.drive_frames_r = SpriteLoader.extract_frames(sheet, drive_rects, flip_x=False)
        self.drive_frames_l = SpriteLoader.extract_frames(sheet, drive_rects, flip_x=True)
        
        # 3. Jump and Shoot
        self.jump_frame_r = SpriteLoader.get_subsurface(sheet, 10, 580, 55, 60, flip_x=False)
        self.jump_frame_l = SpriteLoader.get_subsurface(sheet, 10, 580, 55, 60, flip_x=True)
        
        self.anim_idle = Animation(self.idle_frames_r, frame_duration=8, loop=True)
        self.anim_drive = Animation(self.drive_frames_r, frame_duration=4, loop=True)

    def enter_vehicle(self, player, sound_manager=None):
        """Boards the player into the Metal Slug tank."""
        self.is_occupied = True
        self.pilot = player
        self._just_entered = True
        self.entry_hop_timer = 12  # 12-frame cosmetic entry hop animation
        player.is_invincible = True
        player.invincible_timer = 30
        if sound_manager is None:
            from src.core.sound_manager import SoundManager
            sound_manager = SoundManager()
        if sound_manager:
            sound_manager.play_slug_ok()

    def exit_vehicle(self):
        """Slug Out: Ejects the pilot upward with invulnerability frames."""
        if not self.is_occupied or not self.pilot:
            return None
        pilot = self.pilot
        self.is_occupied = False
        self.pilot = None
        
        # Position pilot leaping out of tank hatch
        pilot.physics.x = self.physics.x
        pilot.physics.y = self.physics.y - 36
        pilot.physics.vy = -5.5
        pilot.physics.vx = -1.5 if self.facing_right else 1.5
        pilot.is_invincible = True
        pilot.invincible_timer = 60
        return pilot

    def trigger_metal_slug_attack(self):
        """Metal Slug Attack: Kamikaze ramming self-destruction."""
        if not self.is_occupied:
            return
        pilot = self.exit_vehicle()
        self.self_destruct_charging = True
        self.physics.vx = 6.0 if self.facing_right else -6.0

    def take_damage(self, amount=1):
        if self.is_dead:
            return
        self.armor -= amount
        if self.armor <= 0:
            self.armor = 0
            self.is_dead = True
            if self.is_occupied:
                self.exit_vehicle()

    def repair(self):
        self.armor = min(self.max_armor, self.armor + 1)

    def handle_input(self, input_manager, projectiles, particle_system, sound_manager):
        if not self.is_occupied or self.is_dead:
            return

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.cannon_cooldown > 0:
            self.cannon_cooldown -= 1

        # Horizontal Drive
        if input_manager.is_held(ACTION_LEFT):
            self.physics.vx = -SLUG_SPEED
            self.facing_right = False
        elif input_manager.is_held(ACTION_RIGHT):
            self.physics.vx = SLUG_SPEED
            self.facing_right = True
        else:
            self.physics.vx = 0.0

        # Aim Vulcan Turret
        if input_manager.is_held(ACTION_UP):
            self.turret_angle_deg = 90.0 if not (input_manager.is_held(ACTION_LEFT) or input_manager.is_held(ACTION_RIGHT)) else 45.0
        elif input_manager.is_held(ACTION_DOWN):
            self.turret_angle_deg = -45.0
        else:
            self.turret_angle_deg = 0.0

        # Slug Out (Down + Jump)
        if input_manager.is_just_pressed(ACTION_JUMP) and input_manager.is_held(ACTION_DOWN):
            self.exit_vehicle()
            return
        # Jump (Button B)
        elif input_manager.is_just_pressed(ACTION_JUMP) and self.physics.is_grounded:
            self.physics.vy = SLUG_JUMP_IMPULSE
            self.physics.is_grounded = False

        # Fire Twin Vulcan Cannons (Button A - Rapid Fire)
        if input_manager.is_held(ACTION_SHOOT) and self.shoot_cooldown == 0:
            self.shoot_cooldown = 5  # Very fast Vulcan rate
            rad = math.radians(self.turret_angle_deg)
            dir_x = math.cos(rad) if self.facing_right else -math.cos(rad)
            dir_y = -math.sin(rad)
            
            # Spawn Vulcan projectiles
            muzzle_x = self.physics.x + (26 if self.facing_right else -26)
            muzzle_y = self.physics.y - 24 + (dir_y * 10)
            projectiles.append(HeavyMachineGunBullet(muzzle_x, muzzle_y, dir_x, dir_y, speed=12.0, damage=1.5))
            if sound_manager:
                sound_manager.play_vulcan_fire()
            if particle_system:
                particle_system.spawn_casing(self.physics.x, self.physics.y - 20, self.facing_right)

        # Fire Heavy Cannon (Button C)
        if input_manager.is_just_pressed(ACTION_GRENADE) and self.cannon_ammo > 0 and self.cannon_cooldown == 0:
            self.cannon_ammo -= 1
            self.cannon_cooldown = 25
            spawn_x = self.physics.x + (30 if self.facing_right else -30)
            spawn_y = self.physics.y - 22
            # Powerful fast explosive grenade shell
            g = Grenade(spawn_x, spawn_y, facing_right=self.facing_right)
            g.vx = 7.0 if self.facing_right else -7.0
            g.vy = -1.5
            projectiles.append(g)

    def update(self, platforms=None, enemies=None, particle_system=None):
        if self.entry_hop_timer > 0:
            self.entry_hop_timer -= 1

        if self.self_destruct_charging:
            self.physics.x += self.physics.vx
            # Check collision with enemies to trigger kamikaze blast
            if enemies:
                for e in enemies:
                    if not e.is_dead and abs(e.physics.x - self.physics.x) < 40:
                        self.is_dead = True
                        if particle_system:
                            particle_system.spawn_explosion(self.physics.x, self.physics.y - 20, size="medium")
                        for hit_e in enemies:
                            if not hit_e.is_dead and abs(hit_e.physics.x - self.physics.x) < 60:
                                hit_e.take_damage(50, death_type="explosion")
                        break
            return

        self.physics.apply_gravity(custom_gravity=GRAVITY * 1.1)
        self.physics.update_movement(platforms)

        # Update Animations
        self.anim_idle.frames = self.idle_frames_r if self.facing_right else self.idle_frames_l
        self.anim_drive.frames = self.drive_frames_r if self.facing_right else self.drive_frames_l

        if abs(self.physics.vx) > 0.1:
            self.anim_drive.update()
        else:
            self.anim_idle.update()

    def draw(self, surface, camera):
        if self.is_dead:
            return

        sx, sy = camera.apply(self.physics.x, self.physics.y)
        
        # Select active sprite
        if not self.physics.is_grounded:
            img = self.jump_frame_r if self.facing_right else self.jump_frame_l
        elif abs(self.physics.vx) > 0.1:
            img = self.anim_drive.get_current_surface()
        else:
            img = self.anim_idle.get_current_surface()

        if img:
            draw_x = sx - (img.get_width() // 2)
            hop_y = 0.0
            if self.entry_hop_timer > 0:
                progress = (12 - self.entry_hop_timer) / 12.0
                hop_y = -math.sin(progress * math.pi) * 6.0
            draw_y = sy - img.get_height() + 4 + int(hop_y)
            surface.blit(img, (draw_x, draw_y))
