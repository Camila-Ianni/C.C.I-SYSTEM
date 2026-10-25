import os
import sys
import runpy

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

if __name__ == '__main__':
    runpy.run_module('sonic', run_name='__main__')
