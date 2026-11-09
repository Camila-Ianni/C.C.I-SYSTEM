"""run_ps4_dashboard.py - Lanzador interactivo del Dashboard estilo PlayStation 4 para C.C.I. SYSTEM.
100% Python puro con Pygame.
"""
from __future__ import annotations

import sys
import pygame
from ps4_dashboard_ui import PS4DashboardUI
from console_selector_ui import ConsoleSelectorUI
from retro_core_runner import LibretroRunner


def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

    screen_w, screen_h = 1280, 720
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("PlayStation 4 UI — C.C.I. SYSTEM Virtual Console")
    clock = pygame.time.Clock()

    dashboard = PS4DashboardUI(screen_w, screen_h)
    selector = None
    active_runner = None
    mode = "DASHBOARD"  # "DASHBOARD", "SELECTOR", "RUNNER"

    # Música de fondo ambiental PS4
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

            if mode == "DASHBOARD":
                res = dashboard.handle_event(event)
                if not res:
                    continue
                if res.get("action") == "SELECT_ITEM":
                    item = res["item"]
                    if item["type"] == "CONSOLE":
                        # Abrir selector de juegos para esa consola
                        selector = ConsoleSelectorUI(screen_w, screen_h)
                        # Preseleccionar consola si coincide
                        for c_idx, c in enumerate(selector.consoles):
                            if c["id"] == item["id"]:
                                selector.selected_console_idx = c_idx
                                selector.selected_game_idx = 0
                                break
                        mode = "SELECTOR"
                    elif item["type"] == "COMMUNITY":
                        print("[PS4 UI] Accediendo a Comunidad C.C.I.")
                elif res.get("action") == "TOPBAR_ACTION":
                    top_id = res["item"]["id"]
                    print(f"[PS4 UI] Acción TopBar activada: {top_id}")
                    if top_id == "off":
                        running = False
                        break
                    elif top_id in ("plus", "friends"):
                        print("[PS4 UI] Abriendo Hub de Comunidad...")
                    elif top_id == "trophy":
                        print("[PS4 UI] Abriendo Sistema de Trofeos...")
                    elif top_id == "settings":
                        print("[PS4 UI] Abriendo Ajustes...")
                    elif top_id == "user":
                        print("[PS4 UI] Abriendo Perfil de Alex...")
                elif res.get("action") == "QUIT":
                    running = False
                    break

            elif mode == "SELECTOR":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    mode = "DASHBOARD"
                    continue
                sel_res = selector.handle_event(event)
                if sel_res:
                    if sel_res.get("action") == "BACK":
                        mode = "DASHBOARD"
                    elif sel_res.get("action") == "LAUNCH_GAME":
                        print(f"[PS4 UI] Lanzando juego: {sel_res['rom_path']} con {sel_res['core_path']}")
                        # Lanzar con LibretroRunner
                        pygame.mixer.music.pause()
                        try:
                            runner = LibretroRunner(
                                core_path=sel_res["core_path"],
                                rom_path=sel_res["rom_path"],
                                screen_w=screen_w,
                                screen_h=screen_h
                            )
                            runner.run_standalone()
                        except Exception as e:
                            print(f"[PS4 UI] Error al ejecutar ROM: {e}")
                        finally:
                            try:
                                pygame.mixer.music.unpause()
                            except Exception:
                                pass
                        mode = "SELECTOR"

        # Render
        if mode == "DASHBOARD":
            dashboard.render(screen)
        elif mode == "SELECTOR":
            selector.render(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
