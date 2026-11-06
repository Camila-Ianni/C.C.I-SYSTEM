"""
mobile/touch_controls.py - Mando táctil virtual transparente (Virtual Gamepad Overlay).
Diseñado para la adaptación de C.C.I. SYSTEM a pantallas táctiles y dispositivos Android (Módulo D).
100% Python con Pygame-CE, soporta eventos multitáctiles nativos SDL2 (FINGERDOWN/UP/MOTION),
zonas de tacto dinámicas, detección de muesca/notch y auto-ocultación al conectar gamepad Bluetooth.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set
import pygame


class VirtualTouchGamepad:
    """Mando virtual multitáctil semitransparente con D-Pad y botones de acción."""

    def __init__(self, screen_w: int = 1280, screen_h: int = 720, layout: str = "arcade"):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.layout = layout  # "arcade" (6 botones), "standard" (4 botones), "simple" (2 botones)
        self.enabled: bool = True
        self.visible: bool = True
        self.hardware_gamepad_connected: bool = False

        # Configuración visual
        self.alpha = 140  # Semitransparencia para ver el gameplay debajo
        self.color_base = (30, 35, 45, self.alpha)
        self.color_active = (0, 240, 255, 210)  # Cyan brillante al tocar
        self.color_border = (180, 190, 210, self.alpha)

        # Estado de botones activos (touch finger_id -> control_name)
        self._touch_map: Dict[int, str] = {}
        self.active_controls: Set[str] = set()

        self._init_geometry()

    def _init_geometry(self):
        """Calcula las áreas táctiles respetando áreas seguras (safe areas)."""
        sw, sh = self.screen_w, self.screen_h
        scale = min(sw / 1280.0, sh / 720.0)

        # 1. D-Pad en esquina inferior izquierda
        self.dpad_radius = int(85 * scale)
        self.dpad_center = (int(130 * scale), sh - int(130 * scale))
        self.dpad_deadzone = int(25 * scale)

        # 2. Botón de Pausa / Menú en la parte superior central
        self.pause_rect = pygame.Rect(sw // 2 - int(45 * scale), int(15 * scale), int(90 * scale), int(36 * scale))

        # 3. Botones de acción en esquina inferior derecha
        self.button_radius = int(32 * scale)
        self.buttons: Dict[str, tuple[int, int]] = {}

        bx = sw - int(140 * scale)
        by = sh - int(130 * scale)
        step = int(68 * scale)

        if self.layout == "arcade":
            # Layout Street Fighter / Da Vinci Fighters: 3 golpes arriba, 3 patadas abajo
            self.buttons["punch_light"] = (bx - step, by - step // 2)
            self.buttons["punch_medium"] = (bx, by - step // 2)
            self.buttons["punch_heavy"] = (bx + step, by - step // 2)

            self.buttons["kick_light"] = (bx - step, by + step // 2)
            self.buttons["kick_medium"] = (bx, by + step // 2)
            self.buttons["kick_heavy"] = (bx + step, by + step // 2)
        elif self.layout == "standard":
            # Layout diamante A, B, X, Y
            self.buttons["btn_a"] = (bx, by + step)
            self.buttons["btn_b"] = (bx + step, by)
            self.buttons["btn_x"] = (bx - step, by)
            self.buttons["btn_y"] = (bx, by - step)
        else:
            # Layout simple 2 botones (Mario, Space Invaders, Asteroids)
            self.buttons["btn_a"] = (bx + int(step * 0.6), by)
            self.buttons["btn_b"] = (bx - int(step * 0.6), by)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Procesa eventos táctiles nativos de SDL2 y eventos de mouse."""
        if not self.enabled:
            return

        # 1. Eventos multitáctiles nativos de SDL2 (Android / iOS)
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            # En Pygame FINGERDOWN da coordenadas normalizadas [0.0, 1.0]
            px = int(event.x * self.screen_w)
            py = int(event.y * self.screen_h)
            self._process_touch_press(event.finger_id, px, py)

        elif event.type == pygame.FINGERUP:
            self._process_touch_release(event.finger_id)

        # 2. Fallback de mouse para pruebas en simulador/escritorio
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._process_touch_press(-1, event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            self._process_touch_press(-1, event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEBUTTONUP:
            self._process_touch_release(-1)

        # 3. Detección automática de gamepad Bluetooth/USB: auto-ocultar overlay si hay mando físico
        elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self.hardware_gamepad_connected = (pygame.joystick.get_count() > 0)
            self.visible = not self.hardware_gamepad_connected

    def _process_touch_press(self, finger_id: int, x: int, y: int):
        """Asigna un toque a los hitboxes de D-Pad o botones."""
        prev_ctrl = self._touch_map.get(finger_id)
        if prev_ctrl in self.active_controls:
            self.active_controls.remove(prev_ctrl)

        matched_control = None

        # Comprobar D-Pad
        dx = x - self.dpad_center[0]
        dy = y - self.dpad_center[1]
        dist = math.hypot(dx, dy)
        if dist <= self.dpad_radius * 1.3:
            if dist >= self.dpad_deadzone:
                angle = math.degrees(math.atan2(dy, dx)) % 360
                # Mapeo angular a direcciones
                if 337.5 <= angle or angle < 22.5:
                    matched_control = "right"
                elif 22.5 <= angle < 67.5:
                    matched_control = "down_right"
                elif 67.5 <= angle < 112.5:
                    matched_control = "down"
                elif 112.5 <= angle < 157.5:
                    matched_control = "down_left"
                elif 157.5 <= angle < 202.5:
                    matched_control = "left"
                elif 202.5 <= angle < 247.5:
                    matched_control = "up_left"
                elif 247.5 <= angle < 292.5:
                    matched_control = "up"
                elif 292.5 <= angle < 337.5:
                    matched_control = "up_right"

        # Comprobar botones de acción
        if not matched_control:
            for btn_name, (bx, by) in self.buttons.items():
                if math.hypot(x - bx, y - by) <= self.button_radius * 1.25:
                    matched_control = btn_name
                    break

        # Comprobar botón de pausa
        if not matched_control and self.pause_rect.collidepoint(x, y):
            matched_control = "pause"

        if matched_control:
            self._touch_map[finger_id] = matched_control
            self.active_controls.add(matched_control)

    def _process_touch_release(self, finger_id: int):
        """Libera el botón al levantar el dedo."""
        ctrl = self._touch_map.pop(finger_id, None)
        if ctrl and ctrl in self.active_controls:
            self.active_controls.remove(ctrl)

    def is_pressed(self, control_name: str) -> bool:
        """Verifica si un control táctil específico está presionado actualmente."""
        if control_name in self.active_controls:
            return True
        # Casos compuestos de D-Pad
        if control_name.startswith("dpad_"):
            return self.is_pressed(control_name[5:])
        if control_name == "left" and any(c in self.active_controls for c in ("left", "up_left", "down_left")):
            return True
        if control_name == "right" and any(c in self.active_controls for c in ("right", "up_right", "down_right")):
            return True
        if control_name == "up" and any(c in self.active_controls for c in ("up", "up_left", "up_right")):
            return True
        if control_name == "down" and any(c in self.active_controls for c in ("down", "down_left", "down_right")):
            return True
        return False

    def set_hardware_gamepad_connected(self, connected: bool) -> None:
        """Actualiza el estado de presencia de un gamepad físico y conmuta visibilidad."""
        self.hardware_gamepad_connected = connected
        self.visible = not connected

    def render(self, surface: pygame.Surface) -> None:
        """Alias para draw()."""
        self.draw(surface)

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja el overlay semitransparente con feedback luminoso de pulsación."""
        if not self.visible or not self.enabled:
            return

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)

        # 1. Dibujar D-Pad
        dpad_color = self.color_active if any("down" in c or "up" in c or "left" in c or "right" in c for c in self.active_controls) else self.color_base
        pygame.draw.circle(overlay, dpad_color, self.dpad_center, self.dpad_radius)
        pygame.draw.circle(overlay, self.color_border, self.dpad_center, self.dpad_radius, 2)
        pygame.draw.circle(overlay, (20, 22, 28, 180), self.dpad_center, self.dpad_deadzone)

        # Cruz direccional interior
        cx, cy = self.dpad_center
        arm = int(self.dpad_radius * 0.7)
        thick = int(self.dpad_deadzone * 1.1)
        pygame.draw.rect(overlay, (255, 255, 255, 60), (cx - arm, cy - thick // 2, arm * 2, thick), border_radius=4)
        pygame.draw.rect(overlay, (255, 255, 255, 60), (cx - thick // 2, cy - arm, thick, arm * 2), border_radius=4)

        # 2. Dibujar Botones de Acción
        for btn_name, (bx, by) in self.buttons.items():
            is_down = (btn_name in self.active_controls)
            color = self.color_active if is_down else self.color_base
            pygame.draw.circle(overlay, color, (bx, by), self.button_radius)
            pygame.draw.circle(overlay, self.color_border, (bx, by), self.button_radius, 2)

        # 3. Dibujar Botón de Pausa
        pause_color = self.color_active if "pause" in self.active_controls else self.color_base
        pygame.draw.rect(overlay, pause_color, self.pause_rect, border_radius=6)
        pygame.draw.rect(overlay, self.color_border, self.pause_rect, 2, border_radius=6)

        surface.blit(overlay, (0, 0))
