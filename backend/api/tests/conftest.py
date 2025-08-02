import os
import sys

# Ensure project root (containing ``src``) is on ``sys.path``
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)
