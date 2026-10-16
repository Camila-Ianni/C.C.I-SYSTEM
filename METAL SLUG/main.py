"""
METAL SLUG: SUPER VEHICLE-001 (SNK Arcade Replica in pygame-ce)
Entry point of the game application.
"""
import sys
import os

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
