"""
Mission 5 Level Implementation for Metal Slug 1.
Features:
- City Ruins & Industrial Zone background (4304 x 224 px).
- Intense infantry waves, heavy tanks, and fortified barriers.
- SV-001 Metal Slug Tank.
- Boss: Iron Nokana armored assault fortress.
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
from src.entities.bosses.iron_nokana import IronNokanaBoss
from src.items.pickup import PickupItem

class Mission5:
    def __init__(self):
        self.stage_width = 4304
        self.stage_height = 224
        self.background_surf = None
        self.platforms = []
        self.enemies = []
        self.pows = []
        self.pickups = []
        self.slugs = []
        self.boss = None
        self.encounter_lock_x = 1900
        self.boss_arena_x = 3800
        self.is_encounter_cleared = False
        self.is_mission_complete = False
        
        self.load_stage()
        self.setup_platforms()
        self.spawn_level_content()

    def load_stage(self):
        sheet_path = "Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 5.png"
        raw_sheet = SpriteLoader.load_sheet(sheet_path, colorkey=None)
        rect = pygame.Rect(0, 0, self.stage_width, self.stage_height)
        self.background_surf = raw_sheet.subsurface(rect).copy()

    def setup_platforms(self):
        self.platforms = [
            Platform(0, 184, 4304, 184, semi_solid=False),
            Platform(800, 140, 1300, 140, semi_solid=True),
            Platform(2300, 135, 2900, 135, semi_solid=True),
        ]

    def spawn_level_content(self):
        self.slugs = [
            MetalSlug(x=900, y=184)
        ]
        self.pows = [
            PrisonerOfWar(450, 184, reward_type="H"),
            PrisonerOfWar(1150, 140, reward_type="S"),
            PrisonerOfWar(2100, 184, reward_type="F"),
            PrisonerOfWar(2700, 135, reward_type="FOOD"),
        ]
        self.pickups = [
            PickupItem(300, 170, item_type="H"),
            PickupItem(1500, 170, item_type="GAS"),
            PickupItem(2500, 170, item_type="BOMB"),
        ]
        self.enemies = [
            RebelSoldier(400, 184, facing_right=False),
            ShieldSoldier(650, 184, facing_right=False),
            DiCokkaTank(1200, 184, facing_right=False),
            FlyingTara(1450, y=45, speed=2.4),
            ShieldSoldier(1800, 184, facing_right=False),
            RebelSoldier(2200, 184, facing_right=False),
            DiCokkaTank(2800, 184, facing_right=False),
            FlyingTara(3200, y=45, speed=2.6),
        ]
        self.boss = IronNokanaBoss(x=3950, y=184)

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
