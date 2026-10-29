# Cecilia Richter: 3D model v2 (Netsu VS)

A cel-shaded, rigged 3D model of Cecilia Richter in the Guilty Gear Xrd style. It was traced from her turnaround sheet so that sprite frames rendered from it stay on-model. It is built and rendered in Blender 5.2 (the file `cecilia_v2.blend`). Every step is a script in `scripts/`, so the whole model can be rebuilt.

Godot ignores this folder (`.gdignore`).

## Final numbers

**Silhouette against the sheet.** The model is rendered as a flat white silhouette, with an orthographic camera framed exactly like each reference crop, and compared with the sheet's own silhouette (`scripts/silhouette.py`). The rest pose, measured with the rig live:

| view | IoU | target |
|---|---|---|
| front | **0.9503** | 0.95 |
| back | **0.9503** | 0.95 |
| side | **0.9676** | 0.92 |

**Outlines.** Each outline is 1.75 sheet px wide, against the sheet's 1.83–1.98 px. At sprite scale it is one pixel.

**Sprite test.** `renders/idle_test.png` is her idle stance through the sprite camera, framed like `actors/cecilia/Sprites/idle1.png`:
- 247 px tall including the ahoge;
- feet on row 620 and the rear foot on column 403;
- silhouette IoU against idle1: **0.695**.

A second frame through the same, unmoved camera, the two-handed draw-slash against `5m4.png`, scores 0.554. Its feet land on the same row and column. The difference is mostly the sword and the sprites' bigger heads; see "What still needs an artist".

Each milestone's notes and review sheet:

| milestone | notes | review sheet |
|---|---|---|
| reference rig and plan | `PLAN_M1.md` | |
| 2 | `M2_NOTES.md` | `renders/m2_*` |
| 3 | `M3_NOTES.md` | `renders/m3_*` |
| 4 | `M4_NOTES.md` | `renders/m4_*` |
| 5 | `M5_NOTES.md` | `renders/m5_review.png` |
| 6 | `M6_NOTES.md` | `renders/m6_review.png` |
| 7 | `M7_NOTES.md` | `renders/m7_review.png` |
| 8 | `M8_NOTES.md` | `renders/m8_review.png` |

## What's in the file

### Collections

| collection | contents |
|---|---|
| MODEL | 44 objects: the character's 42 parts (hair, bangs, ahoge, face, ears, skull filler, headband, clips, body, neck, jacket, collars, tie, neckerchief, brooch, arms, hands, skirt, lace petticoat, belts and buckles, legs, shoes, bows, and the tachi: saya, saya_mouth, saya_tip, blade, tsuka, tsuba, kashira, hanger strap), plus two shading helpers, `GG_FaceNormalCentre` and `GG_HairNormalProxy` |
| RIG | `CEC_rig`, the armature |
| WGT | the control shapes (hidden) |
| REF, CAMS, GUIDES | the sheet's front, back and side images on the orthographic axes, cameras framed exactly like them, and landmark height lines (Milestone 1) |

### Scenes

| scene | use |
|---|---|
| Scene | the working scene: model, rig, references |
| SPRITE | sprite frames: camera `CAM_sprite`, 1024 x 1024, transparent |
| SPRITE_SIL | silhouette passes for framing the sprite camera |
| REVIEW, HEADREVIEW | review renders |
| SIL | silhouette measurement against the sheet |

### Shading

The shading follows the Guilty Gear Xrd model:
- a two-tone ramp plus a darker second shadow, and a specular term;
- every colour sampled from the sheet;
- one fixed key light;
- inverted-hull outlines in the sheet's line colours.

The node group is `GG_Shade`. Its control maps (occlusion, threshold, specular) are measured from the model and stored in `textures/`. The face uses view-dependent eyes taken from the sheet's eyes panel, with irises the eye bones can move (`refs/face/`). The skirt's shadow on the legs is computed live from the posed skirt.

### The rig (`CEC_rig`, 112 bones)

| bones | details |
|---|---|
| arms and legs | IK, with elbow and knee poles |
| fingers and thumbs | three bones each |
| spine | spine, neck and head |
| eyes | eye bones aimed at `eyes_target` |
| hair | hair chains, bangs, ahoge |
| neckerchief | knot and two tails |
| skirt | 8 chains round the waist; they open with the thighs |
| sword | sheath, sword and hilt, plus the sockets for hip, right hand and both hands |

The bone collections are Controls, Body, Fingers, Face, Hair, Cloth, Skirt, Sword and Mechanism (hidden). Weights are computed from the geometry, not painted. The face, headband, sword parts, belts, brooch and bows follow one bone each.

## How to pose her

1. Open `cecilia_v2.blend`, select `CEC_rig` and switch to Pose Mode.
2. Move the controls:

| control | moves |
|---|---|
| `torso` | hips and upper body |
| `foot_ik.L` / `.R` | the feet, with `knee_pole.L` / `.R` setting which way the knees bend |
| `hand_ik.L` / `.R` | the hands, with `elbow_pole.L` / `.R` |
| `eyes_target` | where both eyes look |
| `root` | the whole character |

3. Rotate the rest directly: spine, chest, neck, head, clavicles, fingers, hair, scarf tails, skirt.
4. **Sword:** in Object Properties > Custom Properties of `CEC_rig`:

| property | values |
|---|---|
| `sword` | 0 in the sheath, 1 right hand, 2 both hands |
| `sheath` | 0 on the hip, 1 held (follows the `sheath_hold` control, as in her idle stance) |
| `hand_L` | 1: the left hand holds the hilt |
| `hand_R` | 1: the right hand holds the sheath |

