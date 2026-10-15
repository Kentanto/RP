"""Athas game package.

The env var must be set before pygame is imported anywhere, so it lives here
at the very top of the package.
"""
import os as _os

_os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
