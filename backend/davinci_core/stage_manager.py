"""
stage_manager.py - Gestor de escenarios de combate de Street Fighter II y Da Vinci Fighters.
Soporta:
- Carga y ensamble de los 5 escenarios oficiales a partir de los assets Sega Genesis en assets/backgrounds/.
- Mundo expandido a STAGE_WIDTH = 2200 px con soporte para desplazamiento horizontal de cámara (camera_x).
- Público y personajes de fondo 100% animados con colorkey de transparencia (186, 254, 202).
"""

import os
import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y, COLOR_GROUND_LINE
from audio_manager import audio_manager

STAGE_WIDTH = 2200       # Ancho total del escenario en coordenadas de mundo
STAGE_HEIGHT = 720       # Alto del escenario
SPRITE_KEY_COLOR = (186, 254, 202)  # Color verde menta de fondo de los sprite sheets


class BackgroundCharacter:
    """
    Personaje o elemento animado del público de fondo (espectadores, aldeanos, monjes).
    """
    def __init__(self, frames, world_x, world_y, anim_speed=0.15, scale=2.8):
        self.frames = []
        for f in frames:
            w, h = f.get_size()
            if isinstance(scale, (tuple, list)):
                sx, sy = scale
            else:
                sx, sy = scale, scale
            target_w, target_h = int(w * sx), int(h * sy)

            ck = f.get_colorkey()
            if ck is not None:
                alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                temp = f.copy()
                temp.set_colorkey(ck)
                alpha_surf.blit(temp, (0, 0))
                scaled = pygame.transform.scale(alpha_surf, (target_w, target_h))
            else:
                scaled = pygame.transform.scale(f, (target_w, target_h))
            self.frames.append(scaled)
        
        self.world_x = world_x
        self.world_y = world_y
        self.anim_speed = anim_speed
        self.current_frame = 0.0

    def update(self, dt=1.0 / 60.0):
        if self.frames:
            self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)

    def draw(self, screen, camera_x=0):
        if not self.frames:
            return
        frame_idx = int(self.current_frame) % len(self.frames)
        surf = self.frames[frame_idx]
        screen_x = int(self.world_x - camera_x)
        if -surf.get_width() <= screen_x <= SCREEN_WIDTH:
            screen.blit(surf, (screen_x, self.world_y))


class Stage:
    """
    Escenario de combate de Street Fighter II con base recortada y escalada a 2200x720,
    con público animado sobrepuesto y soporte para scrolling de cámara.
    """
    def __init__(self, name, sheet_file, crop_rect, crowd_defs=None, key_color=None, custom_loader=None):
        self.name = name
        self.sheet_file = sheet_file
        self.crop_rect = crop_rect
        self.crowd_defs = crowd_defs or []
        self.key_color = key_color or SPRITE_KEY_COLOR
        self.custom_loader = custom_loader
        self.surface = None
        self.crowd_characters = []
        self.foreground_characters = []
        self._loaded = False

    def load(self):
        """Carga y ensambla el escenario limpio y sus personajes de público animados."""
        if self._loaded and self.surface:
            return

        path = os.path.join("assets", "backgrounds", self.sheet_file)
        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path)
                if pygame.display.get_surface():
                    sheet = sheet.convert()

                # 1. Recortar la escena base limpia
                cropped = sheet.subsurface(self.crop_rect)
                self.surface = pygame.transform.scale(cropped, (STAGE_WIDTH, STAGE_HEIGHT))

                # 2. Extraer sprites del público animado y primer plano
                self.foreground_characters = []
                if self.custom_loader:
                    self.crowd_characters = self.custom_loader(sheet, self)
                else:
                    self.crowd_characters = []
                    for (world_x, world_y, rect_list, speed, scale) in self.crowd_defs:
                        frames = []
                        for rect in rect_list:
                            if isinstance(rect, pygame.Surface):
                                frames.append(rect)
                            elif (rect[0] + rect[2] <= sheet.get_width() and 
                                  rect[1] + rect[3] <= sheet.get_height()):
                                f = sheet.subsurface(rect).copy()
                                f.set_colorkey(self.key_color)
                                frames.append(f)
                        if frames:
                            bg_char = BackgroundCharacter(frames, world_x, world_y, speed, scale)
                            self.crowd_characters.append(bg_char)

                self._loaded = True
            except Exception as e:
                print(f"[Stage] Error cargando escenario {self.sheet_file}: {e}")

    def update(self, dt=1.0 / 60.0, players=None):
        """Actualiza las animaciones del público y elementos interactivos del escenario."""
        for bg_char in self.crowd_characters:
            if hasattr(bg_char, "update_with_players"):
                bg_char.update_with_players(dt, players)
            else:
                bg_char.update(dt)
        for fg_char in self.foreground_characters:
            if hasattr(fg_char, "update_with_players"):
                fg_char.update_with_players(dt, players)
            else:
                fg_char.update(dt)

    def check_interactions(self, players):
        """Comprueba colisiones e interacciones con elementos interactivos del escenario."""
        for bg_char in self.crowd_characters:
            if hasattr(bg_char, "check_collision"):
                bg_char.check_collision(players)
        for fg_char in self.foreground_characters:
            if hasattr(fg_char, "check_collision"):
                fg_char.check_collision(players)

    def reset(self):
        """Restablece el estado de los elementos interactivos del escenario para un nuevo round."""
        for bg_char in self.crowd_characters:
            if hasattr(bg_char, "reset"):
                bg_char.reset()
        for fg_char in self.foreground_characters:
            if hasattr(fg_char, "reset"):
                fg_char.reset()

    def draw(self, screen, camera_x=0):
        """Renderiza el fondo expandido y el público aplicando el desplazamiento horizontal de la cámara."""
        if not self._loaded:
            self.load()

        if self.surface:
            screen.blit(self.surface, (int(-camera_x), 0))
        else:
            screen.fill((30, 30, 45))

        # Dibujar público animado sobre el fondo
        for bg_char in self.crowd_characters:
            bg_char.draw(screen, camera_x)

    def draw_foreground(self, screen, camera_x=0):
        """Renderiza elementos en primer plano (frente a los luchadores), como cercas o rejas."""
        for fg_char in self.foreground_characters:
            fg_char.draw(screen, camera_x)


