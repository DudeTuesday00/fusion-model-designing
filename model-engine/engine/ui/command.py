"""The one command this add-in exposes: "Create Print Object".

The dialog has a dropdown of every registered generator (see engine/registry.py)
and a group of inputs that gets rebuilt to match whichever generator is
selected. Adding a new generator elsewhere in the codebase makes it show up
here automatically - this file has no knowledge of specific generators.
"""

import os
import traceback

import adsk.core
import adsk.fusion

from .. import geometry_utils
from .. import generators  # noqa: F401 - importing this registers all generators
from .. import registry

_app = adsk.core.Application.get()
_ui = _app.userInterface

_CMD_ID = "printEngine_createObject"
_CMD_NAME = "Create Print Object"
_CMD_TOOLTIP = "Generate a parametric 3D-printable object (planter, creature, aquarium decor, ...)"
_WORKSPACE_ID = "FusionSolidEnvironment"
_PANEL_ID = "SolidCreatePanel"

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RESOURCE_FOLDER = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "resources", "CreatePrintObject"))

# Fusion drops event handlers that aren't referenced from somewhere long-lived,
# so every handler we create gets appended here to keep it alive.
_handlers = []


def start():
    _remove_existing_ui()

    cmd_def = _ui.commandDefinitions.addButtonDefinition(
        _CMD_ID, _CMD_NAME, _CMD_TOOLTIP, _RESOURCE_FOLDER
    )

    on_created = _CommandCreatedHandler()
    cmd_def.commandCreated.add(on_created)
    _handlers.append(on_created)

    panel = _ui.workspaces.itemById(_WORKSPACE_ID).toolbarPanels.itemById(_PANEL_ID)
    panel.controls.addCommand(cmd_def)


def stop():
    _remove_existing_ui()
    _handlers.clear()


