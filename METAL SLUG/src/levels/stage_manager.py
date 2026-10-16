"""
Stage and Mission Progression Manager for Metal Slug 1 (Phases 7 & 8).
Handles:
- Dynamic loading and progression across Mission 1 through Mission 6.
- Stage transitions upon boss defeat.
- Cumulative score, lives, and P.O.W. tallies across the campaign.
"""
import pygame
from src.levels.mission1 import Mission1
from src.levels.mission2 import Mission2
from src.levels.mission3 import Mission3
from src.levels.mission4 import Mission4
from src.levels.mission5 import Mission5
from src.levels.mission6 import Mission6

class StageManager:
    def __init__(self):
        self.current_mission_index = 1
        self.max_missions = 6
        self.active_level = None
        self.total_rescued_pows = 0
        self.load_mission(1)

    def load_mission(self, mission_num):
        self.current_mission_index = mission_num
        mission_classes = {
            1: Mission1,
            2: Mission2,
            3: Mission3,
            4: Mission4,
            5: Mission5,
            6: Mission6,
        }
        level_cls = mission_classes.get(mission_num, Mission1)
        self.active_level = level_cls()

    def advance_to_next_mission(self):
        if self.current_mission_index < self.max_missions:
            self.load_mission(self.current_mission_index + 1)
            return True
        return False
