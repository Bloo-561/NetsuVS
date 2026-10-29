# Cecilia 3D v2: Milestone 1 (reference rig, height check, plan)

Everything lives in `actors/cecilia/3d_v2/`. Nothing outside it was touched.

## What's done

| File | What it is |
|---|---|
| `cecilia_v2.blend` | Reference rig. Collections: `REF` (the three ref images on the ortho axes), `CAMS` (ortho cameras framed exactly like each crop, hidden in the viewport), `GUIDES` (landmark height lines + labels, viewport only), `MODEL` (empty, the character goes here). Scene `SIL` is the silhouette-render setup. |
| `refs/masks/mask_{front,back,side}.png` | Silhouette masks cut from the refs (white figure on black). `check_*.png` show the background tinted blue. |
| `refs/landmarks.json` | Every measurement below, with method and uncertainty. |
| `scripts/cfg.py` | Scale, placement and the image-to-world mapping. All numbers measured, none guessed. |
| `scripts/ref_masks.py` | Rebuilds the masks (runs in Blender, numpy only). |
| `scripts/rig_refs.py` | Rebuilds the reference rig and saves the .blend. |
| `scripts/silhouette.py` | The IoU check used at every milestone: flat white render per view, IoU vs mask, diff image (red = reference only, blue = model only), per-band numbers. `selftest()` proves the pipeline. |
| `scripts/report/m1_report.py` | This report's figures (plain Python + Pillow, not Blender). |
| `renders/m1_height_check.png`, `m1_front_vs_backmirror.png`, `m1_masks.png` | Figures. |

Re-run in Blender's Python console:
```python
import runpy; S = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d_v2\scripts"
runpy.run_path(S + r"\ref_masks.py", run_name="__main__")   # masks
runpy.run_path(S + r"\rig_refs.py", run_name="__main__")    # rig + save
runpy.run_path(S + r"\silhouette.py")["run"]("my_tag")      # IoU of whatever is in MODEL
```
Views: numpad 1 = front, ctrl+numpad 1 = back, ctrl+numpad 3 = side.

## Scale and placement

- **1 px = 2.3235 mm.** At 50 % edge coverage all three figures are exactly 680 px tall, so 680 px = 1.580 m in every view.
- **Soles on z = 0.** The crops do not line up perfectly: the back figure sits 1 px higher in its crop and the side figure 1 px lower than the front. Each view is placed by its own sole, so the head tops then agree exactly.
- **x = 0** is the torso centre line (front crop column 270.13). The back crop is placed at column 264.30, where the mirrored back overlaps the front best (sub-pixel search).
- **y = 0** is the mid-depth of the waist in the side view (column 129.75). She faces -Y, her left is +X.
- **The side view shows her RIGHT side** (Blender Left view, camera on -X). It is consistent with front/back: the near leg has the criss-cross stocking (her right leg), and the only part of the left-hip sword you can see is the gold end of the hilt poking out in front of her belly. So the "known inconsistency" in the brief isn't one. I'll use the side view for colour on her right side, and a mirrored copy (minus the stocking, sock and sword) on her left.

**Pipeline self-test** (flat meshes cut from the masks, rendered through the new cameras): front IoU 0.9997, side 0.9997, centroid offset 0.06 px. The cameras and mapping are pixel-exact. The front mesh seen by the back camera scores 0.913, the same number as the front-vs-back analysis below (computed separately), so the back-view mirroring is right too.

## Height check

Height above the sole in metres (1 px = 2.3 mm). Methods and uncertainties are in `refs/landmarks.json`.

