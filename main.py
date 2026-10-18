"""Punto de entrada de la consola virtual C.C.I. System (Pygame-CE)."""
from __future__ import annotations

import sys

import pygame

from cci_console import CATALOG, CCIConsoleState, UserData
from states import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    BootState,
    IntroAvatarState,
    MenuState,
    PlayingState,
    StateMachine,
)

FPS = 60
SYSTEM_TITLE = "C.C.I. SYSTEM — VIRTUAL CONSOLE"


def init_subsystems():
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except pygame.error as exc:
            print(f"[C.C.I. System] Audio no disponible: {exc}")
    if not pygame.joystick.get_init():
        try:
            pygame.joystick.init()
        except pygame.error as exc:
            print(f"[C.C.I. System] Mandos no disponibles: {exc}")


def _resolution(settings):
    try:
        width, height = str(settings.get("resolution", "1280 x 720")).lower().replace(" ", "").split("x", 1)
        return max(800, int(width)), max(450, int(height))
    except (ValueError, TypeError):
        return SCREEN_WIDTH, SCREEN_HEIGHT


def _open_display(settings):
    size = _resolution(settings)
    flags = pygame.FULLSCREEN if settings.get("fullscreen") else pygame.RESIZABLE
    try:
        surface = pygame.display.set_mode(size, flags)
    except pygame.error as exc:
        print(f"[C.C.I. System] No se pudo aplicar {size}: {exc}; se usa 1280x720.")
        surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(SYSTEM_TITLE)
    if pygame.mixer.get_init():
        try:
            game_volume = max(0.0, min(1.0, int(settings.get("volume_game", 75)) / 100))
            pygame.mixer.music.set_volume(game_volume)
            for channel_id in range(pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(channel_id).set_volume(game_volume)
        except pygame.error:
            pass
    return surface


def main():
    init_subsystems()
    user_data = UserData()
    screen = _open_display(user_data.settings)
    clock = pygame.time.Clock()
    state_machine = StateMachine(screen)

    def apply_display(settings):
        nonlocal screen
        screen = _open_display(settings)
        state_machine.screen = screen

    # Se mantiene el Inicio original con carrusel vertical; las demás vistas son interactivas.
    state_machine.register_state("BOOT", BootState(state_machine))
    state_machine.register_state("INTRO_AVATAR", IntroAvatarState(state_machine))
    def record_game_launch(game_key, elapsed):
        game = next((item for item in CATALOG if item["id"] == game_key), None)
        if game:
            user_data.record_launch(game, elapsed)

    state_machine.register_state("MENU", MenuState(state_machine, on_game_launch=record_game_launch))
    state_machine.register_state("LIBRARY", CCIConsoleState(state_machine, "library", user_data, apply_display))
    state_machine.register_state("PROFILE", CCIConsoleState(state_machine, "profile", user_data, apply_display))
    state_machine.register_state("ACHIEVEMENTS", CCIConsoleState(state_machine, "achievements", user_data, apply_display))
    state_machine.register_state("SETTINGS", CCIConsoleState(state_machine, "settings", user_data, apply_display))
    state_machine.register_state("PLAYING", PlayingState(state_machine))
    state_machine.change_state("BOOT")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        state_machine.handle_events(events)
        state_machine.update(dt)
        screen = pygame.display.get_surface() or screen
        state_machine.screen = screen
        state_machine.draw(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
