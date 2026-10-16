"""
Destructible Environment Entities for Metal Slug 1.
Features:
- DestructibleCrate: Wooden supply boxes that absorb 3 bullet hits, shatter into wood splinter debris, and drop items.
- ExplosiveBarrel: 'DANGER' fuel barrels that explode violently when shot, damaging all enemies in range.
- DestructibleHut: Village stilt huts with damage states, screen shake, and collapse explosions.
"""
import pygame
import random
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.items.pickup import PickupItem

class DestructibleCrate:
    sprite = None

    @classmethod
    def load_sprites(cls):
        if cls.sprite is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Items.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=(255, 255, 255))
            cls.sprite = SpriteLoader.get_subsurface(sheet, 90, 28, 32, 28)
        except Exception as e:
            print(f"[DestructibleCrate] Error loading crate sprite: {e}")

    def __init__(self, x, y, reward_type="BOMB", health=3):
        self.physics = PhysicsBody(x, y, width=28, height=26)
        self.reward_type = reward_type
        self.health = health
        self.max_health = health
        self.is_dead = False
        self.hit_flash_timer = 0
        self.load_sprites()

    @property
    def hitbox(self):
        return self.physics.hurtbox

    def on_collect(self, player, slug=None, sound_manager=None):
        """Claims ammo box immediately upon player contact without requiring shooting."""
        if self.is_dead:
            return
        self.is_dead = True

        # Adds 50 bullets to current weapon ("si tenias 5 balas, te suma 50 mas")
        if player.ammo > 0:
            player.ammo += 50
        elif player.weapon_type == "PISTOL":
            player.weapon_type = "H"
            player.ammo = 50
            player.sync_weapon_visuals()
            if sound_manager:
                sound_manager.play_announcer_weapon("H")
        else:
            player.ammo = 50

        # Tank cannon ammo bonus if inside slug
        if slug:
            if self.reward_type == "GAS":
                slug.repair()
            else:
                slug.cannon_ammo = min(getattr(slug, 'cannon_ammo', 10) + 10, 99)

        # Bomb bonus if crate designated BOMB
        if self.reward_type == "BOMB":
            player.grenades = min(player.grenades + 10, 99)

        player.score += 500

        if sound_manager:
            sound_manager.play_voice("ok")

    def take_damage(self, amount, pickups=None, particle_system=None, sound_manager=None):
        if self.is_dead:
            return
        self.health -= amount
        self.hit_flash_timer = 4

        if self.health <= 0:
            self.is_dead = True
            # Spawn wood debris and drop item
            if particle_system:
                particle_system.spawn_explosion(self.physics.x, self.physics.y - 12, size="small")
            if pickups is not None and self.reward_type:
                item_type = self.reward_type if self.reward_type in ["BOMB", "GAS", "FOOD"] else "AMMO"
                pickups.append(PickupItem(self.physics.x, self.physics.y - 10, item_type=item_type))
            if sound_manager:
                sound_manager.play_sound("grenade", "explosion")

    def update(self, platforms=None):
        if self.is_dead:
            return
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

    def draw(self, surface, camera):
        if self.is_dead or not self.sprite:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        if self.hit_flash_timer > 0:
            # White flash effect
            flash_surf = self.sprite.copy()
            flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(flash_surf, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))
        else:
            surface.blit(self.sprite, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))


class ExplosiveBarrel:
    sprite = None

    @classmethod
    def load_sprites(cls):
        if cls.sprite is not None:
            return
        try:
            path = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Danger Barrel.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=(131, 133, 178))
            cls.sprite = SpriteLoader.get_subsurface(sheet, 86, 12, 25, 30)
        except Exception as e:
            print(f"[ExplosiveBarrel] Error loading barrel sprite: {e}")

    def __init__(self, x, y, health=2, blast_radius=60, damage=25):
        self.physics = PhysicsBody(x, y, width=22, height=28)
        self.health = health
        self.blast_radius = blast_radius
        self.damage = damage
        self.is_dead = False
        self.hit_flash_timer = 0
        self.load_sprites()

    @property
    def hitbox(self):
        return self.physics.hurtbox

    def take_damage(self, amount, enemies=None, particle_system=None, sound_manager=None, camera=None):
        if self.is_dead:
            return
        self.health -= amount
        self.hit_flash_timer = 4

        if self.health <= 0:
            self.is_dead = True
            # Violent detonation
            if particle_system:
                particle_system.spawn_explosion(self.physics.x, self.physics.y - 15, size="medium")
            if camera:
                camera.trigger_shake(duration_frames=14, magnitude=4)
            if sound_manager:
                sound_manager.play_sound("grenade", "explosion")

            # Damage all enemies in blast radius
            if enemies:
                for e in enemies:
                    if not e.is_dead:
                        dist = abs(e.physics.x - self.physics.x)
                        if dist < self.blast_radius:
                            e.take_damage(self.damage, death_type="flame")

    def update(self, platforms=None):
        if self.is_dead:
            return
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

    def draw(self, surface, camera):
        if self.is_dead or not self.sprite:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        if self.hit_flash_timer > 0:
            flash_surf = self.sprite.copy()
            flash_surf.fill((255, 120, 0, 180), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(flash_surf, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))
        else:
            surface.blit(self.sprite, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))


