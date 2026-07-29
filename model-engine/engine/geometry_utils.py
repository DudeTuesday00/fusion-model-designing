"""Thin wrappers around the verbose parts of the Fusion API.

Fusion's API always works in centimeters internally, no matter what units
the document displays. Since 3D-printable parts are usually thought of in
mm, use mm() when a generator receives a millimeter value from the dialog
and needs to pass it to the Fusion API.

These helpers intentionally cover only what the example generator needs.
Add more here as real generators (planter, creature, ...) need them, rather
than guessing ahead of time what every future shape will require.
"""

import math

import adsk.core
import adsk.fusion


def mm(value: float) -> float:
    """Converts millimeters to centimeters (Fusion's internal length unit)."""
    return value / 10.0


def cm_to_mm(value: float) -> float:
    """Converts centimeters (Fusion's internal length unit) back to millimeters."""
    return value * 10.0


def new_component(design: adsk.fusion.Design, name: str) -> adsk.fusion.Component:
    """Returns a component to build into - a new child component when the
    document allows it, otherwise the root component itself.

    Fusion's newer "Part Design" documents only allow a single component, so
    addNewComponent raises a RuntimeError there. Assembly/legacy documents
    take the normal path and get a named child component.
    """
    root = design.rootComponent
    try:
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occurrence.component.name = name
        return occurrence.component
    except RuntimeError:
        return root


def sketch_on_xy(component: adsk.fusion.Component) -> adsk.fusion.Sketch:
    """Creates a new sketch on the component's XY construction plane."""
    return component.sketches.add(component.xYConstructionPlane)


def draw_circle(sketch: adsk.fusion.Sketch, radius_cm: float,
                 center: adsk.core.Point3D = None) -> adsk.fusion.SketchCircle:
    """Draws a circle on `sketch` and returns it. Center defaults to the origin."""
    center = center or adsk.core.Point3D.create(0, 0, 0)
    return sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius_cm)


def offset_plane(component: adsk.fusion.Component, z_cm: float) -> adsk.fusion.ConstructionPlane:
    """Creates a construction plane parallel to XY, z_cm above it."""
    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(component.xYConstructionPlane,
                             adsk.core.ValueInput.createByReal(z_cm))
    return planes.add(plane_input)


def draw_polygon(sketch: adsk.fusion.Sketch, sides: int, flats_radius_cm: float,
                  z_cm: float = 0.0, corner_radius_cm: float = 0.0,
                  center_x: float = 0.0, center_y: float = 0.0) -> None:
    """Draws a regular polygon sized by its across-flats radius (half the
    width measured face-to-face - more intuitive than corner-to-corner when
    you're thinking 'how wide is this pot').

    Vertices are placed so flat faces line up with the X/Y axes. Pass a
    corner_radius to round every corner. Points go through
    modelToSketchSpace so this works on offset construction planes too.
    """
    circum_r = flats_radius_cm / math.cos(math.pi / sides)
    pts = []
    for i in range(sides):
        angle = math.pi / sides + 2.0 * math.pi * i / sides
        pts.append(sketch.modelToSketchSpace(adsk.core.Point3D.create(
            center_x + circum_r * math.cos(angle),
            center_y + circum_r * math.sin(angle), z_cm)))

    lines_col = sketch.sketchCurves.sketchLines
    lines = [lines_col.addByTwoPoints(pts[i], pts[(i + 1) % sides]) for i in range(sides)]

    if corner_radius_cm > 1e-6:
        arcs = sketch.sketchCurves.sketchArcs
        for i in range(sides):
            # Round the corner where the previous line ends and this one starts.
            arcs.addFillet(lines[i - 1], pts[i], lines[i], pts[i], corner_radius_cm)


