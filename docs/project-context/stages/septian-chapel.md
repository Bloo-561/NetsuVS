# Septian Chapel (3D)

**Status (2026-10-26):**
- Built, baked (about 21 min) and checked in Godot from all the fight cameras and the y 20 high camera.
- Thumbnail made.
- Being added to Stage Select as "Septian Chapel" (thumbnail ext id 36, NetsuCameraTop 20).
- Not yet checked in a real match.

## Where things are
- **`stages/septian_chapel/`:**
  - The scene and model: `septian_chapel.tscn` and `.glb`.
  - Shaders: `ch_floor`, `ch_sky`, `ch_glass`, `ch_grass`, `ch_smoke`, `ch_sails`, `ch_birds`, `ch_cloth`.
  - Textures: `textures/floor_light.png` and `dot.png`.
  - The thumbnail and the README.
- **`src/`:**
  - `build_septian_chapel.py`: this stage's own header and body, plus the shared helpers from Ordis and the shared `_shapes.py`.
  - `bake_septian_chapel.py`: derived from Roer's outdoor bake (no mirror copy, nothing cut below the floor).
  - `run_ch.py`.
  - Single variant `afternoon`, so there is no file suffix.
- **Baking:** `stages/bake_roer_chapel.bat` bakes Roer and this stage one after the other.

## Layout (Godot coordinates)
- **Ground:**
  - The floor quad runs x ±60, z -80..22. The Godot shader draws the meadow, the cobbled square, the flagstone path to the steps and the dirt paths.
  - Cobbled square: an ellipse centred on (0, -6) with radii 13.5 × 10.5.
- **Chapel:**
  - Facade at z -28, x ±5. Walls 7 m high, ridge 12.5 m, nave 20 m long.
  - Rose window centred at y 7.9 (r 1.45). Pointed portal 2.4 m wide. Gold emblem in the tympanum and on the apex.
  - Bell tower at (7.1, -30.1), 3.8 m wide. Clock at y 8.2, open belfry 11–14.6 with a bell, spire to about 26 m.
- **Emblem:** an original design (a ring crossed by an upright, seven rays above), because the falcom.wiki page couldn't be fetched.
- **Square:**
  - Statue of Aidios at (-6.6, -17) in a ring of flowers.
  - Notice board at (6.4, -17.4).
- **Left side:**
  - Rectory: x -22.5..-13.5, z -24..-17, half-timbered. Smoke from the chimney.
  - Front garden behind a picket fence at z -13.6.
  - Well at (-11.2, -15.6). Laundry line at z -11.6.
  - Oak at (-15.5, -6.5) with a bench.
- **Right side:**
  - Churchyard: walls x 12.6..32, z -14..-38. Lychgate at x 15–17.
  - Six rows of headstones and three yews.
  - Hand cart at (10.8, -11.6). Hay bales at x 15–20, z 3–8.
- **Fences:** post-and-rail along x ±13.9.
- **Background:**
  - Heightfield terrain beyond z -78: patchwork Voronoi fields with hedgerows, meadow near the chapel.
  - 8 farms, a windmill at (-66, -150) with a turning sails card, a row of poplars, woods.
  - Mountains with snow at z ≈ -700. Sky cylinder r 1000.

## Look
- **Sun:** an afternoon sun from behind the camera on the right, SUN_DIR travel (-0.45, -0.62, -0.64), 4.4, #ffe4bc.
- **Fills:** world #9ab4d8 1.0, Fill_Front 1400 W, Fill_Top 900 W. The emissive sky card also lights the scene.
- **Grade:** EXPOSURE 0.0, SATURATION 1.05, cool shadows and slightly warm highlights. Keep `bake_septian_chapel.py` LOOKS in sync with the floor material's look group.
- **First bake came out right**, with no regrade needed. Mean values: Chapel 0.18, Village 0.12, Land 0.49; floor light 1.03.
- **Moving parts (Godot only):**
  - Grass tufts sway in rolling gusts. Each tuft's seed is floor(UV.x).
  - Birds circle the tower, the windmill turns, the laundry moves and the smoke drifts.
  - The meadow floor has wind bands; petals and pollen drift as particles.
