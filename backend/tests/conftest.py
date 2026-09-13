"""Global pytest fixtures and path initialization."""

import sys
import os

# Ensure backend root is always in Python module search path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
