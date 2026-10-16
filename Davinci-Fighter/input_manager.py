"""
input_manager.py - Gestor unificado de entrada para Joysticks/Gamepads y Teclado en Da Vinci Fighters.

Soporta:
- Detección automática y hot-plugging de mandos (DualSense, Xbox, Switch Pro, genéricos USB).
- Integración transparente con SDL2 GameController y fallback a pygame.joystick.Joystick.
- Mapeo Street Fighter para combate:
    * D-Pad / Stick Izquierdo: Movimiento (Izquierda, Derecha, Salto, Agachado)
    * Botón X / Cuadrado (West): Puño Ligero (Light Punch)
    * Botón Y / Triángulo (North): Puño Fuerte (Heavy Punch)
    * Botón A / Cruz (South): Patada Ligera (Light Kick)
    * Botón B / Círculo (East): Patada Fuerte (Heavy Kick)
    * L1 / LB: Bloqueo (Guard)
    * R1 / RB: Ataque Especial (Special)
    * L2 / LT o R2 / RT o Ambos Gatillos: Ultimate (Super Attack)
- Soporte en menús, intros y Character Select:
    * D-Pad / Stick Izquierdo: Navegación de cuadrícula (Arriba, Abajo, Izquierda, Derecha)
    * Botón A / Cruz / X / Start: Seleccionar / Confirmar / Insertar Crédito
    * Botón B / Círculo / Back: Cancelar / Retroceder
    * Start / Option: Pausa / Start
- Detección independiente para Player 1 (Mando 1) y Player 2 (Mando 2).
"""

import pygame
from typing import Dict, Any, Optional

try:
    from pygame._sdl2 import controller as sdl2_controller
    _SDL2_CONTROLLER_AVAILABLE = True
except Exception:
    _SDL2_CONTROLLER_AVAILABLE = False


class InputManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InputManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.controllers = {}   # instance_id -> Controller or Joystick
        self.player_controllers = {1: None, 2: None}
        self.deadzone = 0.35

        # Seguimiento de botones previos para detectar just_pressed
        self.prev_buttons = {1: {}, 2: {}}
        self.prev_directions = {
            1: {"left": False, "right": False, "up": False, "down": False},
            2: {"left": False, "right": False, "up": False, "down": False},
        }

        self.init()

    def init(self):
        """Inicializa los subsistemas de joystick y controlador."""
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        if _SDL2_CONTROLLER_AVAILABLE and not sdl2_controller.get_init():
            try:
                sdl2_controller.init()
            except Exception as e:
                print(f"[InputManager] Error inicializando sdl2_controller: {e}")

        self.refresh_devices()

    def refresh_devices(self):
        """Escanea mandos conectados y asigna a P1 y P2."""
        self.controllers.clear()
        count = pygame.joystick.get_count()

        for idx in range(count):
            try:
                if _SDL2_CONTROLLER_AVAILABLE and sdl2_controller.is_controller(idx):
                    ctrl = sdl2_controller.Controller(idx)
                    ctrl.init()
                    inst_id = idx  # O el identificador asignado
                    self.controllers[idx] = {"type": "controller", "device": ctrl, "name": ctrl.name}
                else:
                    joy = pygame.joystick.Joystick(idx)
                    joy.init()
                    self.controllers[idx] = {"type": "joystick", "device": joy, "name": joy.get_name()}
            except Exception as e:
                print(f"[InputManager] Error abriendo dispositivo {idx}: {e}")

        # Asignar a jugadores
        dev_indices = sorted(list(self.controllers.keys()))
        self.player_controllers[1] = self.controllers[dev_indices[0]] if len(dev_indices) > 0 else None
        self.player_controllers[2] = self.controllers[dev_indices[1]] if len(dev_indices) > 1 else None

    def handle_device_event(self, event):
        """Maneja eventos de conexión/desconexión de mandos."""
        if event.type in (
            getattr(pygame, "JOYDEVICEADDED", -1),
            getattr(pygame, "JOYDEVICEREMOVED", -1),
            getattr(pygame, "CONTROLLERDEVICEADDED", -1),
            getattr(pygame, "CONTROLLERDEVICEREMOVED", -1),
        ):
            self.refresh_devices()

    def get_player_state(self, player_id: int = 1) -> Dict[str, Any]:
        """
        Lee el estado del mando de un jugador y retorna un diccionario booleano:
        {
            "left": bool,
            "right": bool,
            "jump": bool,
            "crouch": bool,
            "punch_light": bool,
            "punch_heavy": bool,
            "kick_light": bool,
            "kick_heavy": bool,
            "block": bool,
            "special": bool,
            "ultimate": bool,
            "start": bool,
            "select": bool,
            "just_pressed": Dict[str, bool]
        }
        """
        state = {
            "left": False,
            "right": False,
            "jump": False,
            "crouch": False,
            "punch_light": False,
            "punch_heavy": False,
            "kick_light": False,
            "kick_heavy": False,
            "block": False,
            "special": False,
            "ultimate": False,
            "start": False,
            "select": False,
            "just_pressed": {},
        }

        entry = self.player_controllers.get(player_id)
        if not entry:
            return state

        dev = entry["device"]
        is_ctrl = (entry["type"] == "controller")

        if is_ctrl:
            if _SDL2_CONTROLLER_AVAILABLE and not sdl2_controller.get_init():
                try:
                    sdl2_controller.init()
                except Exception:
                    return state

            try:
                # Lectura mediante SDL2 Controller estándar (unificado en todos los SOs)
                axis_x = dev.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32767.0
                axis_y = dev.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32767.0

                d_left = dev.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT) or (axis_x < -self.deadzone)
                d_right = dev.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT) or (axis_x > self.deadzone)
                d_up = dev.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP) or (axis_y < -self.deadzone)
                d_down = dev.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN) or (axis_y > self.deadzone)
            except Exception:
                return state

            # Botones de ataque
            # X (West) = Punch Light (Cuadrado / X)
            # Y (North) = Punch Heavy (Triángulo / Y)
            # A (South) = Kick Light (Cruz / A)
            # B (East) = Kick Heavy (Círculo / B)
            b_x = dev.get_button(pygame.CONTROLLER_BUTTON_X)
            b_y = dev.get_button(pygame.CONTROLLER_BUTTON_Y)
            b_a = dev.get_button(pygame.CONTROLLER_BUTTON_A)
            b_b = dev.get_button(pygame.CONTROLLER_BUTTON_B)

            # Hombros y Gatillos
            lb = dev.get_button(pygame.CONTROLLER_BUTTON_LEFTSHOULDER)
            rb = dev.get_button(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER)
            lt_axis = dev.get_axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT) / 32767.0
            rt_axis = dev.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767.0
            lt = lt_axis > 0.4
            rt = rt_axis > 0.4

            start_btn = dev.get_button(pygame.CONTROLLER_BUTTON_START)
            back_btn = dev.get_button(pygame.CONTROLLER_BUTTON_BACK)

        else:
            # Fallback Joystick nativo
            num_axes = dev.get_numaxes()
            axis_x = dev.get_axis(0) if num_axes > 0 else 0.0
            axis_y = dev.get_axis(1) if num_axes > 1 else 0.0

            num_hats = dev.get_numhats()
            hat_x, hat_y = dev.get_hat(0) if num_hats > 0 else (0, 0)

            d_left = (hat_x < 0) or (axis_x < -self.deadzone)
            d_right = (hat_x > 0) or (axis_x > self.deadzone)
            d_up = (hat_y > 0) or (axis_y < -self.deadzone)
            d_down = (hat_y < 0) or (axis_y > self.deadzone)

            # Botones comunes (DualSense/PS4/Xbox en macOS/Linux/Win)
            # 0: A/Cruz, 1: B/Círculo, 2: X/Cuadrado, 3: Y/Triángulo
            num_buttons = dev.get_numbuttons()
            def get_b(idx):
                return dev.get_button(idx) if idx < num_buttons else 0

            # DualSense en Mac mapping nativo:
            # b0: Cruz/A, b1: Círculo/B, b2: Cuadrado/X, b3: Triángulo/Y
            # b9: L1, b10: R1, b6: Options/Start, b4: Share/Back
            # b11: DPad Up, b12: DPad Down, b13: DPad Left, b14: DPad Right
            if num_buttons >= 15:
                d_up = d_up or bool(get_b(11))
                d_down = d_down or bool(get_b(12))
                d_left = d_left or bool(get_b(13))
                d_right = d_right or bool(get_b(14))

            b_a = bool(get_b(0))
            b_b = bool(get_b(1))
            b_x = bool(get_b(2))
            b_y = bool(get_b(3))
            lb = bool(get_b(9) or get_b(4))
            rb = bool(get_b(10) or get_b(5))
            start_btn = bool(get_b(6) or get_b(7))
            back_btn = bool(get_b(4) or get_b(8))

            lt = False
            rt = False
            if num_axes >= 6:
                lt = dev.get_axis(4) > 0.4
                rt = dev.get_axis(5) > 0.4

        # Configuración exacta solicitada para joystick/gamepad:
        # - Left Joystick / D-Pad: Moverse horizontalmente y agacharse
        # - Cruz / A (South): Salto (Jump)
        # - Triángulo / Y (North): Ataque Especial (Special)
        # - Cuadrado / X (West): Guardia Alta / Bloqueo (Block)
        # - Círculo / B (East): Patadas (Kick Light / Kick Heavy)
        state["left"] = bool(d_left)
        state["right"] = bool(d_right)
        state["jump"] = bool(b_a or d_up)      # Cruz (A) salta (y también stick arriba)
        state["crouch"] = bool(d_down)         # Stick abajo se agacha

        state["block"] = bool(b_x or lb)       # Cuadrado (X) guardia/bloqueo (y L1 opcional)
        state["special"] = bool(b_y or rb)     # Triángulo (Y) ataque especial (y R1 opcional)
        state["kick_light"] = bool(b_b)        # Círculo (B) patada
        state["kick_heavy"] = bool(b_b)        # Círculo (B) patada fuerte
        state["punch_light"] = bool(rb)        # Puño accesible por gatillo/bumper
        state["punch_heavy"] = bool(rb)
        state["ultimate"] = bool(lt or rt)
        state["start"] = bool(start_btn)
        state["select"] = bool(back_btn)

        # Cálculo de just_pressed (flancos ascendentes)
        prev = self.prev_buttons[player_id]
        just_pressed = {}
        for action in [
            "left", "right", "jump", "crouch",
            "punch_light", "punch_heavy", "kick_light", "kick_heavy",
            "block", "special", "ultimate", "start", "select"
        ]:
            val = state[action]
            just_pressed[action] = val and not prev.get(action, False)
            prev[action] = val

        state["just_pressed"] = just_pressed
        return state

    def get_menu_navigation(self) -> Dict[str, bool]:
        """
        Retorna acciones discretas de navegación de menú considerando todos los mandos conectados:
        {
            "up": bool,
            "down": bool,
            "left": bool,
            "right": bool,
            "confirm": bool,
            "cancel": bool,
            "start": bool,
            "coin_p1": bool,
            "coin_p2": bool
        }
        """
        nav = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "confirm": False,
            "cancel": False,
            "start": False,
            "coin_p1": False,
            "coin_p2": False,
        }

        for pid in (1, 2):
            st = self.get_player_state(pid)
            jp = st["just_pressed"]
            if jp.get("left"):
                nav["left"] = True
            if jp.get("right"):
                nav["right"] = True
            if jp.get("jump"):
                nav["up"] = True
            if jp.get("crouch"):
                nav["down"] = True
            if jp.get("punch_light") or jp.get("kick_light") or jp.get("start"):
                nav["confirm"] = True
                if pid == 1:
                    nav["coin_p1"] = True
                else:
                    nav["coin_p2"] = True
            if jp.get("punch_heavy") or jp.get("kick_heavy") or jp.get("select"):
                nav["cancel"] = True
            if jp.get("start"):
                nav["start"] = True

        return nav


# Instancia única accesible globalmente
input_manager = InputManager()
