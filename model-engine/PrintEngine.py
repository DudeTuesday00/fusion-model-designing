"""Entry point for the Print Engine Fusion 360 add-in.

Fusion looks for run(context) and stop(context) in a .py file that has the
same name as its parent folder - that's how it finds this file. Everything
else lives under engine/ so this file stays a thin wrapper.
"""

import traceback
import adsk.core

from .engine.ui import command as create_object_command


def run(context):
    try:
        create_object_command.start()
    except Exception:
        _show_error("Print Engine failed to start")


def stop(context):
    try:
        create_object_command.stop()
    except Exception:
        _show_error("Print Engine failed to stop cleanly")


def _show_error(title):
    # Fusion swallows exceptions raised from run()/stop() silently otherwise,
    # so surface them in a message box with the full traceback.
    ui = adsk.core.Application.get().userInterface
    ui.messageBox(f"{title}:\n{traceback.format_exc()}")
