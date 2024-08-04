# test/conftest.py

import sys
import os

# Get the directory containing the src folder
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

# Add src directory to sys.path
sys.path.insert(0, src_path)
