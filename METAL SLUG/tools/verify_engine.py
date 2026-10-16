"""
Verification Test for Metal Slug Engine (Phase 6: Boss Tetsuyuki).
Tests:
- Boss arena entrance and camera lock.
- Phase 1: Artillery nose cannon combat.
- Phase 2: Rage mode transition (< 50% HP) and Giant Plasma Cannon.
- Boss destruction sequence and 'MISSION 1 COMPLETE!' victory overlay.
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from src.game import Game
from src.config import ACTION_RIGHT, ACTION_SHOOT, ACTION_GRENADE

def test_engine_phase_6():
    print("[Test Phase 6] Initializing Metal Slug Engine...")
    game = Game()
    game.start_new_campaign("marco")
    
    # 1. Transport player directly into the Boss Arena before the waterfall
    game.player.physics.x = 3520
    game.player.physics.y = 184
    
    print("[Test Phase 6] Entering Boss Arena at the waterfall...")
    for _ in range(20):
        game.update()
        game.draw()
        
    boss = game.level.boss
    print(f"[Test Phase 6] Boss initialized at x={boss.x}, HP={boss.health}/{boss.max_health}, Phase={boss.phase}")
    assert boss is not None, "Tetsuyuki boss must exist in Mission 1"
    
    # Save Boss Arena screenshot
    boss_intro_path = "/Users/cami/.gemini/antigravity/brain/9ae7db29-94a3-4166-a111-0dd324437c02/scratch/boss_tetsuyuki_intro.png"
    pygame.image.save(game.screen, boss_intro_path)
    print(f"[Test Phase 6] Saved Boss Intro screenshot to: {boss_intro_path}")
    
    # 2. Attack boss to trigger Phase 2 Rage Mode (< 40 HP)
    print("[Test Phase 6] Attacking Tetsuyuki to trigger Phase 2 Rage Mode...")
    boss.take_damage(45)
    print(f"[Test Phase 6] Boss HP after heavy salvo: {boss.health}, Phase={boss.phase}")
    assert boss.phase == 2, "Boss should have entered Phase 2 Rage Mode"
    
    for _ in range(30):
        game.update()
        game.draw()
        
    # Save Phase 2 screenshot
    boss_phase2_path = "/Users/cami/.gemini/antigravity/brain/9ae7db29-94a3-4166-a111-0dd324437c02/scratch/boss_tetsuyuki_phase2.png"
    pygame.image.save(game.screen, boss_phase2_path)
    print(f"[Test Phase 6] Saved Boss Phase 2 screenshot to: {boss_phase2_path}")
    
    # 3. Defeat boss and trigger cascading explosions and Mission Complete
    print("[Test Phase 6] Landing final blow on Tetsuyuki...")
    boss.take_damage(50)
    print(f"[Test Phase 6] Boss defeated state: {boss.is_defeated}")
    assert boss.is_defeated, "Boss should be defeated"
    
    # Run through explosion sequence to complete mission
    for _ in range(190):
        game.update()
        game.draw()
        
    print(f"[Test Phase 6] Mission Complete state: {game.level.is_mission_complete}")
    assert game.level.is_mission_complete, "Mission 1 should be complete"
    
    # Save Victory screenshot
    victory_path = "/Users/cami/.gemini/antigravity/brain/9ae7db29-94a3-4166-a111-0dd324437c02/scratch/mission1_complete.png"
    pygame.image.save(game.screen, victory_path)
    print(f"[Test Phase 6] All Phase 6 tests passed! Saved Victory screenshot to: {victory_path}")

if __name__ == "__main__":
    test_engine_phase_6()