def loft_between(component: adsk.fusion.Component, profiles: list, operation,
                  participants=None):
    """Lofts through `profiles` (bottom to top). For NewBody operations the
    created body is returned; for cuts, pass `participants` to limit which
    bodies get carved (same safety reasoning as extrude_cut)."""
    lofts = component.features.loftFeatures
    loft_input = lofts.createInput(operation)
    for profile in profiles:
        loft_input.loftSections.add(profile)
    if participants:
        loft_input.participantBodies = list(participants)
    feature = lofts.add(loft_input)
    if operation == adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        return feature.bodies.item(0)
    return None


def build_polygon_shell(component: adsk.fusion.Component, sides: int,
                         outer_bottom_r: float, outer_top_r: float,
                         inner_floor_r: float, inner_top_r: float,
                         height_cm: float, base_cm: float,
                         outer_corner_r: float = 0.0,
                         inner_corner_r: float = 0.0) -> adsk.fusion.BRepBody:
    """Builds a hollow tapered polygon vessel (pot, tray, tower...) and
    returns its body.

    Outer shell lofts bottom->top polygon; the cavity is loft-cut from a
    floor polygon (at base_cm) to an inner top polygon. All radii are
    across-flats. The cavity cut only touches the body built here, so it's
    safe next to other objects.
    """
    top_plane = offset_plane(component, height_cm)

    bottom_sketch = sketch_on_xy(component)
    draw_polygon(bottom_sketch, sides, outer_bottom_r, 0.0, outer_corner_r)
    top_sketch = component.sketches.add(top_plane)
    draw_polygon(top_sketch, sides, outer_top_r, height_cm, outer_corner_r)
    body = loft_between(
        component,
        [bottom_sketch.profiles.item(0), top_sketch.profiles.item(0)],
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )

    floor_plane = offset_plane(component, base_cm)
    floor_sketch = component.sketches.add(floor_plane)
    draw_polygon(floor_sketch, sides, inner_floor_r, base_cm, inner_corner_r)
    cavity_top_sketch = component.sketches.add(top_plane)
    draw_polygon(cavity_top_sketch, sides, inner_top_r, height_cm, inner_corner_r)
    loft_between(
        component,
        [floor_sketch.profiles.item(0), cavity_top_sketch.profiles.item(0)],
        adsk.fusion.FeatureOperations.CutFeatureOperation,
        participants=[body],
    )
    return body


def sketch_on_xz(component: adsk.fusion.Component) -> adsk.fusion.Sketch:
    """Creates a new sketch on the component's XZ construction plane.

    Useful for profiles that will be revolved around the Z (vertical) axis.
    """
    return component.sketches.add(component.xZConstructionPlane)


def sketch_on_yz_at_x(component: adsk.fusion.Component, x_cm: float = 0.0) -> adsk.fusion.Sketch:
    """Creates a new sketch on a plane normal to X (spanning Y and Z),
    offset to the given x_cm. At x_cm=0 this is just the YZ construction
    plane itself; useful for profiles/paths built in the Y-Z plane, e.g. a
    handle loop mounted on a wall whose normal points along Y."""
    if abs(x_cm) < 1e-9:
        return component.sketches.add(component.yZConstructionPlane)
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(component.yZConstructionPlane,
                             adsk.core.ValueInput.createByReal(x_cm))
    plane = component.constructionPlanes.add(plane_input)
    return component.sketches.add(plane)


def draw_closed_profile_rz(sketch: adsk.fusion.Sketch, rz_points: list) -> None:
    """Draws a closed polyline from (radius, height) pairs on an XZ-plane sketch.

    Each (r, z) pair is treated as the MODEL-space point (x=r, y=0, z=z) and
    converted into the sketch's own coordinate system with modelToSketchSpace.
    That conversion matters: Fusion's sketch axes on construction planes don't
    always point the way you'd guess, and going through model space sidesteps
    the problem entirely. Values are in cm (Fusion's internal unit).
    """
    lines = sketch.sketchCurves.sketchLines
    pts = [
        sketch.modelToSketchSpace(adsk.core.Point3D.create(r, 0, z))
        for (r, z) in rz_points
    ]
    for i in range(len(pts)):
        lines.addByTwoPoints(pts[i], pts[(i + 1) % len(pts)])


