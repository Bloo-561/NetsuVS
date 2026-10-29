# Milestone 7: rig, test poses and deformation

`CEC_rig` drives the M6 model. It has:
- IK arms and legs;
- fingers and thumbs;
- head and eyes, with the eye bones moving the irises in the face shader;
- hair, neckerchief and skirt chains;
- the tachi's sockets: hip, right hand and both hands, plus "sheath held" for her idle stance.

It is tested in her idle stance next to `Sprites/idle1.png` and in a two-handed draw-slash, the 5C cut, next to `Sprites/5m4.png`. Two extra poses test the right-hand socket and a fully raised arm. Every pose is checked at the shoulders, hips and skirt.

**The rest pose is unchanged.** With the rig live, the silhouettes still measure the same as M6:

| | front | back | side |
|---|---|---|---|
| IoU at rest, rig live | **0.9503** | **0.9503** | **0.9676** |
| M6 | 0.9503 | 0.9503 | 0.9676 |

**Rebuilds are exact.** A rebuild from the scripts (`rig_build` → `rig_weights` → `rig_eyes`) reproduces the idle and slash poses to 0.0001 mm on all 376,255 vertices.

- Review sheet: `renders/m7_review.png`. It shows the poses next to the sprites, all-round views, shoulder and hip/skirt close-ups, the four sword states, the eye controls and the rig drawn over the rest pose.
- Single renders: `renders/m7_*.png`.
- Saved file: `cecilia_v2.blend`. The M6 file is in `backup/m6/`.

## The rig (`scripts/rig_build.py`)

There are 112 bones, 89 of which deform. All of them are placed from the model's own measurements.

| collection | bones |
|---|---|
| Body | root chain: `pelvis`, `spine`, `chest`, `neck`, `head`; `clavicle`, `upper_arm`, `forearm` and `hand` .L/.R; `thigh`, `shin`, `foot` and `toe` .L/.R |
| Fingers | `index`, `middle`, `ring` and `pinky` `_01..03`, `thumb_01..03`, each .L/.R |
| Hair | `hair_back_01/02`, `hair_front`, `hair_side` and `hair_back_side` `_01/02` .L/.R, `bangs`, `ahoge_01/02` |
| Cloth | `neckerchief`, `scarf_tail_01/02` .L/.R |
| Skirt | front, back, and front-side / side / back-side .L/.R, each `_01` (waistband to mid) and `_02` (to the hem) |
| Face | `eye.L`, `eye.R` (Damped Track to `eyes_target`), `eyes_target` |
| Sword | `sheath`, `sword`, `hilt` |
| Controls | `root`, `torso`; `hand_ik`, `elbow_pole`, `foot_ik` and `knee_pole` .L/.R; `sheath_hold` |
| Mechanism (hidden) | `socket_hip`, `sword_slot`, `hilt_straight`, `socket_hand.R`, `grip.L`, `grip_sheath.R` |

**Conventions.** 1 unit = 1 m, Z up, she faces −Y and her left is +X. Names end in `.L`/`.R` for her own sides, so Blender's mirror tools work. Limb bones are rolled so that on both sides a negative local-X rotation curls a finger towards the palm. Spine, neck and head: +X bends forward, +Y turns towards her left.

**IK.** The arms and legs are two-bone IK chains with poles. Hands and feet copy their IK control's rotation. The pole angles are fitted by testing each candidate, because the textbook formula has the wrong sign in this Blender version.

**Skirt.** Each chain follows the thigh nearest it in angle round the waist: Copy Rotation, at up to half influence, fading with angle. The skirt opens with the legs without being stretched by them.

**Joints** are where the sheet puts them. For example, the elbow is just above the rolled cuff and the wrist is where the glove starts. See the docstring in `rig_build.py`.

## Skinning (`scripts/rig_weights.py`)

No weight is painted; every weight is computed from the rest geometry:
- **Chains** (arms, legs, fingers, scarf tails, ahoge): each vertex is projected onto the chain, with a smooth blend across each joint.
- **Torso garments:** pelvis, spine, chest and neck by height; the clavicle and upper arm take the shoulders.
- **Skirt and lace:** the two nearest chains by angle, mixed with the pelvis at the waistband.
- **Hair:** the head bone above the ears, then the nearest hair chains.
- **Preserve volume** is on for the arms, hands, legs, body, jacket and neck.

The Armature modifier sits after the cloth thickness (Solidify) and before the normal blur, the hair-normal transfer and the outline hull. Those three must see the posed shape.

**Rigid parts** are children of one bone, with no skinning:

| bone | parts |
|---|---|
| head | face, ears, skull filler, headband, clips, and the face and hair normal helpers |
| sheath | saya and its fittings |
| sword | blade |
| hilt | tsuka, tsuba, kashira |
| pelvis | belts, buckles, hanger strap |
| chest | brooch |
| feet | bows |

