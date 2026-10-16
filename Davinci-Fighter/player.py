import pygame
from fighter import Fighter
from settings import CONTROLS_P1, CONTROLS_P2
from input_manager import input_manager

class Player(Fighter):
    """
    Controlador de luchador por teclado y mando (joystick/gamepad) para Player 1 y Player 2.
    """
    def __init__(self, x, y, char_id="carloni", player_id=1):
        super().__init__(x, y, char_id=char_id, player_id=player_id)
        self.controls = CONTROLS_P1 if player_id == 1 else CONTROLS_P2
        self.prev_keys = {}

    def handle_input(self):
        """Lee el teclado y el gamepad utilizando el gestor de entrada."""
        keys = pygame.key.get_pressed()
        pad = input_manager.get_player_state(self.player_id)
        pad_jp = pad.get("just_pressed", {})

        # Movimiento horizontal (teclado OR joystick)
        left_active = keys[self.controls["left"]] or pad.get("left", False)
        right_active = keys[self.controls["right"]] or pad.get("right", False)

        moving = False
        if left_active and not right_active:
            self.move_left()
            moving = True
        elif right_active and not left_active:
            self.move_right()
            moving = True

        if not moving:
            self.stop_horizontal()

        # Salto y Agachado
        jump_active = keys[self.controls["jump"]] or pad.get("jump", False)
        if jump_active:
            self.jump()

        crouch_active = keys[self.controls["crouch"]] or pad.get("crouch", False)
        self.set_crouch(crouch_active)

        # Bloqueo (tecla L o gatillo/bumper del mando)
        block_active = keys[self.controls["block"]] or pad.get("block", False)
        self.set_block(block_active)

        def key_just_pressed(k):
            return keys[k] and not self.prev_keys.get(k, False)

        def action_triggered(action_name):
            k = self.controls.get(action_name)
            k_pressed = key_just_pressed(k) if k is not None else False
            pad_pressed = pad_jp.get(action_name, False)
            return k_pressed or pad_pressed

        # Ataques básicos (activación por flanco de pulsación)
        if action_triggered("punch_light"):
            self.execute_attack("punch_light")
        elif action_triggered("punch_heavy"):
            self.execute_attack("punch_heavy")
        elif action_triggered("kick_light"):
            self.execute_attack("kick_light")
        elif action_triggered("kick_heavy"):
            self.execute_attack("kick_heavy")

        # Ataques especiales y ultimates
        elif action_triggered("special"):
            self.execute_attack("special")
        elif action_triggered("ultimate"):
            self.execute_attack("ultimate")

        # Guardar estado de teclas de ataque para el siguiente frame
        for action in ["punch_light", "punch_heavy", "kick_light", "kick_heavy", "special", "ultimate", "block", "jump"]:
            k = self.controls.get(action)
            if k is not None:
                self.prev_keys[k] = keys[k]

