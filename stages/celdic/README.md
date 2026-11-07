# Celdic (3D): Day and Burning

The market town of Celdic. The fight takes place on a broad, level cobbled platform. At its far edge a wide stone stairway runs down, away from the camera, into the market courtyard below. The courtyard lies in ruins. The old stone arch stands down there at market level, with the wrecked market buildings and the timber tower behind it.

Both variants share the layout and differ in light, damage and crowd. In Stage Select this is one stage, **CELDIC**. Press **up / down** to switch between **Day** and **Burning** (evening).

| File | What it is |
|---|---|
| `celdic.tscn` / `celdic_burning.tscn` | The two stage scenes, used by `data/stage_list.tres` |
| `celdic.glb` / `celdic_burning.glb` | The town with that variant's light baked in. It holds `Buildings`, `Props` and `Far` (baked atlases), plus the shader cards `Sky`, `Window`, `Bunting`, `Crowd`, `Grass`, `Sails`, `Fire`, `Smoke` and `Haze` |
| `ce_*.gdshader` | The floor, sky, pennant, window, crowd, grass, sail, fire, smoke and haze shaders |
| `ce_fighter_light.gd` | Tints the fighters to the stage light and recolours their ground shadow |
| `textures/` | The baked floor light maps (`floor_light.png`, `floor_light_burning.png`) and `dot.png` (particles) |
| `celdic_thumb.png` / `celdic_burning_thumb.png` | Stage Select thumbnails |
| `src/` | **Source**, ignored by Godot: `build_celdic.py`, `bake_celdic.py`, `run_ce.py`, the `.blend` files and the baked atlases. `src/cache/` is git-ignored |

## Layout (Godot coordinates, metres)
From the fight camera, front to back:

1. **The fighting platform.**
   - Level cobbles, x ±50, z −12..22. The floor light map covers exactly this.
   - The fight lane, |x| < 12.5 and z > −9, is kept completely clear.
   - Left: the general store (front x −11.8) with its porch. Right: the half-collapsed repair house with its scaffolding. Both stand on the platform-level ledges either side of the stairs.
2. **The stairway.**
   - Eight broad steps, 13 m wide, start at the platform's back edge (z −12). They descend away from the camera and reach the courtyard level, y −2.0, at z −45.8.
   - Drops 0.11 → 0.30 m, with a last riser of 0.55 m. Runs 3.4 → 5.2 m.
   - The treads are long and the risers low on purpose. From the fight cameras (eye 1.4–3.4 m above the platform), a steeper stair would hide behind the platform edge. This one shows its top treads clearly, and its lamps step down out of sight.
   - Each tread has a field of dark setts and a worn band of dressed stone along its front edge. A curb marks the head of the stairs.
   - Retaining walls with parapets run along both sides at platform level, so the walls grow taller as the steps descend. Piers and pilasters stand along them, and four lamps a side stand on the steps.
3. **The courtyard**, 2 m below the platform.
   - |x| < 26, from the foot of the stairs (z −45.8) back to z −104. Retaining walls close it at the stair foot and at |x| 26.3, with the platform-level ledges above.
   - **The arch** stands at market level at z −55, on a round curbed paving (radius 4.8). It is 1.15× the old arch. In Burning its right half has fallen.
   - **The central aisle** runs straight back past the arch. Benches, planters and lamps flank the way in.
   - **Stalls** line the aisle on both sides: left row x −4.8 (z −63..−81), right row x 4.8 (z −65..−77). They are torn, broken, or stripped to their frames.
   - **Damaged buildings** stand behind the stalls on both sides. Houses have their roofs fallen in to bare rafters and their windows broken or boarded. Timber buildings are wrecked to their frames, with snapped posts, fallen floors and roof slabs, hanging boards and rubble.
   - Crates, barrels, boards, torn awnings and rubble lie along the aisle edges and around the buildings.
4. **The timber tower** (the old headframe) stands farther in, behind the arch, at (1, −86), scaled to 0.6. In Burning it is snapped.
5. **Beyond:**
   - The lower town at market level (z −109..−115), with rows of hazed roofs behind it (z −124..−155).
   - Barns at x ±36, windmills, woods and fields.
   - Three mountain ranges at z −170, −300 and −520. The nearest range dips straight ahead, so a valley opens behind the town.

## Day (weathered)
- A hazy, high-cloud morning sky; greyer haze, and muted fields and mountains.
- Every stone, plaster and light-wood surface carries grime: streaks running down the walls and blotchy dirt.
- The general store has lost the front of its roof (bare rafters), its awning is torn and half down, and a porch post has been knocked over. The house behind it is partly unroofed.
- One faded string of pennants still runs from the arch. A second has snapped and trails in the dirt.
- Two of the wrecked timber buildings still smoulder: thin wisps of smoke.

## Burning (evening)
- **Damage:** stalls mostly crushed, a fallen lamp on the steps, stones knocked loose, burnt-through roofs, and charred timber.
- **Fires and smoke:** fires in the market, the lower town and the barns, smoke rising behind the arch, and haze layers from z −66 back.
- **Crowd:** worried figures (`ce_crowd`) carry water up and down the steps and stand at the foot of the stairs and in the market.

## Cameras in the .blend
- The fight cameras.
- `CAM_market`: at the head of the stairs, looking down into the courtyard.
- `CAM_market_up`: in the courtyard by the arch, looking back up the stairs.

## What moves (all visual: shader `TIME` and CPU particles, nothing in the rollback state)

| Effect | Variant | Where / knobs |
|---|---|---|
| Drifting clouds / dusk sky | both | `Stage/Sky` |
| Fluttering pennants | both | `Stage/Bunting`: `flutter`, `speed`, `tint` |
| Grass tufts swaying (also in the joints of the steps) | both | `Stage/Grass` |
| Windmill sails | both | `Stage/Sails` |
| Smoke wisps from the wrecks | Day | `Stage/Smoke` |
| Flames, smoke plumes, haze layers | Burning | `Stage/Fire`, `Stage/Smoke`, `Stage/Haze` (positions: `FIRES`, `SMOKES`, `HAZE` in `build_celdic.py`) |
| Restless crowd | Burning | `Stage/Crowd` (`ce_crowd.gdshader`) |
| Sparks over the fires, embers, ash, smog | Burning | `FX/*` (spark positions: `SPARKS` in the scene generator) |
| Motes, petals, dust over the courtyard | Day | `FX/*` |

## Re-baking

Run it in a background Blender, so it never touches the Blender windows you have open:

```
blender --background --factory-startup --python "<project>/stages/celdic/src/run_ce.py" -- VARIANT=burning STEPS=build,bake,preview,export CAMS=CAM_mid
```

- `VARIANT` is `day` or `burning`.
- Each bake takes about 1 minute on the RX 9070 XT. When it finishes it writes `src/cache/_status_<variant>.json`.
- The export writes `celdic(_burning).glb` and `textures/floor_light(_burning).png` straight into this folder.

## Notes
- The floor bakes a **light map only**.
- The stairs and the courtyard lie **below** the platform level. The bake's cut below the floor must stay off.
- Builders that work at ground level are placed in the courtyard with `lifted(LY, ...)`, which moves their geometry and their lamp, window, fire, smoke and crowd entries down together.
- Card UVs store their ids in `UV.y`. glTF flips v, so the shaders decode them as `id = -floor(UV.y)` and `h = 1 - fract(UV.y)`.
