import pygame
from fighter import Fighter
from settings import CONTROLS_P1, CONTROLS_P2

class Player(Fighter):
    """
    Controlador de luchador por teclado para Player 1 y Player 2 basado en data de personaje.
    """
    def __init__(self, x, y, char_id="carloni", player_id=1):
        super().__init__(x, y, char_id=char_id, player_id=player_id)
        self.controls = CONTROLS_P1 if player_id == 1 else CONTROLS_P2

    def handle_input(self):
        """Lee el teclado utilizando la configuración centralizada de teclas."""
        keys = pygame.key.get_pressed()

        # Movimiento horizontal
        moving = False
        if keys[self.controls["left"]]:
            self.move_left()
            moving = True
        elif keys[self.controls["right"]]:
            self.move_right()
            moving = True

        if not moving:
            self.stop_horizontal()

        # Salto y Agachado
        if keys[self.controls["jump"]]:
            self.jump()

        self.set_crouch(keys[self.controls["crouch"]])

        # Bloqueo
        self.set_block(keys[self.controls["block"]])

        # Ataques básicos
        if keys[self.controls["punch_light"]]:
            self.execute_attack("punch_light")
        elif keys[self.controls["punch_heavy"]]:
            self.execute_attack("punch_heavy")
        elif keys[self.controls["kick_light"]]:
            self.execute_attack("kick_light")
        elif keys[self.controls["kick_heavy"]]:
            self.execute_attack("kick_heavy")

        # Ataques especiales y ultimates
        elif keys[self.controls["special"]]:
            self.execute_attack("special")
        elif keys[self.controls["ultimate"]]:
            self.execute_attack("ultimate")
