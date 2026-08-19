"""Repo-root pytest bootstrap.

Adds ``python/`` to ``sys.path`` so ``from qector_math_ground_truth import
...`` keeps working from ``tests/`` without changing any test imports.
qector_math_ground_truth.py lives at ``python/qector_math_ground_truth.py``,
not at repo root, to keep repo root free of loose importable modules.
"""

import os
import sys

_PYTHON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")
if _PYTHON_DIR not in sys.path:
    sys.path.insert(0, _PYTHON_DIR)
