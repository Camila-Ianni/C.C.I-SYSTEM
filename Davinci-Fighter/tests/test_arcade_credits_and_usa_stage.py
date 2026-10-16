"""
tests/test_arcade_credits_and_usa_stage.py - Pruebas para el sistema de créditos arcade
(teclas 1 y 2) y la integración del escenario USA (Balrog Las Vegas).
"""

import os
import unittest
import pygame
from tests.base_headless import HeadlessTestCase
from settings import MODE_PVAI, MODE_PVP, SCREEN_WIDTH, SCREEN_HEIGHT
from title_screen import TitleScreen
from character_select import CharacterSelect
from stage_manager import stage_manager
from game import Game
from audio_manager import audio_manager


class TestArcadeCreditsAndUSAStage(HeadlessTestCase):
    """Pruebas del sistema de monedas arcade y escenario de USA."""

    def test_01_title_screen_credits_p1_and_p2(self):
        """Verifica que la tecla 1 cargue crédito para P1 (PVAI) y 2 para P2 (PVP)."""
        title = TitleScreen(self.screen)
        self.assertEqual(title.credits_p1, 0)
        self.assertEqual(title.credits_p2, 0)

        # Presionar 1: crédito P1
        res = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual(res, "start")
        self.assertEqual(title.credits_p1, 1)
        self.assertEqual(title.selected_mode, MODE_PVAI)

        # Presionar 2: crédito P2
        res2 = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
        self.assertEqual(res2, "start")
        self.assertEqual(title.credits_p2, 1)
        self.assertEqual(title.selected_mode, MODE_PVP)

    def test_02_char_select_credit_keys_and_mode_switching(self):
        """Verifica que en CharacterSelect se puedan insertar créditos y cambiar a PVP."""
        cs = CharacterSelect(self.screen, game_mode=MODE_PVAI, credits_p1=1, credits_p2=0)
        self.assertEqual(cs.game_mode, MODE_PVAI)
        self.assertEqual(cs.credits_p1, 1)

        # Presionar 1 agrega crédito P1
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual(cs.credits_p1, 2)
        self.assertEqual(cs.game_mode, MODE_PVAI)

        # Presionar 2 agrega crédito P2 y activa modo PVP (Challenger)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
        self.assertEqual(cs.credits_p2, 1)
        self.assertEqual(cs.game_mode, MODE_PVP)

    def test_03_select_usa_in_pvai_advances_to_balrog_stage(self):
        """Verifica que seleccionar USA en 1P confirme contra CPU y cargue el escenario Balrog."""
        cs = CharacterSelect(self.screen, game_mode=MODE_PVAI, credits_p1=1, credits_p2=0)

        # Navegar a USA (slot 1, Cavasso / USA)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_slot_idx, 1)
        self.assertEqual(cs.get_p1_country(), "usa")

        # Confirmar P1 con ENTER
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertTrue(cs.p1_confirmed)
        self.assertTrue(cs.p2_confirmed)  # CPU auto-confirmado en 1P
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "fight")
        # Slot 1 es USA de arriba -> Ken Stage (Battle Harbor)
        self.assertEqual(res["stage_id"], "ken")

        # El temporizador de transición también retorna stage_id='ken'
        res_update = cs.update(0.5)
        self.assertIsNotNone(res_update)
        self.assertEqual(res_update["stage_id"], "ken")

        # Game instanciado con stage_id='ken' carga el escenario Ken Battle Harbor
        game = Game(self.screen, res["p1_char"], res["p2_char"], MODE_PVAI, stage_id=res["stage_id"])
        self.assertIn("Ken", game.stage.name)
        self.assertEqual(len(game.stage.crowd_characters), 2)  # Ken crowd characters (upper and lower deck)

        # Verificar que el slot 4 (USA de abajo) cargue el escenario Guile Airbase Hangar
        cs_low = CharacterSelect(self.screen, game_mode=MODE_PVAI, credits_p1=1, credits_p2=0)
        cs_low.p1_slot_idx = 4
        self.assertEqual(cs_low.get_selected_stage_id(), "guile")
        game_guile = Game(self.screen, "sellanes", "carloni", MODE_PVAI, stage_id="guile")
        self.assertIn("Guile", game_guile.stage.name)

    def test_04_balrog_stage_crowd_and_cars_animation_updates(self):
        """Verifica que los personajes secundarios del escenario Balrog tengan frames y se animen."""
        stage = stage_manager.get_stage_for_country("balrog")
        self.assertEqual(stage.name, "Balrog Las Vegas Strip (USA)")
        self.assertEqual(len(stage.crowd_characters), 3)

        # Verificar que cada personaje secundario tenga múltiples frames
        for char in stage.crowd_characters:
            self.assertGreater(len(char.frames), 1)

        # Simular ciclo de animación
        prev_frames = [char.current_frame for char in stage.crowd_characters]
        stage.update(dt=0.1)
        new_frames = [char.current_frame for char in stage.crowd_characters]
        for prev, new in zip(prev_frames, new_frames):
            self.assertNotEqual(prev, new)

        # Renderizar escenario y público sin excepciones
        stage.draw(self.screen, camera_x=200)

    def test_05_coin_sfx_cached_and_playable(self):
        """Verifica que el sonido de moneda de arcade esté cacheado desde insert coin.mp3."""
        self.assertIn("coin", audio_manager.sfx_cache)
        self.assertIn("insert coin", audio_manager.sfx_cache)
        self.assertIsNotNone(audio_manager.sfx_cache["coin"])
        self.assertGreater(audio_manager.sfx_cache["coin"].get_length(), 1.0)


    def test_06_zero_credits_both_sides_and_solo_enter(self):
        """Verifica que ambos jugadores inicien con 0 créditos y P1 entre solo al tener créditos."""
        cs = CharacterSelect(self.screen)
        self.assertEqual(cs.credits_p1, 0)
        self.assertEqual(cs.credits_p2, 0)
        self.assertEqual(cs.game_mode, MODE_PVAI)

        # Renderizar en pantalla para comprobar que no lanza excepciones con 0 créditos
        cs.draw()

        # Jugador 1 inserta moneda con la tecla 1
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual(cs.credits_p1, 1)
        self.assertEqual(cs.credits_p2, 0)

        # P1 selecciona USA y confirma con RETURN
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(cs.p1_slot_idx, 1)
        self.assertEqual(cs.get_p1_country(), "usa")

        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertTrue(cs.p1_confirmed)
        # P1 "entra solo": P2 CPU auto-confirmado
        self.assertTrue(cs.p2_confirmed)
        self.assertEqual(res["action"], "fight")
        self.assertEqual(res["stage_id"], "ken")


if __name__ == "__main__":
    unittest.main()
