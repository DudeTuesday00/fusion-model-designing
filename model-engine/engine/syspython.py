"""Finds a system Python that has numpy.

Fusion's bundled Python has no numpy and can't pip-install into itself
safely, so the mesh backend runs on the user's own Python installation in a
subprocess. This module locates it once and caches the result.
"""

import glob
import os
import shutil
import subprocess

# Prevents a console window flashing up when Fusion spawns the subprocess.
CREATE_NO_WINDOW = 0x08000000

_cached_path = None


def _candidates():
    found = []
    which = shutil.which("python")
    if which:
        found.append(which)
    found.extend(glob.glob(os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\Python\Python3*\python.exe")))
    found.extend(glob.glob(r"C:\Python3*\python.exe"))
    return found


def find_system_python() -> str:
    """Returns the path to a Python with numpy, or raises with instructions."""
    global _cached_path
    if _cached_path:
        return _cached_path

    tried = []
    for candidate in _candidates():
        if not candidate or not os.path.exists(candidate) or candidate in tried:
            continue
        tried.append(candidate)
        try:
            result = subprocess.run(
                [candidate, "-c", "import numpy"],
                capture_output=True, timeout=30, creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                _cached_path = candidate
                return candidate
        except Exception:
            continue

    raise ValueError(
        "Couldn't find a system Python with numpy installed (needed for mesh "
        "textures). Install Python from python.org, then run: pip install numpy\n"
        "Checked: " + (", ".join(tried) if tried else "nothing found")
    )
