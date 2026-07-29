"""The one command this add-in exposes: "Create Print Object".

The dialog has a dropdown of every registered generator (see engine/registry.py)
and a group of inputs that gets rebuilt to match whichever generator is
selected. Adding a new generator elsewhere in the codebase makes it show up
here automatically - this file has no knowledge of specific generators.

Supports:
- Parameter subgroups via ParamSpec.group
- Last-used values loaded/saved per generator (engine/prefs.py)
- Live preview via executePreview (temporary only; OK always runs execute)
"""

import os
import traceback

import adsk.core
import adsk.fusion

from .. import geometry_utils
from .. import generators  # noqa: F401 - importing this registers all generators
from .. import prefs
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

# Generators that are too heavy or non-transactional for live preview.
_SKIP_PREVIEW_IDS = {
    "planter_with_tray",  # full planter + tray is too expensive on every change
    "planter_textured",
    "planter_drip_tray_textured",
    "planter_tray_mesh",
    "creature_axolotl",
}


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


def _add_param_input(children: adsk.core.CommandInputs, spec, saved_value=None) -> None:
    """Adds a single parameter input under `children`, optionally prefilled."""
    input_id = f"param_{spec.name}"
    default = saved_value if saved_value is not None else spec.default

    if spec.type == "float":
        try:
            default = float(default)
        except (TypeError, ValueError):
            default = spec.default
        value_cm = geometry_utils.mm(default) if spec.unit == "mm" else default
        children.addValueInput(input_id, spec.label, spec.unit,
                                adsk.core.ValueInput.createByReal(value_cm))
    elif spec.type == "int":
        try:
            default = int(default)
        except (TypeError, ValueError):
            default = int(spec.default)
        children.addIntegerSpinnerCommandInput(
            input_id, spec.label, int(spec.min or 0), int(spec.max or 100), 1, default
        )
    elif spec.type == "bool":
        if not isinstance(default, bool):
            default = bool(default)
        children.addBoolValueInput(input_id, spec.label, True, "", default)
    elif spec.type == "choice":
        dropdown = children.addDropDownCommandInput(
            input_id, spec.label, adsk.core.DropDownStyles.TextListDropDownStyle
        )
        default_str = str(default)
        matched = False
        for choice in spec.choices:
            is_selected = str(choice) == default_str
            if is_selected:
                matched = True
            dropdown.listItems.add(str(choice), is_selected)
        if not matched and dropdown.listItems.count > 0:
            dropdown.listItems.item(0).isSelected = True
    elif spec.type == "string":
        children.addStringValueInput(input_id, spec.label, str(default))
    else:
        raise ValueError(f"Unknown ParamSpec type: {spec.type}")


def _rebuild_param_inputs(children: adsk.core.CommandInputs, generator,
                           saved: dict = None) -> None:
    """Clears out the parameter group and rebuilds it for the given generator.

    Parameters with a non-empty `group` are placed under nested GroupCommandInputs.
    """
    saved = saved or {}
    for i in range(children.count - 1, -1, -1):
        children.item(i).deleteMe()

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
        _add_param_input(children, spec, saved.get(spec.name))

    for group_name in group_order:
        subgroup = children.addGroupCommandInput(f"group_{group_name}", group_name)
        subgroup.isExpanded = True
        for spec in grouped[group_name]:
            _add_param_input(subgroup.children, spec, saved.get(spec.name))


def _read_param_value(input_, spec):
    if spec.type == "float":
        return geometry_utils.cm_to_mm(input_.value) if spec.unit == "mm" else input_.value
    if spec.type in ("int", "bool", "string"):
        return input_.value
    if spec.type == "choice":
        selected = input_.selectedItem
        if selected is None:
            raise ValueError(f"No selection for '{spec.label}'.")
        return selected.name
    raise ValueError(f"Unknown ParamSpec type: {spec.type}")


def _find_param_input(inputs: adsk.core.CommandInputs, name: str):
    """Finds a param input by id, including nested group children."""
    target = f"param_{name}"
    direct = inputs.itemById(target)
    if direct:
        return direct
    for i in range(inputs.count):
        item = inputs.item(i)
        group = adsk.core.GroupCommandInput.cast(item)
        if group:
            nested = group.children.itemById(target)
            if nested:
                return nested
    return None


