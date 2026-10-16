"""
main.py - Consola Virtual Arcade 'C.C.I. System'
Punto de entrada principal del sistema que unifica múltiples juegos bajo una sola ventana de Pygame-CE.

Patrón de Diseño: State Machine (Máquina de Estados)
Flujo de Estados:
1. BOOT: Video de arranque CCI_INTRO.mp4 sincronizado con OpenCV.
2. INTRO_AVATAR: Video cinemático Pixel_girl_reading_dialogue_boxes_20261016123851.mp4 con audio. (Saltable con Enter / Espacio).
3. MENU: Menú interactivo arcade retro con 6 juegos y hover en color.
4. PLAYING: Ejecución modular del juego seleccionado en el mismo contexto gráfico.
"""

import sys
import os

# Importación de la arquitectura de estados y componentes
from states import (
    StateMachine,
    BootState,
    IntroAvatarState,
    MenuState,
    PlayingState,
    SCREEN_WIDTH,
    SCREEN_HEIGHT
)

import pygame


# Configuración del Sistema
FPS = 60
SYSTEM_TITLE = "C.C.I. SYSTEM - VIRTUAL CONSOLE"


def init_subsystems():
    """Inicializa los subsistemas necesarios de Pygame (display, font, mixer, joystick)."""
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[C.C.I. System] Aviso: No se pudo inicializar mixer de audio: {e}")
    if not pygame.joystick.get_init():
        try:
            pygame.joystick.init()
        except Exception as e:
            print(f"[C.C.I. System] Aviso: No se pudo inicializar joystick: {e}")



def main():
    """Función principal y ciclo de vida de la aplicación."""
    init_subsystems()

    # Inicializar la ventana de Pygame una sola vez
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(SYSTEM_TITLE)
    clock = pygame.time.Clock()

    # Instanciar el Gestor de Máquina de Estados
    state_machine = StateMachine(screen)

    # Registrar los estados del sistema
    state_machine.register_state("BOOT", BootState(state_machine))
    state_machine.register_state("INTRO_AVATAR", IntroAvatarState(state_machine))
    state_machine.register_state("MENU", MenuState(state_machine))
    state_machine.register_state("PLAYING", PlayingState(state_machine))

    # Iniciar en el primer estado: BOOT (Video 1)
    state_machine.change_state("BOOT")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time en segundos

        # Captura centralizada de eventos
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state_machine.current_state_name == "MENU":
                    running = False

        # Delegación al estado activo
        state_machine.handle_events(events)
        state_machine.update(dt)
        state_machine.draw(screen)

        # Actualizar pantalla
        pygame.display.flip()

    # Cierre limpio del sistema
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
