"""Executable validation suite for the QECTOR plugin and reference manual."""

import os
import sys

_PYTHON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"
)
if _PYTHON_DIR not in sys.path:
    sys.path.insert(0, _PYTHON_DIR)