def revolve_profile(component: adsk.fusion.Component, profile: adsk.fusion.Profile,
                     angle_deg: float = 360.0) -> adsk.fusion.BRepBody:
    """Revolves `profile` around the component's Z axis into a new body."""
    revolves = component.features.revolveFeatures
    revolve_input = revolves.createInput(
        profile, component.zConstructionAxis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )
    angle = adsk.core.ValueInput.createByReal(math.radians(angle_deg))
    revolve_input.setAngleExtent(False, angle)
    revolve_feature = revolves.add(revolve_input)
    return revolve_feature.bodies.item(0)


def extrude_cut(component: adsk.fusion.Component, profiles,
                 distance_cm: float, participants=None) -> adsk.fusion.ExtrudeFeature:
    """Cuts `profiles` (one Profile or an ObjectCollection of them) upward
    (+Z from the sketch plane).

    Pass `participants` (a list of bodies) to limit which bodies get cut.
    Without it, Fusion cuts EVERY body the extrusion passes through - which
    silently mangles unrelated objects sitting nearby, so generators should
    always pass their own body here.
    """
    extrudes = component.features.extrudeFeatures
    extent = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(distance_cm)
    )
    cut_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    if participants:
        cut_input.participantBodies = list(participants)
    return extrudes.add(cut_input)


def extrude_join(component: adsk.fusion.Component, profiles,
                  distance_cm: float, target_body=None) -> None:
    """Extrudes `profiles` upward (+Z) and merges the result into `target_body`.

    The Fusion API's plain join operation merges with EVERY body the new
    volume overlaps (and participantBodies only works for cuts), so joining
    near other objects would silently fuse them together. To stay safe this
    extrudes as separate new bodies first, then uses a Combine feature that
    explicitly targets only `target_body`. If target_body is None the raw
    merge-with-anything join is used - only do that in an empty design.
    """
    extrudes = component.features.extrudeFeatures
    extent = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(distance_cm)
    )
    if target_body is None:
        join_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        join_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrudes.add(join_input)
        return

    new_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    new_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    feature = extrudes.add(new_input)
    tools = collect([feature.bodies.item(i) for i in range(feature.bodies.count)])
    combines = component.features.combineFeatures
    combine_input = combines.createInput(target_body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    combines.add(combine_input)


def max_body_x(design: adsk.fusion.Design):
    """Returns the largest world-space X reached by any body in the design,
    or None if the design has no bodies yet. Used to place new objects clear
    of existing ones."""
    max_x = None
    bodies = [design.rootComponent.bRepBodies.item(i)
              for i in range(design.rootComponent.bRepBodies.count)]
    for occ in design.rootComponent.allOccurrences:
        bodies.extend(occ.bRepBodies.item(i) for i in range(occ.bRepBodies.count))
    for body in bodies:
        x = body.boundingBox.maxPoint.x
        if max_x is None or x > max_x:
            max_x = x
    return max_x


def move_bodies_x(component: adsk.fusion.Component, bodies, dx_cm: float) -> None:
    """Translates `bodies` (a Python list) along X by dx_cm."""
    if not bodies or abs(dx_cm) < 1e-6:
        return
    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(dx_cm, 0.0, 0.0)
    move_features = component.features.moveFeatures
    move_input = move_features.createInput(collect(bodies), transform)
    move_features.add(move_input)


def place_clear_of_existing(component: adsk.fusion.Component, new_bodies,
                             prior_max_x, gap_mm: float = 20.0) -> None:
    """Slides freshly built bodies along +X so they sit `gap_mm` beyond
    whatever already existed (prior_max_x from max_body_x BEFORE building).
    Does nothing when the design was empty - the first object stays at the
    origin, which is where you want it for a single-piece export."""
    if prior_max_x is None or not new_bodies:
        return
    min_x = min(b.boundingBox.minPoint.x for b in new_bodies)
    move_bodies_x(component, new_bodies, prior_max_x + mm(gap_mm) - min_x)


def revolve_cut(component: adsk.fusion.Component, profile,
                 participants=None) -> adsk.fusion.RevolveFeature:
    """Revolves `profile` a full turn around the Z axis as a CUT, limited to
    `participants` (same safety reasoning as extrude_cut)."""
    revolves = component.features.revolveFeatures
    revolve_input = revolves.createInput(
        profile, component.zConstructionAxis,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
    )
    revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2.0 * math.pi))
    if participants:
        revolve_input.participantBodies = list(participants)
    return revolves.add(revolve_input)


