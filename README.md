# Print Engine

A Fusion 360 add-in for generating 3D-printable objects parametrically:
planters first, then fantasy creatures (dragons, animals, etc.) and aquarium
decor (coral, castles, treasure chests, rocks, etc.).

The idea is one extensible "engine" inside Fusion 360: pick an object type
from a dialog, enter a few parameters (height, diameter, style...), and it
builds the geometry for you. New object types get added as separate
generator modules without touching the core.

## What's here so far

This first pass is the **engine core**, not a finished product:

- A working Fusion 360 add-in (`PrintEngine/`) with one command, "Create
  Print Object", added to the CREATE panel.
- A generator plugin system: any object type implements a small `Generator`
  class describing its parameters and how to build its geometry.
- **Basic Planter** generator: a tapered, hollowed pot in four shapes -
  round, hexagon, square with rounded corners, or terracotta (the classic
  clay flowerpot: tapered body with a thick collar ringing the rim,
  adjustable collar height/protrusion, smooth interior, chamfered collar
  underside so it prints supportless) - with adjustable
  top/bottom width, height, wall thickness, base thickness, and an
  optional drainage hole pattern. For hex/square, widths are measured
  across the flats. Finishing options: a Rounded rim style (any shape);
  flutes (round pots) in Straight, Spiral (set the twist angle), or
  CrissCross (two opposing spiral sets forming a diamond lattice), each
  either Recessed (carved grooves) or Raised (protruding ribs); and
  surface textures (round pots): Ribbed wave rings (also recessed or
  raised), Bubbles dimple field, or Bark striations, each with adjustable
  depth.
- **Drip Tray / Saucer** generator: enter your planter's bottom width and
  shape and it produces a matching saucer with clearance, a flared wall, and
  L-shaped support ribs - the foot of each L lifts the pot off the floor so
  water can collect and evaporate, and the vertical leg centers the pot in
  the tray. Polygon trays put one rib on each flat side. Both tray
  generators offer a Base Style - Flat, Bun Feet, Block Feet, Hex Feet, or
  a ceramic-style raised Foot Ring - with adjustable foot height/size, and
  a Feet Attachment choice: "Separate (glue-on)" keeps the tray's bottom
  flat and printable without supports (feet print as separate pegged
  pieces that glue into shallow alignment sockets), while "Integrated"
  fuses the feet on (needs supports under the raised base). Round trays
  can also take a Scalloped rim finish.
- **Plant Stand (Round)** generator: a raised drip platform plus separate
  pegged legs (3-6, adjustable length/diameter) that glue into sockets in
  the platform's underside - elevates a pot like a piece of furniture, and
  every part prints flat with no supports.
- **Plant Stand (2-Piece Cross)** generator: two flat H-shaped plates with
  half-lap slots that slide together into a perpendicular X - no glue, no
  supports, packs flat. The pot rests on the crossed bars between four
  upright retaining arms (set Arm Height to 0 for a plain riser). Arm
  spacing sizes itself from the pot's bottom diameter; the slot width
  comes from plate thickness + fit clearance.
- **Self-Watering Insert** generator (round pots): a platform standing on a
  central wick cup. Print the pot with zero drainage holes, drop the insert
  in, and the space below becomes a water reservoir; soil packed down into
  the cup wicks water up to the roots. Includes aeration holes and a fill
  hole for watering directly into the reservoir.
- **Drip Tray for Textured Planter** generator: enter the same silhouette
  numbers you used for a Textured Planter (profile, diameters, height,
  bulge, texture depth) and it reconstructs the pot's true outer envelope
  and flares the tray wall automatically so the bulged, textured pot always
  drops in with the requested clearance. Same L-shaped support ribs,
  sized against the textured surface.
- **Textured Tray / Display Bowl (Mesh)** generator: trays that carry the
  SAME texture library as the textured planters, so a set matches exactly.
  Two styles: Saucer (shallow flared dish with an optional raised seat
  ring inside, so the pot sits proud of collected water) and Tilted Bowl
  (the sculptural slant-rim display bowl a pot nests inside - Rim Tilt
  sets how far the front sweeps down). Same texture/depth/density/twist
  controls as the pots, and the same Cross-Section choice (Round/Square/
  Triangle) - a triangle tray hugs a triangle pot with uniform clearance,
  and the seat ring follows the pot's shape too. Writes a print-ready STL
  to generated/.
