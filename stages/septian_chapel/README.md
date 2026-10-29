# Septian Chapel (3D stage)

A small chapel of the Septian Church out in the countryside, on a golden summer afternoon. You fight on the cobbled
churchyard square in front of it.

## What's in it
- **Chapel:** a limestone facade with buttresses and a string course. It has a stained-glass rose window, a pointed
  moulded portal with iron-strapped doors and the Church's emblem in gold, two lancets, and more lancets along the
  nave.
- **Bell tower:** a clock, an open belfry with a bronze bell, a slate spire with pinnacles and a gold emblem finial.
  Swallows wheel around it.
- **Emblem:** an original stylised design (a ring crossed by an upright, with seven rays above).
- **Square:** a statue of the Goddess Aidios in a ring of flowers on the left, and a parish notice board on the
  right.
- **Left side:**
  - The sister's half-timbered rectory, with flower boxes, a porch and a smoking chimney.
  - A front garden with a picket fence, vegetable rows, a well with a little roof, and washing stirring on the line.
  - A big oak with a bench beneath it.
- **Right side:** the churchyard behind a low fieldstone wall, with a lychgate, rows of headstones, crosses and
  obelisks, and yews. A hand cart and hay bales stand in front.
- **Ground:** a meadow with gusts rolling across, wildflowers, cobbles with mossy joints, a flagstone path to the
  steps, dirt paths to the gates, and swaying grass tufts with flowers.
- **Background:** patchwork fields with hedgerows, poplars, farmhouses and barns, woods, a windmill turning on a
  hill, blue mountains with snow, and a sky with drifting cumulus.
- **Particles:** drifting petals and pollen.

## Files
- `septian_chapel.tscn` and `septian_chapel.glb` (baked, unlit), plus `textures/floor_light.png` and
  `textures/dot.png`.
- **Shaders:**
  - `ch_floor`: meadow, cobbles and paths times the light map.
  - `ch_sky`, `ch_glass` (0 rose, 1 facade/tower lancets, 2 nave lancets).
  - `ch_grass` (kind 0 grass, 1 flowers, 2 tall grass), `ch_smoke`, `ch_sails`, `ch_birds`, `ch_cloth`.
- **`src/`:** `build_septian_chapel.py`, `bake_septian_chapel.py`, `run_ch.py`.
- **Baking:** run `stages/bake_roer_chapel.bat`, or:
  `blender --background --factory-startup --python src/run_ch.py -- STEPS=build,bake,preview,export CAMS=CAM_mid`

## Tuning
- **Overall look:** EXPOSURE 0.0, SATURATION 1.05. It lives in `bake_septian_chapel.py` LOOKS and in the floor
  material's look group in the .tscn. Keep the two in sync.
- **Floor layout:** the square, statue and oak positions are uniforms on the floor material. If you move them in the
  build script, move them in the shader too.
- **Grass:** sway, colours and wind direction are uniforms on the Grass material.
- **Camera:** NetsuCameraTop is 20.
