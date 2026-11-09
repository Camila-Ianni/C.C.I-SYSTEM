"""run_omnidash.py - Lanzador interactivo del Sistema OmniDash unificado para C.C.I. SYSTEM.
100% Python puro con Pygame-CE y Libretro ctypes bridge.
"""
from __future__ import annotations

import sys
import pygame
from omnidash_engine import OmniDashEngine
from omnidash_screens import (
    OmniDashHomeView,
    OmniDashGameDetailsView,
    OmniDashSettingsView,
    OmniDashProfileView,
)
from retro_core_runner import LibretroRunner


def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

    screen_w, screen_h = 1280, 720
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("OmniDash — C.C.I. SYSTEM Virtual Console")
    clock = pygame.time.Clock()

    engine = OmniDashEngine(screen_w, screen_h, active_theme="aero")
    home_view = OmniDashHomeView(engine)
    settings_view = OmniDashSettingsView(engine)
    profile_view = OmniDashProfileView(engine)
    details_view = None

    current_view = "HOME"  # "HOME", "DETAILS", "SETTINGS", "PROFILE"

    # Música de fondo
    ambient_path = "assets_ps4/audio/ambient.mp3"
    try:
        pygame.mixer.music.load(ambient_path)
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    running = True
    while running:
        clock.tick(60)
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
                break

            # 1. Eventos del Shell Global (Top bar y cambio de tema)
            shell_res = engine.handle_shell_event(event)
            if shell_res:
                if shell_res.get("action") == "QUIT":
                    running = False
                    break
                elif shell_res.get("action") == "NAVIGATE":
                    dest = shell_res["destination"]
                    if dest == "SETTINGS":
                        current_view = "SETTINGS"
                    elif dest in ("PROFILE", "ACHIEVEMENTS"):
                        current_view = "PROFILE"
                    elif dest == "HOME":
                        current_view = "HOME"
                    continue

            # 2. Eventos de la vista activa
            if current_view == "HOME":
                h_res = home_view.handle_event(event)
                if h_res:
                    if h_res.get("action") == "OPEN_DETAILS":
                        details_view = OmniDashGameDetailsView(engine, h_res["item"])
                        current_view = "DETAILS"
                    elif h_res.get("action") == "NAVIGATE_UTIL":
                        dest = h_res["destination"]
                        if dest == "SETTINGS":
                            current_view = "SETTINGS"
                        elif dest == "PROFILE":
                            current_view = "PROFILE"

            elif current_view == "DETAILS":
                d_res = details_view.handle_event(event)
                if d_res:
                    if d_res.get("action") == "BACK":
                        current_view = "HOME"
                    elif d_res.get("action") == "LAUNCH":
                        item = d_res["item"]
                        rom = d_res.get("rom")
                        if item.get("core") and rom:
                            rom_path = f"roms/{item['id']}/{rom['file']}"
                            core_path = item["core"]
                            print(f"[OmniDash] Lanzando {rom['name']} ({core_path})...")
                            pygame.mixer.music.pause()
                            try:
                                runner = LibretroRunner(
                                    core_path=core_path,
                                    rom_path=rom_path,
                                    screen_w=screen_w,
                                    screen_h=screen_h
                                )
                                runner.run_standalone()
                            except Exception as e:
                                print(f"[OmniDash] Error al ejecutar juego: {e}")
                            finally:
                                try:
                                    pygame.mixer.music.unpause()
                                except Exception:
                                    pass

            elif current_view == "SETTINGS":
                s_res = settings_view.handle_event(event)
                if s_res and s_res.get("action") == "BACK":
                    current_view = "HOME"

            elif current_view == "PROFILE":
                p_res = profile_view.handle_event(event)
                if p_res and p_res.get("action") == "BACK":
                    current_view = "HOME"

        # Renderizado en capas
        engine.render_background(screen)

        if current_view == "HOME":
            home_view.render(screen)
            engine.render_top_bar(screen)
            engine.render_bottom_dock(screen)
        elif current_view == "DETAILS":
            details_view.render(screen)
            engine.render_bottom_dock(screen, extra_actions=[("⌧", "Lanzar Título")])
        elif current_view == "SETTINGS":
            settings_view.render(screen)
        elif current_view == "PROFILE":
            profile_view.render(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
