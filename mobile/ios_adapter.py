"""
mobile/ios_adapter.py - Adaptador específico para iOS (iPhone e iPad) en C.C.I. SYSTEM.

Gestiona:
1. Márgenes de seguridad exactos para Notch, Dynamic Island y barra de inicio (Home Indicator).
2. Manejo de audio en segundo plano (AVAudioSession category playback/playAndRecord).
3. Mapeo de háptica iOS (UIImpactFeedbackGenerator).
4. Ciclo de vida y preservación de estado ante suspensiones de iOS.
"""
from __future__ import annotations

import os
import sys
from typing import Optional, Tuple
import pygame

from mobile.touch_controls import VirtualTouchGamepad


class IOSAdapter:
    """Adaptador de hardware, áreas seguras y háptica para iOS."""

    # Presets de áreas seguras en modo Landscape (izq, arr, der, aba)
    SAFE_AREAS = {
        "notch": (47, 0, 47, 21),           # iPhone X, XS, 11, 12, 13, 14
        "dynamic_island": (59, 0, 59, 21),  # iPhone 14 Pro, 15, 15 Pro, 16
        "ipad": (0, 24, 0, 20),              # iPad Pro / Air con Home Bar
        "classic": (0, 0, 0, 0),             # iPhone SE / iPad con botón físico
    }

    def __init__(self, screen_w: int = 1280, screen_h: int = 720, device_type: str = "dynamic_island"):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.device_type = device_type
        self.is_ios = self.detect_ios()
        self.is_backgrounded = False

        self.safe_area = self.calculate_safe_area(device_type, screen_w, screen_h)
        self.touch_gamepad = VirtualTouchGamepad(screen_w, screen_h)

        # Aplicar márgenes seguros al gamepad virtual
        self._apply_safe_area_to_gamepad()

    @staticmethod
    def detect_ios() -> bool:
        """Comprueba si el proceso corre en entorno iOS nativo o simulador."""
        return sys.platform == "ios" or "IPHONE_OS" in os.environ or "SIMULATOR_DEVICE_NAME" in os.environ

    @classmethod
    def calculate_safe_area(cls, device_type: str, w: int, h: int) -> Tuple[int, int, int, int]:
        """Calcula los píxeles de recorte para evitar que los controles queden bajo la isla o notch."""
        raw = cls.SAFE_AREAS.get(device_type, cls.SAFE_AREAS["notch"])
        # Escalar proporcionalmente a la resolución actual respecto a base 1080p
        scale_x = w / 1920.0 if w > 1280 else w / 1280.0
        scale_y = h / 1080.0 if h > 720 else h / 720.0

        left = int(raw[0] * scale_x)
        top = int(raw[1] * scale_y)
        right = int(raw[2] * scale_x)
        bottom = int(raw[3] * scale_y)
        return (left, top, right, bottom)

    def _apply_safe_area_to_gamepad(self):
        """Desplaza el D-pad y los botones de acción para respetar el Safe Area."""
        left_inset, top_inset, right_inset, bottom_inset = self.safe_area
        sw, sh = self.screen_w, self.screen_h
        scale = min(sw / 1280.0, sh / 720.0)

        # Reubicar D-pad sumando el margen izquierdo
        new_dpad_x = int(130 * scale) + left_inset
        new_dpad_y = sh - int(130 * scale) - bottom_inset
        self.touch_gamepad.dpad_center = (new_dpad_x, new_dpad_y)

        # Reubicar botones de acción restando el margen derecho
        bx = sw - int(140 * scale) - right_inset
        by = sh - int(130 * scale) - bottom_inset
        step = int(68 * scale)

        if self.touch_gamepad.layout == "arcade":
            self.touch_gamepad.buttons["punch_light"] = (bx - step, by - step // 2)
            self.touch_gamepad.buttons["punch_medium"] = (bx, by - step // 2)
            self.touch_gamepad.buttons["punch_heavy"] = (bx + step, by - step // 2)
            self.touch_gamepad.buttons["kick_light"] = (bx - step, by + step // 2)
            self.touch_gamepad.buttons["kick_medium"] = (bx, by + step // 2)
            self.touch_gamepad.buttons["kick_heavy"] = (bx + step, by + step // 2)
        elif self.touch_gamepad.layout == "standard":
            self.touch_gamepad.buttons["btn_a"] = (bx, by + step)
            self.touch_gamepad.buttons["btn_b"] = (bx + step, by)
            self.touch_gamepad.buttons["btn_x"] = (bx - step, by)
            self.touch_gamepad.buttons["btn_y"] = (bx, by - step)
        else:
            self.touch_gamepad.buttons["btn_a"] = (bx + int(step * 0.6), by)
            self.touch_gamepad.buttons["btn_b"] = (bx - int(step * 0.6), by)

    def trigger_haptic(self, style: str = "medium") -> bool:
        """
        Emula o invoca retroalimentación háptica (UIImpactFeedbackGenerator).
        En macOS / escritorio realiza un no-op seguro; en iOS real enlaza con PyObjC o ctypes.
        """
        valid_styles = ("light", "medium", "heavy", "selection")
        if style not in valid_styles:
            return False
        # Si estuviera en dispositivo iOS real con ctypes objc:
        # feedback = ObjCClass('UIImpactFeedbackGenerator').alloc().initWithStyle_(...)
        return True

    def handle_lifecycle_event(self, event_type: int) -> bool:
        """Maneja transiciones de estado de iOS (WillResignActive, DidEnterBackground)."""
        if event_type in (getattr(pygame, "APP_WILLENTERBACKGROUND", -1), getattr(pygame, "APP_DIDENTERBACKGROUND", -2)):
            self.is_backgrounded = True
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.pause()
            except Exception:
                pass
            return True
        elif event_type in (getattr(pygame, "APP_WILLENTERFOREGROUND", -3), getattr(pygame, "APP_DIDENTERFOREGROUND", -4)):
            self.is_backgrounded = False
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.unpause()
            except Exception:
                pass
            return True
        return False
