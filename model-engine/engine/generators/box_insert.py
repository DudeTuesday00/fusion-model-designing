"""Grid insert / divider for a rectangular storage box.

Sized from the parent box outer dimensions + wall thickness (or direct inner
dimensions). Drops into the box with configurable clearance. Prints as a
single piece: outer frame + grid walls.
"""

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_min_wall
from ..registry import register
from .box_basic import _draw_rounded_rect, _outer_profile


@register
class BoxGridInsert(Generator):
    id = "box_insert"
    display_name = "Box Grid Insert / Divider"
    category = "Storage"
    parameters = [
        ParamSpec(name="size_mode", label="Size From", type="choice",
                  default="Outer + Wall",
                  choices=["Outer + Wall", "Inner Dimensions"]),
        ParamSpec(name="length", label="Length (X) — outer or inner", type="float",
                  default=100.0, min=25.0, max=400.0, unit="mm"),
        ParamSpec(name="width", label="Width (Y) — outer or inner", type="float",
                  default=70.0, min=25.0, max=400.0, unit="mm"),
        ParamSpec(name="box_wall", label="Parent Box Wall (Outer mode)", type="float",
                  default=2.4, min=1.2, max=12.0, unit="mm"),
        ParamSpec(name="insert_height", label="Insert Height", type="float",
                  default=40.0, min=8.0, max=200.0, unit="mm"),
        ParamSpec(name="divider_thickness", label="Divider Thickness", type="float",
                  default=1.6, min=1.0, max=5.0, unit="mm"),
        ParamSpec(name="rows", label="Rows (along width)", type="int",
                  default=2, min=1, max=12),
        ParamSpec(name="columns", label="Columns (along length)", type="int",
                  default=3, min=1, max=12),
        ParamSpec(name="fit_clearance", label="Fit Clearance (per side)", type="float",
                  default=0.4, min=0.1, max=2.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius", type="float",
                  default=4.0, min=0.0, max=30.0, unit="mm"),
        ParamSpec(name="include_frame", label="Outer frame", type="bool",
                  default=True),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        require_min_wall(params["divider_thickness"], minimum_mm=1.0)

        if params["size_mode"] == "Outer + Wall":
            inner_l = mm(params["length"]) - 2.0 * mm(params["box_wall"])
            inner_w = mm(params["width"]) - 2.0 * mm(params["box_wall"])
        else:
            inner_l = mm(params["length"])
            inner_w = mm(params["width"])

        clearance = mm(params["fit_clearance"])
        insert_l = inner_l - 2.0 * clearance
        insert_w = inner_w - 2.0 * clearance
        height = mm(params["insert_height"])
        t = mm(params["divider_thickness"])
        rows = int(params["rows"])
        cols = int(params["columns"])
        corner_r = mm(params["corner_radius"])

        if insert_l < mm(15.0) or insert_w < mm(15.0):
            raise ValueError(
                "Insert is too small - increase box size or reduce clearance/wall."
            )

        cell_l = (insert_l - (cols + 1) * t) / cols if params["include_frame"] \
            else (insert_l - (cols - 1) * t) / cols
        cell_w = (insert_w - (rows + 1) * t) / rows if params["include_frame"] \
            else (insert_w - (rows - 1) * t) / rows

        if cell_l < mm(5.0) or cell_w < mm(5.0):
            raise ValueError(
                "Cells are too small - reduce rows/columns or enlarge the insert."
            )

        # Start with a solid block, then cut cell openings (robust, one body).
        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            sketch,
            -insert_l / 2, -insert_w / 2,
            insert_l / 2, insert_w / 2,
            corner_r)
        body = geometry_utils.extrude_profile(
            component, _outer_profile(sketch), height)
        body.name = "GridInsert"

        # Cell cutouts
        cut_sketch = geometry_utils.sketch_on_xy(component)
        if params["include_frame"]:
            x0 = -insert_l / 2 + t
            y0 = -insert_w / 2 + t
        else:
            x0 = -insert_l / 2
            y0 = -insert_w / 2

        for r in range(rows):
            for c in range(cols):
                cx0 = x0 + c * (cell_l + t)
                cy0 = y0 + r * (cell_w + t)
                # Slight inset so adjacent cuts don't merge walls away
                _draw_rounded_rect(
                    cut_sketch,
                    cx0, cy0,
                    cx0 + cell_l, cy0 + cell_w,
                    min(corner_r * 0.3, cell_l * 0.2, cell_w * 0.2))

        if cut_sketch.profiles.count == 0:
            raise ValueError("Could not form cell profiles - try fewer rows/columns.")

        profiles = geometry_utils.collect(
            [cut_sketch.profiles.item(i) for i in range(cut_sketch.profiles.count)]
        )
        # Cut through with slight overshoot
        geometry_utils.extrude_cut(
            component, profiles, height + geometry_utils.mm(1.0),
            participants=[body])
