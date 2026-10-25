import os
import sys

# Ensure bin directory is in sys.path
bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

from game import Game

if __name__ == '__main__':
    game = Game()
    game.run()
