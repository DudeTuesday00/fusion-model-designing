# Print Engine Development Roadmap

Last updated: 2026-07-29

---

## Part 1: Improvement Phases 1–3

### Phase 1 – Quick Wins — **DONE**
| # | Task | Status |
|---|------|--------|
| 1.1 | Gate Example Cylinder | Done |
| 1.2 | `.gitignore` | Done |
| 1.3 | Clean validation errors | Done |
| 1.4 | Parameter groups | Done |

### Phase 2 – Matching & UX — **DONE**
| # | Task | Status |
|---|------|--------|
| 2.1 | Combined Planter + Matching Tray | Done |
| 2.2 | Command preview (B-rep) | Done |
| 2.3 | Last-values + last generator | Done |
| 2.4 | Match Selected Body | Deferred |

### Phase 3 – Robustness & Polish — **DONE**
| # | Task | Status |
|---|------|--------|
| 3.1 | Units module + geometry_utils compatibility | Done (`engine/units.py`) |
| 3.2 | Printability helpers | Done (`engine/printability.py`) |
| 3.3 | Export helper command | Done — **Export Print Bodies** (STL/3MF) |
| 3.4 | Named multi-body output | Done — bodies named after generator |
| 3.5 | Roadmap / docs kept current | Done |

---

## Part 2: New Product Families (next focus)

### Family A: Storage Ecosystem (Highest Priority)
1. Basic Box + Matching Lid
2. Stackable Box variant
3. Box Insert / Divider

### Family B: Expanded Planter / Garden
- Stackable tiers, tower modules, Terracotta tray consistency

### Family C: Desk & Office
- Pen cup, cable box, stands, docks

### Family D: Higher-margin products
- Keepsake boxes, wall organizers, gear cases

---

## Recommended next step

**Family A — Basic Box + Matching Lid** generator (reuse wall/base/lid clearance patterns from planters and drip trays).
