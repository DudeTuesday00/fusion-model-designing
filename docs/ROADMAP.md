# Print Engine Development Roadmap

This document captures the planned improvement phases and new product families for the Print Engine Fusion add-in.

Last updated: 2026-07-29

---

## Part 1: Improvement Phases 1–3

### Phase 1 – Quick Wins — **DONE**
**Goal:** Clean the codebase and improve daily usability with low risk.

| # | Task | Status |
|---|------|--------|
| 1.1 | Remove / gate Example Cylinder | Done — not registered in normal builds |
| 1.2 | Add proper `.gitignore` | Done |
| 1.3 | Improve validation error presentation | Done — clean `ValueError` message boxes |
| 1.4 | Group parameters in dialog | Done — `ParamSpec.group` + nested groups |

---

### Phase 2 – Matching & UX — **DONE**
**Goal:** Reduce friction between related parts and make the tool feel more professional.

| # | Task | Status |
|---|------|--------|
| 2.1 | Combined “Planter + Matching Drip Tray” generator | Done — `planter_with_tray.py` |
| 2.2 | Command Preview support | Done — `executePreview` for B-rep generators |
| 2.3 | Last-values persistence | Done — `engine/prefs.py` + `last_params.json` |
| 2.4 | Optional: “Match Selected Body” mode | Deferred (nice-to-have) |

---

### Phase 3 – Robustness & Polish (next)
**Goal:** Make the engine more maintainable and production-ready for product lines.

| # | Task | Details | Acceptance Criteria |
|---|------|---------|---------------------|
| 3.1 | Split `geometry_utils.py` | Break into focused modules: `sketch_utils.py`, `feature_utils.py`, `body_utils.py`, `placement_utils.py` (keep a thin `__init__` or re-export for compatibility). | Existing generators still import cleanly; file sizes are manageable. |
| 3.2 | Stronger printability guards | Centralize checks (min wall, hole fitting, feature size, overhang risk on feet). Raise clear `ValueError`s with suggested fixes. Optionally add a “Printability Report” message after build. | Dangerous parameter combinations are blocked early with helpful messages. |
| 3.3 | Export helper | Add a command or post-build option: “Export Generated Bodies as STL/3MF”. Handle multi-body (separate files or single multi-body). Name files from component/generator. | One-click clean export of the new objects. |
| 3.4 | Better multi-body & naming | Ensure separate parts (feet, inserts, lids) are clearly named and spaced. Support selective visibility / export. | Generated assemblies are easy to manage and print. |
| 3.5 | Documentation polish | Expand README with architecture overview, how to add a generator, and printability guidelines. | New contributors (or future you) can extend the engine quickly. |

**Phase 3 Exit Criteria:** Cleaner internal structure, safer defaults, easy export, ready for product-family expansion.

---

## Part 2: New Product Families

These families reuse the existing patterns (matching parts, parametric thickness, textures, feet/ribs, inserts) and map cleanly onto new `Generator` subclasses.

### Family A: Storage Ecosystem (Highest Priority for Saleability)
**Core idea:** Parametric boxes with matching lids, optional inserts, and stacking interfaces.

**Generators to create (in order):**

1. **Basic Box + Matching Lid**
   - Parameters: shape (rect, square, round, hex), length/width/height (or diameter), wall & base thickness, lid style (friction, lip, snap-feel), corner radius, optional texture on lid/sides.
   - Build: box body + separate lid body (or two components). Lid sized with configurable clearance/interference.
   - Reuse: wall/base logic, texture helpers, placement spacing.

2. **Stackable Box variant**
   - Adds interlocking lip / recessed bottom so boxes stack securely.
   - Optional “stack height” and registration features.

3. **Box Insert / Divider**
   - Grid, honeycomb, or custom compartment insert that drops into the box (like the self-watering insert pattern).
   - Parameters driven by parent box dimensions.

4. **Later extensions**
   - Wall-mount plate + bin
   - Labeled / embossed lid options
   - Nested size sets

**Implementation notes:**
- Start with rectangular + square (most useful for storage).
- Lid matching logic mirrors the current drip-tray approach (clearance, flare/lip, centering).
- Prefer separate bodies for box and lid so they can be printed and sold as sets.

**Success metric:** A user can generate a complete box + lid + optional insert set in under a minute with consistent fit.

---

### Family B: Expanded Planter / Garden Ecosystem
Build on what already exists.

**New / enhanced generators:**
- Stackable planter tiers (interlocking rims + drainage that doesn’t flood the lower pot)
- Combined “Planter + Tray + Insert” (from Phase 2)
- Improved Terracotta + matching tray consistency
- Vertical garden tower modules
- Modular hardscape (extend existing aquarium décor generators)

**Priority order:** Combined generator first → stackable tiers → tower modules.

---

### Family C: Desk & Office Ecosystem
**Generators:**
- Pen / pencil cup (tapered vessel + optional matching base/tray)
- Cable management box + lid
- Simple phone / tablet stand (parametric angle + width)
- Monitor / laptop riser with cable routing cutouts
- Multi-item “dock” family (shared style language)

These are lower geometric complexity than storage boxes and can reuse vessel + lid patterns heavily.

---

### Family D: Unique / Higher-Margin Products (Later)
- Parametric keepsake / gift boxes with embossed lids
- Modular wall organizers
- Custom camera / gear cases with foam-style inserts
- Habit / pill organizers with daily lids

These benefit from the texture/mesh backend and the insert pattern.

---

## Recommended Execution Sequence

1. ~~**Finish Phase 1**~~ Done.
2. ~~**Phase 2**~~ Done (combined generator, preview, last-values).
3. **Phase 3** and/or **Family A** (Basic Box + Matching Lid) next.
4. Expand into stackable boxes and desk items once the core box + lid pattern is solid.

---

## Notes for Implementation

- All new generators should follow the existing pattern: subclass `Generator`, define `ParamSpec`s, implement `build()`, and register via `@register` + import in `generators/__init__.py`.
- Prefer composition and shared helpers over copy-paste when matching parts (lids, trays, inserts).
- Keep printability (wall thickness, supportless design, clearances) as a first-class concern.
- Update this roadmap as phases are completed or priorities shift.