def extrude_cut_symmetric(component: adsk.fusion.Component, profiles,
                           total_length_cm: float, participants=None) -> adsk.fusion.ExtrudeFeature:
    """Cuts `profiles` symmetrically to BOTH sides of their sketch plane
    (total_length_cm overall). Useful when the sketch sits on an offset
    construction plane whose normal direction is hard to predict - cutting
    both ways means the side facing open air simply does nothing."""
    extrudes = component.features.extrudeFeatures
    cut_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(total_length_cm), True)
    if participants:
        cut_input.participantBodies = list(participants)
    return extrudes.add(cut_input)


def extrude_symmetric(component: adsk.fusion.Component, profiles,
                       total_length_cm: float) -> adsk.fusion.BRepBody:
    """Extrudes `profiles` symmetrically to both sides of the sketch plane as
    a new body. Like extrude_cut_symmetric, this sidesteps not knowing which
    way an offset construction plane's normal points."""
    extrudes = component.features.extrudeFeatures
    new_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    new_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(total_length_cm), True)
    return extrudes.add(new_input).bodies.item(0)


def extrude_symmetric_all(component: adsk.fusion.Component, profiles,
                           total_length_cm: float) -> list:
    """Like extrude_symmetric but returns ALL created bodies (one per
    disjoint profile) instead of just the first."""
    extrudes = component.features.extrudeFeatures
    new_input = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    new_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(total_length_cm), True)
    feature = extrudes.add(new_input)
    return [feature.bodies.item(i) for i in range(feature.bodies.count)]


def angled_plane_through_x(component: adsk.fusion.Component, z_cm: float,
                            angle_deg: float) -> adsk.fusion.ConstructionPlane:
    """A plane through (any x, y=0, z=z_cm), tilted by angle_deg about a line
    running in +X at that height. At angle 0 it's horizontal; increasing
    angle raises the +Y side and lowers the -Y side (a knife blade hinged
    along X). Used for slicing a solid of revolution at a tilt - e.g. a
    scoop's angled mouth."""
    hinge_plane = offset_plane(component, z_cm)
    hinge_sketch = component.sketches.add(hinge_plane)
    big = 1000.0
    p0 = hinge_sketch.modelToSketchSpace(adsk.core.Point3D.create(-big, 0, z_cm))
    p1 = hinge_sketch.modelToSketchSpace(adsk.core.Point3D.create(big, 0, z_cm))
    hinge_line = hinge_sketch.sketchCurves.sketchLines.addByTwoPoints(p0, p1)

    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByAngle(hinge_line, adsk.core.ValueInput.createByReal(
        math.radians(angle_deg)), hinge_plane)
    return planes.add(plane_input)


