"""Command: Export visible B-rep bodies as STL or 3MF."""

import traceback

import adsk.core
import adsk.fusion

from .. import export_utils

_app = adsk.core.Application.get()
_ui = _app.userInterface

_CMD_ID = "printEngine_exportBodies"
_CMD_NAME = "Export Print Bodies"
_CMD_TOOLTIP = "Export visible solid bodies as STL or 3MF into the generated folder"
_WORKSPACE_ID = "FusionSolidEnvironment"
_PANEL_ID = "SolidCreatePanel"

_handlers = []


def start():
    _remove_existing()
    cmd_def = _ui.commandDefinitions.addButtonDefinition(
        _CMD_ID, _CMD_NAME, _CMD_TOOLTIP, ""
    )
    on_created = _CreatedHandler()
    cmd_def.commandCreated.add(on_created)
    _handlers.append(on_created)
    panel = _ui.workspaces.itemById(_WORKSPACE_ID).toolbarPanels.itemById(_PANEL_ID)
    panel.controls.addCommand(cmd_def)


def stop():
    _remove_existing()
    _handlers.clear()


def _remove_existing():
    panel = _ui.workspaces.itemById(_WORKSPACE_ID).toolbarPanels.itemById(_PANEL_ID)
    control = panel.controls.itemById(_CMD_ID)
    if control:
        control.deleteMe()
    cmd_def = _ui.commandDefinitions.itemById(_CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            inputs = args.command.commandInputs
            fmt = inputs.addDropDownCommandInput(
                "format", "Format", adsk.core.DropDownStyles.TextListDropDownStyle
            )
            fmt.listItems.add("STL", True)
            fmt.listItems.add("3MF", False)
            inputs.addStringValueInput("prefix", "Filename prefix", "print_object")

            on_execute = _ExecuteHandler()
            args.command.execute.add(on_execute)
            _handlers.append(on_execute)
        except Exception:
            _ui.messageBox(f"Failed to create export dialog:\n{traceback.format_exc()}")


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args: adsk.core.CommandEventArgs):
        try:
            inputs = args.command.commandInputs
            fmt = inputs.itemById("format").selectedItem.name.lower()
            prefix = inputs.itemById("prefix").value.strip() or "print_object"

            design = adsk.fusion.Design.cast(_app.activeProduct)
            bodies = export_utils.collect_visible_brep_bodies(design)
            if not bodies:
                _ui.messageBox("No visible solid bodies to export.", "Print Engine")
                return

            paths = export_utils.export_bodies(bodies, fmt=fmt, name_prefix=prefix)
            listing = "\n".join(paths)
            _ui.messageBox(
                f"Exported {len(paths)} file(s):\n\n{listing}",
                "Print Engine",
            )
        except ValueError as exc:
            _ui.messageBox(str(exc), "Print Engine")
        except Exception:
            _ui.messageBox(f"Export failed:\n{traceback.format_exc()}", "Print Engine")