The face must stay rigid because its shader reads object coordinates.

## Sword system

Four custom properties on `CEC_rig` switch the sword. Drivers do the rest, using simple expressions only, so Blender needs no Python auto-run.

| property | 0 | 1 | 2 |
|---|---|---|---|
| `sword` | in the sheath | right hand (`socket_hand.R`) | both hands (right-hand socket + left hand on the hilt) |
| `sheath` | on the left hip (`socket_hip`) | held: follows `sheath_hold` | |
| `hand_L` | own IK control | on the hilt (`grip.L`) | |
| `hand_R` | own IK control | on the sheath (`grip_sheath.R`) | |

- When drawn or held, the hilt straightens in line with the blade. The sheet bends the hilt only while it hangs at the hip (see M4).
- The blade is hidden while sheathed.
- The idle stance uses sword 0, sheath 1, hand_L 1, hand_R 1. The draw-slash uses sword 2.

## Eye controls (`scripts/rig_eyes.py`, `face_texture.py`, `gg_face.py`)

The eyes are texture (the sheet's eyes panel), so the eye bones move the irises in the face shader.

`face_texture` now also writes three layers:

| layer | what it holds |
|---|---|
| `refs/face/face_eye_frame.png` | the eyes with each iris painted over in the sclera's own colour, row by row, so the grey shadow under the lid stays |
| `face_eye_iris.png` | each iris as a full ellipse, fitted to its visible edge (fit error under 0.75 panel px) |
| `face_eye_open.png` | the eye opening |

**Compositing.** The face material lays the moved iris over the frame and clips it to the opening, so the iris slides under the lashes. At rest the three layers recombine into the M6 eyes; the render differs only along the iris's anti-aliased edge.

**Drivers.** Each eye's swing in local space (head turns don't count) moves its iris:
- 17.5 sheet px per radian;
- clamped to ±6 px across and ±3 px up and down;
- measured from the rest swing, so the eyes are the sheet's eyes at rest. The bones converge on `eyes_target` 45 cm in front.

Animate with `eyes_target` (both eyes) or by rotating `eye.L` / `eye.R`.

## Test poses (`scripts/rig_poses.py`)

All poses are set with the rig's controls only, the way an animator would.

| pose | what it is |
|---|---|
| `idle` | idle1's stance at its angle. Camera 40° to her right-front, 5° up (`IDLE_AZ`). Left foot forward, deep stance, the sheathed tachi held level across the hips (left hand on the hilt, right hand on the saya, 30 % from the mouth, as on idle1), face turned 3/4 to screen-right. |
| `draw_slash` | the cut of her two-handed draw, 5C as in `5m4.png`. Long lunge, left foot forward as in all her sprites, rear leg straight, body leaning in, both arms straight out at chest height, blade level, sheath on the hip. Feet are placed from the hips and pulled in if the leg couldn't reach (`place_foot`). |
| `right_hand` | the sword in the right hand, held out level. |
| `overhead` | shoulder test: the sword raised high in the right hand, left hand on the sheath at the hip. |
| `rest` | the bind pose. |

`scripts/m7_review.py` renders everything on the sheet, and `scripts/m7_sheet.py` composes it outside Blender.

## Deformation check

**Shoulders** (idle, slash, arm fully raised; front, back, side and from below):
- No collapse or candy-wrapper twist.
- With the arm up, the jacket's side stretches up with it and the sleeve keeps its volume.
- In the slash, the shoulders roll forward with the clavicles. The jacket stays over the shirt.

**Hips:**
- The deep lunge (pelvis down 30 cm, legs about 1.1 m apart) and the idle stance bend cleanly at the hip and knee.
- Thighs keep their volume and nothing pokes through.

**Skirt:**
- It opens with the legs. The pleats ride on the thighs instead of being pierced by them, in every close-up.
- In the deepest lunge, the back panel folds in where the rear thigh pushes it (slash side view). There is no cloth collision.

## Bug found and fixed

The first renders of the drawn sword had the face, headband, sword parts, belts and bows floating away from the body. The face hung at chest height.

**Cause.** Rebuilding the rig while it was posed un-parented the rigid parts at their posed position. Re-binding then baked that pose into their rest transform.
- `rig_build._remove_old` and `rig_weights._parent_to_bone` now work from the rest pose only (`rest_world`). They never read or set `matrix_world`, which Blender resolves through the pose.
- `scripts/rig_fix_rest.py` put every part back at its M6 transform, recorded from `backup/m6/cecilia_v2.blend` in `scripts/_m6_object_world.json`.
- The rebuild check above runs through this path.

## What still looks wrong / open questions

