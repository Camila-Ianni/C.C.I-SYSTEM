"""
Player Entity for Metal Slug 1 (Marco Rossi / Tarma Roving).
Implements:
- Torso + Legs composite animations.
- 8-way aim states (Forward, Straight Up, Diagonal Up running, Downwards in air, Crouch forward).
- Crouching, crawling and crouch-shooting with authentic hitbox shrink (height 18 vs 34).
- Automatic knife melee combat (standing and crouched) in close range (< 24px).
- Weapon firing, bullet spawn and casing ejection in all 8 directions.
- Grenade throwing.
- Platform physics, semi-solid drop-through.
- Respawn parachute and invincibility frames.
"""
import pygame
from src.config import (
    CHROMA_CYAN, PLAYER_WALK_SPEED, PLAYER_JUMP_IMPULSE,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE
)
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.weapons.projectile import Bullet, Grenade

class Player:
    def __init__(self, x=60, y=180, character="marco"):
        self.physics = PhysicsBody(x, y, width=18, height=34)
        self.character = character
        self.facing_right = True
        
        # Gameplay Status
        self.lives = 3
        self.grenades = 10
        self.score = 0
        self.weapon_type = "PISTOL"
        self.current_weapon_visual = None
        self.weapon_data = {}
        self.ammo = -1  # -1 represents infinite
        self.is_invincible = False
        self.invincible_timer = 0
        self.is_dead = False
        self.spawn_timer = 300
        
        # Action & Aiming States
        self.is_crouching = False
        self.is_aiming_up = False
        self.is_aiming_down = False
        self.is_crouch_shooting = False
        self.crouch_shoot_timer = 0
        self.is_standing_shooting = False
        self.standing_shoot_timer = 0
        self.is_run_shooting = False
        self.run_shoot_timer = 0
        self.is_attacking_melee = False
        self.is_crouch_melee = False
        self.melee_timer = 0
        self.is_throwing_grenade = False
        self.grenade_timer = 0
        self.shoot_cooldown = 0
        
        # Load Sprites & Animations
        self.load_sprites()

    def load_sprites(self):
        """Loads and extracts Marco or Tarma sprites with seamless waist-anchored compositions for all weapons."""
        if self.character == "tarma":
            sheet_path = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Tarma Roving.png"
            colorkey = (86, 177, 222)
        else:
            sheet_path = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
            colorkey = CHROMA_CYAN
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=colorkey)

        # Base Anatomy (Legs & Anchors)
        if self.character == "tarma":
            t_legs = SpriteLoader.get_subsurface(sheet, 161, 276, 21, 16)
            jump_leg = SpriteLoader.get_subsurface(sheet, 11, 730, 18, 25)
            jump_down_leg = jump_leg
            t_legs_boxes = [
                (10, 618, 21, 20), (46, 618, 28, 20), (84, 618, 31, 16), (126, 618, 19, 20),
                (163, 618, 15, 20), (200, 618, 16, 20), (238, 618, 21, 20), (274, 618, 26, 20),
                (316, 618, 31, 16), (359, 618, 20, 20), (400, 618, 15, 20), (436, 618, 18, 20)
            ]
            run_legs = [SpriteLoader.get_subsurface(sheet, *b) for b in t_legs_boxes]
            t_jd = SpriteLoader.get_subsurface(sheet, 6, 950, 27, 45)
            t_throw_rects = [
                (8, 1210, 31, 29), (49, 1210, 33, 29), (90, 1209, 31, 30),
                (130, 1211, 31, 28), (170, 1211, 31, 28), (209, 1210, 28, 29)
            ]
            knife_rects = [
                (6, 1400, 39, 56), (47, 1400, 36, 56), (89, 1400, 84, 56),
                (176, 1400, 87, 56), (266, 1400, 37, 56)
            ]
            c_knife_surfs = [SpriteLoader.get_subsurface(sheet, 8, 1400, 39, 56)]
        else:
            t_legs = SpriteLoader.get_subsurface(sheet, 149, 276, 20, 16)
            jump_leg = SpriteLoader.get_subsurface(sheet, 10, 894, 18, 25)
            jump_down_leg = SpriteLoader.get_subsurface(sheet, 59, 645, 16, 19)
            m_legs_boxes = [
                (10, 511, 21, 20), (36, 511, 28, 20), (69, 511, 31, 16), (105, 511, 19, 20),
                (129, 511, 15, 20), (149, 511, 16, 20), (170, 511, 21, 20), (196, 511, 26, 20),
                (227, 511, 31, 16), (263, 511, 20, 20), (288, 511, 15, 20), (308, 511, 16, 20)
            ]
            run_legs = [SpriteLoader.get_subsurface(sheet, *b) for b in m_legs_boxes]
            t_jd = SpriteLoader.get_subsurface(sheet, 10, 953, 23, 32)
            t_throw_rects = [
                (10, 1158, 31, 27), (46, 1158, 33, 27), (84, 1157, 31, 28),
                (120, 1159, 31, 26), (156, 1159, 31, 26), (192, 1158, 28, 27)
            ]
            knife_rects = [
                (10, 1285, 36, 38), (51, 1285, 36, 38), (92, 1285, 37, 38),
                (134, 1285, 39, 38), (178, 1285, 41, 38), (224, 1285, 40, 38)
            ]
            c_knife_surfs = [
                SpriteLoader.get_subsurface(sheet, 10, 1328, 26, 25),
                SpriteLoader.get_subsurface(sheet, 41, 1328, 26, 29),
                SpriteLoader.get_subsurface(sheet, 72, 1328, 30, 28),
                SpriteLoader.get_subsurface(sheet, 107, 1328, 29, 27)
            ]

        # Weapon-Specific Torso Configurations (PISTOL, H, S, R, F)
        # Weapon-Specific Torso Configurations (PISTOL, H, S, R, F)
        if self.character == "tarma":
            t_heavy = {
                "idle": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 2310, 38, 37), (56, 2311, 37, 36), (101, 2310, 36, 37), (145, 2310, 36, 37)
                ]],
                "run": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 2146, 37, 32), (51, 2146, 39, 31), (96, 2146, 37, 32), (140, 2146, 39, 31),
                    (187, 2146, 38, 28), (231, 2146, 39, 31), (277, 2146, 38, 28), (322, 2146, 39, 31),
                    (367, 2146, 38, 28), (413, 2146, 39, 27), (459, 2146, 38, 28), (503, 2146, 39, 27)
                ]],
                "shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (8, 2356, 36, 30), (52, 2356, 37, 30), (98, 2356, 36, 30), (146, 2356, 34, 30)
                ]],
                "aim_up": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (227, 2408, 30, 36), (266, 2408, 29, 36), (303, 2408, 29, 36), (340, 2408, 29, 36)
                ]],
                "jump_tor": SpriteLoader.get_subsurface(sheet, 102, 2273, 38, 28),
                "jump_down": SpriteLoader.get_subsurface(sheet, 47, 2452, 28, 45),
                "c_idle": [SpriteLoader.get_subsurface(sheet, 7, 2556, 41, 24)],
                "c_crawl": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (7, 2556, 41, 24), (56, 2556, 41, 24), (107, 2556, 41, 24)
                ]],
                "c_shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (8, 2589, 60, 27), (78, 2590, 36, 27), (146, 2591, 60, 25)
                ]]
            }
            w_configs = {
                "PISTOL": {
                    "idle": [SpriteLoader.get_subsurface(sheet, 10 + i * 34, 263, 28, 29) for i in range(4)],
                    "run": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (6, 582, 32, 28), (48, 581, 30, 29), (87, 581, 28, 28), (124, 581, 27, 27),
                        (159, 581, 29, 28), (197, 581, 30, 28), (237, 582, 32, 29), (278, 581, 32, 29),
                        (318, 581, 32, 28), (358, 582, 31, 27), (397, 582, 31, 28), (435, 582, 31, 28)
                    ]],
                    "shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (6, 924, 49, 21), (56, 924, 56, 21), (117, 924, 37, 21), (173, 924, 38, 21),
                        (212, 924, 38, 21), (253, 924, 38, 21), (300, 924, 36, 21), (341, 924, 25, 21)
                    ]],
                    "aim_up": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (98, 988, 22, 39), (128, 989, 25, 38), (160, 987, 25, 40), (192, 986, 24, 41)
                    ]],
                    "jump_tor": SpriteLoader.get_subsurface(sheet, 226, 689, 29, 28),
                    "jump_down": SpriteLoader.get_subsurface(sheet, 145, 692, 29, 22),
                    "c_idle": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (125, 860, 31, 27), (164, 860, 31, 27), (204, 860, 31, 27), (243, 860, 31, 27)
                    ]],
                    "c_crawl": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (289, 863, 34, 24), (330, 863, 33, 24), (368, 863, 33, 24), (407, 863, 33, 24)
                    ]],
                    "c_shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (5, 932, 50, 23), (61, 933, 51, 22), (117, 932, 37, 22), (174, 931, 37, 23),
                        (216, 929, 37, 25), (258, 929, 37, 25), (300, 931, 37, 23), (341, 931, 34, 26)
                    ]]
                }
            }
            for wt in ["H", "S", "R", "F"]:
                w_configs[wt] = t_heavy
        else:
            m_heavy = {
                "idle": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 3466, 38, 37), (53, 3467, 37, 36), (95, 3466, 36, 37), (136, 3466, 36, 37)
                ]],
                "run": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 3389, 42, 26), (57, 3388, 39, 27), (101, 3388, 38, 28), (144, 3389, 39, 27),
                    (188, 3389, 41, 28), (234, 3389, 42, 28), (281, 3389, 42, 29), (328, 3389, 43, 29),
                    (376, 3389, 44, 29), (425, 3389, 42, 29), (472, 3389, 43, 28), (520, 3389, 43, 28)
                ]],
                "shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (919, 966, 36, 30), (960, 966, 36, 30), (1001, 966, 36, 29), (1042, 966, 36, 30), (1084, 966, 36, 30)
                ]],
                "aim_up": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 4049, 30, 36), (45, 4049, 29, 36), (79, 4049, 29, 36), (113, 4049, 29, 36)
                ]],
                "jump_tor": SpriteLoader.get_subsurface(sheet, 10, 3762, 36, 28),
                "jump_down": SpriteLoader.get_subsurface(sheet, 1322, 1004, 34, 43),
                "c_idle": [SpriteLoader.get_subsurface(sheet, 10, 4895, 41, 24)],
                "c_crawl": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (10, 4924, 41, 24), (56, 4924, 41, 24), (102, 4924, 41, 24)
                ]],
                "c_shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                    (148, 4924, 41, 24), (194, 4924, 41, 24), (240, 4924, 41, 24)
                ]]
            }
            w_configs = {
                "PISTOL": {
                    "idle": [SpriteLoader.get_subsurface(sheet, 10 + i * 34, 263, 28, 29) for i in range(4)],
                    "run": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (10, 477, 32, 28), (47, 477, 30, 29), (82, 477, 28, 28), (115, 477, 27, 27),
                        (147, 477, 29, 28), (181, 477, 30, 28), (216, 477, 32, 29), (254, 477, 32, 29),
                        (291, 477, 32, 28), (328, 477, 31, 27), (364, 477, 31, 28), (400, 477, 31, 28)
                    ]],
                    "shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (919, 804, 39, 21), (963, 804, 53, 22), (1020, 804, 52, 20), (1077, 804, 38, 19),
                        (1134, 804, 37, 20), (1176, 802, 37, 22), (1218, 802, 37, 23), (1260, 804, 37, 22)
                    ]],
                    "aim_up": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (91, 1577, 22, 39), (118, 1578, 25, 38), (148, 1576, 25, 40), (178, 1575, 24, 41)
                    ]],
                    "jump_tor": SpriteLoader.get_subsurface(sheet, 10, 561, 29, 29),
                    "jump_down": SpriteLoader.get_subsurface(sheet, 147, 865, 29, 22),
                    "c_idle": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (10, 1728, 34, 24), (49, 1728, 33, 24), (87, 1728, 33, 24), (125, 1728, 33, 24)
                    ]],
                    "c_crawl": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (10, 1757, 34, 24), (49, 1757, 34, 24), (88, 1757, 34, 24), (127, 1757, 34, 24),
                        (166, 1757, 35, 24), (206, 1757, 35, 24), (246, 1757, 35, 24)
                    ]],
                    "c_shoot": [SpriteLoader.get_subsurface(sheet, *b) for b in [
                        (10, 1819, 50, 27), (65, 1819, 51, 27), (121, 1819, 37, 27), (178, 1819, 37, 27),
                        (221, 1817, 37, 29), (263, 1817, 37, 29), (305, 1819, 37, 27), (347, 1819, 34, 27)
                    ]]
                }
            }
            for wt in ["H", "S", "R", "F"]:
                w_configs[wt] = m_heavy

        waist_l = [10.7, 13.5, 12.4, 6.7, 5.0, 6.0, 9.8, 12.7, 11.9, 6.8, 4.5, 6.9]
        waist_t = [20.0, 17.6, 16.1, 15.6, 17.1, 18.2, 19.2, 18.1, 18.2, 19.2, 19.2, 19.6]

        self.weapon_data = {}
        for wt, cfg in w_configs.items():
            # 1. Idle
            idle_r = []
            if wt == "PISTOL":
                for tf in cfg["idle"]:
                    comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                    comp.blit(t_legs, (14, 30))
                    comp.blit(tf, (12, 30 - tf.get_height() + 5))
                    idle_r.append(comp)
            else:
                for tf in cfg["idle"]:
                    comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                    comp.blit(tf, (24 - tf.get_width() // 2, 46 - tf.get_height()))
                    idle_r.append(comp)
            idle_l = [pygame.transform.flip(f, True, False) for f in idle_r]

            # 2. Run
            run_r = []
            for i in range(12):
                leg = run_legs[i]
                tor = cfg["run"][i]
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                lx = int(24 - waist_l[i])
                comp.blit(leg, (lx, 26))
                if wt == "PISTOL":
                    tx = int(24 - waist_t[i]) + 8
                    comp.blit(tor, (tx, 26 - tor.get_height() + 5))
                else:
                    comp.blit(tor, (lx - 5, 26 - tor.get_height() + 5))
                run_r.append(comp)
            run_l = [pygame.transform.flip(f, True, False) for f in run_r]

            # 2b. Run Shoot (legs running while firing weapon forward)
            run_shoot_r = []
            for i in range(12):
                leg = run_legs[i]
                tor = cfg["shoot"][i % len(cfg["shoot"])]
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                lx = int(24 - waist_l[i])
                comp.blit(leg, (lx, 26))
                if wt == "PISTOL":
                    comp.blit(tor, (lx - 2, 26 - tor.get_height() + 5))
                else:
                    comp.blit(tor, (lx - 4, 26 - tor.get_height() + 5))
                run_shoot_r.append(comp)
            run_shoot_l = [pygame.transform.flip(f, True, False) for f in run_shoot_r]

            # 3. Aim Up
            aim_up_r = []
            for ut in cfg["aim_up"]:
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                leg_y = 32 if wt == "PISTOL" else 30
                comp.blit(t_legs, (14, leg_y))
                tx = 14 if wt == "PISTOL" else 12
                comp.blit(ut, (tx, max(0, leg_y - ut.get_height() + 5)))
                aim_up_r.append(comp)
            aim_up_l = [pygame.transform.flip(f, True, False) for f in aim_up_r]

            # 4. Aim Up Run
            aim_up_run_r = []
            for i in range(12):
                leg = run_legs[i]
                tor = cfg["aim_up"][i % len(cfg["aim_up"])]
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                lx = int(24 - waist_l[i])
                comp.blit(leg, (lx, 26))
                comp.blit(tor, (lx - 2 if wt == "PISTOL" else lx - 4, max(0, 26 - tor.get_height() + 5)))
                aim_up_run_r.append(comp)
            aim_up_run_l = [pygame.transform.flip(f, True, False) for f in aim_up_run_r]

            # 5. Jump Frame
            jump_comp_r = pygame.Surface((48, 48), pygame.SRCALPHA)
            jump_tor = cfg["jump_tor"]
            jump_comp_r.blit(jump_leg, (15 if self.character == "marco" else 14, 23))
            jump_comp_r.blit(jump_tor, (11 if wt == "PISTOL" else 10, 0))
            jump_frame_r = jump_comp_r
            jump_frame_l = pygame.transform.flip(jump_comp_r, True, False)

            # 6. Jump Aim Up
            jump_up_comp = pygame.Surface((48, 64), pygame.SRCALPHA)
            jump_up_ly = 37
            jump_up_comp.blit(jump_leg, (15 if self.character == "marco" else 14, jump_up_ly))
            ut_mid = cfg["aim_up"][len(cfg["aim_up"]) // 2]
            jump_up_ty = jump_up_ly + 5 - ut_mid.get_height()
            jump_up_tx = 14 if wt == "PISTOL" else 11
            jump_up_comp.blit(ut_mid, (jump_up_tx, jump_up_ty))
            jump_aim_up_r = jump_up_comp
            jump_aim_up_l = pygame.transform.flip(jump_up_comp, True, False)

            # 7. Jump Aim Down
            jump_down_comp = pygame.Surface((48, 48), pygame.SRCALPHA)
            jd_surf = cfg["jump_down"]
            if wt == "PISTOL":
                jump_down_comp.blit(jump_leg, (15 if self.character == "marco" else 14, 20))
                jump_down_comp.blit(jd_surf, (13, 3))
            else:
                jump_down_comp.blit(jd_surf, (24 - jd_surf.get_width() // 2, 46 - jd_surf.get_height()))
            jump_aim_down_r = jump_down_comp
            jump_aim_down_l = pygame.transform.flip(jump_down_comp, True, False)

            # 8. Crouch Idle
            ci = cfg["c_idle"][0]
            c_idle_surf = pygame.Surface((48, 48), pygame.SRCALPHA)
            c_idle_surf.blit(ci, (24 - ci.get_width() // 2, 46 - ci.get_height()))
            crouch_idle_r = c_idle_surf
            crouch_idle_l = pygame.transform.flip(c_idle_surf, True, False)

            # 9. Crouch Crawl
            crouch_crawl_r = []
            for cs in cfg["c_crawl"]:
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                comp.blit(cs, (24 - cs.get_width() // 2, 46 - cs.get_height()))
                crouch_crawl_r.append(comp)
            crouch_crawl_l = [pygame.transform.flip(f, True, False) for f in crouch_crawl_r]

            # 10. Crouch Shoot
            crouch_shoot_r = []
            for cs in cfg["c_shoot"]:
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                comp.blit(cs, (24 - cs.get_width() // 2, 46 - cs.get_height()))
                crouch_shoot_r.append(comp)
            crouch_shoot_l = [pygame.transform.flip(f, True, False) for f in crouch_shoot_r]

            # 11. Standing Shoot
            shoot_r = []
            for tf in cfg["shoot"]:
                comp = pygame.Surface((48, 48), pygame.SRCALPHA)
                comp.blit(t_legs, (14, 30))
                ty = 6 if wt == "PISTOL" else (30 - tf.get_height() + 5)
                comp.blit(tf, (12, ty))
                shoot_r.append(comp)
            shoot_l = [pygame.transform.flip(f, True, False) for f in shoot_r]

            self.weapon_data[wt] = {
                "idle_r": idle_r, "idle_l": idle_l,
                "run_r": run_r, "run_l": run_l,
                "run_shoot_r": run_shoot_r, "run_shoot_l": run_shoot_l,
                "aim_up_r": aim_up_r, "aim_up_l": aim_up_l,
                "aim_up_run_r": aim_up_run_r, "aim_up_run_l": aim_up_run_l,
                "jump_frame_r": jump_frame_r, "jump_frame_l": jump_frame_l,
                "jump_aim_up_r": jump_aim_up_r, "jump_aim_up_l": jump_aim_up_l,
                "jump_aim_down_r": jump_aim_down_r, "jump_aim_down_l": jump_aim_down_l,
                "crouch_idle_r": crouch_idle_r, "crouch_idle_l": crouch_idle_l,
                "crouch_crawl_r": crouch_crawl_r, "crouch_crawl_l": crouch_crawl_l,
                "crouch_shoot_r": crouch_shoot_r, "crouch_shoot_l": crouch_shoot_l,
                "shoot_r": shoot_r, "shoot_l": shoot_l
            }

        # Grenade Throw
        self.throw_frames_r = []
        for tr in t_throw_rects:
            tf = SpriteLoader.get_subsurface(sheet, *tr)
            comp = pygame.Surface((48, 48), pygame.SRCALPHA)
            comp.blit(t_legs, (14, 30))
            comp.blit(tf, (13, 30 - tf.get_height() + 3))
            self.throw_frames_r.append(comp)
        self.throw_frames_l = [pygame.transform.flip(f, True, False) for f in self.throw_frames_r]

        # Crouch Knife Animation
        self.crouch_knife_r = []
        for ck in c_knife_surfs:
            comp = pygame.Surface((48, 48), pygame.SRCALPHA)
            comp.blit(ck, (24 - ck.get_width() // 2, 46 - ck.get_height()))
            self.crouch_knife_r.append(comp)
        self.crouch_knife_l = [pygame.transform.flip(f, True, False) for f in self.crouch_knife_r]

        # Standing Knife Melee Attack
        self.knife_anim_r = []
        for kr in knife_rects:
            kf = SpriteLoader.get_subsurface(sheet, *kr)
            comp = pygame.Surface((48, 48), pygame.SRCALPHA)
            comp.blit(kf, (24 - kf.get_width() // 2, 46 - kf.get_height()))
            self.knife_anim_r.append(comp)
        self.knife_anim_l = [pygame.transform.flip(f, True, False) for f in self.knife_anim_r]

        # Load initial weapon visuals
        self.sync_weapon_visuals()

        # Setup Controllers
        self.anim_idle = Animation(self.idle_frames_r, frame_duration=7, loop=True)
        self.anim_run = Animation(self.run_frames_r, frame_duration=3, loop=True)
        self.anim_run_shoot = Animation(self.run_shoot_frames_r, frame_duration=3, loop=True)
        self.anim_aim_up = Animation(self.aim_up_frames_r, frame_duration=6, loop=True)
        self.anim_aim_up_run = Animation(self.aim_up_run_r, frame_duration=3, loop=True)
        self.anim_throw = Animation(self.throw_frames_r, frame_duration=3, loop=False)
        self.anim_knife = Animation(self.knife_anim_r, frame_duration=3, loop=False)
        self.anim_crouch_crawl = Animation(self.crouch_crawl_r, frame_duration=5, loop=True)
        self.anim_crouch_shoot = Animation(self.crouch_shoot_r, frame_duration=3, loop=False)
        self.anim_crouch_knife = Animation(self.crouch_knife_r, frame_duration=3, loop=False)
        self.anim_shoot = Animation(self.shoot_frames_r, frame_duration=2, loop=False)

    def sync_weapon_visuals(self):
        """Swaps active animation frames when the equipped weapon changes."""
        w = self.weapon_type if self.weapon_type in self.weapon_data else "PISTOL"
        if w == self.current_weapon_visual:
            return
        self.current_weapon_visual = w
        d = self.weapon_data[w]
        self.idle_frames_r = d["idle_r"]
        self.idle_frames_l = d["idle_l"]
        self.run_frames_r = d["run_r"]
        self.run_frames_l = d["run_l"]
        self.run_shoot_frames_r = d["run_shoot_r"]
        self.run_shoot_frames_l = d["run_shoot_l"]
        self.aim_up_frames_r = d["aim_up_r"]
        self.aim_up_frames_l = d["aim_up_l"]
        self.aim_up_run_r = d["aim_up_run_r"]
        self.aim_up_run_l = d["aim_up_run_l"]
        self.jump_frame_r = d["jump_frame_r"]
        self.jump_frame_l = d["jump_frame_l"]
        self.jump_aim_up_r = d["jump_aim_up_r"]
        self.jump_aim_up_l = d["jump_aim_up_l"]
        self.jump_aim_down_r = d["jump_aim_down_r"]
        self.jump_aim_down_l = d["jump_aim_down_l"]
        self.crouch_idle_r = d["crouch_idle_r"]
        self.crouch_idle_l = d["crouch_idle_l"]
        self.crouch_crawl_r = d["crouch_crawl_r"]
        self.crouch_crawl_l = d["crouch_crawl_l"]
        self.crouch_shoot_r = d["crouch_shoot_r"]
        self.crouch_shoot_l = d["crouch_shoot_l"]
        self.shoot_frames_r = d["shoot_r"]
        self.shoot_frames_l = d["shoot_l"]
        
        if hasattr(self, "anim_idle"):
            self.anim_idle.frames = self.idle_frames_r if self.facing_right else self.idle_frames_l
            self.anim_run.frames = self.run_frames_r if self.facing_right else self.run_frames_l
            self.anim_aim_up.frames = self.aim_up_frames_r if self.facing_right else self.aim_up_frames_l
            self.anim_aim_up_run.frames = self.aim_up_run_r if self.facing_right else self.aim_up_run_l
            self.anim_crouch_crawl.frames = self.crouch_crawl_r if self.facing_right else self.crouch_crawl_l
            self.anim_crouch_shoot.frames = self.crouch_shoot_r if self.facing_right else self.crouch_shoot_l
            if hasattr(self, "anim_shoot"):
                self.anim_shoot.frames = self.shoot_frames_r if self.facing_right else self.shoot_frames_l
            if hasattr(self, "anim_run_shoot"):
                self.anim_run_shoot.frames = self.run_shoot_frames_r if self.facing_right else self.run_shoot_frames_l

    def handle_input(self, input_manager, enemies=None, projectiles=None, particle_system=None, sound_manager=None):
        if self.is_dead:
            return

        # Melee & Grenade timer progression
        if self.melee_timer > 0:
            self.melee_timer -= 1
            if self.melee_timer == 0:
                self.is_attacking_melee = False
                self.is_crouch_melee = False
                
        if self.grenade_timer > 0:
            self.grenade_timer -= 1
            if self.grenade_timer == 0:
                self.is_throwing_grenade = False

        if self.crouch_shoot_timer > 0:
            self.crouch_shoot_timer -= 1
            if self.crouch_shoot_timer == 0:
                self.is_crouch_shooting = False

        if self.standing_shoot_timer > 0:
            self.standing_shoot_timer -= 1
            if self.standing_shoot_timer == 0:
                self.is_standing_shooting = False

        if self.run_shoot_timer > 0:
            self.run_shoot_timer -= 1
            if self.run_shoot_timer == 0:
                self.is_run_shooting = False
                
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        # Crouch check (Down held while on ground)
        if input_manager.is_held(ACTION_DOWN) and self.physics.is_grounded:
            self.is_crouching = True
            self.physics.height = 18.0  # Duck down to dodge bullets!
            # Crawl left or right while crouched
            if input_manager.is_held(ACTION_LEFT):
                self.physics.vx = -PLAYER_WALK_SPEED * 0.6
                self.facing_right = False
            elif input_manager.is_held(ACTION_RIGHT):
                self.physics.vx = PLAYER_WALK_SPEED * 0.6
                self.facing_right = True
            else:
                self.physics.vx = 0.0
        else:
            self.is_crouching = False
            self.physics.height = 34.0  # Restore full standing collision box
            # Standard horizontal movement
            if input_manager.is_held(ACTION_LEFT):
                self.physics.vx = -PLAYER_WALK_SPEED
                self.facing_right = False
            elif input_manager.is_held(ACTION_RIGHT):
                self.physics.vx = PLAYER_WALK_SPEED
                self.facing_right = True
            else:
                self.physics.vx = 0.0

        # Aim Directions
        self.is_aiming_up = input_manager.is_held(ACTION_UP) and not self.is_crouching
        self.is_aiming_down = input_manager.is_held(ACTION_DOWN) and not self.physics.is_grounded

        # Jump (Button B)
        if input_manager.is_just_pressed(ACTION_JUMP):
            if input_manager.is_held(ACTION_DOWN) and self.physics.is_grounded:
                # Drop through semi-solid platform
                self.physics.drop_through_platform()
            elif self.physics.is_grounded:
                self.physics.vy = PLAYER_JUMP_IMPULSE
                self.physics.is_grounded = False

        # Check Close Range for Knife Melee Attack (< 24px)
        close_enemy = False
        if enemies:
            for e in enemies:
                if not getattr(e, 'is_dead', False) and abs(e.physics.x - self.physics.x) < 26 and abs(e.physics.y - self.physics.y) < 22:
                    close_enemy = e
                    break

        # Shoot / Attack (Button A)
        can_shoot = input_manager.is_just_pressed(ACTION_SHOOT) or (self.weapon_type == "H" and input_manager.is_held(ACTION_SHOOT))
        if can_shoot:
            if close_enemy and self.physics.is_grounded and self.shoot_cooldown == 0:
                # Trigger Knife Attack (Crouched or Standing)
                self.is_attacking_melee = True
                self.is_crouch_melee = self.is_crouching
                self.melee_timer = 15
                self.shoot_cooldown = 15
                if self.is_crouch_melee:
                    self.anim_crouch_knife.reset()
                else:
                    self.anim_knife.reset()
                close_enemy.take_damage(10, death_type="knife")
                if sound_manager:
                    sound_manager.play_sound("knife", "player")
            elif self.shoot_cooldown == 0:
                if self.is_crouching:
                    self.is_crouch_shooting = True
                    self.crouch_shoot_timer = 10
                    self.anim_crouch_shoot.reset()
                elif self.physics.is_grounded and not self.is_aiming_up:
                    if abs(self.physics.vx) > 0.1:
                        self.is_run_shooting = True
                        self.run_shoot_timer = 12
                        self.is_standing_shooting = False
                        self.standing_shoot_timer = 0
                    else:
                        self.anim_shoot.reset()
                        self.is_standing_shooting = True
                        self.standing_shoot_timer = 12 if self.weapon_type == "H" else 16
                        self.is_run_shooting = False
                        self.run_shoot_timer = 0
                self.fire_weapon(projectiles, particle_system, sound_manager)

        # Throw Grenade (Button C)
        if input_manager.is_just_pressed(ACTION_GRENADE) and self.grenades > 0 and self.grenade_timer == 0:
            self.grenades -= 1
            self.is_throwing_grenade = True
            self.grenade_timer = 18
            self.anim_throw.reset()
            if projectiles is not None:
                spawn_x = self.physics.x + (12 if self.facing_right else -12)
                spawn_y = self.physics.y - (12 if self.is_crouching else 20)
                projectiles.append(Grenade(spawn_x, spawn_y, facing_right=self.facing_right))
            if sound_manager:
                sound_manager.play_sound("throw", "player")

    def fire_weapon(self, projectiles, particle_system, sound_manager):
        """Fires current weapon (Handgun, H, S, R, F) in 8 directions with authentic sprites."""
        from src.weapons.special_weapons import HeavyMachineGunBullet, ShotgunBlast, RocketMissile, FlameShotBall
        
        self.shoot_cooldown = 5 if self.weapon_type == "H" else 10
        
        # Determine 8-way aim vector
        if self.is_aiming_up:
            if abs(self.physics.vx) > 0.1 and not self.is_crouching:
                # Diagonal up while running
                dir_x = 0.707 if self.facing_right else -0.707
                dir_y = -0.707
            else:
                # Straight up
                dir_x = 0.0
                dir_y = -1.0
        elif self.is_aiming_down:
            # Straight down in air
            dir_x = 0.0
            dir_y = 1.0
        else:
            # Horizontal (standing or crouched)
            dir_x = 1.0 if self.facing_right else -1.0
            dir_y = 0.0

        # Calculate spawn muzzle position
        if self.is_aiming_up:
            spawn_x = self.physics.x + (8.0 if self.facing_right else -8.0) * (0.4 if dir_x == 0 else 1.0)
            spawn_y = self.physics.y - 36.0
        elif self.is_aiming_down:
            spawn_x = self.physics.x
            spawn_y = self.physics.y + 4.0
        elif self.is_crouching:
            spawn_x = self.physics.x + (18.0 if self.facing_right else -18.0)
            spawn_y = self.physics.y - 12.0
        else:
            spawn_x = self.physics.x + (18.0 if self.facing_right else -18.0)
            spawn_y = self.physics.y - 22.0

        if projectiles is not None:
            if self.weapon_type == "H":
                projectiles.append(HeavyMachineGunBullet(spawn_x, spawn_y, dir_x, dir_y))
            elif self.weapon_type == "S":
                projectiles.append(ShotgunBlast(spawn_x, spawn_y, facing_right=self.facing_right, aiming_up=self.is_aiming_up, owner=self))
                self.shoot_cooldown = 18
            elif self.weapon_type == "R":
                projectiles.append(RocketMissile(spawn_x, spawn_y, facing_right=self.facing_right, aiming_up=self.is_aiming_up))
                self.shoot_cooldown = 16
            elif self.weapon_type == "F":
                projectiles.append(FlameShotBall(spawn_x, spawn_y, facing_right=self.facing_right, aiming_up=self.is_aiming_up))
                self.shoot_cooldown = 15
            else:
                projectiles.append(Bullet(spawn_x, spawn_y, dir_x, dir_y))

        # Decrement ammo for special weapons
        if self.ammo > 0:
            self.ammo -= 1
            if self.ammo == 0:
                self.weapon_type = "PISTOL"
                self.ammo = -1

        if particle_system is not None:
            casing_y = self.physics.y - (12.0 if self.is_crouching else 20.0)
            particle_system.spawn_casing(self.physics.x, casing_y, self.facing_right)
            particle_system.spawn_muzzle_flash(spawn_x, spawn_y, dir_x, dir_y)

        if sound_manager:
            sfx_map = {
                "H": "heavy_machine_gun_shot",
                "S": "shotgun_blast",
                "R": "rocket_fire",
                "F": "flame_fire"
            }
            snd_name = sfx_map.get(self.weapon_type, "gunshot")
            sound_manager.play_sound(snd_name, "player")

    def update(self, platforms=None):
        if self.is_dead:
            return

        self.sync_weapon_visuals()

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

        # Invincibility flicker timer
        if self.is_invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.is_invincible = False

        # Cancel standing shoot if moving, crouching, in air, or aiming up
        if not self.physics.is_grounded or self.is_crouching or self.is_aiming_up or abs(self.physics.vx) > 0.1:
            self.is_standing_shooting = False
            self.standing_shoot_timer = 0

        # Cancel run shoot if stopped, crouching, in air, or aiming up
        if not self.physics.is_grounded or self.is_crouching or self.is_aiming_up or abs(self.physics.vx) <= 0.1:
            self.is_run_shooting = False
            self.run_shoot_timer = 0

        # Directional animation surface updates
        self.anim_idle.frames = self.idle_frames_r if self.facing_right else self.idle_frames_l
        self.anim_run.frames = self.run_frames_r if self.facing_right else self.run_frames_l
        self.anim_run_shoot.frames = self.run_shoot_frames_r if self.facing_right else self.run_shoot_frames_l
        self.anim_aim_up.frames = self.aim_up_frames_r if self.facing_right else self.aim_up_frames_l
        self.anim_aim_up_run.frames = self.aim_up_run_r if self.facing_right else self.aim_up_run_l
        self.anim_throw.frames = self.throw_frames_r if self.facing_right else self.throw_frames_l
        self.anim_knife.frames = self.knife_anim_r if self.facing_right else self.knife_anim_l
        self.anim_crouch_crawl.frames = self.crouch_crawl_r if self.facing_right else self.crouch_crawl_l
        self.anim_crouch_shoot.frames = self.crouch_shoot_r if self.facing_right else self.crouch_shoot_l
        self.anim_crouch_knife.frames = self.crouch_knife_r if self.facing_right else self.crouch_knife_l
        self.anim_shoot.frames = self.shoot_frames_r if self.facing_right else self.shoot_frames_l

        # Progress active animation
        if self.is_attacking_melee:
            if self.is_crouch_melee:
                self.anim_crouch_knife.update()
            else:
                self.anim_knife.update()
        elif self.is_throwing_grenade:
            self.anim_throw.update()
        elif not self.physics.is_grounded:
            pass  # Jump frames are single-pose
        elif self.is_crouching:
            if self.is_crouch_shooting:
                self.anim_crouch_shoot.update()
            elif abs(self.physics.vx) > 0.1:
                self.anim_crouch_crawl.update()
        elif self.is_aiming_up:
            if abs(self.physics.vx) > 0.1:
                self.anim_aim_up_run.update()
            else:
                self.anim_aim_up.update()
        elif abs(self.physics.vx) > 0.1:
            if self.is_run_shooting:
                self.anim_run_shoot.update()
                self.anim_run.current_frame = self.anim_run_shoot.current_frame
                self.anim_run.tick_counter = self.anim_run_shoot.tick_counter
            else:
                self.anim_run.update()
        elif self.is_standing_shooting:
            self.anim_shoot.update()
        else:
            self.anim_idle.update()

    def draw(self, surface, camera):
        if self.is_dead:
            return

        # Blinking transparency during invincibility frames
        if self.is_invincible and (self.invincible_timer // 3) % 2 == 0:
            return

        sx, sy = camera.apply(self.physics.x, self.physics.y)

        # 1. Melee Knife Attack (Crouching or Standing)
        if self.is_attacking_melee:
            anim = self.anim_crouch_knife if self.is_crouch_melee else self.anim_knife
            img = anim.get_current_surface()
            if img:
                surface.blit(img, (sx - 24, sy - 46))
            return

        # 2. Grenade Throw
        if self.is_throwing_grenade:
            img = self.anim_throw.get_current_surface()
            if img:
                surface.blit(img, (sx - 24, sy - 46))
            return

        # 3. Jump (in air: Up, Down, or Forward)
        if not self.physics.is_grounded:
            if self.is_aiming_up:
                img = self.jump_aim_up_r if self.facing_right else self.jump_aim_up_l
            elif self.is_aiming_down:
                img = self.jump_aim_down_r if self.facing_right else self.jump_aim_down_l
            else:
                img = self.jump_frame_r if self.facing_right else self.jump_frame_l
            surface.blit(img, (sx - 24, sy - img.get_height() + 2))
            return

        # 4. Crouching (Ducking Idle, Crawling, or Crouch-Shooting)
        if self.is_crouching:
            if self.is_crouch_shooting:
                img = self.anim_crouch_shoot.get_current_surface()
            elif abs(self.physics.vx) > 0.1:
                img = self.anim_crouch_crawl.get_current_surface()
            else:
                img = self.crouch_idle_r if self.facing_right else self.crouch_idle_l
            if img:
                surface.blit(img, (sx - 24, sy - 46))
            return

        # 5. Aiming Straight UP or Diagonally UP
        if self.is_aiming_up:
            if abs(self.physics.vx) > 0.1:
                img = self.anim_aim_up_run.get_current_surface()
            else:
                img = self.anim_aim_up.get_current_surface()
            if img:
                surface.blit(img, (sx - 24, sy - 46))
            return

        # 6. Running Forward (or Running & Shooting)
        if abs(self.physics.vx) > 0.1:
            anim = self.anim_run_shoot if self.is_run_shooting else self.anim_run
            img = anim.get_current_surface()
            if img:
                surface.blit(img, (sx - 24, sy - 46))
            return

        # 7. Standing Shoot (Recoil & Gunfire Animation)
        if self.is_standing_shooting:
            img = self.anim_shoot.get_current_surface()
            if img:
                surface.blit(img, (sx - 24, sy - 46))
                return

        # 8. Standing Idle
        img = self.anim_idle.get_current_surface()
        if img:
            surface.blit(img, (sx - 24, sy - 46))

    def die(self):
        """Trigger player death state."""
        self.is_dead = True
