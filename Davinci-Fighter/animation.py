import os
import pygame

class Animation:
    """
    Representa una secuencia de animación recortada de una Sprite Sheet o generada como fallback.
    Soporta frame_width, frame_height, frame_count, animation_speed, scale y loop.
    """
    def __init__(self, frames, speed=0.15, loop=True):
        self.frames = frames            # Lista de superficies Pygame
        self.speed = speed              # Incremento por frame del reloj
        self.loop = loop                # Si la animación se repite indefinidamente
        self.current_frame_idx = 0.0
        self.finished = False

    def update(self):
        """Avanza la animación según la velocidad configurada."""
        if not self.frames:
            return

        if self.finished and not self.loop:
            return

        self.current_frame_idx += self.speed
        if self.current_frame_idx >= len(self.frames):
            if self.loop:
                self.current_frame_idx = 0.0
            else:
                self.current_frame_idx = len(self.frames) - 1
                self.finished = True

    def reset(self):
        """Reinicia la animación al primer cuadro."""
        self.current_frame_idx = 0.0
        self.finished = False

    def get_current_frame(self, flip_x=False):
        """Obtiene la imagen actual de la animación, aplicando flip horizontal si es necesario."""
        if not self.frames:
            return None
        idx = int(self.current_frame_idx) % len(self.frames)
        frame = self.frames[idx]
        if flip_x:
            return pygame.transform.flip(frame, True, False)
        return frame


class AnimationManager:
    """
    Administra y recorta Sprite Sheets para las distintas acciones de un personaje.
    """
    @staticmethod
    def load_spritesheet(image_path, frame_width, frame_height, frame_count=None, scale=1.0):
        """Recorta frames horizontalmente desde una Sprite Sheet, adaptando frame_count si la imagen es más larga."""
        frames = []
        if os.path.exists(image_path):
            try:
                try:
                    sheet = pygame.image.load(image_path).convert_alpha()
                except Exception:
                    sheet = pygame.image.load(image_path)
                sheet_w, sheet_h = sheet.get_size()

                # Si frame_count está definido y la imagen coincide con ese número de frames
                if frame_count and frame_count > 0:
                    slice_w = sheet_w // frame_count
                    slice_h = sheet_h
                    count_to_use = frame_count
                else:
                    slice_w = frame_width
                    slice_h = frame_height
                    count_to_use = sheet_w // frame_width

                for i in range(count_to_use):
                    rect = pygame.Rect(i * slice_w, 0, slice_w, slice_h)
                    sub_surface = sheet.subsurface(rect)
                    if (slice_w, slice_h) != (frame_width, frame_height) or scale != 1.0:
                        target_size = (int(frame_width * scale), int(frame_height * scale))
                        sub_surface = pygame.transform.smoothscale(sub_surface, target_size)
                    frames.append(sub_surface)
                return frames
            except Exception as e:
                print(f"[AnimationManager] Error cargando spritesheet {image_path}: {e}")

        return None


    @staticmethod
    def create_fallback_frames(state_name, color, width=80, height=140, count=4):
        """
        Genera frames procedurales de desarrollo cuando no existe la Sprite Sheet en disco.
        """
        frames = []
        for i in range(count):
            surf = pygame.Surface((width, height), pygame.SRCALPHA)

            # Modificación de forma según estado para feedback visual claro
            if state_name == "crouch":
                h = height // 2
                rect = pygame.Rect(0, height - h, width, h)
            elif state_name == "jump":
                rect = pygame.Rect(10, 0, width - 20, height - 10)
            elif state_name == "walk":
                bob = (i % 2) * 6
                rect = pygame.Rect(0, bob, width, height - bob)
            elif state_name in ["punch_light", "punch_heavy", "kick_light", "kick_heavy", "special", "ultimate"]:
                rect = pygame.Rect(0, 0, width, height)
                # Dibujar extensión de ataque visual
                attack_color = (255, 230, 80) if "light" in state_name else (255, 100, 50)
                ext_rect = pygame.Rect(width - 20, 30 + (i * 5), 30, 25)
                pygame.draw.rect(surf, attack_color, ext_rect)
            elif state_name == "hurt":
                rect = pygame.Rect(5, 5, width - 10, height - 10)
                color = (255, 80, 80)
            elif state_name == "block":
                rect = pygame.Rect(0, 0, width, height)
                pygame.draw.rect(surf, (100, 200, 255), (width - 15, 20, 15, height - 40))
            else: # idle
                pulse = (i % 2) * 4
                rect = pygame.Rect(0, pulse, width, height - pulse)

            pygame.draw.rect(surf, color, rect)
            pygame.draw.rect(surf, (255, 255, 255), rect, 2)
            frames.append(surf)

        return frames

    @classmethod
    def load_character_animations(cls, char_folder_name, base_color, width=80, height=140, scale=1.0):
        """
        Carga el conjunto completo de animaciones para un personaje.
        """
        states_config = {
            "idle": {"count": 4, "speed": 0.1, "loop": True},
            "walk": {"count": 4, "speed": 0.15, "loop": True},
            "jump": {"count": 2, "speed": 0.1, "loop": False},
            "crouch": {"count": 2, "speed": 0.1, "loop": False},
            "punch_light": {"count": 3, "speed": 0.25, "loop": False},
            "punch_heavy": {"count": 4, "speed": 0.2, "loop": False},
            "kick_light": {"count": 3, "speed": 0.25, "loop": False},
            "kick_heavy": {"count": 4, "speed": 0.2, "loop": False},
            "block": {"count": 2, "speed": 0.1, "loop": True},
            "special": {"count": 4, "speed": 0.2, "loop": False},
            "ultimate": {"count": 6, "speed": 0.15, "loop": False},
            "hurt": {"count": 3, "speed": 0.2, "loop": False},
            "ko": {"count": 4, "speed": 0.1, "loop": False}
        }

        animations = {}
        char_dir = os.path.join("assets", "characters", char_folder_name)

        for state, cfg in states_config.items():
            file_path = os.path.join(char_dir, f"{state}.png")
            # Velocidades calibradas para que el movimiento sea pausado, natural y legible
            is_8frame = (char_folder_name in ("cami", "enith", "martin"))
            count_override = 8 if is_8frame else cfg["count"]
            if is_8frame:
                if state == "idle":
                    anim_speed = 0.08   # Respiración calmada y natural (~1.6s el ciclo completo)
                elif state == "walk":
                    anim_speed = 0.12   # Pasos firmes sin aceleración irreal
                elif state == "crouch":
                    anim_speed = 0.12
                elif state in ("block", "hurt", "ko"):
                    anim_speed = 0.14
                else:
                    anim_speed = 0.12
            else:
                anim_speed = cfg["speed"]
            
            frames = cls.load_spritesheet(
                file_path,
                frame_width=int(width / scale),
                frame_height=int(height / scale),
                frame_count=count_override,
                scale=scale
            )

            if not frames:
                frames = cls.create_fallback_frames(state, base_color, width, height, cfg["count"])

            animations[state] = Animation(frames, speed=anim_speed, loop=cfg["loop"])

        return animations