- **Textured Planter (Mesh/STL)** generator - the mesh backend. Produces
  designer-style textured planters (like commercial textured-vase models)
  that CAD features can't reach: Knurl, Scales, Pinecone, Pleats, Pills,
  Bark, Bubbles, Drips, Pinstripe, Lobes, Shingles (bold overlapping
  pinecone/dragon scales - use ~4mm depth and lower density for huge
  scales), Arcs (art-deco fans over pinstripe), Hearts, Honeycomb,
  Triangle Ribs, Weave, Y-Tiles, and Soft Cutout (deep smooth indents -
  pair with Interior = Follow Texture). Three shaping controls multiply
  the range: Cross-Section (Round / rounded Square / rounded Triangle),
  Texture Twist (spirals any texture around the pot), and Interior Wall
  (Smooth, or Follow Texture for constant-wall sculptural pots). All over
  Straight/Barrel/Bowl/Hourglass silhouettes, with wall/base thickness and an optional
  center drainage hole. Instead of building Fusion geometry it writes a
  watertight, print-ready STL (hundreds of thousands of triangles, ~1s)
  into the `generated/` folder - open it straight in your slicer.
  Optionally imports the mesh into Fusion for preview (slow).

  Requirement: a system Python with numpy (found automatically; install
  from python.org and `pip install numpy` if missing). Fusion's own Python
  can't run numpy, so the add-in generates the mesh in a subprocess via
  `PrintEngine/mesh_engine/generate.py` - that script also works standalone
  from a terminal with a JSON parameter file.
- One placeholder generator (a plain parametric cylinder) kept as the
  simplest possible reference for how to write a generator.

## Installing the add-in in Fusion 360

1. Open Fusion 360.
2. Go to the **Utilities** tab → **Scripts and Add-Ins** (or press `Shift+S`).
3. Select the **Add-Ins** tab (not Scripts).
4. Click the green **+** button and browse to select the `PrintEngine`
   folder (the one containing `PrintEngine.py` and `PrintEngine.manifest`,
   i.e. `Fusion 360/PrintEngine`).
5. Select "PrintEngine" in the list and click **Run**.
6. Switch to the **Design** workspace → **CREATE** panel. You should see a
   new **Create Print Object** button.

Leave "Run on Startup" unchecked for now while you're developing - starting
it manually each time makes it easier to see errors.

## Running it

1. Click **Create Print Object**.
2. Pick an object type from the **Object Type** dropdown (e.g.
   "Planter: Basic Planter").
3. Adjust the parameters shown, then click **OK**.
4. A new component containing the generated geometry appears in your design.
   The first object lands at the origin; each additional object is placed
   automatically to the right of existing geometry so nothing overlaps.

## Debugging

Fusion does **not** hot-reload add-ins. After changing any `.py` file:

1. Go back to **Scripts and Add-Ins** (`Shift+S`) → **Add-Ins** tab.
2. Select PrintEngine and click **Stop**, then **Run** again.

If something goes wrong, this add-in shows a message box with the Python
traceback rather than failing silently - read that first. You can also open
**Utilities → Add-Ins → Scripts and Add-Ins → ... (Text Commands)**, or the
**TEXT COMMANDS** palette (`Shift+Ctrl+Alt+C` in some versions, or via the
`View` menu), to see general Fusion API log output.

## Project layout

```
PrintEngine/
  PrintEngine.py            entry point Fusion calls: run(context) / stop(context)
  PrintEngine.manifest       add-in manifest (tells Fusion this is a Python add-in)
  engine/
    base.py                 ParamSpec + Generator base class - the plugin contract
    registry.py              tracks every generator that's been registered
    geometry_utils.py         helpers wrapping common Fusion API calls
    generators/               one module per object type - this is where you add new ones
      example_cylinder.py     placeholder generator, to be replaced by the real planter
    ui/
      command.py              the "Create Print Object" command and its dialog
  resources/
    CreatePrintObject/         toolbar icons for the command (currently placeholders)
```

## Adding a new generator

1. Create a new file in `PrintEngine/engine/generators/`, e.g. `planter_basic.py`.
2. Subclass `Generator` (from `engine/base.py`):

   ```python
   from .. import geometry_utils
   from ..base import Generator, ParamSpec
   from ..registry import register

   @register
   class BasicPlanter(Generator):
       id = "planter_basic"
       display_name = "Basic Planter"
       category = "Planter"
       parameters = [
           ParamSpec(name="diameter", label="Diameter", type="float", default=120.0,
                      min=30.0, max=400.0, unit="mm"),
           # ... more parameters
       ]

       def build(self, component, params):
           # use geometry_utils helpers, or call the Fusion API directly, to
           # create geometry inside `component`
           ...
   ```