| Landmark | Front | Back | Side | Spread |
|---|---|---|---|---|
| Head top (ahoge tip) | 1.580 | 1.580 | 1.580 | 0 |
| Crown (hair top, no ahoge) | 1.540 | 1.540 | 1.543 | 2 mm |
| Chin | 1.287 | hidden | 1.285 | 2 mm |
| Shoulder (top of arm) | 1.262 | 1.259 | 1.265 | 6 mm |
| Arm axis (cuff centre) | 1.224 | 1.222 | **1.210** | **14 mm** |
| Jacket hem | 1.034 | 1.029 | 1.032 | 5 mm |
| Waist (narrowest) | 1.033 | 1.038 | 1.027 | 10 mm (side is a flat plateau, +-16 mm) |
| Skirt hem, front of skirt | 0.741 | - | **0.755** | **14 mm** |
| Skirt hem, back of skirt | - | 0.741 | **0.790** | **49 mm** |
| Stocking top (right leg) | 0.646 | 0.645 | **0.658** | **13 mm** |
| Knee | 0.476 | 0.488 | 0.502 | 26 mm (no sharp feature, +-12 mm each) |
| Sock top (left leg) | 0.409 | 0.414 | hidden | 5 mm |
| Ankle (bow centre) | 0.129 | hidden | 0.127 | 2 mm |
| Sole | 0 | 0 | 0 | 0 |

**Matches within 1-3 px (7 mm or less):** head top, crown, chin, shoulders, jacket hem, sock top, ankle bows, soles. The waist is within its measuring uncertainty.

**Mismatches:**
1. **Skirt hem at the back, 4.9 cm.** The front and back views draw the hem curving down toward the centre, as if seen from slightly above. The side view draws it rising toward the back. One 3D hem can't match both.
2. **Skirt hem at the front, 1.4 cm** (same cause, smaller).
3. **Stocking top:** 1.3 cm higher in the side view.
4. **Arm:** the end-on cuff ring in the side view is drawn 1.4 cm lower than the cuffs in front/back. It's inside the torso outline in the side view, so it doesn't affect IoU.
5. **Knee:** 2.6 cm apart, but there's no crisp knee on the drawing, so this is borderline.

## Front vs back: the bigger problem

From front and back, a 3D model's silhouettes are exact mirror images. The sheet's are not: the front mask and the mirrored back mask overlap at **IoU 0.913**. Main differences:
- jacket body 3.6 cm wider in the front view;
- her left arm reaches 3.6 cm further in the front view (arm span 1.227 m front vs 1.190 m back);
- the sword hilt sticks out sideways in the front view but not the back;
- legs and feet up to ~1 cm apart; small hair-outline differences.

Even a perfect model can't score above **~0.956 in both front and back at once.** The 0.95/0.95 target leaves about 0.6 % of the figure for every other modelling error, and real modelling error is usually larger than that. Expect about 0.94-0.95 in both if I split the difference. If I favour the front instead, I'd expect about 0.97 front and 0.90 back. The side view has no such limit; 0.92 is comfortable.

## Corrections to the brief (the sheet wins)

- **"Round badge on the upper sleeve" (side view):** this is the T-posed arm seen end-on: the white rolled cuff as a ring, with the black-gloved hand and four fingertips inside it. I won't model a badge unless you say there is one.
- **Proportions:** hair top to chin is 25.3 cm of 1.54 m (hair top to sole), so she is about 6 heads tall, not 7. Arm span is 1.23 m against a 1.58 m height. The model follows the sheet.
- **Arm bands:** both arms have the red band in the turnaround (the old README said one); the brief agrees.

## Plan: what I'll model and how

The rule for every part: the geometry is generated by a script from the masks, so outlines are traced, not guessed.

**Vertical parts (silhouette lofting).** This covers torso, dress, jacket body, skirt, lace, legs, shoes, neck, and a blockout of the hair volume. For every 2-px row, the script reads the left/right edges from the front mask (blended with the mirrored back) and the front/back edges from the side mask. It then places a ring inscribed in that box. The ring is a superellipse, with an exponent per part, plus a pleat ripple on the skirt. The outermost points of every ring touch the mask edges, so the model's front and side silhouettes reproduce the masks by construction. What's left for the fit loop is shape between rows, the front/back compromise, and jagged detail.