def _remove_existing_ui():
    panel = _ui.workspaces.itemById(_WORKSPACE_ID).toolbarPanels.itemById(_PANEL_ID)
    control = panel.controls.itemById(_CMD_ID)
    if control:
        control.deleteMe()

    cmd_def = _ui.commandDefinitions.itemById(_CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


def _add_param_input(children: adsk.core.CommandInputs, spec) -> None:
    """Adds a single parameter input under `children`."""
    input_id = f"param_{spec.name}"
    if spec.type == "float":
        value_cm = geometry_utils.mm(spec.default) if spec.unit == "mm" else spec.default
        children.addValueInput(input_id, spec.label, spec.unit,
                                adsk.core.ValueInput.createByReal(value_cm))
    elif spec.type == "int":
        children.addIntegerSpinnerCommandInput(
            input_id, spec.label, int(spec.min or 0), int(spec.max or 100), 1, int(spec.default)
        )
    elif spec.type == "bool":
        children.addBoolValueInput(input_id, spec.label, True, "", spec.default)
    elif spec.type == "choice":
        dropdown = children.addDropDownCommandInput(
            input_id, spec.label, adsk.core.DropDownStyles.TextListDropDownStyle
        )
        for choice in spec.choices:
            dropdown.listItems.add(str(choice), choice == spec.default)
    elif spec.type == "string":
        children.addStringValueInput(input_id, spec.label, str(spec.default))
    else:
        raise ValueError(f"Unknown ParamSpec type: {spec.type}")


def _rebuild_param_inputs(children: adsk.core.CommandInputs, generator) -> None:
    """Clears out the parameter group and rebuilds it for the given generator.

    Parameters with a non-empty `group` are placed under nested GroupCommandInputs
    so related options (Feet, Rim, Texture, ...) stay visually organized.
    """
    for i in range(children.count - 1, -1, -1):
        children.item(i).deleteMe()

    # Preserve first-seen order of groups while collecting ungrouped params first.
    group_order = []
    grouped = {}
    ungrouped = []
    for spec in generator.parameters:
        if spec.group:
            if spec.group not in grouped:
                grouped[spec.group] = []
                group_order.append(spec.group)
            grouped[spec.group].append(spec)
        else:
            ungrouped.append(spec)

    for spec in ungrouped:
        _add_param_input(children, spec)

    for group_name in group_order:
        subgroup = children.addGroupCommandInput(f"group_{group_name}", group_name)
        subgroup.isExpanded = True
        for spec in grouped[group_name]:
            _add_param_input(subgroup.children, spec)


def _read_param_value(input_, spec):
    if spec.type == "float":
        return geometry_utils.cm_to_mm(input_.value) if spec.unit == "mm" else input_.value
    if spec.type in ("int", "bool", "string"):
        return input_.value
    if spec.type == "choice":
        return input_.selectedItem.name
    raise ValueError(f"Unknown ParamSpec type: {spec.type}")


def _find_param_input(inputs: adsk.core.CommandInputs, name: str):
    """Finds a param input by id, including nested group children."""
    direct = inputs.itemById(f"param_{name}")
    if direct:
        return direct
    for i in range(inputs.count):
        item = inputs.item(i)
        # GroupCommandInput exposes .children
        if hasattr(item, "children"):
            nested = item.children.itemById(f"param_{name}")
            if nested:
                return nested
    return None


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            generator_list = registry.list_all()
            if not generator_list:
                _ui.messageBox("No generators are registered yet.")
                return

            inputs = args.command.commandInputs

            dropdown = inputs.addDropDownCommandInput(
                "generatorDropdown", "Object Type", adsk.core.DropDownStyles.TextListDropDownStyle
            )
            for i, gen in enumerate(generator_list):
                dropdown.listItems.add(f"{gen.category}: {gen.display_name}", i == 0)

            params_group = inputs.addGroupCommandInput("paramsGroup", "Parameters")
            params_group.isExpanded = True
            _rebuild_param_inputs(params_group.children, generator_list[0])

            on_input_changed = _InputChangedHandler(generator_list)
            args.command.inputChanged.add(on_input_changed)
            _handlers.append(on_input_changed)

            on_execute = _ExecuteHandler(generator_list)
            args.command.execute.add(on_execute)
            _handlers.append(on_execute)
        except Exception:
            _ui.messageBox(f"Failed to create Print Engine dialog:\n{traceback.format_exc()}")


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self, generator_list):
        super().__init__()
        self._generator_list = generator_list

    def notify(self, args: adsk.core.InputChangedEventArgs):
        try:
            if args.input.id != "generatorDropdown":
                return
            dropdown = args.inputs.itemById("generatorDropdown")
            generator = self._generator_list[dropdown.selectedItem.index]
            params_group = args.inputs.itemById("paramsGroup")
            _rebuild_param_inputs(params_group.children, generator)
        except Exception:
            _ui.messageBox(f"Print Engine failed to update dialog:\n{traceback.format_exc()}")


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, generator_list):
        super().__init__()
        self._generator_list = generator_list

    def notify(self, args: adsk.core.CommandEventArgs):
        try:
            inputs = args.command.commandInputs
            dropdown = inputs.itemById("generatorDropdown")
            generator = self._generator_list[dropdown.selectedItem.index]

            params = {}
            for spec in generator.parameters:
                param_input = _find_param_input(inputs.itemById("paramsGroup").children, spec.name)
                if param_input is None:
                    raise ValueError(f"Missing dialog input for parameter '{spec.name}'.")
                params[spec.name] = _read_param_value(param_input, spec)

            design = adsk.fusion.Design.cast(_app.activeProduct)
            # Snapshot where existing geometry ends BEFORE building, so the
            # new object can be slid in next to it instead of on top of it.
            prior_max_x = geometry_utils.max_body_x(design)

            component = geometry_utils.new_component(design, generator.display_name)
            pre_count = component.bRepBodies.count
            pre_sketches = component.sketches.count
            generator.build(component, params)

            new_bodies = [component.bRepBodies.item(i)
                          for i in range(pre_count, component.bRepBodies.count)]
            geometry_utils.place_clear_of_existing(component, new_bodies, prior_max_x)

            # Hide the construction sketches so they don't clutter the view -
            # Fusion leaves loft/profile sketches visible after the build.
            for i in range(pre_sketches, component.sketches.count):
                component.sketches.item(i).isVisible = False
        except ValueError as exc:
            # User-facing validation failures from generators: clean message only.
            _ui.messageBox(str(exc), "Print Engine")
        except Exception:
            _ui.messageBox(f"Print Engine failed to build object:\n{traceback.format_exc()}")