3. Import the new module in `engine/generators/__init__.py` so it registers:
   `from . import planter_basic`.
4. Stop/Run the add-in in Fusion and it appears in the Object Type dropdown
   automatically - no changes needed in `engine/ui/command.py`.

### Keychains

- **Motel Tag Keychain**: the classic elongated-hex fob, fully parametric
  (size, thickness, ring hole with raised collar, end-stripe grooves) with
  custom **Text** in any font installed on Windows (bold toggle, Raised or
  Engraved at adjustable depth) and a **Symbol** - pick a preset (heart,
  star, moon, sun, music, peace, yin-yang, anchor, snowflake) or choose
  Custom and paste any character into Symbol Text (press Win+. for the
  Windows symbol picker; zodiac glyphs are U+2648-2653, e.g. Aquarius).
  Symbols render via the Segoe UI Symbol font - symbols are just text.

### Aquarium Decor

- **Treasure Chest**: a hollow open-top chest with raised strap bands, an
  optional swim-through hole for fish (doubles as an airline pass), and a
  separate half-barrel lid piece - glue it closed or propped ajar in the
  tank. Print in PLA or PETG; both are aquarium-safe once rinsed.
- **Castle Tower**: a tapered hollow tower with crenellated battlements, an
  arched doorway, and a ring of arched windows - all swim-throughs. Open at
  the bottom (sits over gravel, no trapped air) and at the top. Notch count,
  door/window sizes and window height are all adjustable.
- **Rock, Brain Coral, Finger Coral** (mesh backend): organic pieces
  written as print-ready STLs to `generated/`, like the Textured Planter.
  Rocks are noise-displaced boulders with a flattened underside; brain
  coral is a ridged dome; finger coral grows wavy tapered fingers from a
  rocky mound. Every one has a **Variation Seed** - same settings,
  different seed, different individual - so you can print natural-looking
  clusters.
- **Hollow Log** (SDF backend): a bark-ridged trunk lying on its side -
  hollow bore with open ends, an optional oval swim-through opening in the
  wall, flattened belly so it sits still. Two bark layers (long furrows +
  fine ridges) stretched along the grain; crank Bark Depth for gnarlier.
- **Tire Pile** (SDF backend): 1-4 old tires - one flat, others leaning or
  stacked, fused where they touch. Square-block tread with a center
  circumferential groove; the Variation Seed shuffles the pile.
- **Anchor** (SDF backend): a classic admiralty anchor - ring, shank,
  stock crossbar, curved arms with flukes - melted into one cast-metal
  piece with a flat back, so it prints lying down with no supports.
- **Sunken Ship** (SDF backend): an open-top hull heeled over and buried
  to the sand line, with a pointed bow, broken masts (the seed varies the
  breaks), a deck cabin, planking ridges, and a hull breach fish can use.
- **Staghorn Coral** and **Rock Cave / Arch** (SDF backend): built on the
  signed-distance-field engine (`mesh_engine/sdf.py`), which models parts
  as math functions and melts them together with smooth blending before
  extracting one seamless watertight mesh (marching cubes). Staghorn is a
  recursive branching colony with a trumpet base; the cave is a boulder
  arch with a swim-through tunnel. Finger coral was upgraded to SDF too -
  its fingers now grow smoothly out of the mound. Needs scikit-image on
  the system Python (`pip install scikit-image` - installed automatically
  during development). The SDF engine is the foundation for the creature
  category: bodies with smoothly attached limbs are exactly this technique.

### Creatures

- **Axolotl** (SDF backend): the first creature - a chunky figurine with a
  blunt head, ball-tipped gill frills, four stubby legs, eye bumps, and a
  finned tail. Belly and feet are floor-cut flat so it prints lying down
  with no supports. Adjustable length, chubbiness, leg/gill/tail sizes, and
  a Variation Seed for slight pose differences. Writes a print-ready STL
  to `generated/` like all mesh-backend objects.

### Scoops