def cut_half_space(component: adsk.fusion.Component, plane: adsk.fusion.ConstructionPlane,
                    reach_cm: float, participants, on_plane_point=None,
                    flip: bool = False) -> None:
    """Cuts away everything on one side of `plane` (a big disc extruded
    one-sided). `on_plane_point` is a world-space Point3D that actually lies
    ON the plane, used to center the cutting circle correctly - a sketch's
    local (0,0) is NOT generally the projection of the world origin's
    in-plane component onto an arbitrary construction plane, so world-origin
    center will silently mis-place the cut on any non-default plane. Flip
    the direction with `flip` if the wrong side gets cut - which side is
    "positive" depends on how the plane was constructed and isn't knowable
    without checking, so callers should verify visually."""
    sketch = component.sketches.add(plane)
    if on_plane_point is None:
        on_plane_point = adsk.core.Point3D.create(0, 0, 0)
    center = sketch.modelToSketchSpace(on_plane_point)
    draw_circle(sketch, reach_cm * 3.0, center)
    direction = (adsk.fusion.ExtentDirections.NegativeExtentDirection if flip
                 else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrudes = component.features.extrudeFeatures
    cut_input = extrudes.createInput(sketch.profiles.item(0),
                                      adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_input.setOneSideExtent(
        adsk.fusion.DistanceExtentDefinition.create(
            adsk.core.ValueInput.createByReal(reach_cm)),
        direction)
    cut_input.participantBodies = list(participants)
    extrudes.add(cut_input)


def fillet_edges(component: adsk.fusion.Component, edges, radius_cm: float) -> None:
    """Rounds the given edges (a Python list) with a constant radius."""
    fillets = component.features.filletFeatures
    fillet_input = fillets.createInput()
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
        collect(edges), adsk.core.ValueInput.createByReal(radius_cm), True
    )
    fillets.add(fillet_input)


def edges_at_height(body: adsk.fusion.BRepBody, z_cm: float, tol: float = 1e-4) -> list:
    """Returns the body's edges that lie entirely in the horizontal plane at
    z_cm - e.g. the rim edges of a pot whose opening is at that height."""
    found = []
    for i in range(body.edges.count):
        edge = body.edges.item(i)
        bb = edge.boundingBox
        if abs(bb.minPoint.z - z_cm) < tol and abs(bb.maxPoint.z - z_cm) < tol:
            found.append(edge)
    return found


def combine_join(component: adsk.fusion.Component, target_body,
                  tool_bodies) -> adsk.fusion.CombineFeature:
    """Fuses `tool_bodies` (a Python list) into `target_body` - the explicit,
    can't-grab-the-neighbors way to merge bodies."""
    combines = component.features.combineFeatures
    combine_input = combines.createInput(target_body, collect(tool_bodies))
    combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    return combines.add(combine_input)


def circular_pattern(component: adsk.fusion.Component, feature, count: int) -> None:
    """Repeats `feature` (or a list of features that belong together, e.g. a
    loft + the combine that fuses it) around the Z axis, evenly spread over
    360 degrees. `count` is the total including the original."""
    patterns = component.features.circularPatternFeatures
    entities = collect(feature if isinstance(feature, list) else [feature])
    pattern_input = patterns.createInput(entities, component.zConstructionAxis)
    pattern_input.quantity = adsk.core.ValueInput.createByReal(count)
    pattern_input.totalAngle = adsk.core.ValueInput.createByString("360 deg")
    pattern_input.isSymmetric = False
    patterns.add(pattern_input)


def collect(items) -> adsk.core.ObjectCollection:
    """Wraps a Python list of Fusion objects into the ObjectCollection many
    API calls require instead of a plain list."""
    collection = adsk.core.ObjectCollection.create()
    for item in items:
        collection.add(item)
    return collection


def extrude_profile(component: adsk.fusion.Component, profile: adsk.fusion.Profile,
                     distance_cm: float) -> adsk.fusion.BRepBody:
    """Extrudes `profile` by distance_cm as a new solid body and returns that body."""
    extrudes = component.features.extrudeFeatures
    extent = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(distance_cm)
    )
    extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrude_feature = extrudes.add(extrude_input)
    return extrude_feature.bodies.item(0)
