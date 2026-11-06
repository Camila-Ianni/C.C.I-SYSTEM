"""
mobile/mobile_adapter.py - Adaptador de ciclo de vida móvil y plataforma Android para C.C.I. SYSTEM.

Gestiona:
1. Detección de entorno móvil (Android/iOS vs Desktop).
2. Ciclo de vida SDL2: pausa/reanudación de audio y estados (APP_WILLENTERBACKGROUND, APP_DIDENTERFOREGROUND).
3. Botón físico Volver (Android hardware back button K_AC_BACK).
4. Margen de área segura (Safe Area / Insets para muescas y barras de navegación).
5. Coordinación con VirtualTouchGamepad y gamepads físicos Bluetooth.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional
import pygame

from mobile.touch_controls import VirtualTouchGamepad


class MobileAdapter:
    """Controlador central del ciclo de vida móvil y puente de hardware."""

    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_android = self.detect_android()
        self.is_mobile = self.is_android or self.detect_ios()
        self.is_paused = False

        # Safe area insets (pixels: left, top, right, bottom)
        self.safe_area = (0, 0, 0, 0)
        if self.is_mobile:
            self._calculate_safe_area()

        # Touch gamepad overlay
        self.touch_gamepad = VirtualTouchGamepad(screen_w, screen_h)
        # On desktop, disable touch gamepad by default unless explicitly forced
        if not self.is_mobile and os.environ.get("CCI_FORCE_TOUCH") != "1":
            self.touch_gamepad.enabled = False

        # Callbacks para integración con la consola C.C.I. SYSTEM
        self.on_pause_requested: Optional[Callable[[], None]] = None
        self.on_resume_requested: Optional[Callable[[], None]] = None
        self.on_back_pressed: Optional[Callable[[], None]] = None

    @staticmethod
    def detect_android() -> bool:
        """Determina si la aplicación se ejecuta en Android (Python-for-Android / Buildozer)."""
        return "ANDROID_ARGUMENT" in os.environ or "ANDROID_ENTRYPOINT" in os.environ or sys.platform == "android"

    @staticmethod
    def detect_ios() -> bool:
        """Determina si la aplicación se ejecuta en iOS (kivy-ios / Briefcase)."""
        return sys.platform == "ios" or "IPHONE_OS" in os.environ

    def _calculate_safe_area(self):
        """Calcula márgenes seguros para evitar muescas de cámara (camera cutout) y barra de navegación."""
        # En pantalla horizontal (landscape), recortamos márgenes laterales preventivos (40px)
        left_inset = int(self.screen_w * 0.035)
        right_inset = int(self.screen_w * 0.035)
        top_inset = 0
        bottom_inset = int(self.screen_h * 0.02)
        self.safe_area = (left_inset, top_inset, right_inset, bottom_inset)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Procesa eventos del ciclo de vida móvil y hardware.
        Retorna True si el evento fue consumido por el adaptador móvil.
        """
        # 1. Ciclo de vida SDL2: entrar a segundo plano
        # pygame-ce expone eventos APP_WILLENTERBACKGROUND / APP_DIDENTERBACKGROUND
        event_name = pygame.event.event_name(event.type) if hasattr(pygame.event, "event_name") else ""
        if (
            event.type in (getattr(pygame, "APP_WILLENTERBACKGROUND", -1), getattr(pygame, "APP_DIDENTERBACKGROUND", -2))
            or event_name in ("AppWillEnterBackground", "AppDidEnterBackground")
        ):
            self.pause_app()
            return True

        # 2. Ciclo de vida SDL2: volver al primer plano
        if (
            event.type in (getattr(pygame, "APP_WILLENTERFOREGROUND", -3), getattr(pygame, "APP_DIDENTERFOREGROUND", -4))
            or event_name in ("AppWillEnterForeground", "AppDidEnterForeground")
        ):
            self.resume_app()
            return True

        # 3. Botón físico Atrás de Android (K_AC_BACK o tecla Escape en mapeo estándar)
        ac_back = getattr(pygame, "K_AC_BACK", None)
        if event.type == pygame.KEYDOWN and (event.key == ac_back or event.key == pygame.K_ESCAPE):
            if self.on_back_pressed:
                self.on_back_pressed()
                return True

        # 4. Conexión / Desconexión de gamepad físico (Bluetooth / USB OTG)
        if event.type == pygame.JOYDEVICEADDED:
            self.touch_gamepad.set_hardware_gamepad_connected(True)
        elif event.type == pygame.JOYDEVICEREMOVED:
            # Si ya no quedan joysticks conectados, reactivar controles táctiles
            if pygame.joystick.get_count() == 0:
                self.touch_gamepad.set_hardware_gamepad_connected(False)

        # 5. Delegar toques al gamepad virtual si está activo
        if self.touch_gamepad.enabled:
            self.touch_gamepad.handle_event(event)

        return False

    def pause_app(self):
        """Pausa el audio y la lógica activa cuando la app va a segundo plano."""
        if not self.is_paused:
            self.is_paused = True
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.pause()
            except Exception:
                pass
            if self.on_pause_requested:
                self.on_pause_requested()

    def resume_app(self):
        """Reanuda el audio y la lógica activa al regresar al primer plano."""
        if self.is_paused:
            self.is_paused = False
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.unpause()
            except Exception:
                pass
            if self.on_resume_requested:
                self.on_resume_requested()

    def render(self, surface: pygame.Surface):
        """Dibuja los controles táctiles si corresponde."""
        if self.touch_gamepad.enabled and self.touch_gamepad.visible:
            self.touch_gamepad.render(surface)