1. **The sword's length: the sheet and the game disagree. Your call.**
   - The turnaround draws the tachi about 41 cm overall, with a 9.6 cm hilt. All three views agree and the model follows them. The katana panel shows normal sword proportions but no scale.
   - Every game sprite draws it about 1 m: idle1, 5m4, and the 5C brief's "guard to tip about as long as from her shoulder to her feet".
   - Consequences of keeping the sheet's sword:
     - the idle pose's hands sit close together instead of at the sword's ends as on idle1;
     - the two-handed grip only just fits, with the left fist over the pommel cap;
     - sprites rendered from the model won't match the existing ones.
   - Lengthening it is a quick change: scale the blade, saya and tsuka along the sword's axis, move the sockets and grips, and re-render.
2. **Nothing under the skirt.** The sheet doesn't show it, so between the tops of the legs (z 0.82) and the bodice (z 1.0) there is only the skirt. From low angles in wide stances you see the leg tops and the inside of the skirt. idle1 draws white petticoat there. Shorts or bloomers in the lace's white would close it; that needs your OK, since it isn't on the sheet.
3. **Baked shadow under the skirt.** The occlusion map was baked in the rest pose. When the skirt lifts, the thighs keep the old skirt shadow, including the lace's scalloped edge (idle and slash, front-low and below views). A pose-correct fix: the legs get their skirt shadow live (a ray from each leg vertex up to the skirt), with the skirt left out of the bake. Proposed for M8, where idle1 is the reference.
4. **Idle vs idle1 at equal height:**
   - our stance is about 9 % wider for its hip height;
   - the sprite's head and torso are drawn bigger (sprite proportions);
   - the hands are closer together (item 1).

   M8 fits the camera and the stance to idle1 exactly.
5. **Slash vs 5m4.** The sprite's lunge is longer and lower than a real 0.71 m leg can reach. The model's rear leg is at 98 % of its length.
6. **No collision anywhere.** Hair, skirt and scarf move by bone rotation only. The test poses are clean, but extreme poses would need corrective shapes or a cloth pass: an artist's or simulation job.
7. **Still open from M6:** ribbons in side and back views, the back view darker than the sheet, the straight hair and face shadow edges, and the loafer and bow details.

## Files

| file | what |
|---|---|
| `scripts/rig_build.py` | armature, IK, constraints, sword drivers, widgets, bone collections; rest-safe un-parenting |
| `scripts/rig_weights.py` | computed skinning; rigid parts bound from the rest pose |
| `scripts/rig_eyes.py` | eye-controlled irises: layers, face material, drivers |
| `scripts/rig_poses.py` | test poses and review renders (`pose(name)`, `render(...)`) |
| `scripts/rig_fix_rest.py`, `scripts/_m6_object_world.json` | the repair above, and M6's object transforms |
| `scripts/face_texture.py` | + eye layers (`eye_layers`, `eye_textures`) |
| `scripts/gg_face.py` | + moving-iris compositing (`iris=` argument, Value nodes `iris_du/dv.L/R`) |
| `scripts/m7_review.py`, `scripts/m7_sheet.py` | review renders and sheet |
| `refs/face/face_eye_frame.png`, `face_eye_iris.png`, `face_eye_open.png` | new layers. `face_eyes.png`, `face_tex.png`, `face_base.png` and `face_tex_check.png` were rewritten with identical pixels. |
| `renders/m7_*.png`, `renders/m7_bones.json`, `renders/sil/m7_rest_*` | review renders, the bones for the sheet, the rest-pose IoU |
| `renders/checks/m7_pose_snapshot.npz` | posed vertex positions used for the rebuild check |

## Backups

`backup/m6/` holds:
- the M6 `cecilia_v2.blend`;
- its textures and the `refs/` files it links.

M7 didn't change any body or hair texture.

## How to pose

1. Open `cecilia_v2.blend` and select `CEC_rig`.
2. In Pose Mode, move the controls in the Controls collection:
   - `torso`: hips and upper body;
   - `foot_ik` and `hand_ik` (.L/.R), with `knee_pole` and `elbow_pole` setting the bend;
   - `sheath_hold`: the held sheath.
3. Rotate the FK bones for the spine, neck, head, fingers, hair, scarf and skirt.
4. Set `sword`, `sheath`, `hand_L` and `hand_R` in the rig's Object Properties > Custom Properties.

From Python: `runpy.run_path(r"<3d_v2>\scripts\rig_poses.py")["pose"]("idle")`.

## Rebuild

```python
S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
runpy.run_path(S + r"\rig_build.py")["build"]()              # armature (works on a posed rig too)
runpy.run_path(S + r"\rig_weights.py")["run"]()              # skinning + rigid parts
runpy.run_path(S + r"\rig_eyes.py")["run"]()                 # eye layers, face material, drivers
runpy.run_path(S + r"\m7_review.py")["run"]()                # review renders
# outside Blender: python3 scripts/m7_sheet.py renders ../Sprites renders/m7_review.png renders/sil/m7_rest_iou.json
```