def _collect_params(inputs: adsk.core.CommandInputs, generator) -> dict:
    params_group = adsk.core.GroupCommandInput.cast(inputs.itemById("paramsGroup"))
    if not params_group:
        raise ValueError("Parameters group is missing from the dialog.")
    children = params_group.children
    params = {}
    for spec in generator.parameters:
        param_input = _find_param_input(children, spec.name)
        if param_input is None:
            raise ValueError(f"Missing dialog input for parameter '{spec.name}'.")
        params[spec.name] = _read_param_value(param_input, spec)
    return params


def _should_skip_preview(generator) -> bool:
    gen_id = getattr(generator, "id", "") or ""
    if gen_id in _SKIP_PREVIEW_IDS:
        return True
    if gen_id.endswith("_textured") or "mesh" in gen_id:
        return True
    if getattr(generator, "category", "") in ("Creature",):
        return True
    return False


def _build_into_design(generator, params: dict):
    """Shared geometry path for execute and executePreview."""
    design = adsk.fusion.Design.cast(_app.activeProduct)
    prior_max_x = geometry_utils.max_body_x(design)

    component = geometry_utils.new_component(design, generator.display_name)
    pre_count = component.bRepBodies.count
    pre_sketches = component.sketches.count
    generator.build(component, params)

    new_bodies = [component.bRepBodies.item(i)
                  for i in range(pre_count, component.bRepBodies.count)]
    geometry_utils.place_clear_of_existing(component, new_bodies, prior_max_x)

    for i in range(pre_sketches, component.sketches.count):
        component.sketches.item(i).isVisible = False


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            generator_list = registry.list_all()
            if not generator_list:
                _ui.messageBox("No generators are registered yet.")
                return

            cmd = args.command
            inputs = cmd.commandInputs

            cmd.isExecutedWhenPreEmpted = False

            dropdown = inputs.addDropDownCommandInput(
                "generatorDropdown", "Object Type",
                adsk.core.DropDownStyles.TextListDropDownStyle
            )
            for i, gen in enumerate(generator_list):
                dropdown.listItems.add(f"{gen.category}: {gen.display_name}", i == 0)

            params_group = inputs.addGroupCommandInput("paramsGroup", "Parameters")
            params_group.isExpanded = True
            saved = prefs.load_for(generator_list[0].id)
            _rebuild_param_inputs(params_group.children, generator_list[0], saved)

            on_input_changed = _InputChangedHandler(generator_list)
            cmd.inputChanged.add(on_input_changed)
            _handlers.append(on_input_changed)

            on_preview = _PreviewHandler(generator_list)
            cmd.executePreview.add(on_preview)
            _handlers.append(on_preview)

            on_execute = _ExecuteHandler(generator_list)
            cmd.execute.add(on_execute)
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
            group = adsk.core.GroupCommandInput.cast(params_group)
            if not group:
                return
            saved = prefs.load_for(generator.id)
            _rebuild_param_inputs(group.children, generator, saved)
        except Exception:
            _ui.messageBox(f"Print Engine failed to update dialog:\n{traceback.format_exc()}")


class _PreviewHandler(adsk.core.CommandEventHandler):
    """Shows temporary geometry while the dialog is open.

    IMPORTANT: always leave isValidResult = False so Fusion still fires the
    execute handler on OK. If isValidResult is True, Fusion may skip execute
    entirely, which is why OK appeared to do nothing for complex builds.
    """

    def __init__(self, generator_list):
        super().__init__()
        self._generator_list = generator_list

    def notify(self, args: adsk.core.CommandEventArgs):
        # Never treat preview as the final result — execute always owns the
        # permanent build + preference save.
        args.isValidResult = False
        try:
            inputs = args.command.commandInputs
            dropdown = inputs.itemById("generatorDropdown")
            generator = self._generator_list[dropdown.selectedItem.index]

            if _should_skip_preview(generator):
                return

            params = _collect_params(inputs, generator)
            _build_into_design(generator, params)
        except ValueError:
            pass  # invalid params during edit — no preview until fixed
        except Exception:
            pass  # keep dialog responsive; execute will surface real errors


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, generator_list):
        super().__init__()
        self._generator_list = generator_list

    def notify(self, args: adsk.core.CommandEventArgs):
        try:
            inputs = args.command.commandInputs
            dropdown = inputs.itemById("generatorDropdown")
            generator = self._generator_list[dropdown.selectedItem.index]

            params = _collect_params(inputs, generator)
            prefs.save_for(generator.id, params)
            _build_into_design(generator, params)
        except ValueError as exc:
            _ui.messageBox(str(exc), "Print Engine")
        except Exception:
            _ui.messageBox(f"Print Engine failed to build object:\n{traceback.format_exc()}")
