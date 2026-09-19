# Coding Fly 2.0 — implementation state

This update improves the existing causal heading benchmark. It does **not** yet
meet the full multi-element webpage acceptance test in the new brief.

## Implemented

- Warm, compact home/workroom: neighboring bed, bedding, bedside lamp/table, window,
  wood floor, shelf, books and plant. Charcoal chair, warm desk and dark editor.
- Physical keyboard includes Tab, Escape, backslash/backquote, command/control,
  arrows, Home/End/Delete and the existing letters, modifiers and punctuation.
- Continuous key-to-key travel; no return to a neutral position per character.
  An unmodified-key stroke takes 42 × 2 ms = 84 ms, or 11.9 presses per modeled
  second. Modifier combinations take additional physical actions. Native events
  still wait for exact contact and, in live mode, rendered-pose acknowledgement.
- Pixel-exact retinal memory. Unchanged windows retain their previously measured
  glyph/readout; changed windows receive fresh 16-tick neural processing. Readout
  files store all 80 slots, with per-slot sample ticks and refreshed-slot indices
  in the decision. Memory is an engineered sensor capability, not neural plasticity.
- Separate GPU layers for subdued cool-gray anatomy and modeled activity. Current
  rate is the default: muted blue at low rates, cyan when active, blue-white at
  40 Hz display saturation. Cells at or below 1 Hz have no rate overlay. Real
  threshold events flash white with a 12 ms simulation-time trail. Amber marks
  selected neurons and their connectivity; it does not encode activity.
- Measured resting baseline at 128 ticks. Optional “Change from rest” shows
  |current − resting rate|, saturated at 8 Hz. Both views retain actual recorded
  spike events. Neither creates activity or changes neural state.
- Full-screen CNS, real-metadata population filters, configurable 8–100 ms spike
  trails, anatomy-only comparison and a live desk inset. Thumbnail anatomy samples
  one in eight located cells, but its activity layer includes every located cell;
  the expanded inspector draws all located anatomy. Missing coordinates stay unplaced.
- Fly Vision shows the actual monitor screenshot used by the controller. It is
  an engineered fixed monitor crop, not a head-dependent compound-eye sensor.
- Dark workspace uses a compositor inversion of the original glyph surfaces;
  retinal normalization reverses that transform. This preserves the trained
  glyph shapes. Merely switching to white font rasterization caused a measured
  glyph error and was rejected. Native browser error messages are surfaced by
  the preview environment; source remains editable only through native input.

## Measured results

`experiments/coding_v2/dark_workspace.json` contains fresh subgraph runs: wrong-key
repair for Hello World and held-out Hello Fly both reached zero final pixel error.
`experiments/coding_v2/full_fast.json` records a full-network wrong-key trial:
29 trusted key-downs, one Backspace, 6.686 simulated seconds and 15.688 wall seconds,
zero final pixel error. This was headless; it is not a live-render speed measurement.
The previous 75.276-second simulation repeatedly rescanned all retinal windows.
The newer sensor memory changes the modeled observation schedule, so the reduction
must not be called a pure hardware speedup. Every neural state still integrates
every 2 ms tick that actually occurs.

## Not yet implemented / not claimed

- A trained multi-element HTML/CSS/JavaScript controller or unseen-layout success.
  The active weights remain the narrow heading checkpoint. Existing prototype
  token templates are not promoted as learned webpage synthesis.
- A multi-file IDE and a general debugging curriculum.
- Head-dependent visual perception, validated biomechanics or biological dynamics.
- Autonomous walking/resting: the new bed establishes the room, but is not yet
  connected to an off-task controller. No decorative motion is labeled neural.
- General programming knowledge, consciousness or biological causal claims.

The next controller needs its own dataset, training run, checkpoint, held-out
layouts, physical-input evaluation and correction trials before enabling a
“Build webpage” task. Appearance does not establish that capability.

The visible full-CNS trial `c6cf827ec5a0483cba1237a55f0bef33` also passed after
these changes: **29 native key-downs, all 29 preceded by acknowledged rendered
contacts**, one Backspace, and zero final pixel error. It took 33.910 wall seconds
for 6.686 simulated seconds. Its 6,345,571 archived threshold events exactly match
the streamed packets, including the final flush. See
`experiments/coding_v2/live_verified.json`. During that run, the full-screen CNS
view was opened while the desk remained live in its inset.
