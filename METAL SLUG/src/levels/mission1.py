"""
Mission 1 Level Implementation for Metal Slug 1 (Phases 1-5).
Features:
- 1:1 Stage Background extracted directly from Mission 1.png (4153 x 224 px).
- Walkable ground platforms, wooden docks, and submarine hull.
- P.O.W. Prisoners of war with item drop rewards.
- Rebel Infantry, Shield Soldiers, Di-Cokka Battle Tanks, and Flying Tara bombers.
- SV-001 Metal Slug Tank waiting on the sandbanks.
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
from src.entities.bosses.tetsuyuki import TetsuyukiBoss
from src.items.pickup import PickupItem

from src.entities.destructibles import DestructibleCrate, ExplosiveBarrel, DestructibleHut
from src.core.camera import Camera

class Mission1:
    BACKGROUND_SKY = (172, 193, 194)

    def __init__(self):
        self.stage_width = 4153
        self.stage_height = 224
        self.background_surf = None
        self.platforms = []
        self.enemies = []
        self.pows = []
        self.pickups = []
        self.destructibles = []
        self.slugs = []
        self.boss = None
        self.encounter_lock_x = 1350
        self.boss_arena_x = 3380
        self.is_encounter_cleared = False
        self.is_mission_complete = False
        self._boss_locked = False
        
        self.load_stage()
        self.setup_platforms()
        self.spawn_level_content()

    def load_stage(self):
        """Extracts the 4153x224 level strip and foreground rib arches from Mission 1.png."""
        sheet_path = "Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 1.png"
        raw_sheet = pygame.image.load(sheet_path).convert()
        forest_band = raw_sheet.subsurface((0, 20, 1160, 84))
        sky_color = self.BACKGROUND_SKY
        for y in range(forest_band.get_height()):
            for x in range(forest_band.get_width()):
                if forest_band.get_at((x, y))[:3] == (255, 255, 255):
                    forest_band.set_at((x, y), sky_color)
        forest_tile = pygame.transform.scale(forest_band, (1160, self.stage_height))
        self.background_surf = pygame.Surface((self.stage_width, self.stage_height)).convert()
        for x in range(0, self.stage_width, forest_tile.get_width()):
            self.background_surf.blit(forest_tile, (x, 0))

        stage_strip = raw_sheet.subsurface(
            pygame.Rect(0, 893, self.stage_width, self.stage_height)
        )
        for y in range(self.stage_height):
            for x in range(self.stage_width):
                pixel = stage_strip.get_at((x, y))[:3]
                if pixel != (255, 255, 255):
                    self.background_surf.set_at((x, y), pixel)

        self.foreground_arches = None

    def setup_platforms(self):
        """Constructs walkable collision boundaries matching visual terrain across all 5 zones."""
        self.platforms = [
            # =========================================================================
            # ZONE 1: BEACH (x = 0 .. 565)
            # =========================================================================
            # 1. Starting stone platform (visual floor height y=168)
            Platform(0, 168, 205, 168, semi_solid=False),
            # 2. Sandbag embankment incline slope down to lower steps
            Platform(205, 168, 240, 178, semi_solid=False),
            # 3. Lower stone steps
            Platform(240, 178, 360, 178, semi_solid=False),
            # 4. Wooden dock / pier over beach sand
            Platform(360, 174, 565, 174, semi_solid=True),
            # 5. Beach sand floor beneath pier
            Platform(360, 198, 565, 198, semi_solid=False),

            # =========================================================================
            # ZONE 2: SUBMARINE (x = 565 .. 1350)
            # =========================================================================
            # 6. Continuous beach sandbank around & inside stranded submarine
            Platform(565, 198, 1350, 198, semi_solid=False),
            # 7. Stranded submarine hull top deck (full walkable deck platforms)
            Platform(720, 184, 980, 184, semi_solid=True),

            # =========================================================================
            # ZONE 3: RIVER VILLAGE (x = 1350 .. 2200)
            # =========================================================================
            # 10. Sand dune to river entrance and shallow riverbed
            Platform(1350, 198, 2200, 198, semi_solid=False),
            # 11. Hut 1 (Stone base stilt hut floor)
            Platform(2060, 144, 2135, 144, semi_solid=True),
            # 12. Watchtower 1 (Stilt observation deck)
            Platform(2145, 132, 2195, 132, semi_solid=True),

            # =========================================================================
            # ZONE 4: VALLEY PATH (x = 2200 .. 3300)
            # =========================================================================
            # 13. Shallow riverbed floor continuing through valley
            Platform(2200, 198, 3350, 198, semi_solid=False),
            # 14. Hut 2 (Stilt hut "5" floor)
            Platform(2260, 140, 2340, 140, semi_solid=True),
            # 15. Large Stilt Village House - connecting ramp & walkway
            Platform(2370, 142, 2410, 136, semi_solid=True),
            # 16. Large Stilt Village House - main deck
            Platform(2410, 136, 2530, 136, semi_solid=True),
            # 17. Village Pier / Bridge over water
            Platform(2565, 138, 2665, 138, semi_solid=True),
            # 18. Watchtower 2 (Conical thatched roof tower deck)
            Platform(2700, 132, 2750, 132, semi_solid=True),
            # 19. Ruined Bridge / broken wooden walkway
            Platform(2860, 144, 2960, 144, semi_solid=True),
            # 20. Tall Scaffolding / Watchtower lower platform
            Platform(3100, 144, 3220, 144, semi_solid=True),
            # 21. Tall Scaffolding / Watchtower mid platform
            Platform(3120, 110, 3200, 110, semi_solid=True),

            # =========================================================================
            # ZONE 5: BOSS ARENA (x = 3300 .. 4153)
            # =========================================================================
            # 22. Shallow riverbed arena floor before waterfall
            Platform(3350, 198, 4153, 198, semi_solid=False),
            # 23. Wrecked airplane fuselage - wing incline slope
            Platform(3380, 198, 3540, 142, semi_solid=True),
            # 24. Wrecked airplane fuselage - main cockpit incline slope
            Platform(3540, 142, 3700, 112, semi_solid=True),
            # 25. Waterfall rock ledge (Tetsuyuki upper perch)
            Platform(3700, 112, 3850, 112, semi_solid=True),
        ]

    def spawn_level_content(self):
        """Places rebel infantry, vehicles, aircraft, POWs, destructibles, and boss."""
        from src.entities.destructibles import DestructibleRock, AmbientPig
        from src.entities.vehicles.r_shobu import RShobuHelicopter

        # SV-001 Metal Slug Tank
        self.slugs = [
            MetalSlug(x=720, y=198)
        ]

        # R-Shobu Attack Helicopter Mini-Boss
        self.helicopter = RShobuHelicopter(1550, 45)
        self._heli_locked = False
        
        # Prisoners of War (P.O.W.) - Exact video sequence (6 total)
        self.pows = [
            PrisonerOfWar(460, 180, reward_type="H"),     # Pier / dock -> Heavy Machine Gun
            PrisonerOfWar(880, 184, reward_type="S", pow_type="post"),     # Submarine top deck -> Shotgun tied to wooden post
            PrisonerOfWar(1320, 198, reward_type="FOOD"), # Sandbanks past sub -> Roast chicken (Food)
            PrisonerOfWar(1650, 198, reward_type="R"),    # River stilt village -> Rocket Launcher
            PrisonerOfWar(2050, 198, reward_type="F"),    # River crossing -> Flame Shot
            PrisonerOfWar(3250, 198, reward_type="BOMB"), # Pre-boss waterfall -> Bomb supply
        ]
        
        # Destructible wooden supply crates, explosive barrels, boulders, pigs and stilt huts
        self.destructibles = [
            # Beach pier crate, rock, and pig
            DestructibleCrate(240, 178, reward_type="BOMB"),
            DestructibleCrate(440, 174, reward_type="H"),
            DestructibleRock(480, 174),
            AmbientPig(520, 174),
            # Submarine area barrels & crate
            ExplosiveBarrel(1250, 198),
            DestructibleCrate(1280, 198, reward_type="GAS"),
            # Village stilt huts, barrels & crates
            DestructibleHut(2095, 198, width=75, height=60, health=28, reward_type="R"),
            ExplosiveBarrel(1820, 198),
            DestructibleCrate(1850, 198, reward_type="BOMB"),
            DestructibleHut(2300, 198, width=80, height=60, health=28, reward_type="F"),
            # Pre-boss cliff crate
            DestructibleCrate(3050, 198, reward_type="H"),
        ]

        # Stage 1 Enemy Squad Formations matching video progression
        self.enemies = [
            # 1. Beach encounter (x=200..550)
            RebelSoldier(220, 168, facing_right=False),
            RebelSoldier(330, 178, facing_right=False),
            RebelSoldier(440, 180, facing_right=False),
            RebelSoldier(520, 180, facing_right=False),
            
            # 2. Stranded Submarine & Sandbank (x=600..1300)
            ShieldSoldier(640, 198, facing_right=False),
            RebelSoldier(780, 198, facing_right=False),
            RebelSoldier(850, 184, facing_right=False), # On top of submarine
            ShieldSoldier(1050, 198, facing_right=False),
            FlyingTara(1100, y=48, speed=2.2),
            DiCokkaTank(1220, 198, facing_right=False),
            
            # 3. Helicopter Encounter (x=1350..1650)
            self.helicopter,

            # 4. River & Village Encounter (x=1650..2200)
            FlyingTara(1750, y=42, speed=2.4),
            RebelSoldier(1700, 198, facing_right=False),
            DiCokkaTank(1850, 198, facing_right=False),
            RebelSoldier(1980, 198, facing_right=False),
            FlyingTara(2100, y=44, speed=2.3),
            RebelSoldier(2200, 198, facing_right=False),
            
            # 5. Valley & Waterfall Approach (x=2300..3400)
            ShieldSoldier(2400, 198, facing_right=False),
            RebelSoldier(2550, 198, facing_right=False),
            RebelSoldier(2750, 198, facing_right=False),
            FlyingTara(2850, y=40, speed=2.5),
            RebelSoldier(3000, 198, facing_right=False),
            ShieldSoldier(3150, 198, facing_right=False),
            RebelSoldier(3300, 198, facing_right=False),
        ]

        # Stage 1 Boss: Tetsuyuki (Wedged in the waterfall at stage end)
        self.boss = TetsuyukiBoss(x=3680, y=198)

    def update(self, player_or_cam, cam_or_player, projectiles=None, particle_system=None, enemy_projectiles=None, sound_manager=None):
        if isinstance(player_or_cam, Camera):
            camera = player_or_cam
            player = cam_or_player
        else:
            player = player_or_cam
            camera = cam_or_player

        # Update destructibles
        active_slug = None
        for s in self.slugs:
            if s.is_occupied:
                active_slug = s
                break
        collector_box = active_slug.physics.hurtbox if active_slug else player.physics.hurtbox

        for d in self.destructibles:
            if isinstance(d, DestructibleHut):
                d.update(particle_system)
            elif isinstance(d, DestructibleCrate):
                d.update(self.platforms)
                if not d.is_dead and d.hitbox.colliderect(collector_box):
                    d.on_collect(player, slug=active_slug, sound_manager=sound_manager)
            else:
                d.update(self.platforms)
        self.destructibles = [d for d in self.destructibles if not d.is_dead]

        # Update enemies
        for e in self.enemies:
            if e == self.helicopter:
                e.update_ai(player, self.platforms, enemy_projectiles, particle_system)
            else:
                e.update_ai(player, self.platforms, enemy_projectiles)
        self.enemies = [e for e in self.enemies if not (e.is_dead and getattr(e, 'death_timer', 0) <= 0)]
            
        # Helicopter Camera Lock Encounter
        if self.helicopter and not self.helicopter.is_dead and player.physics.x >= 1350:
            self._heli_locked = True
            camera.lock_at(1350)
            camera.x = 1350
        elif self._heli_locked and (not self.helicopter or self.helicopter.is_dead):
            self._heli_locked = False
            camera.unlock()

        # Update P.O.W.s
        for pow_npc in self.pows:
            pow_npc.update(player, self.platforms, self.pickups, sound_manager=sound_manager, camera=camera)
        self.pows = [p for p in self.pows if not p.is_dead]
            
        # Update pickups
        for p in self.pickups:
            p.update(self.platforms)
            if not p.is_dead and p.hitbox.colliderect(player.physics.hurtbox):
                slug = self.slugs[0] if self.slugs else None
                p.on_collect(player, slug)
        self.pickups = [p for p in self.pickups if not p.is_dead]

        # Update Slugs
        for s in self.slugs:
            s.update(self.platforms, self.enemies, particle_system)
            
        # Update Boss if active
        if self.boss:
            self.boss.update(player, self.platforms, enemy_projectiles, particle_system, camera)
            if self.boss.is_defeated and self.boss.defeat_timer <= 0:
                self.is_mission_complete = True
            
        # Camera Lock: Permanent latch for Boss Arena until boss is defeated
        if (player.physics.x >= self.boss_arena_x - 120 or self._boss_locked) and self.boss and not self.boss.is_defeated:
            self._boss_locked = True
            camera.lock_at(self.boss_arena_x - 120)
            camera.x = self.boss_arena_x - 120
            self.is_encounter_cleared = False
        elif self.boss and self.boss.is_defeated:
            self._boss_locked = False
            camera.unlock()
            self.is_encounter_cleared = True

    def draw_background(self, surface, camera):
        if self.background_surf:
            surface.fill(self.BACKGROUND_SKY)
            cam_x = int(camera.x)
            vis_w = min(VIRTUAL_WIDTH, self.stage_width - cam_x)
            if vis_w > 0:
                sub = self.background_surf.subsurface((cam_x, 0, vis_w, VIRTUAL_HEIGHT))
                surface.blit(sub, (camera.shake_offset_x, camera.shake_offset_y))

    def draw_entities(self, surface, camera):
        # Draw Boss behind foreground entities
        if self.boss:
            self.boss.draw(surface, camera)
            
        for s in self.slugs:
            s.draw(surface, camera)
        for d in self.destructibles:
            d.draw(surface, camera)
        for pow_npc in self.pows:
            pow_npc.draw(surface, camera)
        for p in self.pickups:
            p.draw(surface, camera)

    def draw_foreground(self, surface, camera):
        """Foreground overlay hook."""
        pass


# Alias for backward-compatibility with test suites
Mission1Level = Mission1


# Alias for backward-compatibility with test suites
Mission1Level = Mission1