The ready-made poses are in `scripts/rig_poses.py`: `idle` (the sprite stance), `draw_slash`, `draw_slash_sprite`, `right_hand`, `overhead` and `rest`. Run them from Blender's Python console:

```python
import runpy
S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
P = runpy.run_path(S + r"\rig_poses.py")
P["pose"]("idle")                          # or "draw_slash_sprite", "rest", ...
P["pose"]("idle", head_yaw=-20.0)          # keyword overrides (see IDLE in rig_poses.py)
```

## How to render a sprite frame

The sprite camera, `CAM_sprite` in the SPRITE scene, is fitted to idle1.png:
- orthographic;
- 80° round to her right from her front, level;
- 5.23 mm per pixel.

It is framed so the idle stance stands like idle1: feet on row 620, rear foot on column 403. **Leave the camera where it is for every frame.** Pose her, and scale and ground line stay the same as in the game's sprites. To move her in the frame, move `root`.

**The game format** is 4x supersampled, outlines one pixel wide, and alpha cut at 50 % like the pixel-art sprites:

```python
SP = runpy.run_path(S + r"\sprite.py")
SP["render"](r"E:\...\frame.png")                 # the current pose
SP["render"](r"E:\...\frame.png", smooth=True)    # anti-aliased alpha instead
```

**A quick look:** switch to the SPRITE scene and press F12.

**To reproduce the idle test:** `SP["idle_test"]()`. It poses the idle, frames the camera on it again and writes `renders/idle_test.png`.

**A new camera angle** is only needed for a new kind of shot: `SP["frame_camera"](az, el)` frames the current pose. To compare a frame with an existing sprite, use `SP["frame_test"]("draw_slash_sprite", "5m4")`.

## How to rebuild from scratch

Run these in Blender, in order, starting from an empty file. All paths are relative to `scripts/`.

```python
runpy.run_path(S + r"\rig_refs.py", run_name="__main__")                        # reference images, cameras, guides (M1)
m4 = runpy.run_path(S + r"\m4_preview.py");  m4["run"]("tag", build=m4["FULL"], shade=False)   # geometry
runpy.run_path(S + r"\m6_preview.py")["run"]("tag", unwrap=True, sil=True)     # UVs, colour bake, shading maps, materials
runpy.run_path(S + r"\rig_build.py")["build"]()                                # armature
runpy.run_path(S + r"\rig_weights.py")["run"]()                                # skinning, rigid parts
runpy.run_path(S + r"\rig_eyes.py")["run"]()                                   # moving irises
runpy.run_path(S + r"\toon.py")["apply"]()                                     # materials again (live skirt shadow, eye drivers)
runpy.run_path(S + r"\sprite.py")["idle_test"]()                               # sprite camera + idle test
```

`m6_preview`, `toon.apply` and `shade_bake` work in the rig's Rest Position by themselves. `rig_build` can be re-run on a posed rig.

**What was checked:**
- a rebuild of the rig steps reproduced the saved poses to 0.0001 mm (M7);
- a rebuild of the texture steps reproduced the M6 maps byte for byte (M6). The review sheets are composed outside Blender with plain Python and Pillow (`m6_sheet.py`, `m7_sheet.py`, `m8_sheet.py`).

## What still needs an artist (or a decision)

**Your decisions:**
1. **Sword length.** The sheet draws the tachi about 41 cm long, with a 9.6 cm hilt; the game's sprites draw it about 1 m. The model follows the sheet. Lengthening it is a quick scripted change, but it is your call.
2. **Under the skirt.** Nothing is modelled between the tops of the legs and the bodice, because the sheet doesn't show it. Wide stances seen from low angles show the inside of the skirt. idle1 draws white petticoat there.

**Art work:**
1. **Sprite-scale finish.**
   - At about 250 px the face's eyes are 2–3 px, so a sprite-scale face pass (bigger eyes, darker lines) would help.
   - The interior lines are the sheet's coloured line art, lighter than the sprites' near-black pixel outlines.
   - The frames are clean cel renders, not pixel art; matching the hand-made sprites exactly needs a cleanup pass.
2. **Proportions.** The sprites draw her head about a third bigger and her hair fuller and more violet than the sheet does. The model follows the sheet.
3. **Hair and face shadows.**
   - The hair's shadow edge is a straight line; GG paints hair shadows to follow the clumps.
   - The face's 3/4 shadow is one clean diagonal, not an artist's shape.
   - Both want hand-painted threshold maps.
4. **Extreme poses.** Nothing collides, and hair, skirt and scarf move by bone rotation only. The test poses are clean, but deep lunges fold the back of the skirt. Extreme poses need corrective shapes or a cloth pass.
5. **Sheet details still open:**
   - the stocking ribbons' side and back views (the sheet's views disagree);
   - the loafers' vamp and the bows' loops;
   - the end-on hand in the side view;
   - a hand-drawn "IV" decal for very close views;
   - the back view, which is darker than the sheet because the key light is fixed in front.

## Folders

| folder | contents |
|---|---|
| `scripts/` | every step (see the docstring at the top of each) |
| `textures/` | baked colour and control maps |
| `refs/` | the sheet crops, masks, traced profiles, the face layers |
| `renders/` | review renders, silhouettes (`sil/`), sprite tests, fitting checks (`checks/`) |
| `backup/` | everything replaced along the way, by milestone |
