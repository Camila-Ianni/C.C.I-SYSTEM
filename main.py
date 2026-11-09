"""Punto de entrada de la consola virtual C.C.I. System (Pygame-CE)."""
from __future__ import annotations

# C.C.I. SYSTEM v2.1.0 — 100% Python Architecture (Desktop & Mobile)
VERSION = "2.1.0"

import sys
import time
import pygame

from cci_console import CATALOG, CCIConsoleState, UserData
from cci_users import UserManager
from user_select_state import UserSelectState
from screenshot_manager import ScreenshotManager
from audio_bgm import BGMManager
from mobile.mobile_adapter import MobileAdapter
from recorder.video_recorder import GameplayVideoRecorder
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
SYSTEM_TITLE = "C.C.I. SYSTEM — VIRTUAL CONSOLE (v2.1.0)"


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
    user_manager = UserManager()
    user_data = user_manager.active_user
    screen = _open_display(user_data.settings)
    clock = pygame.time.Clock()
    state_machine = StateMachine(screen)

    def apply_display(settings):
        nonlocal screen
        screen = _open_display(settings)
        state_machine.screen = screen

    def apply_user(new_user_data):
        nonlocal user_data
        user_data = new_user_data
        for st_name in ("LIBRARY", "PROFILE", "ACHIEVEMENTS", "SETTINGS"):
            st = state_machine.states.get(st_name)
            if hasattr(st, "set_user_data"):
                st.set_user_data(new_user_data)
        apply_display(new_user_data.settings)

    # Flujo de inicio: BOOT (CCI_INTRO) -> USER_SELECT -> MENU
    state_machine.register_state("BOOT", BootState(state_machine))
    state_machine.register_state("INTRO_AVATAR", IntroAvatarState(state_machine))
    state_machine.register_state("USER_SELECT", UserSelectState(state_machine, on_user_selected=apply_user))

    def record_game_launch(game_key, elapsed):
        game = next((item for item in CATALOG if item["id"] == game_key), None)
        if game:
            user_manager.active_user.record_launch(game, elapsed)
            try:
                from backend.communities.repository import CommunitiesRepository
                from backend.communities.service import CommunitiesService
                service = CommunitiesService(CommunitiesRepository.get_instance())
                uid = getattr(user_manager.active_user, "user_id", "u_alex") or "u_alex"
                service.set_user_presence(uid, status="online", custom_status=f"Jugando: {game.get('title', game_key)}")
            except Exception:
                pass

    from omnidash_screens import (
        OmniDashHomeState,
        OmniDashLibraryState,
        OmniDashLaunchAnimState,
        OmniDashDetailsState,
        OmniDashSettingsState,
        OmniDashProfileState,
        OmniDashCommunityState,
    )
    state_machine.register_state("MENU", OmniDashHomeState(state_machine, on_game_launch=record_game_launch))
    state_machine.register_state("LIBRARY", OmniDashLibraryState(state_machine))
    state_machine.register_state("LAUNCH_ANIM", OmniDashLaunchAnimState(state_machine))
    state_machine.register_state("DETAILS", OmniDashDetailsState(state_machine))
    state_machine.register_state("SETTINGS", OmniDashSettingsState(state_machine, user_data, apply_display))
    state_machine.register_state("PROFILE", OmniDashProfileState(state_machine, user_data))
    state_machine.register_state("ACHIEVEMENTS", OmniDashProfileState(state_machine, user_data))
    state_machine.register_state("ARCADE_MENU", MenuState(state_machine, on_game_launch=record_game_launch))
    state_machine.register_state("GROUPS", OmniDashCommunityState(state_machine))
    state_machine.register_state("COMMUNITY", OmniDashCommunityState(state_machine))
    state_machine.register_state("PLAYING", PlayingState(state_machine))
    state_machine.change_state("BOOT")

    running = True
    mobile_adapter = MobileAdapter(SCREEN_WIDTH, SCREEN_HEIGHT)
    video_recorder = GameplayVideoRecorder.get_instance()

    # Callback botón físico Volver en Android
    mobile_adapter.on_back_pressed = lambda: state_machine.change_state("MENU")

    while running:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        for event in events:
            # Procesar ciclo de vida móvil y eventos táctiles
            mobile_adapter.handle_event(event)

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_F12, pygame.K_PRINT, pygame.K_F10):
                current_surf = pygame.display.get_surface() or screen
                ScreenshotManager.get_instance().take_screenshot(current_surf)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                # F11: Alternar Grabación Asíncrona de Gameplay en MP4 (Fase 6)
                if video_recorder.is_recording:
                    video_recorder.stop_recording()
                else:
                    active_game = getattr(state_machine.current_state, "game_key", "general")
                    owner = user_manager.active_user.username if user_manager.active_user else "pilot"
                    video_recorder.start_recording(game_id=active_game, owner_id=owner)
            elif event.type == pygame.JOYBUTTONDOWN and event.button in (6, 8):
                current_surf = pygame.display.get_surface() or screen
                ScreenshotManager.get_instance().take_screenshot(current_surf)

        state_machine.handle_events(events)
        state_machine.update(dt)
        screen = pygame.display.get_surface() or screen
        state_machine.screen = screen
        state_machine.draw(screen)

        # Captura asíncrona de frame si la grabación está activa
        if video_recorder.is_recording:
            video_recorder.capture_surface(screen)
            # Indicador visual REC parpadeante en esquina superior derecha
            if int(time.time() * 2) % 2 == 0:
                pygame.draw.circle(screen, (255, 30, 30), (screen.get_width() - 85, 25), 7)
                font = pygame.font.Font(None, 24)
                rec_txt = font.render("REC", True, (255, 50, 50))
                screen.blit(rec_txt, (screen.get_width() - 72, 17))

        # Render de overlay táctil virtual (Android / iOS)
        mobile_adapter.render(screen)
        ScreenshotManager.get_instance().draw_overlay(screen)
        pygame.display.flip()

    if video_recorder.is_recording:
        video_recorder.stop_recording()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