- **Turned-Handle Scoop**: the classic flour/coffee scoop - a hollow
  cylindrical bowl with an angled scoop mouth, on a lathe-turned handle.
  Built as ONE closed revolve profile (bowl + neck + handle all in a single
  silhouette, same trick as the planters), then the mouth is sliced with a
  tilted construction plane (`geometry_utils.angled_plane_through_x` +
  `cut_half_space`) - a knife-cut through a solid of revolution, reusable
  for any future angled-cut generator. Bowl diameter/depth, mouth angle,
  wall thickness, base thickness (keeps the interior floor from digging
  into the handle - see gotcha below), and a rounded-or-flat bowl bottom
  are all adjustable, plus four **Handle Style** choices (Classic Baluster,
  Multi-Bead Spindle, Simple Taper, Stubby Knob) built from reusable turned
  -profile elements (hemisphere tip, cone tip, taper, bead, cove, plain
  cylinder) that any future turned-handle utensil can reuse.

  **Printability**: this whole shape is a single solid of revolution
  printed standing on the handle tip, so any region where the OUTER radius
  increases going up is a horizontal-ish overhang (self-supporting only
  within ~45deg from vertical). A review found the *default* parameters
  already put two things past that: the straight-cone **neck** (handle
  radius flaring out to the full bowl radius) and several handle styles'
  decorative beads. Fixes, all structural rather than one-off tuning:
  - `_taper`, `_cone_tip`, and `_bead` (the shared profile-building blocks
    every handle style is made from) each auto-extend their own length so
    their steepest rising point never exceeds 45deg, no matter what radii
    a style or future style passes in - narrowing segments are left alone
    since those are always self-supporting.
  - The **neck** gets the same treatment via a new **Neck Taper Angle**
    parameter (default 45deg): `neck_length` is now a *minimum* - the
    actual neck auto-extends to whatever height keeps the bowl/handle
    radius gap under that angle, verified live to turn an 85.8deg
    near-flat shelf (bowl_diameter=120, handle_diameter=10,
    neck_length=4 - all in-range) into a clean 45deg cone.
  - `_hemisphere_tip`'s pole is a fixed ~57.5deg from vertical independent
    of scale (a real hemisphere's tangent at its pole is horizontal) -
    left as-is rather than distorting the shape, since in practice
    slicers print small rounded tips like this fine without support (the
    overhang area near a point is tiny) and it can't be fixed by simply
    lengthening it without turning it into an ellipsoid.
  - Since handle styles can now legitimately run longer than the
    requested Handle Length, `build()` reads back each style's actual
    final height (previously discarded) to place the neck correctly, and
    raises a clear error if a style's auto-extension would need
    substantially more room than Handle Length allows (e.g. a very thick
    handle with the Multi-Bead Spindle style at the minimum length),
    rather than silently ballooning the handle or crashing.
  - Also fixed along the way: the Classic Baluster and Stubby Knob styles
    sized their tip from `handle_diameter` alone (independent of
    `handle_length`), which could make a final taper segment's length go
    negative - a real self-intersecting-profile bug, not just a
    printability concern - for a thick-enough handle at a short-enough
    length (e.g. handle_diameter=45mm, handle_length=40mm, both in-range).
    Both tips are now capped to a fraction of Handle Length too.
- **Loop-Handle Scoop (Square)**: a hollow rounded-square cup - built with
  the same `build_polygon_shell` helper as the polygon planters - with the
  same angled mouth cut as the Turned-Handle Scoop (the knife-cut plane
  trick works on any cross-section, not just round). The handle mounts on
  the FRONT wall - the SHORT/low side of the angled mouth - so the tall
  back wall extends away from your hand as a deep backstop, maximizing how
  much a single scoop can hold. Two **Handle Style** choices:
  - **Square Bracket** (default): a "flag" bracket - a horizontal bottom
    leg (finger rest) plus a DIAGONAL top brace, joined by a short
    crossbar. A flat horizontal top leg is a textbook unsupported
    overhang (a shelf cantilevered off a vertical wall); the diagonal
    brace - the same trick a real wall-shelf bracket uses - keeps the top
    surface within the self-supporting overhang angle instead. **Handle
    Top Angle** (default 45°, measured from vertical - smaller is
    steeper/safer, matches the standard FDM 45° self-supporting rule)
    controls how steep the brace is; a guard rejects angle/reach/attach-
    span combinations that would force the brace into the bottom leg. The
    brace's near (wall) end is cut FLUSH VERTICAL to match the wall
    surface, rather than perpendicular to its own slope - a perpendicular
    cut leaves one corner poking out past the wall's outer face as a small
    floating tab barely fused to the body. The perpendicular offset at the
    brace's far end is sign-normalized (always "+offset" = toward +z) so
    it agrees with the near end's fixed top/bottom corners - without this
    the quad's corners can wind into a self-intersecting bowtie instead of
    a simple bracket shape.
  - **Arched Loop**: a curved mug-style handle whose path is a short
    STRAIGHT STUB at each wall attachment (running perpendicular to the
    wall), then a single fitted spline out to a bulge and back to the other
    stub - `sketchLines` + `sketchFittedSplines.add`, all 3 curves passed
    EXPLICITLY to `component.features.createPath` (an `ObjectCollection`
    with `isChain=False`), plus `geometricConstraints.addTangent` between
    each stub and the spline, then `sweepFeatures`. A round tube only meets
    a flat wall as a clean round hole if it arrives PERPENDICULAR to it - a
    tube meeting the wall at an angle intersects it in a tilted ellipse, and
    no amount of sliding the centerline back and forth can make that flush:
    one side of the ellipse pokes into the interior while the other gaps
    away from the wall outside, with the tilted end cap itself showing as a
    visible seam (all confirmed live with an earlier centerline-pullback
    attempt, before landing on the stub). The straight stub's own
    cross-section is confined to a constant-depth plane for its whole
    length, so its wall-facing end can sit exactly at the near-EDGE depth
    (the same quantity the Square Bracket's bars start from) with no
    ambiguity about how far the tube's radius actually reaches. Two gotchas
    hit building this: `createPath(curve, isChain=True)` on a single curve
    only followed the connected chain ONE curve deep and silently dropped
    the second stub (confirmed via `path.count`), leaving the swept tube
    short of the wall - fixed by passing all 3 curves explicitly instead of
    relying on chain auto-detection; and a fitted spline's own tangent at a
    shared endpoint isn't automatically forced to match an adjoining line's
    direction, producing a visible sharp crease at the stub/spline
    junction - fixed with an explicit tangent constraint at each joint. A
    validation guard rejects reach-vs-attach-span proportions that would
    force too tight a turn at the tip for the swept tube to avoid
    self-intersecting (`ASM_SELF_INTER`).

  Both styles share the same wall-attachment fix: the handle's near edge
  is pinned just inside the OUTER wall surface (by a small margin under
  the wall thickness), with the handle's full thickness extending outward
  from there - so a handle thicker than the wall (the usual case) can
  never poke through the inner surface into the hollow interior, which an
  earlier version of this generator got wrong (the handle was centered on
  the wall rather than edge-anchored, so its inner half punched through
  into the scoop's cavity as a visible interior bump).

  Both styles also anchor their bottom attachment from the object's TRUE
  base (z=0, the surface that sits on the print bed) rather than the
  interior cavity floor: `handle_bottom_z = handle_radius + Handle Bottom
  Attach`, so with the default 0mm offset the bottom leg/tube's lowest
  edge sits exactly flush with the bed - no floating gap underneath that
  would need support. An earlier version measured this offset from the
  cavity floor instead, which left the bottom leg elevated (~14mm by
  default) with unsupported air beneath it.

  **Gotcha hit while building this**: the interior cavity's rounded bottom
  dome must never be allowed to dig deeper than the solid material reserved
  below it (`base_thickness`) - skipping that reservation produced a
  self-overlapping profile that silently split into multiple disconnected
  Fusion profiles instead of one clean loop. Any future generator that
  hollows out a shape sitting on top of other solid geometry needs the same
  reserved-floor pattern the planters and this scoop both use.

## Roadmap / open questions

- **Scoops** - both pieces done and both have been through a printability
  pass (the Loop-Handle Scoop's handle attachment across several rounds -
  wall placement, interior poke-through, supportless top/bottom, a clean
  perpendicular wall joint; the Turned-Handle Scoop's neck taper and bead
  overhangs, see memory for both). The second scoop was originally rebuilt
  from a screen recording after the first STL-based read of it turned out
  wrong. Possible later: a flared/fluted bowl option, a matching
  stand/holder, engraved capacity markings (mL/oz) using the same
  SketchText approach as the keychain, a loop-handle option for the round
  bowl too.
- **Planters** - feature-complete for now: shapes (round/hex/square),
  drainage holes, matching trays with L-ribs, straight/spiral/crisscross
  flutes, surface textures (ribbed/bubbles/bark), rounded rims, and a
  self-watering insert. Possible later: flutes/textures on polygon pots,
  hex/square self-watering inserts, overflow side hole, scale texture and
  embossed artwork (hearts, animals) - the latter two want the mesh-based
  pipeline planned for creatures, since B-rep feature counts explode.
- **Aquarium decor** - treasure chest, castle tower (B-rep), rock, brain
  coral, and finger coral (mesh backend) done. Next candidates: tires,
  sunken-ship pieces, branching coral, multi-tower castle assemblies.
- **Creatures** - axolotl done on the SDF backend, proving the pattern:
  a creature is a spine of blended segments + limbs + fins + face details.
  Next candidates: fish, turtle, gecko, snail... and the dragon (same
  pattern with horns, wing membranes as flattened ellipsoids, and spikes -
  the most ambitious composition but no new technology).
