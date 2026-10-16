import pygame
from settings import SCREEN_WIDTH, GROUND_Y, GRAVITY, JUMP_FORCE, PLAYER_SPEED, COLOR_RED, COLOR_BLUE, COLOR_YELLOW
from stage_manager import STAGE_WIDTH
from animation import AnimationManager
from attack import DEFAULT_ATTACKS
from character_data import get_character_data

class FighterState:
    IDLE = "idle"
    WALK = "walk"
    JUMP = "jump"
    CROUCH = "crouch"
    BLOCK = "block"
    PUNCH_LIGHT = "punch_light"
    PUNCH_HEAVY = "punch_heavy"
    KICK_LIGHT = "kick_light"
    KICK_HEAVY = "kick_heavy"
    SPECIAL = "special"
    ULTIMATE = "ultimate"
    HURT = "hurt"
    KO = "ko"


class Fighter:
    """
    Clase base para luchadores con soporte de mundo expandido (STAGE_WIDTH=2200) y scrolling de cámara.
    """
    def __init__(self, x, y, char_id="carloni", player_id=1):
        char_data = get_character_data(char_id)

        self.char_id = char_data["id"]
        self.name = char_data["name"]
        self.subjects = char_data["subjects"]
        self.max_health = char_data["health"]
        self.health = self.max_health
        self.speed = char_data["speed"]
        self.color = char_data["color"]
        self.quote = char_data["quote"]

        self.x = x
        self.y = y
        self.width = 80
        self.height = 140
        self.player_id = player_id
        self.is_p2 = (player_id == 2)

        # Barra de Ultimate (Special Meter: 0 a 100)
        self.special_meter = 0
        self.max_special_meter = 100

        # Física
        self.velocity_x = 0
        self.velocity_y = 0

        # Estados y Efectos
        self.state = FighterState.IDLE
        self.is_jumping = False
        self.is_crouching = False
        self.is_grounded = True
        self.facing_right = not self.is_p2
        self.stun_timer = 0
        self.is_blocking = False

        self.status_effect = None
        self.status_timer = 0

        # Hurtbox base (en coordenadas absolutas del mundo)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Sistema de Ataques Data-Driven
        self.attacks = dict(char_data["attacks"])
        self.current_attack = None
        self.attack_timer = 0
        self.active_hitbox = None
        self.has_hit_target = False

        # Cargar animaciones
        self.animations = AnimationManager.load_character_animations(
            self.char_id, self.color, self.width, self.height
        )

    def gain_special_meter(self, amount):
        self.special_meter = min(self.max_special_meter, self.special_meter + amount)

    def apply_status_effect(self, effect_name, duration=90):
        self.status_effect = effect_name
        self.status_timer = duration

    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            if self.state in self.animations:
                self.animations[self.state].reset()

    def execute_attack(self, attack_name):
        if self.status_effect in ["rooted", "error"]:
            return

        if attack_name == "ultimate":
            if self.special_meter < self.max_special_meter:
                return
            else:
                self.special_meter = 0

        if self.state in [FighterState.IDLE, FighterState.WALK] and attack_name in self.attacks:
            self.current_attack = self.attacks[attack_name]
            self.attack_timer = 0
            self.has_hit_target = False
            self.active_hitbox = None
            self.velocity_x = 0
            self.set_state(attack_name)

    def take_damage(self, damage, knockback_x, stun_duration):
        if self.state == FighterState.KO:
            return

        self.gain_special_meter(15)

        mult = 1.3 if self.status_effect == "vulnerable" else 1.0
        final_damage = int(damage * mult)

        if self.is_blocking:
            actual_damage = int(final_damage * 0.25)
            self.health = max(0, self.health - actual_damage)
            self.x += knockback_x * 0.3
            if self.health <= 0:
                self.set_state(FighterState.KO)
            return

        self.health = max(0, self.health - final_damage)
        self.x += knockback_x
        self.stun_timer = stun_duration

        self.current_attack = None
        self.active_hitbox = None

        if self.health <= 0:
            self.set_state(FighterState.KO)
        else:
            self.set_state(FighterState.HURT)

    def move_left(self):
        if self.status_effect in ["rooted", "error"]:
            return
        if self.state in [FighterState.IDLE, FighterState.WALK, FighterState.JUMP]:
            self.velocity_x = -self.speed
            if self.is_grounded:
                self.set_state(FighterState.WALK)

    def move_right(self):
        if self.status_effect in ["rooted", "error"]:
            return
        if self.state in [FighterState.IDLE, FighterState.WALK, FighterState.JUMP]:
            self.velocity_x = self.speed
            if self.is_grounded:
                self.set_state(FighterState.WALK)

    def stop_horizontal(self):
        self.velocity_x = 0
        if self.is_grounded and self.state == FighterState.WALK:
            self.set_state(FighterState.IDLE)

    def jump(self):
        if self.status_effect in ["rooted", "error"]:
            return
        if self.is_grounded and self.state not in [FighterState.CROUCH, FighterState.HURT, FighterState.KO]:
            self.velocity_y = JUMP_FORCE
            self.is_grounded = False
            self.is_jumping = True
            self.set_state(FighterState.JUMP)

    def set_crouch(self, crouching):
        if self.status_effect in ["rooted", "error"]:
            return
        if self.is_grounded and self.state in [FighterState.IDLE, FighterState.WALK, FighterState.CROUCH]:
            if crouching:
                self.is_crouching = True
                self.velocity_x = 0
                self.set_state(FighterState.CROUCH)
            else:
                if self.state == FighterState.CROUCH:
                    self.is_crouching = False
                    self.set_state(FighterState.IDLE)

    def set_block(self, blocking):
        if self.status_effect in ["error"]:
            return
        if self.is_grounded and self.state in [FighterState.IDLE, FighterState.WALK, FighterState.BLOCK]:
            self.is_blocking = blocking
            if blocking:
                self.velocity_x = 0
                self.set_state(FighterState.BLOCK)
            else:
                if self.state == FighterState.BLOCK:
                    self.set_state(FighterState.IDLE)

    def face_target(self, target_fighter):
        if target_fighter and self.current_attack is None and self.state not in [FighterState.HURT, FighterState.KO]:
            if self.rect.centerx < target_fighter.rect.centerx:
                self.facing_right = True
            else:
                self.facing_right = False

    def update(self):
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer <= 0:
                self.status_effect = None

        if self.stun_timer > 0:
            self.stun_timer -= 1
            if self.stun_timer <= 0 and self.state == FighterState.HURT:
                self.set_state(FighterState.IDLE)

        if self.state not in [FighterState.HURT, FighterState.KO] and self.status_effect not in ["rooted"]:
            self.x += self.velocity_x

        current_height = self.height // 2 if self.is_crouching else self.height

        if not self.is_grounded:
            self.velocity_y += GRAVITY
        self.y += self.velocity_y

        if self.y + current_height >= GROUND_Y:
            self.y = GROUND_Y - current_height
            self.velocity_y = 0
            self.is_grounded = True
            self.is_jumping = False
            if self.state == FighterState.JUMP:
                self.set_state(FighterState.IDLE)

        # Límites del escenario en coordenadas absolutas del mundo (STAGE_WIDTH = 2200)
        if self.x < 0:
            self.x = 0
        elif self.x + self.width > STAGE_WIDTH:
            self.x = STAGE_WIDTH - self.width

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.rect.width = self.width
        self.rect.height = current_height

        if self.current_attack:
            self.attack_timer += 1
            atk = self.current_attack

            if atk.startup <= self.attack_timer < (atk.startup + atk.active_time):
                self.active_hitbox = atk.get_hitbox_rect(self.rect, self.facing_right)
            else:
                self.active_hitbox = None

            if self.attack_timer >= atk.total_duration:
                self.current_attack = None
                self.active_hitbox = None
                self.set_state(FighterState.IDLE)

        if self.state in self.animations:
            anim = self.animations[self.state]
            anim.update()

    def draw(self, screen, camera_x=0):
        """Renderiza al personaje en pantalla aplicando el desplazamiento de la cámara (camera_x)."""
        screen_x = self.rect.x - camera_x
        screen_y = self.rect.y

        if self.state in self.animations:
            anim = self.animations[self.state]
            frame = anim.get_current_frame(flip_x=not self.facing_right)
            if frame:
                screen.blit(frame, (int(screen_x), int(screen_y)))

        if self.status_effect:
            font = pygame.font.Font(None, 20)
            txt_color = (255, 100, 100) if self.status_effect in ["error", "vulnerable"] else (100, 200, 255)
            lbl = font.render(f"[{self.status_effect.upper()}]", True, txt_color)
            screen.blit(lbl, (int(screen_x + self.width // 2 - lbl.get_width() // 2), int(screen_y - 18)))

        if self.active_hitbox:
            hit_screen_x = self.active_hitbox.x - camera_x
            hit_surface = pygame.Surface((self.active_hitbox.width, self.active_hitbox.height), pygame.SRCALPHA)
            hit_surface.fill((255, 50, 50, 160))
            screen.blit(hit_surface, (int(hit_screen_x), int(self.active_hitbox.y)))
            pygame.draw.rect(screen, COLOR_YELLOW, (int(hit_screen_x), int(self.active_hitbox.y), self.active_hitbox.width, self.active_hitbox.height), 2)
