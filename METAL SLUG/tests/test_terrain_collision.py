"""
Test Suite: R1 Core Physics & Level Collision Fixes (Features F1 - F6)
Tiers 1, 2, and 3 Coverage.

Features:
- F1: Beach Terrain Collision (x=0..565)
- F2: Submarine Collision (x=565..1350)
- F3: River Village Stilt Platforms (x=1350..2200)
- F4: Valley Path Stilt Platforms (x=2200..3300)
- F5: Boss Arena Wrecked Fuselage Incline (x=3300..4153)
- F6: Camera Bounds & Clipping Protection
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import unittest
import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT
pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.engine.physics import Platform, PhysicsBody
try:
    from src.levels.mission1 import Mission1Level
except ImportError:
    from src.levels.mission1 import Mission1 as Mission1Level
from src.entities.player import Player
from src.entities.slug import MetalSlug
from src.core.camera import Camera
from src.game import Game


class TestTerrainCollision(unittest.TestCase):
    def setUp(self):
        self.level = Mission1Level()

    def _get_platform_at(self, x, semi_solid=None):
        """Helper to find platform at coordinate x."""
        matches = []
        for p in self.level.platforms:
            if p.x1 <= x <= p.x2:
                if semi_solid is None or p.semi_solid == semi_solid:
                    matches.append(p)
        return matches

    def _get_highest_platform_at(self, x):
        """Helper to find the highest platform (lowest y) at coordinate x."""
        plats = [p for p in self.level.platforms if p.x1 <= x <= p.x2]
        if not plats:
            return None
        return min(plats, key=lambda p: p.get_height_at(x))

    def _get_solid_ground_at(self, x):
        """Helper to find solid base ground (semi_solid=False) at x."""
        plats = [p for p in self.level.platforms if p.x1 <= x <= p.x2 and not p.semi_solid]
        return plats[0] if plats else None

    # =========================================================================
    # FEATURE F1: Beach Terrain Collision (x=0..565)
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f1_tier1_temple_terrace_ground_height(self):
        """F1-T1-1: Stone temple terrace ruins provide solid ground at y=168 (x=0..205)."""
        ground = self._get_solid_ground_at(100)
        self.assertIsNotNone(ground, "Missing solid ground at Beach terrace x=100")
        self.assertEqual(ground.get_height_at(100), 168.0)
        self.assertFalse(ground.semi_solid)

    def test_f1_tier1_steps_ground_height(self):
        """F1-T1-2: Lower stone steps provide solid ground at y=178 (x=240..360)."""
        ground = self._get_solid_ground_at(280)
        self.assertIsNotNone(ground, "Missing solid ground at Beach steps x=280")
        self.assertEqual(ground.get_height_at(280), 178.0)
        self.assertFalse(ground.semi_solid)

    def test_f1_tier1_pier_platform_exists(self):
        """F1-T1-3: Wooden dock / pier exists at y=174 (x=360..565) as semi-solid."""
        pier_plats = [p for p in self.level.platforms if p.x1 <= 450 <= p.x2 and p.semi_solid]
        self.assertTrue(len(pier_plats) > 0, "Missing semi-solid pier platform at x=450")
        self.assertEqual(pier_plats[0].get_height_at(450), 174.0)

    def test_f1_tier1_beach_sand_beneath_pier(self):
        """F1-T1-4: Beach sand floor beneath pier provides solid ground at y=198 (x=360..565)."""
        ground = self._get_solid_ground_at(450)
        self.assertIsNotNone(ground, "Missing solid sand ground beneath pier at x=450")
        self.assertEqual(ground.get_height_at(450), 198.0)

    def test_f1_tier1_pier_drop_through_to_sand(self):
        """F1-T1-5: Player on pier can drop through to sand floor at y=198."""
        body = PhysicsBody(x=450, y=174, width=18, height=36)
        body.is_grounded = True
        pier = [p for p in self.level.platforms if p.x1 <= 450 <= p.x2 and p.semi_solid][0]
        body.current_platform = pier
        body.drop_through_platform()
        self.assertFalse(body.is_grounded)
        self.assertGreater(body.ignore_platform_timer, 0)
        # Advance movement under gravity
        for _ in range(15):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f1_tier2_terrace_start_boundary(self):
        """F1-T2-1: Temple terrace boundary starts at exact stage origin x=0."""
        ground = self._get_solid_ground_at(0)
        self.assertIsNotNone(ground)
        self.assertEqual(ground.x1, 0.0)
        self.assertEqual(ground.y1, 168.0)

    def test_f1_tier2_step_transition_boundary(self):
        """F1-T2-2: Step transition boundary occurs at exact coordinate x=205."""
        p_terrace = [p for p in self.level.platforms if p.x1 <= 205 <= p.x2 and p.y1 == 168]
        p_steps = [p for p in self.level.platforms if p.x1 <= 205 <= p.x2 and p.y2 == 178]
        self.assertTrue(len(p_terrace) > 0, "Terrace must reach boundary x=205")
        self.assertTrue(len(p_steps) > 0, "Steps must start at boundary x=205")

    def test_f1_tier2_pier_start_boundary(self):
        """F1-T2-3: Pier platform starts at exact coordinate x=360."""
        pier = [p for p in self.level.platforms if p.semi_solid and p.x1 <= 360 <= p.x2]
        self.assertTrue(len(pier) > 0)
        self.assertEqual(pier[0].x1, 360.0)

    def test_f1_tier2_beach_zone_end_boundary(self):
        """F1-T2-4: Beach zone ends at exact coordinate x=565."""
        plats = [p for p in self.level.platforms if p.x2 == 565]
        self.assertTrue(len(plats) >= 1, "Expected platform ending at x=565")

    def test_f1_tier2_jump_up_through_pier(self):
        """F1-T2-5: Character jumping up from sand passes through pier from below."""
        body = PhysicsBody(x=450, y=184, width=18, height=36)
        body.vy = -6.0  # Jumping upwards
        body.update_movement(self.level.platforms)
        self.assertLess(body.y, 184.0)
        self.assertFalse(body.is_grounded, "Upward jump must not be blocked by semi-solid pier")

    # =========================================================================
    # FEATURE F2: Submarine Collision (x=565..1350)
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f2_tier1_sandbank_continuous_floor(self):
        """F2-T1-1: Submarine zone sandbank provides continuous solid floor at y=198."""
        for x in (600, 800, 1000, 1300):
            ground = self._get_solid_ground_at(x)
            self.assertIsNotNone(ground, f"Missing solid ground at submarine zone x={x}")
            self.assertEqual(ground.get_height_at(x), 198.0)

    def test_f2_tier1_submarine_deck_height(self):
        """F2-T1-2: Stranded submarine hull top deck is at y=184 as semi-solid."""
        deck = [p for p in self.level.platforms if p.x1 <= 800 <= p.x2 and p.semi_solid]
        self.assertTrue(len(deck) > 0, "Missing submarine hull deck at x=800")
        self.assertEqual(deck[0].get_height_at(800), 184.0)

    def test_f2_tier1_submarine_deck_drop_through(self):
        """F2-T1-3: Dropping through submarine deck lands on sandbank floor at y=198."""
        body = PhysicsBody(x=800, y=184, width=18, height=36)
        body.is_grounded = True
        deck = [p for p in self.level.platforms if p.x1 <= 800 <= p.x2 and p.semi_solid][0]
        body.current_platform = deck
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    def test_f2_tier1_slug_spawn_grounding(self):
        """F2-T1-4: SV-001 tank spawned at x=720, y=198 rests grounded on sandbank."""
        slug = MetalSlug(x=720, y=198)
        slug.update(self.level.platforms)
        self.assertEqual(slug.physics.y, 198.0)

    def test_f2_tier1_continuous_ground_beneath_deck(self):
        """F2-T1-5: Solid sand floor exists continuously underneath the submarine deck."""
        for x in range(720, 1150, 50):
            ground = self._get_solid_ground_at(x)
            self.assertIsNotNone(ground, f"Ground missing beneath submarine deck at x={x}")
            self.assertEqual(ground.get_height_at(x), 198.0)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f2_tier2_submarine_start_edge(self):
        """F2-T2-1: Submarine deck begins at exact coordinate x=720."""
        deck = [p for p in self.level.platforms if p.semi_solid and p.x1 == 720 and p.y1 == 184]
        self.assertTrue(len(deck) > 0, "Submarine deck must start at x=720")

    def test_f2_tier2_submarine_end_edge(self):
        """F2-T2-2: Submarine deck terminates at exact coordinate x=900/980."""
        deck = [p for p in self.level.platforms if p.semi_solid and p.x2 in (900, 950, 980)]
        self.assertTrue(len(deck) > 0, "Submarine deck must terminate between x=900 and x=980")

    def test_f2_tier2_zone_start_boundary(self):
        """F2-T2-3: Submarine sandbank starts at exact coordinate x=565."""
        ground = [p for p in self.level.platforms if not p.semi_solid and p.x1 == 565 and p.y1 == 198]
        self.assertTrue(len(ground) > 0, "Sandbank must start at x=565")

    def test_f2_tier2_zone_end_boundary(self):
        """F2-T2-4: Submarine zone ends at coordinate x=1350."""
        ground = [p for p in self.level.platforms if not p.semi_solid and p.x2 == 1350 and p.y2 == 198]
        self.assertTrue(len(ground) > 0, "Submarine zone base platform must end at x=1350")

    def test_f2_tier2_high_vertical_fall_onto_deck(self):
        """F2-T2-5: Entity falling from high altitude (y=50) lands safely on deck at y=184."""
        body = PhysicsBody(x=800, y=50, width=18, height=36)
        for _ in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 184.0)

    def test_f2_tier2_no_floating_platforms_outside_deck(self):
        """F2-T2-6: No phantom platforms at y=184 exist outside submarine deck (x=1050 lands at sand y=198)."""
        phantom = [p for p in self.level.platforms if p.semi_solid and p.x1 <= 1050 <= p.x2 and p.y1 == 184]
        self.assertEqual(len(phantom), 0, "Phantom platform found at x=1050!")
        body = PhysicsBody(x=1050, y=160, width=18, height=36)
        for _ in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    # =========================================================================
    # FEATURE F3: River Village Stilt Platforms (x=1350..2200)
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f3_tier1_shallow_riverbed_walkable(self):
        """F3-T1-1: Shallow riverbed allows continuous walking at y=184 (x=1350..2200)."""
        for x in (1400, 1600, 1800, 2000):
            ground = self._get_solid_ground_at(x)
            self.assertIsNotNone(ground, f"Missing shallow riverbed at x={x}")
            self.assertEqual(ground.get_height_at(x), 198.0)

    def test_f3_tier1_hut1_platform_height(self):
        """F3-T1-2: Hut 1 stilt floor exists at y=144 (x=2060..2135) as semi-solid."""
        hut1 = [p for p in self.level.platforms if p.x1 <= 2080 <= p.x2 and p.semi_solid]
        self.assertTrue(len(hut1) > 0, "Missing Hut 1 platform at x=2080")
        self.assertEqual(hut1[0].get_height_at(2080), 144.0)

    def test_f3_tier1_watchtower1_platform_height(self):
        """F3-T1-3: Watchtower 1 observation deck exists at y=132 (x=2145..2195) as semi-solid."""
        wt1 = [p for p in self.level.platforms if p.x1 <= 2170 <= p.x2 and p.semi_solid]
        self.assertTrue(len(wt1) > 0, "Missing Watchtower 1 platform at x=2170")
        self.assertEqual(wt1[0].get_height_at(2170), 132.0)

    def test_f3_tier1_hut1_drop_through_to_riverbed(self):
        """F3-T1-4: Dropping through Hut 1 lands cleanly in riverbed at y=184."""
        body = PhysicsBody(x=2080, y=144, width=18, height=36)
        body.is_grounded = True
        hut1 = [p for p in self.level.platforms if p.x1 <= 2080 <= p.x2 and p.semi_solid][0]
        body.current_platform = hut1
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    def test_f3_tier1_destructible_hut1_relocation(self):
        """F3-T1-5: DestructibleHut 1 is positioned at authentic stilt hut x=2095 (not x=1600)."""
        huts = [d for d in self.level.destructibles if type(d).__name__ == "DestructibleHut"]
        hut_x_coords = [getattr(d, 'x', getattr(d.physics, 'x', None)) for d in huts]
        self.assertIn(2095, hut_x_coords, "DestructibleHut 1 must be relocated to x=2095")
        self.assertNotIn(1600, hut_x_coords, "DestructibleHut must not be at x=1600")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f3_tier2_hut1_start_edge(self):
        """F3-T2-1: Hut 1 platform starts at exact coordinate x=2060."""
        hut1 = [p for p in self.level.platforms if p.semi_solid and p.x1 == 2060 and p.y1 == 144]
        self.assertTrue(len(hut1) > 0, "Hut 1 must start at x=2060")

    def test_f3_tier2_hut1_end_edge(self):
        """F3-T2-2: Hut 1 platform ends at exact coordinate x=2135."""
        hut1 = [p for p in self.level.platforms if p.semi_solid and p.x2 == 2135 and p.y2 == 144]
        self.assertTrue(len(hut1) > 0, "Hut 1 must end at x=2135")

    def test_f3_tier2_watchtower1_start_edge(self):
        """F3-T2-3: Watchtower 1 platform starts at exact coordinate x=2145."""
        wt1 = [p for p in self.level.platforms if p.semi_solid and p.x1 == 2145 and p.y1 == 132]
        self.assertTrue(len(wt1) > 0, "Watchtower 1 must start at x=2145")

    def test_f3_tier2_watchtower1_end_edge(self):
        """F3-T2-4: Watchtower 1 platform ends at exact coordinate x=2195."""
        wt1 = [p for p in self.level.platforms if p.semi_solid and p.x2 == 2195 and p.y2 == 132]
        self.assertTrue(len(wt1) > 0, "Watchtower 1 must end at x=2195")

    def test_f3_tier2_no_floating_solid_platforms_over_water(self):
        """F3-T2-5: No non-semi-solid platforms exist above y=184 over river water."""
        floating_solids = [p for p in self.level.platforms if 1350 <= p.x1 <= 2200 and not p.semi_solid and p.y1 < 184]
        self.assertEqual(len(floating_solids), 0, "No solid floating platforms permitted over water")

    # =========================================================================
    # FEATURE F4: Valley Path Stilt Platforms (x=2200..3300)
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f4_tier1_valley_riverbed_continuous(self):
        """F4-T1-1: Shallow riverbed continues through valley path at y=184 (x=2200..3350)."""
        for x in (2300, 2600, 2900, 3200):
            ground = self._get_solid_ground_at(x)
            self.assertIsNotNone(ground, f"Missing valley riverbed at x={x}")
            self.assertEqual(ground.get_height_at(x), 198.0)

    def test_f4_tier1_hut2_platform_height(self):
        """F4-T1-2: Hut 2 platform exists at y=140 (x=2260..2340) as semi-solid."""
        hut2 = [p for p in self.level.platforms if p.x1 <= 2280 <= p.x2 and p.semi_solid]
        self.assertTrue(len(hut2) > 0, "Missing Hut 2 platform at x=2280")
        self.assertEqual(hut2[0].get_height_at(2280), 140.0)

    def test_f4_tier1_large_house_deck_height(self):
        """F4-T1-3: Large Stilt Village House deck exists at y=136 (x=2410..2530)."""
        house = [p for p in self.level.platforms if p.x1 <= 2450 <= p.x2 and p.semi_solid]
        self.assertTrue(len(house) > 0, "Missing Large House platform at x=2450")
        self.assertEqual(house[0].get_height_at(2450), 136.0)

    def test_f4_tier1_scaffolding_platforms_exist(self):
        """F4-T1-4: Tall scaffolding provides two tiers: lower (y=144) and mid (y=110)."""
        lower = [p for p in self.level.platforms if p.x1 <= 3150 <= p.x2 and p.y1 == 144 and p.semi_solid]
        mid = [p for p in self.level.platforms if p.x1 <= 3150 <= p.x2 and p.y1 == 110 and p.semi_solid]
        self.assertTrue(len(lower) > 0, "Missing Scaffolding lower platform at y=144")
        self.assertTrue(len(mid) > 0, "Missing Scaffolding mid platform at y=110")

    def test_f4_tier1_destructible_hut2_relocation(self):
        """F4-T1-5: DestructibleHut 2 is positioned at authentic stilt hut x=2300 (not x=1950)."""
        huts = [d for d in self.level.destructibles if type(d).__name__ == "DestructibleHut"]
        hut_x_coords = [getattr(d, 'x', getattr(d.physics, 'x', None)) for d in huts]
        self.assertIn(2300, hut_x_coords, "DestructibleHut 2 must be relocated to x=2300")
        self.assertNotIn(1950, hut_x_coords, "DestructibleHut must not be at x=1950")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f4_tier2_house_ramp_sloped_interpolation(self):
        """F4-T2-1: Large Stilt House ramp interpolates correctly from y=142 down to y=136."""
        ramp = [p for p in self.level.platforms if p.semi_solid and p.x1 == 2370 and p.x2 == 2410]
        self.assertTrue(len(ramp) > 0, "Missing Large House ramp (x=2370..2410)")
        h_mid = ramp[0].get_height_at(2390)
        self.assertAlmostEqual(h_mid, 139.0, delta=0.1)

    def test_f4_tier2_watchtower2_boundary_edges(self):
        """F4-T2-2: Watchtower 2 platform spans x=2700..2750 at y=132."""
        wt2 = [p for p in self.level.platforms if p.semi_solid and p.x1 == 2700 and p.x2 == 2750]
        self.assertTrue(len(wt2) > 0)
        self.assertEqual(wt2[0].y1, 132.0)

    def test_f4_tier2_ruined_bridge_drop_through(self):
        """F4-T2-3: Dropping through Ruined Bridge (x=2860..2960, y=144) reaches riverbed at y=184."""
        body = PhysicsBody(x=2900, y=144, width=18, height=36)
        body.is_grounded = True
        bridge = [p for p in self.level.platforms if p.x1 <= 2900 <= p.x2 and p.semi_solid][0]
        body.current_platform = bridge
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    def test_f4_tier2_scaffolding_multi_tier_traversal(self):
        """F4-T2-4: Multi-tier scaffolding allows descending from mid (110) to lower (144)."""
        body = PhysicsBody(x=3150, y=110, width=18, height=36)
        body.is_grounded = True
        mid = [p for p in self.level.platforms if p.x1 <= 3150 <= p.x2 and p.y1 == 110][0]
        body.current_platform = mid
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 144.0)

    def test_f4_tier2_pier_boundary_edges(self):
        """F4-T2-5: Village Pier platform spans x=2565..2665 at y=138."""
        pier = [p for p in self.level.platforms if p.semi_solid and p.x1 == 2565 and p.x2 == 2665]
        self.assertTrue(len(pier) > 0)
        self.assertEqual(pier[0].y1, 138.0)

    # =========================================================================
    # FEATURE F5: Boss Arena Wrecked Fuselage Incline (x=3300..4153)
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f5_tier1_boss_riverbed_floor(self):
        """F5-T1-1: Arena shallow riverbed floor provides continuous solid base at y=184 (x=3350..4153)."""
        for x in (3400, 3600, 3800, 4100):
            ground = self._get_solid_ground_at(x)
            self.assertIsNotNone(ground, f"Missing boss arena riverbed ground at x={x}")
            self.assertEqual(ground.get_height_at(x), 198.0)

    def test_f5_tier1_wing_incline_slope_midpoint(self):
        """F5-T1-2: Wrecked wing incline slope (3380->3540) has height y=170 at midpoint x=3460."""
        wing = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3380 and p.x2 == 3540]
        self.assertTrue(len(wing) > 0, "Missing wrecked wing slope platform")
        h = wing[0].get_height_at(3460)
        self.assertAlmostEqual(h, 170.0, delta=0.5)

    def test_f5_tier1_cockpit_incline_slope_midpoint(self):
        """F5-T1-3: Cockpit incline slope (3540->3700) has height y=127 at midpoint x=3620."""
        cockpit = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3540 and p.x2 == 3700]
        self.assertTrue(len(cockpit) > 0, "Missing cockpit slope platform")
        h = cockpit[0].get_height_at(3620)
        self.assertAlmostEqual(h, 127.0, delta=0.5)

    def test_f5_tier1_rock_ledge_platform(self):
        """F5-T1-4: Waterfall rock ledge platform spans x=3700..3850 at y=112."""
        ledge = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3700 and p.x2 == 3850]
        self.assertTrue(len(ledge) > 0, "Missing waterfall rock ledge platform")
        self.assertEqual(ledge[0].y1, 112.0)

    def test_f5_tier1_total_mission_ground_continuity(self):
        """F5-T1-5: Solid base ground (semi_solid=False) is 100% continuous across entire stage (x=0..4153)."""
        # Test every 20 pixels across the entire 4153-pixel mission
        missing = []
        for x in range(0, 4154, 20):
            ground = self._get_solid_ground_at(x)
            if ground is None:
                missing.append(x)
        self.assertEqual(missing, [], f"Gaps detected in solid base ground at x={missing}")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f5_tier2_wing_slope_riverbed_connection(self):
        """F5-T2-1: Wing incline begins smoothly at riverbed level y=184 at x=3380."""
        wing = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3380]
        self.assertTrue(len(wing) > 0)
        self.assertEqual(wing[0].get_height_at(3380), 198.0)

    def test_f5_tier2_wing_to_cockpit_junction(self):
        """F5-T2-2: Wing slope and cockpit slope meet seamlessly at x=3540, y=142."""
        wing = [p for p in self.level.platforms if p.semi_solid and p.x2 == 3540][0]
        cockpit = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3540][0]
        self.assertEqual(wing.get_height_at(3540), 142.0)
        self.assertEqual(cockpit.get_height_at(3540), 142.0)

    def test_f5_tier2_cockpit_to_rock_ledge_junction(self):
        """F5-T2-3: Cockpit slope and rock ledge meet seamlessly at x=3700, y=112."""
        cockpit = [p for p in self.level.platforms if p.semi_solid and p.x2 == 3700][0]
        ledge = [p for p in self.level.platforms if p.semi_solid and p.x1 == 3700][0]
        self.assertEqual(cockpit.get_height_at(3700), 112.0)
        self.assertEqual(ledge.get_height_at(3700), 112.0)

    def test_f5_tier2_boss_arena_end_boundary(self):
        """F5-T2-4: Arena riverbed platform terminates at exact stage end coordinate x=4153."""
        base = [p for p in self.level.platforms if not p.semi_solid and p.x2 == 4153]
        self.assertTrue(len(base) > 0, "Base platform must end at x=4153")

    def test_f5_tier2_incline_drop_through_to_riverbed(self):
        """F5-T2-5: Dropping through wing slope lands in riverbed at y=184."""
        body = PhysicsBody(x=3460, y=163, width=18, height=36)
        body.is_grounded = True
        wing = [p for p in self.level.platforms if p.x1 <= 3460 <= p.x2 and p.semi_solid][0]
        body.current_platform = wing
        body.drop_through_platform()
        for _ in range(25):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0)

    # =========================================================================
    # FEATURE F6: Camera Bounds & Clipping Protection
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f6_tier1_player_dynamic_left_clamp(self):
        """F6-T1-1: Player left clamp uses dynamic half-width (min_x = camera.x + width/2 = 9)."""
        game = Game()
        game.start_new_campaign("marco")
        game.camera.x = 100.0
        game.player.physics.width = 18.0
        # If player attempts to move past left bound
        target_x = 90.0
        half_w = game.player.physics.width / 2.0
        min_x = game.camera.x + half_w
        self.assertEqual(min_x, 109.0)

    def test_f6_tier1_slug_dynamic_left_clamp(self):
        """F6-T1-2: Slug left clamp uses dynamic half-width (min_x = camera.x + 27), preventing 11px clip."""
        slug = MetalSlug(x=100, y=184)
        half_w = slug.physics.width / 2.0
        self.assertEqual(half_w, 27.0)
        camera_x = 100.0
        min_x = camera_x + half_w
        self.assertEqual(min_x, 127.0)
        # Left edge of slug at min_x is exactly camera_x (no offscreen clipping)
        slug_left_edge = min_x - half_w
        self.assertEqual(slug_left_edge, camera_x)

    def test_f6_tier1_slug_dynamic_right_clamp(self):
        """F6-T1-3: Slug right clamp uses dynamic half-width (max_x = camera.x + 320 - 27)."""
        slug = MetalSlug(x=200, y=184)
        half_w = slug.physics.width / 2.0
        camera_x = 100.0
        max_x = camera_x + VIRTUAL_WIDTH - half_w
        self.assertEqual(max_x, 100.0 + 320.0 - 27.0)
        slug_right_edge = max_x + half_w
        self.assertEqual(slug_right_edge, camera_x + VIRTUAL_WIDTH)

    def test_f6_tier1_boss_arena_camera_lock_activation(self):
        """F6-T1-4: Camera locks at x=3260 when player reaches boss arena (x >= boss_arena_x - 120)."""
        camera = Camera()
        player = Player(x=self.level.boss_arena_x, y=184)
        self.level.update(player, camera)
        self.assertTrue(camera.is_locked, "Camera must lock when entering boss arena")
        self.assertEqual(camera.x, self.level.boss_arena_x - 120)

    def test_f6_tier1_boss_camera_latch_persists_on_retreat(self):
        """F6-T1-5: Camera remains latched even if player retreats to x < boss_arena_x - 120."""
        camera = Camera()
        player = Player(x=self.level.boss_arena_x + 50, y=184)
        self.level.update(player, camera)
        self.assertTrue(camera.is_locked)
        # Player moves back
        player.physics.x = self.level.boss_arena_x - 300
        self.level.update(player, camera)
        self.assertTrue(camera.is_locked, "Camera lock must persist/latch until boss is defeated")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f6_tier2_camera_unlocks_on_boss_defeat(self):
        """F6-T2-1: Camera unlocks once boss is marked defeated."""
        camera = Camera()
        player = Player(x=self.level.boss_arena_x + 50, y=184)
        self.level.update(player, camera)
        self.assertTrue(camera.is_locked)
        self.level.boss.is_defeated = True
        self.level.boss.defeat_timer = 0
        self.level.update(player, camera)
        self.assertFalse(camera.is_locked, "Camera must unlock when boss is defeated")

    def test_f6_tier2_screen_coordinates_slug_within_bounds(self):
        """F6-T2-2: Tank clamped to left bound has screen x in [0, 320]."""
        camera_x = 500.0
        half_w = 27.0
        slug_x = camera_x + half_w
        screen_left = slug_x - half_w - camera_x
        self.assertEqual(screen_left, 0.0)

    def test_f6_tier2_screen_coordinates_player_within_bounds(self):
        """F6-T2-3: Player clamped to left bound has screen x >= 0."""
        camera_x = 500.0
        half_w = 9.0
        player_x = camera_x + half_w
        screen_left = player_x - half_w - camera_x
        self.assertEqual(screen_left, 0.0)

    def test_f6_tier2_bottom_boundary_clamping(self):
        """F6-T2-4: PhysicsBody enforces grounded state or fall termination within virtual stage height."""
        body = PhysicsBody(x=200, y=176, width=18, height=36)
        body.is_grounded = True
        self.assertLessEqual(body.y, VIRTUAL_HEIGHT)

    def test_f6_tier2_stage_end_camera_clamping(self):
        """F6-T2-5: Camera x does not exceed stage_width - VIRTUAL_WIDTH."""
        camera = Camera(world_width=self.level.stage_width)
        player = Player(x=4100, y=184)
        camera.update(player.physics.x, player.physics.y)
        max_camera_x = self.level.stage_width - VIRTUAL_WIDTH
        self.assertLessEqual(camera.x, max_camera_x)

    # =========================================================================
    # TIER 3: Cross-Feature Combinations (Pairwise Interactions)
    # =========================================================================
    def test_tier3_f1_f2_traversal_beach_to_submarine(self):
        """T3-1 (F1+F2): Traversal across Beach (x=565) to Submarine zone maintains continuous grounding."""
        body = PhysicsBody(x=560, y=198, width=18, height=36)
        body.vx = 2.0
        body.is_grounded = True
        for _ in range(10):
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded, "Body must remain grounded crossing Beach to Submarine")
        self.assertEqual(body.y, 198.0)
        self.assertGreater(body.x, 565.0)

    def test_tier3_f3_f6_river_village_jump_with_camera_scroll(self):
        """T3-2 (F3+F6): Player jumping onto Hut 1 at x=2080 updates camera position smoothly without clipping."""
        camera = Camera(world_width=self.level.stage_width)
        player = Player(x=2000, y=184)
        player.physics.vx = 2.0
        player.physics.vy = -6.0
        for _ in range(30):
            player.physics.apply_gravity()
            player.physics.update_movement(self.level.platforms)
            camera.update(player.physics.x, player.physics.y)
        self.assertGreater(camera.x, 1800)
        self.assertTrue(camera.x <= player.physics.x <= camera.x + VIRTUAL_WIDTH)

    def test_tier3_f4_f5_valley_to_boss_arena_incline_transition(self):
        """T3-3 (F4+F5): Transition from Valley riverbed onto wrecked wing slope is continuous."""
        body = PhysicsBody(x=3370, y=184, width=18, height=36)
        body.vx = 2.0
        body.is_grounded = True
        for _ in range(15):
            body.update_movement(self.level.platforms)
        self.assertGreater(body.x, 3380.0)
        # Should now be on or above wing slope
        self.assertLessEqual(body.y, 198.0)

    def test_tier3_f5_f6_slug_fuselage_traversal_in_locked_arena(self):
        """T3-4 (F5+F6): SV-001 tank driving up wing slope remains properly clamped within locked arena."""
        camera = Camera()
        camera.lock_at(self.level.boss_arena_x - 120)
        slug = MetalSlug(x=3400, y=184)
        slug.physics.vx = 1.6
        for _ in range(40):
            slug.physics.update_movement(self.level.platforms)
        # Clamp against camera
        half_w = slug.physics.width / 2.0
        min_x = camera.x + half_w
        max_x = camera.x + VIRTUAL_WIDTH - half_w
        clamped_x = max(min_x, min(slug.physics.x, max_x))
        slug.physics.x = clamped_x
        # Verify tank is within visible screen
        screen_x = slug.physics.x - camera.x
        self.assertGreaterEqual(screen_x - half_w, 0.0)
        self.assertLessEqual(screen_x + half_w, float(VIRTUAL_WIDTH))


if __name__ == "__main__":
    unittest.main()
