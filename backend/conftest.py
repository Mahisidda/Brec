# backend/conftest.py
import sys
import os

# Prepend the backend directory itself so "app" is importable
root = os.path.abspath(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)
