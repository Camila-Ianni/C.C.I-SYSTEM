"""
Mission 3 Level Implementation for Metal Slug 1.
Features:
- Snowy mountain railroad valley background (2412 x 224 px).
- Rebel Infantry, Di-Cokka Tanks, and Aerial Bombers.
- SV-001 Metal Slug Tank support.
- Boss: Tani Oh locomotive siege howitzer.
"""
import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT
from src.engine.physics import Platform
from src.engine.sprite_loader import SpriteLoader
from src.entities.enemy import RebelSoldier
from src.entities.enemies.shield_soldier import ShieldSoldier
from src.entities.vehicles.dicokka import DiCokkaTank
from src.entities.vehicles.flying_tara import FlyingTara
from src.entities.slug import MetalSlug
from src.entities.pow import PrisonerOfWar
from src.entities.bosses.tani_oh import TaniOhBoss
from src.items.pickup import PickupItem

class Mission3:
    def __init__(self):
        self.stage_width = 2412
        self.stage_height = 224
        self.background_surf = None
        self.platforms = []
        self.enemies = []
        self.pows = []
        self.pickups = []
        self.slugs = []
        self.boss = None
        self.encounter_lock_x = 1000
        self.boss_arena_x = 2000
        self.is_encounter_cleared = False
        self.is_mission_complete = False
        
        self.load_stage()
        self.setup_platforms()
        self.spawn_level_content()

    def load_stage(self):
        sheet_path = "Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 3.png"
        raw_sheet = SpriteLoader.load_sheet(sheet_path, colorkey=None)
        rect = pygame.Rect(0, 29, self.stage_width, self.stage_height)
        self.background_surf = raw_sheet.subsurface(rect).copy()

    def setup_platforms(self):
        self.platforms = [
            Platform(0, 184, 2412, 184, semi_solid=False),
            Platform(450, 140, 750, 140, semi_solid=True),
        ]

    def spawn_level_content(self):
        self.slugs = [
            MetalSlug(x=550, y=184)
        ]
        self.pows = [
            PrisonerOfWar(350, 184, reward_type="R"),
            PrisonerOfWar(700, 140, reward_type="H"),
            PrisonerOfWar(1400, 184, reward_type="FOOD"),
        ]
        self.pickups = [
            PickupItem(250, 170, item_type="H"),
            PickupItem(850, 170, item_type="GAS"),
            PickupItem(1200, 170, item_type="BOMB"),
        ]
        self.enemies = [
            RebelSoldier(300, 184, facing_right=False),
            ShieldSoldier(500, 184, facing_right=False),
            DiCokkaTank(900, 184, facing_right=False),
            FlyingTara(1100, y=42, speed=2.3),
            ShieldSoldier(1350, 184, facing_right=False),
            RebelSoldier(1550, 184, facing_right=False),
        ]
        self.boss = TaniOhBoss(x=2050, y=184)

    def update(self, player, camera, projectiles=None, particle_system=None, enemy_projectiles=None):
        for e in self.enemies:
            e.update_ai(player, self.platforms, enemy_projectiles)
        for pow_npc in self.pows:
            pow_npc.update(player, self.platforms, self.pickups)
        self.pows = [p for p in self.pows if not p.is_dead]
        for p in self.pickups:
            p.update(self.platforms)
            if not p.is_dead and p.hitbox.colliderect(player.physics.hurtbox):
                slug = self.slugs[0] if self.slugs else None
                p.on_collect(player, slug)
        self.pickups = [p for p in self.pickups if not p.is_dead]
        for s in self.slugs:
            s.update(self.platforms, self.enemies, particle_system)
        if self.boss:
            self.boss.update(player, self.platforms, enemy_projectiles, particle_system, camera)
            if self.boss.is_defeated and self.boss.defeat_timer <= 0:
                self.is_mission_complete = True
        
        # Camera Lock: Only lock at final Stage Boss Arena
        if player.physics.x >= self.boss_arena_x - 120 and self.boss and not self.is_mission_complete:
            camera.lock_at(self.boss_arena_x - 120)
            self.is_encounter_cleared = False
        else:
            camera.unlock()
            self.is_encounter_cleared = True

    def draw_background(self, surface, camera):
        if self.background_surf:
            cam_x = int(camera.x)
            vis_w = min(VIRTUAL_WIDTH, self.stage_width - cam_x)
            if vis_w > 0:
                sub = self.background_surf.subsurface((cam_x, 0, vis_w, VIRTUAL_HEIGHT))
                surface.blit(sub, (camera.shake_offset_x, camera.shake_offset_y))

    def draw_entities(self, surface, camera):
        if self.boss:
            self.boss.draw(surface, camera)
        for s in self.slugs:
            s.draw(surface, camera)
        for pow_npc in self.pows:
            pow_npc.draw(surface, camera)
        for p in self.pickups:
            p.draw(surface, camera)
