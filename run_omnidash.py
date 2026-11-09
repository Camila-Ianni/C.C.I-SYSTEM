"""run_omnidash.py - Lanzador oficial e interactivo de OmniDash Frutiger Aero para C.C.I. SYSTEM.
100% Python puro con Pygame-CE y Libretro ctypes bridge.
Soporta el flujo completo de pantallas oficiales OmniDash:
- HOME: Isla soleada, Hero card con lanzamiento directo, tarjetas glossy y 4 tarjetas de utilidad.
- LIBRARY: Biblioteca completa de juegos con 8 plataformas y buscador interactivo.
- SETTINGS: Panel oficial de Ajustes con 8 categorías en cristal translúcido.
- PROFILE: Perfil de usuario con Gamerscore (18,450 G) y logros.
- COMMUNITY: Vista de grupos y amigos en línea.
- LAUNCH_ANIM: Animación oficial de elevación de logo ("rises the logo over key art") con sonido startup.mp3.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import sys
import pygame
from omnidash_engine import OmniDashEngine
from omnidash_screens import (
    OmniDashHomeView,
    OmniDashLibraryView,
    OmniDashGameDetailsView,
    OmniDashSettingsView,
    OmniDashProfileView,
    OmniDashCommunityView,
    OmniDashLaunchScreenView,
    ALL_GAMES,
)
from retro_core_runner import LibretroRunner


def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

    screen_w, screen_h = 1280, 720
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("OmniDash — C.C.I. SYSTEM Virtual Console (Frutiger Aero)")
    clock = pygame.time.Clock()

    engine = OmniDashEngine(screen_w, screen_h, active_theme="aero")
    home_view = OmniDashHomeView(engine)
    library_view = OmniDashLibraryView(engine)
    settings_view = OmniDashSettingsView(engine)
    profile_view = OmniDashProfileView(engine)
    community_view = OmniDashCommunityView(engine)
    details_view = None
    launch_anim_view = None

    current_view = "HOME"  # "HOME", "LIBRARY", "DETAILS", "SETTINGS", "PROFILE", "COMMUNITY", "LAUNCH_ANIM"
    pending_launch_target = None

    # Música de fondo
    ambient_path = "assets_ps4/audio/ambient.mp3"
    try:
        pygame.mixer.music.load(ambient_path)
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    def open_game_details(game_item: dict):
        nonlocal current_view, details_view
        details_view = OmniDashGameDetailsView(engine, game_item)
        current_view = "DETAILS"

    def start_launch_sequence(target: dict):
        nonlocal current_view, launch_anim_view, pending_launch_target
        pending_launch_target = target
        launch_anim_view = OmniDashLaunchScreenView(engine, target)
        current_view = "LAUNCH_ANIM"

    def execute_game(target: dict):
        nonlocal current_view
        core_path = target.get("core")
        rom_path = target.get("rom")

        if core_path and rom_path:
            print(f"[OmniDash] Iniciando emulación Libretro 60 FPS: {target.get('title')} ({core_path})...")
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

            try:
                runner = LibretroRunner(
                    core_path=core_path,
                    rom_path=rom_path,
                    screen_w=screen_w,
                    screen_h=screen_h
                )
                runner.run_standalone()
            except Exception as exc:
                print(f"[OmniDash] Error al ejecutar emulador Libretro: {exc}")
            finally:
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
        else:
            print(f"[OmniDash] Lanzando juego nativo C.C.I.: {target.get('title')}")

        current_view = "HOME"

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
                break

            # 1. Navegación global del dock superior e inferior (en vista HOME)
            if current_view == "HOME":
                shell_res = engine.handle_shell_event(event)
                if shell_res:
                    if shell_res.get("action") == "QUIT":
                        running = False
                        break
                    elif shell_res.get("action") == "NAVIGATE":
                        dest = shell_res["destination"]
                        if dest == "LIBRARY":
                            current_view = "LIBRARY"
                        elif dest in ("GROUPS", "COMMUNITY"):
                            current_view = "COMMUNITY"
                        elif dest == "SETTINGS":
                            current_view = "SETTINGS"
                        elif dest in ("PROFILE", "ACHIEVEMENTS"):
                            current_view = "PROFILE"
                        elif dest == "HOME":
                            current_view = "HOME"
                        continue

            # 2. Eventos por cada pantalla activa
            if current_view == "HOME":
                h_res = home_view.handle_event(event)
                if h_res:
                    if h_res.get("action") == "OPEN_DETAILS":
                        open_game_details(h_res["item"])
                    elif h_res.get("action") == "LAUNCH_DIRECT":
                        start_launch_sequence(h_res["item"])
                    elif h_res.get("action") == "NAVIGATE_UTIL":
                        dest = h_res["destination"]
                        if dest == "LIBRARY":
                            current_view = "LIBRARY"
                        elif dest in ("GROUPS", "COMMUNITY"):
                            current_view = "COMMUNITY"
                        elif dest == "SETTINGS":
                            current_view = "SETTINGS"
                        elif dest in ("PROFILE", "ACHIEVEMENTS"):
                            current_view = "PROFILE"

            elif current_view == "LIBRARY":
                lib_res = library_view.handle_event(event)
                if lib_res:
                    if lib_res.get("action") == "BACK":
                        current_view = "HOME"
                    elif lib_res.get("action") == "OPEN_DETAILS":
                        open_game_details(lib_res["item"])
                    elif lib_res.get("action") == "LAUNCH_GAME":
                        start_launch_sequence(lib_res["game"])

            elif current_view == "DETAILS":
                if details_view:
                    d_res = details_view.handle_event(event)
                    if d_res:
                        if d_res.get("action") == "BACK":
                            current_view = "LIBRARY"
                        elif d_res.get("action") == "LAUNCH":
                            start_launch_sequence(d_res["item"])

            elif current_view == "SETTINGS":
                s_res = settings_view.handle_event(event)
                if s_res and s_res.get("action") == "BACK":
                    current_view = "HOME"

            elif current_view == "PROFILE":
                p_res = profile_view.handle_event(event)
                if p_res and p_res.get("action") == "BACK":
                    current_view = "HOME"

            elif current_view == "COMMUNITY":
                c_res = community_view.handle_event(event)
                if c_res and c_res.get("action") == "BACK":
                    current_view = "HOME"

            elif current_view == "LAUNCH_ANIM":
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    current_view = "HOME"

        # 3. Actualización de animaciones
        if current_view == "LAUNCH_ANIM" and launch_anim_view:
            l_res = launch_anim_view.update(dt)
            if l_res and l_res.get("action") == "LAUNCH_NOW":
                target = l_res["target"]
                execute_game(target)

        # 4. Renderizado en capas sobre el mar de Frutiger Aero
        engine.render_background(screen)

        if current_view == "HOME":
            home_view.render(screen)
            engine.render_top_bar(screen)
            engine.render_bottom_dock(screen)
        elif current_view == "LIBRARY":
            library_view.render(screen)
            engine.render_bottom_dock(screen)
        elif current_view == "DETAILS" and details_view:
            details_view.render(screen)
        elif current_view == "SETTINGS":
            settings_view.render(screen)
        elif current_view == "PROFILE":
            profile_view.render(screen)
        elif current_view == "COMMUNITY":
            community_view.render(screen)
        elif current_view == "LAUNCH_ANIM" and launch_anim_view:
            launch_anim_view.render(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
