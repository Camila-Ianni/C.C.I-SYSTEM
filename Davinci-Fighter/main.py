"""
main.py - Punto de entrada principal y máquina de estados arcade para Da Vinci Fighters.
Secuencia pre-combate completa y continua (100% fiel a Street Fighters.mov):
1. AppState.INTRO_CUTSCENE (Intro Street Fighter II a 60 FPS, punch brawl, skyscraper pan, logo drop).
2. AppState.TITLE_SCREEN (Pantalla de título oficial con home.png, brillo animado y Opening Theme.mp3).
3. AppState.MENU (Modos 1P vs IA / 2P PVP, Cómo Jugar y Salir).
4. AppState.CHARACTER_SELECT (Mapa mundial con casillas de los 5 profesores y Character Select.mp3).
5. AppState.VS_SCREEN (Cutscene de vuelo de avión, trazado de ruta en mapa y choque de impacto VS).
6. AppState.GAME (Combate en escenario de 2200px con scrolling de cámara y público animado).
"""

import sys
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS
from intro_cutscene import IntroCutscene
from title_screen import TitleScreen
from menu import MainMenu
from character_select import CharacterSelect
from vs_screen import VSScreen
from game import Game


class AppState:
    INTRO_CUTSCENE = "intro_cutscene"
    TITLE_SCREEN = "title_screen"
    MENU = "menu"
    CHARACTER_SELECT = "character_select"
    VS_SCREEN = "vs_screen"
    GAME = "game"


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    app_state = AppState.INTRO_CUTSCENE
    intro_cutscene = IntroCutscene(screen)
    title_screen = None
    selected_mode = None

    menu = None
    char_select = None
    vs_screen = None
    game_instance = None
    p1_char = "carloni"
    p2_char = "cavasso"
    selected_stage_id = None

    running = True
    while running:
        dt = 1.0 / FPS

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if app_state == AppState.INTRO_CUTSCENE:
                res = intro_cutscene.handle_input(event)
                if res == "finish":
                    app_state = AppState.TITLE_SCREEN
                    title_screen = TitleScreen(screen)

            elif app_state == AppState.TITLE_SCREEN:
                res = title_screen.handle_input(event)
                if res in ("continue", "start"):
                    selected_mode = getattr(title_screen, "selected_mode", "1p")
                    credits_p1 = getattr(title_screen, "credits_p1", 1)
                    credits_p2 = getattr(title_screen, "credits_p2", 0)
                    char_select = CharacterSelect(screen, selected_mode, credits_p1=credits_p1, credits_p2=credits_p2)
                    app_state = AppState.CHARACTER_SELECT

            elif app_state == AppState.MENU:
                res = menu.handle_input(event) if menu else None
                if res:
                    if res.get("action") == "start":
                        selected_mode = res.get("mode", "1p")
                        char_select = CharacterSelect(screen, selected_mode)
                        app_state = AppState.CHARACTER_SELECT
                    elif res.get("action") == "exit":
                        running = False

            elif app_state == AppState.CHARACTER_SELECT:
                res = char_select.handle_input(event)
                if res and res.get("action") in ("vs", "fight"):
                    p1_char = res.get("p1_char", "carloni")
                    p2_char = res.get("p2_char", "cavasso")
                    selected_stage_id = res.get("stage_id", None)
                    selected_mode = char_select.game_mode
                    game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                    app_state = AppState.GAME

            elif app_state == AppState.VS_SCREEN:
                res = vs_screen.handle_input(event)
                if res == "fight":
                    game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                    app_state = AppState.GAME

            elif app_state == AppState.GAME:
                pass

        # Actualización y Renderizado por Estado
        if app_state == AppState.INTRO_CUTSCENE:
            res = intro_cutscene.update(dt)
            if res == "finish":
                app_state = AppState.TITLE_SCREEN
                title_screen = TitleScreen(screen)
            intro_cutscene.draw(screen)

        elif app_state == AppState.TITLE_SCREEN:
            title_screen.update(dt)
            title_screen.draw(screen)

        elif app_state == AppState.MENU:
            if menu:
                menu.update(dt)
                menu.draw(screen)
            else:
                char_select = CharacterSelect(screen, "1p")
                app_state = AppState.CHARACTER_SELECT

        elif app_state == AppState.CHARACTER_SELECT:
            res = char_select.update(dt)
            if res and res.get("action") in ("vs", "fight"):
                p1_char = res.get("p1_char", "carloni")
                p2_char = res.get("p2_char", "cavasso")
                selected_stage_id = res.get("stage_id", None)
                selected_mode = char_select.game_mode
                game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                app_state = AppState.GAME
            char_select.draw(screen)

        elif app_state == AppState.VS_SCREEN:
            res = vs_screen.update(dt)
            if res == "fight":
                game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                app_state = AppState.GAME
            vs_screen.draw(screen)

        elif app_state == AppState.GAME:
            result = game_instance.run()
            if result == "menu":
                char_select = CharacterSelect(screen, "1p")
                app_state = AppState.CHARACTER_SELECT

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
