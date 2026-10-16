"""
Unified Arcade & Gamepad Input Manager.
Supports 8-way directional controls, Action Buttons A, B, C, Start, and Coin.
Full plug-and-play support for PlayStation 5 DualSense and standard gamepads,
including analog sticks, D-pad, face buttons, shoulder triggers, and hotplugging.
"""
import pygame
from src.config import (
    KEY_BINDINGS, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE, ACTION_START, ACTION_COIN
)

class InputManager:
    # PS5 DualSense and Standard Gamepad Button Mapping
    BUTTON_MAP = {
        0: ACTION_JUMP,     # Cross (PS5) / A (Xbox)
        1: ACTION_GRENADE,  # Circle (PS5) / B (Xbox)
        2: ACTION_SHOOT,    # Square (PS5) / X (Xbox)
        3: ACTION_GRENADE,  # Triangle (PS5) / Y (Xbox)
        4: ACTION_COIN,     # Create/Share (PS5) / Back (Xbox)
        6: ACTION_START,    # Options (PS5) / Start (Xbox)
        7: ACTION_GRENADE,  # L2 (PS5 when reported as digital button)
        8: ACTION_SHOOT,    # R2 (PS5 when reported as digital button)
        9: ACTION_JUMP,     # L1 (PS5) / LB
        10: ACTION_SHOOT,   # R1 (PS5) / RB
        11: ACTION_UP,      # D-pad Up (when reported as button)
        12: ACTION_DOWN,    # D-pad Down
        13: ACTION_LEFT,    # D-pad Left
        14: ACTION_RIGHT,   # D-pad Right
        15: ACTION_COIN,    # Touchpad click (PS5)
    }

    STICK_DEADZONE = 0.35
    TRIGGER_THRESHOLD = 0.2

    def __init__(self):
        self.current_state = {
            ACTION_UP: False,
            ACTION_DOWN: False,
            ACTION_LEFT: False,
            ACTION_RIGHT: False,
            ACTION_SHOOT: False,
            ACTION_JUMP: False,
            ACTION_GRENADE: False,
            ACTION_START: False,
            ACTION_COIN: False,
        }
        self.previous_state = self.current_state.copy()
        self.just_pressed_actions = set()
        self.just_released_actions = set()

        # Track stick analog axes per device
        self._stick_state = {
            ACTION_UP: False,
            ACTION_DOWN: False,
            ACTION_LEFT: False,
            ACTION_RIGHT: False,
        }

        # Track trigger states per device
        self._trigger_state = {
            ACTION_SHOOT: False,
            ACTION_GRENADE: False,
        }

        # Initialize Gamepad Subsystem
        self.joysticks = {}
        if not pygame.joystick.get_init():
            try:
                pygame.joystick.init()
            except Exception as e:
                print(f"[InputManager] Warning initializing joystick subsystem: {e}")

        self._refresh_joysticks()

    def _refresh_joysticks(self):
        """Scans and initializes all currently plugged-in controllers."""
        if not pygame.joystick.get_init():
            return
        count = pygame.joystick.get_count()
        for i in range(count):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                jid = joy.get_instance_id() if hasattr(joy, "get_instance_id") else i
                self.joysticks[jid] = joy
                print(f"[InputManager] Connected Gamepad #{i}: {joy.get_name()} (Axes: {joy.get_numaxes()}, Buttons: {joy.get_numbuttons()})")
            except Exception as e:
                print(f"[InputManager] Error initializing joystick {i}: {e}")

    def _set_action(self, action, is_pressed):
        """Updates action state and tracks single-frame edge triggers."""
        if action not in self.current_state:
            return

        was_pressed = self.current_state[action]
        if is_pressed and not was_pressed:
            self.current_state[action] = True
            self.just_pressed_actions.add(action)
        elif not is_pressed and was_pressed:
            self.current_state[action] = False
            self.just_released_actions.add(action)

    def process_event(self, event):
        """Processes pygame events for keys, gamepads, analog sticks, and hotplugging."""
        # 1. Hotplugging Controller Support
        if event.type == pygame.JOYDEVICEADDED:
            try:
                joy = pygame.joystick.Joystick(event.device_index)
                joy.init()
                jid = joy.get_instance_id() if hasattr(joy, "get_instance_id") else event.device_index
                self.joysticks[jid] = joy
                print(f"[InputManager] Hotplug: Connected {joy.get_name()}")
            except Exception as e:
                print(f"[InputManager] Error on JOYDEVICEADDED: {e}")

        elif event.type == pygame.JOYDEVICEREMOVED:
            try:
                if event.instance_id in self.joysticks:
                    name = self.joysticks[event.instance_id].get_name()
                    del self.joysticks[event.instance_id]
                    print(f"[InputManager] Disconnected: {name}")
            except Exception as e:
                print(f"[InputManager] Error on JOYDEVICEREMOVED: {e}")

        # 2. Keyboard Support
        elif event.type == pygame.KEYDOWN:
            if event.key in KEY_BINDINGS:
                self._set_action(KEY_BINDINGS[event.key], True)
        elif event.type == pygame.KEYUP:
            if event.key in KEY_BINDINGS:
                self._set_action(KEY_BINDINGS[event.key], False)

        # 3. Gamepad Button Support (Cross, Square, Circle, Triangle, Options, Share, L1, R1)
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in self.BUTTON_MAP:
                self._set_action(self.BUTTON_MAP[event.button], True)
        elif event.type == pygame.JOYBUTTONUP:
            if event.button in self.BUTTON_MAP:
                self._set_action(self.BUTTON_MAP[event.button], False)

        # 4. Gamepad D-Pad (Hat) Support
        elif event.type == pygame.JOYHATMOTION:
            hat_x, hat_y = event.value
            self._set_action(ACTION_LEFT, (hat_x < 0))
            self._set_action(ACTION_RIGHT, (hat_x > 0))
            self._set_action(ACTION_UP, (hat_y > 0))
            self._set_action(ACTION_DOWN, (hat_y < 0))

        # 5. Gamepad Analog Stick & Trigger Support
        elif event.type == pygame.JOYAXISMOTION:
            # Left Stick X (Axis 0)
            if event.axis == 0:
                is_left = (event.value < -self.STICK_DEADZONE)
                is_right = (event.value > self.STICK_DEADZONE)
                self._stick_state[ACTION_LEFT] = is_left
                self._stick_state[ACTION_RIGHT] = is_right
                self._set_action(ACTION_LEFT, is_left)
                self._set_action(ACTION_RIGHT, is_right)

            # Left Stick Y (Axis 1)
            elif event.axis == 1:
                is_up = (event.value < -self.STICK_DEADZONE)
                is_down = (event.value > self.STICK_DEADZONE)
                self._stick_state[ACTION_UP] = is_up
                self._stick_state[ACTION_DOWN] = is_down
                self._set_action(ACTION_UP, is_up)
                self._set_action(ACTION_DOWN, is_down)

            # PS5 DualSense L2 Trigger (Axis 4 on Mac/SDL)
            elif event.axis == 4:
                # Triggers rest at -1.0 and reach +1.0 when fully pulled
                is_pulled = (event.value > self.TRIGGER_THRESHOLD)
                self._trigger_state[ACTION_GRENADE] = is_pulled
                self._set_action(ACTION_GRENADE, is_pulled)

            # PS5 DualSense R2 Trigger (Axis 5 on Mac/SDL)
            elif event.axis == 5:
                is_pulled = (event.value > self.TRIGGER_THRESHOLD)
                self._trigger_state[ACTION_SHOOT] = is_pulled
                self._set_action(ACTION_SHOOT, is_pulled)

    def update(self):
        """Called at end of frame to prepare edge triggers for next frame."""
        self.just_pressed_actions.clear()
        self.just_released_actions.clear()
        self.previous_state = self.current_state.copy()

    def is_held(self, action):
        """Returns True if the action is currently pressed down."""
        return self.current_state.get(action, False)

    def is_just_pressed(self, action):
        """Returns True only on the frame the action was pressed."""
        return action in self.just_pressed_actions

    def is_just_released(self, action):
        """Returns True only on the frame the action was released."""
        return action in self.just_released_actions
