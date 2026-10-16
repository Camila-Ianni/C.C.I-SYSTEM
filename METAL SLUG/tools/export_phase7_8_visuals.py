"""
Exports rendered PNG frames for all menu screens and stages (Phases 7 & 8).
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from src.game import (
    Game, STATE_TITLE, STATE_CHAR_SELECT, STATE_GAMEPLAY,
    STATE_RESULTS, STATE_GAMEOVER, STATE_VICTORY
)

os.makedirs("test_output", exist_ok=True)

game = Game()

# 1. Capture Title Screen (at 120 ticks into video playback)
for _ in range(120):
    game.update()
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_01_title.png")
print("[EXPORT] Saved test_output/screen_01_title.png")

# 2. Advance to Character Select
ev_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
pygame.event.post(ev_enter)
game.handle_events()
game.update()
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_02_char_select.png")
print("[EXPORT] Saved test_output/screen_02_char_select.png")

# 3. Launch Gameplay with Tarma
game.char_select_screen.selected_index = 1
pygame.event.post(ev_enter)
game.handle_events()
for _ in range(20):
    game.update()
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_03_mission1_tarma.png")
print("[EXPORT] Saved test_output/screen_03_mission1_tarma.png")

# 4. Capture Mission 2
game.stage_manager.load_mission(2)
game.setup_next_mission()
for _ in range(10):
    game.update()
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_04_mission2.png")
print("[EXPORT] Saved test_output/screen_04_mission2.png")

# 5. Capture Mission 3
game.stage_manager.load_mission(3)
game.setup_next_mission()
for _ in range(10):
    game.update()
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_05_mission3.png")
print("[EXPORT] Saved test_output/screen_05_mission3.png")

# 6. Capture Mission Results
from src.ui.menu_screens import MissionResultsScreen, GameOverScreen, VictoryScreen
game.results_screen = MissionResultsScreen(mission_num=2, rescued_pows=4, slug_intact=True, score=85400)
game.state = STATE_RESULTS
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_06_results.png")
print("[EXPORT] Saved test_output/screen_06_results.png")

# 7. Capture Game Over Screen
game.game_over_screen = GameOverScreen(countdown=9)
game.state = STATE_GAMEOVER
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_07_gameover.png")
print("[EXPORT] Saved test_output/screen_07_gameover.png")

# 8. Capture Victory Screen
game.victory_screen = VictoryScreen(final_score=350000)
game.state = STATE_VICTORY
game.draw()
pygame.image.save(game.virtual_screen, "test_output/screen_08_victory.png")
print("[EXPORT] Saved test_output/screen_08_victory.png")

print("\n[ALL EXPORTS COMPLETED]")
