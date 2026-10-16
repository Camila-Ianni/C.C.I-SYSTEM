"""
Prisoner of War (P.O.W.) Entity for Metal Slug 1.
Features:
- Tied state (kneeling/bound) or waving arms asking for help.
- Rescue trigger: untied upon bullet impact or player contact.
- Untying rope animation (rope falls away).
- Military salute with 'Thank You!' narrator voice.
- Reaches into shorts to pull weapon/points reward and drop it on the ground.
- Runs away in celebration off-screen (despawns upon leaving camera view).
- Increments rescued POW counter.
"""
import random
import pygame
from src.config import CHROMA_WHITE, VIRTUAL_WIDTH
from src.engine.physics import PhysicsBody
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation
from src.items.pickup import PickupItem

class PrisonerOfWar:
    def __init__(self, x, y, reward_type="H", pow_type="sitting"):
        height = 48 if pow_type == "post" else 28
        self.physics = PhysicsBody(x, y, width=22, height=height)
        self.reward_type = reward_type
        self.pow_type = pow_type
        self.facing_right = True
        self.is_rescued = False
        self.is_dead = False

        # States: 'TIED', 'UNTYING', 'SALUTE', 'GIVE_ITEM', 'RUNNING'
        self.state = "TIED"
        self.state_timer = 0
        self.has_dropped_item = False

        self.load_sprites()

    def load_sprites(self):
        sheet_path = "Assets/Non-Playable Characters/Neo Geo _ NGCD - Metal Slug - Non-Playable Characters - P.O.W.s _ Helpful NPCs.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=CHROMA_WHITE)

        # 1. Tied Animation (Sitting on ground or Tied to wooden post)
        if self.pow_type == "post":
            tied_rects = [
                (6, 126, 33, 64),
                (42, 126, 33, 64),
                (78, 126, 35, 64),
                (117, 126, 35, 64)
            ]
        else:
            tied_rects = [
                (5, 25, 32, 29),
                (38, 25, 33, 29),
                (72, 25, 38, 29),
                (111, 25, 39, 29),
                (151, 25, 39, 29)
            ]
        self.tied_frames = SpriteLoader.extract_frames(sheet, tied_rects, flip_x=False)

        # 2. Untying Ropes (Bursting free)
        untying_rects = [
            (197, 19, 40, 35),
            (238, 19, 42, 35),
            (281, 19, 38, 35),
            (326, 17, 32, 37)
        ]
        self.untying_frames = SpriteLoader.extract_frames(sheet, untying_rects, flip_x=False)

        # 3. Military Salute (Thank you!)
        salute_rects = [
            (5, 440, 23, 40),
            (29, 440, 24, 40),
            (54, 440, 26, 40),
            (81, 440, 33, 40),
            (115, 440, 34, 40)
        ]
        self.salute_frames = SpriteLoader.extract_frames(sheet, salute_rects, flip_x=False)

        # 4. Give Item (Full 11-frame sequence: digging into shorts, pulling out cloth/gift with arc swoosh)
        give_rects = [
            (5, 397, 22, 40),
            (28, 397, 24, 40),
            (53, 397, 27, 40),
            (81, 397, 27, 40),
            (109, 397, 23, 40),
            (133, 397, 23, 40),
            (157, 397, 35, 40),
            (193, 397, 42, 40),
            (236, 397, 46, 40),
            (283, 397, 44, 40),
            (328, 397, 44, 40)
        ]
        self.give_frames = SpriteLoader.extract_frames(sheet, give_rects, flip_x=False)

        # 5. Running Away Celebrating (12 full lossless animated frames)
        run_rects = [
            (5, 244, 35, 43), (41, 244, 36, 43), (78, 244, 31, 43), (110, 244, 23, 43),
            (134, 244, 21, 43), (156, 244, 25, 43), (182, 244, 32, 43), (215, 244, 27, 43),
            (243, 244, 24, 43), (268, 244, 24, 43), (293, 244, 32, 43), (326, 244, 35, 43)
        ]
        # Raw sheet frames face LEFT -> flip_x=False is LEFT, flip_x=True is RIGHT
        self.run_frames_l = SpriteLoader.extract_frames(sheet, run_rects, flip_x=False)
        self.run_frames_r = SpriteLoader.extract_frames(sheet, run_rects, flip_x=True)

        self.anim_tied = Animation(self.tied_frames, frame_duration=10, loop=True)
        self.anim_untying = Animation(self.untying_frames, frame_duration=6, loop=False)
        self.anim_salute = Animation(self.salute_frames, frame_duration=7, loop=False)
        self.anim_give = Animation(self.give_frames, frame_duration=4, loop=False)
        self.anim_run_l = Animation(self.run_frames_l, frame_duration=4, loop=True)
        self.anim_run_r = Animation(self.run_frames_r, frame_duration=4, loop=True)

    def trigger_rescue(self, sound_manager=None):
        """Called when shot or touched by player."""
        if self.is_rescued:
            return False
        self.is_rescued = True
        self.state = "UNTYING"
        self.state_timer = 24
        self.anim_untying.reset()
        if sound_manager is None:
            from src.core.sound_manager import SoundManager
            sound_manager = SoundManager()
        if sound_manager:
            sound_manager.play_pow_thank_you()
        return True

    def update(self, player, platforms=None, pickups=None, sound_manager=None, camera=None):
        if self.is_dead:
            return

        self.physics.apply_gravity()
        self.physics.update_movement(platforms)

        # 1. Tied State (Waiting to be freed by gunshot or knife melee)
        if not self.is_rescued:
            self.anim_tied.update()
            return

        # 2. Rescued State Machine: UNTYING -> GIVE_ITEM -> SALUTE -> RUNNING
        if self.state == "UNTYING":
            self.anim_untying.update()
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "GIVE_ITEM"
                self.state_timer = 44
                self.anim_give.reset()

        elif self.state == "GIVE_ITEM":
            self.anim_give.update()
            self.state_timer -= 1
            # Drop reward item when cloth is pulled out from shorts (around tick 18)
            if self.state_timer <= 20 and not self.has_dropped_item and pickups is not None:
                self.has_dropped_item = True
                drop_x = self.physics.x + 14
                drop_y = self.physics.y - 12
                pickups.append(PickupItem(drop_x, drop_y, item_type=self.reward_type))
            elif self.state_timer <= 0:
                self.state = "SALUTE"
                self.state_timer = 35
                self.anim_salute.reset()

        elif self.state == "SALUTE":
            self.anim_salute.update()
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "RUNNING"
                # Run towards left screen exit
                self.physics.vx = -2.2

        elif self.state == "RUNNING":
            if self.physics.vx < 0:
                self.anim_run_l.update()
            else:
                self.anim_run_r.update()

            # Despawn once safely off-screen relative to camera
            if camera:
                sx, sy = camera.apply(self.physics.x, self.physics.y)
                if sx < -40 or sx > VIRTUAL_WIDTH + 40:
                    self.is_dead = True
            elif self.physics.x < -50:
                self.is_dead = True

    def draw(self, surface, camera):
        if self.is_dead:
            return

        sx, sy = camera.apply(self.physics.x, self.physics.y)

        if self.state == "TIED":
            img = self.anim_tied.get_current_surface()
        elif self.state == "UNTYING":
            img = self.anim_untying.get_current_surface()
        elif self.state == "SALUTE":
            img = self.anim_salute.get_current_surface()
        elif self.state == "GIVE_ITEM":
            img = self.anim_give.get_current_surface()
        else:
            img = self.anim_run_l.get_current_surface() if self.physics.vx < 0 else self.anim_run_r.get_current_surface()

        if img:
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height()))