def _load_balrog_stage_crowd(sheet, stage):
    """
    Carga y ensambla los personajes animados del escenario de Balrog (Las Vegas, USA):
    1. Multitud central y autos clásicos con alternancia rítmica de festejos.
    2. Bailarina de cabaret izquierda (traje violeta y sombrero de copa).
    3. Bailarina de cabaret derecha (traje rojo y sombrero de copa).
    Utiliza colorkey magenta (255, 0, 255) y normalización vertical para evitar vibraciones.
    """
    crowd = []
    magenta = (255, 0, 255)
    sx = STAGE_WIDTH / 512.0
    sy = STAGE_HEIGHT / 224.0

    # 1. Capa de Multitud y Autos Clásicos (3 estados animados)
    try:
        base_cars = sheet.subsurface((96, 592, 328, 88)).copy()
        base_cars.set_colorkey(magenta)

        f1 = base_cars.copy()

        f2 = base_cars.copy()
        s2 = sheet.subsurface((112, 848, 296, 80)).copy()
        s2.set_colorkey(magenta)
        f2.blit(s2, (16, 8))

        f3 = base_cars.copy()
        s3 = sheet.subsurface((112, 936, 296, 80)).copy()
        s3.set_colorkey(magenta)
        f3.blit(s3, (16, 8))

        # Ciclo suave reposo -> festejo -> reposo
        crowd_frames = [f1, f2, f3, f2]
        crowd_char = BackgroundCharacter(
            crowd_frames,
            world_x=int(96 * sx),
            world_y=int(96 * sy),
            anim_speed=0.06,
            scale=(sx, sy)
        )
        crowd.append(crowd_char)
    except Exception as e:
        print(f"[Stage] Error cargando multitud Balrog: {e}")

    # 2. Bailarina de Cabaret Izquierda (Violeta)
    try:
        p_frames = []
        for r, ox, oy in [((13, 764, 35, 76), 2, 4), ((63, 761, 27, 79), 2, 1), ((115, 764, 29, 76), 5, 4)]:
            surf = pygame.Surface((40, 80))
            surf.fill(magenta)
            sub = sheet.subsurface(r).copy()
            sub.set_colorkey(magenta)
            surf.blit(sub, (ox, oy))
            surf.set_colorkey(magenta)
            p_frames.append(surf)

        p_dancer = BackgroundCharacter(
            [p_frames[0], p_frames[1], p_frames[2], p_frames[1]],
            world_x=int(166 * sx),
            world_y=int(106 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(p_dancer)
    except Exception as e:
        print(f"[Stage] Error cargando bailarina violeta Balrog: {e}")

    # 3. Bailarina de Cabaret Derecha (Roja)
    try:
        r_frames = []
        for r, ox, oy in [((152, 764, 29, 76), 4, 4), ((206, 761, 27, 79), 9, 1), ((248, 764, 35, 76), 1, 4)]:
            surf = pygame.Surface((40, 80))
            surf.fill(magenta)
            sub = sheet.subsurface(r).copy()
            sub.set_colorkey(magenta)
            surf.blit(sub, (ox, oy))
            surf.set_colorkey(magenta)
            r_frames.append(surf)

        r_dancer = BackgroundCharacter(
            [r_frames[0], r_frames[1], r_frames[2], r_frames[1]],
            world_x=int(322 * sx),
            world_y=int(106 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(r_dancer)
    except Exception as e:
        print(f"[Stage] Error cargando bailarina roja Balrog: {e}")

    return crowd


def _load_dhalsim_stage_crowd(sheet, stage):
    """
    Carga y ensambla los elementos animados del escenario de Dhalsim (Maharajah Palace, India):
    1. 6 elefantes ceremoniales (3 en el ala izquierda y 3 en el ala derecha):
       - 2 Elefantes interiores (148, 72) a los lados de los pilares de Ganesha (escala 0.90 de profundidad).
       - 2 Elefantes medios (72, 68) en el centro de cada ala con manta ceremonial.
       - 2 Elefantes exteriores (0, 54) en primer plano con gran tocado dorado y canal alfa limpio.
    2. Vasijas ceremoniales a los pies de los elefantes exteriores.
    """
    crowd = []
    magenta = (255, 0, 255)
    sx = STAGE_WIDTH / 512.0
    sy = STAGE_HEIGHT / 216.0

    def extract_alpha_sprite(rect, flip_h=False):
        sub = sheet.subsurface(rect).copy()
        sub.set_colorkey(magenta)
        surf = pygame.Surface(sub.get_size(), pygame.SRCALPHA)
        surf.blit(sub, (0, 0))
        if flip_h:
            surf = pygame.transform.flip(surf, True, False)
        return surf

    def extract_elephant_frames(flip_h=False):
        raw_frames = [
            sheet.subsurface((8, 792, 136, 96)).copy(),
            sheet.subsurface((152, 792, 136, 96)).copy(),
            sheet.subsurface((296, 792, 136, 96)).copy(),
        ]
        alpha_frames = []
        for f in raw_frames:
            surf = pygame.Surface((136, 96), pygame.SRCALPHA)
            for x in range(136):
                for y in range(96):
                    c = f.get_at((x, y))
                    r, g, b = c[:3]
                    is_wall = (r > 90 and g < 90 and b < 60 and (r - g) > 30 and (r - b) > 50)
                    is_floor = (g > 30 and r < 30 and b < 40)
                    is_pillar_steps = (x > 115 and y > 60 and g > 100 and b > 100 and r < 60)
                    if not is_wall and not is_floor and not is_pillar_steps:
                        surf.set_at((x, y), c)
            if flip_h:
                surf = pygame.transform.flip(surf, True, False)
            alpha_frames.append(surf)
        return alpha_frames

    # Extraer fotogramas de elefantes con manta ceremonial
    l_ele_frames = extract_elephant_frames(flip_h=False)
    r_ele_frames = extract_elephant_frames(flip_h=True)

    seq_l = [l_ele_frames[0]] * 32 + [l_ele_frames[1]] * 5 + [l_ele_frames[2]] * 16 + [l_ele_frames[1]] * 5
    seq_r = [r_ele_frames[0]] * 32 + [r_ele_frames[1]] * 5 + [r_ele_frames[2]] * 16 + [r_ele_frames[1]] * 5

    # Paleta exacta del elefante (excluye las columnas verde azuladas y sombras de pared)
    elephant_colors = {
        # Manta dorada / ornamentos
        (247, 214, 0), (231, 198, 0), (198, 148, 0), (181, 132, 0),
        (165, 115, 0), (148, 99, 0), (132, 82, 0), (115, 66, 0),
        (99, 16, 0), (115, 33, 0), (132, 49, 0), (115, 99, 66),
        # Colmillos de marfil
        (239, 239, 247), (231, 231, 247),
        # Piel gris y sombras
        (181, 181, 198), (148, 148, 165), (115, 115, 132), (99, 99, 115),
        (66, 82, 82), (41, 57, 57), (165, 165, 165),
        (99, 82, 82), (49, 66, 66),
    }

    # 1. Elefantes Interiores (Trompeta animada barritando junto a los pilares de Ganesha: 80x96 en 128, 72 y 304, 72)
    try:
        def extract_clean_sub(rect, f_idx):
            sub = sheet.subsurface(rect)
            w, h = sub.get_size()
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            for x in range(w):
                for y in range(h):
                    if f_idx == 0:
                        if x > 48: # Trompa en reposo termina en x=48 (x=104 en base 136)
                            continue
                    elif f_idx == 1:
                        if x > 78 or (x > 48 and y > 70): # Escalones inferiores
                            continue
                    elif f_idx == 2:
                        if x > 71 or (x > 48 and y > 50): # Trompa levantada preservada
                            continue
                    c = sub.get_at((x, y))
                    if c[:3] in elephant_colors:
                        surf.set_at((x, y), c)
            return surf

        in_f0 = extract_clean_sub((8 + 56, 792, 80, 96), 0)
        in_f1 = extract_clean_sub((152 + 56, 792, 80, 96), 1)
        in_f2 = extract_clean_sub((296 + 56, 792, 80, 96), 2)

        in_left_seq = [in_f0] * 32 + [in_f1] * 5 + [in_f2] * 16 + [in_f1] * 5
        ele_in_left = BackgroundCharacter(
            in_left_seq,
            world_x=int(128 * sx),
            world_y=int(72 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_in_left.current_frame = 0.0
        crowd.append(ele_in_left)

        rin_f0 = pygame.transform.flip(in_f0, True, False)
        rin_f1 = pygame.transform.flip(in_f1, True, False)
        rin_f2 = pygame.transform.flip(in_f2, True, False)

        in_right_seq = [rin_f0] * 32 + [rin_f1] * 5 + [rin_f2] * 16 + [rin_f1] * 5
        ele_in_right = BackgroundCharacter(
            in_right_seq,
            world_x=int(304 * sx),
            world_y=int(72 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_in_right.current_frame = 29.0
        crowd.append(ele_in_right)
    except Exception as e:
        print(f"[Stage] Error cargando elefantes interiores Dhalsim: {e}")

    # 2. Elefantes Medios (Con manta ceremonial en 16, 68 y 360, 68)
    try:
        raw0 = sheet.subsurface((8, 792, 136, 96)).copy()
        raw1 = sheet.subsurface((152, 792, 136, 96)).copy()
        raw2 = sheet.subsurface((296, 792, 136, 96)).copy()

        # Crear sprites con máscara limpia del elefante medio
        def make_mid_frames(flip_h=False):
            frames = []
            for f_idx, f in enumerate((raw0, raw1, raw2)):
                surf = pygame.Surface((136, 96), pygame.SRCALPHA)
                for x in range(136):
                    for y in range(96):
                        if f_idx == 0:
                            if x > 104: # Trompa en reposo termina en x=104
                                continue
                        elif f_idx == 1:
                            if x > 134 or (x > 104 and y > 70): # Escalones inferiores
                                continue
                        elif f_idx == 2:
                            if x > 127 or (x > 104 and y > 50): # Trompa levantada preservada
                                continue
                        c = f.get_at((x, y))
                        if c[:3] in elephant_colors:
                            surf.set_at((x, y), c)
                if flip_h:
                    surf = pygame.transform.flip(surf, True, False)
                frames.append(surf)
            return frames

        mid_l_seq_frames = make_mid_frames(flip_h=False)
        mid_r_seq_frames = make_mid_frames(flip_h=True)

        mid_l_seq = [mid_l_seq_frames[0]] * 32 + [mid_l_seq_frames[1]] * 5 + [mid_l_seq_frames[2]] * 16 + [mid_l_seq_frames[1]] * 5
        ele_mid_left = BackgroundCharacter(
            mid_l_seq,
            world_x=int(16 * sx),
            world_y=int(68 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_mid_left.current_frame = 15.0
        crowd.append(ele_mid_left)

        mid_r_seq = [mid_r_seq_frames[0]] * 32 + [mid_r_seq_frames[1]] * 5 + [mid_r_seq_frames[2]] * 16 + [mid_r_seq_frames[1]] * 5
        ele_mid_right = BackgroundCharacter(
            mid_r_seq,
            world_x=int(360 * sx),
            world_y=int(68 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_mid_right.current_frame = 44.0
        crowd.append(ele_mid_right)
    except Exception as e:
        print(f"[Stage] Error cargando elefantes medios Dhalsim: {e}")

    # 3. Elefantes Exteriores (Primer plano, tocado dorado y colmillos en -20, 54 y 404, 54)
    try:
        out_f0 = extract_alpha_sprite((8, 896, 128, 136))
        out_f1 = extract_alpha_sprite((144, 896, 128, 136))
        out_left_seq = [out_f0] * 36 + [out_f1] * 14 + [out_f0] * 10

        ele_out_left = BackgroundCharacter(
            out_left_seq,
            world_x=int(-20 * sx),
            world_y=int(54 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_out_left.current_frame = 30.0
        crowd.append(ele_out_left)

        rout_f0 = extract_alpha_sprite((8, 896, 128, 136), flip_h=True)
        rout_f1 = extract_alpha_sprite((144, 896, 128, 136), flip_h=True)
        out_right_seq = [rout_f0] * 36 + [rout_f1] * 14 + [rout_f0] * 10

        ele_out_right = BackgroundCharacter(
            out_right_seq,
            world_x=int(404 * sx),
            world_y=int(54 * sy),
            anim_speed=0.20,
            scale=(sx, sy)
        )
        ele_out_right.current_frame = 5.0
        crowd.append(ele_out_right)
    except Exception as e:
        print(f"[Stage] Error cargando elefantes exteriores Dhalsim: {e}")

    # 4. Urnas ceremoniales a los pies de los elefantes exteriores en (20, 161) y (468, 161)
    try:
        urn_g = extract_alpha_sprite((8, 752, 24, 32))
        urn_gold_char = BackgroundCharacter(
            [urn_g],
            world_x=int(20 * sx),
            world_y=int(161 * sy),
            anim_speed=0.0,
            scale=(sx, sy)
        )
        crowd.append(urn_gold_char)

        urn_c = extract_alpha_sprite((40, 752, 24, 32))
        urn_clay_char = BackgroundCharacter(
            [urn_c],
            world_x=int(468 * sx),
            world_y=int(161 * sy),
            anim_speed=0.0,
            scale=(sx, sy)
        )
        crowd.append(urn_clay_char)
    except Exception as e:
        print(f"[Stage] Error cargando vasijas ceremoniales Dhalsim: {e}")

    return crowd


class CyclistCharacter:
    """
    Ciclista animado que cruza periódicamente la calle del escenario de Chun-Li (China).
    Alterna entre la ciclista mujer (ropa roja) y el hombre con gafas de sol (ropa verde).
    Pedalea continuamente a través de sus 3 fotogramas mientras recorre la calle horizontalmente hacia adelante.
    """
    def __init__(self, female_frames, male_frames, sx, sy):
        self.female_frames = female_frames
        self.male_frames = male_frames
        self.sx = sx
        self.sy = sy
        self.world_y = int(112 * sy)
        self.speed = 140.0
        self.world_x = -int(120 * sx)
        self.is_active = True
        self.current_type = "male"
        self.frame_index = 0.0
        self.respawn_timer = 2.0

    def update(self, dt=1.0 / 60.0):
        if self.is_active:
            self.world_x += self.speed * dt
            frames = self.female_frames if self.current_type == "female" else self.male_frames
            self.frame_index = (self.frame_index + 8.0 * dt) % len(frames)
            if self.world_x > STAGE_WIDTH + 150:
                self.is_active = False
                self.respawn_timer = 3.5  # Pausa de 3.5 segundos antes de que pase el siguiente ciclista
        else:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.is_active = True
                self.world_x = -int(120 * self.sx)
                self.current_type = "female" if self.current_type == "male" else "male"
                self.frame_index = 0.0

    def draw(self, screen, camera_x=0):
        if not self.is_active:
            return
        frames = self.female_frames if self.current_type == "female" else self.male_frames
        surf = frames[int(self.frame_index) % len(frames)]
        screen_x = int(self.world_x - camera_x)
        if -surf.get_width() <= screen_x <= SCREEN_WIDTH:
            screen.blit(surf, (screen_x, self.world_y))


def _load_chunli_stage_crowd(sheet, stage):
    """
    Carga y ensambla los elementos y personajes animados del escenario de Chun-Li (Beijing/Shanghai, China):
    1. Tienda de comestibles y carnicería con espectadores festejando, carnicero cortando,
       hombre en uniforme militar sosteniendo la gallina viva y gallina enjaulada aleteando.
    2. Cilindro giratorio de la peluquería Shanghai Barber en ciclo continuo de 3 fotogramas.
    3. Muchacha lavando ropa en la tina bajo el caño de agua corriente con vaivén rítmico.
    4. Tráfico de ciclistas (mujer con pantalones rojos y hombre con gafas oscuras) pedaleando hacia adelante.
    """
    crowd = []
    magenta = (255, 0, 255)
    # Escenario recortado a 400x224 (eliminando las bandas negras laterales de x<64 y x>=464)
    sx = STAGE_WIDTH / 400.0
    sy = STAGE_HEIGHT / 224.0

    # 1. Puesto de carnicería, espectadores y gallinas animadas (136x72 px en x=(104-64), y=88)
    try:
        stall_f0 = sheet.subsurface((104, 576, 136, 72)).copy()
        stall_f1 = sheet.subsurface((248, 576, 136, 72)).copy()

        stall_char = BackgroundCharacter(
            [stall_f0, stall_f1],
            world_x=int((104 - 64) * sx),
            world_y=int(88 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(stall_char)
    except Exception as e:
        print(f"[Stage] Error cargando puesto de carnicería y gallinas Chun-Li: {e}")

    # 2. Cilindro giratorio de la peluquería (Barber Pole: 24x56 px en x=(416-64), y=40)
    try:
        pole_f0 = sheet.subsurface((8, 576, 24, 56)).copy()
        pole_f1 = sheet.subsurface((40, 576, 24, 56)).copy()
        pole_f2 = sheet.subsurface((72, 576, 24, 56)).copy()

        pole_char = BackgroundCharacter(
            [pole_f0, pole_f1, pole_f2],
            world_x=int((416 - 64) * sx),
            world_y=int(40 * sy),
            anim_speed=0.15,
            scale=(sx, sy)
        )
        crowd.append(pole_char)
    except Exception as e:
        print(f"[Stage] Error cargando poste de barbería Chun-Li: {e}")

    # 3. Muchacha lavando ropa en la tina de agua (40x40 px en x=(360-64), y=112)
    try:
        girl_f0 = sheet.subsurface((8, 648, 40, 40)).copy()
        girl_f1 = sheet.subsurface((56, 648, 40, 40)).copy()

        girl_char = BackgroundCharacter(
            [girl_f0, girl_f1],
            world_x=int((360 - 64) * sx),
            world_y=int(112 * sy),
            anim_speed=0.10,
            scale=(sx, sy)
        )
        crowd.append(girl_char)
    except Exception as e:
        print(f"[Stage] Error cargando muchacha lavando ropa Chun-Li: {e}")

    # 4. Tráfico de ciclistas volteados horizontalmente para mirar hacia adelante (derecha) al pedalear
    try:
        def extract_cyclist_frame(rect):
            sub = sheet.subsurface(rect).copy()
            sub.set_colorkey(magenta)
            w, h = sub.get_size()
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.blit(sub, (0, 0))
            # Voltear horizontalmente para que el manillar y la rueda delantera apunten hacia la derecha (sentido de marcha)
            flipped = pygame.transform.flip(surf, True, False)
            return pygame.transform.scale(flipped, (int(w * sx), int(h * sy)))

        female_frames = [extract_cyclist_frame((x, 496, 64, 72)) for x in (8, 80, 152)]
        male_frames = [extract_cyclist_frame((x, 496, 64, 72)) for x in (224, 296, 368)]

        cyclist_char = CyclistCharacter(female_frames, male_frames, sx, sy)
        crowd.append(cyclist_char)
    except Exception as e:
        print(f"[Stage] Error cargando ciclistas Chun-Li: {e}")

    return crowd


def _load_zangief_stage_crowd(sheet, stage):
    """
    Carga y ensambla los personajes animados y el alambrado frontal del escenario de Zangief (URSS):
    1. Obrero colgado de la baranda del balcón superior (balanceo de piernas).
    2. Multitud de obreros en la plataforma inferior (festejo, brindis y puños en alto).
    3. Cerca metálica de alambre de rombos en primer plano (frente a los luchadores en la esquina izquierda).
    """
    crowd = []
    sx = STAGE_WIDTH / 416.0
    sy = STAGE_HEIGHT / 216.0

    # 1. Obrero colgado del balcón superior
    try:
        hang_f0 = sheet.subsurface((8, 1056, 56, 32)).copy()
        hang_f1 = sheet.subsurface((72, 1056, 56, 32)).copy()
        catwalk_worker = BackgroundCharacter(
            [hang_f0, hang_f1],
            world_x=int(48 * sx),
            world_y=int(40 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(catwalk_worker)
    except Exception as e:
        print(f"[Stage] Error cargando obrero del balcón de Zangief: {e}")

    # 2. Multitud de obreros en la plataforma inferior
    try:
        crowd_f0 = sheet.subsurface((8, 1104, 72, 64)).copy()
        crowd_f1 = sheet.subsurface((88, 1104, 72, 64)).copy()
        deck_crowd = BackgroundCharacter(
            [crowd_f0, crowd_f1],
            world_x=int(32 * sx),
            world_y=int(88 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(deck_crowd)
    except Exception as e:
        print(f"[Stage] Error cargando multitud de obreros de Zangief: {e}")

    # 3. Alambrado de primer plano (frente a los luchadores)
    try:
        fence_raw = sheet.subsurface((48, 893, 176, 75)).copy()
        fence_raw.set_colorkey((115, 115, 115))
        foreground_fence = BackgroundCharacter(
            [fence_raw],
            world_x=0,
            world_y=int(141 * sy),
            anim_speed=0.0,
            scale=(sx, sy)
        )
        stage.foreground_characters = [foreground_fence]
    except Exception as e:
        print(f"[Stage] Error cargando cerca frontal de Zangief: {e}")

    return crowd


def _load_ken_stage_crowd(sheet, stage):
    """
    Carga y ensambla los pasajeros animados del barco en el escenario de Ken (Battle Harbor, USA):
    1. Pasajeros de la cubierta superior (hombre en bata brindando con su trago y hombre apoyado en la baranda).
    2. Multitud de pasajeros en la cubierta inferior (hombre calvo alzando el puño, hombre de gabardina, mujer saludando rítmicamente, hombre de suéter azul y hombre con abrigo y sombrero azul).
    """
    crowd = []
    sx = STAGE_WIDTH / 416.0
    sy = STAGE_HEIGHT / 208.0

    # 1. Pasajeros de la cubierta superior (2 fotogramas)
    try:
        up_f0 = sheet.subsurface((8, 824, 64, 56)).copy()
        up_f1 = sheet.subsurface((80, 824, 64, 56)).copy()
        upper_passengers = BackgroundCharacter(
            [up_f0, up_f1],
            world_x=int(48 * sx),
            world_y=int(8 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(upper_passengers)
    except Exception as e:
        print(f"[Stage] Error cargando pasajeros superiores de Ken: {e}")

    # 2. Pasajeros de la cubierta inferior (2 fotogramas)
    try:
        low_f0 = sheet.subsurface((152, 824, 120, 48)).copy()
        low_f1 = sheet.subsurface((280, 824, 120, 48)).copy()
        lower_passengers = BackgroundCharacter(
            [low_f0, low_f1],
            world_x=int(88 * sx),
            world_y=int(80 * sy),
            anim_speed=0.08,
            scale=(sx, sy)
        )
        crowd.append(lower_passengers)
    except Exception as e:
        print(f"[Stage] Error cargando multitud inferior de Ken: {e}")

    return crowd


class HondaBathTubWater:
    """
    Simulación y renderizado animado del agua de la bañera (onsen / sentō) de E. Honda:
    1. Superficie de agua con ondulación armónica y destellos cáusticos de luz.
    2. Desborde ('revalsando') auténtico del agua sobre el labio superior de la bañera:
       - No cae en regueros o hilos verticales hacia el suelo (los azulejos inferiores permanecen limpios y secos).
       - Forma una cortina horizontal ondulada con festones (scallops) con brillo blanco superior,
         cuerpo celeste traslúcido y ribete inferior verde menta/cian.
       - Alternancia cíclica entre dos estados auténticos:
         * Estado 0: Desborde reposado con ondas festonadas poco profundas (shallow scallops).
         * Estado 1: Desborde impetuoso con cascada en la esquina izquierda y festones más profundos (deep scallops).
    3. Ondulación y destellos del agua caliente dentro de la tina (en el receptáculo superior).
    """
    def __init__(self, scale_x, scale_y):
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.time = 0.0

        # Coordenadas de mundo de la bañera
        self.tub_x = int(112 * scale_x)
        self.tub_y = int(122 * scale_y)
        self.tub_w = int(208 * scale_x)
        self.tub_h = int(46 * scale_y)

        # Borde superior por donde revalsa el agua
        self.rim_y = int(131 * scale_y)
        self.tub_snes_w = 208

        # Construir fotogramas auténticos del desborde festonado (shallow y deep)
        self.overflow_frames = self._build_overflow_frames()
        self.anim_speed = 0.90  # Ciclo auténtico reposado (~0.90 s por estado, periodo total 1.8 s)
        self.current_frame_idx = 0

    def _build_overflow_frames(self):
        surfaces = []
        w_s = self.tub_snes_w + 2
        h_s = 20

        # Paleta auténtica de agua cristalina / azul hielo (sin tinte verde, B > G > R)
        c_white = (255, 255, 255, 255)
        c_white_soft = (245, 250, 255, 240)
        c_cyan_light = (215, 235, 250, 245)
        c_cyan_mid = (185, 212, 238, 245)
        c_blue_edge = (160, 190, 222, 255)
        c_blue_dark = (145, 175, 210, 255)

        for state in (0, 1):
            snes_surf = pygame.Surface((w_s, h_s), pygame.SRCALPHA)
            if state == 0:
                # Estado 0: Desborde reposado (festones suaves)
                peaks = [16, 54, 94, 134, 174, 204]
                for x in range(self.tub_snes_w):
                    dp = min(abs(x - p) for p in peaks)
                    sc = max(0.0, 1.0 - (dp / 16.0))
                    depth = 1.8 + (sc ** 1.3) * 3.0
                    if x < 6:
                        depth = max(depth, 3.2 - x * 0.3)
                    int_d = max(1, int(round(depth)))
                    for y in range(int_d + 1):
                        if y == 0:
                            snes_surf.set_at((x, y), c_white)
                        elif y == 1:
                            snes_surf.set_at((x, y), c_white_soft if sc < 0.6 else c_white)
                        elif y == int_d:
                            snes_surf.set_at((x, y), c_blue_dark if sc > 0.5 else c_blue_edge)
                        elif y == int_d - 1:
                            snes_surf.set_at((x, y), c_blue_edge if sc > 0.5 else c_cyan_mid)
                        else:
                            snes_surf.set_at((x, y), c_cyan_light)
            else:
                # Estado 1: Desborde con oleada y cascada lateral
                peaks = [20, 60, 102, 146, 188]
                for x in range(self.tub_snes_w):
                    dp = min(abs(x - p) for p in peaks)
                    sc = max(0.0, 1.0 - (dp / 16.0))
                    depth = 3.8 + (sc ** 1.2) * 7.2
                    if x < 14:
                        corner_d = 10.5 - (x * 0.55)
                        depth = max(depth, corner_d)
                    int_d = max(1, int(round(depth)))
                    for y in range(int_d + 1):
                        if y == 0:
                            snes_surf.set_at((x, y), c_white)
                        elif y == 1:
                            snes_surf.set_at((x, y), c_white if (sc > 0.4 or x < 12) else c_white_soft)
                        elif y == int_d:
                            snes_surf.set_at((x, y), c_blue_dark if sc > 0.4 else c_blue_edge)
                        elif y == int_d - 1:
                            snes_surf.set_at((x, y), c_blue_edge)
                        elif y >= int_d - 3:
                            snes_surf.set_at((x, y), c_cyan_mid)
                        else:
                            snes_surf.set_at((x, y), c_cyan_light)

            target_w = int(w_s * self.scale_x)
            target_h = int(h_s * self.scale_y)
            scaled = pygame.transform.scale(snes_surf, (target_w, target_h))
            surfaces.append(scaled)

        return surfaces

    def update(self, dt=1.0 / 60.0):
        self.time += dt
        self.current_frame_idx = int((self.time / self.anim_speed)) % len(self.overflow_frames)

    def draw(self, screen, camera_x=0):
        # 1. Destellos y ondulación del agua interior dentro del receptáculo
        surf_w = int(200 * self.scale_x)
        surf_x1 = int(116 * self.scale_x - camera_x)
        for i in range(5):
            shimmer_phase = self.time * 2.0 + i * 1.5
            shim_x = surf_x1 + int((i / 5.0) * surf_w) + int(math.sin(shimmer_phase) * 8)
            shim_y = self.tub_y + int(4 * self.scale_y) + (i % 2) * 4
            shim_len = int(36 + math.sin(shimmer_phase * 1.5) * 12)
            if 0 <= shim_x <= SCREEN_WIDTH:
                pygame.draw.line(screen, (220, 240, 255), (shim_x, shim_y), (min(SCREEN_WIDTH, shim_x + shim_len), shim_y), 2)

        # 2. Desborde festonado horizontal sobre el labio de la bañera (azulejos inferiores limpios)
        overflow_surf = self.overflow_frames[self.current_frame_idx]
        sx = int(self.tub_x - camera_x)
        sy = self.rim_y
        if -overflow_surf.get_width() <= sx <= SCREEN_WIDTH:
            screen.blit(overflow_surf, (sx, sy))


class HondaCeilingDroplets:
    """
    Simulación auténtica de gotas de agua que caen del techo del baño tradicional:
    1. Formación de gota en las vigas del techo (fotogramas 0, 1, 2).
    2. Caída con aceleración gravitatoria real (fotogramas 3 y 4).
    3. Impacto y salpicadura contra el suelo mojado de azulejos (fotograma 5).
    4. Ondas concéntricas de agua expandiéndose y disipándose en el suelo (fotogramas 6, 7, 8).
    5. Múltiples corrientes independientes distribuidas por el techo (mural, duchas izquierda y derecha).
    """
    def __init__(self, drop_frames, scale_x, scale_y):
        self.drop_frames = drop_frames
        self.scale_x = scale_x
        self.scale_y = scale_y

        self.streams = [
            {"x": int(263 * scale_x), "ceil_y": int(12 * scale_y), "floor_y": int(168 * scale_y), "delay": 0.2},
            {"x": int(98 * scale_x), "ceil_y": int(12 * scale_y), "floor_y": int(166 * scale_y), "delay": 1.4},
            {"x": int(342 * scale_x), "ceil_y": int(12 * scale_y), "floor_y": int(167 * scale_y), "delay": 0.8},
        ]
        self.active_drops = []
        for s in self.streams:
            self.active_drops.append({
                "x": s["x"],
                "ceil_y": s["ceil_y"],
                "floor_y": s["floor_y"],
                "state": "idle",
                "timer": s["delay"],
                "y": s["ceil_y"],
                "vy": 0.0,
                "frame_idx": 0,
                "ripple_timer": 0.0
            })

    def update(self, dt=1.0 / 60.0):
        for drop in self.active_drops:
            st = drop["state"]
            if st == "idle":
                drop["timer"] -= dt
                if drop["timer"] <= 0:
                    drop["state"] = "forming"
                    drop["timer"] = 0.45
                    drop["frame_idx"] = 0
            elif st == "forming":
                drop["timer"] -= dt
                if drop["timer"] > 0.30:
                    drop["frame_idx"] = 0
                elif drop["timer"] > 0.15:
                    drop["frame_idx"] = 1
                elif drop["timer"] > 0:
                    drop["frame_idx"] = 2
                else:
                    drop["state"] = "falling"
                    drop["y"] = drop["ceil_y"] + 10
                    drop["vy"] = 240.0
                    drop["frame_idx"] = 3
            elif st == "falling":
                drop["vy"] += 1200.0 * dt
                drop["y"] += drop["vy"] * dt
                drop["frame_idx"] = 3 if int(drop["y"] / 25) % 2 == 0 else 4
                if drop["y"] >= drop["floor_y"]:
                    drop["y"] = drop["floor_y"]
                    drop["state"] = "splash"
                    drop["frame_idx"] = 5
                    drop["timer"] = 0.08
            elif st == "splash":
                drop["timer"] -= dt
                drop["frame_idx"] = 5
                if drop["timer"] <= 0:
                    drop["state"] = "ripple"
                    drop["ripple_timer"] = 0.28
            elif st == "ripple":
                drop["ripple_timer"] -= dt
                if drop["ripple_timer"] > 0.18:
                    drop["frame_idx"] = 6
                elif drop["ripple_timer"] > 0.09:
                    drop["frame_idx"] = 7
                elif drop["ripple_timer"] > 0:
                    drop["frame_idx"] = 8
                else:
                    drop["state"] = "idle"
                    drop["timer"] = random.uniform(1.2, 3.2)

    def draw(self, screen, camera_x=0):
        for drop in self.active_drops:
            if drop["state"] == "idle":
                continue
            idx = min(drop["frame_idx"], len(self.drop_frames) - 1)
            surf = self.drop_frames[idx]
            sx = int(drop["x"] - camera_x - surf.get_width() // 2)
            sy = int(drop["y"] if drop["state"] == "falling" else (drop["ceil_y"] if drop["state"] == "forming" else drop["floor_y"]))
            if -surf.get_width() <= sx <= SCREEN_WIDTH:
                screen.blit(surf, (sx, sy))


class HondaLanterns:
    """
    Linternas tradicionales japonesas (chōchin) colgando del techo a ambos lados:
    Alternancia suave de luminosidad entre el brillo tenue y la calidez encendida.
    """
    def __init__(self, norm_frame, glow_frame, sx, sy):
        self.norm_frame = norm_frame
        self.glow_frame = glow_frame
        self.sx = sx
        self.sy = sy
        self.time = 0.0
        self.left_x = int(32 * sx)
        self.right_x = int(320 * sx)
        self.y = 0

    def update(self, dt=1.0 / 60.0):
        self.time += dt

    def draw(self, screen, camera_x=0):
        use_glow = (math.sin(self.time * 2.8) > 0.3)
        surf = self.glow_frame if use_glow else self.norm_frame
        for lx in (self.left_x, self.right_x):
            sx = int(lx - camera_x)
            if -surf.get_width() <= sx <= SCREEN_WIDTH:
                screen.blit(surf, (sx, self.y))


def _load_honda_stage_crowd(sheet, stage):
    """
    Carga y ensambla los elementos interactivos y animados del escenario de E. Honda (Baño tradicional sentō, Japón):
    1. Superficie limpia del fondo (eliminando la gota estática original para simulación viva).
    2. Agua de la bañera con olas interiores, destellos cáusticos y desborde ('revalsando') continuo por los azulejos frontales.
    3. Gotas de agua que caen del techo con ciclo completo: formación, caída gravitatoria, salpicadura y ondas en el suelo.
    4. Linternas colgantes japonesas (chōchin) con alternancia y pulsación cálida de luminosidad.
    """
    crowd = []
    sx = STAGE_WIDTH / 384.0
    sy = STAGE_HEIGHT / 208.0

    # Limpiar gota estática del fondo para dar paso a la simulación dinámica
    try:
        if stage.surface:
            raw_w, raw_h = 384, 208
            raw_crop = sheet.subsurface((64, 0, raw_w, raw_h)).copy()
            tile_col = raw_crop.get_at((260, 75))
            for dy in range(74, 80):
                for dx in range(262, 266):
                    raw_crop.set_at((dx, dy), tile_col)
            stage.surface = pygame.transform.scale(raw_crop, (STAGE_WIDTH, STAGE_HEIGHT))
    except Exception as e:
        print(f"[Stage] Nota limpiando gota de fondo de Honda: {e}")

    # 1. Simulación y animación de agua desbordante de la bañera
    try:
        tub_water = HondaBathTubWater(sx, sy)
        crowd.append(tub_water)
    except Exception as e:
        print(f"[Stage] Error cargando agua de bañera de Honda: {e}")

    # 2. Gotas de agua que caen del techo
    try:
        drop_frames = []
        for i in range(9):
            rect = (40 + i * 8, 712, 8, 8)
            sub = sheet.subsurface(rect).copy()
            sub.set_colorkey((255, 0, 255))
            w, h = sub.get_size()
            alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            alpha_surf.blit(sub, (0, 0))
            target_w = max(1, int(w * sx))
            target_h = max(1, int(h * sy))
            scaled = pygame.transform.scale(alpha_surf, (target_w, target_h))
            drop_frames.append(scaled)

        ceiling_drops = HondaCeilingDroplets(drop_frames, sx, sy)
        crowd.append(ceiling_drops)
    except Exception as e:
        print(f"[Stage] Error cargando gotas del techo de Honda: {e}")

    # 3. Linternas japonesas con iluminación cálida
    try:
        def extract_lantern(rx, ry, rw, rh):
            sub = sheet.subsurface((rx, ry, rw, rh)).copy()
            sub.set_colorkey((0, 0, 0))
            alpha_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
            alpha_surf.blit(sub, (0, 0))
            return pygame.transform.scale(alpha_surf, (int(rw * sx), int(rh * sy)))

        l_norm = extract_lantern(224, 744, 56, 120)
        l_glow = extract_lantern(288, 744, 56, 120)
        lanterns = HondaLanterns(l_norm, l_glow, sx, sy)
        crowd.append(lanterns)
    except Exception as e:
        print(f"[Stage] Error cargando linternas de Honda: {e}")

    return crowd


class GuileBreakableCrate:
    """
    Caja de madera destructible en la esquina derecha del hangar de Guile.
    Se destruye en pedazos cuando un luchador es empujado, golpeado, o ataca contra ella,
    emitiendo crujido de madera SFX y dispersando astillas y trozos voladores.
    """
    def __init__(self, intact_surf, break1_surf, broken_surf, splinter_surfs, world_x, world_y, width, height):
        self.intact_surf = intact_surf
        self.break1_surf = break1_surf
        self.broken_surf = broken_surf
        self.splinter_surfs = splinter_surfs
        self.world_x = world_x
        self.world_y = world_y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(world_x, world_y, width, height)

        # Estados: "intact", "breaking", "broken"
        self.state = "intact"
        self.break_timer = 0.0
        self.splinters = []

    def reset(self):
        """Restaura la caja a su estado intacto inicial al reiniciar el round."""
        self.state = "intact"
        self.break_timer = 0.0
        self.splinters = []

    def smash(self):
        """Rompe la caja en pedazos, genera sonido y dispersa las astillas voladoras."""
        if self.state != "intact":
            return
        self.state = "breaking"
        self.break_timer = 0.16  # Duración del primer fotograma de fractura

        # Audio de ruptura contundente de caja de madera
        audio_manager.play_sfx("crate_break")
        audio_manager.play_sfx("wood_smash")

        # Generar astillas físicas voladoras
        self.splinters = []
        center_x = self.world_x + self.width // 2
        center_y = self.world_y + self.height // 2
        floor_y = self.world_y + self.height - 15

        # 4 astillas con distintas trayectorias parabólicas hacia la izquierda y arriba
        initial_trajectories = [
            (-320, -420, 260),   # Gran trozo de madera volando hacia el centro
            (-200, -350, -320),  # Astilla mediana
            (-130, -500, 380),   # Astilla alta
            (90, -330, -220),    # Astilla rebotando a la derecha
        ]
        for i, s_surf in enumerate(self.splinter_surfs):
            idx = i % len(initial_trajectories)
            vx, vy, vrot = initial_trajectories[idx]
            self.splinters.append({
                "x": float(center_x + (i - 1.5) * 20),
                "y": float(center_y - 20),
                "vx": float(vx),
                "vy": float(vy),
                "angle": 0.0,
                "vrot": float(vrot),
                "surf": s_surf,
                "ground_y": float(floor_y),
                "settled": False
            })

    def check_collision(self, players):
        """Verifica si algún jugador colisiona, ataca o es empujado contra la caja."""
        if self.state != "intact" or not players:
            return

        # Hitbox de impacto ligeramente ampliada a la izquierda para captar empujes
        crate_hitbox = pygame.Rect(self.world_x - 30, self.world_y, self.width + 30, self.height)

        for p in players:
            if not p:
                continue
            p_rect = getattr(p, "rect", None)
            if not p_rect:
                p_rect = pygame.Rect(getattr(p, "x", 0), getattr(p, "y", 0), getattr(p, "width", 80), getattr(p, "height", 140))

            # Colisión directa de hurtbox o posición
            collided = p_rect.colliderect(crate_hitbox) or (getattr(p, "x", 0) + getattr(p, "width", 80) >= self.world_x - 15)

            # Hitbox de ataque activo si está golpeando
            active_hb = getattr(p, "active_hitbox", None)
            if active_hb and active_hb.colliderect(crate_hitbox):
                self.smash()
                return

            if collided:
                self.smash()
                return

    def update_with_players(self, dt=1.0 / 60.0, players=None):
        self.update(dt)
        if players:
            self.check_collision(players)

    def update(self, dt=1.0 / 60.0):
        # Transición de rotura
        if self.state == "breaking":
            self.break_timer -= dt
            if self.break_timer <= 0:
                self.state = "broken"

        # Físicas de astillas
        gravity = 1100.0
        for sp in self.splinters:
            if not sp["settled"]:
                sp["x"] += sp["vx"] * dt
                sp["vy"] += gravity * dt
                sp["y"] += sp["vy"] * dt
                sp["angle"] += sp["vrot"] * dt

                if sp["y"] >= sp["ground_y"]:
                    sp["y"] = sp["ground_y"]
                    if abs(sp["vy"]) > 80:
                        sp["vy"] = -sp["vy"] * 0.32
                        sp["vx"] *= 0.6
                        sp["vrot"] *= 0.5
                    else:
                        sp["vy"] = 0
                        sp["vx"] = 0
                        sp["vrot"] = 0
                        sp["settled"] = True

    def draw(self, screen, camera_x=0):
        screen_x = int(self.world_x - camera_x)

        # Dibujar base de la caja según estado
        if self.state == "intact":
            screen.blit(self.intact_surf, (screen_x, self.world_y))
        elif self.state == "breaking":
            b1_y = self.world_y + self.height - self.break1_surf.get_height()
            screen.blit(self.break1_surf, (screen_x, b1_y))
        elif self.state == "broken":
            broken_y = self.world_y + self.height - self.broken_surf.get_height()
            screen.blit(self.broken_surf, (screen_x, broken_y))

        # Dibujar astillas voladoras
        for sp in self.splinters:
            sp_screen_x = int(sp["x"] - camera_x)
            if -50 <= sp_screen_x <= SCREEN_WIDTH + 50:
                if abs(sp["angle"]) > 1.0:
                    rot_surf = pygame.transform.rotate(sp["surf"], sp["angle"])
                    r = rot_surf.get_rect(center=(sp_screen_x, int(sp["y"])))
                    screen.blit(rot_surf, r.topleft)
                else:
                    screen.blit(sp["surf"], (sp_screen_x, int(sp["y"])))


def _load_guile_stage_crowd(sheet, stage):
    """
    Carga y ensambla los elementos interactivos y público del escenario de Guile (USA - Airbase Hangar):
    1. Limpieza del asfalto en la superficie base para que la caja de madera se pueda destruir limpiamente.
    2. Mecánico con gafas oscuras sentado a la izquierda (reposo y festejo alzando el puño).
    3. Pareja de pie a la derecha del F-16 (piloto en mono de vuelo verde y mujer animando).
    4. Caja de madera rompible (GuileBreakableCrate) en la esquina derecha que se rompe al impactar.
    """
    crowd = []
    sx = STAGE_WIDTH / 416.0
    sy = STAGE_HEIGHT / 208.0

    # 1. Limpiar la caja de madera de la superficie base del escenario
    try:
        if stage.surface:
            c_world_x = int(360 * sx)
            c_world_y = int(143 * sy)
            c_w = int(48 * sx)
            c_h = int(48 * sy)
            ref_x = min(STAGE_WIDTH - 1, int(412 * sx))
            for y in range(c_world_y, min(STAGE_HEIGHT, c_world_y + c_h)):
                col = stage.surface.get_at((ref_x, y))
                for x in range(c_world_x, min(STAGE_WIDTH, c_world_x + c_w)):
                    stage.surface.set_at((x, y), col)
    except Exception as e:
        print(f"[Stage] Error limpiando asfalto de caja de Guile: {e}")

    # 2. Mecánico con gafas oscuras sentado a la izquierda (reposo y puño en alto)
    try:
        f1 = sheet.subsurface((8, 1080, 48, 72)).copy()
        f2 = sheet.subsurface((64, 1080, 48, 72)).copy()
        teal = (66, 148, 165)
        # Limpiar sombra donde se movió el brazo en f2
        for x in range(6, 17):
            for y in range(19, 29):
                if f2.get_at((x, y))[:3] == teal:
                    f2.set_at((x, y), (16, 16, 16))
        f1.set_colorkey(teal)
        f2.set_colorkey(teal)

        guy_frames = [f1, f1, f1, f2, f2, f1]
        m_char = BackgroundCharacter(
            guy_frames,
            world_x=int(144 * sx),
            world_y=int(112 * sy),
            anim_speed=0.06,
            scale=(sx, sy)
        )
        crowd.append(m_char)
    except Exception as e:
        print(f"[Stage] Error cargando mecánico sentado de Guile: {e}")

    # 3. Pareja de pie a la derecha (piloto y mujer en falda roja)
    try:
        s1 = sheet.subsurface((120, 1072, 48, 80)).copy()
        s2 = sheet.subsurface((176, 1072, 48, 80)).copy()
        raw = sheet.subsurface((48, 0, 416, 208))
        teal = (66, 148, 165)
        for x in range(30, 48):
            for y in range(80):
                if s2.get_at((x, y))[:3] == teal:
                    s2.set_at((x, y), raw.get_at((328, 104 + y)))
        s1.set_colorkey(teal)
        s2.set_colorkey(teal)

        couple_frames = [s1, s1, s2, s2, s1]
        couple_char = BackgroundCharacter(
            couple_frames,
            world_x=int(280 * sx),
            world_y=int(104 * sy),
            anim_speed=0.07,
            scale=(sx, sy)
        )
        crowd.append(couple_char)
    except Exception as e:
        print(f"[Stage] Error cargando pareja de pie de Guile: {e}")

    # 4. Caja de madera interactiva y rompible (GuileBreakableCrate)
    try:
        def make_clean_alpha_sprite(sub, target_w, target_h):
            w, h = sub.get_size()
            alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            temp = sub.copy()
            temp.set_colorkey((255, 0, 255))
            alpha_surf.blit(temp, (0, 0))
            for x in range(w):
                for y in range(h):
                    if alpha_surf.get_at((x, y))[:3] == (255, 255, 255):
                        alpha_surf.set_at((x, y), (0, 0, 0, 0))
            return pygame.transform.scale(alpha_surf, (target_w, target_h))

        intact = sheet.subsurface((8, 1016, 48, 48))
        intact_scaled = make_clean_alpha_sprite(intact, int(48 * sx), int(48 * sy))

        break1 = sheet.subsurface((120, 1032, 48, 32))
        break1_scaled = make_clean_alpha_sprite(break1, int(48 * sx), int(32 * sy))

        broken = sheet.subsurface((64, 1016, 48, 48))
        broken_scaled = make_clean_alpha_sprite(broken, int(48 * sx), int(48 * sy))

        splinters = []
        for r in [(176, 1016, 16, 16), (200, 1016, 8, 8), (216, 1016, 16, 8), (240, 1016, 8, 16)]:
            sub = sheet.subsurface(r)
            w, h = sub.get_size()
            scaled = make_clean_alpha_sprite(sub, int(w * sx), int(h * sy))
            splinters.append(scaled)

        crate = GuileBreakableCrate(
            intact_surf=intact_scaled,
            break1_surf=break1_scaled,
            broken_surf=broken_scaled,
            splinter_surfs=splinters,
            world_x=int(360 * sx),
            world_y=int(143 * sy),
            width=int(48 * sx),
            height=int(48 * sy)
        )
        crowd.append(crate)
    except Exception as e:
        print(f"[Stage] Error cargando caja rompible de Guile: {e}")

    return crowd


def _load_blanka_stage_crowd(sheet, stage):
    """
    Carga y ensambla los personajes y elementos animados del escenario de Blanka (Cuenca del Amazonas, Brasil):
    1. Base limpia del escenario: limpia la rama del árbol para evitar dobles siluetas fantasma de la anaconda.
    2. Espectadores aldeanos en el muelle / porche de la choza de palafito (animación viva de 2 fotogramas:
       hombre saltando festejando, niño celebrando y aldeano sentado).
    3. Serpiente anaconda gigante enrollada en la rama del árbol banyan a la derecha, con ondulación y
       respiración rítmica en el follaje amazónico.
    """
    crowd = []
    crop_rect = (48, 0, 416, 208)
    sx = STAGE_WIDTH / 416.0
    sy = STAGE_HEIGHT / 208.0

    # 1. Base limpia del escenario
    try:
        raw_crop = sheet.subsurface(crop_rect).copy()
        # En la hoja, la rama limpia sin la serpiente se encuentra en y=224+68=292, x=436 (24x104)
        clean_branch = sheet.subsurface((436, 224 + 68, 24, 104)).copy()
        # Estampar la rama limpia en la posición relativa dentro del recorte (436 - 48 = 388, 68)
        raw_crop.blit(clean_branch, (388, 68))
        stage.surface = pygame.transform.scale(raw_crop, (STAGE_WIDTH, STAGE_HEIGHT))
    except Exception as e:
        print(f"[Stage] Nota limpiando rama de árbol Blanka: {e}")

    # 2. Aldeanos espectadores de la choza amazónica (en x=256, y=120 relativo al recorte, tamaño 112x64)
    try:
        f1_base = raw_crop.subsurface((256, 120, 112, 64)).copy()
        c1_raw = sheet.subsurface((8, 1128, 112, 64))
        c2_raw = sheet.subsurface((128, 1128, 112, 64))
        bg_sky = (115, 181, 247)
        white = (255, 255, 255)

        # Generar fotograma 2 asegurando que los píxeles donde el espectador bajó los brazos
        # muestren el fondo de la choza sin bandas ni siluetas residuales
        f2_surf = f1_base.copy()
        for y in range(64):
            for x in range(112):
                c2 = c2_raw.get_at((x, y))[:3]
                c1 = c1_raw.get_at((x, y))[:3]
                if c2 != bg_sky and c2 != white:
                    f2_surf.set_at((x, y), c2)
                elif c1 != bg_sky and c1 != white:
                    replacement = None
                    for dy in range(1, 15):
                        if y - dy >= 0:
                            c_above = c1_raw.get_at((x, y - dy))[:3]
                            if c_above == bg_sky or c_above == white:
                                replacement = f1_base.get_at((x, y - dy))
                                break
                    if replacement is None:
                        for dx in range(1, 15):
                            if x - dx >= 0:
                                c_left = c1_raw.get_at((x - dx, y))[:3]
                                if c_left == bg_sky or c_left == white:
                                    replacement = f1_base.get_at((x - dx, y))
                                    break
                    if replacement:
                        f2_surf.set_at((x, y), replacement)

        target_w = int(112 * sx)
        target_h = int(64 * sy)
        f1_scaled = pygame.transform.scale(f1_base, (target_w, target_h))
        f2_scaled = pygame.transform.scale(f2_surf, (target_w, target_h))

        villagers = BackgroundCharacter(
            [f1_scaled, f2_scaled],
            world_x=int(256 * sx),
            world_y=int(120 * sy),
            anim_speed=0.08,
            scale=(1.0, 1.0)
        )
        crowd.append(villagers)
    except Exception as e:
        print(f"[Stage] Error cargando aldeanos de Blanka: {e}")

    # 3. Serpiente anaconda gigante enrollada en el árbol (en x=388, y=68 relativo al recorte, tamaño 24x104)
    try:
        snake_raw = sheet.subsurface((8, 1016, 24, 104)).copy()
        magenta = (255, 0, 255)
        snake_base = pygame.Surface((24, 104), pygame.SRCALPHA)
        for y in range(104):
            for x in range(24):
                c = snake_raw.get_at((x, y))
                if c[:3] != magenta:
                    snake_base.set_at((x, y), c)

        # Generar ciclo de ondulación y respiración vertical (offsets en píxeles originales)
        offsets = [0, -1, -2, -1, 0, 1, 2, 1]
        pad_y = 4
        frame_h = 104 + pad_y * 2
        target_snake_w = int(24 * sx)
        target_snake_h = int(frame_h * sy)

        snake_frames = []
        for dy in offsets:
            f_surf = pygame.Surface((24, frame_h), pygame.SRCALPHA)
            f_surf.blit(snake_base, (0, pad_y + dy))
            scaled = pygame.transform.scale(f_surf, (target_snake_w, target_snake_h))
            snake_frames.append(scaled)

        snake_char = BackgroundCharacter(
            snake_frames,
            world_x=int(388 * sx),
            world_y=int((68 - pad_y) * sy),
            anim_speed=0.05,
            scale=(1.0, 1.0)
        )
        crowd.append(snake_char)
    except Exception as e:
        print(f"[Stage] Error cargando anaconda de Blanka: {e}")

    return crowd


class StageManager:
    """
    Gestor de escenarios de los 5 profesores con recortes y animaciones de fondo fieles.
    """
    def __init__(self):
        self.stages = {}
        self._init_stages()

    def _init_stages(self):
        # 1. Carloni - Ryu Stage (Castillo Suzaku, Japón)
        self.stages["carloni"] = Stage(
            name="Carloni Database Dojo (Japan)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Ryu Stage.png",
            crop_rect=(4, 196, 504, 216),
            crowd_defs=[]
        )

        # 2. Cavasso / Guile Stage - Mobile Airbase Hangar (F-16 Falcon & Runway, USA abajo)
        self.stages["guile"] = Stage(
            name="Guile Airbase Hangar (USA)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Guile Stage (World Warrior).png",
            crop_rect=(48, 0, 416, 208),
            custom_loader=_load_guile_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["cavasso"] = self.stages["guile"]
        self.stages["usa_guile"] = self.stages["guile"]
        self.stages["usa_low"] = self.stages["guile"]
        self.stages["airbase"] = self.stages["guile"]
        self.stages["hangar"] = self.stages["guile"]
        self.stages["guile_stage"] = self.stages["guile"]

        # 3. Romero - Sagat Stage (Ruinas de Ayutthaya con Buda reclinado, Tailandia)
        self.stages["romero"] = Stage(
            name="Romero Corporate Ruins (Thailand)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Sagat Stage.png",
            crop_rect=(8, 224, 512, 224),
            crowd_defs=[]
        )

        # 4. Gamaliel - Blanka Stage (Cuenca del Amazonas con aldeanos y serpiente, Brasil)
        self.stages["gamaliel"] = Stage(
            name="Blanka Amazon River (Brazil)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Blanka Stage (World Warrior).png",
            crop_rect=(48, 0, 416, 208),
            custom_loader=_load_blanka_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["brazil"] = self.stages["gamaliel"]
        self.stages["blanka"] = self.stages["gamaliel"]
        self.stages["blanka_stage"] = self.stages["gamaliel"]

        # 5. Sellanes - M. Bison Stage (Templo Real de Tailandia, Bells & Statues)
        self.stages["sellanes"] = Stage(
            name="Sellanes Requirements Palace (Thailand)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - M. Bison Stage.png",
            crop_rect=(8, 880, 512, 224),
            crowd_defs=[
                # Monje / estatua dorada izquierda
                (460, 280, [(8, 184, 24, 168), (40, 184, 24, 168)], 0.08, 2.2),
                # Monje / estatua dorada derecha
                (1680, 280, [(65, 184, 23, 168), (96, 184, 32, 168)], 0.08, 2.2),
            ]
        )

        # 6. Balrog Stage - Las Vegas Strip (Golden Nugget & Nin-Nin Hall, USA)
        self.stages["balrog"] = Stage(
            name="Balrog Las Vegas Strip (USA)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Balrog Stage (World Warrior).png",
            crop_rect=(0, 232, 512, 224),
            custom_loader=_load_balrog_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["usa_balrog"] = self.stages["balrog"]
        self.stages["las_vegas"] = self.stages["balrog"]
        self.stages["vegas"] = self.stages["balrog"]

        # 7. Dhalsim Stage - Maharajah Palace (Altar de Ganesha, 6 Elefantes y Alfombra, India)
        self.stages["dhalsim"] = Stage(
            name="Dhalsim Maharajah Palace (India)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Dhalsim Stage (World Warrior).png",
            crop_rect=(0, 488, 512, 216),
            custom_loader=_load_dhalsim_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["india"] = self.stages["dhalsim"]
        self.stages["india_dhalsim"] = self.stages["dhalsim"]
        self.stages["dhalsim_stage"] = self.stages["dhalsim"]

        # 8. Chun-Li Stage - Beijing/Shanghai Market Street (Carnicería, Gallinas, Peluquería y Ciclistas, China)
        self.stages["chunli"] = Stage(
            name="Chun-Li Market Street (China)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Chun-Li Stage (World Warrior).png",
            crop_rect=(64, 232, 400, 224),
            custom_loader=_load_chunli_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["china"] = self.stages["chunli"]
        self.stages["china_chunli"] = self.stages["chunli"]
        self.stages["chun_li"] = self.stages["chunli"]
        self.stages["chunli_stage"] = self.stages["chunli"]

        # 9. Zangief Stage - Industrial Furnace (URSS / U.S.S.R.)
        self.stages["zangief"] = Stage(
            name="Zangief Industrial Furnace (U.S.S.R.)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Zangief Stage (World Warrior).png",
            crop_rect=(48, 0, 416, 216),
            custom_loader=_load_zangief_stage_crowd,
            key_color=(115, 115, 115)
        )
        self.stages["ussr"] = self.stages["zangief"]
        self.stages["urss"] = self.stages["zangief"]
        self.stages["russia"] = self.stages["zangief"]
        self.stages["zangief_stage"] = self.stages["zangief"]

        # 10. Ken Stage - Battle Harbor / American Port (USA)
        self.stages["ken"] = Stage(
            name="Ken Battle Harbor (USA)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Ken Stage (World Warrior).png",
            crop_rect=(48, 0, 416, 208),
            custom_loader=_load_ken_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["usa_ken"] = self.stages["ken"]
        self.stages["ken_stage"] = self.stages["ken"]
        self.stages["harbor"] = self.stages["ken"]
        self.stages["port"] = self.stages["ken"]
        self.stages["usa"] = self.stages["ken"]
        self.stages["usa_up"] = self.stages["ken"]

        # 11. E. Honda Stage - Traditional Japanese Bathhouse / Sentō (Japan)
        self.stages["honda"] = Stage(
            name="E. Honda Bathhouse (Japan)",
            sheet_file="SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - E.Honda Stage (World Warrior).png",
            crop_rect=(64, 0, 384, 208),
            custom_loader=_load_honda_stage_crowd,
            key_color=(255, 0, 255)
        )
        self.stages["romero"] = self.stages["honda"]
        self.stages["japan_up"] = self.stages["honda"]
        self.stages["japan_honda"] = self.stages["honda"]
        self.stages["bathhouse"] = self.stages["honda"]
        self.stages["sento"] = self.stages["honda"]
        self.stages["ehonda"] = self.stages["honda"]

    def get_stage_for_character(self, char_id):
        """Retorna el escenario recortado correspondiente al personaje o país."""
        stage = self.stages.get(char_id, self.stages["carloni"])
        stage.load()
        return stage

    def get_stage_for_country(self, country):
        """Retorna el escenario correspondiente al país seleccionado."""
        country_lower = str(country).lower()
        if country_lower in ("japan_up", "honda", "ehonda", "bathhouse", "sento", "romero"):
            stage = self.stages["honda"]
        elif country_lower in ("usa_up", "usa", "us", "united states", "eeuu", "ken", "usa_ken", "harbor", "port", "barco"):
            stage = self.stages["ken"]
        elif country_lower in ("usa_low", "guile", "cavasso", "airbase", "hangar", "usa_guile"):
            stage = self.stages["guile"]
        elif country_lower in ("balrog", "las_vegas", "vegas", "usa_balrog"):
            stage = self.stages["balrog"]
        elif country_lower in ("india", "ind", "dhalsim"):
            stage = self.stages["dhalsim"]
        elif country_lower in ("china", "chn", "chunli", "chun_li", "chun-li"):
            stage = self.stages["chunli"]
        elif country_lower in ("ussr", "urss", "russia", "zangief", "soviet"):
            stage = self.stages["zangief"]
        elif country_lower == "japan":
            stage = self.stages["carloni"]
        elif country_lower == "thailand":
            stage = self.stages["romero"]
        elif country_lower == "brazil":
            stage = self.stages["gamaliel"]
        elif country_lower == "spain":
            stage = self.stages["sellanes"]
        else:
            stage = self.stages.get(country_lower, self.stages["carloni"])
        stage.load()
        return stage


# Instancia global del gestor de escenarios
stage_manager = StageManager()
