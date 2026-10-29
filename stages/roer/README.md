# Roer (3D stage)

Roer, the city of industry and capital of Nortia, at dusk. You fight on the Upper Level plaza at the head of the two
giant escalators that run down to the Lower Level. The avenue below runs between tall buildings to the
Khemia Corp tower, and the sun sets just to the right of it.

## What's in it
- **Plaza (fight area):** granite slabs with steel expansion strips, an inlaid orbal-gear medallion behind the
  fighters, and a dark granite band at the railing over the 7 m drop.
- **Gateway:** a plain steel arch over the escalator heads, with cyan light strips and red gear banners either side.
- **Plaza edges:** orbal street lamps, trees in planters and benches. The buildings have shops (a dining bar on
  the left, an arms store with a red sign on the right) and Hotel Lagrange stands on the corner.
- **Escalators:** two of them, with moving steps, balustrades and cyan skirt lights running with the steps. The left
  one goes down, the right one goes up.
- **Lower Level promenade:** pedestrians only, paved with the same granite slabs as the plaza. Trees in planters down
  the middle with stone benches, kiosks, street lamps, and shops with awnings.
- **Railway viaduct:** a steel truss across the avenue. A train crosses behind the truss every 38 s, alternating
  direction.
- **The rest of Roer:** the Khemia Corp tower (lit windows, a lit glass lobby and a red KC emblem), the cathedral with twin spires and a
  rose window, the Institute of Technology's copper dome, and blocks of buildings on both plateaus.
- **Factory district:** sawtooth halls, banded chimneys with red beacons and smoke, gantry cranes, and three orbal
  turbines with turning rotors and green chase rings.
- **Sky:** smog layers, two airships drifting, mountains, and a dusk sky with cloud streaks lit from below and the
  first stars.
- **Particles:** soot flecks on the wind and dust motes in the low sun.

## Files
- `roer.tscn` and `roer.glb` (baked, unlit), plus `textures/floor_light.png` and `textures/dot.png`.
- **Shaders:**
  - `rr_floor`: the granite paving times the light map.
  - `rr_sky`, `rr_window`, `rr_glow` (ids 0 lamps, 1 sign strips, 2 sign letters (unused), 3 turbine rings, 4 escalator
    skirts, 5 red signs/KC, 6 beacons, 7 rose window).
  - `rr_steps`, `rr_smoke`, `rr_rotor`, `rr_train`, `rr_ship`, `rr_flag`, `rr_haze`.
- **`src/`:** `build_roer.py` (geometry, materials, lights), `bake_roer.py` (Cycles bake, grade, preview, export)
  and `run_rr.py` (the background pipeline).
- **Baking:** run `stages/bake_roer_chapel.bat`, or:
  `blender --background --factory-startup --python src/run_rr.py -- STEPS=build,bake,preview,export CAMS=CAM_mid`

## Tuning
- **Overall look:** EXPOSURE 0.2, SATURATION 1.1, with cool shadows and warm highlights. It lives in
  `bake_roer.py` LOOKS and in the floor material's look group in the .tscn. Keep the two in sync and re-run
  `STEPS=regrade,preview,export`.
- **Train:** speed, period and number of cars are uniforms on the Train material.
- **Windows:** `lit_fraction` sets how many are lit.
- **Haze:** the haze colour and range are uniforms on the window and glow shaders.
- **Camera:** NetsuCameraTop is 20.
