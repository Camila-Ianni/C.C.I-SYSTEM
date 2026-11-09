#!/usr/bin/env python3
"""run_console_selector.py - Lanzador independiente del Selector de Consolas y Emulador C.C.I. SYSTEM."""
import sys
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from console_selector_ui import ConsoleSelectorUI
from retro_core_runner import LibretroRunner


def main():
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
    if not pygame.joystick.get_init():
        try:
            pygame.joystick.init()
        except Exception:
            pass

    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()

    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("C.C.I. SYSTEM — SELECTOR DE CONSOLAS & EMULADOR RETRO (60 FPS)")
    clock = pygame.time.Clock()

    ui = ConsoleSelectorUI(1280, 720)
    current_runner: LibretroRunner | None = None
    running = True

    print("=== C.C.I. SYSTEM CONSOLE SELECTOR INICIADO ===")
    print("Controles UI: Flechas / WASD para moverte | ENTER / Z para seleccionar | ESC / X para volver")
    print("Controles en Juego: Flechas para moverte | Z=B, X=A, A=Y, S=X, ENTER=Start, SHIFT=Select | ESC para salir")

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if current_runner is None:
                action = ui.handle_event(event)
                if action and action.get("action") == "LAUNCH":
                    core_p = action["core_path"]
                    rom_p = action["game"]["path"]
                    print(f"\n[LAUNCH] Iniciando {action['game']['title']} con núcleo {action['console']['name']}...")
                    try:
                        current_runner = LibretroRunner(core_p)
                        if not current_runner.load_rom(rom_p):
                            print("[ERROR] No se pudo cargar la ROM.")
                            current_runner = None
                    except Exception as err:
                        print(f"[ERROR] Error al inicializar núcleo: {err}")
                        current_runner = None
            else:
                # Controles en juego
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    print("\n[PAUSE/EXIT] Saliendo del juego y volviendo al Selector de Consolas...")
                    current_runner.unload()
                    current_runner = None

        if current_runner:
            # En juego
            keys = pygame.key.get_pressed()
            joy = joysticks[0] if joysticks else None
            current_runner.update_input(keys, joy)
            current_runner.step_frame()
            current_runner.render_to(screen, 1280, 720)
        else:
            # En UI de Consolas
            ui.render(screen)

        pygame.display.flip()

    if current_runner:
        current_runner.unload()
    pygame.quit()


if __name__ == "__main__":
    main()
