"""
Arcade Menu Screens and Results Flow for Metal Slug 1.
Includes:
- Title Screen: Plays the authentic full arcade video recording (Nazca logo,
  Neo-Geo startup, Metal Slug title animation, and complete "How to Play" tutorial).
- Character Select Screen: Features animated standing sprites of Marco Rossi and
  Tarma Roving with squad dossiers and interactive selection.
- Mission Results & P.O.W. Tally Screen.
- Game Over & Continue Screen with countdown.
- Victory Screen.
"""
import os
import pygame
from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, COLOR_HUD_YELLOW, COLOR_HUD_ORANGE,
    COLOR_WHITE, COLOR_BLACK, CHROMA_CYAN
)
from src.engine.sprite_loader import SpriteLoader
from src.engine.animation import Animation

def _safe_convert(surf):
    try:
        return surf.convert()
    except Exception:
        return surf

def _safe_convert_alpha(surf):
    try:
        return surf.convert_alpha()
    except Exception:
        return surf


from src.engine.arcade_font import ArcadeFont

INTRO_FRAMES_DIR = os.path.join("Assets", "frames intro")
INTRO_CACHE_PATH = os.path.join(INTRO_FRAMES_DIR, ".cached_320x224.raw")


class TitleScreen:
    """
    Arcade Intro + Attract Title Screen for Metal Slug 1.

    Plays back the 639 authentic captured frames located in 'Assets/frames intro'
    (frame_001.png .. frame_639.png). No synthetic animation is used.

    Frame map (0-based index):
      0..59     Neo-Geo BIOS (white)
      60..239   NEO-GEO MAX 330 MEGA PRO-GEAR SPEC
      240..289  Fade to black
      290..544  SV-001 cutscene (forest, vulcan, breech, aim, blast)  -> title BGM starts at 290
      545..550  Blasted crater
      551..624  Title screen with blinking INSERT COIN (looped while credits == 0)
      625..629  Black transition
      630..638  PUSH 1P START screen (looped while credits > 0)

    Frames were captured at 30 FPS; the game runs at 60 FPS, so one video frame
    is advanced every 2 game ticks for 1:1 arcade timing.
    """
    # Stage constants kept for compatibility with src/game.py
    STAGE_NEOGEO = 0
    STAGE_GIGA_POWER = 1
    STAGE_FOREST = 2
    STAGE_VULCAN = 3
    STAGE_LOADING = 4
    STAGE_AIM = 5
    STAGE_BLAST = 6
    STAGE_CRATER = 7
    STAGE_TITLE = 8

    FRAME_W = VIRTUAL_WIDTH
    FRAME_H = VIRTUAL_HEIGHT
    TICKS_PER_FRAME = 2

    BGM_START_FRAME = 290
    TITLE_START = 551
    INSERT_COIN_LOOP = (551, 624)
    START_LOOP = (630, 638)
    ATTRACT_RESTART_TICKS = 1800  # ~30 s idle on title -> replay intro

    # Class-level cache: frames are decoded only once per process
    _cached_frames = None

    def __init__(self):
        self.tick = 0
        self.credits = 0
        self.frame_index = 0
        self.frame_tick = 0
        self.stage = self.STAGE_NEOGEO
        self.stage_tick = 0
        self.frames = self._load_frames()
        self.total_frames = len(self.frames)

    # ------------------------------------------------------------------ loading
    @classmethod
    def _load_frames(cls):
        if cls._cached_frames is not None:
            return cls._cached_frames

        w, h = cls.FRAME_W, cls.FRAME_H
        frame_bytes = w * h * 3
        frames = []

        png_files = []
        if os.path.isdir(INTRO_FRAMES_DIR):
            png_files = sorted(
                f for f in os.listdir(INTRO_FRAMES_DIR)
                if f.startswith("frame_") and f.endswith(".png")
            )

        # 1. Fast path: pre-scaled raw cache
        if os.path.exists(INTRO_CACHE_PATH):
            size = os.path.getsize(INTRO_CACHE_PATH)
            if size % frame_bytes == 0 and (not png_files or size // frame_bytes == len(png_files)):
                try:
                    with open(INTRO_CACHE_PATH, "rb") as f:
                        buf = f.read()
                    for i in range(size // frame_bytes):
                        chunk = buf[i * frame_bytes:(i + 1) * frame_bytes]
                        frames.append(_safe_convert(pygame.image.frombytes(chunk, (w, h), "RGB")))
                except Exception as e:
                    print(f"[TitleScreen] Intro cache read failed: {e}")
                    frames = []

        # 2. Slow path: decode PNGs, scale, and rebuild the cache
        if not frames and png_files:
            raw_parts = []
            for name in png_files:
                try:
                    img = pygame.image.load(os.path.join(INTRO_FRAMES_DIR, name))
                    img = pygame.transform.smoothscale(img, (w, h))
                except Exception:
                    img = pygame.Surface((w, h))
                raw_parts.append(pygame.image.tobytes(img, "RGB"))
                frames.append(_safe_convert(img))
            try:
                with open(INTRO_CACHE_PATH, "wb") as f:
                    f.write(b"".join(raw_parts))
            except Exception as e:
                print(f"[TitleScreen] Could not write intro cache: {e}")

        if not frames:
            print("[TitleScreen] WARNING: no intro frames found in 'Assets/frames intro'")
            frames = [pygame.Surface((w, h))]

        cls._cached_frames = frames
        return frames

    # ------------------------------------------------------------------ control
    def _play_title_bgm(self):
        from src.core.sound_manager import SoundManager
        sm = SoundManager()
        if sm:
            sm.play_title_bgm()

    def _sync_stage(self):
        i = self.frame_index
        if i >= self.TITLE_START:
            self.stage = self.STAGE_TITLE
        elif i >= 545:
            self.stage = self.STAGE_CRATER
        elif i >= 495:
            self.stage = self.STAGE_BLAST
        elif i >= 465:
            self.stage = self.STAGE_AIM
        elif i >= 415:
            self.stage = self.STAGE_LOADING
        elif i >= 370:
            self.stage = self.STAGE_VULCAN
        elif i >= 290:
            self.stage = self.STAGE_FOREST
        elif i >= 60:
            self.stage = self.STAGE_GIGA_POWER
        else:
            self.stage = self.STAGE_NEOGEO

    def add_credit(self):
        self.credits += 1
        self.stage_tick = 0
        if self.frame_index >= self.TITLE_START and self.frame_index < self.START_LOOP[0]:
            self.frame_index = self.START_LOOP[0]
            self.frame_tick = 0

    def skip_to_title(self):
        """Immediately skips the attract cutscene to the interactive title screen."""
        self.frame_index = self.START_LOOP[0] if self.credits > 0 else self.TITLE_START
        self.frame_tick = 0
        self.stage_tick = 0
        self._sync_stage()
        self._play_title_bgm()

    def restart_attract(self):
        self.frame_index = 0
        self.frame_tick = 0
        self.stage_tick = 0
        self._sync_stage()
        from src.core.sound_manager import SoundManager
        sm = SoundManager()
        if sm:
            sm.stop_music()

    def update(self):
        self.tick += 1
        self.stage_tick += 1
        self.frame_tick += 1
        if self.frame_tick < self.TICKS_PER_FRAME:
            return
        self.frame_tick = 0

        prev = self.frame_index
        nxt = prev + 1

        if prev < self.TITLE_START:
            # Linear intro playback
            if nxt == self.BGM_START_FRAME:
                self._play_title_bgm()
            if nxt >= self.TITLE_START:
                nxt = self.START_LOOP[0] if self.credits > 0 else self.TITLE_START
                self.stage_tick = 0
        else:
            # Title attract loops
            if self.credits > 0:
                lo, hi = self.START_LOOP
            else:
                lo, hi = self.INSERT_COIN_LOOP
                if self.stage_tick > self.ATTRACT_RESTART_TICKS:
                    self.restart_attract()
                    return
            if nxt < lo or nxt > hi:
                nxt = lo

        self.frame_index = min(nxt, self.total_frames - 1)
        self._sync_stage()

    # ------------------------------------------------------------------ render
    def draw(self, surface):
        idx = max(0, min(self.frame_index, self.total_frames - 1))
        surface.blit(self.frames[idx], (0, 0))


class CharacterSelectScreen:
    def __init__(self):
        self.selected_index = 0  # 0: Marco, 1: Tarma
        self.tick = 0
        self.load_sprites()
        self.font = pygame.font.Font(None, 14)
        self.font_bold = pygame.font.Font(None, 16)
        self.font_title = pygame.font.Font(None, 22)

    def load_sprites(self):
        """Loads animated standing sprites of Marco Rossi and Tarma Roving."""
        try:
            # Marco Rossi
            m_path = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
            m_sheet = SpriteLoader.load_sheet(m_path, colorkey=CHROMA_CYAN)
            m_torso_rects = [(10 + i * 34, 263, 28, 29) for i in range(4)]
            m_torso_frames = SpriteLoader.extract_frames(m_sheet, m_torso_rects, flip_x=False)
            m_legs = SpriteLoader.get_subsurface(m_sheet, 149, 276, 20, 16, flip_x=False)
            
            # Tarma Roving
            t_path = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Tarma Roving.png"
            t_sheet = SpriteLoader.load_sheet(t_path, colorkey=(86, 177, 222))
            t_torso_rects = [(10 + i * 34, 263, 28, 29) for i in range(4)]
            t_torso_frames = SpriteLoader.extract_frames(t_sheet, t_torso_rects, flip_x=False)
            t_legs = SpriteLoader.get_subsurface(t_sheet, 161, 276, 21, 16, flip_x=False)

            # Build composited animated standing frames
            self.marco_frames = []
            for tf in m_torso_frames:
                comp = pygame.Surface((32, 42), pygame.SRCALPHA)
                comp.blit(m_legs, (6, 25))
                comp.blit(tf, (2, 0))
                # Scale 2x for prominent character select display
                scaled = pygame.transform.scale(comp, (64, 84))
                self.marco_frames.append(scaled)

            self.tarma_frames = []
            for tf in t_torso_frames:
                comp = pygame.Surface((32, 42), pygame.SRCALPHA)
                comp.blit(t_legs, (6, 25))
                comp.blit(tf, (2, 0))
                scaled = pygame.transform.scale(comp, (64, 84))
                self.tarma_frames.append(scaled)

            self.anim_marco = Animation(self.marco_frames, frame_duration=8, loop=True)
            self.anim_tarma = Animation(self.tarma_frames, frame_duration=8, loop=True)
        except Exception as e:
            print(f"[CharacterSelect] Error loading character sprites: {e}")
            self.anim_marco = None
            self.anim_tarma = None

    def update(self, input_manager):
        self.tick += 1
        from src.config import ACTION_LEFT, ACTION_RIGHT
        if input_manager.is_just_pressed(ACTION_LEFT):
            self.selected_index = 0
        elif input_manager.is_just_pressed(ACTION_RIGHT):
            self.selected_index = 1

        if self.anim_marco:
            self.anim_marco.update()
        if self.anim_tarma:
            self.anim_tarma.update()

    def get_selected_character(self):
        return "marco" if self.selected_index == 0 else "tarma"

    def draw(self, surface):
        # Dark camo / military command background
        surface.fill((16, 20, 24))

        # Header Title
        title = self.font_title.render("SELECT PLAYER", False, COLOR_HUD_YELLOW)
        surface.blit(title, ((VIRTUAL_WIDTH - title.get_width()) // 2, 12))

        # 1. Marco Rossi Selection Panel
        p1_box = pygame.Rect(25, 34, 130, 145)
        p1_selected = (self.selected_index == 0)
        border_col = COLOR_HUD_YELLOW if p1_selected else (60, 70, 80)
        pygame.draw.rect(surface, (25, 30, 36), p1_box)
        pygame.draw.rect(surface, border_col, p1_box, 2 if not p1_selected else 3)
        
        name1 = self.font_bold.render("1P: MARCO ROSSI", False, COLOR_HUD_YELLOW if p1_selected else (160, 160, 160))
        surface.blit(name1, (p1_box.centerx - name1.get_width() // 2, 42))

        # Marco Sprite Display
        if self.anim_marco:
            m_img = self.anim_marco.get_current_surface()
            if m_img:
                if not p1_selected:
                    dimmed = m_img.copy()
                    dimmed.fill((140, 140, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(dimmed, (p1_box.centerx - 32, 60))
                else:
                    surface.blit(m_img, (p1_box.centerx - 32, 60))

        squad1 = self.font.render("REGULAR ARMY", False, (200, 200, 200))
        surface.blit(squad1, (p1_box.centerx - squad1.get_width() // 2, 155))

        # 2. Tarma Roving Selection Panel
        p2_box = pygame.Rect(165, 34, 130, 145)
        p2_selected = (self.selected_index == 1)
        border_col2 = COLOR_HUD_YELLOW if p2_selected else (60, 70, 80)
        pygame.draw.rect(surface, (25, 30, 36), p2_box)
        pygame.draw.rect(surface, border_col2, p2_box, 2 if not p2_selected else 3)

        name2 = self.font_bold.render("2P: TARMA ROVING", False, COLOR_HUD_YELLOW if p2_selected else (160, 160, 160))
        surface.blit(name2, (p2_box.centerx - name2.get_width() // 2, 42))

        # Tarma Sprite Display
        if self.anim_tarma:
            t_img = self.anim_tarma.get_current_surface()
            if t_img:
                if not p2_selected:
                    dimmed = t_img.copy()
                    dimmed.fill((140, 140, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(dimmed, (p2_box.centerx - 32, 60))
                else:
                    surface.blit(t_img, (p2_box.centerx - 32, 60))

        squad2 = self.font.render("P.F. SQUAD", False, (200, 200, 200))
        surface.blit(squad2, (p2_box.centerx - squad2.get_width() // 2, 155))

        # Control Prompt
        prompt = self.font.render("< LEFT / RIGHT >    [1 / J / ENTER TO CONFIRM]", False, COLOR_HUD_ORANGE)
        surface.blit(prompt, ((VIRTUAL_WIDTH - prompt.get_width()) // 2, 195))

class MissionResultsScreen:
    def __init__(self, mission_num=1, rescued_pows=3, slug_intact=True, score=50000):
        self.mission_num = mission_num
        self.rescued_pows = rescued_pows
        self.slug_intact = slug_intact
        self.score = score
        self.pow_bonus = rescued_pows * 10000
        self.slug_bonus = 100000 if slug_intact else 0
        self.total_score = score + self.pow_bonus + self.slug_bonus
        self.tick = 0
        self.font = pygame.font.Font(None, 14)
        self.font_big = pygame.font.Font(None, 20)

    def update(self):
        self.tick += 1

    def draw(self, surface):
        surface.fill(COLOR_BLACK)
        
        # Header
        head_txt = self.font_big.render(f"MISSION {self.mission_num} COMPLETE", False, COLOR_HUD_YELLOW)
        surface.blit(head_txt, ((VIRTUAL_WIDTH - head_txt.get_width()) // 2, 25))

        # Tally Box
        box = pygame.Rect(30, 55, 260, 120)
        pygame.draw.rect(surface, (200, 160, 0), box, 2)

        # POW Tally
        pow_str = f"RESCUED P.O.W.  x {self.rescued_pows} ... {self.pow_bonus:06d} PTS"
        pow_surf = self.font.render(pow_str, False, COLOR_WHITE)
        surface.blit(pow_surf, (45, 75))

        # Slug Bonus
        slug_str = f"SV-001 TANK BONUS ... {self.slug_bonus:06d} PTS" if self.slug_intact else "SV-001 TANK BONUS ... NONE"
        slug_surf = self.font.render(slug_str, False, COLOR_WHITE)
        surface.blit(slug_surf, (45, 105))

        # Total
        tot_str = f"TOTAL SCORE: {self.total_score:07d} PTS"
        tot_surf = self.font_big.render(tot_str, False, COLOR_HUD_YELLOW)
        surface.blit(tot_surf, (45, 135))

        # Continue prompt
        if (self.tick // 20) % 2 == 0:
            cont = self.font.render("PRESS START / ENTER TO ADVANCE", False, COLOR_HUD_ORANGE)
            surface.blit(cont, ((VIRTUAL_WIDTH - cont.get_width()) // 2, 190))

class GameOverScreen:
    def __init__(self, countdown=9):
        self.countdown = countdown
        self.tick = 0
        self.font_big = pygame.font.Font(None, 32)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 14)

    def update(self):
        self.tick += 1
        if self.tick % 60 == 0 and self.countdown > 0:
            self.countdown -= 1

    def draw(self, surface):
        surface.fill(COLOR_BLACK)

        # GAME OVER title
        go_txt = self.font_big.render("GAME OVER", False, (220, 20, 20))
        gx = (VIRTUAL_WIDTH - go_txt.get_width()) // 2
        surface.blit(go_txt, (gx, 50))

        # Continue prompt with countdown
        cont_txt = self.font_medium.render(f"CONTINUE?   {self.countdown}", False, COLOR_HUD_YELLOW)
        cx = (VIRTUAL_WIDTH - cont_txt.get_width()) // 2
        surface.blit(cont_txt, (cx, 110))

        # Instructions
        prompt = self.font_small.render("PRESS START / ENTER TO CONTINUE", False, COLOR_WHITE)
        px = (VIRTUAL_WIDTH - prompt.get_width()) // 2
        surface.blit(prompt, (px, 160))

class VictoryScreen:
    def __init__(self, final_score=0):
        self.final_score = final_score
        self.tick = 0
        self.font_big = pygame.font.Font(None, 26)
        self.font_medium = pygame.font.Font(None, 16)
        self.font_small = pygame.font.Font(None, 12)

    def update(self):
        self.tick += 1

    def draw(self, surface):
        surface.fill((10, 15, 30))

        # Victory title
        vic_txt = self.font_big.render("PEACE FOREVER!", False, COLOR_HUD_YELLOW)
        vx = (VIRTUAL_WIDTH - vic_txt.get_width()) // 2
        surface.blit(vic_txt, (vx, 35))

        sub_txt = self.font_medium.render("ALL MISSIONS ACCOMPLISHED", False, COLOR_WHITE)
        sx = (VIRTUAL_WIDTH - sub_txt.get_width()) // 2
        surface.blit(sub_txt, (sx, 75))

        score_txt = self.font_medium.render(f"FINAL SCORE: {self.final_score:07d}", False, COLOR_HUD_ORANGE)
        scx = (VIRTUAL_WIDTH - score_txt.get_width()) // 2
        surface.blit(score_txt, (scx, 115))

        congrats = self.font_small.render("REGULAR ARMY PEREGRINE FALCON SQUAD", False, (180, 180, 180))
        cx = (VIRTUAL_WIDTH - congrats.get_width()) // 2
        surface.blit(congrats, (cx, 150))

        if (self.tick // 25) % 2 == 0:
            prompt = self.font_small.render("PRESS START / ENTER TO RETURN TO TITLE", False, COLOR_HUD_YELLOW)
            px = (VIRTUAL_WIDTH - prompt.get_width()) // 2
            surface.blit(prompt, (px, 190))