class DestructibleHut:
    """Village wooden stilt hut in Mission 1. Takes bullet hits, shakes, and collapses."""
    def __init__(self, x, y, width=70, height=60, health=28, reward_type="R"):
        self.physics = PhysicsBody(x, y, width=width, height=height)
        self.health = health
        self.max_health = health
        self.reward_type = reward_type
        self.is_dead = False
        self.shake_timer = 0
        self.smoke_timer = 0

    @property
    def hitbox(self):
        return self.physics.hurtbox

    def take_damage(self, amount, pickups=None, particle_system=None, sound_manager=None, camera=None):
        if self.is_dead:
            return
        self.health -= amount
        self.shake_timer = 6

        if self.health <= 0:
            self.is_dead = True
            if particle_system:
                particle_system.spawn_explosion(self.physics.x - 20, self.physics.y - 25, size="medium")
                particle_system.spawn_explosion(self.physics.x + 20, self.physics.y - 15, size="medium")
            if camera:
                camera.trigger_shake(duration_frames=16, magnitude=5)
            if sound_manager:
                sound_manager.play_sound("grenade", "explosion")
            if pickups is not None and self.reward_type:
                pickups.append(PickupItem(self.physics.x, self.physics.y - 15, item_type=self.reward_type))

    def update(self, particle_system=None):
        if self.is_dead:
            return
        if self.shake_timer > 0:
            self.shake_timer -= 1
        # Emit smoke when heavily damaged
        if self.health < self.max_health // 2:
            self.smoke_timer += 1
            if self.smoke_timer % 12 == 0 and particle_system:
                particle_system.spawn_casing(self.physics.x + random.randint(-15, 15), self.physics.y - 35, True)

    def draw(self, surface, camera):
        # Village huts are part of the stage background layer; when active, hit flash and smoke indicate damage
        if self.is_dead:
            return
        if self.shake_timer > 0:
            sx, sy = camera.apply(self.physics.x, self.physics.y)
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-1, 1)
            # Subtle transparent dust puff around the structure
            dust = pygame.Surface((self.physics.width, self.physics.height), pygame.SRCALPHA)
            dust.fill((255, 255, 200, 45))
            surface.blit(dust, (sx - self.physics.width // 2 + shake_x, sy - self.physics.height + shake_y))


class DestructibleRock:
    """Breakable boulder on the wooden stilt bridge (Mission 1 Beach Pier)."""
    sprite = None

    @classmethod
    def load_sprites(cls):
        if cls.sprite is not None:
            return
        try:
            path = "Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 1.png"
            sheet = SpriteLoader.load_sheet(path, colorkey=(255, 255, 255))
            cls.sprite = SpriteLoader.get_subsurface(sheet, 1218, 2, 65, 63)
        except Exception as e:
            print(f"[DestructibleRock] Error loading rock sprite: {e}")

    def __init__(self, x, y, health=4):
        self.physics = PhysicsBody(x, y, width=32, height=26)
        self.health = health
        self.is_dead = False
        self.hit_flash_timer = 0
        self.load_sprites()

    @property
    def hitbox(self):
        return self.physics.hurtbox

    def take_damage(self, amount, pickups=None, particle_system=None, sound_manager=None):
        if self.is_dead:
            return
        self.health -= amount
        self.hit_flash_timer = 4
        if self.health <= 0:
            self.is_dead = True
            if particle_system:
                particle_system.spawn_explosion(self.physics.x, self.physics.y - 10, size="small")
            if pickups is not None:
                pickups.append(PickupItem(self.physics.x, self.physics.y - 8, item_type="FOOD"))

    def update(self, platforms=None):
        if self.is_dead:
            return
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

    def draw(self, surface, camera):
        if self.is_dead or not self.sprite:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        if self.hit_flash_timer > 0:
            flash_surf = self.sprite.copy()
            flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(flash_surf, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))
        else:
            surface.blit(self.sprite, (sx - self.sprite.get_width() // 2, sy - self.sprite.get_height()))


class AmbientPig:
    """Ambient pig walking on the wooden stilt bridge."""
    def __init__(self, x, y):
        self.physics = PhysicsBody(x, y, width=20, height=16)
        self.facing_right = False
        self.is_dead = False
        self.anim_tick = 0
        self.min_x = x - 35.0
        self.max_x = x + 35.0

    @property
    def hitbox(self):
        return self.physics.hurtbox

    def take_damage(self, amount, pickups=None, particle_system=None, sound_manager=None):
        if self.is_dead:
            return
        self.is_dead = True
        if particle_system:
            particle_system.spawn_explosion(self.physics.x, self.physics.y - 8, size="small")
        if pickups is not None:
            pickups.append(PickupItem(self.physics.x, self.physics.y - 8, item_type="FOOD"))

    def update(self, platforms=None):
        if self.is_dead:
            return
        self.anim_tick += 1
        speed = 0.4
        if self.facing_right:
            self.physics.vx = speed
            if self.physics.x >= self.max_x:
                self.facing_right = False
        else:
            self.physics.vx = -speed
            if self.physics.x <= self.min_x:
                self.facing_right = True

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

    def draw(self, surface, camera):
        if self.is_dead:
            return
        sx, sy = camera.apply(self.physics.x, self.physics.y)
        pig_surf = pygame.Surface((22, 16), pygame.SRCALPHA)
        # Pink pig body
        pygame.draw.ellipse(pig_surf, (230, 160, 165), (2, 2, 18, 12))
        # Snout
        snout_x = 17 if self.facing_right else 1
        pygame.draw.ellipse(pig_surf, (240, 130, 140), (snout_x, 6, 5, 5))
        # Animated legs
        leg_off = 2 if (self.anim_tick // 8) % 2 == 0 else -2
        pygame.draw.line(pig_surf, (200, 130, 135), (6, 12), (6 + leg_off, 15), 2)
        pygame.draw.line(pig_surf, (200, 130, 135), (14, 12), (14 - leg_off, 15), 2)
        # Eye
        eye_x = 14 if self.facing_right else 6
        pygame.draw.circle(pig_surf, (40, 20, 20), (eye_x, 5), 1)

        surface.blit(pig_surf, (sx - 11, sy - 16))