| Part | Traced from | Notes |
|---|---|---|
| Legs (L, R) | front + mirrored back per leg, side depth | Right leg carries the stocking, left the sock; both get their colour from projection in M5 |
| Skirt + lace petticoat | front/back/side skirt masks | Pleat ripple; scallops traced as detail; hem shape per decision 2 below |
| Dress bodice, jacket body | front/back/side | Jacket is a shell over the dress, open front, flared cropped hem; collars in M4 |
| Arms (sleeves, cuffs, forearms) | front + mirrored back, sliced along X | Round sections centred on the arm axis at y = +2.7 cm; cuff radius 4.3 cm from the side view's end-on ring |
| Hands | front outline | Palm down, finger spacing from the end-on fingertips in the side view |
| Shoes + bows | front/back/side | Bows separate in M4 |
| Tachi | katana detail panel (true proportions) | Placed to match the front/back views (hilt end at x +17 cm, z 1.00 m; sheath tip at x +24 cm, z 0.66 m). "Down and back" angle limited so the sheath stays hidden in the side view, as drawn. Separate blade. |
| Head, face, eyes, hair, ahoge, clip, headband | all three views + eyes/headband panels | Milestone 3 (below) |
| Belts, shirt collar, tie, sailor collar, brooch, neckerchief | front/back outlines, depth from side | Milestone 4 |

**Fit loop (every milestone).** `silhouette.py`: IoU per view and per height band, plus diff images. Then I adjust the generator parameters and rebuild, until the targets are hit or the remaining error is pinned to a sheet inconsistency (each one shown in the diff).

**Milestone 3, head.** The face profile is a silhouette in the side view, so it's exact. The cheek and jaw outline comes from the skin edge in the front view. Eyes are separate meshes so they can be rigged; colour from the front view plus the eyes panel. Hair is 25-40 clumps (bangs, the lock between the eyes, side locks, back layers, nape tips, ahoge), each traced in the view where it is clearest and fitted to all three silhouettes. The purple fade comes from projection. The sheet has no 3/4 view, so for the 3/4 close-up I'd compare against your other artwork (MainRender, Portrait, win render, idle1) for looks only. Go/no-go is judged there.

**Milestones 5-8** as briefed:
- Projection with occlusion (ray-cast visibility, so the front image doesn't paint through to the back) and angle blending.
- Seam and hidden-area cleanup, flattened to base colours.
- Toon ramp; inverted-hull outlines tuned to the sheet's ~1.5-2 px line (about 4 mm).
- Custom armature with IK and switchable sword sockets.
- Sprite camera matched to idle1.

## Risks

1. **Front/back IoU ceiling** (above). Not fixable by modelling; needs your call.
2. **Face and hair at 3/4.** A face projected from the front looks right from the front and the side but can look flat or off at 3/4, and the sheet has no 3/4 to check against. This is where the first attempt failed, and it decides M3.
3. **Jagged detail** (lace scallops, hair tips, fingers, ahoge) costs IoU if smoothed. It's modelled as detail pieces, which takes time but is doable.
4. **Projection seams.** The views disagree by 1-5 cm in places (hem, stocking top), so textures from different views won't meet cleanly and need hand cleanup in M5.
5. **Hidden areas** (under the arms, inside the skirt, soles, top of head) have no reference and will get flat base colours.
6. **Sword angle.** The side view hides the sheath, so its backward tilt is bounded, not measured.

## Decisions I need

1. **IoU target for front/back:** (a) split the difference, expecting ~0.94-0.95 each, and I report exactly how much is the sheet's fault; or (b) favour the front, ~0.97 front / ~0.90 back.
2. **Skirt hem at the back:** follow the front/back views (hem at the same height front and back; the side view's skirt back then hangs ~5 cm lower than drawn), or follow the side view (hem rises 5 cm at the back; the back-view stripes and lace get cut off). I suggest front/back.
3. OK to drop the "badge", and to use your other Cecilia artwork as a looks-only 3/4 reference in M3?
